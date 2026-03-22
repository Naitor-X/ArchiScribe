-- ============================================================================
-- ArchiScribe - Datenbankschema
-- Multi-Tenant SaaS-App für Architekten
-- ============================================================================

-- Aktiviere UUID-Erweiterung
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================================
-- ENUMS
-- ============================================================================

CREATE TYPE topography_enum AS ENUM ('eben', 'leichte Hanglage', 'starke Hanglage', 'Sonstiges');
CREATE TYPE access_status_enum AS ENUM ('voll erschlossen', 'teilerschlossen', 'nicht erschlossen');
CREATE TYPE project_type_enum AS ENUM ('Neubau', 'Bauen im Bestand', 'Umbau im Inneren', 'Sanierung/Modernis.', 'Zubau/Anbau', 'Aufstockung', 'noch unklar', 'Sonstiges');
CREATE TYPE building_type_enum AS ENUM ('EFH', 'Doppelhaus', 'Reihenhaus', 'Mehrfamilienhaus', 'Sonstige');
CREATE TYPE construction_method_enum AS ENUM ('Massivbau', 'Holzbau', 'noch offen');
CREATE TYPE heating_type_enum AS ENUM ('Wärmepumpe', 'Gasheizung', 'Fernwärme', 'Holz/Pellets', 'Sonstige');
CREATE TYPE own_contribution_enum AS ENUM ('ja', 'nein', 'teilweise');
CREATE TYPE accessibility_enum AS ENUM ('wichtig', 'optional', 'nicht relevant');

-- ============================================================================
-- TABELLEN
-- ============================================================================

-- -----------------------------------------------------------------------------
-- 1. tenants (Mandanten / Architekturbüros)
-- -----------------------------------------------------------------------------
CREATE TABLE tenants (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- -----------------------------------------------------------------------------
-- 2. project_statuses (Status des Dokuments)
-- -----------------------------------------------------------------------------
CREATE TABLE project_statuses (
    id VARCHAR(50) PRIMARY KEY,
    label VARCHAR(100) NOT NULL
);

-- Default-Status einfügen
INSERT INTO project_statuses (id, label) VALUES
    ('needs_review', 'Überprüfung erforderlich'),
    ('aktiv', 'Aktives Projekt');

-- -----------------------------------------------------------------------------
-- 3. projects (Das eigentliche Grundlagenformular)
-- -----------------------------------------------------------------------------
CREATE TABLE projects (
    -- Primärschlüssel und Referenzen
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    status_id VARCHAR(50) NOT NULL DEFAULT 'needs_review' REFERENCES project_statuses(id),

    -- Datei-Referenzen
    pdf_path VARCHAR(500),                          -- Pfad zum Original-PDF im Archiv
    page_paths JSONB,                               -- Array mit PNG-Pfaden pro Seite

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    -- Allgemeine Angaben
    client_name VARCHAR(255),
    address TEXT,
    phone VARCHAR(50),
    email VARCHAR(255),
    date DATE,

    -- Grundstück
    plot_location TEXT,
    plot_size_m2 DECIMAL(12, 2),
    landowner VARCHAR(255),
    topography topography_enum,
    topography_other VARCHAR(255),
    development_plan BOOLEAN,
    access_status access_status_enum,

    -- Vorstellungen / Ziele
    project_type project_type_enum,
    project_type_other VARCHAR(255),
    building_type building_type_enum,
    building_type_other VARCHAR(255),
    construction_method construction_method_enum,
    heating_type heating_type_enum,
    heating_type_other VARCHAR(255),
    budget DECIMAL(15, 2),
    planned_start DATE,
    own_contribution own_contribution_enum,
    own_contribution_details TEXT,

    -- Besondere Hinweise / Notizen
    accessibility accessibility_enum,
    outdoor_area TEXT,
    materiality TEXT,
    notes TEXT,

    -- Constraints
    CONSTRAINT valid_email CHECK (email IS NULL OR email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$'),
    CONSTRAINT valid_budget CHECK (budget IS NULL OR budget >= 0),
    CONSTRAINT valid_plot_size CHECK (plot_size_m2 IS NULL OR plot_size_m2 >= 0)
);

-- -----------------------------------------------------------------------------
-- 4. project_rooms (Dynamisches Raumprogramm)
-- -----------------------------------------------------------------------------
CREATE TABLE project_rooms (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    room_type VARCHAR(100) NOT NULL,
    quantity INTEGER DEFAULT 1,
    size_m2 DECIMAL(10, 2),
    special_requirements TEXT,

    -- Constraints
    CONSTRAINT valid_quantity CHECK (quantity > 0),
    CONSTRAINT valid_room_size CHECK (size_m2 IS NULL OR size_m2 >= 0)
);

-- -----------------------------------------------------------------------------
-- 5. ai_extractions (KI-Rohdaten für Debugging)
-- -----------------------------------------------------------------------------
CREATE TABLE ai_extractions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    raw_json JSONB NOT NULL,
    confidence_scores JSONB,
    extracted_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- -----------------------------------------------------------------------------
-- 6. project_history (Audit Trail / Versionierung)
-- -----------------------------------------------------------------------------
CREATE TABLE project_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    changed_by_user_id UUID,
    changed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    changes JSONB NOT NULL
);

-- ============================================================================
-- INDIZES (für Performance)
-- ============================================================================

-- Projects
CREATE INDEX idx_projects_tenant_id ON projects(tenant_id);
CREATE INDEX idx_projects_status_id ON projects(status_id);
CREATE INDEX idx_projects_created_at ON projects(created_at);
CREATE INDEX idx_projects_client_name ON projects USING gin(to_tsvector('german', client_name));
CREATE INDEX idx_projects_page_paths ON projects USING gin(page_paths);

-- Project Rooms
CREATE INDEX idx_project_rooms_project_id ON project_rooms(project_id);

-- AI Extractions
CREATE INDEX idx_ai_extractions_project_id ON ai_extractions(project_id);
CREATE INDEX idx_ai_extractions_extracted_at ON ai_extractions(extracted_at);

-- Project History
CREATE INDEX idx_project_history_project_id ON project_history(project_id);
CREATE INDEX idx_project_history_changed_at ON project_history(changed_at);

-- ============================================================================
-- TRIGGER (updated_at automatisch aktualisieren)
-- ============================================================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_projects_updated_at
    BEFORE UPDATE ON projects
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- API-KEYS (für Frontend-Authentifizierung)
-- ============================================================================

CREATE TABLE api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    key_hash VARCHAR(128) NOT NULL,           -- SHA-256 Hash des API-Keys
    key_prefix VARCHAR(20) NOT NULL,          -- "sk-tenant-550e8..." für Identifikation
    name VARCHAR(100),                         -- "Produktion", "Test", etc.
    is_active BOOLEAN DEFAULT true,
    last_used_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP WITH TIME ZONE,      -- Optional: Ablaufdatum

    UNIQUE(key_prefix)
);

CREATE INDEX idx_api_keys_tenant ON api_keys(tenant_id);
CREATE INDEX idx_api_keys_prefix ON api_keys(key_prefix);
CREATE INDEX idx_api_keys_active ON api_keys(is_active);

-- ============================================================================
-- VIEWS (optional für häufige Abfragen)
-- ============================================================================

-- View: Projekte mit Status-Label
CREATE VIEW v_projects_with_status AS
SELECT
    p.*,
    ps.label AS status_label,
    t.name AS tenant_name
FROM projects p
JOIN project_statuses ps ON p.status_id = ps.id
JOIN tenants t ON p.tenant_id = t.id;
