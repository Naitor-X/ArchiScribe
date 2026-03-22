"""Pydantic-Modelle für Projekt-API."""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, AliasChoices


# === Projekt-Schemas ===


class ProjectBase(BaseModel):
    """Basis-Modell für Projekt-Daten."""

    model_config = ConfigDict(populate_by_name=True)

    # Allgemeine Angaben
    client_name: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    form_date: Optional[date] = Field(
        None,
        validation_alias=AliasChoices("date", "form_date"),
        serialization_alias="date"
    )

    # Grundstück
    plot_location: Optional[str] = None
    plot_size_m2: Optional[Decimal] = None
    landowner: Optional[str] = None
    topography: Optional[str] = None
    topography_other: Optional[str] = None
    development_plan: Optional[bool] = None
    access_status: Optional[str] = None

    # Vorstellungen / Ziele
    project_type: Optional[str] = None
    project_type_other: Optional[str] = None
    building_type: Optional[str] = None
    building_type_other: Optional[str] = None
    construction_method: Optional[str] = None
    heating_type: Optional[str] = None
    heating_type_other: Optional[str] = None
    budget: Optional[Decimal] = None
    planned_start: Optional[date] = None
    own_contribution: Optional[str] = None
    own_contribution_details: Optional[str] = None

    # Besondere Hinweise
    accessibility: Optional[str] = None
    outdoor_area: Optional[str] = None
    materiality: Optional[str] = None
    notes: Optional[str] = None


class ProjectCreate(ProjectBase):
    """Request-Modell für Projekt-Erstellung."""

    tenant_id: UUID


class ProjectUpdate(ProjectBase):
    """Request-Modell für Projekt-Update (partial)."""

    pass


class ProjectListItem(BaseModel):
    """Lightweight Response für Projekt-Listen (nur benötigte Felder)."""

    id: UUID
    status_id: str
    client_name: Optional[str] = None
    address: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ProjectResponse(ProjectBase):
    """Response-Modell für Projekt-Daten."""

    id: UUID
    tenant_id: UUID
    status_id: str
    pdf_path: Optional[str] = None
    page_paths: Optional[list[str]] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ProjectWithDetails(ProjectResponse):
    """Projekt mit allen Details (Räume, AI-Extraktion)."""

    rooms: list["RoomResponse"] = []
    latest_extraction: Optional["AIExtractionResponse"] = None


class ProjectListResponse(BaseModel):
    """Response für Projekt-Liste mit Paginierung."""

    projects: list[ProjectListItem]
    total: int
    page: int
    page_size: int
    has_next: bool


# === Raum-Schemas ===


class RoomBase(BaseModel):
    """Basis-Modell für Raum-Daten."""

    room_type: str = Field(..., min_length=1, max_length=100)
    quantity: int = Field(default=1, ge=1)
    size_m2: Optional[Decimal] = Field(None, ge=0)
    special_requirements: Optional[str] = None


class RoomCreate(RoomBase):
    """Request-Modell für Raum-Erstellung."""

    # project_id kommt aus der URL, nicht aus dem Body
    pass


class RoomUpdate(RoomBase):
    """Request-Modell für Raum-Update (partial)."""

    room_type: Optional[str] = Field(None, min_length=1, max_length=100)
    quantity: Optional[int] = Field(None, ge=1)


class RoomResponse(RoomBase):
    """Response-Modell für Raum-Daten."""

    id: UUID
    project_id: UUID

    class Config:
        from_attributes = True


# === AI-Extraktion-Schemas ===


class AIExtractionResponse(BaseModel):
    """Response-Modell für AI-Extraktion."""

    id: UUID
    project_id: UUID
    raw_json: dict
    confidence_scores: Optional[dict] = None
    extracted_at: datetime

    class Config:
        from_attributes = True


# === Projekt-Historie-Schemas ===


class ProjectHistoryResponse(BaseModel):
    """Response-Modell für Projekt-Historie."""

    id: UUID
    project_id: UUID
    changed_by_user_id: Optional[UUID] = None
    changed_at: datetime
    changes: dict

    class Config:
        from_attributes = True


# === Status-Update-Schema ===


class StatusUpdateRequest(BaseModel):
    """Request für Status-Änderung."""

    new_status_id: str
    changed_by_user_id: Optional[UUID] = None


# === Tenant-Schemas ===


class TenantResponse(BaseModel):
    """Response-Modell für Tenant."""

    id: UUID
    name: str
    created_at: datetime

    class Config:
        from_attributes = True


# Forward References auflösen
ProjectWithDetails.model_rebuild()
