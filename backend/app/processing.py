"""
Workflow-Orchestrierung für ArchiScribe.

Verbindet alle Komponenten zu einer automatisierten Pipeline:
- PDF-Konvertierung
- KI-Extraktion
- Daten-Mapping
- Datenbank-Speicherung
- Archivierung

Features:
- Async Processing-Queue für parallele Verarbeitung
- Status-Updates während der Verarbeitung
- Umfassende Fehlerbehandlung
- Manuelle Re-Trigger-Möglichkeit
"""

import asyncio
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Optional

from app.config import settings
from app.database import (
    DatabaseError,
    close_db_pool,
    ensure_test_tenant_exists,
    get_connection,
    init_db_pool,
    save_project,
    update_project_status,
)
from app.exceptions import ArchiScribeException
from app.file_utils import (
    cleanup_processing_folder,
    get_processing_folder,
    move_to_archive,
    move_to_error,
)
from app.logger import logger
from app.mapping import MappedProject, ValidationResult, map_extraction_to_project
from app.openrouter_client import extract_form_data
from app.pdf_converter import konvertiere_pdf_fuer_vision
from app.schemas.extraction import ExtractionResult


class ProcessingStatus(str, Enum):
    """Status einer Verarbeitung."""

    QUEUED = "queued"
    CONVERTING = "converting"
    EXTRACTING = "extracting"
    MAPPING = "mapping"
    SAVING = "saving"
    ARCHIVING = "archiving"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class ProcessingJob:
    """Repräsentiert einen Verarbeitungsjob."""

    job_id: uuid.UUID
    process_id: uuid.UUID
    pdf_path: Path
    file_hash: str
    original_filename: str
    status: ProcessingStatus = ProcessingStatus.QUEUED
    created_at: datetime = field(default_factory=datetime.now)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error_message: str | None = None
    project_id: uuid.UUID | None = None
    warnings: list[str] = field(default_factory=list)

    # Callbacks für Status-Updates
    on_status_change: Optional[Callable[["ProcessingJob"], None]] = None

    def update_status(self, new_status: ProcessingStatus) -> None:
        """Aktualisiert den Status und löst Callback aus."""
        old_status = self.status
        self.status = new_status

        if new_status == ProcessingStatus.CONVERTING:
            self.started_at = datetime.now()
        elif new_status in (ProcessingStatus.COMPLETED, ProcessingStatus.FAILED):
            self.completed_at = datetime.now()

        logger.info(f"Job {self.job_id}: {old_status.value} → {new_status.value}")

        if self.on_status_change:
            self.on_status_change(self)


@dataclass
class ProcessingResult:
    """Ergebnis einer abgeschlossenen Verarbeitung."""

    success: bool
    job_id: uuid.UUID
    project_id: uuid.UUID | None = None
    tenant_id: uuid.UUID | None = None
    error_message: str | None = None
    warnings: list[str] = field(default_factory=list)
    extraction_result: ExtractionResult | None = None
    mapped_project: MappedProject | None = None


class ProcessingQueue:
    """
    Async Queue für parallele PDF-Verarbeitung.

    Verwaltet mehrere gleichzeitige Verarbeitungen und limitiert
    die Anzahl paralleler Jobs.
    """

    def __init__(self, max_concurrent: int = 3):
        self.max_concurrent = max_concurrent
        self._queue: asyncio.Queue[ProcessingJob] = asyncio.Queue()
        self._active_jobs: dict[uuid.UUID, ProcessingJob] = {}
        self._completed_jobs: dict[uuid.UUID, ProcessingResult] = {}
        self._workers: list[asyncio.Task] = []
        self._running = False
        self._pipeline: "ProcessingPipeline | None" = None

    def set_pipeline(self, pipeline: "ProcessingPipeline") -> None:
        """Setzt die Pipeline-Instanz für die Worker."""
        self._pipeline = pipeline

    async def start(self) -> None:
        """Startet die Worker-Tasks."""
        if self._running:
            return

        self._running = True
        for i in range(self.max_concurrent):
            worker = asyncio.create_task(self._worker(i))
            self._workers.append(worker)

        logger.info(
            f"Processing-Queue gestartet mit {self.max_concurrent} Workern"
        )

    async def stop(self) -> None:
        """Stoppt alle Worker-Tasks."""
        self._running = False

        # Queue leeren um Worker zu beenden
        for _ in range(self.max_concurrent):
            await self._queue.put(None)  # type: ignore

        # Warten bis alle Worker beendet sind
        if self._workers:
            await asyncio.gather(*self._workers, return_exceptions=True)
            self._workers.clear()

        logger.info("Processing-Queue gestoppt")

    async def enqueue(self, job: ProcessingJob) -> uuid.UUID:
        """
        Fügt einen Job zur Warteschlange hinzu.

        Returns:
            Die Job-ID für Tracking
        """
        await self._queue.put(job)
        logger.info(f"Job {job.job_id} zur Queue hinzugefügt (Position: {self._queue.qsize()})")
        return job.job_id

    def get_job_status(self, job_id: uuid.UUID) -> ProcessingJob | None:
        """Gibt den Status eines aktiven Jobs zurück."""
        return self._active_jobs.get(job_id)

    def get_result(self, job_id: uuid.UUID) -> ProcessingResult | None:
        """Gibt das Ergebnis eines abgeschlossenen Jobs zurück."""
        return self._completed_jobs.get(job_id)

    async def _worker(self, worker_id: int) -> None:
        """Worker-Task der Jobs aus der Queue verarbeitet."""
        logger.debug(f"Worker {worker_id} gestartet")

        while self._running:
            try:
                job = await asyncio.wait_for(self._queue.get(), timeout=1.0)
            except asyncio.TimeoutError:
                continue

            if job is None:
                break

            logger.info(f"Worker {worker_id} verarbeitet Job {job.job_id}")
            self._active_jobs[job.job_id] = job

            try:
                result = await self._process_job(job)
                self._completed_jobs[job.job_id] = result
            except Exception as e:
                logger.error(f"Worker {worker_id} Fehler bei Job {job.job_id}: {e}")
                self._completed_jobs[job.job_id] = ProcessingResult(
                    success=False,
                    job_id=job.job_id,
                    error_message=str(e),
                )
            finally:
                del self._active_jobs[job.job_id]

        logger.debug(f"Worker {worker_id} beendet")

    async def _process_job(self, job: ProcessingJob) -> ProcessingResult:
        """Verarbeitet einen Job mit der Pipeline."""
        if self._pipeline is None:
            raise RuntimeError("Pipeline nicht initialisiert")

        return await self._pipeline.process_pdf(job)


class ProcessingPipeline:
    """
    Haupt-Pipeline für die PDF-Verarbeitung.

    Orchestriert alle Schritte:
    1. PDF-Konvertierung zu Bildern
    2. KI-Extraktion via OpenRouter
    3. Daten-Mapping & Validierung
    4. Datenbank-Speicherung
    5. Archivierung
    """

    def __init__(
        self,
        tenant_id: uuid.UUID | None = None,
        on_job_complete: Optional[Callable[[ProcessingResult], None]] = None,
    ):
        self.tenant_id = tenant_id or uuid.UUID(settings.test_tenant_id)
        self.on_job_complete = on_job_complete

    async def process_pdf(self, job: ProcessingJob) -> ProcessingResult:
        """
        Führt die komplette Verarbeitungspipeline aus.

        Args:
            job: Der zu verarbeitende Job

        Returns:
            ProcessingResult mit Ergebnis oder Fehler
        """
        result = ProcessingResult(
            success=False,
            job_id=job.job_id,
        )

        processing_folder = get_processing_folder(job.process_id)

        try:
            # === Schritt 1: PDF-Konvertierung ===
            job.update_status(ProcessingStatus.CONVERTING)

            konvertierung = konvertiere_pdf_fuer_vision(
                pdf_pfad=job.pdf_path,
                output_ordner=processing_folder,
                mit_base64=True,
            )

            logger.info(
                f"PDF konvertiert: {konvertierung.seiten_anzahl} Seiten, "
                f"{len(konvertierung.base64_bilder)} Base64-Bilder"
            )

            # === Schritt 2: KI-Extraktion ===
            job.update_status(ProcessingStatus.EXTRACTING)

            extraction_result = await extract_form_data(konvertierung.base64_bilder)
            result.extraction_result = extraction_result

            logger.info(
                f"KI-Extraktion erfolgreich: "
                f"{len(extraction_result.rooms)} Räume extrahiert"
            )

            # === Schritt 3: Daten-Mapping ===
            job.update_status(ProcessingStatus.MAPPING)

            # Archiv-Pfade vorbereiten (werden später gesetzt)
            archive_base = str(settings.archive_path / str(self.tenant_id))

            mapped_project, validation = map_extraction_to_project(
                extraction_result,
                pdf_path=f"{archive_base}/{{project_id}}/original.pdf",
                page_paths=[],  # Wird nach Archivierung aktualisiert
            )

            result.mapped_project = mapped_project
            result.warnings = validation.warnings
            job.warnings = validation.warnings

            if validation.warnings:
                logger.warning(f"Validierungswarnungen: {len(validation.warnings)}")

            # === Schritt 4: Datenbank-Speicherung ===
            job.update_status(ProcessingStatus.SAVING)

            # Rohes JSON für Debugging speichern
            raw_json = extraction_result.model_dump()

            project_id = await save_project(
                project=mapped_project,
                tenant_id=self.tenant_id,
                raw_json=raw_json,
            )

            result.project_id = project_id
            result.tenant_id = self.tenant_id
            job.project_id = project_id

            logger.info(f"Projekt in DB gespeichert: {project_id}")

            # === Schritt 5: Archivierung ===
            job.update_status(ProcessingStatus.ARCHIVING)

            # Dateien ins Archiv verschieben
            archive_folder = move_to_archive(
                processing_folder=processing_folder,
                tenant_id=self.tenant_id,
                project_id=project_id,
                png_files=konvertierung.bild_pfade,
            )

            # PDF-Pfad und PNG-Pfade in DB aktualisieren
            await self._update_file_paths(project_id, archive_folder, konvertierung.bild_pfade)

            logger.info(f"Dateien archiviert: {archive_folder}")

            # Processing-Ordner bereinigen
            cleanup_processing_folder(job.process_id)

            # === Abgeschlossen ===
            job.update_status(ProcessingStatus.COMPLETED)
            result.success = True

            logger.info(
                f"Pipeline erfolgreich abgeschlossen: Job {job.job_id}, "
                f"Projekt {project_id}"
            )

        except ArchiScribeException as e:
            # Bekannter Fehler
            job.error_message = str(e)
            result.error_message = str(e)
            await self._handle_error(job, processing_folder, str(e))

        except Exception as e:
            # Unerwarteter Fehler
            error_msg = f"Unerwarteter Fehler: {e}"
            logger.exception(f"Pipeline-Fehler bei Job {job.job_id}")
            job.error_message = error_msg
            result.error_message = error_msg
            await self._handle_error(job, processing_folder, error_msg)

        # Callback auslösen
        if self.on_job_complete:
            self.on_job_complete(result)

        return result

    async def _update_file_paths(
        self,
        project_id: uuid.UUID,
        archive_folder: Path,
        png_files: list[Path],
    ) -> None:
        """Aktualisiert die Dateipfade in der Datenbank nach der Archivierung."""
        # Archivierte Dateien finden
        archived_files = list(archive_folder.glob("*"))
        pdf_path = None
        page_paths = []

        for f in archived_files:
            if f.suffix == ".pdf":
                pdf_path = str(f)
            elif f.suffix == ".png":
                page_paths.append(str(f))

        # In DB aktualisieren
        async with get_connection() as conn:
            await conn.execute(
                """
                UPDATE projects
                SET pdf_path = $1, page_paths = $2
                WHERE id = $3
                """,
                pdf_path,
                json.dumps(sorted(page_paths)),
                project_id,
            )

    async def _handle_error(
        self,
        job: ProcessingJob,
        processing_folder: Path,
        error_message: str,
    ) -> None:
        """Behandelt Fehler während der Verarbeitung."""
        job.update_status(ProcessingStatus.FAILED)

        # Dateien in Error-Ordner verschieben
        if processing_folder.exists():
            move_to_error(processing_folder, error_message)

        # Processing-Ordner bereinigen
        cleanup_processing_folder(job.process_id)


# === Globale Instanzen ===

_queue: ProcessingQueue | None = None
_pipeline: ProcessingPipeline | None = None


def get_queue() -> ProcessingQueue:
    """Gibt die globale Processing-Queue zurück."""
    global _queue
    if _queue is None:
        raise RuntimeError("Processing-Queue nicht initialisiert")
    return _queue


def get_pipeline() -> ProcessingPipeline:
    """Gibt die globale Pipeline zurück."""
    global _pipeline
    if _pipeline is None:
        raise RuntimeError("Pipeline nicht initialisiert")
    return _pipeline


async def init_processing(
    tenant_id: uuid.UUID | None = None,
    max_concurrent: int = 3,
    on_job_complete: Optional[Callable[[ProcessingResult], None]] = None,
) -> ProcessingQueue:
    """
    Initialisiert die Processing-Infrastruktur.

    Args:
        tenant_id: Mandanten-ID (optional, Standard: Test-Tenant)
        max_concurrent: Maximale parallele Verarbeitungen
        on_job_complete: Callback bei Job-Abschluss

    Returns:
        Die Processing-Queue
    """
    global _queue, _pipeline

    # DB-Pool initialisieren
    await init_db_pool()

    # Test-Tenant sicherstellen
    async with get_connection() as conn:
        await ensure_test_tenant_exists(conn)

    # Pipeline erstellen
    _pipeline = ProcessingPipeline(
        tenant_id=tenant_id,
        on_job_complete=on_job_complete,
    )

    # Queue erstellen und starten
    _queue = ProcessingQueue(max_concurrent=max_concurrent)
    _queue.set_pipeline(_pipeline)
    await _queue.start()

    logger.info("Processing-Infrastruktur initialisiert")
    return _queue


async def shutdown_processing() -> None:
    """Fährt die Processing-Infrastruktur herunter."""
    global _queue, _pipeline

    if _queue:
        await _queue.stop()
        _queue = None

    await close_db_pool()

    _pipeline = None
    logger.info("Processing-Infrastruktur heruntergefahren")


def create_job(
    process_id: uuid.UUID,
    pdf_path: Path,
    file_hash: str,
    original_filename: str,
    on_status_change: Optional[Callable[[ProcessingJob], None]] = None,
) -> ProcessingJob:
    """
    Erstellt einen neuen Processing-Job.

    Args:
        process_id: Die Prozess-ID vom File-Watcher
        pdf_path: Pfad zur PDF im Processing-Ordner
        file_hash: Datei-Hash für Duplicate-Erkennung
        original_filename: Ursprünglicher Dateiname
        on_status_change: Optionaler Callback für Status-Updates

    Returns:
        Den erstellten Job
    """
    return ProcessingJob(
        job_id=uuid.uuid4(),
        process_id=process_id,
        pdf_path=pdf_path,
        file_hash=file_hash,
        original_filename=original_filename,
        on_status_change=on_status_change,
    )


async def enqueue_pdf(
    process_id: uuid.UUID,
    pdf_path: Path,
    file_hash: str,
    original_filename: str,
) -> uuid.UUID:
    """
    Convenience-Funktion: Erstellt und enqueued einen Job.

    Returns:
        Die Job-ID für Tracking
    """
    job = create_job(process_id, pdf_path, file_hash, original_filename)
    queue = get_queue()
    return await queue.enqueue(job)
