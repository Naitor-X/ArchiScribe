from fastapi import FastAPI
from app.config import settings
from app.exceptions import ArchiScribeException, archiscribe_exception_handler
from app.file_utils import ensure_directories
from app.file_watcher import start_file_watcher, stop_file_watcher
from app.logger import logger

app = FastAPI(
    title="ArchiScribe API",
    description="KI-gestützte Verarbeitung von Grundlagenformularen für Architekturbüros",
    version="0.1.0",
)

app.add_exception_handler(ArchiScribeException, archiscribe_exception_handler)


@app.on_event("startup")
async def startup():
    # Ordnerstruktur sicherstellen
    ensure_directories()
    # Dateiüberwachung starten
    start_file_watcher(on_pdf_detected=handle_new_pdf)
    logger.info(f"ArchiScribe startet (Umgebung: {settings.app_env})")


@app.on_event("shutdown")
async def shutdown():
    stop_file_watcher()
    logger.info("ArchiScribe wird beendet")


def handle_new_pdf(file_path, process_id: str, file_hash: str) -> None:
    """
    Callback für neue PDF-Dateien.

    Wird vom FileWatcher aufgerufen wenn eine neue PDF erkannt wird.
    Hier wird später die eigentliche Verarbeitungs-Pipeline getriggert.
    """
    logger.info(f"PDF bereit für Pipeline: process_id={process_id}, hash={file_hash[:8]}...")
    # TODO: Verarbeitungs-Pipeline triggern (wird in 1.7 implementiert)


@app.get("/health", tags=["System"])
async def health_check():
    """Gibt den aktuellen Status der Anwendung zurück."""
    return {
        "status": "ok",
        "version": "0.1.0",
        "umgebung": settings.app_env,
    }
