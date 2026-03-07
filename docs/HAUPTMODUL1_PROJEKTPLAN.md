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

### 1.1 Backend-Infrastruktur

**Ziel:** FastAPI-Projekt aufsetzen mit sauberer Struktur

| Task | Beschreibung | Status |
|------|--------------|--------|
| 1.1.1 | FastAPI-Grundstruktur erstellen | ⬜ |
| 1.1.2 | Umgebungsvariablen erweitern (OpenRouter API-Key) | ⬜ |
| 1.1.3 | Logging-System implementieren | ⬜ |
| 1.1.4 | Error-Handling & Exceptions definieren | ⬜ |
| 1.1.5 | Health-Check Endpunkt | ⬜ |

**Abhängigkeiten:** Keine

---

### 1.2 Datei-Management

**Ziel:** Ordnerüberwachung und Dateiorganisation

| Task | Beschreibung | Status |
|------|--------------|--------|
| 1.2.1 | Ordnerstruktur anlegen (`inbox/`, `processing/`, `archive/`, `error/`) | ⬜ |
| 1.2.2 | Watchdog-Service für `inbox/` implementieren | ⬜ |
| 1.2.3 | Datei-Validierung (PDF-Format, Größe) | ⬜ |
| 1.2.4 | Datei-Handling: Inbox → Processing → Archive/Error | ⬜ |
| 1.2.5 | Duplicate-Erkennung (Hash-basiert) | ⬜ |
| 1.2.6 | PNG-Dateien mit ins Archiv verschieben | ⬜ |

**Abhängigkeiten:** 1.1

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

### 1.3 PDF-Konvertierung

**Ziel:** PDFs für Vision-Modelle aufbereiten

| Task | Beschreibung | Status |
|------|--------------|--------|
| 1.3.1 | PDF-zu-Bild Konvertierung (`pdf2image`) | ⬜ |
| 1.3.2 | Bild-Optimierung (Größe, Qualität) | ⬜ |
| 1.3.3 | Base64-Encoding für API-Übertragung | ⬜ |
| 1.3.4 | Multi-Page-Handling (mehrseitige PDFs) | ⬜ |

**Abhängigkeiten:** 1.2

**Technologie:**
- `pdf2image` mit `poppler-utils`
- Ziel: 1 Bild pro Seite, optimiert für OCR

---

### 1.4 OpenRouter-Integration

**Ziel:** KI-API für Formular-Extraktion anbinden

| Task | Beschreibung | Status |
|------|--------------|--------|
| 1.4.1 | OpenRouter API-Client erstellen | ⬜ |
| 1.4.2 | Prompt für Grundlagenformular entwickeln | ⬜ |
| 1.4.3 | Response-Schema definieren (JSON-Struktur) | ⬜ |
| 1.4.4 | Retry-Logik bei API-Fehlern | ⬜ |
| 1.4.5 | Rate-Limiting beachten | ⬜ |

**Abhängigkeiten:** 1.3

**Verwendetes Modell:**
- Qwen2.5-VL über OpenRouter
- Fallback-Option: Claude 3.5 Sonnet (falls nötig)

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
1.1 Backend-Infrastruktur
    │
    ├──> 1.2 Datei-Management
    │        │
    │        └──> 1.3 PDF-Konvertierung
    │                 │
    │                 └──> 1.4 OpenRouter-Integration
    │                          │
    │                          └──> 1.5 Daten-Mapping
    │                                   │
    │                                   └──> 1.6 Datenbank-Integration
    │
    └──────────────────────────────────────────> 1.7 Workflow-Orchestrierung
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

1. **Sofort:** Untermodule 1.1 und 1.2 parallel starten
2. **Danach:** 1.3 PDF-Konvertierung implementieren
3. **Parallel:** OpenRouter API-Key besorgen und 1.4 testen

---

## Offene Fragen

- [ ] OpenRouter API-Key vorhanden?
- [ ] Muster-PDF für Tests verfügbar?
- [x] ~~Soll Multi-Tenancy schon in HM1 berücksichtigt werden?~~ → **Ja, Tenant-Struktur in `/files/archive/`**
- [ ] Docker-Setup bereits jetzt oder später?
- [ ] Standard-Tenant für erste Tests definieren?

---

*Erstellt: 2026-03-07*
*Status: Planung*
