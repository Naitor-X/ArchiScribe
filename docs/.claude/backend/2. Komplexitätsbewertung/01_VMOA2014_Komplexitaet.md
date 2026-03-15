# VM.OA.2014 – Vollständige Beschreibung der Komplexitäts- und Vergütungslogik

> Dieses Dokument beschreibt die vollständige normative Grundlage des Vergütungsmodells
> Objektplanung Architektur [VM.OA.2014] für die Verwendung in KI-gestützten Systemen.
> Alle Regeln, Formeln und Bewertungskriterien sind maschinenlesbar aufbereitet.

---

## 1. Grundstruktur des Vergütungsmodells

Die Honorarermittlung folgt einem fixen Berechnungsweg:

```
Projektdaten → BMGL → Bewertungspunkte (bw) → fbw → hOA → VOA
```

| Kürzel | Bedeutung |
|--------|-----------|
| BMGL | Bemessungsgrundlage in € (gewichtete anrechenbare Kosten) |
| bw | Summe der Bewertungspunkte (A+B+C+D+Zusatz) |
| fbw | Faktor aus Bewertungspunkten |
| hOA | Honorarprozentsatz für Objektplanung Architektur |
| fLPH | Prozentwert der beauftragten Leistungsphasen |
| VOA | Vergütung Objektplanung Architektur in € |

---

## 2. Leistungsphasen (LPH) nach OA.4

Die Gesamtleistung gliedert sich in 10 Leistungsphasen mit fixen Prozentwerten:

| PPH | LPH | Bezeichnung | Standardwert |
|-----|-----|-------------|-------------|
| PPH 2a | 1 | Grundlagenanalyse | 2 % |
| PPH 2b | 2 | Vorentwurfsplanung | 8 % |
| PPH 2c | 3 | Entwurfsplanung | 12 % |
| PPH 2d | 4 | Einreichplanung | 5 % |
| PPH 3a | 5 | Ausführungsplanung | 22 % |
| PPH 3b | 6 | Ausschreibung | 6 % |
| PPH 3c | – | Mitwirkung an der Vergabe | 2 % |
| PPH 4 | 7 | Begleitung der Bauausführung | 4 % |
| PPH 4 | 8 | Örtliche Bauaufsicht, Dokumentation | 37 % |
| PPH 5 | 9 | Objektbetreuung | 2 % |
| | | **Summe** | **100 %** |

Der Architekt kann Teilleistungen beauftragen. `fLPH` = Summe der gewählten Prozentwerte.

---

## 3. Bemessungsgrundlage (BMGL) nach OA.7

Die BMGL ist **nicht** die gesamte Bausumme, sondern eine gewichtete Teilmenge davon.
Sie richtet sich danach, welche Kostengruppen der Architekt fachlich plant oder koordiniert.

### 3.1 Kostengruppen und Anrechenbarkeit

| KGR | Bezeichnung | Anrechenbarkeit | Regel |
|-----|-------------|----------------|-------|
| 1 | Aufschließung | Variabel (0–100%) | Soweit der Objektplaner diese plant oder überwacht |
| 2 | Bauwerk – Rohbau | 100% | Fließt vollständig in die BMGL ein |
| 3 | Bauwerk – Technik | Sonderregel (siehe 3.2) | Abminderungslogik nach OA.7(1) Ziff. 3 |
| 4 | Bauwerk – Ausbau | 100% | Fließt vollständig in die BMGL ein |
| 5 | Einrichtung | Nach LM+VM Architekt Einrichtungsplanung | Üblicherweise 0% für OA |
| 6 | Außenanlagen | Nach LM+VM Architekt – Freianlagen | Eigenes Vergütungsmodell |
| 7 | Planungsleistungen (GP) | **Nicht anrechenbar** | KGR 7 ist nicht in BMGL einzurechnen |
| 8 | Nebenkosten | **Nicht anrechenbar** | KGR 8 ist nicht in BMGL einzurechnen |
| 9 | Reserven | Abgestuft anrechenbar | Vorl. anrechenbar; in Kostenfeststellung nicht enthalten |

### 3.2 Sonderregel KGR 3 – Technik (Abminderungslogik)

KGR 3 umfasst alle technischen Gebäudeanlagen (Haustechnik, TGA), die üblicherweise
von Fachplanern geplant werden. Der Architekt koordiniert und integriert nur.

**Schwellenwert:**
```
Schwellenwert = (KGR2 + KGR4) × 0,50
```

**Fallunterscheidung:**

```
WENN (KGR3_gesamt + mvB_KGR3) ≤ Schwellenwert:
    → KGR3 fließt zu 100% in die BMGL ein  [Ziffer 3.1]

WENN (KGR3_gesamt + mvB_KGR3) > Schwellenwert:
    → Abminderung greift  [Ziffer 3.2]
    → BMGL_KGR3 = Schwellenwert
    → Überschreitungsbetrag = (KGR3 + mvB) - Schwellenwert
    → BMGL_Abminderung = Überschreitungsbetrag × 0,50
    [Alternativ nach Ziffer 3.3: KGR3 kann zu 80% der BMGL eingerechnet werden]
```

**Hintergrund:** Wenn die Haustechnikkosten mehr als 50% von Rohbau+Ausbau betragen,
wird die Honorarbasis gedeckelt, da der Architekt nicht die volle Fachplanung erbringt.

### 3.3 mvB – Mitzuverarbeitende vorhandene Bausubstanz

Bei Umbauten und Modernisierungen kann vorhandene Bausubstanz (mvB) gemäß
AR.15(7) und AR.16(3) in die anrechenbaren Kosten einbezogen werden.
Basis: Kostenschätzung oder Kostenberechnung nach m² oder m³.

### 3.4 Zeitliche Gültigkeit der BMGL

| Leistungsphase | Grundlage der BMGL |
|---------------|-------------------|
| LPH 1–4 | Kostenberechnung (ggf. Kostenschätzung wenn keine KB vorliegt) |
| LPH 5–9 | Kostenfeststellung (ggf. Kostenanschlag wenn keine KF vorliegt) |

### 3.5 Nachlässe und Skonti

- Nachlässe **vor** Submission → werden von der BMGL abgezogen
- Nachlässe **die der Planer für den AG erwirkt** → werden der BMGL **doppelt** dazugezählt
- Skonti und Finanzierungsvorteile → werden für die BMGL **nicht** abgezogen

---

## 4. Bewertungspunkte (bw) nach OA.6

Die Bewertungspunkte erfassen die Planungskomplexität über vier Anforderungsmerkmale
plus optionale Zusatzpunkte. Sie sind das zentrale „subjektive" Element der Honorarermittlung
und sollen **einvernehmlich zwischen AG und AN** festgelegt werden.

```
bw = A + B + C + D + Zusatzpunkte
```

---

### 4.1 Merkmal (A) – Vielfalt der Besonderheiten in den Projektinhalten

**Wertebereich: 6 – 42 Punkte**

Dieses Merkmal erfasst die gestalterische, konstruktive und technische Komplexität
des Objekts selbst. Es ist das gewichtigste Merkmal.

#### Bewertungsmatrix (A):

| Punktebereich | Kategorie | Typische Merkmale |
|--------------|-----------|-------------------|
| **6–8** | Sehr gering | Sehr geringe Einbindungsanforderungen (0–2 Pkt.), ein Funktionsbereich (0–2), sehr geringe Gestaltung (0–2), einfachste Konstruktionen (0–2), keine/einfache TGA (1–3), kein/einfacher Ausbau (1–3) |
| **9–16** | Gering | Geringe Einbindung (1–3), wenige Funktionsbereiche (1–3), geringe Gestaltung (1–3), einfache Konstruktionen (1–3), geringe TGA (2–4), geringer Ausbau (2–4) |
| **17–25** | Durchschnittlich | Durchschnittliche Einbindung (2–4), mehrere einfache Funktionsbereiche (2–4), normale Gestaltung (2–4), normale Konstruktionen (2–4), durchschnittliche TGA (2–6), normaler Ausbau (2–6) |
| **26–32** | Hoch / überdurchschnittlich | Überdurchschnittliche Einbindung (3–6), mehrere Funktionsbereiche mit Beziehungen (3–6), überdurchschn. Gestaltung (3–6), überdurchschn. Konstruktion (3–6), überdurchschn. TGA (4–8), überdurchschn. Ausbau (4–8) |
| **33–42** | Sehr hoch | Sehr hohe Einbindung (4–7), Vielzahl von Funktionsbereichen (4–7), sehr hohe Gestaltung (4–7), sehr hohe Konstruktion (4–7), vielfältige TGA mit hohen Ansprüchen (5–9), umfangreicher Ausbau mehrerer Gewerke (5–9) |

#### Objektartenliste – Richtwerte für (A):

| Objektgruppe | Beispiele | Bewertungspunkte (A) |
|-------------|-----------|---------------------|
| 1 | Einfriedungen, Stützmauern, Schuppen, Baracken, Brücken | 6 |
| 2 | Einfache Hochbauten ohne TGA: Scheunen, Wirtschaftsgebäude, Magazine | 6–10 |
| 3 | Einfache Hochbauten mit TGA: Werkstätten, Lagerhäuser, Garagen, Umspannwerke | 11–17 |
| 4 | Normale Hochbauten: einfache Siedlungshäuser, einfache Gewerbebauten | 18–24 |
| 5 | Normale Hochbauten mit schwieriger Anordnung: Industriehochbauten, einfache Einfamilienhäuser, Miethäuser, sozialer Wohnungsbau, einfache Verwaltungsgebäude, Schulen, Kindergärten, Sportanlagen einfacher Art | 25–30 |
| 6 | Spezielle Hochbauten mit erhöhten Anforderungen: einfache Kirchen, Hotels, Altersheime, Bürogebäude, Rechenzentren, Fachhochschulen, Universitäten, Sporthallen, Hallenbäder, Tiefgaragen | 31–35 |
| 7 | Schwierige Hochbauten: Kirchen, Bahnhöfe, Bankgebäude, Justizgebäude mit besonderen Anforderungen, Universitäten Laborbetrieb, Theater, Krankenhäuser, Büchereien | 36–42 |
| 10 | Sonderbauten mit speziellen Erfahrungen / Technologien | 38–42 |

> **Hinweis für KI-Systeme:** Gruppen 8 und 9 (Wiederherstellungsarbeiten, Umbauten)
> wurden zugunsten der Umbauzuschlagsregelung nach OA.11 aufgelöst.

#### Sub-Kriterien für (A) – alternative Ermittlung:

| Sub-Kriterium | Beschreibung |
|--------------|-------------|
| 1. Einbindung in Umgebung | Städtebauliche, denkmalpflegerische, topografische Anforderungen |
| 2. Funktionsbereiche | Anzahl und Komplexität der Nutzungsbereiche und ihrer Beziehungen |
| 3. Gestalterische Anforderungen | Architektonische Qualitätsansprüche, Repräsentativität |
| 4. Konstruktive Anforderungen | Bautechnische Schwierigkeit, Sonderkonstruktionen |
| 5. Technische Gebäudeausrüstung (TGA) | Umfang und Komplexität der Haustechnik |
| 6. Ausbau | Umfang und Qualität des Innenausbaus, Anzahl der Gewerke |

---

### 4.2 Merkmal (B) – Komplexität der Projektorganisation

**Wertebereich: 1 – 5 Punkte**

Dieses Merkmal erfasst die organisatorische Komplexität auf Auftraggeber- und
Projektbeteiligten-Seite.

| Punkte | Kategorie | Kriterien |
|--------|-----------|-----------|
| **1** | Sehr gering | Einfache und eindeutige Entscheidungsstrukturen des AG; sehr geringe Anzahl Schnittstellen; ein AG zugleich Nutzer; sehr hohe Projektroutine aller Beteiligten |
| **2** | Gering | Eindeutige Entscheidungsstrukturen; geringe Anzahl Schnittstellen; ein AG, ein Nutzer; hohe Projektroutine |
| **3** | Durchschnittlich | Eindeutige Entscheidungsstrukturen; durchschnittliche Schnittstellen; ein AG, mehrere Nutzer; hohe Projektroutine |
| **4** | Hoch | Komplexe Entscheidungsstrukturen des AG; hohe Anzahl Schnittstellen; mehrere AG und Nutzer; geringe Projektroutine |
| **5** | Sehr hoch | Sehr komplexe Entscheidungsstrukturen; sehr hohe Anzahl Schnittstellen; große Anzahl AG und/oder mehrere Nutzer; sehr geringe Bauprojektroutine |

**Zusatzpunkte für (B):**
- Mehr als 20 Planungsbeteiligte → +1 bis +3 Zusatzpunkte
- Mehr als 50 beteiligte ausführende Unternehmen → +3 bis +5 Zusatzpunkte

---

### 4.3 Merkmal (C) – Risiko bei der Projektrealisierung

**Wertebereich: 1 – 5 Punkte**

Dieses Merkmal erfasst technische, wirtschaftliche, politische und verfahrensrechtliche Risiken.

| Punkte | Kategorie | Kriterien |
|--------|-----------|-----------|
| **1** | Sehr gering | Keine technischen Risiken; Finanzierung ausreichend und abgesichert; keine politischen/gesellschaftlichen Risiken; keine Umwelt-/Bodenrisiken; alle Genehmigungen unproblematisch |
| **2** | Gering | Geringe technische Risiken; Finanzierung fast abgesichert; geringe politische Risiken; geringe Umwelt-/Bodenrisiken; geringe Verfahrensrisiken |
| **3** | Durchschnittlich | Standardlösungen, bauübliche Strukturen; wenig wirtschaftliche Diskussionen; wenig politische Diskussionen; Umwelt-/Bodenrisiken einschätz- und beherrschbar; angemessene Verfahrenssicherheit |
| **4** | Hoch | Engagierte technische Lösungen, mittlerer Innovationsgrad; Kostenziele engagiert, Finanzierung noch nicht abgesichert; beherrschbare politische Diskussionen, Anrainer; Umwelt-/Bodenrisiken, Denkmalschutz nicht vollständig erkundet; beherrschbare, aber aufwändige Verfahren |
| **5** | Sehr hoch | Schwierige komplexe technische Lösungen, hoher Innovationsgrad; Kostenziele schwer erreichbar, Finanzierung schwierig; politische Diskussionen, Bürgerinitiativen; Umwelt-/Bodenrisiken, Denkmalschutz zu bearbeiten; Besondere Bau-/Genehmigungsverfahren |

**Zusatzpunkte für (C):**
- Starke terminliche Verdichtung (z.B. LPH 5+6+7 parallel) → +2 bis +4 Zusatzpunkte

---

### 4.4 Merkmal (D) – Termin- und Kostenanforderungen

**Wertebereich: 1 – 5 Punkte**

Dieses Merkmal erfasst den Druck durch Terminvorgaben und Kostenziele.

| Punkte | Kategorie | Kriterien |
|--------|-----------|-----------|
| **1** | Sehr gering | Ausreichend Zeit für Planung und Realisierung; konsekutive Abwicklung der LPH, Baustart nach vollständiger Planung; sehr geringer Kostenoptimierungsdruck; Anwendbarkeit von Standardkennwerten |
| **2** | Gering | Angemessene Dauern; Abwicklung größtenteils konsekutiv; geringer Einsparungsdruck; weitgehende Verwendung von Standardkennwerten |
| **3** | Durchschnittlich | Begrenzte Dauern; Planung/Ausführung zum Teil ineinander verschoben; normaler Kostenoptimierungsdruck; durchschnittlicher Aufwand Termin- und Kostenplanung |
| **4** | Hoch | Kurze Dauern; Planung/Ausführung zum Teil parallelisiert; hoher Einsparungsdruck; hohe Anforderung an Termin- und Kostenplanung |
| **5** | Sehr hoch | Außergewöhnlich kurze Dauern; Abwicklung zum größten Teil parallelisiert; sehr hoher Einsparungsdruck; hohe Anforderung an Termin- und Kostenkontrollsysteme |

**Zusatzpunkte für (D):**
- Kostendeckel / design to cost → +5 bis +7 Zusatzpunkte

---

### 4.5 Zusatzpunkte (allgemein) nach OA.6(4)

Für überdurchschnittliche Projekte/Anforderungen können Zusatzpunkte angerechnet werden:

| Situation | Zusatzpunkte |
|-----------|-------------|
| Projekt über 100 Mio. € Baukosten | +1 bis +5 (auf A) |
| Vertiefte Kostenschätzung (LPH 2) | +2 bis +4 |
| Vertiefte Kostenberechnung (LPH 3) | +4 bis +6 |
| Durchgehende vertiefte Kostensteuerung (LPH 3–9) | +12 bis +16 |
| Durchgehende vertiefte Terminplanung + Kontrolle | +10 bis +12 |
| Mitwirkung an vKM+vKPK einer Projektsteuerung | +4 bis +8 |

> **Nicht zutreffend:** Umbauten und Modernisierungen erhöhen die Bewertungspunkte
> **nicht**, wenn mvB nach AR.16(3) einbezogen **und** der Umbauzuschlag nach OA.11
> berechnet wurde.

---

### 4.6 Veränderungen der Bewertung (OA.6(3))

Gravierende Abweichungen von den vertraglich vereinbarten Bewertungspunkten in der
Projektabwicklung (15–20%) sollten mit einer Revision der vertraglichen Vergütung
ausgeglichen werden.

---

## 5. Honorarformel nach OA.9

### 5.1 Faktor aus Bewertungspunkten (fbw)

```
fbw = 0,0198 × bw + 0,9406
```

### 5.2 Honorarprozentsatz (hOA)

Je nach Höhe der BMGL gilt eine andere Potenzformel:

```
WENN BMGL < 2.000.000 €:
    hOA = 40,0000 × (BMGL)^(-0,1208) × fbw / 100

WENN BMGL ≥ 2.000.000 €:
    hOA = 12,2611 × (BMGL)^(-0,0394) × fbw / 100
```

Der Faktor kann mit ×1,05 bis ×0,95 eine Bandbreite von +/–5% verhandelt werden.

**Gerundet auf 6 Dezimalstellen.**

### 5.3 Gesamtvergütung (VOA)

```
VOA = BMGL × hOA × fLPH × (1 + Umbauzuschlag)
```

**Gerundet auf 2 Dezimalstellen.**

---

## 6. Umbauzuschlag nach OA.11

Für Umbauten und Modernisierungen kann ein Zuschlag vereinbart werden:

| Umbaugrad | Zuschlag |
|-----------|---------|
| Leichte Umbauten (geringe Eingriffe in Substanz) | 10–20 % |
| Mittlere Umbauten (Eingriffe in die Substanz) | 15–30 % |
| Schwere Umbauten (erhebliche Eingriffe in Substanz) | 25–40 % |
| **Ohne schriftliche Vereinbarung (Standard)** | **20 %** |
| Instandsetzungen / Instandhaltungen (auf ÖBA) | 25–50 % |
| Umbau unter Betrieb (zusätzlich) | +5–10 % auf BMGL oder Vergütungssatz |
| Rekonstruktion | bis 100 % oder nach Aufwand |

---

## 7. Generalunternehmer nach OA.10

Bei Einschaltung eines GU erfordert das Änderungsmanagement einen besonderen
Aufwand. Die Vergütung für LPH 8 kann durch schriftliche Vereinbarung um bis zu
10% vermindert werden.

---

## 8. Nebenkosten und MwSt.

Nebenkosten und MwSt. sind **nicht** in der VOA enthalten.
Sie werden gemäß den Allgemeinen Regelungen für Planerverträge [AR] gesondert
angesetzt und können pauschal oder nach Aufwand vereinbart werden.

```
Nebenkosten = VOA × Nebenkostensatz (typisch: 3–5%)
Nettovergütung = VOA + Nebenkosten
MwSt. = Nettovergütung × MwSt.-Satz (AT: 20%)
Bruttovergütung = Nettovergütung + MwSt.
```

---

## 9. Wichtige Hinweise für KI-Systeme

1. **BMGL ≠ Budget:** Das Budget aus dem Grundlagenformular ist ein grober Proxy.
   Die echte BMGL ergibt sich erst aus der detaillierten Kostenberechnung nach KGR.

2. **Bewertungspunkte (B), (C), (D)** erfordern Informationen, die im Grundlagenformular
   oft nicht vollständig vorhanden sind → Rückfragen an Architekten erforderlich.

3. **Merkmal (A)** kann aus Projektart + Gebäudeart + Raumprogramm + Heizung/TGA
   bereits gut geschätzt werden → höchste Automatisierbarkeit.

4. **Unter 300.000 € BMGL** sollte der Ermittlungsweg über Büro-/Personalaufwand
   gewählt werden (OA.9(3)) – die Formel liefert dort unzuverlässige Werte.

5. **Abweichung >10%** von den Proportionen der LPH-Werte signalisiert, dass
   Bearbeitungstiefe und Qualitätsziele gefährdet sein könnten (OA.9(6)).
