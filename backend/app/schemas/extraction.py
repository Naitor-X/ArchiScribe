"""
Pydantic-Modelle für KI-Extraktion von Grundlagenformularen.

Diese Schemas definieren die erwartete JSON-Struktur der OpenRouter-API-Antwort.
Sie entsprechen der Datenbankstruktur aus docs/DATABASE.md.
"""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# === ENUMS (entsprechen DB-Enum-Typen) ===


class TopographyEnum(str, Enum):
    EBEN = "eben"
    LEICHTE_HANG = "leichte Hanglage"
    STARKE_HANG = "starke Hanglage"
    SONSTIGES = "Sonstiges"


class AccessStatusEnum(str, Enum):
    VOLL_ERSCHLOSSEN = "voll erschlossen"
    TEILERSCHLOSSEN = "teilerschlossen"
    NICHT_ERSCHLOSSEN = "nicht erschlossen"


class ProjectTypeEnum(str, Enum):
    NEUBAU = "Neubau"
    BAUEN_IM_BESTAND = "Bauen im Bestand"
    UMBAU_INNEN = "Umbau im Inneren"
    SANIERUNG = "Sanierung/Modernis."
    ZUBAU = "Zubau/Anbau"
    AUFSTOCKUNG = "Aufstockung"
    NOCH_UNKLAR = "noch unklar"
    SONSTIGES = "Sonstiges"


class BuildingTypeEnum(str, Enum):
    EFH = "EFH"
    DOPPELHAUS = "Doppelhaus"
    REIHENHAUS = "Reihenhaus"
    MEHRFAMILIENHAUS = "Mehrfamilienhaus"
    SONSTIGE = "Sonstige"


class ConstructionMethodEnum(str, Enum):
    MASSIVBAU = "Massivbau"
    HOLZBAU = "Holzbau"
    NOCH_OFFEN = "noch offen"


class HeatingTypeEnum(str, Enum):
    WARMERPUMPE = "Wärmepumpe"
    GASHEIZUNG = "Gasheizung"
    FERNWARME = "Fernwärme"
    HOLZ_PELLETS = "Holz/Pellets"
    SONSTIGE = "Sonstige"


class OwnContributionEnum(str, Enum):
    JA = "ja"
    NEIN = "nein"
    TEILWEISE = "teilweise"


class AccessibilityEnum(str, Enum):
    WICHTIG = "wichtig"
    OPTIONAL = "optional"
    NICHT_RELEVANT = "nicht relevant"


# === SCHEMAS ===


class RoomSchema(BaseModel):
    """Raumprogramm-Eintrag für project_rooms-Tabelle."""

    room_type: str = Field(..., description="Raumtyp (z.B. 'Schlafzimmer', 'Küche')")
    quantity: int = Field(default=1, ge=1, description="Anzahl der Räume")
    size_m2: Optional[float] = Field(default=None, ge=0, description="Gewünschte Größe in m²")
    special_requirements: Optional[str] = Field(
        default=None, description="Besondere Anforderungen"
    )


class ExtractionResult(BaseModel):
    """
    Validiertes Ergebnis der KI-Extraktion.

    Entspricht der projects-Tabelle mit allen relevanten Feldern.
    Optional-Fields ermöglichen teilweise Extraktion bei unvollständigen Formularen.
    """

    # === Allgemeine Angaben ===
    client_name: Optional[str] = Field(default=None, description="Name des Bauherren")
    address: Optional[str] = Field(default=None, description="Adresse des Bauherren")
    phone: Optional[str] = Field(default=None, description="Telefonnummer")
    email: Optional[str] = Field(default=None, description="E-Mail-Adresse")
    date: Optional[str] = Field(
        default=None, description="Datum der Erfassung (ISO-Format: YYYY-MM-DD)"
    )

    # === Grundstück ===
    plot_location: Optional[str] = Field(default=None, description="Lage des Grundstücks")
    plot_size_m2: Optional[float] = Field(default=None, ge=0, description="Grundstücksgröße in m²")
    landowner: Optional[str] = Field(default=None, description="Grundstückseigentümer")
    topography: Optional[str] = Field(
        default=None, description="Topographie: 'eben', 'leichte Hanglage', 'starke Hanglage', 'Sonstiges'"
    )
    topography_other: Optional[str] = Field(
        default=None, description="Freitext wenn topography='Sonstiges'"
    )
    development_plan: Optional[bool] = Field(
        default=None, description="Bebauungsplan vorhanden?"
    )
    access_status: Optional[str] = Field(
        default=None,
        description="Erschließungsstatus: 'voll erschlossen', 'teilerschlossen', 'nicht erschlossen'",
    )

    # === Vorstellungen / Ziele ===
    project_type: Optional[str] = Field(
        default=None,
        description="Projektart: 'Neubau', 'Bauen im Bestand', 'Umbau im Inneren', 'Sanierung/Modernis.', 'Zubau/Anbau', 'Aufstockung', 'noch unklar', 'Sonstiges'",
    )
    project_type_other: Optional[str] = Field(
        default=None, description="Freitext wenn project_type='Sonstiges'"
    )
    building_type: Optional[str] = Field(
        default=None,
        description="Gebäudetyp: 'EFH', 'Doppelhaus', 'Reihenhaus', 'Mehrfamilienhaus', 'Sonstige'",
    )
    building_type_other: Optional[str] = Field(
        default=None, description="Freitext wenn building_type='Sonstige'"
    )
    construction_method: Optional[str] = Field(
        default=None, description="Bauweise: 'Massivbau', 'Holzbau', 'noch offen'"
    )
    heating_type: Optional[str] = Field(
        default=None,
        description="Heizungstyp: 'Wärmepumpe', 'Gasheizung', 'Fernwärme', 'Holz/Pellets', 'Sonstige'",
    )
    heating_type_other: Optional[str] = Field(
        default=None, description="Freitext wenn heating_type='Sonstige'"
    )
    budget: Optional[float] = Field(default=None, ge=0, description="Budget in EUR")
    planned_start: Optional[str] = Field(
        default=None, description="Geplanter Baubeginn (ISO-Format: YYYY-MM-DD)"
    )
    own_contribution: Optional[str] = Field(
        default=None, description="Eigenleistung: 'ja', 'nein', 'teilweise'"
    )
    own_contribution_details: Optional[str] = Field(
        default=None, description="Details zur Eigenleistung"
    )

    # === Besondere Hinweise / Notizen ===
    accessibility: Optional[str] = Field(
        default=None, description="Barrierefreiheit: 'wichtig', 'optional', 'nicht relevant'"
    )
    outdoor_area: Optional[str] = Field(default=None, description="Außenanlagen-Wünsche")
    materiality: Optional[str] = Field(default=None, description="Materialvorstellungen")
    notes: Optional[str] = Field(default=None, description="Sonstige Notizen")

    # === Raumprogramm ===
    rooms: list[RoomSchema] = Field(
        default_factory=list, description="Liste der gewünschten Räume"
    )

    model_config = {
        "extra": "ignore",  # Ignoriere zusätzliche Felder von der KI
    }
