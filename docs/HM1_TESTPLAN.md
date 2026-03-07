# Hauptmodul 1: Vollständiger Testplan für KI-gestützte Tests

## Ziel

Dieser Testplan ermöglicht einer KI, systematisch alle Funktionen des Hauptmodul 1 zu testen,
Edge Cases zu validieren und die Anwendung "beinahe" bugfrei zu bekommen.

---

## Test-Voraussetzungen

### 1. Umgebung vorbereiten
```bash
# Backend-Umgebung aktivieren
cd backend && source venv/bin/activate

# Dependencies sicherstellen
pip install -r requirements.txt

# PostgreSQL läuft und ist erreichbar
# .env ist korrekt konfiguriert
# OpenRouter API-Key ist gesetzt
```

### 2. Test-Reset durchführen
Vor jedem Testdurchlauf:
```bash
# Datenbank zurücksetzen (nur Test-Tabellen)
python3 -c "
import asyncio
from app.database import init_db_pool, close_db_pool, get_connection

async def reset():
    await init_db_pool()
    async with get_connection() as conn:
        await conn.execute('DELETE FROM project_rooms')
        await conn.execute('DELETE FROM ai_extractions')
        await conn.execute('DELETE FROM project_history')
        await conn.execute('DELETE FROM projects')
        print('DB zurückgesetzt')
    await close_db_pool()

asyncio.run(reset())
"

# Datei-Ordner bereinigen
rm -rf files/processing/*
rm -rf files/archive/test-tenant/*
rm -rf files/error/*
# inbox/ NICHT löschen - dort liegen die Test-PDFs
```

---

## Modul 1.1: Backend-Infrastruktur

### Test 1.1.1: Health-Check Endpoint
```python
# Test: GET /health
import httpx

async def test_health_check():
    async with httpx.AsyncClient() as client:
        response = await client.get("http://localhost:8000/health")

        # Erwartet: 200 OK
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "healthy"
        assert "queue" in data
        assert "db_connected" in data
```

**Edge Cases:**
- [ ] Server nicht erreichbar → Timeout-Handling
- [ ] DB-Verbindung getrennt → Status sollte "degraded" sein
- [ ] Queue voll → Queue-Statistiken korrekt

### Test 1.1.2: Konfiguration laden
```python
from app.config import settings

def test_config():
    # Alle Pflicht-Variablen gesetzt?
    assert settings.openrouter_api_key is not None
    assert settings.database_url is not None
    assert settings.test_tenant_id is not None

    # Default-Werte korrekt?
    assert settings.max_file_size_mb == 50
    assert settings.openrouter_timeout == 120
```

**Edge Cases:**
- [ ] API-Key fehlt → Sollte Fehler beim Startup werfen
- [ ] Ungültige DB-URL → Sollte Fehler beim Startup werfen
- [ ] Ungültiger Timeout-Wert (negativ/String) → Validierung

### Test 1.1.3: Logging-System
```python
from app.logger import logger

def test_logging():
    # Verschiedene Log-Level testen
    logger.debug("Debug-Test")
    logger.info("Info-Test")
    logger.warning("Warning-Test")
    logger.error("Error-Test")

    # Prüfen ob Logs geschrieben werden
    # (je nach Konfiguration in Datei oder Console)
```

**Edge Cases:**
- [ ] Unicode in Log-Nachrichten (Emojis, Umlaute)
- [ ] Sehr lange Log-Nachrichten (>10KB)
- [ ] Log-Verzeichnis nicht beschreibbar

### Test 1.1.4: Exception-Hierarchy
```python
from app.exceptions import (
    ArchiScribeException,
    DateiNichtGefunden,
    UngueltigesDateiformat,
    KIExtraktionFehlgeschlagen,
    DatenbankFehler,
)

def test_exceptions():
    # Vererbung prüfen
    assert issubclass(DateiNichtGefunden, ArchiScribeException)
    assert issubclass(UngueltigesDateiformat, ArchiScribeException)

    # Exception mit Message
    exc = DateiNichtGefunden("/pfad/zur/datei.pdf")
    assert "nicht gefunden" in str(exc).lower()
```

---

## Modul 1.2: Datei-Management

### Test 1.2.1: Ordnerstruktur erstellen
```python
from app.file_utils import ensure_directories
from app.config import settings
from pathlib import Path

def test_ensure_directories():
    ensure_directories()

    assert settings.inbox_path.exists()
    assert settings.processing_path.exists()
    assert settings.archive_path.exists()
    assert settings.error_path.exists()
```

**Edge Cases:**
- [ ] Ordner bereits vorhanden → Kein Fehler
- [ ] Keine Schreibrechte → Exception mit klarem Hinweis
- [ ] Symlink als Ordner → Korrekte Behandlung

### Test 1.2.2: PDF-Validierung
```python
from app.file_utils import validate_pdf_file
from app.exceptions import UngueltigesDateiformat, DateiNichtGefunden
from pathlib import Path

def test_validate_pdf():
    # Gültige PDF
    validate_pdf_file(Path("files/Form2.pdf"))  # Keine Exception

    # Edge Cases
    # Nicht existierende Datei
    try:
        validate_pdf_file(Path("nicht_vorhanden.pdf"))
        assert False, "Sollte DateiNichtGefunden werfen"
    except DateiNichtGefunden:
        pass

    # Keine PDF (falsche Endung)
    try:
        validate_pdf_file(Path("requirements.txt"))
        assert False, "Sollte UngueltigesDateiformat werfen"
    except UngueltigesDateiformat:
        pass

    # Datei zu groß (>50MB)
    # (Muss künstlich erzeugt werden oder Test-Config anpassen)
```

**Edge Cases:**
- [ ] Datei mit .pdf-Endung aber kein PDF-Inhalt (Magic-Bytes prüfen)
- [ ] Leere PDF-Datei (0 Bytes)
- [ ] PDF mit nur Header (%PDF-1.4) aber kein Inhalt
- [ ] Beschädigte PDF (nur erster Teil)
- [ ] PDF mit Passwortschutz
- [ ] Dateiname mit Sonderzeichen (äöü, Leerzeichen, Klammern)
- [ ] Sehr langer Dateiname (>255 Zeichen)
- [ ] Unicode im Dateinamen

### Test 1.2.3: Datei-Hash
```python
from app.file_utils import calculate_file_hash
from pathlib import Path

def test_file_hash():
    hash1 = calculate_file_hash(Path("files/Form2.pdf"))
    hash2 = calculate_file_hash(Path("files/Form2.pdf"))

    # Gleiche Datei = gleicher Hash
    assert hash1 == hash2

    # Hash-Länge (SHA-256 = 64 Hex-Zeichen)
    assert len(hash1) == 64
```

**Edge Cases:**
- [ ] Leere Datei → Hash sollte definiert sein
- [ ] Datei während Hash-Berechnung ändern → Sollte nicht crashen
- [ ] Sehr große Datei (>100MB) → Performance prüfen

### Test 1.2.4: Processing-Ordner
```python
from app.file_utils import get_processing_folder
import uuid

def test_processing_folder():
    process_id = uuid.uuid4()
    folder = get_processing_folder(process_id)

    assert folder.exists()
    assert folder.name == str(process_id)
```

### Test 1.2.5: Archiv-Ordner
```python
from app.file_utils import get_archive_folder
import uuid

def test_archive_folder():
    tenant_id = uuid.uuid4()
    project_id = uuid.uuid4()
    folder = get_archive_folder(tenant_id, project_id)

    assert folder.exists()
    assert str(tenant_id) in str(folder)
    assert str(project_id) in str(folder)
```

### Test 1.2.6: Error-Ordner
```python
from app.file_utils import get_error_folder
from pathlib import Path

def test_error_folder():
    folder = get_error_folder("test_file.pdf")

    assert folder.exists()
    assert "test_file" in str(folder)

    # Sonderzeichen im Dateinamen
    folder2 = get_error_folder("test (1) äöü.pdf")
    assert folder2.exists()
```

### Test 1.2.7: Datei-Verschiebung
```python
import asyncio
from pathlib import Path
import uuid
from app.file_utils import (
    move_file_to_processing,
    move_to_archive,
    move_to_error,
    cleanup_processing_folder,
)

async def test_file_moves():
    # Test-Datei vorbereiten
    test_pdf = Path("files/inbox/test_move.pdf")
    test_pdf.write_bytes(b"%PDF-1.4\ntest content")

    process_id = uuid.uuid4()

    # Nach Processing verschieben
    moved = move_file_to_processing(test_pdf, process_id)
    assert moved.exists()
    assert not test_pdf.exists()  # Original weg

    # Cleanup
    cleanup_processing_folder(process_id)
    assert not moved.parent.exists()
```

**Edge Cases:**
- [ ] Processing-Ordner bereits vorhanden
- [ ] Ziel-Datei bereits vorhanden → Überschreiben?
- [ ] Keine Schreibrechte im Zielordner
- [ ] Disk full während Verschiebung

---

## Modul 1.3: PDF-Konvertierung

### Test 1.3.1: PDF-zu-Bild Konvertierung
```python
from app.pdf_converter import pdf_zu_bilder, get_pdf_info
from pathlib import Path

def test_pdf_conversion():
    pdf_path = Path("files/Form2.pdf")

    # PDF-Info ohne Konvertierung
    info = get_pdf_info(pdf_path)
    assert info["seiten"] == 4
    assert info["size_bytes"] > 0

    # Konvertierung
    output_folder = Path("files/processing/test_conversion")
    output_folder.mkdir(parents=True, exist_ok=True)

    bilder = pdf_zu_bilder(pdf_path, output_folder)

    assert len(bilder) == 4
    for bild in bilder:
        assert bild.suffix == ".png"
        assert bild.exists()
```

**Edge Cases:**
- [ ] Leere PDF (0 Seiten)
- [ ] 1-seitige PDF
- [ ] Sehr große PDF (>20 Seiten)
- [ ] PDF mit verschiedenen Seitengrößen (A4, A3, Letter)
- [ ] PDF mit querformatigen Seiten
- [ ] PDF mit gemischten Formaten
- [ ] PDF mit Bildern vs. Text
- [ ] Farbig vs. Schwarz-Weiß
- [ ] Niedrige DPI vs. hohe DPI im Original
- [ ] PDF mit Transparenz
- [ ] PDF mit Vektoren vs. Rasterbildern

### Test 1.3.2: Bild-Optimierung
```python
from app.pdf_converter import _optimiere_bild
from PIL import Image
from pathlib import Path

def test_image_optimization():
    # Großes Bild erstellen
    large_img = Image.new("RGB", (4000, 6000), color="red")
    output_path = Path("files/processing/test_optimized.png")

    _optimiere_bild(large_img, output_path)

    # Prüfen: Größe sollte reduziert sein
    result = Image.open(output_path)
    assert result.width <= 2000
    assert result.height <= 3000
```

**Edge Cases:**
- [ ] Bereits kleines Bild (keine Änderung nötig)
- [ ] Sehr kleines Bild (<100px)
- [ ] Extrem großes Bild (>10000px)
- [ ] Schwarz-Weiß Bild (Graustufen)
- [ ] RGBA mit Transparenz

### Test 1.3.3: Base64-Encoding
```python
from app.pdf_converter import bild_zu_base64
from pathlib import Path
import base64

def test_base64():
    # Test-Bild
    test_img = Path("files/processing/test.png")
    if not test_img.exists():
        from PIL import Image
        img = Image.new("RGB", (100, 100), color="blue")
        img.save(test_img)

    data_uri = bild_zu_base64(test_img)

    # Prüfen: Data-URI Format
    assert data_uri.startswith("data:image/png;base64,")
    assert len(data_uri) > 100

    # Dekodierbar?
    base64_part = data_uri.split(",")[1]
    decoded = base64.b64decode(base64_part)
    assert len(decoded) > 0
```

### Test 1.3.4: Komplette Vision-Konvertierung
```python
from app.pdf_converter import konvertiere_pdf_fuer_vision
from pathlib import Path

def test_vision_conversion():
    pdf_path = Path("files/Form2.pdf")
    output_folder = Path("files/processing/test_vision")
    output_folder.mkdir(parents=True, exist_ok=True)

    result = konvertiere_pdf_fuer_vision(
        pdf_pfad=pdf_path,
        output_ordner=output_folder,
        mit_base64=True,
    )

    assert result.seiten_anzahl == 4
    assert len(result.bild_pfade) == 4
    assert len(result.base64_bilder) == 4

    for b64 in result.base64_bilder:
        assert b64.startswith("data:image/png;base64,")
```

**Edge Cases:**
- [ ] PDF nicht gefunden
- [ ] Output-Ordner nicht beschreibbar
- [ ] mit_base64=False (keine Base64-Bilder)
- [ ] Sehr große PDF mit vielen Seiten (Memory)

---

## Modul 1.4: OpenRouter-Integration

### Test 1.4.1: API-Client Initialisierung
```python
from app.openrouter_client import OpenRouterClient
from app.config import settings

def test_client_init():
    client = OpenRouterClient(
        api_key=settings.openrouter_api_key,
        model=settings.openrouter_model,
    )

    assert client.api_key is not None
    assert client.model is not None
    assert client.timeout == 120
```

### Test 1.4.2: KI-Extraktion (echter API-Call)
```python
import asyncio
from app.openrouter_client import extract_form_data
from app.pdf_converter import konvertiere_pdf_fuer_vision
from pathlib import Path

async def test_extraction():
    # PDF vorbereiten
    pdf_path = Path("files/Form2.pdf")
    output_folder = Path("files/processing/test_extraction")
    output_folder.mkdir(parents=True, exist_ok=True)

    konvertierung = konvertiere_pdf_fuer_vision(
        pdf_pfad=pdf_path,
        output_ordner=output_folder,
        mit_base64=True,
    )

    # Extraktion durchführen
    result = await extract_form_data(konvertierung.base64_bilder)

    # Pflichtfelder prüfen
    assert result.client_name is not None
    assert result.address is not None
    assert len(result.rooms) > 0

    # Enum-Werte prüfen
    assert result.project_type in [
        "Neubau", "Bauen im Bestand", "Umbau im Inneren",
        "Sanierung/Modernis.", "Zubau/Anbau", "Aufstockung",
        "noch unklar", "Sonstiges"
    ]
```

**Edge Cases:**
- [ ] API-Key ungültig → 401 Fehler mit klarer Meldung
- [ ] Rate-Limit erreicht → 429 mit Retry-After
- [ ] API-Timeout → 504 nach 120s
- [ ] Leere Base64-Liste
- [ ] Nur 1 Bild
- [ ] Sehr viele Bilder (>10)
- [ ] Ungültiges Base64
- [ ] API gibt kein JSON zurück
- [ ] API gibt unvollständiges JSON zurück
- [ ] API gibt Markdown mit JSON-Block zurück
- [ ] API gibt nur Text zurück

### Test 1.4.3: Retry-Logik
```python
import asyncio
from unittest.mock import patch, AsyncMock
from app.openrouter_client import extract_form_data

async def test_retry_logic():
    # Mock: Erster Aufruf fehlschlägt, zweiter erfolgreich
    call_count = 0

    async def mock_request(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise Exception("Temporary error")
        return {"client_name": "Test"}

    # Test mit Mock
    # (Echte Implementierung mit pytest-httpx oder similar)
```

**Edge Cases:**
- [ ] Alle 3 Versuche fehlschlagen
- [ ] Exponential-Backoff Timing prüfen
- [ ] Retry-After Header wird respektiert

### Test 1.4.4: JSON-Extraktion
```python
from app.openrouter_client import _extract_json_from_response

def test_json_extraction():
    # Fall 1: Reines JSON
    json1 = '{"client_name": "Test"}'
    assert _extract_json_from_response(json1) is not None

    # Fall 2: JSON im Markdown-Code-Block
    json2 = '''
    Hier ist das Ergebnis:
    ```json
    {"client_name": "Test"}
    ```
    '''
    assert _extract_json_from_response(json2) is not None

    # Fall 3: JSON ohne Sprachangabe
    json3 = '''
    ```
    {"client_name": "Test"}
    ```
    '''
    assert _extract_json_from_response(json3) is not None

    # Fall 4: Kein JSON
    json4 = "Das ist kein JSON"
    result = _extract_json_from_response(json4)
    assert result is None
```

---

## Modul 1.5: Daten-Mapping & Validierung

### Test 1.5.1: Enum-Normalisierung
```python
from app.mapping import normalize_enum, VALID_PROJECT_TYPE

def test_enum_normalization():
    # Exakter Match
    assert normalize_enum("Neubau", VALID_PROJECT_TYPE, "test") == "Neubau"

    # Groß-/Kleinschreibung ignorieren
    assert normalize_enum("neubau", VALID_PROJECT_TYPE, "test") == "Neubau"
    assert normalize_enum("NEUBAU", VALID_PROJECT_TYPE, "test") == "Neubau"

    # Varianten
    assert normalize_enum("sanierung", VALID_PROJECT_TYPE, "test") == "Sanierung/Modernis."
    assert normalize_enum("Sanierung/Modernisierung", VALID_PROJECT_TYPE, "test") == "Sanierung/Modernis."

    # Ungültiger Wert
    assert normalize_enum("UngültigerWert123", VALID_PROJECT_TYPE, "test") is None

    # None
    assert normalize_enum(None, VALID_PROJECT_TYPE, "test") is None
```

**Edge Cases:**
- [ ] Leerer String
- [ ] Nur Leerzeichen
- [ | Unicode-Zeichen
- [ ] Sehr langer String
- [ ] Zahlen als String

### Test 1.5.2: Datum-Parsing
```python
from app.mapping import parse_date
from datetime import date

def test_date_parsing():
    # ISO-Format
    assert parse_date("2026-03-07", "test") == date(2026, 3, 7)

    # Deutsches Format
    assert parse_date("07.03.2026", "test") == date(2026, 3, 7)

    # Ungültiges Format
    assert parse_date("07/03/2026", "test") is None
    assert parse_date("nicht-ein-datum", "test") is None
    assert parse_date("", "test") is None
    assert parse_date(None, "test") is None
```

**Edge Cases:**
- [ ] Schaltjahr (29.02.2024)
- [ ] Ungültiges Datum (31.02.2026)
- [ ] Altes Datum (01.01.1900)
- [ ] Zukünftiges Datum (01.01.2100)
- [ ] Nur Jahr (2026)
- [ ] Jahr-Monat (2026-03)

### Test 1.5.3: Decimal-Parsing
```python
from app.mapping import parse_decimal
from decimal import Decimal

def test_decimal_parsing():
    # Integer
    assert parse_decimal(100, "test") == Decimal("100")

    # Float
    assert parse_decimal(100.5, "test") == Decimal("100.5")

    # String mit Punkt
    assert parse_decimal("100.50", "test") == Decimal("100.50")

    # String mit Komma (deutsch)
    assert parse_decimal("100,50", "test") == Decimal("100.50")

    # Mit Tausendertrennzeichen (Leerzeichen)
    assert parse_decimal("1 000,50", "test") == Decimal("1000.50")

    # Ungültig
    assert parse_decimal("abc", "test") is None
    assert parse_decimal(None, "test") is None
```

**Edge Cases:**
- [ ] Negative Zahlen
- [ ] Sehr große Zahlen (>1 Milliarde)
- [ ] Sehr kleine Zahlen (<0.01)
- [ ] Wissenschaftliche Notation (1e10)
- [ ] Mehrere Kommas

### Test 1.5.4: Plausibilitätsprüfung
```python
from app.mapping import validate_plausibility, MappedProject
from decimal import Decimal
from datetime import date

def test_plausibility():
    # Gültiges Projekt
    project = MappedProject()
    warnings = validate_plausibility(project)
    assert len(warnings) == 0

    # Negatives Budget
    project.budget = Decimal("-1000")
    warnings = validate_plausibility(project)
    assert any("Budget" in w for w in warnings)

    # Sehr großes Grundstück
    project.budget = Decimal("100000")
    project.plot_size_m2 = Decimal("200000")  # 20 Hektar
    warnings = validate_plausibility(project)
    assert any("Grundstücksgröße" in w for w in warnings)

    # Sonstiges ohne Details
    project.plot_size_m2 = Decimal("500")
    project.topography = "Sonstiges"
    project.topography_other = None
    warnings = validate_plausibility(project)
    assert any("Sonstiges" in w for w in warnings)
```

**Edge Cases:**
- [ ] Alle "Sonstiges"-Felder ohne Details
- [ ] Baujahr in sehr weiter Zukunft (>5 Jahre)
- [ ] Budget = 0
- [ ] Grundstücksgröße = 0

### Test 1.5.5: Komplettes Mapping
```python
from app.mapping import map_extraction_to_project
from app.schemas.extraction import ExtractionResult, RoomSchema

def test_full_mapping():
    extraction = ExtractionResult(
        client_name="Max Mustermann",
        address="Musterstraße 1, 12345 Musterstadt",
        phone="+49 123 456789",
        email="max@example.com",
        date="2026-03-07",
        project_type="Neubau",
        building_type="EFH",
        rooms=[
            RoomSchema(
                room_type="Wohnzimmer",
                quantity=1,
                size_m2=30.5,
                special_requirements="Große Fenster"
            )
        ]
    )

    project, validation = map_extraction_to_project(
        extraction,
        pdf_path="/test/path.pdf",
        page_paths=["/test/page1.png"]
    )

    assert project.client_name == "Max Mustermann"
    assert project.project_type == "Neubau"
    assert project.building_type == "EFH"
    assert len(project.rooms) == 1
    assert validation.is_valid
```

---

## Modul 1.6: Datenbank-Integration

### Test 1.6.1: Connection-Pool
```python
import asyncio
from app.database import init_db_pool, close_db_pool, get_connection

async def test_db_pool():
    await init_db_pool()

    async with get_connection() as conn:
        result = await conn.fetchval("SELECT 1")
        assert result == 1

    await close_db_pool()
```

**Edge Cases:**
- [ ] DB nicht erreichbar
- [ ] Falsche Credentials
- [ ] DB existiert nicht
- [ ] Pool-Größe erreicht (max_connections)
- [ ] Connection-Timeout

### Test 1.6.2: Projekt speichern
```python
import asyncio
from app.database import init_db_pool, close_db_pool, save_project
from app.mapping import MappedProject
from decimal import Decimal
import uuid

async def test_save_project():
    await init_db_pool()

    project = MappedProject(
        client_name="Test Client",
        address="Test Address",
        project_type="Neubau",
        budget=Decimal("500000"),
        rooms=[
            {
                "room_type": "Wohnzimmer",
                "quantity": 1,
                "size_m2": Decimal("30"),
            }
        ]
    )

    tenant_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
    raw_json = {"client_name": "Test Client"}

    project_id = await save_project(
        project=project,
        tenant_id=tenant_id,
        raw_json=raw_json,
    )

    assert project_id is not None
    assert isinstance(project_id, uuid.UUID)

    await close_db_pool()
```

**Edge Cases:**
- [ ] Projekt mit minimalen Daten (nur client_name)
- [ ] Projekt ohne Räume
- [ ] Viele Räume (>20)
- [ ] Ungültige Tenant-ID
- [ ] Enum-Wert nicht in DB-Enum
- [ ] SQL-Injection-Versuch in Strings
- [ ] Unicode in Textfeldern
- [ ] Sehr langer Text (>5000 Zeichen)

### Test 1.6.3: Projekt laden
```python
import asyncio
from app.database import init_db_pool, close_db_pool, get_project_by_id, save_project
from app.mapping import MappedProject
import uuid

async def test_load_project():
    await init_db_pool()

    # Erst speichern
    project = MappedProject(client_name="Load Test")
    tenant_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
    project_id = await save_project(project, tenant_id, {})

    # Dann laden
    loaded = await get_project_by_id(project_id)

    assert loaded is not None
    assert loaded["client_name"] == "Load Test"
    assert loaded["status_id"] == "raw_extracted"

    await close_db_pool()
```

**Edge Cases:**
- [ ] Projekt nicht vorhanden
- [ ] Projekt ohne Räume
- [ ] Projekt ohne AI-Extraktion
- [ ] Gelöschtes Projekt

### Test 1.6.4: Transaktionssicherheit
```python
import asyncio
from app.database import init_db_pool, close_db_pool, get_connection
from app.mapping import MappedProject
import uuid

async def test_transaction_rollback():
    await init_db_pool()

    tenant_id = uuid.UUID("00000000-0000-0000-0000-000000000001")

    # Transaktion mit Fehler simulieren
    try:
        async with get_connection() as conn:
            async with conn.transaction():
                # Projekt einfügen
                await conn.execute(
                    """
                    INSERT INTO projects (id, tenant_id, client_name)
                    VALUES ($1, $2, $3)
                    """,
                    uuid.uuid4(), tenant_id, "Rollback Test"
                )

                # Fehler auslösen
                raise Exception("Simulierter Fehler")
    except Exception:
        pass

    # Prüfen: Projekt sollte NICHT in DB sein
    async with get_connection() as conn:
        result = await conn.fetchval(
            "SELECT COUNT(*) FROM projects WHERE client_name = $1",
            "Rollback Test"
        )
        assert result == 0

    await close_db_pool()
```

---

## Modul 1.7: Workflow-Orchestrierung

### Test 1.7.1: Processing-Job erstellen
```python
from app.processing import ProcessingJob, ProcessingStatus, create_job
from pathlib import Path
import uuid

def test_job_creation():
    process_id = uuid.uuid4()
    pdf_path = Path("files/Form2.pdf")

    job = create_job(
        process_id=process_id,
        pdf_path=pdf_path,
        file_hash="abc123",
        original_filename="Form2.pdf",
    )

    assert job.status == ProcessingStatus.QUEUED
    assert job.original_filename == "Form2.pdf"
    assert job.started_at is None
```

### Test 1.7.2: Status-Updates
```python
from app.processing import ProcessingJob, ProcessingStatus
from pathlib import Path
import uuid

def test_status_updates():
    job = ProcessingJob(
        job_id=uuid.uuid4(),
        process_id=uuid.uuid4(),
        pdf_path=Path("test.pdf"),
        file_hash="abc",
        original_filename="test.pdf",
    )

    # Status ändern
    job.update_status(ProcessingStatus.CONVERTING)
    assert job.status == ProcessingStatus.CONVERTING
    assert job.started_at is not None

    job.update_status(ProcessingStatus.COMPLETED)
    assert job.completed_at is not None
```

### Test 1.7.3: Komplette Pipeline (Integration Test)
```python
import asyncio
from pathlib import Path
from app.processing import (
    init_processing,
    shutdown_processing,
    enqueue_pdf,
    get_queue,
)
import uuid
import shutil

async def test_full_pipeline():
    # Test-PDF in inbox kopieren
    test_pdf = Path("files/inbox/test_pipeline.pdf")
    shutil.copy("files/Form2.pdf", test_pdf)

    # Processing initialisieren
    queue = await init_processing(max_concurrent=1)

    # Job einreihen
    process_id = uuid.uuid4()
    job_id = await enqueue_pdf(
        process_id=process_id,
        pdf_path=test_pdf,
        file_hash="test123",
        original_filename="test_pipeline.pdf",
    )

    # Warten bis fertig
    import time
    for _ in range(60):  # Max 60 Sekunden
        result = queue.get_result(job_id)
        if result:
            break
        await asyncio.sleep(1)

    # Ergebnis prüfen
    assert result is not None
    assert result.success
    assert result.project_id is not None

    # Cleanup
    await shutdown_processing()
```

**Edge Cases:**
- [ ] Pipeline mit ungültiger PDF
- [ ] Pipeline mit API-Fehler
- [ ] Pipeline mit DB-Fehler
- [ ] Mehrere gleichzeitige Jobs
- [ ] Job-Abbruch während Verarbeitung

### Test 1.7.4: Queue-Statistiken
```python
import asyncio
from app.processing import init_processing, shutdown_processing, get_queue

async def test_queue_stats():
    await init_processing(max_concurrent=2)
    queue = get_queue()

    stats = {
        "queued": queue._queue.qsize(),
        "active": len(queue._active_jobs),
        "completed": len(queue._completed_jobs),
        "max_concurrent": queue.max_concurrent,
    }

    assert stats["max_concurrent"] == 2

    await shutdown_processing()
```

### Test 1.7.5: Fehlerbehandlung
```python
import asyncio
from pathlib import Path
from app.processing import (
    init_processing,
    shutdown_processing,
    enqueue_pdf,
    get_queue,
)
import uuid

async def test_error_handling():
    # Ungültige PDF erstellen
    invalid_pdf = Path("files/inbox/invalid.pdf")
    invalid_pdf.write_text("Das ist keine PDF")

    await init_processing(max_concurrent=1)
    queue = get_queue()

    process_id = uuid.uuid4()
    job_id = await enqueue_pdf(
        process_id=process_id,
        pdf_path=invalid_pdf,
        file_hash="invalid",
        original_filename="invalid.pdf",
    )

    # Warten bis fertig
    for _ in range(30):
        result = queue.get_result(job_id)
        if result:
            break
        await asyncio.sleep(1)

    # Sollte fehlgeschlagen sein
    assert result is not None
    assert not result.success
    assert result.error_message is not None

    # Error-Ordner sollte existieren
    from app.config import settings
    error_folders = list(settings.error_path.glob("*"))
    assert len(error_folders) > 0

    await shutdown_processing()
```

---

## End-to-End Tests

### E2E Test 1: Vollständige Verarbeitung
```python
import asyncio
import shutil
from pathlib import Path
from app.config import settings

async def test_e2e_full_processing():
    """
    Kompletter Testdurchlauf:
    1. PDF in inbox kopieren
    2. Watchdog erkennt Datei
    3. Verarbeitung läuft
    4. Projekt in DB
    5. Dateien im Archiv
    """

    # 1. Test-PDF in inbox
    test_pdf = Path("files/inbox/e2e_test.pdf")
    shutil.copy("files/Form2.pdf", test_pdf)

    # 2. Warten auf Verarbeitung (60s Timeout)
    # (Watchdog muss laufen oder manuell triggern)

    # 3. Prüfen: Projekt in DB
    from app.database import get_connection, init_db_pool
    await init_db_pool()

    async with get_connection() as conn:
        project = await conn.fetchrow(
            "SELECT * FROM projects WHERE client_name IS NOT NULL ORDER BY created_at DESC LIMIT 1"
        )

    assert project is not None
    project_id = project["id"]

    # 4. Prüfen: AI-Extraktion vorhanden
    async with get_connection() as conn:
        extraction = await conn.fetchrow(
            "SELECT * FROM ai_extractions WHERE project_id = $1",
            project_id
        )

    assert extraction is not None
    assert extraction["raw_json"] is not None

    # 5. Prüfen: Räume vorhanden
    async with get_connection() as conn:
        rooms = await conn.fetch(
            "SELECT * FROM project_rooms WHERE project_id = $1",
            project_id
        )

    assert len(rooms) > 0

    # 6. Prüfen: Dateien im Archiv
    archive_folder = settings.archive_path / str(project["tenant_id"]) / str(project_id)
    assert archive_folder.exists()

    files = list(archive_folder.glob("*"))
    assert any(f.suffix == ".pdf" for f in files)
    assert any(f.suffix == ".png" for f in files)
```

### E2E Test 2: API-Endpunkte
```python
import httpx
import asyncio

async def test_api_endpoints():
    """Testet alle API-Endpunkte."""

    async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
        # Health Check
        response = await client.get("/health")
        assert response.status_code == 200

        # Queue Stats
        response = await client.get("/queue/stats")
        assert response.status_code == 200
        data = response.json()
        assert "queued" in data
        assert "active" in data

        # Jobs auflisten
        response = await client.get("/jobs")
        assert response.status_code == 200

        # Re-trigger (ohne Datei sollte fehlschlagen)
        response = await client.post("/jobs/retrigger", json={})
        assert response.status_code in [400, 404, 422]
```

---

## Edge Case Matrix

### Datei-Edge-Cases
| Testfall | Erwartetes Verhalten |
|----------|---------------------|
| Leere PDF | Fehler: Ungültiges PDF |
| Passwortgeschützte PDF | Fehler: Passwortgeschützt |
| 0-Byte-Datei | Fehler: Leere Datei |
| Datei > 50MB | Fehler: Datei zu groß |
| Unicode-Dateiname | Funktioniert (sanitized) |
| Dateiname > 255 Zeichen | Gekürzt/sanitized |
| .pdf aber keine PDF | Fehler: Magic-Bytes |
| Beschädigte PDF | Fehler beim Konvertieren |
| 50 Seiten PDF | Funktioniert (langsam) |

### KI-Edge-Cases
| Testfall | Erwartetes Verhalten |
|----------|---------------------|
| Leere Antwort | Retry, dann Fehler |
| Unvollständiges JSON | Mapping mit Defaults |
| Falsches JSON-Format | Extraktionsversuch |
| Rate-Limit | Retry mit Backoff |
| Timeout | Retry, dann Fehler |
| Ungültiger API-Key | Sofortiger Fehler |
| 429 Too Many Requests | Retry nach Retry-After |

### Datenbank-Edge-Cases
| Testfall | Erwartetes Verhalten |
|----------|---------------------|
| DB nicht erreichbar | Fehler mit klarem Hinweis |
| Ungültige Tenant-ID | Foreign-Key-Fehler |
| SQL-Injection | Sichere Parameter-Übergabe |
| Unicode in Text | Korrekt gespeichert |
| Leere Pflichtfelder | Warnung, kein Fehler |
| Transaktionsfehler | Rollback |

### Concurrency-Edge-Cases
| Testfall | Erwartetes Verhalten |
|----------|---------------------|
| 5 gleichzeitige PDFs | Queue verarbeitet nach max_concurrent |
| Abbruch während Verarbeitung | Cleanup, Error-Archiv |
| Memory-Limit erreicht | Fehler mit Log |

---

## Test-Ausführungsreihenfolge

1. **Unit-Tests** (isoliert, keine externen Dependencies)
   - 1.1.x - Infrastruktur
   - 1.5.x - Mapping (ohne DB)

2. **Integration-Tests** (mit DB, ohne API)
   - 1.2.x - Datei-Management
   - 1.3.x - PDF-Konvertierung
   - 1.6.x - Datenbank

3. **API-Tests** (mit echter KI-API)
   - 1.4.x - OpenRouter

4. **E2E-Tests** (vollständige Pipeline)
   - 1.7.x - Orchestrierung
   - E2E Tests

---

## Test-Report-Format

Nach jedem Testdurchlauf sollte dieser Report erstellt werden:

```markdown
# Test-Report: Hauptmodul 1

**Datum:** YYYY-MM-DD HH:MM
**Dauer:** X Minuten
**Getestet von:** Claude (KI)

## Zusammenfassung
- ✅ Bestanden: X
- ❌ Fehlgeschlagen: Y
- ⚠️ Warnungen: Z

## Details

### 1.1 Backend-Infrastruktur
| Test | Status | Dauer | Notizen |
|------|--------|-------|---------|
| 1.1.1 Health-Check | ✅ | 0.1s | |
| 1.1.2 Config | ✅ | 0.1s | |

### 1.2 Datei-Management
...

## Gefundene Issues
1. [BUG] Beschreibung...
2. [IMPROVEMENT] Beschreibung...

## Empfehlungen
- ...
```

---

## Automatisierter Test-Runner

```python
"""
test_runner_hm1.py - Automatischer Test-Runner für Hauptmodul 1

Verwendung:
    cd backend
    source venv/bin/activate
    python3 test_runner_hm1.py
"""

import asyncio
import sys
from datetime import datetime
from pathlib import Path

# Test-Imports
from app.config import settings
from app.file_utils import ensure_directories
from app.database import init_db_pool, close_db_pool


class TestRunner:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.warnings = 0
        self.results = []

    async def run_all(self):
        """Führt alle Tests aus."""
        print("=" * 60)
        print("HAUTPMODUL 1 TEST-Runner")
        print("=" * 60)
        print(f"Gestartet: {datetime.now()}")
        print()

        # Setup
        ensure_directories()
        await init_db_pool()

        try:
            # Tests ausführen
            await self.test_section("1.1 Backend-Infrastruktur", [
                self.test_1_1_1_health,
                self.test_1_1_2_config,
            ])

            await self.test_section("1.2 Datei-Management", [
                self.test_1_2_1_directories,
                self.test_1_2_2_pdf_validation,
            ])

            # ... weitere Tests

        finally:
            await close_db_pool()

        # Report
        self.print_report()

    async def test_section(self, name, tests):
        print(f"\n--- {name} ---")
        for test in tests:
            await test()

    async def test_1_1_1_health(self):
        """Test 1.1.1: Health-Check"""
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                response = await client.get(f"http://localhost:8000/health", timeout=5)
                if response.status_code == 200:
                    self.pass("1.1.1 Health-Check")
                else:
                    self.fail("1.1.1 Health-Check", f"Status: {response.status_code}")
        except Exception as e:
            self.fail("1.1.1 Health-Check", str(e))

    async def test_1_1_2_config(self):
        """Test 1.1.2: Konfiguration"""
        try:
            assert settings.openrouter_api_key is not None
            assert settings.database_url is not None
            self.pass("1.1.2 Konfiguration")
        except AssertionError as e:
            self.fail("1.1.2 Konfiguration", str(e))

    async def test_1_2_1_directories(self):
        """Test 1.2.1: Ordnerstruktur"""
        try:
            ensure_directories()
            assert settings.inbox_path.exists()
            assert settings.processing_path.exists()
            self.pass("1.2.1 Ordnerstruktur")
        except Exception as e:
            self.fail("1.2.1 Ordnerstruktur", str(e))

    async def test_1_2_2_pdf_validation(self):
        """Test 1.2.2: PDF-Validierung"""
        from app.file_utils import validate_pdf_file
        from app.exceptions import UngueltigesDateiformat

        try:
            # Gültige PDF
            validate_pdf_file(Path("files/Form2.pdf"))
            self.pass("1.2.2 PDF-Validierung (gültig)")
        except Exception as e:
            self.fail("1.2.2 PDF-Validierung", str(e))

    def pass(self, name):
        print(f"  ✅ {name}")
        self.passed += 1
        self.results.append({"name": name, "status": "PASS"})

    def fail(self, name, error):
        print(f"  ❌ {name}: {error}")
        self.failed += 1
        self.results.append({"name": name, "status": "FAIL", "error": error})

    def warn(self, name, message):
        print(f"  ⚠️ {name}: {message}")
        self.warnings += 1

    def print_report(self):
        print("\n" + "=" * 60)
        print("TEST-REPORT")
        print("=" * 60)
        print(f"✅ Bestanden: {self.passed}")
        print(f"❌ Fehlgeschlagen: {self.failed}")
        print(f"⚠️ Warnungen: {self.warnings}")
        print(f"Beendet: {datetime.now()}")


if __name__ == "__main__":
    runner = TestRunner()
    asyncio.run(runner.run_all())
```

---

## Checkliste für KI-Tester

Vor jedem Test:
- [ ] venv aktiviert
- [ ] requirements.txt aktuell
- [ ] .env korrekt konfiguriert
- [ ] PostgreSQL läuft
- [ ] Test-PDF vorhanden (files/Form2.pdf)
- [ ] Server läuft (für API-Tests)

Nach jedem Test:
- [ ] Alle Errors geloggt?
- [ ] Cleanup durchgeführt?
- [ ] DB-Einträge geprüft?
- [ ] Archiv-Dateien geprüft?

---

*Erstellt: 2026-03-07*
*Version: 1.0*
