#!/usr/bin/env python3
"""
ArchiScribe - Testdaten einfügen

Fügt Testdaten in die Datenbank ein für API-Tests.
"""

import asyncio
import json
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

import asyncpg
from dotenv import load_dotenv
import os
from pathlib import Path


# .env laden
backend_dir = Path(__file__).parent.parent
env_path = backend_dir / ".env"
load_dotenv(env_path)


async def insert_test_data():
    """Fügt Testdaten ein."""

    # Verbindung zur DB
    conn = await asyncpg.connect(
        host=os.getenv("POSTGRES_HOST"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        database=os.getenv("POSTGRES_DB"),
        user=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD"),
    )

    print("🔗 Verbunden mit Datenbank")

    try:
        # Test-Tenant sicherstellen
        test_tenant_id = UUID(os.getenv("TEST_TENANT_ID"))

        await conn.execute(
            """
            INSERT INTO tenants (id, name)
            VALUES ($1, 'Test Architekturbüro')
            ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name
            """,
            test_tenant_id,
        )
        print(f"✅ Test-Tenant erstellt/aktualisiert: {test_tenant_id}")

        # Test-Projekte erstellen
        projects = [
            {
                "id": UUID("00000000-0000-0000-0001-000000000001"),
                "tenant_id": test_tenant_id,
                "status_id": "needs_review",
                "client_name": "Max Mustermann",
                "address": "Musterstraße 123, 6840 Götzis",
                "phone": "+43 664 123456",
                "email": "max.mustermann@email.at",
                "date": date(2026, 3, 10),
                "plot_location": "Am Kobel, 6840 Götzis",
                "plot_size_m2": Decimal("850.5"),
                "landowner": "Max Mustermann",
                "topography": "leichte Hanglage",
                "development_plan": True,
                "access_status": "voll erschlossen",
                "project_type": "Neubau",
                "building_type": "EFH",
                "construction_method": "Massivbau",
                "heating_type": "Wärmepumpe",
                "budget": Decimal("450000.00"),
                "planned_start": date(2026, 6, 1),
                "own_contribution": "teilweise",
                "own_contribution_details": "Malerarbeiten, Gartenanlage",
                "accessibility": "wichtig",
                "outdoor_area": "Große Terrasse, Carport, Garten mit Pool",
                "materiality": "Holz, Naturstein, offene Bauweise",
                "notes": "Kunde wünscht energieeffizientes Haus",
            },
            {
                "id": UUID("00000000-0000-0000-0001-000000000002"),
                "tenant_id": test_tenant_id,
                "status_id": "needs_review",
                "client_name": "Anna Schmidt",
                "address": "Dorfstraße 45, 6850 Dornbirn",
                "phone": "+43 664 654321",
                "email": "anna.schmidt@email.at",
                "date": date(2026, 3, 12),
                "plot_location": "Hatlerdorf, 6850 Dornbirn",
                "plot_size_m2": Decimal("1200.0"),
                "landowner": "Anna Schmidt",
                "topography": "eben",
                "development_plan": True,
                "access_status": "voll erschlossen",
                "project_type": "Sanierung/Modernis.",
                "building_type": "Mehrfamilienhaus",
                "construction_method": "Massivbau",
                "heating_type": "Fernwärme",
                "budget": Decimal("280000.00"),
                "planned_start": date(2026, 5, 15),
                "own_contribution": "nein",
                "accessibility": "optional",
                "outdoor_area": "Kleiner Garten",
                "materiality": "Moderne Materialien",
                "notes": "Sanierung eines bestehenden MFH",
            },
            {
                "id": UUID("00000000-0000-0000-0001-000000000003"),
                "tenant_id": test_tenant_id,
                "status_id": "aktiv",
                "client_name": "Peter Huber",
                "address": "Hauptstraße 78, 6900 Bregenz",
                "phone": "+43 664 111222",
                "email": "peter.huber@email.at",
                "date": date(2026, 3, 5),
                "plot_location": "Vorkloster, 6900 Bregenz",
                "plot_size_m2": Decimal("650.0"),
                "landowner": "Peter Huber",
                "topography": "starke Hanglage",
                "topography_other": None,
                "development_plan": True,
                "access_status": "teilerschlossen",
                "project_type": "Neubau",
                "building_type": "Doppelhaus",
                "construction_method": "Holzbau",
                "heating_type": "Wärmepumpe",
                "budget": Decimal("380000.00"),
                "planned_start": date(2026, 4, 1),
                "own_contribution": "ja",
                "own_contribution_details": "Innenausbau, Elektroinstallation",
                "accessibility": "nicht relevant",
                "outdoor_area": "Terrasse, Stellplatz",
                "materiality": "Holz, Glas",
                "notes": "Passivhaus-Standard gewünscht",
            },
        ]

        for project_data in projects:
            await conn.execute(
                """
                INSERT INTO projects (
                    id, tenant_id, status_id,
                    client_name, address, phone, email, date,
                    plot_location, plot_size_m2, landowner,
                    topography, development_plan, access_status,
                    project_type, building_type, construction_method,
                    heating_type, budget, planned_start,
                    own_contribution, own_contribution_details,
                    accessibility, outdoor_area, materiality, notes
                ) VALUES (
                    $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14,
                    $15, $16, $17, $18, $19, $20, $21, $22, $23, $24, $25, $26
                )
                ON CONFLICT (id) DO UPDATE SET
                    client_name = EXCLUDED.client_name,
                    status_id = EXCLUDED.status_id
                """,
                project_data["id"],
                project_data["tenant_id"],
                project_data["status_id"],
                project_data["client_name"],
                project_data["address"],
                project_data["phone"],
                project_data["email"],
                project_data["date"],
                project_data["plot_location"],
                project_data["plot_size_m2"],
                project_data["landowner"],
                project_data["topography"],
                project_data["development_plan"],
                project_data["access_status"],
                project_data["project_type"],
                project_data["building_type"],
                project_data["construction_method"],
                project_data["heating_type"],
                project_data["budget"],
                project_data["planned_start"],
                project_data["own_contribution"],
                project_data.get("own_contribution_details"),
                project_data["accessibility"],
                project_data["outdoor_area"],
                project_data["materiality"],
                project_data["notes"],
            )
            print(f"✅ Projekt erstellt: {project_data['client_name']}")

        # Räume für Projekt 1
        rooms_p1 = [
            {
                "project_id": projects[0]["id"],
                "room_type": "Wohnzimmer",
                "quantity": 1,
                "size_m2": Decimal("45.0"),
                "special_requirements": "Offen zur Küche",
            },
            {
                "project_id": projects[0]["id"],
                "room_type": "Küche",
                "quantity": 1,
                "size_m2": Decimal("20.0"),
                "special_requirements": "Großer Kochbereich",
            },
            {
                "project_id": projects[0]["id"],
                "room_type": "Schlafzimmer",
                "quantity": 3,
                "size_m2": Decimal("18.0"),
                "special_requirements": None,
            },
            {
                "project_id": projects[0]["id"],
                "room_type": "Badezimmer",
                "quantity": 2,
                "size_m2": Decimal("10.0"),
                "special_requirements": "Eines davon barrierefrei",
            },
            {
                "project_id": projects[0]["id"],
                "room_type": "Büro",
                "quantity": 1,
                "size_m2": Decimal("15.0"),
                "special_requirements": "Ruhig gelegen",
            },
        ]

        for room_data in rooms_p1:
            await conn.execute(
                """
                INSERT INTO project_rooms (
                    project_id, room_type, quantity, size_m2, special_requirements
                ) VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT DO NOTHING
                """,
                room_data["project_id"],
                room_data["room_type"],
                room_data["quantity"],
                room_data["size_m2"],
                room_data["special_requirements"],
            )
        print(f"✅ {len(rooms_p1)} Räume für Projekt 1 erstellt")

        # Räume für Projekt 2
        rooms_p2 = [
            {
                "project_id": projects[1]["id"],
                "room_type": "Wohnung",
                "quantity": 4,
                "size_m2": Decimal("75.0"),
                "special_requirements": "Jeweils 3 Zimmer",
            },
        ]

        for room_data in rooms_p2:
            await conn.execute(
                """
                INSERT INTO project_rooms (
                    project_id, room_type, quantity, size_m2, special_requirements
                ) VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT DO NOTHING
                """,
                room_data["project_id"],
                room_data["room_type"],
                room_data["quantity"],
                room_data["size_m2"],
                room_data["special_requirements"],
            )
        print(f"✅ {len(rooms_p2)} Räume für Projekt 2 erstellt")

        # AI-Extraktion für Projekt 1
        extraction_data = {
            "project_id": projects[0]["id"],
            "raw_json": {
                "client_name": "Max Mustermann",
                "address": "Musterstraße 123, 6840 Götzis",
                "phone": "+43 664 123456",
                "email": "max.mustermann@email.at",
                "rooms": [
                    {"room_type": "Wohnzimmer", "quantity": 1, "size_m2": 45},
                    {"room_type": "Küche", "quantity": 1, "size_m2": 20},
                    {"room_type": "Schlafzimmer", "quantity": 3, "size_m2": 18},
                ],
            },
            "confidence_scores": {
                "client_name": 0.98,
                "address": 0.95,
                "phone": 0.92,
                "email": 0.99,
            },
        }

        await conn.execute(
            """
            INSERT INTO ai_extractions (project_id, raw_json, confidence_scores)
            VALUES ($1, $2, $3)
            ON CONFLICT DO NOTHING
            """,
            extraction_data["project_id"],
            json.dumps(extraction_data["raw_json"]),
            json.dumps(extraction_data["confidence_scores"]),
        )
        print(f"✅ AI-Extraktion für Projekt 1 erstellt")

        # Projekt-Historie für Projekt 3
        history_data = {
            "project_id": projects[2]["id"],
            "changed_by_user_id": None,
            "changes": {
                "status_id": {
                    "old": "needs_review",
                    "new": "aktiv",
                },
                "budget": {
                    "old": 350000,
                    "new": 380000,
                },
            },
        }

        await conn.execute(
            """
            INSERT INTO project_history (project_id, changed_by_user_id, changes)
            VALUES ($1, $2, $3)
            """,
            history_data["project_id"],
            history_data["changed_by_user_id"],
            json.dumps(history_data["changes"]),
        )
        print(f"✅ Projekt-Historie für Projekt 3 erstellt")

        print("\n🎉 Alle Testdaten erfolgreich eingefügt!")

        # Datenbank-Statistik
        count_projects = await conn.fetchval("SELECT COUNT(*) FROM projects")
        count_rooms = await conn.fetchval("SELECT COUNT(*) FROM project_rooms")
        count_extractions = await conn.fetchval("SELECT COUNT(*) FROM ai_extractions")
        count_history = await conn.fetchval("SELECT COUNT(*) FROM project_history")

        print(f"\n📊 Datenbank-Statistik:")
        print(f"   Projekte: {count_projects}")
        print(f"   Räume: {count_rooms}")
        print(f"   AI-Extraktionen: {count_extractions}")
        print(f"   Historien-Einträge: {count_history}")

    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(insert_test_data())
