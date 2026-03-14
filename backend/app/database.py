"""
Datenbank-Integration für ArchiScribe.

Stellt async PostgreSQL-Funktionen bereit für:
- Connection-Pool-Management
- Projekt-Speicherung mit Transaktionssicherheit
- AI-Extraktion-Speicherung
- Raumprogramm-Eintragung
"""

import json
import logging
from contextlib import asynccontextmanager
from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

import asyncpg

from app.config import settings
from app.mapping import MappedProject

logger = logging.getLogger(__name__)

# Globaler Connection-Pool
_pool: asyncpg.Pool | None = None


class DatabaseError(Exception):
    """Fehler bei Datenbankoperationen."""
    pass


async def init_db_pool() -> asyncpg.Pool:
    """
    Initialisiert den globalen Connection-Pool.

    Returns:
        Der initialisierte Pool

    Raises:
        DatabaseError: Wenn die Verbindung fehlschlägt
    """
    global _pool

    if _pool is not None:
        return _pool

    try:
        _pool = await asyncpg.create_pool(
            host=settings.postgres_host,
            port=settings.postgres_port,
            database=settings.postgres_db,
            user=settings.postgres_user,
            password=settings.postgres_password,
            min_size=2,
            max_size=10,
            command_timeout=60,
        )
        logger.info(
            f"DB-Pool erstellt: {settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}"
        )
        return _pool
    except Exception as e:
        logger.error(f"DB-Pool-Erstellung fehlgeschlagen: {e}")
        raise DatabaseError(f"DB-Verbindung fehlgeschlagen: {e}")


async def close_db_pool() -> None:
    """Schließt den globalen Connection-Pool."""
    global _pool

    if _pool is not None:
        await _pool.close()
        _pool = None
        logger.info("DB-Pool geschlossen")


def get_pool() -> asyncpg.Pool:
    """
    Gibt den globalen Connection-Pool zurück.

    Raises:
        DatabaseError: Wenn der Pool nicht initialisiert wurde
    """
    if _pool is None:
        raise DatabaseError("DB-Pool nicht initialisiert. Rufe zuerst init_db_pool() auf.")
    return _pool


@asynccontextmanager
async def get_connection():
    """
    Context-Manager für DB-Verbindungen aus dem Pool.

    Yields:
        asyncpg.Connection

    Usage:
        async with get_connection() as conn:
            await conn.execute(...)
    """
    pool = get_pool()
    async with pool.acquire() as conn:
        yield conn


def _prepare_value(value: Any) -> Any:
    """
    Bereitet einen Wert für die DB-Speicherung vor.

    - UUID → str
    - Decimal → float
    - date → date (asyncpg unterstützt dies)
    - None → None
    """
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return value
    return value


async def ensure_test_tenant_exists(conn: asyncpg.Connection) -> UUID:
    """
    Stellt sicher, dass der Test-Tenant existiert.

    Args:
        conn: Datenbankverbindung

    Returns:
        UUID des Test-Tenants
    """
    tenant_id = UUID(settings.test_tenant_id)

    # Prüfen ob Tenant existiert
    exists = await conn.fetchval(
        "SELECT 1 FROM tenants WHERE id = $1",
        tenant_id
    )

    if not exists:
        await conn.execute(
            "INSERT INTO tenants (id, name) VALUES ($1, $2)",
            tenant_id,
            "Test-Mandant"
        )
        logger.info(f"Test-Tenant erstellt: {tenant_id}")

    return tenant_id


async def save_project(
    project: MappedProject,
    tenant_id: UUID | str,
    raw_json: dict[str, Any],
    confidence_scores: dict[str, float] | None = None,
) -> UUID:
    """
    Speichert ein komplettes Projekt mit allen abhängigen Daten.

    Führt alle Operationen in einer Transaktion durch.
    Bei Fehlern wird ein Rollback durchgeführt.

    Args:
        project: Das gemappte Projekt
        tenant_id: UUID des Mandanten
        raw_json: Rohe KI-Extraktion für Debugging
        confidence_scores: Optionale Confidence-Scores pro Feld

    Returns:
        UUID des erstellten Projekts

    Raises:
        DatabaseError: Bei Fehlern während der Speicherung
    """
    if isinstance(tenant_id, str):
        tenant_id = UUID(tenant_id)

    pool = get_pool()

    async with pool.acquire() as conn:
        async with conn.transaction():
            try:
                # 1. Projekt in `projects` einfügen
                project_id = await _insert_project(conn, project, tenant_id)
                logger.info(f"Projekt erstellt: {project_id}")

                # 2. AI-Extraktion in `ai_extractions` speichern
                await _insert_ai_extraction(
                    conn, project_id, raw_json, confidence_scores
                )
                logger.debug(f"AI-Extraktion gespeichert für Projekt {project_id}")

                # 3. Räume in `project_rooms` einfügen
                if project.rooms:
                    await _insert_rooms(conn, project_id, project.rooms)
                    logger.debug(
                        f"{len(project.rooms)} Räume gespeichert für Projekt {project_id}"
                    )

                return project_id

            except Exception as e:
                # Transaction wird automatisch zurückgerollt
                logger.error(f"Fehler beim Speichern des Projekts: {e}")
                raise DatabaseError(f"Projekt-Speicherung fehlgeschlagen: {e}")


async def _insert_project(
    conn: asyncpg.Connection,
    project: MappedProject,
    tenant_id: UUID,
) -> UUID:
    """
    Fügt ein Projekt in die projects-Tabelle ein.

    Args:
        conn: Datenbankverbindung
        project: Die Projektdaten
        tenant_id: Mandanten-ID

    Returns:
        UUID des erstellten Projekts
    """
    # page_paths als JSON für DB
    page_paths_json = json.dumps(project.page_paths) if project.page_paths else None

    row = await conn.fetchrow(
        """
        INSERT INTO projects (
            tenant_id, status_id, pdf_path, page_paths,
            client_name, address, phone, email, date,
            plot_location, plot_size_m2, landowner,
            topography, topography_other, development_plan, access_status,
            project_type, project_type_other, building_type, building_type_other,
            construction_method, heating_type, heating_type_other,
            budget, planned_start, own_contribution, own_contribution_details,
            accessibility, outdoor_area, materiality, notes
        ) VALUES (
            $1, $2, $3, $4,
            $5, $6, $7, $8, $9,
            $10, $11, $12,
            $13, $14, $15, $16,
            $17, $18, $19, $20,
            $21, $22, $23,
            $24, $25, $26, $27,
            $28, $29, $30, $31
        ) RETURNING id
        """,
        tenant_id,
        "raw_extracted",  # Status
        project.pdf_path,
        page_paths_json,
        project.client_name,
        project.address,
        project.phone,
        project.email,
        _prepare_value(project.date),
        project.plot_location,
        _prepare_value(project.plot_size_m2),
        project.landowner,
        project.topography,
        project.topography_other,
        project.development_plan,
        project.access_status,
        project.project_type,
        project.project_type_other,
        project.building_type,
        project.building_type_other,
        project.construction_method,
        project.heating_type,
        project.heating_type_other,
        _prepare_value(project.budget),
        _prepare_value(project.planned_start),
        project.own_contribution,
        project.own_contribution_details,
        project.accessibility,
        project.outdoor_area,
        project.materiality,
        project.notes,
    )

    return row["id"]


async def _insert_ai_extraction(
    conn: asyncpg.Connection,
    project_id: UUID,
    raw_json: dict[str, Any],
    confidence_scores: dict[str, float] | None = None,
) -> UUID:
    """
    Speichert die rohe KI-Extraktion für Debugging.

    Args:
        conn: Datenbankverbindung
        project_id: Projekt-ID
        raw_json: Rohe KI-Daten
        confidence_scores: Optionale Confidence-Scores

    Returns:
        UUID des Extraktions-Eintrags
    """
    confidence_json = json.dumps(confidence_scores) if confidence_scores else None

    row = await conn.fetchrow(
        """
        INSERT INTO ai_extractions (project_id, raw_json, confidence_scores)
        VALUES ($1, $2, $3)
        RETURNING id
        """,
        project_id,
        json.dumps(raw_json),
        confidence_json,
    )

    return row["id"]


async def _insert_rooms(
    conn: asyncpg.Connection,
    project_id: UUID,
    rooms: list[dict[str, Any]],
) -> list[UUID]:
    """
    Fügt Räume in die project_rooms-Tabelle ein.

    Args:
        conn: Datenbankverbindung
        project_id: Projekt-ID
        rooms: Liste der Raum-Dicts

    Returns:
        Liste der erstellten Raum-UUIDs
    """
    room_ids = []

    for room in rooms:
        row = await conn.fetchrow(
            """
            INSERT INTO project_rooms (
                project_id, room_type, quantity, size_m2, special_requirements
            ) VALUES ($1, $2, $3, $4, $5)
            RETURNING id
            """,
            project_id,
            room["room_type"],
            room.get("quantity", 1),
            _prepare_value(room.get("size_m2")),
            room.get("special_requirements"),
        )
        room_ids.append(row["id"])

    return room_ids


async def get_project_by_id(
    project_id: UUID | str,
    tenant_id: UUID | str,
) -> dict[str, Any] | None:
    """
    Lädt ein Projekt mit allen abhängigen Daten.

    Args:
        project_id: Projekt-ID
        tenant_id: Mandanten-ID (für Multi-Tenant-Sicherheit)

    Returns:
        Projekt-Dict mit rooms-Array oder None
    """
    if isinstance(project_id, str):
        project_id = UUID(project_id)
    if isinstance(tenant_id, str):
        tenant_id = UUID(tenant_id)

    async with get_connection() as conn:
        # Projekt laden
        row = await conn.fetchrow(
            """
            SELECT * FROM projects
            WHERE id = $1 AND tenant_id = $2
            """,
            project_id,
            tenant_id,
        )

        if not row:
            return None

        project = dict(row)

        # Räume laden
        rooms = await conn.fetch(
            """
            SELECT id, room_type, quantity, size_m2, special_requirements
            FROM project_rooms
            WHERE project_id = $1
            ORDER BY room_type
            """,
            project_id,
        )
        project["rooms"] = [dict(r) for r in rooms]

        # Neueste AI-Extraktion laden
        extraction = await conn.fetchrow(
            """
            SELECT id, raw_json, confidence_scores, extracted_at
            FROM ai_extractions
            WHERE project_id = $1
            ORDER BY extracted_at DESC
            LIMIT 1
            """,
            project_id,
        )
        project["latest_extraction"] = dict(extraction) if extraction else None

        return project


async def update_project_status(
    project_id: UUID | str,
    tenant_id: UUID | str,
    new_status: str,
    changed_by_user_id: UUID | str | None = None,
) -> bool:
    """
    Aktualisiert den Projektstatus und erstellt einen History-Eintrag.

    Args:
        project_id: Projekt-ID
        tenant_id: Mandanten-ID
        new_status: Neuer Status (raw_extracted, needs_review, verified_by_architect)
        changed_by_user_id: Optional User-ID für Audit-Trail

    Returns:
        True wenn erfolgreich, False wenn Projekt nicht gefunden
    """
    if isinstance(project_id, str):
        project_id = UUID(project_id)
    if isinstance(tenant_id, str):
        tenant_id = UUID(tenant_id)
    if isinstance(changed_by_user_id, str):
        changed_by_user_id = UUID(changed_by_user_id)

    pool = get_pool()

    async with pool.acquire() as conn:
        async with conn.transaction():
            # Alten Status holen
            old_status = await conn.fetchval(
                "SELECT status_id FROM projects WHERE id = $1 AND tenant_id = $2",
                project_id,
                tenant_id,
            )

            if old_status is None:
                return False

            # Status aktualisieren
            await conn.execute(
                "UPDATE projects SET status_id = $1 WHERE id = $2",
                new_status,
                project_id,
            )

            # History-Eintrag erstellen
            changes = {"status_id": {"old": old_status, "new": new_status}}

            await conn.execute(
                """
                INSERT INTO project_history (project_id, changed_by_user_id, changes)
                VALUES ($1, $2, $3)
                """,
                project_id,
                changed_by_user_id,
                json.dumps(changes),
            )

            logger.info(
                f"Projekt {project_id} Status geändert: {old_status} → {new_status}"
            )
            return True


# === API-Funktionen ===


async def list_projects(
    tenant_id: UUID | str,
    status_id: str | None = None,
    search: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[dict[str, Any]], int]:
    """
    Listet Projekte eines Mandanten mit Paginierung und Filterung.

    Args:
        tenant_id: Mandanten-ID
        status_id: Optionaler Status-Filter
        search: Optionaler Suchbegriff (client_name, address)
        page: Seitennummer (1-basiert)
        page_size: Anzahl pro Seite

    Returns:
        Tuple aus (Projekt-Liste, Gesamtanzahl)
    """
    if isinstance(tenant_id, str):
        tenant_id = UUID(tenant_id)

    async with get_connection() as conn:
        # Basis-Query
        base_query = "FROM projects WHERE tenant_id = $1"
        params = [tenant_id]
        param_count = 1

        # Status-Filter
        if status_id:
            param_count += 1
            base_query += f" AND status_id = ${param_count}"
            params.append(status_id)

        # Such-Filter
        if search:
            param_count += 1
            base_query += f" AND (client_name ILIKE ${param_count} OR address ILIKE ${param_count})"
            params.append(f"%{search}%")

        # Gesamtanzahl
        count_query = f"SELECT COUNT(*) {base_query}"
        total = await conn.fetchval(count_query, *params)

        # Projekte laden
        param_count += 1
        offset = (page - 1) * page_size
        data_query = f"""
            SELECT id, tenant_id, status_id, client_name, address, 
                   plot_location, project_type, budget, created_at, updated_at
            {base_query}
            ORDER BY created_at DESC
            LIMIT ${param_count} OFFSET {offset}
        """
        params.append(page_size)

        rows = await conn.fetch(data_query, *params)
        projects = [dict(r) for r in rows]

        return projects, total


async def update_project(
    project_id: UUID | str,
    tenant_id: UUID | str,
    updates: dict[str, Any],
    changed_by_user_id: UUID | str | None = None,
) -> dict[str, Any] | None:
    """
    Aktualisiert ein Projekt mit Audit-Trail.

    Args:
        project_id: Projekt-ID
        tenant_id: Mandanten-ID
        updates: Dictionary mit zu aktualisierenden Feldern
        changed_by_user_id: Optional User-ID für Audit-Trail

    Returns:
        Aktualisiertes Projekt oder None wenn nicht gefunden
    """
    if isinstance(project_id, str):
        project_id = UUID(project_id)
    if isinstance(tenant_id, str):
        tenant_id = UUID(tenant_id)
    if isinstance(changed_by_user_id, str):
        changed_by_user_id = UUID(changed_by_user_id)

    pool = get_pool()

    async with pool.acquire() as conn:
        async with conn.transaction():
            # Altes Projekt laden
            old_project = await conn.fetchrow(
                "SELECT * FROM projects WHERE id = $1 AND tenant_id = $2",
                project_id,
                tenant_id,
            )

            if not old_project:
                return None

            # Changes für Audit-Trail vorbereiten
            changes = {}
            for key, new_value in updates.items():
                old_value = old_project.get(key)
                if old_value != new_value:
                    changes[key] = {"old": old_value, "new": new_value}

            if not changes:
                # Keine Änderungen
                return dict(old_project)

            # Update durchführen
            set_clauses = []
            params = []
            param_count = 0

            for key, value in updates.items():
                param_count += 1
                set_clauses.append(f"{key} = ${param_count}")
                params.append(_prepare_value(value))

            param_count += 1
            params.append(project_id)
            param_count += 1
            params.append(tenant_id)

            update_query = f"""
                UPDATE projects 
                SET {', '.join(set_clauses)}
                WHERE id = ${param_count - 1} AND tenant_id = ${param_count}
                RETURNING *
            """

            updated_row = await conn.fetchrow(update_query, *params)

            # History-Eintrag erstellen
            await conn.execute(
                """
                INSERT INTO project_history (project_id, changed_by_user_id, changes)
                VALUES ($1, $2, $3)
                """,
                project_id,
                changed_by_user_id,
                json.dumps(changes),
            )

            logger.info(f"Projekt {project_id} aktualisiert: {len(changes)} Felder geändert")
            return dict(updated_row)


async def get_project_history(
    project_id: UUID | str,
    tenant_id: UUID | str,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """
    Lädt die Änderungshistorie eines Projekts.

    Args:
        project_id: Projekt-ID
        tenant_id: Mandanten-ID
        limit: Maximale Anzahl Einträge

    Returns:
        Liste der Historien-Einträge
    """
    if isinstance(project_id, str):
        project_id = UUID(project_id)
    if isinstance(tenant_id, str):
        tenant_id = UUID(tenant_id)

    async with get_connection() as conn:
        # Prüfen ob Projekt existiert
        exists = await conn.fetchval(
            "SELECT 1 FROM projects WHERE id = $1 AND tenant_id = $2",
            project_id,
            tenant_id,
        )

        if not exists:
            return []

        rows = await conn.fetch(
            """
            SELECT id, project_id, changed_by_user_id, changed_at, changes
            FROM project_history
            WHERE project_id = $1
            ORDER BY changed_at DESC
            LIMIT $2
            """,
            project_id,
            limit,
        )

        return [dict(r) for r in rows]


async def create_room(
    project_id: UUID | str,
    tenant_id: UUID | str,
    room_data: dict[str, Any],
) -> UUID | None:
    """
    Erstellt einen neuen Raum für ein Projekt.

    Args:
        project_id: Projekt-ID
        tenant_id: Mandanten-ID
        room_data: Raum-Daten

    Returns:
        UUID des erstellten Raums oder None wenn Projekt nicht gefunden
    """
    if isinstance(project_id, str):
        project_id = UUID(project_id)
    if isinstance(tenant_id, str):
        tenant_id = UUID(tenant_id)

    async with get_connection() as conn:
        # Prüfen ob Projekt existiert
        exists = await conn.fetchval(
            "SELECT 1 FROM projects WHERE id = $1 AND tenant_id = $2",
            project_id,
            tenant_id,
        )

        if not exists:
            return None

        row = await conn.fetchrow(
            """
            INSERT INTO project_rooms (
                project_id, room_type, quantity, size_m2, special_requirements
            ) VALUES ($1, $2, $3, $4, $5)
            RETURNING id
            """,
            project_id,
            room_data["room_type"],
            room_data.get("quantity", 1),
            _prepare_value(room_data.get("size_m2")),
            room_data.get("special_requirements"),
        )

        logger.info(f"Raum erstellt: {room_data['room_type']} für Projekt {project_id}")
        return row["id"]


async def update_room(
    room_id: UUID | str,
    project_id: UUID | str,
    tenant_id: UUID | str,
    updates: dict[str, Any],
) -> dict[str, Any] | None:
    """
    Aktualisiert einen Raum.

    Args:
        room_id: Raum-ID
        project_id: Projekt-ID
        tenant_id: Mandanten-ID
        updates: Zu aktualisierende Felder

    Returns:
        Aktualisierter Raum oder None wenn nicht gefunden
    """
    if isinstance(room_id, str):
        room_id = UUID(room_id)
    if isinstance(project_id, str):
        project_id = UUID(project_id)
    if isinstance(tenant_id, str):
        tenant_id = UUID(tenant_id)

    async with get_connection() as conn:
        # Prüfen ob Raum zum Projekt und Tenant gehört
        row = await conn.fetchrow(
            """
            SELECT pr.* FROM project_rooms pr
            JOIN projects p ON pr.project_id = p.id
            WHERE pr.id = $1 AND pr.project_id = $2 AND p.tenant_id = $3
            """,
            room_id,
            project_id,
            tenant_id,
        )

        if not row:
            return None

        # Update durchführen
        set_clauses = []
        params = []
        param_count = 0

        for key, value in updates.items():
            if key in ["room_type", "quantity", "size_m2", "special_requirements"]:
                param_count += 1
                set_clauses.append(f"{key} = ${param_count}")
                params.append(_prepare_value(value))

        if not set_clauses:
            return dict(row)

        param_count += 1
        params.append(room_id)

        update_query = f"""
            UPDATE project_rooms 
            SET {', '.join(set_clauses)}
            WHERE id = ${param_count}
            RETURNING *
        """

        updated_row = await conn.fetchrow(update_query, *params)
        logger.info(f"Raum {room_id} aktualisiert")
        return dict(updated_row)


async def delete_room(
    room_id: UUID | str,
    project_id: UUID | str,
    tenant_id: UUID | str,
) -> bool:
    """
    Löscht einen Raum.

    Args:
        room_id: Raum-ID
        project_id: Projekt-ID
        tenant_id: Mandanten-ID

    Returns:
        True wenn erfolgreich, False wenn nicht gefunden
    """
    if isinstance(room_id, str):
        room_id = UUID(room_id)
    if isinstance(project_id, str):
        project_id = UUID(project_id)
    if isinstance(tenant_id, str):
        tenant_id = UUID(tenant_id)

    async with get_connection() as conn:
        # Löschen mit Join-Check
        result = await conn.execute(
            """
            DELETE FROM project_rooms pr
            USING projects p
            WHERE pr.id = $1 
              AND pr.project_id = $2 
              AND p.id = pr.project_id 
              AND p.tenant_id = $3
            """,
            room_id,
            project_id,
            tenant_id,
        )

        deleted = result == "DELETE 1"
        if deleted:
            logger.info(f"Raum {room_id} gelöscht")
        return deleted


async def list_tenants() -> list[dict[str, Any]]:
    """
    Listet alle Mandanten.

    Returns:
        Liste der Tenants
    """
    async with get_connection() as conn:
        rows = await conn.fetch(
            "SELECT id, name, created_at FROM tenants ORDER BY name"
        )
        return [dict(r) for r in rows]


# === Lifecycle-Management für FastAPI ===

async def db_lifespan(app):
    """
    FastAPI Lifespan-Context-Manager für DB-Pool.

    Usage in main.py:
        from contextlib import asynccontextmanager

        @asynccontextmanager
        async def lifespan(app):
            async with db_lifespan(app):
                yield

        app = FastAPI(lifespan=lifespan)
    """
    # Startup
    await init_db_pool()
    yield
    # Shutdown
    await close_db_pool()
