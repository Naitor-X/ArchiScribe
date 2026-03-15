# Projekt-Felder: Editierbarkeit via PATCH /projects/{id}

Bitte für jedes Feld "Ja" oder "Nein" in der Spalte **Editierbar** eintragen.

> **Nicht aufgeführt** (immer schreibgeschützt): `id`, `tenant_id`, `pdf_path`, `page_paths`, `created_at`, `updated_at`
> **Eigener Endpoint**: `status_id` → via `POST /projects/{id}/verify`

---

## Allgemeine Angaben

| Feld | Typ | Beschreibung | Editierbar |
|------|-----|--------------|------------|
| `address` | Text | Adresse des Bauherrn | ja |
| `client_name` | Text | Name des Bauherrn | ja |
| `phone` | Text | Telefonnummer | ja |
| `email` | Text | E-Mail-Adresse |  ja |
| `date` | Datum | Datum des Formulars |nein |

---

## Grundstück

| Feld | Typ | Beschreibung | Editierbar |
|------|-----|--------------|------------|
| `plot_location` | Text | Lage des Grundstücks |   ja |
| `plot_size_m2` | Zahl | Grundstücksgröße in m² | ja |
| `landowner` | Text | Grundeigentümer | ja |
| `topography` | Enum | Topografie (`eben`, `leichte Hanglage`, `starke Hanglage`, `Sonstiges`) | ja |
| `development_plan` | Boolean | Bebauungsplan vorhanden? | ja |
| `topography_other` | Text | Topografie – Freitextfeld bei "Sonstiges" | ja k|
| `access_status` | Enum | Erschließung (`voll erschlossen`, `teilerschlossen`, `nicht erschlossen`) | ja |

---

## Vorstellungen / Ziele

| Feld | Typ | Beschreibung | Editierbar |
|------|-----|--------------|------------|
| `project_type` | Enum | Projektart (`Neubau`, `Bauen im Bestand`, `Umbau im Inneren`, …) | ja |
| `project_type_other` | Text | Projektart – Freitextfeld bei "Sonstiges" | ja |
| `building_type_other` | Text | Gebäudetyp – Freitextfeld bei "Sonstige" |ja  |
| `building_type` | Enum | Gebäudetyp (`EFH`, `Doppelhaus`, `Reihenhaus`, `Mehrfamilienhaus`, `Sonstige`) | ja |
| `construction_method` | Enum | Bauweise (`Massivbau`, `Holzbau`, `noch offen`) | ja |
| `heating_type` | Enum | Heizungsart (`Wärmepumpe`, `Gasheizung`, `Fernwärme`, `Holz/Pellets`, `Sonstige`) |ja| 
| `heating_type_other` | Text | Heizungsart – Freitextfeld bei "Sonstige" | ja |
| `budget` | Zahl | Budget in € | |ja 
| `planned_start` | Datum | Geplanter Baubeginn | ja |
| `own_contribution` | Enum | Eigenleistung (`ja`, `nein`, `teilweise`) | ja |
| `own_contribution_details` | Text | Eigenleistung – Details | ja |

---

## Besondere Hinweise

| Feld | Typ | Beschreibung | Editierbar |
|------|-----|--------------|------------|
| `accessibility` | Enum | Barrierefreiheit (`wichtig`, `optional`, `nicht relevant`) | ja |
| `outdoor_area` | Text | Außenbereich / Garten | ja |
| `materiality` | Text | Materialwünsche | ja |
| `notes` | Text | Sonstige Notizen | ja |
