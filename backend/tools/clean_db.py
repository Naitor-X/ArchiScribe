#!/usr/bin/env python3
"""
Datenbank-Bereinigungstool für ArchiScribe.

Leert alle Datentabellen (außer project_statuses mit Default-Werten).
Tabellenstruktur bleibt erhalten - nur Daten werden gelöscht.

Verwendung:
    python3 clean_db.py [--force]

Optionen:
    --force    Überspringt die Bestätigungsabfrage
"""

import sys
from pathlib import Path

# Backend-Verzeichnis zum Pfad hinzufügen
sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncio

import asyncpg
from dotenv import load_dotenv

from app.config import settings


async def clean_database() -> dict[str, int]:
    """
    Leert alle Datentabellen in der korrekten Reihenfolge.

    Returns:
        Dict mit Anzahl gelöschter Datensätze pro Tabelle
    """
    conn = await asyncpg.connect(
        host=settings.postgres_host,
        port=settings.postgres_port,
        database=settings.postgres_db,
        user=settings.postgres_user,
        password=settings.postgres_password,
    )

    deleted_counts = {}

    try:
        # Reihenfolge wichtig wegen Foreign Keys (Kind-Tabellen zuerst)
        tables_to_clean = [
            "project_history",
            "ai_extractions",
            "project_rooms",
            "projects",
            "tenants",
        ]

        for table in tables_to_clean:
            count = await conn.fetchval(f"SELECT COUNT(*) FROM {table}")
            if count > 0:
                await conn.execute(f"TRUNCATE TABLE {table} CASCADE")
                deleted_counts[table] = count
                print(f"  ✓ {table}: {count} Datensätze gelöscht")
            else:
                print(f"  ○ {table}: bereits leer")

        # UUID-Tabellen haben keine Sequenzen
        # (uuid_generate_v4() generiert IDs direkt)
        print("  ✓ UUID-Tabellen haben keine Sequenzen")

    finally:
        await conn.close()

    return deleted_counts


def main():
    """Hauptfunktion."""
    # .env laden
    env_path = Path(__file__).parent.parent / ".env"
    load_dotenv(env_path)

    # Bestätigung einholen (außer mit --force)
    force = "--force" in sys.argv or "-f" in sys.argv

    if not force:
        print("\n" + "=" * 60)
        print("  ⚠️  ACHTUNG: Datenbank wird komplett geleert!")
        print("=" * 60)
        print(f"\n  Datenbank: {settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}")
        print("\n  Folgende Tabellen werden geleert:")
        print("    - project_history")
        print("    - ai_extractions")
        print("    - project_rooms")
        print("    - projects")
        print("    - tenants")
        print("\n  project_statuses bleibt erhalten (Default-Werte)")
        print("\n" + "-" * 60)

        response = input("  Fortfahren? [j/N]: ").strip().lower()
        if response not in ("j", "ja", "y", "yes"):
            print("\n  Abgebrochen.")
            sys.exit(0)

    print("\n  Bereinige Datenbank...")

    try:
        deleted = asyncio.run(clean_database())

        total = sum(deleted.values())
        print(f"\n  ✅ Fertig! Insgesamt {total} Datensätze gelöscht.")

    except Exception as e:
        print(f"\n  ❌ Fehler: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
