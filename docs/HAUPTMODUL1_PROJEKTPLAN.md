# Hauptmodul 1: PDF-Verarbeitung & KI-Extraktion

## Ziel

Automatisierte Verarbeitung von Grundlagenformularen:
- PDF-Upload in überwachten Ordner
- KI-basierte Datenextraktion via OpenRouter
- Speicherung der extrahierten Daten in PostgreSQL

---

## Architektur-Überblick

```
┌─────────────┐    ┌──────────────┐    ┌─────────────┐    ┌────────────┐
│  /files/    │───>│  PDF-Worker  │───>│  OpenRouter │───>│ PostgreSQL │
│   inbox/    │    │  (FastAPI)   │    │  (Qwen VL)  │    │  Database  │
└─────────────┘    └──────────────┘    └─────────────┘    └────────────┘
                          │
                          ├──────────────────────────────────────┐
                          ▼                                      ▼
                   ┌──────────────┐                      ┌──────────────┐
                   │ /files/      │                      │ /files/      │
                   │ processing/  │                      │ archive/     │
                   │ (temporär)   │                      │ (permanent)  │
                   └──────────────┘                      └──────────────┘
                          │
                          ▼
                   ┌──────────────┐
                   │ /files/      │
                   │ error/       │
                   └──────────────┘
```

---

## Untermodule

### 1.1 Backend-Infrastruktur ✅

**Ziel:** FastAPI-Projekt aufsetzen mit sauberer Struktur

| Task | Beschreibung | Status |
|------|--------------|--------|
| 1.1.1 | FastAPI-Grundstruktur erstellen | ✅ `app/main.py` |
| 1.1.2 | Umgebungsvariablen erweitern (OpenRouter API-Key) | ✅ `app/config.py` |
| 1.1.3 | Logging-System implementieren | ✅ `app/logger.py` |
| 1.1.4 | Error-Handling & Exceptions definieren | ✅ `app/exceptions.py` |
| 1.1.5 | Health-Check Endpunkt | ✅ `/health` in `main.py` |

**Abhängigkeiten:** Keine

**Implementiert:** 2026-03-07

---

### 1.2 Datei-Management ✅

**Ziel:** Ordnerüberwachung und Dateiorganisation

| Task | Beschreibung | Status |
|------|--------------|--------|
| 1.2.1 | Ordnerstruktur anlegen (`inbox/`, `processing/`, `archive/`, `error/`) | ✅ `ensure_directories()` |
| 1.2.2 | Watchdog-Service für `inbox/` implementieren | ✅ `app/file_watcher.py` |
| 1.2.3 | Datei-Validierung (PDF-Format, Größe) | ✅ `validate_pdf_file()` |
| 1.2.4 | Datei-Handling: Inbox → Processing → Archive/Error | ✅ `move_file_to_processing()`, `move_to_archive()`, `move_to_error()` |
| 1.2.5 | Duplicate-Erkennung (Hash-basiert) | ✅ `calculate_file_hash()` |
| 1.2.6 | PNG-Dateien mit ins Archiv verschieben | ✅ `move_to_archive()` mit `png_files` Parameter |

**Abhängigkeiten:** 1.1

**Implementiert:** 2026-03-07

**Ordnerstruktur:**
```
/files/
├── inbox/                              # Eingehende PDFs (Watchdog überwacht)
│   └── {beliebiger_name}.pdf
│
├── processing/                         # Temporärer Arbeitsbereich
│   └── {process_uuid}/
│       ├── original.pdf                # Kopie für Verarbeitung
│       ├── page_001.png                # Konvertierte Seiten
│       ├── page_002.png
│       └── metadata.json               # Temp. Prozess-Infos
│
├── archive/                            # Dauerhafte Ablage
│   └── {tenant_id}/
│       └── {project_uuid}/
│           ├── original_{timestamp}.pdf    # Eindeutiger Name
│           ├── page_001_{timestamp}.png    # Für Frontend-Anzeige
│           ├── page_002_{timestamp}.png
│           └── extraction.json             # KI-Response (Debug)
│
└── error/                              # Fehlgeschlagene Verarbeitungen
    └── {timestamp}_{original_filename}/
        ├── original.pdf
        └── error.log
```

**Dateinamen-Konvention:**
- Original-PDF: `original_{YYYYMMDD_HHMMSS}.pdf`
- PNG-Seiten: `page_{03d}_{YYYYMMDD_HHMMSS}.png`
- Timestamp gewährleistet Eindeutigkeit auch bei gleichem Dateinamen

**Datei-Speicherübersicht:**

| Datei | Speicherort | Zweck | Dauer |
|-------|-------------|-------|-------|
| Original-PDF | `/files/archive/{tenant}/{project}/` | Frontend-Anzeige, Download | Permanent |
| PNG-Seiten | `/files/archive/{tenant}/{project}/` | Frontend-Vorschau (was KI "gesehen" hat) | Permanent |
| KI-Response JSON | DB `ai_extractions` + `/files/archive/` | Debugging, Nachvollziehbarkeit | Permanent |
| PDF-Pfad | DB `projects.pdf_path` | Frontend-Zugriff | Permanent |
| PNG-Pfade | DB `projects.page_paths` (neu) | Frontend-Zugriff auf Seiten | Permanent |
| Temp-Dateien | `/files/processing/` | Verarbeitung | Temporär (wird gelöscht) |

---

### 1.3 PDF-Konvertierung ✅

**Ziel:** PDFs für Vision-Modelle aufbereiten

| Task | Beschreibung | Status |
|------|--------------|--------|
| 1.3.1 | PDF-zu-Bild Konvertierung (`pdf2image`) | ✅ `pdf_zu_bilder()` |
| 1.3.2 | Bild-Optimierung (Größe, Qualität) | ✅ `_optimiere_bild()` mit PIL |
| 1.3.3 | Base64-Encoding für API-Übertragung | ✅ `bild_zu_base64()` |
| 1.3.4 | Multi-Page-Handling (mehrseitige PDFs) | ✅ `konvertiere_pdf_fuer_vision()` |

**Abhängigkeiten:** 1.2

**Implementiert:** 2026-03-07

**Technologie:**
- `pdf2image` mit `poppler-utils` für PDF-zu-Bild
- `Pillow` für Bild-Optimierung
- DPI: 200, Max-Größe: 2000x3000px

**Modul:** `app/pdf_converter.py`

**Funktionen:**
- `pdf_zu_bilder()` - Konvertiert PDF zu PNG-Bildern
- `bild_zu_base64()` - Erstellt Data-URI für API-Übertragung
- `konvertiere_pdf_fuer_vision()` - Hauptfunktion mit allen Features
- `get_pdf_info()` - Metadaten ohne Konvertierung

**Getestet mit:** `files/inbox/Form2.pdf` (4 Seiten, ~1MB)

---

### 1.4 OpenRouter-Integration ✅

**Ziel:** KI-API für Formular-Extraktion anbinden

| Task | Beschreibung | Status |
|------|--------------|--------|
| 1.4.1 | OpenRouter API-Client erstellen | ✅ `app/openrouter_client.py` |
| 1.4.2 | Prompt für Grundlagenformular entwickeln | ✅ `app/prompts.py` |
| 1.4.3 | Response-Schema definieren (JSON-Struktur) | ✅ `app/schemas/extraction.py` |
| 1.4.4 | Retry-Logik bei API-Fehlern | ✅ Exponential-Backoff (2^attempt Sekunden) |
| 1.4.5 | Rate-Limiting beachten | ✅ Retry-After Header + 429-Handling |

**Abhängigkeiten:** 1.3

**Implementiert:** 2026-03-07

**Verwendetes Modell:**
- Qwen2.5-VL-72B-Instruct über OpenRouter
- API-Timeout: 120s (Vision-Modelle benötigen ~30-60s)

**Module:**
- `app/openrouter_client.py` - Async API-Client mit Retry-Logik
- `app/prompts.py` - System-Prompt mit allen Enum-Werten
- `app/schemas/extraction.py` - Pydantic-Modelle für Validierung

**Getestet mit:** `files/Form2.pdf` (4 Seiten, ~1MB)
- Ergebnis: 22 Felder extrahiert, 12 Räume erkannt
- Test-Skript: `backend/test_openrouter.py`

---

### 1.5 Daten-Mapping & Validierung

**Ziel:** KI-Response auf Datenbank-Schema mappen

| Task | Beschreibung | Status |
|------|--------------|--------|
| 1.5.1 | Mapping-Logik (JSON → DB-Felder) | ⬜ |
| 1.5.2 | Pflichtfeld-Validierung | ⬜ |
| 1.5.3 | Enum-Werte prüfen und normalisieren | ⬜ |
| 1.5.4 | "Sonstiges"-Felder verarbeiten | ⬜ |
| 1.5.5 | Plausibilitätsprüfungen (z.B. Baujahr, Flächen) | ⬜ |

**Abhängigkeiten:** 1.4

**Referenz:** `docs/DATABASE.md` für alle Enum-Werte und Felder

---

### 1.6 Datenbank-Integration

**Ziel:** Extrahierte Daten in PostgreSQL speichern

| Task | Beschreibung | Status |
|------|--------------|--------|
| 1.6.1 | Database-Connection-Pool einrichten | ⬜ |
| 1.6.2 | Projekt anlegen mit Status `raw_extracted` | ⬜ |
| 1.6.3 | AI-Extraktion in `ai_extractions` speichern | ⬜ |
| 1.6.4 | Räume in `project_rooms` einfügen | ⬜ |
| 1.6.5 | PDF-Pfad und PNG-Pfade in DB speichern | ⬜ |
| 1.6.6 | Transaktionssicherheit (Rollback bei Fehlern) | ⬜ |

**Abhängigkeiten:** 1.5

**DB-Erweiterung erforderlich:**
- Neues Feld `page_paths` (JSONB) in `projects` für PNG-Pfade
- Siehe `docs/DATABASE.md` für Schema-Update

---

### 1.7 Workflow-Orchestrierung

**Ziel:** Alle Komponenten zu einem automatisierten Prozess verbinden

| Task | Beschreibung | Status |
|------|--------------|--------|
| 1.7.1 | Main-Processing-Pipeline implementieren | ⬜ |
| 1.7.2 | Status-Updates während Verarbeitung | ⬜ |
| 1.7.3 | Fehlerbehandlung mit aussagekräftigen Logs | ⬜ |
| 1.7.4 | Manuelle Re-Trigger-Möglichkeit | ⬜ |
| 1.7.5 | Processing-Queue für mehrere gleichzeitige Dateien | ⬜ |

**Abhängigkeiten:** 1.1 - 1.6

---

## Abhängigkeits-Diagramm

```
1.1 Backend-Infrastruktur ✅
    │
    ├──> 1.2 Datei-Management ✅
    │        │
    │        └──> 1.3 PDF-Konvertierung ✅
    │                 │
    │                 └──> 1.4 OpenRouter-Integration ✅
    │                          │
    │                          └──> 1.5 Daten-Mapping ⬜ (NÄCHSTER SCHRITT)
    │                                   │
    │                                   └──> 1.6 Datenbank-Integration ⬜
    │
    └──────────────────────────────────────────> 1.7 Workflow-Orchestrierung ⬜
```

---

## Technologie-Stack Erweiterung

| Komponente | Technologie |
|------------|-------------|
| Backend-Framework | FastAPI |
| ASGI-Server | Uvicorn |
| Dateiüberwachung | watchdog |
| PDF-Konvertierung | pdf2image, poppler-utils |
| HTTP-Client | httpx (async) |
| Validierung | Pydantic |

---

## Nächste Schritte

1. **Aktuell:** 1.5 Daten-Mapping & Validierung implementieren
2. **Danach:** 1.6 Datenbank-Integration
3. **Abschließend:** 1.7 Workflow-Orchestrierung

---

## Offene Fragen

- [ ] OpenRouter API-Key vorhanden?
- [ ] Muster-PDF für Tests verfügbar?
- [x] ~~Soll Multi-Tenancy schon in HM1 berücksichtigt werden?~~ → **Ja, Tenant-Struktur in `/files/archive/`**
- [ ] Docker-Setup bereits jetzt oder später?
- [ ] Standard-Tenant für erste Tests definieren?

---

*Erstellt: 2026-03-07*
*Letztes Update: 2026-03-07*
*Status: In Entwicklung - 1.1, 1.2, 1.3 & 1.4 abgeschlossen*
