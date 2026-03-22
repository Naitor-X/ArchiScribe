~~~~~~~
Problematiken sollten eigentlich geklärt sein. Dieses Dokument wird nur vollständigkeitshalber aubewahrt. 'depricated'
~~~~~
# Performance-Problem: Langsames Frontend bei API-Datenabfrage

## Tech-Stack

**Backend:**
- Python 3.12 mit FastAPI
- PostgreSQL mit asyncpg (async driver)
- Connection Pooling (min 2, max 10 connections)
- Pydantic für Request/Response Validation

**Frontend:**
- Vanilla JavaScript (kein Framework) - künftig aber Umstieg auf react / next.js
- Klassisches HTML/CSS
- Fetch API für HTTP-Requests
- Single-Page-ähnliche Navigation zwischen Liste und Detailansicht

**Daten:**
- ~100 Projekte in der Datenbank
- Jedes Projekt hat ~30 Felder + 1:N Relation zu Räumen (project_rooms)
- PostgreSQL-Indizes auf tenant_id, status_id, created_at vorhanden

## Problem

Das Frontend fühlt sich "lahm" an. Die Projektliste lädt spürbar langsam.

## Was bereits versucht wurde

1. **Backend-Serialisierung optimiert:**
   - Statt 30+ Felder einzeln zu kopieren, jetzt `**dict` pattern
   - Neues `ProjectListItem` Schema mit nur 5 Feldern für Listen-Endpoint

2. **Frontend-Caching (wieder verworfen):**
   - SessionStorage-Caching implementiert
   - Problem: Veraltete Daten bei Änderungen durch andere Prozesse/User
   - Caching auf Client-Seite scheint nicht der richtige Ansatz zu sein

## Frage an das Premium LLM

1. **Was ist der Industriestandard** für performante Datenabfrage in einer solchen Architektur (FastAPI + PostgreSQL + Vanilla JS)?

2. **Wo sollte Caching stattfinden** - Client, Server (Redis), Datenbank, oder gar nicht?

3. **Gibt es Best Practices** für:
   - Pagination Strategien
   - Lazy Loading
   - Optimistic UI Updates
   - Debouncing/Throttling bei Filter-Änderungen

4. **Sollte man für dieses Szenario eine Frontend-Library nutzen** wie TanStack Query, oder ist das Overkill für Vanilla JS?

5. **Performance-Profiling:** Wie kann man systematisch herausfinden, wo genau die Langsamkeit liegt (Backend vs. Netzwerk vs. Frontend-Rendering)?

## Kontext

- Multi-Tenant SaaS (Mandanten-Trennung via tenant_id)
- Daten werden durch einen Background-Service (PDF-Verarbeitung) hinzugefügt
- Frontend ist primär "Read-Heavy" - viel Anzeigen, wenig Schreiben
- Typischer User-Workflow: Liste durchsehen → Projekt öffnen → Verifizieren

## Aktuelle API-Struktur

```
GET /api/v1/projects              # Liste (paginiert, filterbar nach Status)
GET /api/v1/projects/{id}         # Detail mit Räumen und AI-Extraktion
PUT /api/v1/projects/{id}         # Update
PATCH /api/v1/projects/{id}/status # Status ändern
```

## Gewünschter Outcome

Empfehlung für eine saubere, wartbare Architektur die:
- Schnell genug für gute UX ist (< 200ms gefühlte Latenz)
- Nicht over-engineered ist
- Dem Industriestandard entspricht
- Mit Vanilla JS funktioniert (oder begründete Empfehlung für eine Library)
