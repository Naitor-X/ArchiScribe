"""
PDF-Konvertierung für ArchiScribe.

Konvertiert PDFs in Bilder für die Verarbeitung durch Vision-Modelle.

Funktionen:
- PDF-zu-Bild Konvertierung (pdf2image)
- Bild-Optimierung (DPI, Qualität)
- Base64-Encoding für API-Übertragung
- Multi-Page-Handling
"""

import base64
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from pdf2image import convert_from_path

from app.config import settings
from app.exceptions import PDFVerarbeitungsFehler
from app.logger import logger


@dataclass
class KonvertierungsErgebnis:
    """Ergebnis einer PDF-Konvertierung."""

    seiten_anzahl: int
    bild_pfade: list[Path]
    base64_bilder: list[str]
    original_pdf: Path


@dataclass
class BildOptimierung:
    """Konfiguration für Bild-Optimierung."""

    dpi: int = 200  # Balance zwischen Qualität und Größe
    max_breite: int = 2000  # Maximale Breite in Pixeln
    max_hoehe: int = 3000  # Maximale Höhe in Pixeln
    jpeg_qualitaet: int = 85  # Qualität für JPEG (1-100)


# Standard-Konfiguration für Vision-Modelle
STANDARD_OPTIMIERUNG = BildOptimierung(
    dpi=200,
    max_breite=2000,
    max_hoehe=3000,
    jpeg_qualitaet=85,
)


def pdf_zu_bilder(
    pdf_pfad: Path,
    output_ordner: Path,
    optimierung: Optional[BildOptimierung] = None,
) -> list[Path]:
    """
    Konvertiert ein PDF in einzelne PNG-Bilder.

    Args:
        pdf_pfad: Pfad zur PDF-Datei
        output_ordner: Ordner für die Ausgabebilder
        optimierung: Bild-Optimierungseinstellungen (optional)

    Returns:
        Liste der Pfade zu den erstellten Bildern (sortiert nach Seitenzahl)

    Raises:
        PDFVerarbeitungsFehler: Bei Konvertierungsfehlern
    """
    if optimierung is None:
        optimierung = STANDARD_OPTIMIERUNG

    if not pdf_pfad.exists():
        raise PDFVerarbeitungsFehler(f"PDF-Datei nicht gefunden: {pdf_pfad}")

    output_ordner.mkdir(parents=True, exist_ok=True)

    try:
        logger.info(f"Starte PDF-Konvertierung: {pdf_pfad.name}")

        # PDF zu Bildern konvertieren
        bilder = convert_from_path(
            str(pdf_pfad),
            dpi=optimierung.dpi,
            output_folder=str(output_ordner),
            output_file="page_",
            fmt="png",
            paths_only=True,
        )

        # Pfade normalisieren und sortieren
        bild_pfade = sorted([Path(b) for b in bilder])

        logger.info(f"PDF konvertiert: {len(bild_pfade)} Seiten")

        # Bilder optimieren falls nötig
        for bild_pfad in bild_pfade:
            _optimiere_bild(bild_pfad, optimierung)

        return bild_pfade

    except Exception as e:
        raise PDFVerarbeitungsFehler(f"Fehler bei PDF-Konvertierung: {e}")


def _optimiere_bild(bild_pfad: Path, optimierung: BildOptimierung) -> None:
    """
    Optimiert ein Bild auf die Zielgröße (in-place).

    Verwendet PIL für die Skalierung falls das Bild zu groß ist.
    """
    try:
        from PIL import Image

        with Image.open(bild_pfad) as img:
            breite, hoehe = img.size

            # Prüfen ob Skalierung nötig
            skalierung = min(
                optimierung.max_breite / breite,
                optimierung.max_hoehe / hoehe,
                1.0,  # Nicht vergrößern
            )

            if skalierung < 1.0:
                neue_breite = int(breite * skalierung)
                neue_hoehe = int(hoehe * skalierung)

                logger.debug(
                    f"Bild skalieren: {bild_pfad.name} "
                    f"von {breite}x{hoehe} auf {neue_breite}x{neue_hoehe}"
                )

                # Hochwertige Skalierung mit LANCZOS
                img_resized = img.resize((neue_breite, neue_hoehe), Image.Resampling.LANCZOS)
                img_resized.save(bild_pfad, "PNG", optimize=True)

    except ImportError:
        logger.warning("PIL nicht installiert - Bild-Optimierung übersprungen")
    except Exception as e:
        logger.warning(f"Bild-Optimierung fehlgeschlagen für {bild_pfad}: {e}")


def bild_zu_base64(bild_pfad: Path) -> str:
    """
    Konvertiert ein Bild in einen Base64-kodierten Data-URI.

    Returns:
        Data-URI String (z.B. "data:image/png;base64,...")
    """
    with open(bild_pfad, "rb") as f:
        bild_daten = f.read()

    base64_daten = base64.b64encode(bild_daten).decode("utf-8")
    return f"data:image/png;base64,{base64_daten}"


def konvertiere_pdf_fuer_vision(
    pdf_pfad: Path,
    output_ordner: Path,
    mit_base64: bool = True,
    optimierung: Optional[BildOptimierung] = None,
) -> KonvertierungsErgebnis:
    """
    Hauptfunktion: Konvertiert ein PDF für die Verarbeitung durch Vision-Modelle.

    Args:
        pdf_pfad: Pfad zur PDF-Datei
        output_ordner: Ordner für die Ausgabebilder
        mit_base64: Ob Base64-kodierte Bilder zurückgegeben werden sollen
        optimierung: Bild-Optimierungseinstellungen (optional)

    Returns:
        KonvertierungsErgebnis mit allen Informationen

    Raises:
        PDFVerarbeitungsFehler: Bei Konvertierungsfehlern
    """
    # PDF zu Bildern konvertieren
    bild_pfade = pdf_zu_bilder(pdf_pfad, output_ordner, optimierung)

    # Optional Base64-Encoding
    base64_bilder = []
    if mit_base64:
        logger.debug(f"Base64-Encoding für {len(bild_pfade)} Bilder")
        base64_bilder = [bild_zu_base64(pfad) for pfad in bild_pfade]

    return KonvertierungsErgebnis(
        seiten_anzahl=len(bild_pfade),
        bild_pfade=bild_pfade,
        base64_bilder=base64_bilder,
        original_pdf=pdf_pfad,
    )


def get_pdf_info(pdf_pfad: Path) -> dict:
    """
    Liefert Metadaten eines PDFs ohne Konvertierung.

    Returns:
        Dict mit Seitenzahl, Dateigröße etc.
    """
    try:
        from pdf2image.pdf2image import pdfinfo_from_path

        info = pdfinfo_from_path(str(pdf_pfad))

        return {
            "seiten_anzahl": info.get("Pages", 0),
            "dateigroesse_bytes": pdf_pfad.stat().st_size,
            "titel": info.get("Title"),
            "autor": info.get("Author"),
            "erstellungsdatum": info.get("CreationDate"),
        }
    except Exception as e:
        logger.warning(f"PDF-Info konnte nicht ermittelt werden: {e}")
        return {
            "seiten_anzahl": 0,
            "dateigroesse_bytes": pdf_pfad.stat().st_size if pdf_pfad.exists() else 0,
        }
