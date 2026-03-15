# Berechnungslogik: Objektplanung Architekt nach VM.OA.2014

Dieses Dokument beschreibt vollständig die Berechnungslogik eines Excel-Kalkulationsmodells zur Ermittlung des Architektenhonorars nach der österreichischen Vergabemethodik OA.2014. Eine KI soll damit in der Lage sein, das Modell in Python zu replizieren.

---

## 1. Eingangsdaten: Errichtungskosten (Kostengruppen)

Die Errichtungskosten bestehen aus folgenden Kostengruppen (KGR), die als Eingabewerte vorgegeben werden:

| KGR | Bezeichnung | Beispielwert (€) |
|-----|-------------|-----------------|
| 1 | Aufschließung | 0 |
| 2 | Bauwerk – Rohbau | 9.000.000 |
| 3.01 | Abwasser-, Wasser-, Gasanlagen | 900.000 |
| 3.02 | Wärme- und Kälteversorgungsanlagen | 1.000.000 |
| 3.03 | Lufttechnische Anlagen | 1.000.000 |
| 3.04 | Starkstrom – Elektroanlagen | 1.500.000 |
| 3.05 | Fernmelde-, IT- und Sicherheitsanlagen | 600.000 |
| 3.06 | Fördertechnische Anlagen | 150.000 |
| 3.07 | Nutzungsspezifische Anlagen | 0 |
| 3.08 | Gebäudeautomation | 300.000 |
| 4 | Bauwerk – Ausbau | 6.500.000 |
| 5.01 | Einbaumöbel | 1.500.000 |
| 5.02 | Serienmöbel | 500.000 |
| 5.03 | Nutzungsspezifische Ausstattung | 0 |
| 6 | Außenanlagen | 500.000 |
| 7 | Planungsleistungen (GP) | 5.342.460 |
| 8 | Nebenkosten | 36.000 |
| 9 | Reserven | 1.600.000 |

Zusätzlich kann es pro Kostengruppe einen Wert `mvB` (Mehrkosten vor Beauftragung, Spalte I) geben. Im Standardfall sind diese 0.

---

## 2. Gesamte Errichtungskosten (G37)

```
ERK_gesamt = KGR1 + KGR2 + KGR3_gesamt + KGR4 + KGR5_gesamt + KGR6 + KGR7 + KGR8 + KGR9
```

Wobei:
- `KGR3_gesamt = Summe aller KGR 3.01 bis 3.08`
- `KGR5_gesamt = Summe KGR 5.01 + 5.02 + 5.03`

---

## 3. Bemessungsgrundlage (BMGL) – Kernlogik

Die BMGL (Spalte O) wird pro Kostengruppe unterschiedlich berechnet.

### KGR 1 – Aufschließung
```
BMGL_KGR1 = KGR1 * BMGL_Prozent_KGR1
# BMGL_Prozent_KGR1 = 0 (fließt nicht in die BMGL ein)
```

### KGR 2 – Rohbau
```
BMGL_KGR2 = KGR2 * 1.0 + mvB_KGR2
# Fließt zu 100% in die BMGL ein
```

### KGR 3 – Technik (Sonderregel: Abminderung)

Hilfsberechnung:
```
Schwellenwert = (KGR2 + KGR4) * 0.5
```

Bedingung:
```
if (KGR3_gesamt + mvB_KGR3) > Schwellenwert:
    # Abminderung → KGR 3 wird auf den Schwellenwert gedeckelt
    BMGL_KGR3 = Schwellenwert
    Abminderungsbetrag = (KGR3_gesamt + mvB_KGR3) - Schwellenwert
    Abminderungs_BMGL_Prozent = 0.50   # 50% des überschießenden Betrags fließen trotzdem ein
    BMGL_Abminderung = Abminderungsbetrag * Abminderungs_BMGL_Prozent
    # Der Abminderungsbetrag wird separat in Zeile 20 ausgewiesen
else:
    # Keine Abminderung → KGR 3 fließt zu 100% in die BMGL ein
    BMGL_KGR3 = (KGR3_gesamt + mvB_KGR3) * 1.0
    BMGL_Abminderung = 0
```

### KGR 4 – Ausbau
```
BMGL_KGR4 = KGR4 * 1.0 + mvB_KGR4
# Fließt zu 100% in die BMGL ein
```

### KGR 5 – Einrichtung
```
# Alle Unterpositionen fließen zu 0% in die BMGL ein (im Beispiel)
BMGL_KGR5 = KGR5.01 * 0 + KGR5.02 * 0 + KGR5.03 * 0 + mvB_KGR5
```
*Hinweis: Der BMGL-Prozentsatz für KGR 5 ist ein Eingabewert und kann variieren.*

### KGR 6 – Außenanlagen
```
BMGL_KGR6 = KGR6 * BMGL_Prozent_KGR6 + mvB_KGR6
# Im Beispiel: 0%
```

### KGR 7 – Planungsleistungen
```
BMGL_KGR7 = KGR7 * BMGL_Prozent_KGR7
# Im Beispiel: 0%
```

### KGR 8 – Nebenkosten
```
BMGL_KGR8 = KGR8 * BMGL_Prozent_KGR8
# Im Beispiel: 0%
```

### KGR 9 – Reserven
```
BMGL_KGR9 = KGR9 * BMGL_Prozent_KGR9
# Im Beispiel: 10% → BMGL_KGR9 = 1.600.000 * 0.10 = 160.000
```

### Gesamt-BMGL
```
BMGL_gesamt = BMGL_KGR1 + BMGL_KGR2 + BMGL_KGR3 + BMGL_Abminderung + BMGL_KGR4
            + BMGL_KGR5 + BMGL_KGR6 + BMGL_KGR7 + BMGL_KGR8 + BMGL_KGR9
```

---

## 4. Bewertungspunkte (bw)

Folgende Punkte werden als Eingabewerte gesetzt:

| Merkmal | Kürzel | Wertebereich | Beispielwert |
|---------|--------|-------------|-------------|
| (A) Vielfalt der Besonderheiten | A | 6–42 | 22 |
| (B) Komplexität der Projektorganisation | B | 1–5 | 2 |
| (C) Risiko bei der Projektrealisierung | C | 1–5 | 1 |
| (D) Termin- und Kostenanforderungen | D | 1–5 | 2 |
| Zusatzpunkte | Z | optional | 3 |

```
bw = A + B + C + D + Z
```

---

## 5. Faktor aus Bewertungspunkten (fbw)

```
fbw = 0.0198 * bw + 0.9406
```

---

## 6. Honorarsatz hOA (%-Satz für Objektplanung Architekt)

Je nach Höhe der BMGL gilt eine andere Formel:

```
if BMGL_gesamt < 2.000.000:
    hOA = 40.0 * BMGL_gesamt**(-0.1208) * fbw / 100
else:
    hOA = 12.2611 * BMGL_gesamt**(-0.0394) * fbw / 100

# Gerundet auf 6 Dezimalstellen:
hOA = round(hOA, 6)
```

---

## 7. Umbauzuschlag

```
Umbauzuschlag = 0.05   # 5% nach AR.18(2) und OA.11, Eingabewert
```

---

## 8. Leistungsphasen (LPH) und fLPH

Die Leistungsphasen werden als Prozentwerte eingegeben (Summe ergibt fLPH):

| LPH | Bezeichnung | Standardwert | Gewählter Wert |
|-----|-------------|-------------|----------------|
| 1 | Grundlagenanalyse | 2% | 2% |
| 2 | Vorentwurfsplanung | 8% | 8% |
| 3 | Entwurfsplanung | 12% | 12% |
| 4 | Einreichplanung | 5% | 5% |
| 5 | Ausführungsplanung | 22% | 22% |
| 6 | Ausschreibung | 6% | 6% |
| 6b | Mitwirkung an der Vergabe | 2% | 2% |
| 7 | Begleitung der Bauausführung | 4% | 4% |
| 8 | Örtliche Bauaufsicht, Dokumentation | 37% | 37% |
| 9 | Objektbetreuung | 2% | 2% |

```
fLPH = Summe aller gewählten LPH-Prozentwerte
# Beispiel: 0.02+0.08+0.12+0.05+0.22+0.06+0.02+0.04+0.37+0.02 = 1.00
```

---

## 9. Gesamtvergütung VOA

```
VOA_gesamt = round(BMGL_gesamt * hOA * fLPH * (1 + Umbauzuschlag), 2)
```

Die Vergütung je LPH:
```
Vergütung_LPH_x = VOA_gesamt * LPH_x_Prozent
```

---

## 10. Stundenpool (optionale Leistungen)

```
Stundenpool_Vergütung = Stunden * Stundensatz
# Im Beispiel: 0 Stunden * 0 €/h = 0
```

---

## 11. Nebenkosten und MwSt.

```
Summe_ohne_NK = VOA_gesamt + Stundenpool_Vergütung

Nebenkosten_Prozent = 0.04   # Eingabewert (4%)
Nebenkosten = round(Summe_ohne_NK * Nebenkosten_Prozent, 2)

Summe_netto = Summe_ohne_NK + Nebenkosten

MwSt_Prozent = 0.20   # Eingabewert (20%)
MwSt = round(Summe_netto * MwSt_Prozent, 2)

Summe_brutto = Summe_netto + MwSt
```

---

## 12. Kontrollkennzahl

```
Prozentanteil_an_ERK = Summe_netto / ERK_gesamt
```

---

## Zusammenfassung: Python-Implementierungshinweise

- Alle `€`-Werte als `float` behandeln
- `round(x, 2)` für Geldbeträge, `round(x, 6)` für Honorarsatz hOA
- Die Abminderungslogik für KGR 3 ist der komplexeste Teil – siehe Abschnitt 3
- BMGL-Prozentsätze für KGR 5, 6, 7, 8 sind Eingabewerte (können 0–100% sein)
- Die Formel `BMGL_gesamt**(-0.0394)` erfordert `float`-Arithmetik (kein Integer-Exponent)
- Alle Eingabewerte sollten als Dictionary übergeben werden für maximale Flexibilität
