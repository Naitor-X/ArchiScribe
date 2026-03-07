#!/usr/bin/env python3
"""
Leert alle Unterordner des konfigurierten FILES_BASE_PATH.

Verwendung:
    python tools/clean_files.py [--dry-run] [folders...]

Optionen:
    --dry-run    Zeigt nur an, welche Dateien gelöscht würden, ohne sie zu löschen
    folders      Optional: Spezifische Ordner leeren (inbox, processing, archive, error)
                 Ohne Angabe werden alle Ordner geleert

Beispiele:
    python tools/clean_files.py                    # Alle Ordner leeren
    python tools/clean_files.py --dry-run          # Alle Ordner anzeigen (nicht löschen)
    python tools/clean_files.py inbox processing   # Nur inbox und processing leeren
"""

import argparse
import shutil
import sys
from pathlib import Path

# Pfad für Imports anpassen
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import settings


# Verfügbare Ordner mit Beschreibung
FOLDER_CONFIG = {
    "inbox": {
        "path": settings.inbox_path,
        "description": "Eingehende PDFs (Watchdog-Überwachung)",
    },
    "processing": {
        "path": settings.processing_path,
        "description": "Laufende Verarbeitungen",
    },
    "archive": {
        "path": settings.archive_path,
        "description": "Verarbeitete Dateien",
    },
    "error": {
        "path": settings.error_path,
        "description": "Fehlgeschlagene Verarbeitungen",
    },
}


def count_files(folder_path: Path) -> int:
    """Zählt alle Dateien in einem Ordner (rekursiv)."""
    if not folder_path.exists():
        return 0
    return sum(1 for _ in folder_path.rglob("*") if _.is_file())


def get_total_size(folder_path: Path) -> int:
    """Berechnet die Gesamtgröße eines Ordners in Bytes."""
    if not folder_path.exists():
        return 0
    return sum(f.stat().st_size for f in folder_path.rglob("*") if f.is_file())


def format_size(size_bytes: int) -> str:
    """Formatiert Bytes in lesbare Größe."""
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


def clean_folder(folder_path: Path, dry_run: bool = False) -> tuple[int, int]:
    """
    Leert einen Ordner (behält den Ordner selbst bei).

    Returns:
        Tuple aus (gelöschte Dateien, gelöschte Bytes)
    """
    if not folder_path.exists():
        return 0, 0

    file_count = 0
    total_size = 0

    # Alle Unterordner und Dateien sammeln
    items = list(folder_path.iterdir())

    for item in items:
        if item.is_file():
            file_count += 1
            total_size += item.stat().st_size
            if not dry_run:
                item.unlink()
        elif item.is_dir():
            # Für Unterordner: Dateien zählen
            sub_files = count_files(item)
            sub_size = get_total_size(item)
            file_count += sub_files
            total_size += sub_size
            if not dry_run:
                shutil.rmtree(item)

    return file_count, total_size


def main():
    parser = argparse.ArgumentParser(
        description="Leert alle Unterordner des konfigurierten FILES_BASE_PATH",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Beispiele:
  python tools/clean_files.py                    # Alle Ordner leeren
  python tools/clean_files.py --dry-run          # Nur anzeigen
  python tools/clean_files.py inbox processing   # Nur spezifische Ordner
        """,
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Zeigt nur an, was gelöscht würde, ohne zu löschen",
    )
    parser.add_argument(
        "folders",
        nargs="*",
        choices=list(FOLDER_CONFIG.keys()) + [[]],
        help="Spezifische Ordner (leer = alle)",
    )

    args = parser.parse_args()
    folders_to_clean = args.folders if args.folders else list(FOLDER_CONFIG.keys())

    print(f"Basis-Pfad: {settings.files_path}")
    print(f"Modus: {'DRY-RUN (nichts wird gelöscht)' if args.dry_run else 'LÖSCHEN'}")
    print("-" * 60)

    total_files = 0
    total_size = 0

    for folder_name in folders_to_clean:
        config = FOLDER_CONFIG[folder_name]
        folder_path = config["path"]

        file_count = count_files(folder_path)
        folder_size = get_total_size(folder_path)

        print(f"\n📁 {folder_name}/")
        print(f"   Pfad: {folder_path}")
        print(f"   Beschreibung: {config['description']}")
        print(f"   Dateien: {file_count} ({format_size(folder_size)})")

        if file_count > 0:
            deleted_files, deleted_size = clean_folder(folder_path, args.dry_run)
            total_files += deleted_files
            total_size += deleted_size

            if args.dry_run:
                print(f"   ⚠️  Würde löschen: {deleted_files} Dateien ({format_size(deleted_size)})")
            else:
                print(f"   ✅ Gelöscht: {deleted_files} Dateien ({format_size(deleted_size)})")
        else:
            print("   ℹ️  Ordner ist bereits leer")

    print("\n" + "=" * 60)
    if args.dry_run:
        print(f"Gesamt: {total_files} Dateien würden gelöscht ({format_size(total_size)})")
    else:
        print(f"✅ Fertig: {total_files} Dateien gelöscht ({format_size(total_size)})")


if __name__ == "__main__":
    main()
