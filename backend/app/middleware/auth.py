"""
API-Key Authentifizierungs-Middleware.

Validiert API-Keys via SHA-256 Hash-Vergleich und extrahiert Tenant-Informationen.
"""

import hashlib
import logging
import re
from contextvars import ContextVar
from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings

logger = logging.getLogger(__name__)

# Context-Variable für aktuellen Tenant (thread-safe für async)
_current_tenant: ContextVar[dict | None] = ContextVar("current_tenant", default=None)

# API-Key Format: sk-tenant-{tenant_id}-{random_32_chars}
API_KEY_PATTERN = re.compile(
    r"^sk-tenant-([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})-([a-z0-9]{32})$"
)

# Bearer-Security für OpenAPI-Dokumentation
bearer_scheme = HTTPBearer(auto_error=False)


class AuthenticationError(Exception):
    """Fehler bei der Authentifizierung."""

    def __init__(self, message: str, code: str = "authentication_failed"):
        self.message = message
        self.code = code
        super().__init__(message)


def hash_api_key(api_key: str) -> str:
    """
    Erstellt SHA-256 Hash eines API-Keys.

    Args:
        api_key: Der rohe API-Key

    Returns:
        Hex-String des Hashes
    """
    return hashlib.sha256(api_key.encode()).hexdigest()


def extract_key_prefix(api_key: str) -> str:
    """
    Extrahiert den Prefix eines API-Keys (erste 20 Zeichen).

    Der Prefix wird für die schnelle Identifikation verwendet,
    bevor der aufwändigere Hash-Vergleich durchgeführt wird.

    Args:
        api_key: Der API-Key

    Returns:
        Die ersten 20 Zeichen des Keys
    """
    return api_key[:20] if len(api_key) >= 20 else api_key


def parse_api_key(api_key: str) -> tuple[UUID, str] | None:
    """
    Parst einen API-Key und extrahiert Tenant-ID und Random-Teil.

    Args:
        api_key: Der API-Key im Format sk-tenant-{uuid}-{random}

    Returns:
        Tuple (tenant_id, random_part) oder None bei ungültigem Format
    """
    match = API_KEY_PATTERN.match(api_key)
    if not match:
        return None

    try:
        tenant_id = UUID(match.group(1))
        random_part = match.group(2)
        return tenant_id, random_part
    except ValueError:
        return None


async def validate_api_key(api_key: str) -> dict | None:
    """
    Validiert einen API-Key gegen die Datenbank.

    Args:
        api_key: Der zu validierende API-Key

    Returns:
        Dict mit tenant_id und key_info bei Erfolg, None bei Misserfolg
    """
    from app.database import get_connection

    # Key-Format prüfen
    parsed = parse_api_key(api_key)
    if not parsed:
        logger.warning(f"Ungültiges API-Key-Format")
        return None

    tenant_id, _ = parsed
    key_prefix = extract_key_prefix(api_key)
    key_hash = hash_api_key(api_key)

    try:
        async with get_connection() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, tenant_id, name, is_active, expires_at
                FROM api_keys
                WHERE key_prefix = $1 AND key_hash = $2
                """,
                key_prefix,
                key_hash,
            )

            if not row:
                logger.warning(f"API-Key nicht gefunden: prefix={key_prefix}")
                return None

            if not row["is_active"]:
                logger.warning(f"API-Key deaktiviert: {row['id']}")
                return None

            # Optional: Ablaufdatum prüfen
            if row["expires_at"]:
                from datetime import datetime, timezone

                if row["expires_at"] < datetime.now(timezone.utc):
                    logger.warning(f"API-Key abgelaufen: {row['id']}")
                    return None

            # last_used_at aktualisieren
            await conn.execute(
                "UPDATE api_keys SET last_used_at = CURRENT_TIMESTAMP WHERE id = $1",
                row["id"],
            )

            return {
                "tenant_id": row["tenant_id"],
                "key_id": row["id"],
                "key_name": row["name"],
            }

    except Exception as e:
        logger.error(f"Fehler bei API-Key-Validierung: {e}")
        return None


def get_current_tenant() -> dict | None:
    """
    Gibt den aktuellen Tenant aus dem Request-Kontext zurück.

    Returns:
        Dict mit tenant_id und key_info oder None
    """
    return _current_tenant.get()


def set_current_tenant(tenant_info: dict | None) -> None:
    """Setzt den aktuellen Tenant im Request-Kontext."""
    _current_tenant.set(tenant_info)


class APIKeyMiddleware(BaseHTTPMiddleware):
    """
    Middleware für API-Key-Validierung.

    Extrahiert den API-Key aus:
    1. Authorization: Bearer {api_key}
    2. X-API-Key Header

    Validiert den Key und setzt Tenant-Kontext.
    """

    # Pfade, die keine Authentifizierung benötigen
    PUBLIC_PATHS = {
        "/health",
        "/docs",
        "/redoc",
        "/openapi.json",
    }

    async def dispatch(self, request: Request, call_next):
        # Öffentliche Pfade überspringen
        path = request.url.path

        # Prüfen ob Pfad öffentlich ist oder mit /docs beginnt
        if path in self.PUBLIC_PATHS or path.startswith("/docs"):
            return await call_next(request)

        # API-Key aus Headern extrahieren
        api_key = None

        # 1. Authorization: Bearer {api_key}
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            api_key = auth_header[7:]  # "Bearer " entfernen

        # 2. X-API-Key Header (Fallback)
        if not api_key:
            api_key = request.headers.get("X-API-Key")

        # Development-Modus: Test-API-Key verwenden
        if not api_key and settings.app_env == "development":
            api_key = settings.dev_api_key

        # Kein API-Key vorhanden
        if not api_key:
            logger.warning(f"Kein API-Key für {path}")
            from fastapi.responses import JSONResponse

            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={
                    "error": "unauthorized",
                    "message": "API-Key erforderlich. Verwende X-API-Key oder Authorization: Bearer Header",
                    "details": None,
                },
            )

        # API-Key validieren
        tenant_info = await validate_api_key(api_key)

        if not tenant_info:
            logger.warning(f"Ungültiger API-Key für {path}")
            from fastapi.responses import JSONResponse

            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={
                    "error": "unauthorized",
                    "message": "Ungültiger API-Key",
                    "details": None,
                },
            )

        # X-Tenant-ID Header prüfen (zusätzliche Validierung)
        header_tenant_id = request.headers.get("X-Tenant-ID")
        if header_tenant_id:
            try:
                header_uuid = UUID(header_tenant_id)
                if header_uuid != tenant_info["tenant_id"]:
                    logger.warning(
                        f"Tenant-ID Mismatch: header={header_uuid}, key={tenant_info['tenant_id']}"
                    )
                    from fastapi.responses import JSONResponse

                    return JSONResponse(
                        status_code=status.HTTP_403_FORBIDDEN,
                        content={
                            "error": "forbidden",
                            "message": "Tenant-ID passt nicht zum API-Key",
                            "details": None,
                        },
                    )
            except ValueError:
                pass  # Ignorieren, API-Key ist maßgeblich

        # Tenant-Kontext setzen
        set_current_tenant(tenant_info)

        # Request weiterleiten
        response = await call_next(request)

        # Kontext bereinigen
        set_current_tenant(None)

        return response


# === FastAPI Dependencies für einfache Verwendung ===


async def require_tenant() -> dict:
    """
    Dependency, die einen authentifizierten Tenant erfordert.

    Raises:
        HTTPException: Wenn kein Tenant authentifiziert ist

    Returns:
        Dict mit tenant_id und key_info
    """
    tenant = get_current_tenant()
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Nicht authentifiziert",
        )
    return tenant


async def optional_tenant() -> dict | None:
    """
    Dependency für optionale Authentifizierung.

    Returns:
        Dict mit tenant_id oder None
    """
    return get_current_tenant()


# Type-Aliases für Dependency Injection
CurrentTenant = Annotated[dict, Depends(require_tenant)]
OptionalTenant = Annotated[dict | None, Depends(optional_tenant)]
