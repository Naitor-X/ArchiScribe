// Projektstatus
export type ProjectStatus = 'raw_extracted' | 'needs_review' | 'verified_by_architect'

export const STATUS_LABELS: Record<ProjectStatus, string> = {
  raw_extracted: 'Rohdaten',
  needs_review: 'Prüfung erforderlich',
  verified_by_architect: 'Verifiziert',
}

// Enum-Optionen (aus Backend-Schema)
export const ENUM_OPTIONS = {
  topography: ['eben', 'leichte Hanglage', 'starke Hanglage', 'Sonstiges'] as const,
  access_status: ['voll erschlossen', 'teilerschlossen', 'nicht erschlossen'] as const,
  project_type: ['Neubau', 'Bauen im Bestand', 'Umbau im Inneren', 'Sanierung/Modernis.', 'Zubau/Anbau', 'Aufstockung', 'noch unklar', 'Sonstiges'] as const,
  building_type: ['EFH', 'Doppelhaus', 'Reihenhaus', 'Mehrfamilienhaus', 'Sonstige'] as const,
  construction_method: ['Massivbau', 'Holzbau', 'noch offen'] as const,
  heating_type: ['Wärmepumpe', 'Gasheizung', 'Fernwärme', 'Holz/Pellets', 'Sonstige'] as const,
  own_contribution: ['ja', 'nein', 'teilweise'] as const,
  accessibility: ['wichtig', 'optional', 'nicht relevant'] as const,
} as const

// Raum im Raumprogramm
export interface ProjectRoom {
  id: string
  project_id: string
  room_type: string | null
  size_m2: number | null
  quantity: number
  special_requirements: string | null
  created_at: string
}

// Projekt (vollständig)
export interface Project {
  id: string
  tenant_id: string
  status_id: ProjectStatus
  form_date: string | null
  client_name: string | null
  address: string | null
  phone: string | null
  email: string | null
  plot_location: string | null
  plot_size_m2: number | null
  landowner: string | null
  topography: string | null
  topography_other: string | null
  development_plan: boolean
  access_status: string | null
  project_type: string | null
  project_type_other: string | null
  building_type: string | null
  building_type_other: string | null
  construction_method: string | null
  heating_type: string | null
  heating_type_other: string | null
  budget: number | null
  planned_start: string | null
  own_contribution: string | null
  own_contribution_details: string | null
  accessibility: string | null
  outdoor_area: string | null
  materiality: string | null
  notes: string | null
  rooms: ProjectRoom[]
  created_at: string
  updated_at: string
}

// Projekt-Listeneintrag (gekürzt)
export interface ProjectListItem {
  id: string
  client_name: string | null
  address: string | null
  status_id: ProjectStatus
  created_at: string
}

// API Response für Projektliste
export interface ProjectsResponse {
  projects: ProjectListItem[]
  total: number
}

// Update-Daten für Projekt
export type ProjectUpdate = Partial<Omit<Project, 'id' | 'tenant_id' | 'status_id' | 'rooms' | 'created_at' | 'updated_at'>>
