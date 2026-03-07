#!/usr/bin/env python3
"""
Test-Skript für die OpenRouter-Integration.

Testet die KI-Extraktion mit der Test-PDF /files/inbox/Form2.pdf.

Verwendung:
    source venv/bin/activate
    python test_openrouter.py
"""

import asyncio
import json
import sys
from pathlib import Path

# Backend-Pfad zum sys.path hinzufügen
sys.path.insert(0, str(Path(__file__).parent))

from app.config import settings
from app.logger import logger
from app.pdf_converter import pdf_zu_bilder
from app.openrouter_client import extract_form_data


async def test_extraction():
    """Testet die vollständige Extraktions-Pipeline."""
    # Test-PDF liegt im Hauptordner (nicht inbox, da Watchdog sie verschiebt)
    test_pdf = Path(__file__).parent.parent / "files" / "Form2.pdf"

    # Prüfe ob Test-PDF existiert
    if not test_pdf.exists():
        logger.error(f"Test-PDF nicht gefunden: {test_pdf}")
        print(f"\n❌ Test-PDF nicht gefunden: {test_pdf}")
        return None

    print(f"\n📄 Test-PDF: {test_pdf}")
    print(f"🤖 Modell: {settings.openrouter_model}")
    print(f"🔑 API-Key: {settings.openrouter_api_key[:20]}...")
    print()

    # Schritt 1: PDF zu Bilder konvertieren
    print("📊 Schritt 1: PDF konvertieren...")
    output_ordner = settings.processing_path / "test_extraction"
    output_ordner.mkdir(parents=True, exist_ok=True)

    try:
        bilder = pdf_zu_bilder(test_pdf, output_ordner)
        print(f"   ✓ {len(bilder)} Seite(n) konvertiert")

        # Base64-Encoding für API
        from app.pdf_converter import bild_zu_base64
        base64_bilder = [bild_zu_base64(bild) for bild in bilder]
        print(f"   ✓ {len(base64_bilder)} Base64-Bilder erstellt")
    except Exception as e:
        print(f"   ❌ Konvertierung fehlgeschlagen: {e}")
        return None

    # Schritt 2: KI-Extraktion
    print("\n🧠 Schritt 2: KI-Extraktion...")
    try:
        ergebnis = await extract_form_data(base64_bilder)
        print("   ✓ Extraktion erfolgreich!")
    except Exception as e:
        print(f"   ❌ Extraktion fehlgeschlagen: {e}")
        return None

    # Schritt 3: Ergebnisse anzeigen
    print("\n📋 Extrahierte Daten:")
    print("=" * 50)

    # Wichtige Felder anzeigen
    fields_to_show = [
        ("Bauherr", "client_name"),
        ("Adresse", "address"),
        ("Telefon", "phone"),
        ("E-Mail", "email"),
        ("Grundstück Lage", "plot_location"),
        ("Grundstücksgröße", "plot_size_m2"),
        ("Projektart", "project_type"),
        ("Gebäudetyp", "building_type"),
        ("Bauweise", "construction_method"),
        ("Heizung", "heating_type"),
        ("Budget", "budget"),
        ("Barrierefreiheit", "accessibility"),
    ]

    for label, field in fields_to_show:
        value = getattr(ergebnis, field, None)
        if value is not None:
            print(f"  {label}: {value}")

    # Raumprogramm
    if ergebnis.rooms:
        print(f"\n🏠 Raumprogramm ({len(ergebnis.rooms)} Räume):")
        for room in ergebnis.rooms:
            size_str = f", {room.size_m2}m²" if room.size_m2 else ""
            print(f"   • {room.quantity}x {room.room_type}{size_str}")

    # Vollständiges JSON
    print("\n📄 Vollständiges JSON:")
    print(json.dumps(ergebnis.model_dump(), indent=2, ensure_ascii=False))

    print("\n✅ Test erfolgreich!")
    return ergebnis


if __name__ == "__main__":
    asyncio.run(test_extraction())
