"""
Watchdog-Service für PDF-Überwachung.

Überwacht den /files/inbox/ Ordner und startet bei neuen PDF-Dateien
automatisch die Verarbeitung.
"""

import json
import time
import uuid
from pathlib import Path
from typing import Callable, Optional

from watchdog.events import FileCreatedEvent, FileSystemEventHandler
from watchdog.observers import Observer

from app.config import settings
from app.file_utils import (
    calculate_file_hash,
    get_processing_folder,
    move_file_to_processing,
    validate_pdf_file,
)
from app.logger import logger


class PDFFileHandler(FileSystemEventHandler):
    """
    Event-Handler für neue PDF-Dateien im Inbox-Ordner.
    """

    def __init__(
        self,
        on_pdf_detected: Optional[Callable[[Path, uuid.UUID, str], None]] = None,
    ):
        """
        Args:
            on_pdf_detected: Callback-Funktion (file_path, process_id, file_hash)
                            wird aufgerufen wenn eine neue PDF erkannt wird.
        """
        self.on_pdf_detected = on_pdf_detected
        self._processed_hashes: set[str] = set()  # Cache für bereits verarbeitete Hashes
        self._load_processed_hashes()

    def _load_processed_hashes(self) -> None:
        """
        Lädt bereits verarbeitete Hashes aus einer Datei.
        Verhindert doppelte Verarbeitung nach Neustart.
        """
        hash_file = settings.processing_path / ".processed_hashes.json"
        if hash_file.exists():
            try:
                with open(hash_file, "r") as f:
                    self._processed_hashes = set(json.load(f))
                logger.info(f"{len(self._processed_hashes)} verarbeitete Hashes geladen")
            except Exception as e:
                logger.warning(f"Konnte Hash-Datei nicht laden: {e}")

    def _save_processed_hashes(self) -> None:
        """Speichert verarbeitete Hashes in Datei."""
        hash_file = settings.processing_path / ".processed_hashes.json"
        try:
            with open(hash_file, "w") as f:
                json.dump(list(self._processed_hashes), f)
        except Exception as e:
            logger.warning(f"Konnte Hash-Datei nicht speichern: {e}")

    def on_created(self, event: FileCreatedEvent) -> None:
        """Wird aufgerufen wenn eine neue Datei erstellt wird."""
        if event.is_directory:
            return

        file_path = Path(event.src_path)

        # Nur PDF-Dateien verarbeiten
        if file_path.suffix.lower() != ".pdf":
            return

        # Kurze Verzögerung, damit Datei vollständig geschrieben wird
        time.sleep(0.5)

        logger.info(f"Neue PDF erkannt: {file_path.name}")
        self._process_pdf(file_path)

    def _process_pdf(self, file_path: Path) -> None:
        """
        Verarbeitet eine neu erkannte PDF-Datei.

        1. Validierung
        2. Hash-Berechnung (Duplicate-Erkennung)
        3. Verschieben in Processing-Ordner
        4. Callback auslösen
        """
        try:
            # Validierung
            validate_pdf_file(file_path)

            # Hash für Duplicate-Erkennung
            file_hash = calculate_file_hash(file_path)

            if file_hash in self._processed_hashes:
                logger.warning(f"Duplikat erkannt, überspringe: {file_path.name}")
                # Duplikat in Error-Ordner verschieben
                self._handle_duplicate(file_path, file_hash)
                return

            # Process-ID generieren
            process_id = uuid.uuid4()

            # In Processing-Ordner verschieben
            new_path = move_file_to_processing(file_path, process_id)

            # Metadaten schreiben
            self._write_metadata(process_id, file_path.name, file_hash)

            # Hash als verarbeitet markieren
            self._processed_hashes.add(file_hash)
            self._save_processed_hashes()

            logger.info(f"PDF bereit für Verarbeitung: {process_id} ({file_path.name})")

            # Callback auslösen falls definiert
            if self.on_pdf_detected:
                self.on_pdf_detected(new_path, process_id, file_hash)

        except Exception as e:
            logger.error(f"Fehler bei PDF-Verarbeitung {file_path.name}: {e}")

    def _handle_duplicate(self, file_path: Path, file_hash: str) -> None:
        """Verschiebt Duplikat in Error-Ordner."""
        from app.file_utils import get_error_folder
        from datetime import datetime

        error_folder = get_error_folder(f"duplicate_{file_path.name}")
        dest = error_folder / "original.pdf"
        file_path.rename(dest)

        error_log = error_folder / "error.log"
        with open(error_log, "w", encoding="utf-8") as f:
            f.write(f"Fehlerzeitpunkt: {datetime.now().isoformat()}\n")
            f.write(f"Fehler: Duplikat erkannt\n")
            f.write(f"Datei-Hash: {file_hash}\n")

    def _write_metadata(
        self, process_id: uuid.UUID, original_filename: str, file_hash: str
    ) -> None:
        """Schreibt Metadaten für die Verarbeitung."""
        metadata = {
            "process_id": str(process_id),
            "original_filename": original_filename,
            "file_hash": file_hash,
            "detected_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        }

        metadata_path = get_processing_folder(process_id) / "metadata.json"
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)


class FileWatcher:
    """
    Hauptklasse für die Dateiüberwachung.
    """

    def __init__(
        self,
        on_pdf_detected: Optional[Callable[[Path, uuid.UUID, str], None]] = None,
    ):
        self.observer = Observer()
        self.handler = PDFFileHandler(on_pdf_detected=on_pdf_detected)

    def start(self) -> None:
        """Startet die Überwachung des Inbox-Ordners."""
        self.observer.schedule(
            self.handler,
            str(settings.inbox_path),
            recursive=False,
        )
        self.observer.start()
        logger.info(f"Dateiüberwachung gestartet: {settings.inbox_path}")

        # Existierende PDFs beim Start verarbeiten
        self._process_existing_files()

    def stop(self) -> None:
        """Stoppt die Überwachung."""
        self.observer.stop()
        self.observer.join()
        logger.info("Dateiüberwachung gestoppt")

    def _process_existing_files(self) -> None:
        """Verarbeitet bereits existierende PDFs im Inbox-Ordner."""
        existing_pdfs = list(settings.inbox_path.glob("*.pdf"))
        if existing_pdfs:
            logger.info(f"{len(existing_pdfs)} existierende PDF(s) im Inbox-Ordner gefunden")
            for pdf_path in existing_pdfs:
                logger.info(f"Verarbeite existierende PDF: {pdf_path.name}")
                self.handler._process_pdf(pdf_path)


# Globale Instanz
_watcher: Optional[FileWatcher] = None


def start_file_watcher(
    on_pdf_detected: Optional[Callable[[Path, uuid.UUID, str], None]] = None
) -> FileWatcher:
    """
    Startet den globalen File-Watcher.

    Args:
        on_pdf_detected: Callback für neue PDFs

    Returns:
        FileWatcher Instanz
    """
    global _watcher
    if _watcher is None:
        _watcher = FileWatcher(on_pdf_detected=on_pdf_detected)
        _watcher.start()
    return _watcher


def stop_file_watcher() -> None:
    """Stoppt den globalen File-Watcher."""
    global _watcher
    if _watcher:
        _watcher.stop()
        _watcher = None
