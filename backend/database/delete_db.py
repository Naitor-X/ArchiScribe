#!/usr/bin/env python3
"""
ArchiScribe - Datenbank-Löschskript

Löscht die PostgreSQL-Datenbank komplett inklusive aller Tabellen und Daten.

⚠️  WARNUNG: Dies ist ein destruktiver Vorgang und kann NICHT rückgängig gemacht werden!

Ausführung vom backend-Ordner:
    python database/delete_db.py
"""

import os
import sys
import random
import string
from pathlib import Path

from dotenv import load_dotenv
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT


def load_env() -> None:
    """Lädt die .env-Datei aus dem backend-Ordner."""
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


def generate_confirmation_word(length: int = 6) -> str:
    """Generiert ein zufälliges Bestätigungswort."""
    return ''.join(random.choices(string.ascii_uppercase, k=length))


def check_database_exists(config: dict) -> bool:
    """Prüft, ob die Datenbank existiert."""
    conn = psycopg2.connect(
        host=config["host"],
        port=config["port"],
        user=config["user"],
        password=config["password"],
        database="postgres",
    )
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)

    cursor = conn.cursor()
    cursor.execute(
        "SELECT 1 FROM pg_database WHERE datname = %s",
        (config["database"],)
    )
    exists = cursor.fetchone() is not None

    cursor.close()
    conn.close()
    return exists


def get_table_count(config: dict) -> int:
    """Gibt die Anzahl der Tabellen in der Datenbank zurück."""
    try:
        conn = psycopg2.connect(
            host=config["host"],
            port=config["port"],
            user=config["user"],
            password=config["password"],
            database=config["database"],
        )
        cursor = conn.cursor()

        cursor.execute("""
            SELECT COUNT(*)
            FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_type = 'BASE TABLE'
        """)

        count = cursor.fetchone()[0]

        cursor.close()
        conn.close()
        return count
    except Exception:
        return 0


def drop_database(config: dict) -> None:
    """Löscht die Datenbank komplett."""
    conn = psycopg2.connect(
        host=config["host"],
        port=config["port"],
        user=config["user"],
        password=config["password"],
        database="postgres",
    )
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)

    cursor = conn.cursor()

    try:
        # Verbindungen zur Datenbank trennen
        cursor.execute(f"""
            SELECT pg_terminate_backend(pg_stat_activity.pid)
            FROM pg_stat_activity
            WHERE pg_stat_activity.datname = '{config["database"]}'
            AND pid <> pg_backend_pid()
        """)

        # Datenbank löschen
        cursor.execute(f'DROP DATABASE IF EXISTS "{config["database"]}"')
        print(f"✓ Datenbank '{config['database']}' erfolgreich gelöscht")
    except Exception as e:
        print(f"❌ Fehler beim Löschen der Datenbank: {e}")
        raise
    finally:
        cursor.close()
        conn.close()


def main() -> None:
    """Hauptfunktion."""
    print("=" * 60)
    print("ArchiScribe - Datenbank löschen")
    print("=" * 60)
    print()

    # .env laden
    load_env()
    config = get_db_config()

    print("🔗 Ziel-Datenbank:")
    print(f"   Host: {config['host']}")
    print(f"   Port: {config['port']}")
    print(f"   Datenbank: {config['database']}")
    print(f"   User: {config['user']}")
    print()

    # Prüfen ob Datenbank existiert
    if not check_database_exists(config):
        print(f"ℹ️  Datenbank '{config['database']}' existiert nicht.")
        print("   Nichts zu löschen.")
        sys.exit(0)

    # Tabellenanzahl anzeigen
    table_count = get_table_count(config)
    print(f"📊 Gefundene Tabellen: {table_count}")
    print()

    # Warnung anzeigen
    print("⚠️  ═════════════════════════════════════════════════════")
    print("    WARNUNG: Dieser Vorgang löscht die komplette Datenbank!")
    print("    Alle Tabellen und Daten werden unwiderruflich gelöscht.")
    print("    Dies kann NICHT rückgängig gemacht werden!")
    print("⚠️  ═════════════════════════════════════════════════════")
    print()

    # Bestätigungswort generieren und abfragen
    confirmation_word = generate_confirmation_word()
    print(f"🔐 Zur Bestätigung gib bitte folgendes Wort ein: {confirmation_word}")
    print()

    user_input = input("Bestätigungswort: ").strip().upper()

    if user_input != confirmation_word:
        print()
        print("❌ Bestätigung fehlgeschlagen. Falsches Wort eingegeben.")
        print("   Datenbank wurde NICHT gelöscht.")
        sys.exit(1)

    print()
    print("⏳ Lösche Datenbank...")
    drop_database(config)
    print()
    print("✅ Datenbank erfolgreich gelöscht!")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ Abbruch durch Benutzer. Datenbank wurde NICHT gelöscht.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Fehler: {e}")
        sys.exit(1)
