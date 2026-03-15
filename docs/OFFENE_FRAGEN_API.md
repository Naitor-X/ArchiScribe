# Offene Fragen zur API-Implementierung

Bitte die Antworten direkt in die jeweiligen Felder eintragen.

---

## 2.4 File Endpoints

### Frage A: Wo liegen die archivierten Dateien?

Der Plan nennt `/files/archive/{tenant_id}/{process_id}/` als Pfad.
Ist diese Ordnerstruktur korrekt, oder weicht die tatsächliche Struktur davon ab?

Zum Vergleich – im Code (`file_utils.py`) wird die Struktur so aufgebaut:
Später wird das Projekt als dockercontainer deployed. Wir müssen dann halt später entsprechend den Pfad /fies aus dem docker hinaus mappen. aber grundsätzlich wird der ordner /files so bleiben mit den unterordnern. 
wir werden hier glaube ich schon noch eine tenant_id ebene einziehen müssen. sieh das bitte vor und wir müsse ndas vor der api implementierung noch in das erste modul einbauen. damit wir hier eine schöne Trennung der Datein haben. 
```
files/
├── inbox/
├── processing/{process_id}/
├── archive/{process_id}/      ← tenant_id-Ebene vorhanden?
└── error/
```

**Antwort:**

---

### Frage B: Wohin sollen die Signed URLs zeigen?

Option 1 – **Lokaler Static-File-Server** (FastAPI `StaticFiles`):
- URL: `http://localhost:8000/files/archive/.../original.pdf?token=xyz`
- Einfach umzusetzen, kein externer Dienst nötig
- Nur sinnvoll solange Dateien lokal auf dem Server liegen

Option 2 – **Externer Speicher (z.B. S3, MinIO)**:
- URL: `https://s3.example.com/bucket/...?token=xyz`
- Erfordert S3-kompatiblen Dienst

Für den aktuellen MVP: Welche Option soll umgesetzt werden?

**Antwort:**
hier ist es wieder wichtig, dass wir im hinterkopf behlaten, dass wir das ganze in einem docker deployen. ich weiß im moment noch nicht , auf welche URL die Anfrage später genau kommt. wir könnten es sinnvoll auf localhost: mit dezidiertem port machen, sodass wir es einfach später über die docker yaml mappen können oder?
---

### Frage C: Wie heißen die PNG-Dateien für einzelne Seiten?

Der Endpoint `GET /projects/{id}/pages` soll Signed URLs für alle Seiten-PNGs zurückgeben.
Wie heißen die PNG-Dateien? (z.B. `page_1.png`, `page_01.png`, `seite_1.png`, …?)

**Antwort:**
---
diese informationen solltest du selbstständig aus dem hauptmodul 1 exrahieren können. sieh bitte nach wie genau das erste modul die seiten bennent. 

## 2.5 History Endpoint

### Frage D: Was soll im Feld `changed_by` stehen?

Die DB-Tabelle `project_history` hat ein Feld `changed_by_user_id UUID`.
Aktuell gibt es keine Benutzerkonten – nur API-Keys pro Tenant.

Optionen:
- **API-Key-ID**: Die UUID des verwendeten API-Keys (`api_keys.id`)
- **Key-Name**: Der lesbare Name des Keys (z.B. "Frontend-Dev", "Produktion")
- **Tenant-ID**: Einfach die Tenant-ID (weniger granular)
- **Leer lassen**: `NULL` bis echte User existieren

**Antwort:**
TenantID macht am meisten sinn vorerst!
---

## 2.6 Job & Tenant Endpoints

### Frage E: Soll `/jobs` nach `/api/v1/jobs` verschoben werden?

Aktuell existieren diese Endpunkte **ohne** `/api/v1/`-Prefix:
- `GET /jobs`
- `GET /jobs/{job_id}`
- `POST /jobs/retrigger`
- `GET /queue/stats`

Der Plan sieht sie unter `/api/v1/jobs/` vor.

Optionen:
- **Umziehen**: Alte Pfade entfernen, neue unter `/api/v1/` anlegen
- **Parallel**: Beide Pfade behalten (alter bleibt für Rückwärtskompatibilität)
- **Lassen wie es ist**: Kein Umzug, `/api/v1/` nur für neue Endpoints

**Antwort:** wir macheh hier die sauberste lösung bitte
