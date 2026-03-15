# Frontend-Plan: ArchiScribe

## Ziel

Minimales, funktionales Frontend für Architekturbüros zur Verifizierung von KI-extrahierten Grundlagenformularen.

**Grundprinzip:** Einfach vor schön. Nur das Notwendigste zuerst.

---

## Tech-Stack

- **Technologie:** Vanilla HTML + CSS + JavaScript (kein Framework, kein Build-Tool)
- **Auslieferung:** FastAPI serviert das Frontend als statische Dateien (`StaticFiles`)
- **API-Kommunikation:** Native `fetch()` API gegen den bestehenden FastAPI-Backend

---

## Projektstruktur

```
frontend/
├── index.html          # Projektliste (Landing Page)
├── project.html        # Projektdetail + Verifizierung
├── css/
│   └── style.css       # Gemeinsames Styling
└── js/
    ├── api.js          # API-Client (fetch-Wrapper, Auth-Header)
    ├── list.js         # Logik für Projektliste
    └── detail.js       # Logik für Projektdetail
```

---

## Implementierungsschritte

### Schritt 1: Grundstruktur & FastAPI-Integration
- [ ] `frontend/` Ordner anlegen
- [ ] FastAPI: `StaticFiles` unter `/` mounten
- [ ] API-Client (`api.js`) mit API-Key-Header und Basis-URL

### Schritt 2: View 1 – Projektliste (`index.html`)
- [ ] Tabelle: Projektname, Adresse, Status-Badge, Erstellungsdatum
- [ ] Status-Filter (Dropdown: alle / `needs_review` / `verified_by_architect`)
- [ ] Klick auf Zeile → navigiert zu `project.html?id={uuid}`
- [ ] API-Endpunkt: `GET /projects`

### Schritt 3: View 2 – Projektdetail (`project.html`)
- [ ] Formular mit allen extrahierten KI-Daten (editierbar)
- [ ] Raumprogramm als separate Sektion (Räume anzeigen)
- [ ] Button "Speichern" → `PUT /projects/{id}`
- [ ] Button "Als verifiziert markieren" → `PATCH /projects/{id}/status`
- [ ] API-Endpunkt: `GET /projects/{id}`

---

## API-Endpunkte (bereits vorhanden)

| Endpunkt | Methode | Verwendet in |
|----------|---------|--------------|
| `/projects` | GET | Projektliste |
| `/projects/{id}` | GET | Projektdetail |
| `/projects/{id}` | PUT | Daten speichern |
| `/projects/{id}/status` | PATCH | Status verifizieren |

---

## Status-Workflow (visuell)

```
raw_extracted  →  needs_review  →  verified_by_architect
   (grau)           (orange)            (grün)
```

---

## Bewusst weggelassen (MVP)

- Kein Login / keine Session-Verwaltung (API-Key hardcoded für Dev)
- Kein CSS-Framework (Bootstrap, Tailwind etc.)
- Keine Raum-Bearbeitung (nur Anzeige)
- Keine Paginierung (vorerst)
- Kein Scan-Upload im Frontend (läuft weiterhin über Backend/Inbox)
