# ArchiScribe – Brückendokument: Berechnungslogik VM.OA.2014 → Implementierung

> Dieses Dokument verbindet die Berechnungslogik aus `Formel_OA2014_Beschreibung.md`
> mit der Datenbankstruktur aus `DATABASE.md` und dem Gesamtkonzept aus
> `03_Gesamtkonzept_ArchiScribe_Schritt2_3.md`.
> Es ist der direkte Übergabepunkt für die Implementierung von Schritt 3.

---

## 1. Variablen-Mapping: Formel → Datenbankfeld

### 1.1 Eingangsdaten (KGR-Werte)

| Variable (Formel) | DB-Tabelle | DB-Feld | Quelle |
|------------------|------------|---------|--------|
| KGR1 | `fee_calculations` | `kgr_1` | Architekt-Eingabe (Schritt 3) |
| KGR2 | `fee_calculations` | `kgr_2` | Architekt-Eingabe |
| KGR3.01–3.08 | `fee_calculations` | `kgr_3_01` … `kgr_3_08` | Architekt-Eingabe |
| KGR4 | `fee_calculations` | `kgr_4` | Architekt-Eingabe |
| KGR5.01–5.03 | `fee_calculations` | `kgr_5_01` … `kgr_5_03` | Architekt-Eingabe |
| KGR6 | `fee_calculations` | `kgr_6` | Architekt-Eingabe |
| KGR7 | `fee_calculations` | `kgr_7` | Architekt-Eingabe (info only, nicht anrechenbar) |
| KGR8 | `fee_calculations` | `kgr_8` | Architekt-Eingabe (info only, nicht anrechenbar) |
| KGR9 | `fee_calculations` | `kgr_9` | Architekt-Eingabe |
| mvB | `fee_calculations` | `mvb` | Architekt-Eingabe (nur bei Umbau) |

**Wenn noch keine KGR-Werte vorliegen (Frühphase):**
```
kgr_2 = budget * 0.50   # Rohbau-Schätzung
kgr_4 = budget * 0.30   # Ausbau-Schätzung
kgr_3_gesamt = budget * 0.15  # Technik-Schätzung (gleichmäßig auf 3.01–3.08 verteilen)
kgr_9 = budget * 0.05   # Reserven-Schätzung
bmgl_source = 'budget_estimate'  # Immer kennzeichnen!
```

### 1.2 BMGL-Anrechnungsprozentsätze

| Variable (Formel) | DB-Feld | Standardwert | Anmerkung |
|------------------|---------|-------------|-----------|
| BMGL_Prozent_KGR1 | `bmgl_pct_kgr1` | 0.0 | Je nach Planerleistung 0–100% |
| BMGL_Prozent_KGR3 | `bmgl_pct_kgr3` | 1.0 | Vor Abminderungsprüfung, immer 1.0 |
| BMGL_Prozent_KGR5 | `bmgl_pct_kgr5` | 0.0 | 0% für Standard-OA |
| BMGL_Prozent_KGR6 | `bmgl_pct_kgr6` | 0.0 | Eigenes VM für Freianlagen |
| BMGL_Prozent_KGR9 | `bmgl_pct_kgr9` | 0.1 | 10% Reserven-Anteil (verhandelbar) |

### 1.3 Abminderungsberechnung KGR3

| Variable (Formel) | DB-Feld | Berechnung |
|------------------|---------|-----------|
| Schwellenwert | `kgr3_threshold` | `(kgr_2 + kgr_4) * 0.5` |
| Abminderung aktiv? | `kgr3_abminderung` | `kgr3_total > kgr3_threshold` |
| Abminderungsbetrag | `kgr3_abminderung_betrag` | `(kgr3_total - kgr3_threshold) * 0.5` |

### 1.4 Bewertungspunkte

| Variable (Formel) | DB-Tabelle | DB-Feld | Quelle |
|------------------|------------|---------|--------|
| A | `complexity_analyses` | `final_score_a` (fallback: `ai_score_a`) | Schritt 2 |
| B | `complexity_analyses` | `final_score_b` (fallback: `ai_score_b`) | Schritt 2 |
| C | `complexity_analyses` | `final_score_c` (fallback: `ai_score_c`) | Schritt 2 |
| D | `complexity_analyses` | `final_score_d` (fallback: `ai_score_d`) | Schritt 2 |
| Zusatzpunkte | `complexity_analyses` | `final_score_extra` | Schritt 2 |
| bw (Summe) | `complexity_analyses` | `total_score_bw` | Generated Column |
| fbw | `fee_calculations` | `fbw` | Berechnet: `0.0198 * bw + 0.9406` |

### 1.5 Honorarformel

| Variable (Formel) | DB-Feld | Berechnung |
|------------------|---------|-----------|
| hOA | `hoa` | Formel je nach BMGL (siehe Abschnitt 2) |
| fLPH | `flph` | Summe aus `lph_selection` JSONB |
| Umbauzuschlag | `umbau_zuschlag` | Architekt-Eingabe, default aus `project_type` |
| Bandbreitenfaktor | `bandbreite_faktor` | 0.95–1.05, default 1.0 |
| VOA | `voa_gesamt` | `bmgl_total * hoa * flph * (1 + umbau_zuschlag)` |

### 1.6 Nebenkosten & MwSt.

| Variable (Formel) | DB-Feld | Standard |
|------------------|---------|---------|
| Nebenkostensatz | `nk_prozent` | 0.04 (4%) |
| Nebenkostenbetrag | `nk_betrag` | `(voa_gesamt + stundenpool_gesamt) * nk_prozent` |
| MwSt.-Satz | `mwst_prozent` | 0.20 (20%, Österreich) |
| MwSt.-Betrag | `mwst_betrag` | `gesamt_netto * mwst_prozent` |
| Nettosumme | `gesamt_netto` | `voa_gesamt + stundenpool_gesamt + nk_betrag` |
| Bruttosumme | `gesamt_brutto` | `gesamt_netto + mwst_betrag` |

### 1.7 Leistungsphasen

Das `lph_selection` JSONB-Feld in `fee_calculations` speichert nur die
**beauftragten** Leistungsphasen mit ihrem jeweiligen Prozentwert:

```json
{
  "1": 0.02,
  "2": 0.08,
  "3": 0.12,
  "4": 0.05,
  "5": 0.22,
  "6": 0.06,
  "6b": 0.02,
  "7": 0.04,
  "8": 0.37,
  "9": 0.02
}
```

```python
flph = sum(lph_selection.values())  # z.B. 1.0 wenn alle LPH beauftragt
```

---

## 2. Berechnungsreihenfolge (strikt einzuhalten)

```
1. KGR-Werte aus fee_calculations lesen (oder aus Budget schätzen)
2. KGR3_gesamt berechnen (Summe kgr_3_01 bis kgr_3_08 + mvb)
3. kgr3_threshold berechnen → kgr3_abminderung prüfen
4. bmgl_total berechnen (alle KGR mit Anrechnungsprozentsätzen)
5. bw lesen aus complexity_analyses.total_score_bw
6. fbw berechnen: 0.0198 * bw + 0.9406
7. hoa berechnen (Formel je nach bmgl_total)
8. flph berechnen (Summe lph_selection)
9. voa_gesamt berechnen
10. nk_betrag berechnen
11. gesamt_netto berechnen
12. mwst_betrag berechnen
13. gesamt_brutto berechnen
14. Alle Werte in fee_calculations speichern
15. project_history Eintrag schreiben
16. project.status_id → 'fee_draft' setzen
```

---

## 3. Status-Flow im Gesamtsystem

```
projects.status_id Übergänge für Schritt 3:

'complexity_done'
    │
    │  POST /fee/calculate (mit oder ohne KGR-Werte)
    ▼
'fee_draft'
    │
    │  PUT /fee/{id} (Architekt passt an: LPH, Zuschläge, KGR)
    ▼
'fee_draft' (bleibt bis Freigabe)
    │
    │  POST /fee/{id}/finalize (Architekt gibt frei)
    ▼
'fee_finalized'
    │
    │  GET /fee/{id}/export (PDF/DOCX, spätere Phase)
    ▼
  Export
```

---

## 4. KGR-Eingabe: Entscheidung für Frühphase

Da in Schritt 1 nur `budget` erfasst wird, muss für Schritt 3 eine bewusste
Entscheidung getroffen werden. Zwei Modi:

### Modus A – Schnellkalkulation (nur Budget)
```python
bmgl_source = 'budget_estimate'
# System schätzt KGR automatisch aus budget (siehe Abschnitt 1.1)
# Ergebnis ist eine Honorar-Indikation, kein verbindliches Angebot
# Frontend zeigt deutlichen Hinweis: "⚠ Schätzung – keine verbindliche Berechnung"
```

### Modus B – Detailkalkulation (KGR-Eingabe durch Architekten)
```python
bmgl_source = 'cost_estimate'  # oder 'cost_calculation'
# Architekt gibt KGR-Werte manuell ein (Formular in Schritt 3)
# Ergebnis ist verbindlich verwendbar
```

**Empfehlung für Implementierungsreihenfolge:**
1. Zuerst Modus A implementieren → sofort nutzbar
2. Modus B als zweite Ausbaustufe → wenn Kostenschätzung vorliegt

---

## 5. Abhängigkeiten zwischen den Dokumenten

```
Formel_OA2014_Beschreibung.md
    └── Vollständige Berechnungslogik (was berechnet wird)
    └── Wird durch dieses Dokument mit der DB verbunden

01_VMOA2014_Komplexitaet.md
    └── Normative Grundlage (warum so berechnet wird)
    └── Wird als LLM-Wissensbasis für Schritt 2 verwendet

02_Formular_Mapping_Komplexitaet.md
    └── Mapping Formularfelder → Bewertungsmerkmale
    └── Input für den LLM-Analyse-Prompt in Schritt 2

03_Gesamtkonzept_ArchiScribe_Schritt2_3.md
    └── SQL-Tabellen, API-Endpunkte, Frontend-Flow
    └── Implementierungsgrundlage für beide Schritte

DATABASE.md (besteht)
    └── Bestehende Tabellenstruktur (Schritt 1)
    └── Basis für alle neuen Tabellen

dieses Dokument (Brücke)
    └── Verbindet Formel ↔ DB ↔ Flow
    └── Übergabepunkt für Schritt-3-Implementierung
```

---

## 6. Vollständige Implementierungs-Checkliste für Schritt 3

### Backend
- [ ] `fee_calculations` Tabelle anlegen (SQL aus Gesamtkonzept)
- [ ] Pydantic Schema `FeeCalculationCreate` und `FeeCalculationResponse`
- [ ] `calculate_bmgl()` Funktion implementieren und unit-testen
- [ ] `calculate_hoa()` Funktion implementieren und unit-testen
- [ ] `calculate_voa()` Funktion implementieren und unit-testen
- [ ] `POST /fee/calculate` Endpunkt (Modus A: Budget-Schätzung)
- [ ] `PUT /fee/{id}` Endpunkt (Architekt-Anpassungen)
- [ ] `POST /fee/{id}/finalize` Endpunkt + Status-Update + project_history
- [ ] KGR-Eingabe Endpunkt für Modus B (zweite Ausbaustufe)

### Frontend
- [ ] Schritt-3-Ansicht: LPH-Auswahl (Checkboxen mit Prozentwerten)
- [ ] Umbauzuschlag-Auswahl (Dropdown mit Richtwerten aus project_type)
- [ ] Ergebnisanzeige: BMGL, hOA, fLPH, VOA, NK, MwSt., Brutto
- [ ] Hinweis-Banner wenn `bmgl_source = 'budget_estimate'`
- [ ] KGR-Eingabeformular (Modus B, zweite Ausbaustufe)

### Tests
- [ ] Unit-Test: BMGL-Berechnung mit Abminderung KGR3
- [ ] Unit-Test: hOA unter 2 Mio. €
- [ ] Unit-Test: hOA über 2 Mio. €
- [ ] Unit-Test: VOA mit Umbauzuschlag
- [ ] Integrationstest: Kompletter Flow Schritt 2 → Schritt 3
