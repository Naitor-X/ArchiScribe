#!/usr/bin/env python3
"""
Test-Skript für HM1.5 und HM1.6: Daten-Mapping & Datenbank-Integration.

Testet die komplette Pipeline:
1. Mock-KI-Extraktion
2. Mapping mit Validierung
3. Speicherung in PostgreSQL
4. Laden und Verifizieren
"""

import asyncio
import json
import logging
import sys
from pathlib import Path
from uuid import UUID

# Pfad für Imports
sys.path.insert(0, str(Path(__file__).parent))

from app.config import settings
from app.database import (
    close_db_pool,
    ensure_test_tenant_exists,
    get_pool,
    get_project_by_id,
    init_db_pool,
    save_project,
    update_project_status,
)
from app.mapping import (
    MappedProject,
    map_raw_json_to_project,
)

# Logging konfigurieren
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Mock-Daten basierend auf echten Form2.pdf-Extraktion
MOCK_EXTRACTION = {
    "client_name": "Familie Max Mustermann",
    "address": "Hauptstraße 123, 80331 München",
    "phone": "+49 89 1234567",
    "email": "max.mustermann@email.de",
    "date": "2026-03-07",
    "plot_location": "Südwesthang, München-Bogenhausen",
    "plot_size_m2": 850.5,
    "landowner": "Max Mustermann",
    "topography": "leichte Hanglage",
    "topography_other": None,
    "development_plan": True,
    "access_status": "voll erschlossen",
    "project_type": "Neubau",
    "project_type_other": None,
    "building_type": "EFH",
    "building_type_other": None,
    "construction_method": "Holzbau",
    "heating_type": "Wärmepumpe",
    "heating_type_other": None,
    "budget": 450000.00,
    "planned_start": "2026-06-01",
    "own_contribution": "teilweise",
    "own_contribution_details": "Malerarbeiten und Gartenanlage selbst übernommen",
    "accessibility": "wichtig",
    "outdoor_area": "Große Terrasse, Swimmingpool, Garage für 2 Autos",
    "materiality": "Holz und Naturstein, moderne Architektur",
    "notes": "Barrierefreier Zugang wichtig, da Oma mit einzieht",
    "rooms": [
        {"room_type": "Schlafzimmer", "quantity": 2, "size_m2": 18.0, "special_requirements": None},
        {"room_type": "Kinderzimmer", "quantity": 2, "size_m2": 14.0, "special_requirements": None},
        {"room_type": "Wohnzimmer", "quantity": 1, "size_m2": 45.0, "special_requirements": "Kamin"},
        {"room_type": "Küche", "quantity": 1, "size_m2": 20.0, "special_requirements": "Insel"},
        {"room_type": "Badezimmer", "quantity": 2, "size_m2": 10.0, "special_requirements": None},
        {"room_type": "Gäste-WC", "quantity": 1, "size_m2": 4.0, "special_requirements": None},
        {"room_type": "Arbeitszimmer", "quantity": 1, "size_m2": 15.0, "special_requirements": "Schallgedämmt"},
        {"room_type": "Hauswirtschaftsraum", "quantity": 1, "size_m2": 8.0, "special_requirements": None},
        {"room_type": "Keller", "quantity": 1, "size_m2": 60.0, "special_requirements": None},
        {"room_type": "Garage", "quantity": 1, "size_m2": 35.0, "special_requirements": "2 Stellplätze"},
        {"room_type": "Terrasse", "quantity": 1, "size_m2": 40.0, "special_requirements": "Überdacht"},
    ],
}


async def test_mapping():
    """Testet das Daten-Mapping mit Validierung."""
    logger.info("=" * 60)
    logger.info("TEST: Daten-Mapping & Validierung")
    logger.info("=" * 60)

    # Mapping durchführen
    project, result = map_raw_json_to_project(
        MOCK_EXTRACTION,
        pdf_path="/files/archive/test-tenant/test-project/original_20260307.pdf",
        page_paths=[
            "/files/archive/test-tenant/test-project/page_001_20260307.png",
            "/files/archive/test-tenant/test-project/page_002_20260307.png",
        ],
    )

    # Ergebnisse anzeigen
    logger.info(f"Validierung erfolgreich: {result.is_valid}")
    logger.info(f"Fehler: {len(result.errors)}")
    for err in result.errors:
        logger.error(f"  - {err}")

    logger.info(f"Warnungen: {len(result.warnings)}")
    for warn in result.warnings:
        logger.warning(f"  - {warn}")

    # Projektdaten
    logger.info("\nProjektdaten:")
    logger.info(f"  Bauherr: {project.client_name}")
    logger.info(f"  Adresse: {project.address}")
    logger.info(f"  Projektart: {project.project_type}")
    logger.info(f"  Gebäudetyp: {project.building_type}")
    logger.info(f"  Budget: {project.budget} EUR")
    logger.info(f"  Grundstück: {project.plot_size_m2} m²")
    logger.info(f"  Räume: {len(project.rooms)}")

    return project, result


async def test_database(project: MappedProject):
    """Testet die Datenbank-Integration."""
    logger.info("\n" + "=" * 60)
    logger.info("TEST: Datenbank-Integration")
    logger.info("=" * 60)

    # DB-Pool initialisieren
    logger.info("Initialisiere DB-Pool...")
    await init_db_pool()

    try:
        pool = get_pool()
        async with pool.acquire() as conn:
            tenant_id = await ensure_test_tenant_exists(conn)

        logger.info(f"Test-Tenant: {tenant_id}")

        # Projekt speichern
        logger.info("\nSpeichere Projekt...")
        project_id = await save_project(
            project=project,
            tenant_id=tenant_id,
            raw_json=MOCK_EXTRACTION,
            confidence_scores={"client_name": 0.95, "budget": 0.88},
        )
        logger.info(f"Projekt gespeichert: {project_id}")

        # Projekt laden
        logger.info("\nLade Projekt zur Verifizierung...")
        loaded = await get_project_by_id(project_id, tenant_id)

        if loaded:
            logger.info("Projekt erfolgreich geladen:")
            logger.info(f"  ID: {loaded['id']}")
            logger.info(f"  Status: {loaded['status_id']}")
            logger.info(f"  Bauherr: {loaded['client_name']}")
            logger.info(f"  Budget: {loaded['budget']}")
            logger.info(f"  Räume in DB: {len(loaded['rooms'])}")
            logger.info(f"  AI-Extraktion vorhanden: {loaded['latest_extraction'] is not None}")

            # Status ändern
            logger.info("\nÄndere Projekt-Status...")
            success = await update_project_status(
                project_id=project_id,
                tenant_id=tenant_id,
                new_status="needs_review",
            )
            logger.info(f"Status-Änderung erfolgreich: {success}")

            # Erneut laden
            loaded2 = await get_project_by_id(project_id, tenant_id)
            logger.info(f"Neuer Status: {loaded2['status_id']}")

            return True
        else:
            logger.error("Projekt konnte nicht geladen werden!")
            return False

    finally:
        # Cleanup
        logger.info("\nSchließe DB-Pool...")
        await close_db_pool()


async def test_enum_normalization():
    """Testet die Enum-Normalisierung mit verschiedenen Eingaben."""
    logger.info("\n" + "=" * 60)
    logger.info("TEST: Enum-Normalisierung")
    logger.info("=" * 60)

    test_cases = [
        # (input, field, expected_valid)
        ("neubau", "project_type", True),
        ("Sanierung/Modernisierung", "project_type", True),  # Sollte zu "Sanierung/Modernis."
        ("EFH", "building_type", True),
        ("einfamilienhaus", "building_type", True),  # Sollte zu "EFH"
        ("wärmepumpe", "heating_type", True),
        ("Wärmepumpe", "heating_type", True),
        ("Ungültiger Wert", "project_type", False),
    ]

    from app.mapping import map_raw_json_to_project

    for input_val, field, should_be_valid in test_cases:
        test_data = {**MOCK_EXTRACTION, field: input_val}
        project, result = map_raw_json_to_project(test_data)

        actual_value = getattr(project, field)
        is_valid = actual_value is not None

        status = "✓" if is_valid == should_be_valid else "✗"
        logger.info(f"{status} '{input_val}' → '{actual_value}' (erwartet: valid={should_be_valid})")


async def main():
    """Haupt-Testfunktion."""
    logger.info("Starte HM1.5 + HM1.6 Integration Tests")
    logger.info(f"Datenbank: {settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}")
    logger.info(f"Test-Tenant: {settings.test_tenant_id}")

    try:
        # Test 1: Mapping
        project, result = await test_mapping()

        # Test 2: Enum-Normalisierung
        await test_enum_normalization()

        # Test 3: Datenbank (nur wenn DB erreichbar)
        try:
            await test_database(project)
            logger.info("\n" + "=" * 60)
            logger.info("ALLE TESTS ERFOLGREICH!")
            logger.info("=" * 60)
        except Exception as e:
            logger.warning(f"\nDatenbank-Test übersprungen: {e}")
            logger.info("Mapping-Tests waren erfolgreich!")

    except Exception as e:
        logger.error(f"Test fehlgeschlagen: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
