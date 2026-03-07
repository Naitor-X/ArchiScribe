# ArchiScribe - Datenbank-Dokumentation

> **Für KI-Assistenten:** Diese Dokumentation beschreibt die vollständige Datenbankstruktur der ArchiScribe SaaS-App für Architekten.

---

## Projektübersicht

**ArchiScribe** ist eine mandantenfähige (Multi-Tenant) SaaS-Anwendung für Architekturbüros. Die App:

1. Liest handschriftliche Grundlagenformulare via KI/OCR aus
2. Stellt extrahierte Daten dem Architekten zur Verifizierung bereit
3. Speichert KI-Rohdaten für Debugging-Zwecke
4. Trackt alle Änderungen via Audit-Trail

---

## Technologie-Stack

| Komponente | Technologie |
|------------|-------------|
| Datenbank | PostgreSQL |
| Primärschlüssel | UUID (uuid-ossp) |
| JSON-Speicherung | JSONB |
| Zeitstempel | TIMESTAMP WITH TIME ZONE |

---

## Enums

### topography_enum
```sql
'eben' | 'leichte Hanglage' | 'starke Hanglage' | 'Sonstiges'
```

### access_status_enum
```sql
'voll erschlossen' | 'teilerschlossen' | 'nicht erschlossen'
```

### project_type_enum
```sql
'Neubau' | 'Bauen im Bestand' | 'Umbau im Inneren' | 'Sanierung/Modernis.' | 'Zubau/Anbau' | 'Aufstockung' | 'noch unklar' | 'Sonstiges'
```

### building_type_enum
```sql
'EFH' | 'Doppelhaus' | 'Reihenhaus' | 'Mehrfamilienhaus' | 'Sonstige'
```

### construction_method_enum
```sql
'Massivbau' | 'Holzbau' | 'noch offen'
```

### heating_type_enum
```sql
'Wärmepumpe' | 'Gasheizung' | 'Fernwärme' | 'Holz/Pellets' | 'Sonstige'
```

### own_contribution_enum
```sql
'ja' | 'nein' | 'teilweise'
```

### accessibility_enum
```sql
'wichtig' | 'optional' | 'nicht relevant'
```

---

## Tabellenstruktur

### 1. `tenants` - Mandanten / Architekturbüros

| Spalte | Typ | Constraints | Beschreibung |
|--------|-----|-------------|--------------|
| `id` | UUID | PK, auto-generated | Eindeutige Mandanten-ID |
| `name` | VARCHAR(255) | NOT NULL | Name des Architekturbüros |
| `created_at` | TIMESTAMPTZ | DEFAULT NOW() | Erstellungszeitpunkt |

---

### 2. `project_statuses` - Dokumentenstatus

| Spalte | Typ | Constraints | Beschreibung |
|--------|-----|-------------|--------------|
| `id` | VARCHAR(50) | PK | Status-ID |
| `label` | VARCHAR(100) | NOT NULL | Anzeigename (DE) |

**Vordefinierte Status:**

| id | label |
|----|-------|
| `raw_extracted` | KI-Rohextraktion |
| `needs_review` | Überprüfung erforderlich |
| `verified_by_architect` | Vom Architekten verifiziert |

---

### 3. `projects` - Grundlagenformulare (Haupttabelle)

| Spalte | Typ | Constraints | Beschreibung |
|--------|-----|-------------|--------------|
| `id` | UUID | PK, auto-generated | Eindeutige Projekt-ID |
| `tenant_id` | UUID | FK → tenants, NOT NULL | Mandantenzuordnung |
| `status_id` | VARCHAR(50) | FK → project_statuses, DEFAULT 'raw_extracted' | Projektstatus |
| `original_file_url` | VARCHAR(500) | - | Link zum Original-Scan |
| `created_at` | TIMESTAMPTZ | DEFAULT NOW() | Erstellungszeitpunkt |
| `updated_at` | TIMESTAMPTZ | DEFAULT NOW(), auto-update | Letzte Änderung |

#### Allgemeine Angaben

| Spalte | Typ | Beschreibung |
|--------|-----|-------------|
| `client_name` | VARCHAR(255) | Name des Bauherren |
| `address` | TEXT | Adresse des Bauherren |
| `phone` | VARCHAR(50) | Telefonnummer |
| `email` | VARCHAR(255) | E-Mail (mit Validierung) |
| `date` | DATE | Datum der Erfassung |

#### Grundstück

| Spalte | Typ | Beschreibung |
|--------|-----|-------------|
| `plot_location` | TEXT | Lage des Grundstücks |
| `plot_size_m2` | DECIMAL(12,2) | Grundstücksgröße in m² |
| `landowner` | VARCHAR(255) | Grundstückseigentümer |
| `topography` | topography_enum | Topographie |
| `topography_other` | VARCHAR(255) | Freitext wenn topography='Sonstiges' |
| `development_plan` | BOOLEAN | Bebauungsplan vorhanden? |
| `access_status` | access_status_enum | Erschließungsstatus |

#### Vorstellungen / Ziele

| Spalte | Typ | Beschreibung |
|--------|-----|-------------|
| `project_type` | project_type_enum | Art des Projekts |
| `project_type_other` | VARCHAR(255) | Freitext wenn project_type='Sonstiges' |
| `building_type` | building_type_enum | Gebäudetyp |
| `building_type_other` | VARCHAR(255) | Freitext wenn building_type='Sonstige' |
| `construction_method` | construction_method_enum | Bauweise |
| `heating_type` | heating_type_enum | Heizungstyp |
| `heating_type_other` | VARCHAR(255) | Freitext wenn heating_type='Sonstige' |
| `budget` | DECIMAL(15,2) | Budget in EUR |
| `planned_start` | DATE | Geplanter Baubeginn |
| `own_contribution` | own_contribution_enum | Eigenleistung? |
| `own_contribution_details` | TEXT | Details zur Eigenleistung |

#### Besondere Hinweise / Notizen

| Spalte | Typ | Beschreibung |
|--------|-----|-------------|
| `accessibility` | accessibility_enum | Barrierefreiheit |
| `outdoor_area` | TEXT | Außenanlagen-Wünsche |
| `materiality` | TEXT | Materialvorstellungen |
| `notes` | TEXT | Sonstige Notizen |

**Constraints:**
- `valid_email`: E-Mail-Format-Validierung
- `valid_budget`: Budget ≥ 0
- `valid_plot_size`: Grundstücksgröße ≥ 0

---

### 4. `project_rooms` - Dynamisches Raumprogramm

| Spalte | Typ | Constraints | Beschreibung |
|--------|-----|-------------|--------------|
| `id` | UUID | PK, auto-generated | Eindeutige Raum-ID |
| `project_id` | UUID | FK → projects, NOT NULL, ON DELETE CASCADE | Projektzuordnung |
| `room_type` | VARCHAR(100) | NOT NULL | Raumtyp (z.B. "Schlafzimmer", "Küche") |
| `quantity` | INTEGER | DEFAULT 1, > 0 | Anzahl |
| `size_m2` | DECIMAL(10,2) | ≥ 0 | Gewünschte Größe in m² |
| `special_requirements` | TEXT | - | Besondere Anforderungen |

---

### 5. `ai_extractions` - KI-Rohdaten für Debugging

| Spalte | Typ | Constraints | Beschreibung |
|--------|-----|-------------|--------------|
| `id` | UUID | PK, auto-generated | Eindeutige Extraktions-ID |
| `project_id` | UUID | FK → projects, NOT NULL, ON DELETE CASCADE | Projektzuordnung |
| `raw_json` | JSONB | NOT NULL | Exakter KI-Output (Original) |
| `confidence_scores` | JSONB | - | Confidence-Score pro Feld |
| `extracted_at` | TIMESTAMPTZ | DEFAULT NOW() | Zeitpunkt der Extraktion |

**Verwendungszweck:**
- Debugging bei Fehlernkennung
- Verbesserung der KI-Prompts
- Qualitätsanalyse der OCR-Ergebnisse

---

### 6. `project_history` - Audit Trail / Versionierung

| Spalte | Typ | Constraints | Beschreibung |
|--------|-----|-------------|--------------|
| `id` | UUID | PK, auto-generated | Eindeutige Historien-ID |
| `project_id` | UUID | FK → projects, NOT NULL, ON DELETE CASCADE | Projektzuordnung |
| `changed_by_user_id` | UUID | - | User-ID des Ändernden |
| `changed_at` | TIMESTAMPTZ | DEFAULT NOW() | Zeitpunkt der Änderung |
| `changes` | JSONB | NOT NULL | Delta: {field: {old: x, new: y}} |

**Beispiel `changes` JSONB:**
```json
{
  "budget": {"old": 250000, "new": 300000},
  "client_name": {"old": "Max Müller", "new": "Max Mustermann"}
}
```

---

## Entity-Relationship-Diagramm

```
┌─────────────────┐
│     tenants     │
├─────────────────┤
│ id (PK)         │
│ name            │
│ created_at      │
└────────┬────────┘
         │ 1:N
         ▼
┌─────────────────┐       ┌─────────────────────┐
│    projects     │       │  project_statuses   │
├─────────────────┤       ├─────────────────────┤
│ id (PK)         │──────►│ id (PK)             │
│ tenant_id (FK)  │       │ label               │
│ status_id (FK)  │       └─────────────────────┘
│ ...             │
└────────┬────────┘
         │
    ┌────┴────┬──────────────┬───────────────┐
    │ 1:N     │ 1:N          │ 1:N           │
    ▼         ▼              ▼               ▼
┌─────────┐ ┌───────────────┐ ┌───────────────┐
│ project │ │ ai_extractions│ │ project_      │
│ _rooms  │ ├───────────────┤ │ history       │
├─────────┤ │ id (PK)       │ ├───────────────┤
│id (PK)  │ │ project_id(FK)│ │ id (PK)       │
│project_id│ │ raw_json      │ │ project_id(FK)│
│room_type│ │ confidence_   │ │ changed_by_   │
│quantity │ │   scores      │ │   user_id     │
│size_m2  │ │ extracted_at  │ │ changed_at    │
│special_ │ └───────────────┘ │ changes       │
│requirements│                 └───────────────┘
└─────────┘
```

---

## Indizes

| Tabelle | Index | Spalte(n) | Zweck |
|---------|-------|-----------|-------|
| projects | `idx_projects_tenant_id` | tenant_id | Multi-Tenant-Queries |
| projects | `idx_projects_status_id` | status_id | Status-Filter |
| projects | `idx_projects_created_at` | created_at | Zeitbasierte Sortierung |
| projects | `idx_projects_client_name` | client_name (GIN) | Volltextsuche |
| project_rooms | `idx_project_rooms_project_id` | project_id | JOIN-Performance |
| ai_extractions | `idx_ai_extractions_project_id` | project_id | JOIN-Performance |
| ai_extractions | `idx_ai_extractions_extracted_at` | extracted_at | Zeitbasierte Queries |
| project_history | `idx_project_history_project_id` | project_id | JOIN-Performance |
| project_history | `idx_project_history_changed_at` | changed_at | Audit-Trail |

---

## Trigger

### `update_projects_updated_at`

Automatisches Update von `updated_at` bei Änderungen an der `projects`-Tabelle.

```sql
BEFORE UPDATE ON projects
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column()
```

---

## Views

### `v_projects_with_status`

Vereinfachte Sicht für häufige Abfragen mit Status-Label und Tenant-Name.

```sql
SELECT p.*, ps.label AS status_label, t.name AS tenant_name
FROM projects p
JOIN project_statuses ps ON p.status_id = ps.id
JOIN tenants t ON p.tenant_id = t.id;
```

---

## Typische Abfragen

### Alle Projekte eines Mandanten
```sql
SELECT * FROM projects WHERE tenant_id = :tenant_id ORDER BY created_at DESC;
```

### Projekt mit Raumprogramm
```sql
SELECT p.*, json_agg(pr.*) AS rooms
FROM projects p
LEFT JOIN project_rooms pr ON p.id = pr.project_id
WHERE p.id = :project_id
GROUP BY p.id;
```

### Änderungshistorie eines Projekts
```sql
SELECT * FROM project_history
WHERE project_id = :project_id
ORDER BY changed_at DESC;
```

### KI-Extraktion mit Confidence-Scores
```sql
SELECT raw_json, confidence_scores
FROM ai_extractions
WHERE project_id = :project_id
ORDER BY extracted_at DESC
LIMIT 1;
```

---

## Wichtige Hinweise für KI-Assistenten

1. **Multi-Tenancy:** Jede Query an `projects` MUSS `tenant_id` filtern (außer Admin-Queries)

2. **Enum-Werte:** Bei "Sonstiges"-Werten immer das entsprechende `_other`-Feld prüfen

3. **Audit-Trail:** Änderungen an `projects` sollten immer einen Eintrag in `project_history` erzeugen

4. **KI-Daten:** `raw_json` in `ai_extractions` niemals verändern - nur für Debugging lesen

5. **Löschverhalten:** `ON DELETE CASCADE` bei `project_rooms`, `ai_extractions`, `project_history` - Löschen eines Projekts entfernt alle abhängigen Daten

6. **Budget-Einheit:** EUR, nicht formatiert (ohne € oder Tausendertrennzeichen)

7. **Flächen-Einheit:** m², als DECIMAL gespeichert

---

## Dateipfade

| Datei | Pfad | Beschreibung |
|-------|------|--------------|
| Schema | `backend/database/schema.sql` | Vollständiges SQL-Schema |
| Init-Skript | `backend/database/init_db.py` | Python-Initialisierung |
| Umgebungsvariablen | `backend/.env` | DB-Konfiguration |

---

## Initialisierung

```bash
cd backend
source venv/bin/activate
python database/init_db.py
```

---

*Stand: 2026-03-07*
