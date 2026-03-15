# ArchiScribe – Grundlagenformular: Mapping zu VM.OA.2014 Komplexitätskriterien

> Dieses Dokument beschreibt, wie die Felder des Grundlagenformulars (und der
> bestehenden ArchiScribe-Datenbank) auf die Bewertungskriterien der VM.OA.2014
> gemappt werden. Es ist die Brücke zwischen Schritt 1 (Digitalisierung) und
> Schritt 2 (Komplexitätsanalyse).

---

## 1. Übersicht: Formularfelder → Datenbank → Komplexitätskriterium

| Formular-Feld | DB-Spalte (`projects`) | Relevanz für | Automatisierbarkeit |
|--------------|----------------------|-------------|---------------------|
| Projektart | `project_type` | BMGL-Typ, Umbauzuschlag, (A) | Hoch |
| Gebäudeart | `building_type` | (A) direkt | Hoch |
| Topografie | `topography` | (A) Einbindung, (C) Bodenrisiken | Mittel |
| Erschließung | `access_status` | KGR 1, (C) Verfahren | Mittel |
| Budget | `budget` | BMGL-Schätzung | Hoch (als Proxy) |
| Heizungsart | `heating_type` | KGR 3 / TGA-Komplexität → (A) | Mittel |
| Bauweise | `construction_method` | (A) konstruktive Anforderungen | Mittel |
| Barrierefreiheit | `accessibility` | (A) Funktionsanforderungen | Mittel |
| Eigenleistung | `own_contribution` | BMGL (Abzug?), (B) Schnittstellen | Niedrig |
| Bebauungsplan | `development_plan` | (C) Verfahrensrisiken | Mittel |
| Außenbereich | `outdoor_area` | KGR 6, (A) Einbindung | Niedrig |
| Materialität | `materiality` | (A) Gestaltung, Ausbau | Niedrig |
| Raumprogramm | `project_rooms` | (A) Funktionsbereiche | Hoch |
| Notizen | `notes` | Alle Merkmale (Freitext-Analyse) | Mittel (LLM) |
| Geplanter Baubeginn | `planned_start` | (D) Terminanforderungen | Niedrig |

---

## 2. Detailliertes Mapping pro Bewertungsmerkmal

### 2.1 Merkmal (A) – Vielfalt der Besonderheiten (6–42 Punkte)

Dies ist das am stärksten automatisierbare Merkmal.

#### 2.1.1 Gebäudeart → Objektgruppe → (A)-Richtwert

| `building_type` | Objektgruppe (OA.6) | (A)-Richtwert |
|----------------|---------------------|---------------|
| `EFH` | Gruppe 5 (einfaches EFH) | 25–30 |
| `Doppelhaus` | Gruppe 5 | 25–28 |
| `Reihenhaus` | Gruppe 5 | 24–28 |
| `Mehrfamilienhaus` | Gruppe 5–6 | 25–32 |
| `Sonstige` | Kein direktes Mapping | Rückfrage erforderlich |

#### 2.1.2 Projektart → Modifikation von (A)

| `project_type` | Einfluss auf (A) |
|---------------|-----------------|
| `Neubau` | Basis-Richtwert aus Gebäudeart |
| `Bauen im Bestand` | +2 bis +4 Punkte (erhöhte Einbindungsanforderungen) |
| `Umbau im Inneren` | +1 bis +3 Punkte (Anpassung an Bestand) |
| `Sanierung/Modernis.` | +2 bis +5 Punkte (je nach Substanzeingriff) |
| `Zubau/Anbau` | +2 bis +4 Punkte (Einbindung in Bestand) |
| `Aufstockung` | +2 bis +4 Punkte (konstruktive Anforderungen erhöht) |
| `noch unklar` | Kein Richtwert möglich → Rückfrage |

#### 2.1.3 Heizungsart → TGA-Komplexität → (A) Sub-Kriterium 5

| `heating_type` | TGA-Komplexität | Einfluss auf (A) |
|---------------|----------------|-----------------|
| `Wärmepumpe` | Mittel-Hoch | +1 bis +2 Punkte auf TGA-Sub-Kriterium |
| `Fernwärme` | Gering | Kein Zusatz |
| `Gasheizung` | Gering-Mittel | Kein Zusatz |
| `Holz/Pellets` | Mittel | +1 Punkt auf TGA-Sub-Kriterium |
| `Sonstige` | Unbekannt | Rückfrage |

#### 2.1.4 Raumprogramm → Funktionsbereiche → (A) Sub-Kriterium 2

Die Anzahl unterschiedlicher Raumtypen und ihre Besonderheiten aus `project_rooms`:

| Anzahl unterschiedlicher Raumtypen | Einfluss auf (A) |
|-----------------------------------|-----------------|
| 1–3 | Sehr geringe Funktionskomplexität |
| 4–6 | Geringe bis durchschnittliche Komplexität |
| 7–9 | Durchschnittliche Komplexität |
| 10+ | Hohe Komplexität |

Zusätzlich: `special_requirements` in `project_rooms` → LLM-Analyse für Sonderfunktionen.

#### 2.1.5 Barrierefreiheit → (A) Funktionsanforderungen

| `accessibility` | Einfluss auf (A) |
|----------------|-----------------|
| `wichtig` | +1 bis +2 Punkte (erhöhte funktionale Anforderungen) |
| `optional` | +0 bis +1 Punkt |
| `nicht relevant` | Kein Einfluss |

#### 2.1.6 Topografie → (A) Sub-Kriterium 1 (Einbindung in Umgebung)

| `topography` | Einfluss auf (A) |
|-------------|-----------------|
| `eben` | Kein Zusatz |
| `leichte Hanglage` | +1 Punkt auf Einbindungs-Sub-Kriterium |
| `starke Hanglage` | +2 bis +3 Punkte (konstruktive + Einbindungsanforderungen) |
| `Sonstiges` | LLM-Analyse von `topography_other` |

---

### 2.2 Merkmal (B) – Komplexität der Projektorganisation (1–5 Punkte)

Dieses Merkmal ist aus dem Grundlagenformular **kaum direkt ableitbar**.
Das Formular erfasst nur den Bauherrn (eine Person/Adresse) → impliziert
in den meisten Fällen einen privaten Einzelbauherrn.

| Formular-Information | Ableitung für (B) |
|--------------------|-------------------|
| `client_name` (Privatperson erkennbar) | Starker Hinweis auf B=1–2 |
| `client_name` (Firmenname erkennbar) | Hinweis auf B=2–3, Rückfrage |
| `own_contribution` = `ja`/`teilweise` | Zusätzliche Schnittstelle → leicht erhöhend |
| Keine weiteren Informationen | Standard: B=2 als Vorschlag mit Rückfrage |

**→ Empfehlung:** Für (B) immer eine gezielte Rückfrage generieren:
- „Handelt es sich um einen privaten oder institutionellen Auftraggeber?"
- „Gibt es mehrere Entscheidungsträger oder Nutzergruppen?"

---

### 2.3 Merkmal (C) – Risiko bei der Projektrealisierung (1–5 Punkte)

Teilweise aus Formulardaten ableitbar:

| Formular-Information | Ableitung für (C) |
|--------------------|-------------------|
| `development_plan` = `false` | Erhöhtes Verfahrensrisiko → C um +1 |
| `access_status` = `nicht erschlossen` | Erhöhtes technisches Risiko → C um +1 |
| `access_status` = `teilerschlossen` | Leicht erhöhtes Risiko → C um +0,5 |
| `topography` = `starke Hanglage` | Erhöhte Bodenrisiken → C um +1 |
| `project_type` = `Bauen im Bestand` / `Umbau` | Bestandsrisiken erhöht → C um +1 |
| `budget` sehr niedrig bei hohem Raumprogramm | Finanzierungsrisiko → C erhöhen |
| `notes` / `materiality` → LLM-Analyse | Freitext auf Risikohinweise prüfen |

**→ Empfehlung:** Für (C) gezielte Rückfragen:
- „Liegen Altlasten oder besondere Bodenverhältnisse vor?"
- „Ist die Finanzierung bereits gesichert?"
- „Sind besondere Genehmigungsverfahren zu erwarten?"

---

### 2.4 Merkmal (D) – Termin- und Kostenanforderungen (1–5 Punkte)

| Formular-Information | Ableitung für (D) |
|--------------------|-------------------|
| `planned_start` sehr bald (< 6 Monate) | Erhöhter Termindruck → D um +1 bis +2 |
| `planned_start` offen / nicht gesetzt | Kein Termindruck erkennbar → D=1–2 |
| `budget` sehr knapp für Raumprogramm | Hoher Kostenoptimierungsdruck → D um +1 |
| `own_contribution` = `ja` | Koordinationsaufwand → leicht erhöhend für D |

**→ Empfehlung:** Für (D) gezielte Rückfragen:
- „Gibt es einen fixen Fertigstellungstermin (z.B. durch Einzugstermin)?"
- „Ist das Budget als harte Obergrenze (Kostendeckel) zu verstehen?"

---

## 3. BMGL-Schätzung aus Formulardaten

Da die echte BMGL erst nach detaillierter Kostenplanung feststeht, kann das Budget
als grober Proxy verwendet werden:

```
BMGL_geschätzt = budget × BMGL_Faktor
```

| Projektart | Typischer BMGL-Faktor | Begründung |
|-----------|----------------------|------------|
| `Neubau` | 0,75–0,85 | KGR 7, 8, 9 nicht oder nur teilweise anrechenbar |
| `Umbau im Inneren` | 0,65–0,80 | KGR 3 oft abgemindert |
| `Sanierung/Modernis.` | 0,60–0,75 | Hoher KGR 7/8-Anteil |
| `Zubau/Anbau` | 0,70–0,85 | Je nach Erschließungsaufwand |

> **Wichtig:** Diese Schätzung ist nur für eine erste Honorarindikation geeignet.
> Sie muss vom Architekten nach der Kostenschätzung (LPH 2) ersetzt werden.

---

## 4. Umbauzuschlag aus Formulardaten

| `project_type` | Umbauzuschlag-Empfehlung |
|---------------|--------------------------|
| `Neubau` | 0% (kein Zuschlag) |
| `Bauen im Bestand` | 15–25% (je nach Substanzeingriff) |
| `Umbau im Inneren` | 15–25% |
| `Sanierung/Modernis.` | 20–30% (Standard: 20% ohne Vereinbarung) |
| `Zubau/Anbau` | 10–20% (nur für Bestandsanteile) |
| `Aufstockung` | 15–25% |
| `noch unklar` | Rückfrage erforderlich |

---

## 5. Fehlende Informationen – Rückfragen nach Priorität

Das System sollte folgende Rückfragen generieren, wenn die entsprechenden
Daten fehlen oder unklar sind. Sortiert nach Priorität für die Honorarermittlung:

### Priorität 1 – Zwingend für Honorarberechnung

| Frage | Ziel-Merkmal | DB-Feld (neu) |
|-------|-------------|---------------|
| „Handelt es sich um einen Neubau oder Umbau?" | Umbauzuschlag | bereits: `project_type` |
| „Was ist die geplante Nutzfläche (m²) oder Kubatur?" | BMGL-Kalibrierung | fehlt in DB |
| „Welche Leistungsphasen sollen beauftragt werden?" | fLPH | fehlt in DB |

### Priorität 2 – Wichtig für Bewertungspunkte

| Frage | Ziel-Merkmal |
|-------|-------------|
| „Privater oder institutioneller/öffentlicher Auftraggeber?" | (B) |
| „Gibt es einen fixen Fertigstellungstermin?" | (D) |
| „Ist das Budget als harte Obergrenze zu verstehen?" | (D) |
| „Wie tief sind die geplanten Eingriffe in die Bausubstanz?" | (A), Umbauzuschlag |

### Priorität 3 – Für Lernqualität und Präzision

| Frage | Ziel-Merkmal |
|-------|-------------|
| „Gibt es besondere Genehmigungsverfahren?" | (C) |
| „Sind Altlasten oder schwierige Bodenverhältnisse bekannt?" | (C) |
| „Wie viele Planungsbeteiligte sind vorgesehen?" | (B) |

---

## 6. Konfidenzmodell für KI-Vorschläge

Für jeden Bewertungspunkt sollte das System einen Konfidenzwert ausgeben:

| Konfidenz | Bedeutung | Anzeige im Frontend |
|-----------|-----------|---------------------|
| Hoch (>80%) | Ausreichend Datenbasis | Vorschlag mit grüner Markierung |
| Mittel (50–80%) | Teilweise Datenbasis | Vorschlag mit gelber Markierung + Begründung |
| Niedrig (<50%) | Unzureichende Datenbasis | Rückfrage vor Vorschlag |

---

## 7. Erweiterungsempfehlung für das Grundlagenformular

Folgende Felder sollten in einer zukünftigen Version des Formulars ergänzt werden,
um die Automatisierbarkeit von Schritt 2 deutlich zu verbessern:

| Neues Feld | Typ | Ziel-Merkmal | Priorität |
|-----------|-----|-------------|-----------|
| Geplante Nutzfläche (m² NF) | Decimal | BMGL-Kalibrierung | Hoch |
| Öffentlicher / privater AG | Boolean | (B) | Hoch |
| Harte Kostenobergrenze? | Boolean | (D) | Hoch |
| Anzahl Nutzergruppen | Integer | (B) | Mittel |
| Bekannte Altlasten? | Boolean | (C) | Mittel |
| Denkmalschutz? | Boolean | (A), (C) | Mittel |
| Anzahl geplante Wohneinheiten | Integer | (A) Funktionsbereiche | Mittel |
