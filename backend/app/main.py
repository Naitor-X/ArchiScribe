"""
ArchiScribe Backend - Hauptanwendung.

FastAPI-App mit:
- File-Watcher für PDF-Überwachung
- Processing-Pipeline für automatisierte KI-Extraktion
- API-Endpunkte für Status-Abfragen und manuelle Re-Trigger
- API-Key-Authentifizierung für Frontend-Integration
"""

import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.config import settings
from app.database import init_db_pool, close_db_pool
from app.exceptions import ArchiScribeException, archiscribe_exception_handler
from app.file_utils import ensure_directories
from app.file_watcher import start_file_watcher, stop_file_watcher
from app.logger import logger
from app.middleware.auth import APIKeyMiddleware
from app.middleware.error_handler import (
    APIError,
    api_error_handler,
    generic_exception_handler,
    http_exception_handler,
    pydantic_validation_handler,
)
from app.middleware.request_logging import RequestLoggingMiddleware
from app.processing import (
    ProcessingJob,
    ProcessingResult,
    ProcessingStatus,
    enqueue_pdf,
    get_pipeline,
    get_queue,
    init_processing,
    shutdown_processing,
)


@asynccontextmanager
async def lifespan(app):
    """FastAPI Lifespan-Context-Manager."""
    # === Startup ===
    logger.info(f"ArchiScribe startet (Umgebung: {settings.app_env})")

    # Datenbank-Pool initialisieren
    await init_db_pool()
    logger.info("Datenbank-Pool initialisiert")

    # Ordnerstruktur sicherstellen
    ensure_directories()

    # Processing-Infrastruktur initialisieren
    await init_processing(
        max_concurrent=settings.max_concurrent_processing,
        on_job_complete=handle_job_complete,
    )

    # Test-API-Key für Development sicherstellen
    if settings.app_env == "development":
        from app.services.api_keys import ensure_test_api_key

        test_key = await ensure_test_api_key()
        logger.info(f"Test-API-Key bereit: {test_key[:20]}...")

    # Dateiüberwachung starten
    start_file_watcher(on_pdf_detected=handle_new_pdf)

    logger.info("ArchiScribe bereit")

    yield

    # === Shutdown ===
    logger.info("ArchiScribe wird beendet")

    stop_file_watcher()
    await shutdown_processing()
    await close_db_pool()

    logger.info("ArchiScribe beendet")


app = FastAPI(
    title="ArchiScribe API",
    description="KI-gestützte Verarbeitung von Grundlagenformularen für Architekturbüros",
    version="0.3.0",
    lifespan=lifespan,
)

# === Exception Handler ===
app.add_exception_handler(ArchiScribeException, archiscribe_exception_handler)
app.add_exception_handler(APIError, api_error_handler)
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

# Pydantic Validation Error Handler
from pydantic import ValidationError as PydanticValidationError
app.add_exception_handler(PydanticValidationError, pydantic_validation_handler)

# === Middleware ===
# Request-Logging (zuerst, damit alle Requests geloggt werden)
app.add_middleware(RequestLoggingMiddleware)

# API-Key-Authentifizierung
app.add_middleware(APIKeyMiddleware)


# === Callbacks ===


def handle_new_pdf(file_path: Path, process_id: uuid.UUID, file_hash: str) -> None:
    """
    Callback für neue PDF-Dateien vom File-Watcher.

    Wird synchron aufgerufen, daher erstellen wir einen async Task.
    """
    import asyncio

    # Original-Dateiname aus Metadaten lesen
    original_filename = file_path.name
    metadata_path = file_path.parent / "metadata.json"
    if metadata_path.exists():
        import json

        try:
            with open(metadata_path, "r") as f:
                metadata = json.load(f)
                original_filename = metadata.get("original_filename", file_path.name)
        except Exception:
            pass

    logger.info(f"Neue PDF erkannt: {original_filename} (process_id={process_id})")

    # Async Task erstellen für Non-Blocking
    asyncio.create_task(
        enqueue_pdf(
            process_id=process_id,
            pdf_path=file_path,
            file_hash=file_hash,
            original_filename=original_filename,
        )
    )


def handle_job_complete(result: ProcessingResult) -> None:
    """Callback wenn ein Job abgeschlossen ist."""
    if result.success:
        logger.info(
            f"Job {result.job_id} erfolgreich abgeschlossen. "
            f"Projekt: {result.project_id}"
        )
    else:
        logger.error(
            f"Job {result.job_id} fehlgeschlagen: {result.error_message}"
        )


# === API-Endpunkte ===


@app.get("/health", tags=["System"])
async def health_check() -> dict[str, Any]:
    """Gibt den aktuellen Status der Anwendung zurück."""
    queue = get_queue()

    return {
        "status": "ok",
        "version": "0.3.0",
        "umgebung": settings.app_env,
        "queue": {
            "active_jobs": len(queue._active_jobs),
            "queued_jobs": queue._queue.qsize(),
            "completed_jobs": len(queue._completed_jobs),
            "max_concurrent": queue.max_concurrent,
        },
    }


# === Tenant-Endpunkte ===


class TenantInfoResponse(BaseModel):
    """Response-Modell für Tenant-Info."""

    tenant_id: str
    key_name: str | None = None


@app.get("/api/v1/tenants/me", response_model=TenantInfoResponse, tags=["Tenant"])
async def get_tenant_info() -> TenantInfoResponse:
    """
    Gibt Informationen zum aktuellen Tenant zurück.

    Erfordert authentifizierten API-Key.
    """
    from app.middleware.auth import get_current_tenant

    tenant = get_current_tenant()
    if not tenant:
        raise HTTPException(
            status_code=401,
            detail="Nicht authentifiziert",
        )

    return TenantInfoResponse(
        tenant_id=str(tenant["tenant_id"]),
        key_name=tenant.get("key_name"),
    )


@app.get("/api/v1/auth/test", tags=["Auth"])
async def test_auth() -> dict[str, Any]:
    """
    Testet die API-Key-Authentifizierung.

    Gibt Tenant-Informationen zurück, wenn der API-Key gültig ist.
    """
    from app.middleware.auth import get_current_tenant

    tenant = get_current_tenant()
    if not tenant:
        raise HTTPException(
            status_code=401,
            detail="Nicht authentifiziert",
        )

    return {
        "authenticated": True,
        "tenant_id": str(tenant["tenant_id"]),
        "key_id": str(tenant.get("key_id")),
        "key_name": tenant.get("key_name"),
    }


# === Response Models ===


class JobStatusResponse(BaseModel):
    """Response-Modell für Job-Status."""

    job_id: str
    process_id: str
    original_filename: str
    status: str
    created_at: str
    started_at: str | None = None
    completed_at: str | None = None
    project_id: str | None = None
    error_message: str | None = None
    warnings: list[str] = []


class QueueStatsResponse(BaseModel):
    """Response-Modell für Queue-Statistiken."""

    active_jobs: int
    queued_jobs: int
    completed_jobs: int
    max_concurrent: int
    recent_jobs: list[dict[str, Any]]


# === Job-Management Endpunkte ===


@app.get("/queue/stats", response_model=QueueStatsResponse, tags=["Queue"])
async def get_queue_stats() -> QueueStatsResponse:
    """Gibt Statistiken zur Processing-Queue zurück."""
    queue = get_queue()

    # Letzte 10 abgeschlossene Jobs
    recent_jobs = []
    for job_id, result in list(queue._completed_jobs.items())[-10:]:
        recent_jobs.append({
            "job_id": str(result.job_id),
            "success": result.success,
            "project_id": str(result.project_id) if result.project_id else None,
            "error": result.error_message,
            "warnings_count": len(result.warnings),
        })

    return QueueStatsResponse(
        active_jobs=len(queue._active_jobs),
        queued_jobs=queue._queue.qsize(),
        completed_jobs=len(queue._completed_jobs),
        max_concurrent=queue.max_concurrent,
        recent_jobs=recent_jobs,
    )


@app.get("/jobs/{job_id}", response_model=JobStatusResponse, tags=["Jobs"])
async def get_job_status(job_id: str) -> JobStatusResponse:
    """
    Gibt den Status eines Jobs zurück.

    Prüft zuerst aktive Jobs, dann abgeschlossene Jobs.
    """
    job_uuid = uuid.UUID(job_id)
    queue = get_queue()

    # In aktiven Jobs suchen
    job = queue.get_job_status(job_uuid)
    if job:
        return JobStatusResponse(
            job_id=str(job.job_id),
            process_id=str(job.process_id),
            original_filename=job.original_filename,
            status=job.status.value,
            created_at=job.created_at.isoformat(),
            started_at=job.started_at.isoformat() if job.started_at else None,
            completed_at=job.completed_at.isoformat() if job.completed_at else None,
            project_id=str(job.project_id) if job.project_id else None,
            error_message=job.error_message,
            warnings=job.warnings,
        )

    # In abgeschlossenen Jobs suchen
    result = queue.get_result(job_uuid)
    if result:
        return JobStatusResponse(
            job_id=str(result.job_id),
            process_id="",  # Nicht mehr verfügbar nach Abschluss
            original_filename="",  # Nicht mehr verfügbar nach Abschluss
            status="completed" if result.success else "failed",
            created_at="",  # Nicht mehr verfügbar
            started_at=None,
            completed_at=None,
            project_id=str(result.project_id) if result.project_id else None,
            error_message=result.error_message,
            warnings=result.warnings,
        )

    raise HTTPException(status_code=404, detail=f"Job {job_id} nicht gefunden")


@app.get("/jobs", response_model=list[JobStatusResponse], tags=["Jobs"])
async def list_active_jobs() -> list[JobStatusResponse]:
    """Listet alle aktuell aktiven Jobs auf."""
    queue = get_queue()
    jobs = []

    for job in queue._active_jobs.values():
        jobs.append(
            JobStatusResponse(
                job_id=str(job.job_id),
                process_id=str(job.process_id),
                original_filename=job.original_filename,
                status=job.status.value,
                created_at=job.created_at.isoformat(),
                started_at=job.started_at.isoformat() if job.started_at else None,
                completed_at=job.completed_at.isoformat() if job.completed_at else None,
                project_id=str(job.project_id) if job.project_id else None,
                error_message=job.error_message,
                warnings=job.warnings,
            )
        )

    return jobs


# === Manuelle Re-Trigger Endpunkte ===


class ReTriggerRequest(BaseModel):
    """Request für manuellen Re-Trigger."""

    file_path: str
    tenant_id: str | None = None


@app.post("/jobs/retrigger", response_model=JobStatusResponse, tags=["Jobs"])
async def retrigger_processing(request: ReTriggerRequest) -> JobStatusResponse:
    """
    Löst eine manuelle Neuverarbeitung aus.

    Nützlich für:
    - Fehlgeschlagene Jobs erneut versuchen
    - Neue PDFs ohne File-Watcher verarbeiten

    Args:
        request: file_path (absolut oder relativ zu /files/inbox/)

    Returns:
        Der erstellte Job
    """
    # Pfad auflösen
    file_path = Path(request.file_path)

    if not file_path.is_absolute():
        # Relativer Pfad - in inbox suchen
        file_path = settings.inbox_path / request.file_path

    if not file_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Datei nicht gefunden: {request.file_path}",
        )

    # Validierung
    if file_path.suffix.lower() != ".pdf":
        raise HTTPException(
            status_code=400,
            detail="Nur PDF-Dateien können verarbeitet werden",
        )

    # Hash berechnen
    from app.file_utils import calculate_file_hash, get_processing_folder, move_file_to_processing

    file_hash = calculate_file_hash(file_path)

    # In Processing-Ordner verschieben
    process_id = uuid.uuid4()
    new_path = move_file_to_processing(file_path, process_id)

    # Job erstellen und enqueuen
    job_id = await enqueue_pdf(
        process_id=process_id,
        pdf_path=new_path,
        file_hash=file_hash,
        original_filename=file_path.name,
    )

    # Job-Status zurückgeben
    queue = get_queue()
    job = queue.get_job_status(job_id)

    if not job:
        raise HTTPException(
            status_code=500,
            detail="Job konnte nicht erstellt werden",
        )

    return JobStatusResponse(
        job_id=str(job.job_id),
        process_id=str(job.process_id),
        original_filename=job.original_filename,
        status=job.status.value,
        created_at=job.created_at.isoformat(),
        started_at=job.started_at.isoformat() if job.started_at else None,
        completed_at=job.completed_at.isoformat() if job.completed_at else None,
        project_id=str(job.project_id) if job.project_id else None,
        error_message=job.error_message,
        warnings=job.warnings,
    )


# === Projekt-Endpunkte ===


@app.get("/projects/{project_id}", tags=["Projekte"])
async def get_project(project_id: str) -> dict[str, Any]:
    """
    Lädt ein Projekt mit allen Details.

    Enthält:
    - Projektdaten
    - Raumprogramm
    - Neueste KI-Extraktion
    """
    from app.database import get_project_by_id

    project_uuid = uuid.UUID(project_id)
    tenant_uuid = uuid.UUID(settings.test_tenant_id)

    project = await get_project_by_id(project_uuid, tenant_uuid)

    if not project:
        raise HTTPException(status_code=404, detail=f"Projekt {project_id} nicht gefunden")

    # UUIDs zu Strings konvertieren für JSON-Serialisierung
    result = {}
    for key, value in project.items():
        if isinstance(value, uuid.UUID):
            result[key] = str(value)
        else:
            result[key] = value

    return result
