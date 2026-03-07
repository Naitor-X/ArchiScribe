# API-Endpoints: REST-API für Frontend-Integration

## Ziel

RESTful API für Architekten-Frontend:
- Projektdaten abrufen und bearbeiten
- PDF/PNG-Vorschau mit Signed URLs
- Audit-Trail für Änderungen
- Verarbeitungsstatus überwachen

---

## Architektur-Entscheidungen

### Übersicht

| Thema | Entscheidung |
|-------|--------------|
| Tenant-Identifikation | Header `X-Tenant-ID` + API-Key-Fallback |
| Authentifizierung | API-Key via `X-API-Key` Header |
| Versionierung | URL-Prefix `/api/v1/...` |
| Response-Format | Direkte Daten + HTTP-Status-Codes |
| Pagination | Cursor-basiert |
| Datei-Zugriff | Signed URLs mit Ablaufzeit |
| Sorting/Filtering | Query-Parameter |
| Dokumentation | OpenAPI/Swagger UI (automatisch) |

### Request/Response Beispiele

**Erfolgreiche Response:**
```json
GET /api/v1/projects/abc-123

HTTP 200 OK
{
  "id": "abc-123",
  "tenant_id": "tenant-001",
  "project_number": "2026-001",
  "name": "Neubau Familie Müller",
  "status": "needs_review",
  "building_type": "neubau",
  ...
}
```

**Fehler-Response:**
```json
HTTP 404 Not Found
{
  "error": "not_found",
  "message": "Projekt nicht gefunden",
  "details": { "project_id": "abc-123" }
}
```

**Paginierte Liste:**
```json
GET /api/v1/projects?limit=20&cursor=xyz

HTTP 200 OK
{
  "data": [...],
  "pagination": {
    "next_cursor": "abc456",
    "prev_cursor": null,
    "has_more": true
  }
}
```

**Signed URL Response:**
```json
GET /api/v1/projects/abc-123/pdf

HTTP 200 OK
{
  "url": "http://localhost:8000/files/archive/tenant-001/abc-123/original_20260307_143022.pdf?token=xyz&expires=1709820000",
  "expires_at": "2026-03-07T15:00:00Z",
  "filename": "original_20260307_143022.pdf"
}
```

---

## Endpunkt-Übersicht

```
/api/v1/
│
├── projects/
│   ├── GET    /                           # Liste (paginiert, filterbar)
│   ├── GET    /{id}                       # Details + Räume
│   ├── PATCH  /{id}                       # Architekt-Änderungen
│   ├── POST   /{id}/verify                # Status → verified_by_architect
│   ├── GET    /{id}/pdf                   # Signed URL für PDF
│   ├── GET    /{id}/pages                 # Signed URLs für PNGs
│   ├── GET    /{id}/history               # Audit-Trail
│   │
│   └── rooms/
│       ├── POST   /{project_id}/rooms     # Neuer Raum
│       ├── PATCH  /{project_id}/rooms/{id} # Raum bearbeiten
│       └── DELETE /{project_id}/rooms/{id} # Raum löschen
│
├── jobs/
│   ├── GET    /                           # Alle Verarbeitungsjobs
│   ├── GET    /{id}                       # Job-Status (existiert bereits)
│   └── POST   /retrigger                  # Neuverarbeitung (existiert bereits)
│
└── tenants/
    └── GET    /me                         # Eigene Tenant-Infos
```

---

## Untermodule

### 2.1 Auth & Middleware

**Ziel:** API-Key-Validierung, Tenant-Extraktion, Error-Handling

| Task | Beschreibung | Status |
|------|--------------|--------|
| 2.1.1 | API-Key Middleware implementieren | ⬜ |
| 2.1.2 | Tenant-Extraktion (Header + API-Key-Fallback) | ⬜ |
| 2.1.3 | Unified Error Handler mit Standard-Format | ⬜ |
| 2.1.4 | Request-Logging für Debugging | ⬜ |
| 2.1.5 | Rate-Limiting (optional, später) | ⬜ |

**Abhängigkeiten:** Keine

**Module:**
- `app/middleware/auth.py` - API-Key-Validierung
- `app/middleware/tenant.py` - Tenant-Extraktion
- `app/middleware/error_handler.py` - Error-Responses

**Headers:**
```
X-API-Key: sk-tenant-001-abc123...
X-Tenant-ID: tenant-001  (optional, falls nicht im API-Key enthalten)
```

---

### 2.2 Project Endpoints

**Ziel:** CRUD für Projekte mit Filter/Sort/Pagination

| Task | Beschreibung | Status |
|------|--------------|--------|
| 2.2.1 | `GET /projects` - Liste mit Cursor-Pagination | ⬜ |
| 2.2.2 | Filter-Parameter (status, building_type, search) | ⬜ |
| 2.2.3 | Sort-Parameter (created_at, name, status) | ⬜ |
| 2.2.4 | `GET /projects/{id}` - Details mit Räumen | ⬜ |
| 2.2.5 | `PATCH /projects/{id}` - Teilweise Updates | ⬜ |
| 2.2.6 | `POST /projects/{id}/verify` - Status-Änderung | ⬜ |
| 2.2.7 | Pydantic-Models für Request/Response | ⬜ |

**Abhängigkeiten:** 2.1

**Module:**
- `app/routers/projects.py` - Router mit allen Endpoints
- `app/schemas/project.py` - Request/Response-Models

**Query-Parameter für Liste:**
```
GET /api/v1/projects?
    limit=20&
    cursor=abc123&
    status=needs_review&
    building_type=neubau&
    search=müller&
    sort=created_at:desc
```

---

### 2.3 Room Endpoints

**Ziel:** Einzelne Raum-Bearbeitung

| Task | Beschreibung | Status |
|------|--------------|--------|
| 2.3.1 | `POST /projects/{id}/rooms` - Neuen Raum anlegen | ⬜ |
| 2.3.2 | `PATCH /projects/{id}/rooms/{room_id}` - Raum bearbeiten | ⬜ |
| 2.3.3 | `DELETE /projects/{id}/rooms/{room_id}` - Raum löschen | ⬜ |
| 2.3.4 | Validation: Keine doppelten Raum-Namen | ⬜ |
| 2.3.5 | Audit-Trail für Raum-Änderungen | ⬜ |

**Abhängigkeiten:** 2.2

**Module:**
- `app/routers/rooms.py` - Router für Raum-Endpoints
- `app/schemas/room.py` - Request/Response-Models

**Request-Beispiel:**
```json
POST /api/v1/projects/abc-123/rooms
{
  "name": "Küche",
  "area_m2": 18.5,
  "floor": "EG",
  "notes": "Mit Insel"
}
```

---

### 2.4 File Endpoints

**Ziel:** Signed URLs für PDF und PNG-Zugriff

| Task | Beschreibung | Status |
|------|--------------|--------|
| 2.4.1 | `GET /projects/{id}/pdf` - Signed URL für PDF | ⬜ |
| 2.4.2 | `GET /projects/{id}/pages` - Signed URLs für alle PNGs | ⬜ |
| 2.4.3 | Token-Generierung mit Ablaufzeit (15 min) | ⬜ |
| 2.4.4 | Static-File-Server mit Token-Validierung | ⬜ |
| 2.4.5 | Optional: Single-Page URL `GET /projects/{id}/pages/{num}` | ⬜ |

**Abhängigkeiten:** 2.2

**Module:**
- `app/routers/files.py` - File-Endpoints
- `app/services/signed_urls.py` - Token-Generierung

**Sicherheit:**
- Tokens laufen nach 15 Minuten ab
- Tokens sind an Tenant gebunden
- Tokens sind an spezifische Datei gebunden

---

### 2.5 History Endpoint

**Ziel:** Audit-Trail für Projekt-Änderungen

| Task | Beschreibung | Status |
|------|--------------|--------|
| 2.5.1 | `GET /projects/{id}/history` - Alle Änderungen | ⬜ |
| 2.5.2 | Pagination für History (viele Einträge möglich) | ⬜ |
| 2.5.3 | Filter nach changed_by, changed_at | ⬜ |

**Abhängigkeiten:** 2.2

**Module:**
- Erweiterung `app/routers/projects.py`
- Erweiterung `app/database.py` - `get_project_history()`

**Response-Beispiel:**
```json
{
  "data": [
    {
      "id": "hist-001",
      "changed_at": "2026-03-07T14:30:00Z",
      "changed_by": "architect",
      "action": "update",
      "changes": {
        "status": { "from": "needs_review", "to": "verified_by_architect" }
      }
    }
  ],
  "pagination": { ... }
}
```

---

### 2.6 Job & Tenant Endpoints

**Ziel:** Verarbeitungsstatus und Tenant-Infos

| Task | Beschreibung | Status |
|------|--------------|--------|
| 2.6.1 | `GET /jobs` - Liste aller Jobs (bereits teilweise vorhanden) | ⬜ |
| 2.6.2 | `GET /tenants/me` - Aktuelle Tenant-Infos | ⬜ |
| 2.6.3 | Tenant-Settings erweiterbar machen | ⬜ |

**Abhängigkeiten:** 2.1

**Module:**
- `app/routers/jobs.py` - Jobs (teilweise vorhanden)
- `app/routers/tenants.py` - Tenant-Endpoint

---

## Abhängigkeits-Diagramm

```
2.1 Auth & Middleware
    │
    ├──> 2.2 Project Endpoints
    │         │
    │         ├──> 2.3 Room Endpoints
    │         │
    │         ├──> 2.4 File Endpoints
    │         │
    │         └──> 2.5 History Endpoint
    │
    └──> 2.6 Job & Tenant Endpoints
```

---

## Technologie-Stack

| Komponente | Technologie |
|------------|-------------|
| API-Framework | FastAPI |
| Validierung | Pydantic v2 |
| Auth-Middleware | Custom + API-Key |
| File-Server | FastAPI StaticFiles |
| Token-Generierung | itsdangerous oder PyJWT |

---

## Neue Dependencies

```
itsdangerous>=2.1.0    # Für Signed URLs
# oder
PyJWT>=2.8.0           # Alternative für JWT-basierte Tokens
```

---

## HTTP-Status-Codes

| Code | Verwendung |
|------|------------|
| 200 | Erfolgreiche GET/PATCH |
| 201 | Erfolgreiche POST (neue Ressource) |
| 204 | Erfolgreiche DELETE (kein Content) |
| 400 | Validierungsfehler |
| 401 | Fehlender/ungültiger API-Key |
| 403 | Kein Zugriff auf diese Tenant |
| 404 | Ressource nicht gefunden |
| 422 | Pydantic-Validierungsfehler |
| 429 | Rate Limit überschritten |
| 500 | Server-Fehler |

---

## Offene Fragen

- [ ] API-Key-Format definieren (z.B. `sk-tenant-{id}-{random}`)
- [ ] Token-Ablaufzeit für Signed URLs (15 min okay?)
- [ ] Sollen API-Keys in DB oder Environment gespeichert werden?
- [ ] Rate-Limiting bereits implementieren?

---

## Erweiterbarkeit

Diese Architektur unterstützt:

| Szenario | Umsetzung |
|----------|-----------|
| Neue Module | Einfach neuer Router (z.B. `/api/v1/invoices`) |
| Neue Version | `/api/v2/` parallel zu `/api/v1/` |
| JWT-Auth | Middleware kann erweitert werden |
| S3-Storage | Signed URLs funktionieren identisch |
| Subdomain-Tenants | Header-Logik bleibt gleich |

---

*Erstellt: 2026-03-07*
*Status: Planung abgeschlossen, Implementierung ausstehend*
