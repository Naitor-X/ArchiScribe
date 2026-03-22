"""API-Router für Projekt-Endpunkte."""

import logging
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from app.database import (
    create_room,
    delete_room,
    get_project_by_id,
    get_project_history,
    list_projects,
    update_project,
    update_project_status,
    update_room,
)
from app.schemas.project import (
    ProjectListItem,
    ProjectListResponse,
    ProjectResponse,
    ProjectUpdate,
    ProjectWithDetails,
    RoomCreate,
    RoomResponse,
    RoomUpdate,
    StatusUpdateRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/projects", tags=["Projekte"])


def _get_tenant_id() -> UUID:
    """
    Gibt die Tenant-ID zurück.

    In einer echten App würde dies aus dem JWT-Token kommen.
    Für jetzt nutzen wir die Test-Tenant-ID.
    """
    from app.config import settings
    return UUID(settings.test_tenant_id)


@router.get("", response_model=ProjectListResponse)
async def list_projects_endpoint(
    status_id: str | None = Query(None, description="Filter nach Status"),
    search: str | None = Query(None, description="Suchbegriff (client_name, address)"),
    page: int = Query(1, ge=1, description="Seitennummer"),
    page_size: int = Query(20, ge=1, le=100, description="Einträge pro Seite"),
) -> ProjectListResponse:
    """
    Listet alle Projekte eines Mandanten.

    Unterstützt:
    - Paginierung (page, page_size)
    - Filterung nach Status
    - Volltextsuche (client_name, address)
    """
    tenant_id = _get_tenant_id()

    projects, total = await list_projects(
        tenant_id=tenant_id,
        status_id=status_id,
        search=search,
        page=page,
        page_size=page_size,
    )

    # Effiziente Konvertierung mit ProjectListItem (nur 5 Felder)
    project_items = [ProjectListItem(**p) for p in projects]

    return ProjectListResponse(
        projects=project_items,
        total=total,
        page=page,
        page_size=page_size,
        has_next=(page * page_size) < total,
    )


@router.get("/{project_id}", response_model=ProjectWithDetails)
async def get_project_endpoint(project_id: UUID) -> ProjectWithDetails:
    """
    Lädt ein Projekt mit allen Details.

    Enthält:
    - Projektdaten
    - Raumprogramm
    - Neueste KI-Extraktion
    """
    import json

    tenant_id = _get_tenant_id()

    project = await get_project_by_id(project_id, tenant_id)

    if not project:
        raise HTTPException(status_code=404, detail=f"Projekt {project_id} nicht gefunden")

    # Räume aus project entfernen und konvertieren
    rooms_data = project.pop("rooms", [])
    rooms = [RoomResponse(project_id=project_id, **r) for r in rooms_data]

    # AI-Extraktion konvertieren
    extraction = None
    raw_extraction = project.pop("latest_extraction", None)
    if raw_extraction:
        from app.schemas.project import AIExtractionResponse

        raw_json = raw_extraction["raw_json"]
        if isinstance(raw_json, str):
            raw_json = json.loads(raw_json)

        confidence = raw_extraction.get("confidence_scores")
        if isinstance(confidence, str):
            confidence = json.loads(confidence)

        extraction = AIExtractionResponse(
            id=raw_extraction["id"],
            project_id=project_id,
            raw_json=raw_json,
            confidence_scores=confidence,
            extracted_at=raw_extraction["extracted_at"],
        )

    # page_paths parsen (JSONB kann als String kommen)
    page_paths = project.pop("page_paths", None)
    if isinstance(page_paths, str):
        page_paths = json.loads(page_paths)

    # DB-Feld 'date' zu 'form_date' für Response
    if "date" in project:
        project["form_date"] = project.pop("date")

    return ProjectWithDetails(
        **project,
        page_paths=page_paths,
        rooms=rooms,
        latest_extraction=extraction,
    )


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project_endpoint(
    project_id: UUID,
    updates: ProjectUpdate,
) -> ProjectResponse:
    """
    Aktualisiert ein Projekt (partial update).

    Nur übergebene Felder werden aktualisiert.
    Erstellt automatisch einen Eintrag in der Projekt-Historie.
    """
    import json

    tenant_id = _get_tenant_id()

    update_data = updates.model_dump(exclude_unset=True, by_alias=True)

    if not update_data:
        raise HTTPException(status_code=400, detail="Keine Änderungen angegeben")

    updated_project = await update_project(
        project_id=project_id,
        tenant_id=tenant_id,
        updates=update_data,
    )

    if not updated_project:
        raise HTTPException(status_code=404, detail=f"Projekt {project_id} nicht gefunden")

    # DB-Feld 'date' zu 'form_date' mappen
    if "date" in updated_project:
        updated_project["form_date"] = updated_project.pop("date")

    # page_paths parsen
    if isinstance(updated_project.get("page_paths"), str):
        updated_project["page_paths"] = json.loads(updated_project["page_paths"])

    return ProjectResponse(**updated_project)


@router.patch("/{project_id}/status", response_model=ProjectResponse)
async def update_status_endpoint(
    project_id: UUID,
    status_update: StatusUpdateRequest,
) -> ProjectResponse:
    """
    Ändert den Status eines Projekts.

    Erlaubte Status:
    - raw_extracted: KI-Rohextraktion
    - needs_review: Überprüfung erforderlich
    - verified_by_architect: Vom Architekten verifiziert
    """
    tenant_id = _get_tenant_id()

    success = await update_project_status(
        project_id=project_id,
        tenant_id=tenant_id,
        new_status=status_update.new_status_id,
        changed_by_user_id=status_update.changed_by_user_id,
    )

    if not success:
        raise HTTPException(status_code=404, detail=f"Projekt {project_id} nicht gefunden")

    # Aktualisiertes Projekt zurückgeben
    project = await get_project_by_id(project_id, tenant_id)
    return ProjectResponse(**project)


@router.get("/{project_id}/history")
async def get_history_endpoint(project_id: UUID) -> list[dict[str, Any]]:
    """
    Lädt die Änderungshistorie eines Projekts.

    Zeigt alle Änderungen mit Zeitstempel und User-ID.
    """
    tenant_id = _get_tenant_id()

    history = await get_project_history(project_id, tenant_id)

    # UUIDs zu Strings konvertieren für JSON
    result = []
    for entry in history:
        result.append({
            "id": str(entry["id"]),
            "project_id": str(entry["project_id"]),
            "changed_by_user_id": str(entry["changed_by_user_id"]) if entry.get("changed_by_user_id") else None,
            "changed_at": entry["changed_at"].isoformat(),
            "changes": entry["changes"],
        })

    return result


# === Raum-Endpunkte ===


@router.post("/{project_id}/rooms", response_model=RoomResponse, status_code=201)
async def create_room_endpoint(
    project_id: UUID,
    room: RoomCreate,
) -> RoomResponse:
    """
    Fügt einen neuen Raum zum Raumprogramm hinzu.
    """
    tenant_id = _get_tenant_id()

    room_id = await create_room(
        project_id=project_id,
        tenant_id=tenant_id,
        room_data={
            "room_type": room.room_type,
            "quantity": room.quantity,
            "size_m2": room.size_m2,
            "special_requirements": room.special_requirements,
        },
    )

    if not room_id:
        raise HTTPException(status_code=404, detail=f"Projekt {project_id} nicht gefunden")

    return RoomResponse(
        id=room_id,
        project_id=project_id,
        room_type=room.room_type,
        quantity=room.quantity,
        size_m2=room.size_m2,
        special_requirements=room.special_requirements,
    )


@router.put("/{project_id}/rooms/{room_id}", response_model=RoomResponse)
async def update_room_endpoint(
    project_id: UUID,
    room_id: UUID,
    updates: RoomUpdate,
) -> RoomResponse:
    """
    Aktualisiert einen Raum (partial update).
    """
    tenant_id = _get_tenant_id()

    # Nur nicht-None Werte übernehmen, Aliases für DB-Kompatibilität verwenden
    update_data = updates.model_dump(exclude_unset=True, by_alias=True)

    if not update_data:
        raise HTTPException(status_code=400, detail="Keine Änderungen angegeben")

    updated_room = await update_room(
        room_id=room_id,
        project_id=project_id,
        tenant_id=tenant_id,
        updates=update_data,
    )

    if not updated_room:
        raise HTTPException(status_code=404, detail=f"Raum {room_id} nicht gefunden")

    return RoomResponse(**updated_room)


@router.delete("/{project_id}/rooms/{room_id}", status_code=204)
async def delete_room_endpoint(
    project_id: UUID,
    room_id: UUID,
) -> None:
    """
    Löscht einen Raum aus dem Raumprogramm.
    """
    tenant_id = _get_tenant_id()

    success = await delete_room(
        room_id=room_id,
        project_id=project_id,
        tenant_id=tenant_id,
    )

    if not success:
        raise HTTPException(status_code=404, detail=f"Raum {room_id} nicht gefunden")
