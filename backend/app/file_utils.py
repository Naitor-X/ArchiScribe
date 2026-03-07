"""
Datei-Management Utilities für ArchiScribe.

Stellt Funktionen bereit für:
- Ordnerstruktur-Erstellung
- Pfad-Handling für verschiedene Dateitypen
- Datei-Validierung
"""

import hashlib
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from app.config import settings
from app.exceptions import DateiNichtGefunden, UngueltigesDateiformat
from app.logger import logger


def ensure_directories() -> None:
    """
    Stellt sicher, dass alle benötigten Ordner existieren.
    Wird beim Startup der Anwendung aufgerufen.
    """
    ordner = [
        settings.inbox_path,
        settings.processing_path,
        settings.archive_path,
        settings.error_path,
    ]

    for ordner_pfad in ordner:
        ordner_pfad.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Ordner sichergestellt: {ordner_pfad}")


def get_processing_folder(process_id: uuid.UUID) -> Path:
    """
    Erstellt und gibt den Processing-Ordner für eine Verarbeitung zurück.

    Struktur: /files/processing/{process_uuid}/
    """
    folder = settings.processing_path / str(process_id)
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def get_archive_folder(tenant_id: uuid.UUID, project_id: uuid.UUID) -> Path:
    """
    Erstellt und gibt den Archiv-Ordner für ein Projekt zurück.

    Struktur: /files/archive/{tenant_id}/{project_id}/
    """
    folder = settings.archive_path / str(tenant_id) / str(project_id)
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def get_error_folder(original_filename: str) -> Path:
    """
    Erstellt und gibt den Error-Ordner für eine fehlgeschlagene Verarbeitung zurück.

    Struktur: /files/error/{timestamp}_{original_filename}/
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    # Sichere Dateinamen (Sonderzeichen entfernen)
    safe_name = "".join(c if c.isalnum() or c in "._-" else "_" for c in original_filename)
    folder = settings.error_path / f"{timestamp}_{safe_name}"
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def generate_timestamped_filename(base_name: str, extension: str, suffix: str = "") -> str:
    """
    Generiert einen eindeutigen Dateinamen mit Timestamp.

    Format: {base_name}_{suffix}_{YYYYMMDD_HHMMSS}.{extension}
    oder: {base_name}_{YYYYMMDD_HHMMSS}.{extension} wenn kein suffix
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    if suffix:
        return f"{base_name}_{suffix}_{timestamp}.{extension}"
    return f"{base_name}_{timestamp}.{extension}"


def validate_pdf_file(file_path: Path) -> None:
    """
    Validiert eine PDF-Datei.

    Prüft:
    - Datei existiert
    - Dateiendung ist .pdf
    - Dateigröße innerhalb Limit
    - PDF-Magic-Bytes

    Raises:
        DateiNichtGefunden: Datei existiert nicht
        UngueltigesDateiformat: Keine gültige PDF-Datei
    """
    if not file_path.exists():
        raise DateiNichtGefunden(str(file_path))

    # Dateiendung prüfen
    if file_path.suffix.lower() != ".pdf":
        raise UngueltigesDateiformat(file_path.name)

    # Dateigröße prüfen
    file_size = file_path.stat().st_size
    if file_size > settings.max_file_size_bytes:
        raise UngueltigesDateiformat(
            f"{file_path.name}: Datei zu groß ({file_size / 1024 / 1024:.1f}MB > {settings.max_file_size_mb}MB)"
        )

    # PDF-Magic-Bytes prüfen (%PDF-)
    try:
        with open(file_path, "rb") as f:
            header = f.read(5)
            if header != b"%PDF-":
                raise UngueltigesDateiformat(f"{file_path.name}: Keine gültige PDF-Datei")
    except IOError as e:
        raise DateiNichtGefunden(f"{file_path.name}: {e}")


def calculate_file_hash(file_path: Path) -> str:
    """
    Berechnet SHA-256 Hash einer Datei für Duplicate-Erkennung.
    """
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def move_file_to_processing(source: Path, process_id: uuid.UUID) -> Path:
    """
    Verschiebt eine Datei von Inbox in den Processing-Ordner.

    Returns:
        Pfad zur Datei im Processing-Ordner
    """
    dest_folder = get_processing_folder(process_id)
    dest_path = dest_folder / "original.pdf"
    source.rename(dest_path)
    logger.info(f"Datei verschoben: {source} -> {dest_path}")
    return dest_path


def move_to_archive(
    processing_folder: Path,
    tenant_id: uuid.UUID,
    project_id: uuid.UUID,
    png_files: Optional[list[Path]] = None,
    extraction_json: Optional[Path] = None,
) -> Path:
    """
    Verschiebt verarbeitete Dateien ins Archiv.

    Args:
        processing_folder: Ordner mit verarbeiteten Dateien
        tenant_id: Tenant-ID
        project_id: Projekt-ID
        png_files: Liste der konvertierten PNG-Dateien
        extraction_json: Pfad zur KI-Extraktions-JSON

    Returns:
        Pfad zum Archiv-Ordner
    """
    archive_folder = get_archive_folder(tenant_id, project_id)

    # Original-PDF verschieben
    original_pdf = processing_folder / "original.pdf"
    if original_pdf.exists():
        dest_name = generate_timestamped_filename("original", "pdf")
        original_pdf.rename(archive_folder / dest_name)

    # PNG-Dateien verschieben
    if png_files:
        for i, png_path in enumerate(png_files, start=1):
            if png_path.exists():
                dest_name = generate_timestamped_filename(f"page_{i:03d}", "png")
                png_path.rename(archive_folder / dest_name)

    # Extraktions-JSON verschieben
    if extraction_json and extraction_json.exists():
        dest_name = generate_timestamped_filename("extraction", "json")
        extraction_json.rename(archive_folder / dest_name)

    logger.info(f"Dateien archiviert: {archive_folder}")
    return archive_folder


def move_to_error(processing_folder: Path, error_message: str) -> Path:
    """
    Verschiebt fehlgeschlagene Verarbeitung in den Error-Ordner.

    Args:
        processing_folder: Ordner mit der fehlgeschlagenen Verarbeitung
        error_message: Fehlermeldung für error.log

    Returns:
        Pfad zum Error-Ordner
    """
    # Ursprünglichen Dateinamen aus processing_folder ableiten
    # (Verarbeitung läuft in UUID-Ordner, Originalname in metadata.json falls vorhanden)
    metadata_path = processing_folder / "metadata.json"
    original_name = "unknown"

    if metadata_path.exists():
        import json
        try:
            with open(metadata_path, "r") as f:
                metadata = json.load(f)
                original_name = metadata.get("original_filename", "unknown")
        except Exception:
            pass

    error_folder = get_error_folder(original_name)

    # Original-PDF verschieben
    original_pdf = processing_folder / "original.pdf"
    if original_pdf.exists():
        original_pdf.rename(error_folder / "original.pdf")

    # Fehler-Log schreiben
    error_log = error_folder / "error.log"
    with open(error_log, "w", encoding="utf-8") as f:
        f.write(f"Fehlerzeitpunkt: {datetime.now().isoformat()}\n")
        f.write(f"Fehlermeldung: {error_message}\n")

    logger.error(f"Verarbeitung fehlgeschlagen, Dateien in Error-Ordner: {error_folder}")
    return error_folder


def cleanup_processing_folder(process_id: uuid.UUID) -> None:
    """
    Berechnet den Processing-Ordner nach Abschluss der Verarbeitung.

    Entfernt den gesamten Ordner inklusive aller enthaltenen Dateien.
    """
    import shutil

    folder = settings.processing_path / str(process_id)
    if folder.exists():
        shutil.rmtree(folder)
        logger.debug(f"Processing-Ordner bereinigt: {folder}")
