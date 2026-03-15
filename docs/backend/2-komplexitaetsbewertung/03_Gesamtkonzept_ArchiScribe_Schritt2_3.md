# ArchiScribe – Gesamtkonzept: Komplexitätsanalyse & Honorarangebot (Schritt 2 & 3)

> Dieses Dokument beschreibt die Systemarchitektur, Datenbankstruktur und
> API-Logik für die Erweiterung von ArchiScribe um Schritt 2 (Komplexitätsanalyse)
> und Schritt 3 (Honorarangebot). Es baut vollständig auf der bestehenden
> ArchiScribe-Datenbank (`DATABASE.md`, Stand 2026-03-15) auf.

---

## 1. Systemübersicht

```
┌─────────────────────────────────────────────────────────────────────┐
│                          ArchiScribe                                 │
│                                                                      │
│  SCHRITT 1 (besteht)          SCHRITT 2 (neu)       SCHRITT 3 (neu) │
│  ─────────────────            ──────────────         ────────────── │
│  Formular                     Komplexitäts-          Honorar-       │
│  → OCR/LLM                    analyse                angebot        │
│  → projects (DB)              → KI-Vorschlag         → Berechnung   │
│                               → Rückfragen           → PDF-Export   │
│                               → Architekt            → Lernschicht  │
│                                 korrigiert                          │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 2. Neue Datenbank-Tabellen

Alle neuen Tabellen referenzieren die bestehende `projects`-Tabelle.
Multi-Tenancy: Jede Query muss `tenant_id` über den JOIN auf `projects` sicherstellen.

---

### 2.1 `complexity_analyses` – Komplexitätsanalyse pro Projekt

Speichert den vollständigen Analysezustand: KI-Vorschlag, Architekten-Entscheidung,
Begründungen und Konfidenzwerte.

```sql
CREATE TABLE complexity_analyses (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id              UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,

    -- Status der Analyse
    status                  VARCHAR(50) NOT NULL DEFAULT 'ai_draft',
    -- Werte: 'ai_draft' | 'pending_questions' | 'architect_review' | 'finalized'

    -- KI-Vorschläge (Rohausgabe des LLM)
    ai_score_a              DECIMAL(5,2),   -- Vorschlag für Merkmal A (6–42)
    ai_score_b              DECIMAL(4,2),   -- Vorschlag für Merkmal B (1–5)
    ai_score_c              DECIMAL(4,2),   -- Vorschlag für Merkmal C (1–5)
    ai_score_d              DECIMAL(4,2),   -- Vorschlag für Merkmal D (1–5)
    ai_score_extra          DECIMAL(5,2)    DEFAULT 0, -- KI-Vorschlag Zusatzpunkte
    ai_reasoning            JSONB,          -- Begründungen pro Merkmal {A: "...", B: "..."}
    ai_confidence           JSONB,          -- Konfidenzwerte {A: 0.85, B: 0.40, ...}
    ai_missing_info         JSONB,          -- Fehlende Infos als Array ["Frage 1", ...]

    -- Architekt-Entscheidung (nach Korrektur)
    final_score_a           DECIMAL(5,2),
    final_score_b           DECIMAL(4,2),
    final_score_c           DECIMAL(4,2),
    final_score_d           DECIMAL(4,2),
    final_score_extra       DECIMAL(5,2)    DEFAULT 0,
    architect_notes         TEXT,           -- Globale Notiz des Architekten

    -- Änderungsprotokoll (welche Werte hat der Architekt geändert?)
    corrections             JSONB,
    -- Format: {A: {ai: 22, final: 25, reason: "Denkmalschutz nicht berücksichtigt"}}

    -- Berechnete Summe (wird automatisch befüllt)
    total_score_bw          DECIMAL(6,2) GENERATED ALWAYS AS (
        COALESCE(final_score_a, ai_score_a, 0) +
        COALESCE(final_score_b, ai_score_b, 0) +
        COALESCE(final_score_c, ai_score_c, 0) +
        COALESCE(final_score_d, ai_score_d, 0) +
        COALESCE(final_score_extra, ai_score_extra, 0)
    ) STORED,

    -- Metadaten
    analyzed_by_user_id     UUID,
    finalized_by_user_id    UUID,
    created_at              TIMESTAMPTZ DEFAULT NOW(),
    updated_at              TIMESTAMPTZ DEFAULT NOW()
);
```

---

### 2.2 `complexity_questions` – Rückfragen des Systems an den Architekten

Das System generiert kontextabhängige Rückfragen. Der Architekt beantwortet sie
direkt in der App. Antworten fließen in die finale Bewertung ein.

```sql
CREATE TABLE complexity_questions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    analysis_id     UUID NOT NULL REFERENCES complexity_analyses(id) ON DELETE CASCADE,
    project_id      UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,

    -- Die Frage
    question_key    VARCHAR(100) NOT NULL,  -- Eindeutiger Key, z.B. "ag_type", "hard_budget"
    question_text   TEXT NOT NULL,          -- Anzeigetext (DE)
    target_metric   VARCHAR(10),            -- Welches Merkmal betrifft die Frage: A/B/C/D/BMGL
    priority        INTEGER DEFAULT 2,      -- 1=zwingend, 2=wichtig, 3=optional
    answer_type     VARCHAR(50),            -- 'boolean' | 'select' | 'text' | 'number'
    answer_options  JSONB,                  -- Bei 'select': ["Privat", "Öffentlich", ...]

    -- Antwort des Architekten
    answer          JSONB,                  -- Flexible Speicherung je nach answer_type
    answered_at     TIMESTAMPTZ,
    answered_by     UUID,

    created_at      TIMESTAMPTZ DEFAULT NOW()
);
```

---

### 2.3 `fee_calculations` – Honorarangebot (Schritt 3)

Speichert die vollständige Honorarberechnung nach VM.OA.2014.

```sql
CREATE TABLE fee_calculations (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id              UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    analysis_id             UUID REFERENCES complexity_analyses(id),

    -- BMGL-Ermittlung
    bmgl_source             VARCHAR(50) DEFAULT 'budget_estimate',
    -- Werte: 'budget_estimate' | 'cost_estimate' | 'cost_calculation' | 'final_costs'
    bmgl_total              DECIMAL(15,2),  -- Gesamt-BMGL in €

    -- Kostengruppen (KGR) – alle optional, werden je nach Projekt befüllt
    kgr_1                   DECIMAL(15,2) DEFAULT 0,  -- Aufschließung
    kgr_2                   DECIMAL(15,2) DEFAULT 0,  -- Rohbau
    kgr_3_01                DECIMAL(15,2) DEFAULT 0,  -- Abwasser/Wasser/Gas
    kgr_3_02                DECIMAL(15,2) DEFAULT 0,  -- Wärme/Kälte
    kgr_3_03                DECIMAL(15,2) DEFAULT 0,  -- Lufttechnik
    kgr_3_04                DECIMAL(15,2) DEFAULT 0,  -- Starkstrom
    kgr_3_05                DECIMAL(15,2) DEFAULT 0,  -- Fernmelde/IT
    kgr_3_06                DECIMAL(15,2) DEFAULT 0,  -- Fördertechnik
    kgr_3_07                DECIMAL(15,2) DEFAULT 0,  -- Nutzungsspezifisch
    kgr_3_08                DECIMAL(15,2) DEFAULT 0,  -- Gebäudeautomation
    kgr_4                   DECIMAL(15,2) DEFAULT 0,  -- Ausbau
    kgr_5_01                DECIMAL(15,2) DEFAULT 0,  -- Einbaumöbel
    kgr_5_02                DECIMAL(15,2) DEFAULT 0,  -- Serienmöbel
    kgr_5_03                DECIMAL(15,2) DEFAULT 0,  -- Nutzungsspez. Ausstattung
    kgr_6                   DECIMAL(15,2) DEFAULT 0,  -- Außenanlagen
    kgr_7                   DECIMAL(15,2) DEFAULT 0,  -- Planungsleistungen (nicht anrechenbar)
    kgr_8                   DECIMAL(15,2) DEFAULT 0,  -- Nebenkosten (nicht anrechenbar)
    kgr_9                   DECIMAL(15,2) DEFAULT 0,  -- Reserven
    mvb                     DECIMAL(15,2) DEFAULT 0,  -- Mitzuverarbeitende Bausubstanz

    -- BMGL-Prozentsätze (Anrechenbarkeit je KGR)
    bmgl_pct_kgr1           DECIMAL(5,4) DEFAULT 0,
    bmgl_pct_kgr3           DECIMAL(5,4) DEFAULT 1,   -- vor Abminderungsprüfung
    bmgl_pct_kgr5           DECIMAL(5,4) DEFAULT 0,
    bmgl_pct_kgr6           DECIMAL(5,4) DEFAULT 0,
    bmgl_pct_kgr9           DECIMAL(5,4) DEFAULT 0.1,

    -- Abminderungsberechnung KGR 3
    kgr3_threshold          DECIMAL(15,2),  -- 50% von (KGR2 + KGR4)
    kgr3_abminderung        BOOLEAN DEFAULT false,
    kgr3_abminderung_betrag DECIMAL(15,2) DEFAULT 0,

    -- Bewertungspunkte (aus complexity_analyses übernommen)
    score_bw                DECIMAL(6,2),   -- Gesamtpunktzahl
    fbw                     DECIMAL(8,6),   -- 0.0198 * bw + 0.9406
    hoa                     DECIMAL(10,6),  -- Honorarprozentsatz

    -- Leistungsphasen
    lph_selection           JSONB NOT NULL,
    -- Format: {1: 0.02, 2: 0.08, 3: 0.12, ...} – nur beauftragte LPH
    flph                    DECIMAL(5,4),   -- Summe der gewählten LPH-Anteile

    -- Zuschläge
    umbau_zuschlag          DECIMAL(5,4) DEFAULT 0,   -- z.B. 0.20 für 20%
    bandbreite_faktor       DECIMAL(4,3) DEFAULT 1.0, -- 0.95 bis 1.05

    -- Vergütung
    voa_gesamt              DECIMAL(15,2),  -- BMGL × hOA × fLPH × (1 + Umbauzuschlag)
    stundenpool_stunden     DECIMAL(10,2) DEFAULT 0,
    stundenpool_satz        DECIMAL(10,2) DEFAULT 0,
    stundenpool_gesamt      DECIMAL(15,2) DEFAULT 0,

    -- Nebenkosten & MwSt
    nk_prozent              DECIMAL(5,4) DEFAULT 0.04,
    nk_betrag               DECIMAL(15,2),
    mwst_prozent            DECIMAL(5,4) DEFAULT 0.20,
    mwst_betrag             DECIMAL(15,2),
    gesamt_netto            DECIMAL(15,2),
    gesamt_brutto           DECIMAL(15,2),

    -- Metadaten
    version                 INTEGER DEFAULT 1,  -- Für mehrere Angebotsvarianten
    notes                   TEXT,
    created_by_user_id      UUID,
    created_at              TIMESTAMPTZ DEFAULT NOW(),
    updated_at              TIMESTAMPTZ DEFAULT NOW()
);
```

---

### 2.4 `learning_examples` – Lernbasis für das KI-System

Diese Tabelle ist das Herzstück des Human-in-the-Loop-Lernens. Jedes finalisierte
Projekt wird als Lernbeispiel gespeichert und bei zukünftigen Projekten als
semantischer Kontext herangezogen.

```sql
CREATE TABLE learning_examples (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id          UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    tenant_id           UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    analysis_id         UUID REFERENCES complexity_analyses(id),

    -- Projektkontext (denormalisiert für schnellen Zugriff ohne JOINs)
    project_type        VARCHAR(50),        -- Aus projects.project_type
    building_type       VARCHAR(50),        -- Aus projects.building_type
    construction_method VARCHAR(50),
    heating_type        VARCHAR(50),
    topography          VARCHAR(50),
    accessibility       VARCHAR(50),
    budget_range        VARCHAR(20),        -- 'unter_100k' | '100k_500k' | '500k_1m' | 'über_1m'
    room_count          INTEGER,            -- Anzahl Räume im Raumprogramm

    -- KI-Vorschlag
    ai_scores           JSONB NOT NULL,     -- {A: 22, B: 2, C: 1, D: 2, extra: 3}
    ai_reasoning        JSONB,

    -- Finale Werte (nach Architekten-Entscheidung)
    final_scores        JSONB NOT NULL,     -- {A: 25, B: 2, C: 1, D: 2, extra: 3}
    corrections_made    BOOLEAN,            -- Hat der Architekt etwas geändert?
    correction_delta    JSONB,              -- {A: +3, B: 0, C: 0, D: 0}
    architect_reasoning JSONB,             -- Begründungen des Architekten

    -- Honorardaten (nach Abschluss)
    bmgl_actual         DECIMAL(15,2),      -- Tatsächliche BMGL nach Kalkulation
    voa_actual          DECIMAL(15,2),      -- Tatsächliches Honorar

    -- Embedding für semantische Ähnlichkeitssuche
    -- (pgvector Extension erforderlich, oder Qdrant extern)
    context_embedding   vector(1536),       -- Optional: wenn pgvector verfügbar

    -- Qualitätsbewertung (für Lernqualität)
    quality_score       DECIMAL(3,2),       -- 0.0–1.0, wie gut war der KI-Vorschlag
    finalized_at        TIMESTAMPTZ,
    created_at          TIMESTAMPTZ DEFAULT NOW()
);
```

> **Hinweis zu pgvector:** Falls pgvector nicht installiert ist, kann das Embedding
> als `JSONB` gespeichert und die Ähnlichkeitssuche über Qdrant (extern) durchgeführt
> werden – du hast Qdrant bereits in deinem Stack (Obsidian-Setup).

---

### 2.5 Neue Status-Werte für `project_statuses`

```sql
INSERT INTO project_statuses (id, label) VALUES
('complexity_draft',    'Komplexitätsanalyse – KI-Entwurf'),
('complexity_questions','Komplexitätsanalyse – Rückfragen offen'),
('complexity_review',   'Komplexitätsanalyse – Architekten-Review'),
('complexity_done',     'Komplexitätsanalyse – Abgeschlossen'),
('fee_draft',           'Honorarangebot – Entwurf'),
('fee_review',          'Honorarangebot – Review'),
('fee_finalized',       'Honorarangebot – Finalisiert');
```

---

### 2.6 Neue Indizes

```sql
-- complexity_analyses
CREATE INDEX idx_complexity_project_id ON complexity_analyses(project_id);
CREATE INDEX idx_complexity_status ON complexity_analyses(status);

-- complexity_questions
CREATE INDEX idx_questions_analysis_id ON complexity_questions(analysis_id);
CREATE INDEX idx_questions_unanswered ON complexity_questions(analysis_id)
    WHERE answered_at IS NULL;

-- fee_calculations
CREATE INDEX idx_fee_project_id ON fee_calculations(project_id);

-- learning_examples
CREATE INDEX idx_learning_tenant_id ON learning_examples(tenant_id);
CREATE INDEX idx_learning_project_type ON learning_examples(project_type);
CREATE INDEX idx_learning_building_type ON learning_examples(building_type);
-- Für pgvector (optional):
-- CREATE INDEX idx_learning_embedding ON learning_examples USING ivfflat (context_embedding);
```

---

## 3. API-Endpunkte (FastAPI)

Alle Endpunkte folgen dem bestehenden Multi-Tenancy-Muster: `tenant_id` wird aus
dem API-Key extrahiert und bei jeder Query als Filter verwendet.

### 3.1 Schritt 2 – Komplexitätsanalyse

```
POST   /api/v1/projects/{project_id}/complexity/analyze
       → Startet KI-Analyse, legt complexity_analyses + complexity_questions an
       → Gibt: analysis_id, ai_scores, ai_reasoning, ai_confidence, questions

GET    /api/v1/projects/{project_id}/complexity
       → Gibt aktuellen Analyse-Stand zurück

POST   /api/v1/projects/{project_id}/complexity/questions/{question_id}/answer
       → Architekt beantwortet eine Rückfrage
       → Body: {answer: ...}

POST   /api/v1/projects/{project_id}/complexity/finalize
       → Architekt bestätigt / korrigiert finale Scores
       → Body: {final_score_a, final_score_b, final_score_c, final_score_d,
                final_score_extra, architect_notes, corrections_reasoning}
       → Trigger: Speichert in learning_examples, Status → 'complexity_done'
```

### 3.2 Schritt 3 – Honorarangebot

```
POST   /api/v1/projects/{project_id}/fee/calculate
       → Erstellt Honorarberechnung auf Basis der finalisierten Komplexitätsanalyse
       → Body: {lph_selection, umbau_zuschlag, kgr_values (optional),
                nk_prozent, bandbreite_faktor}
       → Gibt: vollständige fee_calculation zurück

GET    /api/v1/projects/{project_id}/fee
       → Gibt aktuelle Honorarberechnung zurück

PUT    /api/v1/projects/{project_id}/fee/{calculation_id}
       → Architekten-Anpassungen (z.B. LPH-Auswahl ändern)

POST   /api/v1/projects/{project_id}/fee/{calculation_id}/finalize
       → Finalisiert das Angebot, Status → 'fee_finalized'

GET    /api/v1/projects/{project_id}/fee/{calculation_id}/export
       → Gibt PDF oder DOCX zurück (spätere Ausbaustufe)
```

---

## 4. KI-Analyse-Logik (Backend-Service)

### 4.1 Analyse-Prompt-Struktur

Der LLM-Aufruf für Schritt 2 besteht aus drei Teilen:

```python
system_prompt = """
Du bist ein Experte für österreichisches Architektenhonorarrecht nach VM.OA.2014.
Deine Aufgabe ist die Bewertung von Bauprojekten anhand der vier Komplexitätsmerkmale
A (Vielfalt der Besonderheiten, 6-42 Punkte), B (Projektorganisation, 1-5),
C (Risiko, 1-5), D (Termin/Kosten, 1-5).

Antworte ausschließlich als JSON-Objekt mit folgender Struktur:
{
  "scores": {"A": float, "B": float, "C": float, "D": float, "extra": float},
  "reasoning": {"A": "...", "B": "...", "C": "...", "D": "..."},
  "confidence": {"A": float, "B": float, "C": float, "D": float},
  "missing_info": ["Frage 1", "Frage 2", ...]
}
"""

# Kontext aus bestehenden Lernbeispielen (ähnliche Projekte)
similar_projects_context = get_similar_projects(project_id, tenant_id, n=3)

user_prompt = f"""
Projektdaten:
- Projektart: {project.project_type}
- Gebäudeart: {project.building_type}
- Bauweise: {project.construction_method}
- Heizung: {project.heating_type}
- Topografie: {project.topography}
- Erschließung: {project.access_status}
- Budget: {project.budget} EUR
- Barrierefreiheit: {project.accessibility}
- Bebauungsplan: {project.development_plan}
- Geplanter Baubeginn: {project.planned_start}
- Raumprogramm: {rooms_summary}
- Notizen: {project.notes}

Ähnliche frühere Projekte (Lernbasis):
{similar_projects_context}

Bewerte die vier Merkmale nach VM.OA.2014.
"""
```

### 4.2 Lernschicht – Ähnlichkeitssuche

Für die Ähnlichkeitssuche in `learning_examples` gibt es zwei Optionen:

**Option A: Regelbasiert (sofort verfügbar, ohne Embeddings)**
```sql
SELECT * FROM learning_examples
WHERE tenant_id = :tenant_id
  AND project_type = :project_type
  AND building_type = :building_type
ORDER BY finalized_at DESC
LIMIT 3;
```

**Option B: Semantisch über pgvector (ab ~20 Projekten sinnvoll)**
```sql
SELECT *, (context_embedding <-> :query_embedding) AS distance
FROM learning_examples
WHERE tenant_id = :tenant_id
ORDER BY distance
LIMIT 3;
```

### 4.3 BMGL-Berechnungslogik (Python)

```python
def calculate_bmgl(calc: FeeCalculation) -> float:
    kgr3_total = sum([
        calc.kgr_3_01, calc.kgr_3_02, calc.kgr_3_03,
        calc.kgr_3_04, calc.kgr_3_05, calc.kgr_3_06,
        calc.kgr_3_07, calc.kgr_3_08
    ]) + calc.mvb

    # Schwellenwert für KGR 3 Abminderung
    threshold = (calc.kgr_2 + calc.kgr_4) * 0.5

    if kgr3_total <= threshold:
        bmgl_kgr3 = kgr3_total  # 100% anrechenbar
        abminderung = 0
    else:
        bmgl_kgr3 = threshold   # gedeckelt
        abminderung = (kgr3_total - threshold) * 0.5  # 50% des Überschusses

    bmgl = (
        calc.kgr_1 * calc.bmgl_pct_kgr1 +
        calc.kgr_2 * 1.0 +
        bmgl_kgr3 + abminderung +
        calc.kgr_4 * 1.0 +
        calc.kgr_5_01 * calc.bmgl_pct_kgr5 +
        calc.kgr_5_02 * calc.bmgl_pct_kgr5 +
        calc.kgr_5_03 * calc.bmgl_pct_kgr5 +
        calc.kgr_6 * calc.bmgl_pct_kgr6 +
        # kgr_7 und kgr_8 sind nicht anrechenbar
        calc.kgr_9 * calc.bmgl_pct_kgr9
    )
    return round(bmgl, 2)

def calculate_hoa(bmgl: float, fbw: float, bandbreite: float = 1.0) -> float:
    if bmgl < 2_000_000:
        hoa = 40.0 * (bmgl ** -0.1208) * fbw / 100
    else:
        hoa = 12.2611 * (bmgl ** -0.0394) * fbw / 100
    return round(hoa * bandbreite, 6)

def calculate_voa(bmgl, hoa, flph, umbau_zuschlag) -> float:
    return round(bmgl * hoa * flph * (1 + umbau_zuschlag), 2)
```

---

## 5. Frontend-Flow (Next.js)

### 5.1 Schritt 2 – Komplexitätsanalyse UI

```
Projektansicht (Schritt 1 abgeschlossen)
    │
    ▼
[Button: "Komplexitätsanalyse starten"]
    │
    ▼
Ladeanimation (LLM analysiert)
    │
    ▼
Analyse-Ansicht:
    ┌─────────────────────────────────────────────┐
    │  Merkmal A: Vielfalt der Besonderheiten      │
    │  KI-Vorschlag: 22 Punkte  [Konfidenz: Hoch] │
    │  Begründung: "EFH Gruppe 5, Hanglage..."    │
    │  [────────────────────────] Slider: 6–42    │
    │                                              │
    │  Merkmal B: Projektorganisation              │
    │  KI-Vorschlag: 2 Punkte  [Konfidenz: Mittel]│
    │  ⚠ Rückfrage: "Privater oder öff. AG?"      │
    │  [Privat] [Öffentlich/Institution]           │
    └─────────────────────────────────────────────┘
    │
    ▼
[Optionales Freitextfeld: "Begründung für Änderungen"]
    │
    ▼
[Button: "Analyse finalisieren"]
```

### 5.2 Schritt 3 – Honorarangebot UI

```
Analyse finalisiert
    │
    ▼
Honorarangebot:
    ┌─────────────────────────────────────────────┐
    │  BMGL: € 320.000 (Schätzung aus Budget)     │
    │  Bewertungspunkte: 30 | fbw: 1,534          │
    │  Honorarsatz hOA: 14,2%                     │
    │                                              │
    │  Leistungsphasen:                            │
    │  ☑ LPH 1 Grundlagenanalyse      2%          │
    │  ☑ LPH 2 Vorentwurf             8%          │
    │  ☑ LPH 3 Entwurf               12%          │
    │  ...                                         │
    │  fLPH gesamt: 100%                           │
    │                                              │
    │  Umbauzuschlag: [20%] ▼                      │
    │                                              │
    │  ─────────────────────────────              │
    │  Honorar netto:        € 48.230             │
    │  Nebenkosten (4%):     €  1.929             │
    │  Summe netto:          € 50.159             │
    │  MwSt. (20%):          € 10.032             │
    │  Summe brutto:         € 60.191             │
    └─────────────────────────────────────────────┘
    │
    ▼
[Speichern]  [Als PDF exportieren]
```

---

## 6. Lernlogik – Human in the Loop

### 6.1 Was wann gespeichert wird

| Ereignis | Was wird gespeichert | Tabelle |
|---------|---------------------|---------|
| Analyse finalisiert | Vollständiger Lernfall | `learning_examples` |
| Korrektur durch Architekt | `corrections`, `correction_delta` | `learning_examples` |
| Rückfrage beantwortet | Antwort + Zeitstempel | `complexity_questions` |
| Honorar finalisiert | Echte BMGL und VOA | `learning_examples` (Update) |

### 6.2 Qualitätsmessung des Lernens

```python
def calculate_quality_score(ai_scores: dict, final_scores: dict) -> float:
    """
    Misst wie gut der KI-Vorschlag war.
    1.0 = perfekt, 0.0 = komplett daneben
    """
    max_deviations = {"A": 36, "B": 4, "C": 4, "D": 4}
    total_deviation = 0
    for key in ["A", "B", "C", "D"]:
        deviation = abs(ai_scores[key] - final_scores[key])
        total_deviation += deviation / max_deviations[key]
    return round(1 - (total_deviation / 4), 2)
```

### 6.3 Mandantenübergreifendes Lernen (optional)

Das System kann entweder:
- **Tenant-spezifisch** lernen (Standard, DSGVO-sicher)
- **Tenant-übergreifend** lernen (mit expliziter Zustimmung, bessere Qualität)

Dieses Flag sollte in der `tenants`-Tabelle ergänzt werden:
```sql
ALTER TABLE tenants ADD COLUMN allow_shared_learning BOOLEAN DEFAULT false;
```

---

## 7. Implementierungsreihenfolge (empfohlen)

### Phase 1 – Datenbankstruktur (1–2 Tage)
1. SQL-Migrations für alle neuen Tabellen ausführen
2. Neue Status-Werte in `project_statuses` einfügen
3. Neue Indizes anlegen

### Phase 2 – Backend-Logik (3–5 Tage)
1. Pydantic-Schemas für neue Tabellen erstellen
2. CRUD-Operationen für `complexity_analyses`, `complexity_questions`, `fee_calculations`
3. Honorar-Berechnungslogik implementieren und testen
4. LLM-Analyse-Endpunkt implementieren (zunächst ohne Lernbasis)
5. `learning_examples` Speicherlogik implementieren

### Phase 3 – Frontend (3–5 Tage)
1. Schritt 2: Analyse-Ansicht mit Slider-Korrektur und Rückfragen
2. Schritt 3: Honorarberechnungs-Ansicht mit LPH-Auswahl
3. Status-Übergänge im Projekt-Workflow

### Phase 4 – Lernschicht (ab ~10 Projekten sinnvoll)
1. Ähnlichkeitssuche aktivieren (regelbasiert → später pgvector)
2. Qualitätsmonitoring implementieren
3. Feedback-Loop in LLM-Prompt integrieren

---

## 8. Wichtige Hinweise für die Implementierung

1. **Multi-Tenancy:** Alle neuen Tabellen erben die Tenant-Isolation über den
   JOIN auf `projects.tenant_id`. Kein direktes `tenant_id` in `complexity_analyses`
   nötig – immer über `project_id` joinen.

2. **Audit-Trail:** Korrekturen des Architekten in `complexity_analyses.corrections`
   sollten zusätzlich in `project_history` protokolliert werden (Konsistenz mit
   bestehendem Audit-System).

3. **LLM-Modell:** Der Endpunkt ist modell-agnostisch. Mistral OCR 2503 (Schritt 1)
   und das Analyse-LLM können unterschiedliche Modelle sein. Für Schritt 2 empfiehlt
   sich ein Reasoning-Modell (kein reines OCR-Modell).

4. **BMGL in früher Phase:** Solange keine echten KGR-Werte vorliegen, immer
   `bmgl_source = 'budget_estimate'` setzen und im Frontend deutlich kennzeichnen,
   dass es sich um eine Schätzung handelt.

5. **Keine Haftung durch das System:** Das Honorarangebot ist immer ein Entwurf,
   der vom Architekten freigegeben werden muss. Das Frontend sollte das klar
   kommunizieren.
