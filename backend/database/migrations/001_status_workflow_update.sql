-- ============================================================================
-- Migration 001: Status-Workflow Update für Sidebar-Navigation
-- Issue #22: Eliminierung von raw_extracted, Einführung von aktiv
-- ============================================================================

-- 1. Neuen Status 'aktiv' hinzufügen (falls nicht vorhanden)
INSERT INTO project_statuses (id, label) VALUES ('aktiv', 'Aktives Projekt')
ON CONFLICT (id) DO NOTHING;

-- 2. Bestehende 'verified_by_architect' Projekte zu 'aktiv' migrieren
UPDATE projects SET status_id = 'aktiv' WHERE status_id = 'verified_by_architect';

-- 3. Bestehende 'raw_extracted' Projekte zu 'needs_review' migrieren
UPDATE projects SET status_id = 'needs_review' WHERE status_id = 'raw_extracted';

-- 4. Alte Status-Einträge entfernen
DELETE FROM project_statuses WHERE id IN ('raw_extracted', 'verified_by_architect');

-- 5. Default-Constraint aktualisieren
ALTER TABLE projects ALTER COLUMN status_id SET DEFAULT 'needs_review';

-- ============================================================================
-- Rollback (falls benötigt)
-- ============================================================================
-- INSERT INTO project_statuses (id, label) VALUES
--     ('raw_extracted', 'KI-Rohextraktion'),
--     ('verified_by_architect', 'Vom Architekten verifiziert')
-- ON CONFLICT (id) DO NOTHING;
--
-- UPDATE projects SET status_id = 'raw_extracted' WHERE status_id = 'needs_review' AND created_at > NOW() - INTERVAL '1 hour';
-- UPDATE projects SET status_id = 'verified_by_architect' WHERE status_id = 'aktiv';
--
-- DELETE FROM project_statuses WHERE id = 'aktiv';
