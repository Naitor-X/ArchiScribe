# Backend CLAUDE.md

## Implementierungsfortschritt

### Hauptmodul 1: PDF-Verarbeitung & KI-Extraktion

#### 1.1 Backend-Infrastruktur ✅ (2026-03-07)
- FastAPI-Grundstruktur mit Health-Check
- Pydantic-Settings für Konfiguration
- Logging-System mit konfigurierbarem Level
- Error-Handling mit custom Exceptions

#### 1.2 Datei-Management ✅ (2026-03-07)
- Ordnerstruktur: `inbox/`, `processing/`, `archive/`, `error/`
- Watchdog-Service für PDF-Überwachung
- PDF-Validierung (Magic-Bytes, Größe)
- Datei-Handling mit Hash-basierter Duplicate-Erkennung
- Modul: `app/file_utils.py`, `app/file_watcher.py`

#### 1.3 PDF-Konvertierung ✅ (2026-03-07)
- PDF-zu-Bild mit `pdf2image` + `poppler-utils`
- Bild-Optimierung mit `Pillow` (DPI 200, Max 2000x3000px)
- Base64-Encoding für API-Übertragung
- Multi-Page-Handling
- Modul: `app/pdf_converter.py`

#### 1.4 OpenRouter-Integration ✅ (2026-03-07)
- Async API-Client mit `httpx`
- Pydantic-Modelle für Request/Response (`app/schemas/extraction.py`)
- System-Prompt mit allen Enum-Werten (`app/prompts.py`)
- Exponential-Backoff Retry-Logik (3 Versuche)
- Rate-Limiting mit Retry-After Header
- JSON-Extraktion aus verschiedenen Antwortformaten
- Modul: `app/openrouter_client.py`
- Test: `test_openrouter.py` (22 Felder, 12 Räume aus Form2.pdf)

#### 1.5 Daten-Mapping & Validierung ✅ (2026-03-07)
- Mapping KI-JSON → DB-Felder
- Enum-Werte normalisieren (Groß-/Kleinschreibung, Varianten)
- Plausibilitätsprüfungen (Baujahr, Flächen, Budget)
- "Sonstiges"-Felder-Handling
- Modul: `app/mapping.py`

#### 1.6 Datenbank-Integration ✅ (2026-03-07)
- Async Connection-Pool mit `asyncpg`
- Transaktionssichere Projektspeicherung
- AI-Extraktion in `ai_extractions` speichern
- Räume in `project_rooms` einfügen
- Status-Updates mit History-Eintrag
- Modul: `app/database.py`
- Test: `test_db_integration.py`

#### 1.7 Workflow-Orchestrierung ✅ (2026-03-07)
- Processing-Pipeline: PDF → KI → Mapping → DB → Archiv
- Async Processing-Queue mit konfigurierbaren Workern
- Status-Tracking mit Callbacks
- Fehlerbehandlung mit Error-Archivierung
- Manuelle Re-Trigger via API
- Modul: `app/processing.py`
- API-Endpunkte: `/jobs`, `/queue/stats`, `/jobs/retrigger`

### Hauptmodul 2: API-Endpoints für Frontend-Integration

#### 2.1 Auth & Middleware ✅ (2026-03-07)
- API-Key-Authentifizierung mit SHA-256 Hash
- Bearer Token und X-API-Key Header Support
- Tenant-Extraktion aus API-Key
- X-Tenant-ID Header Validierung (Mismatch Detection)
- Unified Error Handler mit Standard-Format
- Request-Logging mit Verarbeitungszeit
- Development-Modus mit dev_api_key Fallback
- Module: `app/middleware/auth.py`, `app/middleware/error_handler.py`, `app/middleware/request_logging.py`
- Service: `app/services/api_keys.py`
- Test: `test_auth_middleware.py` (7/7 Tests bestanden)

## API-Endpunkte

| Endpoint | Methode | Beschreibung | Auth |
|----------|---------|--------------|------|
| `/health` | GET | System-Status + Queue-Statistiken | Nein |
| `/queue/stats` | GET | Processing-Queue Statistiken | Ja |
| `/jobs` | GET | Aktive Jobs auflisten | Ja |
| `/jobs/{job_id}` | GET | Job-Status abfragen | Ja |
| `/jobs/retrigger` | POST | Manuelle Neuverarbeitung | Ja |
| `/projects/{project_id}` | GET | Projekt mit Details laden | Ja |
| `/api/v1/tenants/me` | GET | Aktuelle Tenant-Infos | Ja |
| `/api/v1/auth/test` | GET | Authentifizierung testen | Ja |

## Test-PDF

**Original:** `/files/Form2.pdf` (4 Seiten, ~1MB)
- **WICHTIG:** Immer kopieren, nie verschieben!
- Test-Skript liest direkt aus Hauptordner (nicht inbox, da Watchdog)

## Lesson Learned

### OpenRouter API-Timeout
- Vision-Modelle benötigen ~30-60s für 4-seitige PDFs
- Timeout auf 120s konfiguriert (`openrouter_timeout`)

### JSON aus KI-Response extrahieren
- KI kann JSON in Markdown-Code-Blöcken zurückgeben
- Funktion `_extract_json_from_response()` behandelt verschiedene Formate

### API-Key-Format
- Format: `sk-tenant-{tenant_id}-{random_32_chars}`
- In DB wird nur SHA-256 Hash gespeichert
- Key-Prefix (erste 20 Zeichen) für schnelle Identifikation
- Development-Modus nutzt `dev_api_key` als Fallback

### Test-API-Key
```
sk-tenant-00000000-0000-0000-0000-000000000001-a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6
```
