#!/usr/bin/env python3
"""
ArchiScribe - Datenbank-Initialisierungsskript

Initialisiert die PostgreSQL-Datenbank mit dem definierten Schema.

Ausführung vom backend-Ordner:
    python database/init_db.py
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT


def load_env() -> None:
    """Lädt die .env-Datei aus dem backend-Ordner."""
    # Ermittle den backend-Ordner (Elternverzeichnis von database/)
    backend_dir = Path(__file__).parent.parent
    env_path = backend_dir / ".env"

    if env_path.exists():
        load_dotenv(env_path)
        print(f"📄 .env geladen aus: {env_path}")
    else:
        print(f"⚠️  Keine .env gefunden unter: {env_path}")
        print("   Verwende Umgebungsvariablen oder Standardwerte")


def get_db_config() -> dict:
    """Lädt Datenbank-Konfiguration aus Umgebungsvariablen."""
    return {
        "host": os.getenv("POSTGRES_HOST", "localhost"),
        "port": int(os.getenv("POSTGRES_PORT", "5432")),
        "database": os.getenv("POSTGRES_DB", "archiscribe"),
        "user": os.getenv("POSTGRES_USER", "postgres"),
        "password": os.getenv("POSTGRES_PASSWORD", ""),
    }


def create_database_if_not_exists(config: dict) -> None:
    """Erstellt die Datenbank, falls sie noch nicht existiert."""
    # Ohne Datenbanknamen verbinden
    conn = psycopg2.connect(
        host=config["host"],
        port=config["port"],
        user=config["user"],
        password=config["password"],
        database="postgres",
    )
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)

    cursor = conn.cursor()

    # Prüfen ob Datenbank existiert
    cursor.execute(
        "SELECT 1 FROM pg_database WHERE datname = %s",
        (config["database"],)
    )

    if not cursor.fetchone():
        print(f"📊 Erstelle Datenbank '{config['database']}'...")
        cursor.execute(f'CREATE DATABASE "{config["database"]}"')
    else:
        print(f"✓ Datenbank '{config['database']}' existiert bereits")

    cursor.close()
    conn.close()


def execute_schema(config: dict) -> None:
    """Führt das SQL-Schema aus."""
    schema_path = Path(__file__).parent / "schema.sql"

    if not schema_path.exists():
        print(f"❌ Schema-Datei nicht gefunden: {schema_path}")
        sys.exit(1)

    print(f"📄 Lade Schema aus: {schema_path}")

    with open(schema_path, "r", encoding="utf-8") as f:
        schema_sql = f.read()

    conn = psycopg2.connect(**config)
    cursor = conn.cursor()

    try:
        print("⚙️  Führe Schema aus...")
        cursor.execute(schema_sql)
        conn.commit()
        print("✓ Schema erfolgreich ausgeführt")
    except Exception as e:
        conn.rollback()
        print(f"❌ Fehler beim Ausführen des Schemas: {e}")
        raise
    finally:
        cursor.close()
        conn.close()


def show_tables(config: dict) -> None:
    """Zeigt alle erstellten Tabellen an."""
    conn = psycopg2.connect(**config)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
        AND table_type = 'BASE TABLE'
        ORDER BY table_name
    """)

    tables = cursor.fetchall()

    print("\n📋 Erstellte Tabellen:")
    for (table_name,) in tables:
        print(f"   • {table_name}")

    cursor.close()
    conn.close()


def main() -> None:
    """Hauptfunktion."""
    print("=" * 50)
    print("ArchiScribe - Datenbank-Initialisierung")
    print("=" * 50)
    print()

    # .env aus dem backend-Ordner laden
    load_env()

    config = get_db_config()

    print("🔗 Verbindungseinstellungen:")
    print(f"   Host: {config['host']}")
    print(f"   Port: {config['port']}")
    print(f"   Datenbank: {config['database']}")
    print(f"   User: {config['user']}")
    print()

    try:
        create_database_if_not_exists(config)
        execute_schema(config)
        show_tables(config)
        print("\n✅ Datenbank erfolgreich initialisiert!")
    except Exception as e:
        print(f"\n❌ Initialisierung fehlgeschlagen: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
