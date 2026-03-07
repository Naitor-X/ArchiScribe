"""
OpenRouter API-Client für KI-Extraktion von Grundlagenformularen.

Verwendet httpx für asynchrone HTTP-Requests mit Retry-Logik und Rate-Limiting.
"""

import asyncio
import json
import re
from typing import Any

import httpx

from app.config import settings
from app.exceptions import KIExtraktionsFehler
from app.logger import logger
from app.prompts import build_extraction_prompt, build_multi_page_prompt
from app.schemas.extraction import ExtractionResult


def _extract_json_from_response(content: str) -> dict[str, Any]:
    """
    Extrahiert JSON aus einer KI-Antwort.

    Behandelt verschiedene Formate:
    - Reines JSON
    - JSON in Markdown-Code-Blöcken
    - JSON mit zusätzlichem Text

    Args:
        content: Roher Antworttext der KI

    Returns:
        dict: Geparstes JSON-Objekt

    Raises:
        KIExtraktionsFehler: Wenn kein valides JSON gefunden wird
    """
    # Versuch 1: Direktes JSON-Parsing
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass

    # Versuch 2: JSON aus Markdown-Code-Block extrahieren
    markdown_pattern = r"```(?:json)?\s*([\s\S]*?)```"
    matches = re.findall(markdown_pattern, content)
    for match in matches:
        try:
            return json.loads(match.strip())
        except json.JSONDecodeError:
            continue

    # Versuch 3: JSON-Objekt im Text finden
    json_pattern = r"\{[\s\S]*\}"
    matches = re.findall(json_pattern, content)
    for match in matches:
        try:
            return json.loads(match)
        except json.JSONDecodeError:
            continue

    raise KIExtraktionsFehler(
        f"Kein valides JSON in der KI-Antwort gefunden. "
        f"Antwort beginnt mit: {content[:200]}..."
    )


def _build_messages(base64_images: list[str]) -> list[dict[str, Any]]:
    """
    Erstellt die Message-Struktur für die OpenRouter API.

    Args:
        base64_images: Liste von Base64-kodierten Bildern (Data-URI-Format)

    Returns:
        list: Messages-Array für die API
    """
    # Prompt basierend auf Seitenanzahl
    prompt = (
        build_multi_page_prompt(len(base64_images))
        if len(base64_images) > 1
        else build_extraction_prompt()
    )

    # Content-Array mit Text und Bildern
    content: list[dict[str, Any]] = [{"type": "text", "text": prompt}]

    for img in base64_images:
        content.append(
            {
                "type": "image_url",
                "image_url": {"url": img},
            }
        )

    return [{"role": "user", "content": content}]


async def _make_request_with_retry(
    client: httpx.AsyncClient, messages: list[dict[str, Any]]
) -> dict[str, Any]:
    """
    Führt API-Request mit Exponential-Backoff Retry aus.

    Args:
        client: httpx AsyncClient
        messages: Messages für die API

    Returns:
        dict: API-Response

    Raises:
        KIExtraktionsFehler: Nach erschöpften Retries
    """
    last_error: Exception | None = None

    for attempt in range(1, settings.openrouter_max_retries + 1):
        try:
            response = await client.post(
                f"{settings.openrouter_base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.openrouter_api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://archiscribe.local",  # Optional für Rankings
                },
                json={
                    "model": settings.openrouter_model,
                    "messages": messages,
                    "max_tokens": 4096,
                    "temperature": 0.1,  # Niedrige Temperatur für konsistente Ergebnisse
                },
            )

            # Rate-Limiting behandeln
            if response.status_code == 429:
                retry_after = int(response.headers.get("retry-after", 60))
                logger.warning(
                    f"Rate Limited. Warte {retry_after}s vor Retry "
                    f"(Versuch {attempt}/{settings.openrouter_max_retries})"
                )
                await asyncio.sleep(retry_after)
                continue

            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            last_error = e
            logger.error(
                f"OpenRouter HTTP-Fehler: {e.response.status_code} - {e.response.text}",
                error=e,
            )

            # Bei 401/403 kein Retry
            if e.response.status_code in (401, 403):
                raise KIExtraktionsFehler(
                    f"OpenRouter Authentifizierung fehlgeschlagen: {e.response.status_code}"
                )

            # Exponential Backoff
            wait_time = 2**attempt
            logger.warning(
                f"Retry in {wait_time}s (Versuch {attempt}/{settings.openrouter_max_retries})"
            )
            await asyncio.sleep(wait_time)

        except httpx.TimeoutException as e:
            last_error = e
            logger.error(f"OpenRouter Timeout", error=e)
            wait_time = 2**attempt
            logger.warning(
                f"Retry in {wait_time}s (Versuch {attempt}/{settings.openrouter_max_retries})"
            )
            await asyncio.sleep(wait_time)

        except httpx.RequestError as e:
            last_error = e
            logger.error(f"OpenRouter Request-Fehler", error=e)
            wait_time = 2**attempt
            logger.warning(
                f"Retry in {wait_time}s (Versuch {attempt}/{settings.openrouter_max_retries})"
            )
            await asyncio.sleep(wait_time)

    raise KIExtraktionsFehler(
        f"OpenRouter API nach {settings.openrouter_max_retries} Versuchen fehlgeschlagen. "
        f"Letzter Fehler: {last_error}"
    )


async def extract_form_data(base64_images: list[str]) -> ExtractionResult:
    """
    Extrahiert Formulardaten aus PDF-Seiten-Bildern via OpenRouter Vision-API.

    Args:
        base64_images: Liste von Base64-kodierten Bildern im Data-URI-Format
                      (z.B. "data:image/png;base64,...")

    Returns:
        ExtractionResult: Validiertes Extraktionsergebnis

    Raises:
        KIExtraktionsFehler: Bei API-Fehlern oder ungültiger Response

    Example:
        >>> from app.pdf_converter import pdf_zu_bilder
        >>> konvertierung = pdf_zu_bilder("formular.pdf")
        >>> ergebnis = await extract_form_data(konvertierung.base64_bilder)
        >>> print(ergebnis.client_name)
        "Max Mustermann"
    """
    if not base64_images:
        raise KIExtraktionsFehler("Keine Bilder für die Extraktion bereitgestellt")

    if not settings.openrouter_api_key:
        raise KIExtraktionsFehler(
            "OPENROUTER_API_KEY nicht konfiguriert. "
            "Bitte in .env-Datei eintragen."
        )

    logger.info(
        f"Starte KI-Extraktion für {len(base64_images)} Seite(n) "
        f"mit Modell {settings.openrouter_model}"
    )

    messages = _build_messages(base64_images)

    async with httpx.AsyncClient(timeout=settings.openrouter_timeout) as client:
        response_data = await _make_request_with_retry(client, messages)

    # Response validieren
    try:
        content = response_data["choices"][0]["message"]["content"]
    except (KeyError, IndexError) as e:
        raise KIExtraktionsFehler(
            f"Unerwartete API-Response-Struktur: {response_data}"
        ) from e

    # JSON extrahieren
    raw_json = _extract_json_from_response(content)

    # Pydantic-Validierung
    try:
        result = ExtractionResult.model_validate(raw_json)
    except Exception as e:
        raise KIExtraktionsFehler(
            f"KI-Response konnte nicht validiert werden: {e}\n"
            f"Rohdaten: {json.dumps(raw_json, ensure_ascii=False)[:500]}..."
        ) from e

    logger.info(
        f"KI-Extraktion erfolgreich. "
        f"Extrahierte Felder: {sum(1 for v in result.model_dump().values() if v is not None)}, "
        f"Räume: {len(result.rooms)}"
    )

    return result


def get_raw_response(base64_images: list[str]) -> dict[str, Any]:
    """
    Synchroner Wrapper für die Extraktion (für Debugging/Testing).

    Returns die rohe API-Antwort ohne Validierung.

    Args:
        base64_images: Liste von Base64-kodierten Bildern

    Returns:
        dict: Rohe API-Response
    """
    import asyncio

    async def _get_raw() -> dict[str, Any]:
        messages = _build_messages(base64_images)
        async with httpx.AsyncClient(timeout=settings.openrouter_timeout) as client:
            return await _make_request_with_retry(client, messages)

    return asyncio.run(_get_raw())
