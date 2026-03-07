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
