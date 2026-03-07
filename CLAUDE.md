# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Projektübersicht

**ArchiScribe** ist eine mandantenfähige (Multi-Tenant) SaaS-Anwendung für Architekturbüros:
- Liest handschriftliche Grundlagenformulare via KI/OCR aus
- Extrahierte Daten werden Architekten zur Verifizierung bereitgestellt
- KI-Rohdaten werden für Debugging gespeichert
- Vollständiger Audit-Trail für alle Änderungen

## Technologie-Stack

- **Backend**: Python 3.12
- **Datenbank**: PostgreSQL mit UUID-Primärschlüsseln
- **Dependencies**: `psycopg2-binary`, `python-dotenv`

## Wichtige Befehle

```bash
# Backend-Umgebung aktivieren
cd backend && source venv/bin/activate

# Datenbank initialisieren
python database/init_db.py

# Dependencies installieren
pip install -r requirements.txt
```

## Datenbank-Architektur

### Kern-Tabellen
- `tenants` - Mandanten/Architekturbüros (Multi-Tenancy)
- `projects` - Haupttabelle für Grundlagenformulare
- `project_rooms` - Dynamisches Raumprogramm (1:N zu projects)
- `ai_extractions` - KI-Rohdaten für Debugging (JSONB)
- `project_history` - Audit-Trail/Versionierung (JSONB)

### Projektstatus-Workflow
1. `raw_extracted` → KI-Rohextraktion
2. `needs_review` → Überprüfung erforderlich
3. `verified_by_architect` → Vom Architekten verifiziert

### Wichtige Regeln
- **Multi-Tenancy**: Jede Query an `projects` MUSS `tenant_id` filtern
- **Enum-"Sonstiges"**: Bei Enum-Werten mit "Sonstiges" immer das entsprechende `_other`-Feld prüfen
- **Audit-Trail**: Änderungen an `projects` erzeugen Einträge in `project_history`
- **KI-Daten**: `raw_json` in `ai_extractions` niemals verändern

## Projektstruktur

```
backend/
├── app/                 # Anwendungscode (noch leer)
├── database/
│   ├── schema.sql       # Vollständiges DB-Schema
│   └── init_db.py       # DB-Initialisierung
├── .env                 # DB-Konfiguration (nicht committen!)
├── .env.example         # Vorlage für Umgebungsvariablen
└── requirements.txt
docs/
└── DATABASE.md          # Detaillierte DB-Dokumentation
```

## Umgebungsvariablen

Siehe `backend/.env.example` für benötigte Variablen:
- `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_DB`
- `POSTGRES_USER`, `POSTGRES_PASSWORD`

## Dokumentation

Detaillierte Datenbankdokumentation mit ER-Diagramm, allen Enum-Werten und Beispiel-Queries: `docs/DATABASE.md`
