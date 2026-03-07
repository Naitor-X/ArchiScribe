"""
Daten-Mapping & Validierung für KI-Extraktionen.

Mappt KI-JSON-Responses auf Datenbank-kompatible Strukturen und führt
Validierungen durch (Enum-Werte, Pflichtfelder, Plausibilitätsprüfungen).
"""

import logging
from dataclasses import dataclass, field
from datetime import date as Date
from datetime import datetime
from decimal import Decimal
from typing import Any

from app.schemas.extraction import ExtractionResult, RoomSchema

logger = logging.getLogger(__name__)


# === GÜLTIGE ENUM-WERTE (aus DB-Schema) ===

VALID_TOPOGRAPHY = {"eben", "leichte Hanglage", "starke Hanglage", "Sonstiges"}
VALID_ACCESS_STATUS = {"voll erschlossen", "teilerschlossen", "nicht erschlossen"}
VALID_PROJECT_TYPE = {
    "Neubau", "Bauen im Bestand", "Umbau im Inneren",
    "Sanierung/Modernis.", "Zubau/Anbau", "Aufstockung",
    "noch unklar", "Sonstiges"
}
VALID_BUILDING_TYPE = {"EFH", "Doppelhaus", "Reihenhaus", "Mehrfamilienhaus", "Sonstige"}
VALID_CONSTRUCTION_METHOD = {"Massivbau", "Holzbau", "noch offen"}
VALID_HEATING_TYPE = {"Wärmepumpe", "Gasheizung", "Fernwärme", "Holz/Pellets", "Sonstige"}
VALID_OWN_CONTRIBUTION = {"ja", "nein", "teilweise"}
VALID_ACCESSIBILITY = {"wichtig", "optional", "nicht relevant"}


# === ENUM-NORMALISIERUNG ===

ENUM_NORMALIZATION = {
    # project_type
    "sanierung": "Sanierung/Modernis.",
    "sanierung/modernisierung": "Sanierung/Modernis.",
    "modernisierung": "Sanierung/Modernis.",
    "neubau": "Neubau",
    "bauen im bestand": "Bauen im Bestand",
    "umbau": "Umbau im Inneren",
    "umbau im inneren": "Umbau im Inneren",
    "zubau": "Zubau/Anbau",
    "anbau": "Zubau/Anbau",
    "zubau/anbau": "Zubau/Anbau",
    "aufstockung": "Aufstockung",
    "noch unklar": "noch unklar",
    "sonstiges": "Sonstiges",

    # building_type
    "efh": "EFH",
    "einfamilienhaus": "EFH",
    "doppelhaus": "Doppelhaus",
    "reihenhaus": "Reihenhaus",
    "mehrfamilienhaus": "Mehrfamilienhaus",
    "sonstige": "Sonstige",

    # topography
    "eben": "eben",
    "leichte hanglage": "leichte Hanglage",
    "starke hanglage": "starke Hanglage",

    # access_status
    "voll erschlossen": "voll erschlossen",
    "teilerschlossen": "teilerschlossen",
    "nicht erschlossen": "nicht erschlossen",

    # construction_method
    "massivbau": "Massivbau",
    "holzbau": "Holzbau",
    "noch offen": "noch offen",

    # heating_type
    "wärmepumpe": "Wärmepumpe",
    "warmepumpe": "Wärmepumpe",
    "gasheizung": "Gasheizung",
    "fernwärme": "Fernwärme",
    "fernwaerme": "Fernwärme",
    "holz/pellets": "Holz/Pellets",
    "pellets": "Holz/Pellets",
    "holz": "Holz/Pellets",

    # own_contribution
    "ja": "ja",
    "nein": "nein",
    "teilweise": "teilweise",

    # accessibility
    "wichtig": "wichtig",
    "optional": "optional",
    "nicht relevant": "nicht relevant",
    "nicht relevant": "nicht relevant",
}


@dataclass
class ValidationResult:
    """Ergebnis der Daten-Validierung mit Warnungen und Fehlern."""

    is_valid: bool = True
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    normalized_data: dict[str, Any] = field(default_factory=dict)


@dataclass
class MappedProject:
    """Für Datenbank vorbereitetes Projekt-DTO."""

    # Allgemeine Angaben
    client_name: str | None = None
    address: str | None = None
    phone: str | None = None
    email: str | None = None
    date: Date | None = None

    # Grundstück
    plot_location: str | None = None
    plot_size_m2: Decimal | None = None
    landowner: str | None = None
    topography: str | None = None
    topography_other: str | None = None
    development_plan: bool | None = None
    access_status: str | None = None

    # Vorstellungen / Ziele
    project_type: str | None = None
    project_type_other: str | None = None
    building_type: str | None = None
    building_type_other: str | None = None
    construction_method: str | None = None
    heating_type: str | None = None
    heating_type_other: str | None = None
    budget: Decimal | None = None
    planned_start: Date | None = None
    own_contribution: str | None = None
    own_contribution_details: str | None = None

    # Besondere Hinweise
    accessibility: str | None = None
    outdoor_area: str | None = None
    materiality: str | None = None
    notes: str | None = None

    # Datei-Referenzen
    pdf_path: str | None = None
    page_paths: list[str] | None = None

    # Räume (separat zu speichern)
    rooms: list[dict[str, Any]] = field(default_factory=list)


def normalize_enum(value: str | None, valid_values: set[str], field_name: str) -> str | None:
    """
    Normalisiert einen Enum-Wert.

    Args:
        value: Der zu normalisierende Wert
        valid_values: Menge der gültigen Werte
        field_name: Feldname für Logging

    Returns:
        Normalisierter Wert oder None
    """
    if value is None:
        return None

    # Direkter Match
    if value in valid_values:
        return value

    # Normalisierung über Lookup-Tabelle
    normalized = ENUM_NORMALIZATION.get(value.lower().strip())
    if normalized and normalized in valid_values:
        logger.debug(f"Enum normalisiert: {field_name} '{value}' → '{normalized}'")
        return normalized

    # Kein Match gefunden
    logger.warning(f"Ungültiger Enum-Wert für {field_name}: '{value}'")
    return None


def parse_date(value: str | None, field_name: str) -> Date | None:
    """
    Parst ein Datum aus verschiedenen Formaten.

    Args:
        value: Datum als String
        field_name: Feldname für Logging

    Returns:
        date-Objekt oder None
    """
    if not value:
        return None

    value = value.strip()

    # ISO-Format (YYYY-MM-DD)
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        pass

    # Deutsches Format (DD.MM.YYYY)
    try:
        return datetime.strptime(value, "%d.%m.%Y").date()
    except ValueError:
        pass

    logger.warning(f"Datum konnte nicht geparst werden ({field_name}): '{value}'")
    return None


def parse_decimal(value: float | int | str | None, field_name: str) -> Decimal | None:
    """
    Konvertiert einen Wert zu Decimal.

    Args:
        value: Der zu konvertierende Wert
        field_name: Feldname für Logging

    Returns:
        Decimal oder None
    """
    if value is None:
        return None

    try:
        if isinstance(value, str):
            # Deutsche Schreibweise: Komma als Dezimaltrennzeichen
            value = value.replace(",", ".").replace(" ", "")
            return Decimal(value)
        return Decimal(str(value))
    except Exception:
        logger.warning(f"Dezimalwert konnte nicht geparst werden ({field_name}): '{value}'")
        return None


def validate_plausibility(data: MappedProject) -> list[str]:
    """
    Führt Plausibilitätsprüfungen durch.

    Args:
        data: Die gemappten Projektdaten

    Returns:
        Liste der Warnungen
    """
    warnings = []
    current_year = Date.today().year

    # Baujahr/Startdatum in der Zukunft?
    if data.planned_start:
        if data.planned_start.year > current_year + 5:
            warnings.append(
                f"Geplanter Baubeginn liegt weit in der Zukunft: {data.planned_start}"
            )

    # Negative oder extrem hohe Flächen?
    if data.plot_size_m2 is not None:
        if data.plot_size_m2 <= 0:
            warnings.append(f"Grundstücksgröße ist <= 0: {data.plot_size_m2}")
        elif data.plot_size_m2 > 100000:  # > 10 Hektar
            warnings.append(f"Grundstücksgröße ungewöhnlich groß: {data.plot_size_m2} m²")

    # Budget-Plausibilität
    if data.budget is not None:
        if data.budget <= 0:
            warnings.append(f"Budget ist <= 0: {data.budget}")
        elif data.budget > 100000000:  # > 100 Mio
            warnings.append(f"Budget ungewöhnlich hoch: {data.budget} EUR")

    # "Sonstiges" ohne Details?
    if data.topography == "Sonstiges" and not data.topography_other:
        warnings.append("Topographie='Sonstiges' aber kein Detailtext angegeben")

    if data.project_type == "Sonstiges" and not data.project_type_other:
        warnings.append("Projektart='Sonstiges' aber kein Detailtext angegeben")

    if data.building_type == "Sonstige" and not data.building_type_other:
        warnings.append("Gebäudetyp='Sonstige' aber kein Detailtext angegeben")

    if data.heating_type == "Sonstige" and not data.heating_type_other:
        warnings.append("Heizungstyp='Sonstige' aber kein Detailtext angegeben")

    return warnings


def map_extraction_to_project(
    extraction: ExtractionResult,
    pdf_path: str | None = None,
    page_paths: list[str] | None = None,
) -> tuple[MappedProject, ValidationResult]:
    """
    Mappt ein ExtractionResult auf ein MappedProject mit Validierung.

    Args:
        extraction: Das KI-Extraktionsergebnis
        pdf_path: Pfad zum Original-PDF
        page_paths: Liste der PNG-Seitenpfade

    Returns:
        Tuple aus (MappedProject, ValidationResult)
    """
    result = ValidationResult()
    project = MappedProject()

    # Datei-Referenzen
    project.pdf_path = pdf_path
    project.page_paths = page_paths or []

    # === Allgemeine Angaben ===
    project.client_name = extraction.client_name
    project.address = extraction.address
    project.phone = extraction.phone
    project.email = extraction.email
    project.date = parse_date(extraction.date, "date")

    # === Grundstück ===
    project.plot_location = extraction.plot_location
    project.plot_size_m2 = parse_decimal(extraction.plot_size_m2, "plot_size_m2")
    project.landowner = extraction.landowner

    project.topography = normalize_enum(
        extraction.topography, VALID_TOPOGRAPHY, "topography"
    )
    project.topography_other = extraction.topography_other

    project.development_plan = extraction.development_plan
    project.access_status = normalize_enum(
        extraction.access_status, VALID_ACCESS_STATUS, "access_status"
    )

    # === Vorstellungen / Ziele ===
    project.project_type = normalize_enum(
        extraction.project_type, VALID_PROJECT_TYPE, "project_type"
    )
    project.project_type_other = extraction.project_type_other

    project.building_type = normalize_enum(
        extraction.building_type, VALID_BUILDING_TYPE, "building_type"
    )
    project.building_type_other = extraction.building_type_other

    project.construction_method = normalize_enum(
        extraction.construction_method, VALID_CONSTRUCTION_METHOD, "construction_method"
    )

    project.heating_type = normalize_enum(
        extraction.heating_type, VALID_HEATING_TYPE, "heating_type"
    )
    project.heating_type_other = extraction.heating_type_other

    project.budget = parse_decimal(extraction.budget, "budget")
    project.planned_start = parse_date(extraction.planned_start, "planned_start")

    project.own_contribution = normalize_enum(
        extraction.own_contribution, VALID_OWN_CONTRIBUTION, "own_contribution"
    )
    project.own_contribution_details = extraction.own_contribution_details

    # === Besondere Hinweise ===
    project.accessibility = normalize_enum(
        extraction.accessibility, VALID_ACCESSIBILITY, "accessibility"
    )
    project.outdoor_area = extraction.outdoor_area
    project.materiality = extraction.materiality
    project.notes = extraction.notes

    # === Raumprogramm ===
    for room in extraction.rooms:
        room_dict = {
            "room_type": room.room_type,
            "quantity": room.quantity,
            "size_m2": parse_decimal(room.size_m2, f"room.{room.room_type}.size_m2"),
            "special_requirements": room.special_requirements,
        }
        project.rooms.append(room_dict)

    # === Plausibilitätsprüfungen ===
    plausibility_warnings = validate_plausibility(project)
    result.warnings.extend(plausibility_warnings)

    # === Pflichtfeld-Prüfung (nur Warnung, kein Fehler) ===
    if not project.client_name:
        result.warnings.append("Pflichtfeld 'client_name' ist leer")

    # Logging
    if result.warnings:
        logger.warning(f"Validierungswarnungen: {len(result.warnings)}")
        for w in result.warnings:
            logger.warning(f"  - {w}")

    result.normalized_data = project.__dict__.copy()
    result.is_valid = True  # Wir akzeptieren auch unvollständige Daten

    return project, result


def map_raw_json_to_project(
    raw_json: dict[str, Any],
    pdf_path: str | None = None,
    page_paths: list[str] | None = None,
) -> tuple[MappedProject | None, ValidationResult]:
    """
    Mappt ein rohes JSON-Dict auf ein MappedProject.

    Convenience-Funktion, die erst das Pydantic-Modell validiert.

    Args:
        raw_json: Rohe JSON-Daten von der KI
        pdf_path: Pfad zum Original-PDF
        page_paths: Liste der PNG-Seitenpfade

    Returns:
        Tuple aus (MappedProject | None, ValidationResult)
    """
    result = ValidationResult()

    try:
        # Pydantic-Validierung
        extraction = ExtractionResult(**raw_json)
    except Exception as e:
        result.is_valid = False
        result.errors.append(f"Pydantic-Validierung fehlgeschlagen: {e}")
        logger.error(f"Pydantic-Validierung fehlgeschlagen: {e}")
        return None, result

    # Mapping durchführen
    return map_extraction_to_project(extraction, pdf_path, page_paths)
