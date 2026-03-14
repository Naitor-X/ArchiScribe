# API-Endpoints: Implementierungsplan (Hauptmodul 2)

## Übersicht

RESTful API für das Architekten-Frontend. Alle Entscheidungen sind final getroffen — dieser Plan
ist direkt umsetzbar.

---

## Bereits implementiert (nicht anfassen)

- `app/middleware/auth.py` — API-Key-Validierung (SHA-256)
- `app/middleware/tenant.py` — TenantContext
- `app/middleware/error_handler.py` — Unified Error-Responses
- `app/middleware/request_logging.py` — Request-Logging
- `app/services/api_keys.py` — Key-Generierung & Validierung
- `app/config.py` — Settings inkl. `dev_api_key`
- `app/main.py` — Middleware eingebunden, alte Job/Projekt-Endpoints vorhanden (werden in Schritt 8 ersetzt)

**Test-API-Key (Development):**
```
sk-tenant-00000000-0000-0000-0000-000000000001-a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6
```

---

## Finale Architektur-Entscheidungen

| Thema | Entscheidung |
|-------|--------------|
| Auth | `X-API-Key` Header (bereits implementiert) |
| URL-Prefix | `/api/v1/` für alle neuen Endpoints |
| Pagination | Cursor-basiert: Cursor = Base64(JSON(`{"created_at": "...", "id": "..."}`)), sortiert nach `created_at DESC, id DESC` |
| Suche | `client_name` + `address` (PostgreSQL `ILIKE`) |
| Datei-Ablage | `files/archive/{tenant_id}/{project_id}/` (bereits so implementiert in `file_utils.py`) |
| Signed URLs | FastAPI `StaticFiles` auf gleichem Port, Base-URL via `FILES_BASE_URL` Env-Variable |
| PNG-Pfade | Aus DB-Feld `projects.page_paths` (JSONB-Array), kein Filesystem-Scan |
| PNG-Dateiname | `page_001_YYYYMMDD_HHMMSS.png` (so generiert von `file_utils.move_to_archive`) |
| Token-Ablaufzeit | 15 Minuten |
| Token-Library | `itsdangerous` (TimestampSigner) |
| `changed_by_user_id` | Tenant-UUID aus dem authentifizierten Request |
| Jobs-Endpoints | Umzug von `/jobs/...` nach `/api/v1/jobs/...` (alte Pfade in `main.py` entfernen) |

---

## Endpunkt-Übersicht (final)

```
/api/v1/
│
├── projects/
│   ├── GET    /                            # Liste (paginiert, filterbar, sortierbar)
│   ├── GET    /{id}                        # Details + Räume
│   ├── PATCH  /{id}                        # Felder bearbeiten
│   ├── POST   /{id}/verify                 # Status → verified_by_architect
│   ├── GET    /{id}/pdf                    # Signed URL für Original-PDF
│   ├── GET    /{id}/pages                  # Signed URLs für alle Seiten-PNGs
│   └── GET    /{id}/history                # Audit-Trail
│
├── projects/{project_id}/rooms/
│   ├── POST   /                            # Neuen Raum anlegen
│   ├── PATCH  /{room_id}                   # Raum bearbeiten
│   └── DELETE /{room_id}                   # Raum löschen
│
├── jobs/
│   ├── GET    /                            # Alle aktiven Jobs
│   ├── GET    /{id}                        # Job-Status
│   └── POST   /retrigger                   # Neuverarbeitung
│
└── tenants/
    └── GET    /me                          # Eigene Tenant-Infos (bereits in main.py)
```

---

## Editierbare Projekt-Felder (PATCH /projects/{id})

Nur diese Felder darf der Architekt via PATCH ändern. Alle anderen sind schreibgeschützt.

**Schreibgeschützt (nie via PATCH änderbar):**
`id`, `tenant_id`, `status_id`, `pdf_path`, `page_paths`, `created_at`, `updated_at`, `date`

**Editierbare Felder:**

| Feld | DB-Typ | Pydantic-Typ |
|------|--------|--------------|
| `client_name` | VARCHAR(255) | `str \| None` |
| `address` | TEXT | `str \| None` |
| `phone` | VARCHAR(50) | `str \| None` |
| `email` | VARCHAR(255) | `str \| None` |
| `plot_location` | TEXT | `str \| None` |
| `plot_size_m2` | DECIMAL(12,2) | `float \| None` |
| `landowner` | VARCHAR(255) | `str \| None` |
| `topography` | ENUM | `str \| None` (Werte: `eben`, `leichte Hanglage`, `starke Hanglage`, `Sonstiges`) |
| `topography_other` | VARCHAR(255) | `str \| None` |
| `development_plan` | BOOLEAN | `bool \| None` |
| `access_status` | ENUM | `str \| None` (Werte: `voll erschlossen`, `teilerschlossen`, `nicht erschlossen`) |
| `project_type` | ENUM | `str \| None` (Werte: `Neubau`, `Bauen im Bestand`, `Umbau im Inneren`, `Sanierung/Modernis.`, `Zubau/Anbau`, `Aufstockung`, `noch unklar`, `Sonstiges`) |
| `project_type_other` | VARCHAR(255) | `str \| None` |
| `building_type` | ENUM | `str \| None` (Werte: `EFH`, `Doppelhaus`, `Reihenhaus`, `Mehrfamilienhaus`, `Sonstige`) |
| `building_type_other` | VARCHAR(255) | `str \| None` |
| `construction_method` | ENUM | `str \| None` (Werte: `Massivbau`, `Holzbau`, `noch offen`) |
| `heating_type` | ENUM | `str \| None` (Werte: `Wärmepumpe`, `Gasheizung`, `Fernwärme`, `Holz/Pellets`, `Sonstige`) |
| `heating_type_other` | VARCHAR(255) | `str \| None` |
| `budget` | DECIMAL(15,2) | `float \| None` |
| `planned_start` | DATE | `date \| None` |
| `own_contribution` | ENUM | `str \| None` (Werte: `ja`, `nein`, `teilweise`) |
| `own_contribution_details` | TEXT | `str \| None` |
| `accessibility` | ENUM | `str \| None` (Werte: `wichtig`, `optional`, `nicht relevant`) |
| `outdoor_area` | TEXT | `str \| None` |
| `materiality` | TEXT | `str \| None` |
| `notes` | TEXT | `str \| None` |

---

## Raum-Felder (DB Single Point of Truth)

Tabelle `project_rooms` — alle 4 Felder sind editierbar:

| Feld | DB-Typ | Pflicht | Constraints |
|------|--------|---------|-------------|
| `room_type` | VARCHAR(100) | Ja | — |
| `quantity` | INTEGER | Nein | Default 1, muss > 0 |
| `size_m2` | DECIMAL(10,2) | Nein | muss ≥ 0 |
| `special_requirements` | TEXT | Nein | — |

> Kein `floor`-Feld. Duplikate (gleicher `room_type` im selben Projekt) → HTTP 400.

---

## HTTP-Status-Codes

| Code | Verwendung |
|------|------------|
| 200 | Erfolgreiche GET / PATCH |
| 201 | Erfolgreiche POST (neue Ressource) |
| 204 | Erfolgreiche DELETE (kein Response-Body) |
| 400 | Fachlicher Validierungsfehler (z.B. Duplikat-Raum) |
| 401 | Fehlender oder ungültiger API-Key |
| 403 | Zugriff auf fremden Tenant |
| 404 | Ressource nicht gefunden |
| 422 | Pydantic-Validierungsfehler (automatisch durch FastAPI) |
| 500 | Unerwarteter Server-Fehler |

---

## Schritt-für-Schritt Implementierung

Die Schritte müssen **in dieser Reihenfolge** umgesetzt werden, da jeder Schritt auf dem vorherigen aufbaut.

---

### Schritt 0: Vorbereitung

#### 0.1 Neue Dependency installieren

```bash
cd backend && source venv/bin/activate
pip install itsdangerous
```

`requirements.txt` ergänzen:
```
itsdangerous>=2.1.0
```

#### 0.2 Config erweitern (`app/config.py`)

Folgende Felder zur `Settings`-Klasse hinzufügen:

```python
# Signed URLs
files_base_url: str = "http://localhost:8000"   # Env-Variable: FILES_BASE_URL
signed_url_secret: str = "change-me-in-production"  # Env-Variable: SIGNED_URL_SECRET
signed_url_expiry_seconds: int = 900  # 15 Minuten
```

`.env.example` entsprechend ergänzen:
```
FILES_BASE_URL=http://localhost:8000
SIGNED_URL_SECRET=change-me-in-production
```

#### 0.3 Ordnerstruktur für neue Module anlegen

Folgende leere `__init__.py`-Dateien erstellen (falls nicht vorhanden):
- `backend/app/routers/__init__.py`

---

### Schritt 1: Datenbank-Funktionen erweitern (`app/database.py`)

Alle neuen Funktionen ans Ende von `app/database.py` anhängen.
Bestehenden Code **nicht verändern**.

#### 1.1 `get_projects_list()`

```python
async def get_projects_list(
    tenant_id: UUID,
    limit: int = 20,
    cursor_created_at: datetime | None = None,
    cursor_id: UUID | None = None,
    status: str | None = None,
    building_type: str | None = None,
    search: str | None = None,
) -> list[dict]:
```

SQL-Logik:
```sql
SELECT id, tenant_id, status_id, client_name, address, building_type,
       project_type, created_at, updated_at, budget, planned_start
FROM projects
WHERE tenant_id = $1
  AND ($2::text IS NULL OR status_id = $2)
  AND ($3::text IS NULL OR building_type::text = $3)
  AND ($4::text IS NULL OR (client_name ILIKE '%' || $4 || '%' OR address ILIKE '%' || $4 || '%'))
  AND (
    $5::timestamptz IS NULL OR $6::uuid IS NULL
    OR (created_at, id) < ($5, $6)   -- Cursor-Bedingung für Pagination
  )
ORDER BY created_at DESC, id DESC
LIMIT $7
```

Rückgabe: Liste von Dicts. UUIDs als `str` konvertieren.

#### 1.2 `update_project()`

```python
async def update_project(
    project_id: UUID,
    tenant_id: UUID,
    fields: dict,  # Nur die zu ändernden Felder (kein None für unveränderte)
    changed_by_tenant_id: UUID,
) -> dict | None:
```

Logik:
1. Nur Felder in `fields` updaten, die explizit übergeben wurden (kein Überschreiben mit NULL bei nicht übergebenen Feldern)
2. Dynamisches SQL: `UPDATE projects SET field1=$1, field2=$2 WHERE id=$n AND tenant_id=$m RETURNING *`
3. Vorher alten Zustand lesen für Audit-Trail
4. Nach UPDATE einen Eintrag in `project_history` schreiben:
   ```sql
   INSERT INTO project_history (project_id, changed_by_user_id, changes)
   VALUES ($1, $2, $3::jsonb)
   ```
   `changes`-Format:
   ```json
   { "field_name": { "from": "alter_wert", "to": "neuer_wert" } }
   ```
5. Rückgabe: aktualisiertes Projekt als Dict

#### 1.3 `verify_project()`

```python
async def verify_project(
    project_id: UUID,
    tenant_id: UUID,
    changed_by_tenant_id: UUID,
) -> dict | None:
```

Logik:
1. Prüfen ob Projekt existiert und `status_id != 'verified_by_architect'`
2. `UPDATE projects SET status_id = 'verified_by_architect' WHERE id = $1 AND tenant_id = $2 RETURNING *`
3. Eintrag in `project_history`:
   ```json
   { "status_id": { "from": "<alter_status>", "to": "verified_by_architect" } }
   ```
4. Rückgabe: aktualisiertes Projekt

#### 1.4 `create_room()`

```python
async def create_room(
    project_id: UUID,
    tenant_id: UUID,
    room_type: str,
    quantity: int = 1,
    size_m2: float | None = None,
    special_requirements: str | None = None,
    changed_by_tenant_id: UUID | None = None,
) -> dict:
```

Logik:
1. Prüfen ob Projekt dem Tenant gehört: `SELECT id FROM projects WHERE id=$1 AND tenant_id=$2`
2. Prüfen ob `room_type` bereits existiert: `SELECT id FROM project_rooms WHERE project_id=$1 AND room_type=$2` → falls ja, HTTP 400
3. `INSERT INTO project_rooms (project_id, room_type, quantity, size_m2, special_requirements) VALUES (...) RETURNING *`
4. Eintrag in `project_history` (Action: Raum hinzugefügt):
   ```json
   { "room_added": { "room_type": "Küche", "quantity": 1 } }
   ```
5. Rückgabe: neuer Raum als Dict

#### 1.5 `update_room()`

```python
async def update_room(
    room_id: UUID,
    project_id: UUID,
    tenant_id: UUID,
    fields: dict,
    changed_by_tenant_id: UUID | None = None,
) -> dict | None:
```

Logik:
1. Prüfen ob Raum zum Projekt/Tenant gehört (JOIN mit projects)
2. Falls `room_type` geändert wird: Duplikat-Check (außer eigene ID)
3. Dynamisches UPDATE auf `project_rooms`
4. Eintrag in `project_history`
5. Rückgabe: aktualisierter Raum

#### 1.6 `delete_room()`

```python
async def delete_room(
    room_id: UUID,
    project_id: UUID,
    tenant_id: UUID,
    changed_by_tenant_id: UUID | None = None,
) -> bool:
```

Logik:
1. Prüfen ob Raum zum Projekt/Tenant gehört
2. `DELETE FROM project_rooms WHERE id=$1 AND project_id=$2`
3. Eintrag in `project_history`
4. Rückgabe: `True` wenn gelöscht, `False` wenn nicht gefunden

#### 1.7 `get_project_history()`

```python
async def get_project_history(
    project_id: UUID,
    tenant_id: UUID,
    limit: int = 50,
    cursor_changed_at: datetime | None = None,
    cursor_id: UUID | None = None,
) -> list[dict]:
```

SQL:
```sql
SELECT ph.id, ph.project_id, ph.changed_by_user_id, ph.changed_at, ph.changes
FROM project_history ph
JOIN projects p ON ph.project_id = p.id
WHERE ph.project_id = $1
  AND p.tenant_id = $2
  AND (
    $3::timestamptz IS NULL OR $4::uuid IS NULL
    OR (ph.changed_at, ph.id) < ($3, $4)
  )
ORDER BY ph.changed_at DESC, ph.id DESC
LIMIT $5
```

---

### Schritt 2: Pydantic Schemas erstellen

#### 2.1 `app/schemas/project.py` (neu erstellen)

```python
from datetime import date, datetime
from uuid import UUID
from pydantic import BaseModel, EmailStr

# --- Response-Schemas ---

class RoomResponse(BaseModel):
    id: str
    project_id: str
    room_type: str
    quantity: int
    size_m2: float | None
    special_requirements: str | None

class ProjectListItem(BaseModel):
    """Kompaktes Schema für die Projektliste."""
    id: str
    tenant_id: str
    status_id: str
    client_name: str | None
    address: str | None
    building_type: str | None
    project_type: str | None
    budget: float | None
    planned_start: date | None
    created_at: datetime
    updated_at: datetime

class ProjectDetail(BaseModel):
    """Vollständiges Schema für Projektdetails inkl. Räume."""
    id: str
    tenant_id: str
    status_id: str
    # Allgemeine Angaben
    client_name: str | None
    address: str | None
    phone: str | None
    email: str | None
    date: date | None
    # Grundstück
    plot_location: str | None
    plot_size_m2: float | None
    landowner: str | None
    topography: str | None
    topography_other: str | None
    development_plan: bool | None
    access_status: str | None
    # Vorstellungen
    project_type: str | None
    project_type_other: str | None
    building_type: str | None
    building_type_other: str | None
    construction_method: str | None
    heating_type: str | None
    heating_type_other: str | None
    budget: float | None
    planned_start: date | None
    own_contribution: str | None
    own_contribution_details: str | None
    # Besondere Hinweise
    accessibility: str | None
    outdoor_area: str | None
    materiality: str | None
    notes: str | None
    # Timestamps
    created_at: datetime
    updated_at: datetime
    # Räume (werden beim Laden mitgeliefert)
    rooms: list[RoomResponse] = []

class PaginationInfo(BaseModel):
    next_cursor: str | None
    has_more: bool

class ProjectListResponse(BaseModel):
    data: list[ProjectListItem]
    pagination: PaginationInfo

# --- Request-Schemas ---

class ProjectPatchRequest(BaseModel):
    """Alle Felder optional — nur übergebene Felder werden geändert."""
    client_name: str | None = None
    address: str | None = None
    phone: str | None = None
    email: str | None = None
    plot_location: str | None = None
    plot_size_m2: float | None = None
    landowner: str | None = None
    topography: str | None = None
    topography_other: str | None = None
    development_plan: bool | None = None
    access_status: str | None = None
    project_type: str | None = None
    project_type_other: str | None = None
    building_type: str | None = None
    building_type_other: str | None = None
    construction_method: str | None = None
    heating_type: str | None = None
    heating_type_other: str | None = None
    budget: float | None = None
    planned_start: date | None = None
    own_contribution: str | None = None
    own_contribution_details: str | None = None
    accessibility: str | None = None
    outdoor_area: str | None = None
    materiality: str | None = None
    notes: str | None = None

    model_config = {"extra": "forbid"}  # Unbekannte Felder ablehnen
```

**Wichtig für PATCH:** Das `ProjectPatchRequest`-Schema muss so behandelt werden, dass `None`
bedeutet "nicht übergeben" (kein Update), nicht "auf NULL setzen". Dafür `model.model_fields_set`
verwenden — nur Felder in `fields_set` an `update_project()` übergeben.

#### 2.2 `app/schemas/room.py` (neu erstellen)

```python
from pydantic import BaseModel, field_validator

class RoomCreateRequest(BaseModel):
    room_type: str
    quantity: int = 1
    size_m2: float | None = None
    special_requirements: str | None = None

    @field_validator("quantity")
    def quantity_must_be_positive(cls, v):
        if v <= 0:
            raise ValueError("quantity muss größer als 0 sein")
        return v

    @field_validator("size_m2")
    def size_must_be_non_negative(cls, v):
        if v is not None and v < 0:
            raise ValueError("size_m2 darf nicht negativ sein")
        return v

    model_config = {"extra": "forbid"}

class RoomPatchRequest(BaseModel):
    room_type: str | None = None
    quantity: int | None = None
    size_m2: float | None = None
    special_requirements: str | None = None

    @field_validator("quantity")
    def quantity_must_be_positive(cls, v):
        if v is not None and v <= 0:
            raise ValueError("quantity muss größer als 0 sein")
        return v

    model_config = {"extra": "forbid"}
```

---

### Schritt 3: Signed-URL-Service erstellen (`app/services/signed_urls.py`)

```python
"""
Signed URL Generierung und Validierung mit itsdangerous.

Token-Format: itsdangerous TimestampSigner
Token ist gebunden an: tenant_id + relativer Dateipfad
Ablaufzeit: 15 Minuten (konfigurierbar via settings.signed_url_expiry_seconds)
"""
from itsdangerous import TimestampSigner, BadSignature, SignatureExpired
from app.config import settings

def generate_signed_url(tenant_id: str, relative_path: str) -> tuple[str, str]:
    """
    Erzeugt eine Signed URL für eine Datei.

    Args:
        tenant_id: Tenant-UUID als String
        relative_path: Pfad relativ zu files/archive/, z.B. "{tenant_id}/{project_id}/original_xyz.pdf"

    Returns:
        Tuple: (vollständige URL mit Token, ISO-Ablaufzeitpunkt)
    """

def validate_signed_token(token: str, tenant_id: str, relative_path: str) -> bool:
    """
    Validiert ein Signed-URL-Token.

    Returns:
        True wenn gültig, False wenn abgelaufen oder ungültig
    """
```

Implementierungsdetails:
- `signer = TimestampSigner(settings.signed_url_secret, salt=f"{tenant_id}:{relative_path}")`
- Token = `signer.sign(relative_path)`
- URL = `f"{settings.files_base_url}/files/{relative_path}?token={token}"`
- Validierung: `signer.unsign(token, max_age=settings.signed_url_expiry_seconds)`

#### 3.1 Static File Serving mit Token-Validierung in `app/main.py`

Ein neuer Endpoint (kein `StaticFiles`-Mount, da Token-Validierung nötig):

```python
@app.get("/files/{file_path:path}", tags=["Files"])
async def serve_file(file_path: str, token: str, request: Request):
    """
    Liefert eine Datei aus dem Archiv — nur mit gültigem Token.

    file_path: relativer Pfad z.B. "{tenant_id}/{project_id}/original_xyz.pdf"
    token: Signed Token aus generate_signed_url()
    """
```

Logik:
1. Tenant-ID aus erstem Segment von `file_path` extrahieren
2. `validate_signed_token(token, tenant_id, file_path)` aufrufen
3. Bei ungültigem Token: HTTP 401
4. Absoluten Pfad bilden: `settings.archive_path / file_path`
5. Path-Traversal-Check: Pfad muss innerhalb `settings.archive_path` liegen
6. `FileResponse(absolute_path)` zurückgeben

---

### Schritt 4: Router — Projects (`app/routers/projects.py`)

Neue Datei erstellen. Alle 5 Endpoints implementieren.

#### 4.1 `GET /api/v1/projects`

```python
@router.get("/", response_model=ProjectListResponse)
async def list_projects(
    limit: int = Query(default=20, ge=1, le=100),
    cursor: str | None = Query(default=None),
    status: str | None = Query(default=None),
    building_type: str | None = Query(default=None),
    search: str | None = Query(default=None),
):
```

Cursor-Logik:
- Cursor dekodieren: `base64.b64decode(cursor)` → JSON `{"created_at": "...", "id": "..."}`
- `get_projects_list()` mit `limit + 1` aufrufen
- Wenn `len(results) > limit`: `has_more = True`, letztes Element abschneiden
- Nächsten Cursor aus letztem Element bilden und Base64-kodieren

#### 4.2 `GET /api/v1/projects/{project_id}`

```python
@router.get("/{project_id}", response_model=ProjectDetail)
async def get_project(project_id: str):
```

Logik:
- Bestehende `get_project_by_id()` aus `database.py` verwenden
- Tenant-ID aus `get_current_tenant()` holen (nicht aus Settings!)
- 404 wenn nicht gefunden

#### 4.3 `PATCH /api/v1/projects/{project_id}`

```python
@router.patch("/{project_id}", response_model=ProjectDetail)
async def patch_project(project_id: str, body: ProjectPatchRequest):
```

Logik:
- `body.model_fields_set` → nur explizit übergebene Felder extrahieren
- Wenn `fields_set` leer: HTTP 400 "Keine Felder zum Aktualisieren"
- `update_project(fields=dict mit nur den gesetzten Feldern)` aufrufen

#### 4.4 `POST /api/v1/projects/{project_id}/verify`

```python
@router.post("/{project_id}/verify", response_model=ProjectDetail)
async def verify_project(project_id: str):
```

Logik:
- `verify_project()` aus `database.py` aufrufen
- 404 wenn nicht gefunden
- 400 wenn bereits `verified_by_architect`

#### 4.5 `GET /api/v1/projects/{project_id}/history`

```python
@router.get("/{project_id}/history")
async def get_project_history(
    project_id: str,
    limit: int = Query(default=50, ge=1, le=200),
    cursor: str | None = Query(default=None),
):
```

Response-Format:
```json
{
  "data": [
    {
      "id": "uuid",
      "changed_at": "2026-03-07T14:30:00Z",
      "changed_by_tenant_id": "uuid",
      "changes": { "client_name": { "from": "alt", "to": "neu" } }
    }
  ],
  "pagination": { "next_cursor": "...", "has_more": false }
}
```

---

### Schritt 5: Router — Files (`app/routers/files.py`)

Neue Datei erstellen.

#### 5.1 `GET /api/v1/projects/{project_id}/pdf`

```python
@router.get("/{project_id}/pdf")
async def get_pdf_url(project_id: str):
```

Logik:
1. Projekt laden (mit Tenant-Check)
2. `project["pdf_path"]` lesen — wenn `None`: HTTP 404 "Kein PDF vorhanden"
3. Relativen Pfad aus absolutem `pdf_path` ableiten (relativ zu `settings.archive_path`)
4. `generate_signed_url(tenant_id, relative_path)` aufrufen

Response:
```json
{
  "url": "http://localhost:8000/files/{tenant_id}/{project_id}/original_xyz.pdf?token=...",
  "expires_at": "2026-03-07T15:00:00Z",
  "filename": "original_xyz.pdf"
}
```

#### 5.2 `GET /api/v1/projects/{project_id}/pages`

```python
@router.get("/{project_id}/pages")
async def get_page_urls(project_id: str):
```

Logik:
1. Projekt laden
2. `project["page_paths"]` lesen (JSONB-Array aus DB) — wenn `None` oder leer: leere Liste
3. Für jeden Pfad `generate_signed_url()` aufrufen

Response:
```json
{
  "pages": [
    {
      "page_number": 1,
      "url": "http://localhost:8000/files/.../page_001_xyz.png?token=...",
      "expires_at": "2026-03-07T15:00:00Z",
      "filename": "page_001_xyz.png"
    }
  ],
  "total_pages": 3
}
```

---

### Schritt 6: Router — Rooms (`app/routers/rooms.py`)

Neue Datei erstellen. Der Router wird mit Prefix `/api/v1/projects` eingebunden.

#### 6.1 `POST /api/v1/projects/{project_id}/rooms`

```python
@router.post("/{project_id}/rooms", response_model=RoomResponse, status_code=201)
async def create_room(project_id: str, body: RoomCreateRequest):
```

Fehlerbehandlung:
- Projekt nicht gefunden → 404
- `room_type` bereits vorhanden → 400 mit Message: `"Raum '{room_type}' existiert bereits in diesem Projekt"`

#### 6.2 `PATCH /api/v1/projects/{project_id}/rooms/{room_id}`

```python
@router.patch("/{project_id}/rooms/{room_id}", response_model=RoomResponse)
async def patch_room(project_id: str, room_id: str, body: RoomPatchRequest):
```

Logik:
- `body.model_fields_set` für partielle Updates
- Duplikat-Check bei `room_type`-Änderung (darf nicht gleich wie ein anderer Raum im Projekt sein)

#### 6.3 `DELETE /api/v1/projects/{project_id}/rooms/{room_id}`

```python
@router.delete("/{project_id}/rooms/{room_id}", status_code=204)
async def delete_room(project_id: str, room_id: str):
```

---

### Schritt 7: Router — Jobs (`app/routers/jobs.py`)

Neue Datei erstellen. **Bestehende Job-Endpoints aus `main.py` werden hierher verschoben** und erhalten den Prefix `/api/v1/jobs`.

Folgende Endpoints aus `main.py` **ausschneiden** und in `jobs.py` **einfügen**:
- `GET /jobs` → wird zu `GET /` (mit Prefix `/api/v1/jobs`)
- `GET /jobs/{job_id}` → wird zu `GET /{job_id}`
- `POST /jobs/retrigger` → wird zu `POST /retrigger`
- `GET /queue/stats` → wird zu `GET /stats` (unter `/api/v1/jobs/stats`)

Auch `JobStatusResponse` und `QueueStatsResponse` aus `main.py` in `app/schemas/job.py` auslagern.

---

### Schritt 8: `app/main.py` anpassen

#### 8.1 Alle Router einbinden

```python
from app.routers import projects, rooms, files, jobs

app.include_router(projects.router, prefix="/api/v1/projects", tags=["Projekte"])
app.include_router(rooms.router, prefix="/api/v1/projects", tags=["Räume"])
app.include_router(files.router, prefix="/api/v1/projects", tags=["Dateien"])
app.include_router(jobs.router, prefix="/api/v1/jobs", tags=["Jobs"])
```

#### 8.2 Alte Endpoints entfernen

Folgende Endpoints aus `main.py` **löschen** (werden durch Router ersetzt):
- `GET /jobs`
- `GET /jobs/{job_id}`
- `POST /jobs/retrigger`
- `GET /queue/stats`
- `GET /projects/{project_id}` (alter Endpoint ohne `/api/v1/`)

Folgende Endpoints **behalten** (bereits korrekt):
- `GET /health`
- `GET /api/v1/tenants/me`
- `GET /api/v1/auth/test`
- Neuer `GET /files/{file_path:path}` (aus Schritt 3.1)

#### 8.3 `sanitize_path()` in `file_utils.py` verschieben

Die Hilfsfunktion `sanitize_path()` aus `main.py` nach `app/file_utils.py` verschieben,
da sie nun auch im Jobs-Router und File-Serving benötigt wird.

---

### Schritt 9: Tests

Nach der Implementierung folgende Szenarien mit `curl` oder dem Swagger UI (`/docs`) testen:

**Projekte:**
```bash
# Liste
curl -H "X-API-Key: sk-tenant-...-a1b2c3d4..." http://localhost:8000/api/v1/projects

# Mit Filter
curl -H "X-API-Key: ..." "http://localhost:8000/api/v1/projects?status=needs_review&search=müller"

# Details
curl -H "X-API-Key: ..." http://localhost:8000/api/v1/projects/{id}

# PATCH
curl -X PATCH -H "X-API-Key: ..." -H "Content-Type: application/json" \
  -d '{"client_name": "Familie Mustermann"}' \
  http://localhost:8000/api/v1/projects/{id}

# Verify
curl -X POST -H "X-API-Key: ..." http://localhost:8000/api/v1/projects/{id}/verify
```

**Räume:**
```bash
# Erstellen
curl -X POST -H "X-API-Key: ..." -H "Content-Type: application/json" \
  -d '{"room_type": "Küche", "quantity": 1, "size_m2": 18.5}' \
  http://localhost:8000/api/v1/projects/{id}/rooms

# Duplikat (soll 400 geben)
# Bearbeiten
# Löschen
```

**Dateien:**
```bash
curl -H "X-API-Key: ..." http://localhost:8000/api/v1/projects/{id}/pdf
curl -H "X-API-Key: ..." http://localhost:8000/api/v1/projects/{id}/pages
# Signed URL aufrufen (ohne API-Key, nur Token)
```

**Jobs:**
```bash
curl -H "X-API-Key: ..." http://localhost:8000/api/v1/jobs
curl -H "X-API-Key: ..." http://localhost:8000/api/v1/jobs/{job_id}
```

---

## Abhängigkeits-Reihenfolge

```
Schritt 0: Vorbereitung (Config, Dependencies)
    │
    ├── Schritt 1: DB-Funktionen
    │       │
    │       ├── Schritt 2: Schemas
    │       │       │
    │       │       ├── Schritt 3: Signed-URL-Service
    │       │       │       │
    │       │       │       ├── Schritt 4: Router Projects
    │       │       │       ├── Schritt 5: Router Files
    │       │       │       └── Schritt 6: Router Rooms
    │       │
    │       └── Schritt 7: Router Jobs (Umzug)
    │
    └── Schritt 8: main.py anpassen (alle Router einbinden, alte Endpoints entfernen)
            │
            └── Schritt 9: Tests
```

---

## Neue Dateien (Übersicht)

| Datei | Inhalt |
|-------|--------|
| `app/routers/__init__.py` | Leere Init-Datei |
| `app/routers/projects.py` | GET list, GET detail, PATCH, POST verify, GET history |
| `app/routers/rooms.py` | POST, PATCH, DELETE rooms |
| `app/routers/files.py` | GET pdf, GET pages |
| `app/routers/jobs.py` | Umgezogene Job-Endpoints |
| `app/schemas/project.py` | ProjectListItem, ProjectDetail, ProjectPatchRequest, etc. |
| `app/schemas/room.py` | RoomCreateRequest, RoomPatchRequest, RoomResponse |
| `app/schemas/job.py` | JobStatusResponse, QueueStatsResponse (ausgelagert aus main.py) |
| `app/services/signed_urls.py` | generate_signed_url(), validate_signed_token() |

## Geänderte Dateien (Übersicht)

| Datei | Änderung |
|-------|----------|
| `app/config.py` | `files_base_url`, `signed_url_secret`, `signed_url_expiry_seconds` hinzufügen |
| `app/database.py` | 7 neue Funktionen anhängen (bestehenden Code nicht anfassen) |
| `app/file_utils.py` | `sanitize_path()` von `main.py` hierher verschieben |
| `app/main.py` | Router einbinden, alte Endpoints entfernen, `/files/{path}` hinzufügen |
| `requirements.txt` | `itsdangerous>=2.1.0` hinzufügen |
| `.env.example` | `FILES_BASE_URL`, `SIGNED_URL_SECRET` hinzufügen |

---

*Erstellt: 2026-03-07 | Aktualisiert: 2026-03-14*
*Status: Planung abgeschlossen — bereit zur Implementierung*
