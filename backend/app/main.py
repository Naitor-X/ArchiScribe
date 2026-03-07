from fastapi import FastAPI
from app.config import settings
from app.exceptions import ArchiScribeException, archiscribe_exception_handler
from app.logger import logger

app = FastAPI(
    title="ArchiScribe API",
    description="KI-gestützte Verarbeitung von Grundlagenformularen für Architekturbüros",
    version="0.1.0",
)

app.add_exception_handler(ArchiScribeException, archiscribe_exception_handler)


@app.on_event("startup")
async def startup():
    logger.info(f"ArchiScribe startet (Umgebung: {settings.app_env})")


@app.on_event("shutdown")
async def shutdown():
    logger.info("ArchiScribe wird beendet")


@app.get("/health", tags=["System"])
async def health_check():
    """Gibt den aktuellen Status der Anwendung zurück."""
    return {
        "status": "ok",
        "version": "0.1.0",
        "umgebung": settings.app_env,
    }
