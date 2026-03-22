import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useProject, useUpdateProject, useUpdateProjectStatus } from '@/lib/queries'
import { ENUM_OPTIONS, STATUS_LABELS, type ProjectStatus, type ProjectUpdate } from '@/types'

function StatusBadge({ status }: { status: ProjectStatus }) {
  const colors: Record<ProjectStatus, string> = {
    needs_review: 'bg-orange-100 text-orange-800',
    aktiv: 'bg-green-100 text-green-800',
  }

  return (
    <span className={`px-3 py-1 rounded-full text-sm font-medium ${colors[status]}`}>
      {STATUS_LABELS[status]}
    </span>
  )
}

function EnumSelect({
  id,
  value,
  options,
  onChange,
}: {
  id: string
  value: string | null
  options: readonly string[]
  onChange: (value: string) => void
}) {
  return (
    <select
      id={id}
      value={value || ''}
      onChange={(e) => onChange(e.target.value)}
      className="w-full border rounded-lg px-3 py-2 text-sm"
    >
      <option value="">Bitte wählen</option>
      {options.map((opt) => (
        <option key={opt} value={opt}>{opt}</option>
      ))}
    </select>
  )
}

function formatDateForInput(dateString: string | null | undefined): string {
  if (!dateString) return ''
  return dateString.split('T')[0]
}

export default function ProjectDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { data: project, isLoading, error } = useProject(id!)
  const updateProject = useUpdateProject()
  const updateStatus = useUpdateProjectStatus()

  const [formData, setFormData] = useState<ProjectUpdate>({})
  const [message, setMessage] = useState<{ text: string; isError: boolean } | null>(null)

  // Bestimme die Rückkehr-Route basierend auf dem Status
  const backRoute = project?.status_id === 'needs_review' ? '/inbox' : '/projekte'

  useEffect(() => {
    if (project) {
      setFormData({
        client_name: project.client_name,
        address: project.address,
        phone: project.phone,
        email: project.email,
        plot_location: project.plot_location,
        plot_size_m2: project.plot_size_m2,
        landowner: project.landowner,
        topography: project.topography,
        topography_other: project.topography_other,
        development_plan: project.development_plan,
        access_status: project.access_status,
        project_type: project.project_type,
        project_type_other: project.project_type_other,
        building_type: project.building_type,
        building_type_other: project.building_type_other,
        construction_method: project.construction_method,
        heating_type: project.heating_type,
        heating_type_other: project.heating_type_other,
        budget: project.budget,
        planned_start: project.planned_start,
        own_contribution: project.own_contribution,
        own_contribution_details: project.own_contribution_details,
        accessibility: project.accessibility,
        outdoor_area: project.outdoor_area,
        materiality: project.materiality,
        notes: project.notes,
      })
    }
  }, [project])

  const updateField = <K extends keyof ProjectUpdate>(field: K, value: ProjectUpdate[K]) => {
    setFormData((prev) => ({ ...prev, [field]: value }))
  }

  const handleSave = async () => {
    if (!id) return

    try {
      await updateProject.mutateAsync({ id, data: formData })
      setMessage({ text: 'Projekt erfolgreich gespeichert', isError: false })
    } catch (err) {
      setMessage({ text: `Fehler: ${(err as Error).message}`, isError: true })
    }

    setTimeout(() => setMessage(null), 3000)
  }

  const handleVerify = async () => {
    if (!id) return

    try {
      await updateStatus.mutateAsync({ id, status: 'aktiv' })
      setMessage({ text: 'Projekt als aktiv markiert', isError: false })
      // Nach kurzer Verzögerung zur Projekte-Liste navigieren
      setTimeout(() => navigate('/projekte'), 1500)
    } catch (err) {
      setMessage({ text: `Fehler: ${(err as Error).message}`, isError: true })
    }
  }

  if (!id) {
    navigate('/')
    return null
  }

  if (isLoading) {
    return (
      <div className="max-w-4xl mx-auto p-6">
        <p className="text-gray-500">Lade Projekt...</p>
      </div>
    )
  }

  if (error || !project) {
    return (
      <div className="max-w-4xl mx-auto p-6">
        <div className="bg-red-50 text-red-700 p-4 rounded-lg">
          Fehler beim Laden: {(error as Error)?.message || 'Projekt nicht gefunden'}
        </div>
      </div>
    )
  }

  return (
    <div className="max-w-4xl mx-auto p-6">
      <div className="flex justify-between items-center mb-6">
        <div>
          <button onClick={() => navigate(backRoute)} className="text-blue-600 hover:underline mb-2">
            ← Zurück zur {project.status_id === 'needs_review' ? 'Inbox' : 'Projektliste'}
          </button>
          <h1 className="text-2xl font-bold">{project.client_name || 'Projekt'}</h1>
        </div>
        <div className="flex items-center gap-4">
          <StatusBadge status={project.status_id} />
          {project.status_id === 'needs_review' && (
            <button
              onClick={handleVerify}
              disabled={updateStatus.isPending}
              className="bg-green-600 text-white px-4 py-2 rounded-lg hover:bg-green-700 disabled:opacity-50"
            >
              Aktivieren
            </button>
          )}
        </div>
      </div>

      {message && (
        <div className={`p-4 rounded-lg mb-4 ${message.isError ? 'bg-red-50 text-red-700' : 'bg-green-50 text-green-700'}`}>
          {message.text}
        </div>
      )}

      <form onSubmit={(e) => { e.preventDefault(); handleSave() }} className="space-y-8">
        {/* Kontaktdaten */}
        <section className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold mb-4">Kontaktdaten</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Kunde</label>
              <input
                type="text"
                value={formData.client_name || ''}
                onChange={(e) => updateField('client_name', e.target.value || null)}
                className="w-full border rounded-lg px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Adresse</label>
              <input
                type="text"
                value={formData.address || ''}
                onChange={(e) => updateField('address', e.target.value || null)}
                className="w-full border rounded-lg px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Telefon</label>
              <input
                type="tel"
                value={formData.phone || ''}
                onChange={(e) => updateField('phone', e.target.value || null)}
                className="w-full border rounded-lg px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">E-Mail</label>
              <input
                type="email"
                value={formData.email || ''}
                onChange={(e) => updateField('email', e.target.value || null)}
                className="w-full border rounded-lg px-3 py-2 text-sm"
              />
            </div>
          </div>
        </section>

        {/* Grundstück */}
        <section className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold mb-4">Grundstück</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Lage</label>
              <input
                type="text"
                value={formData.plot_location || ''}
                onChange={(e) => updateField('plot_location', e.target.value || null)}
                className="w-full border rounded-lg px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Größe (m²)</label>
              <input
                type="number"
                step="0.01"
                value={formData.plot_size_m2 ?? ''}
                onChange={(e) => updateField('plot_size_m2', e.target.value ? parseFloat(e.target.value) : null)}
                className="w-full border rounded-lg px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Grundstückseigentümer</label>
              <input
                type="text"
                value={formData.landowner || ''}
                onChange={(e) => updateField('landowner', e.target.value || null)}
                className="w-full border rounded-lg px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Topografie</label>
              <EnumSelect
                id="topography"
                value={formData.topography || null}
                options={ENUM_OPTIONS.topography}
                onChange={(v) => updateField('topography', v || null)}
              />
            </div>
            {formData.topography === 'Sonstiges' && (
              <div className="md:col-span-2">
                <label className="block text-sm font-medium text-gray-700 mb-1">Sonstige Topografie</label>
                <input
                  type="text"
                  value={formData.topography_other || ''}
                  onChange={(e) => updateField('topography_other', e.target.value || null)}
                  className="w-full border rounded-lg px-3 py-2 text-sm"
                />
              </div>
            )}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Erschließung</label>
              <EnumSelect
                id="access_status"
                value={formData.access_status || null}
                options={ENUM_OPTIONS.access_status}
                onChange={(v) => updateField('access_status', v || null)}
              />
            </div>
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="development_plan"
                checked={formData.development_plan || false}
                onChange={(e) => updateField('development_plan', e.target.checked)}
                className="rounded"
              />
              <label htmlFor="development_plan" className="text-sm font-medium text-gray-700">
                Bebauungsplan vorhanden
              </label>
            </div>
          </div>
        </section>

        {/* Vorstellungen / Ziele */}
        <section className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold mb-4">Vorstellungen / Ziele</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Projektart</label>
              <EnumSelect
                id="project_type"
                value={formData.project_type || null}
                options={ENUM_OPTIONS.project_type}
                onChange={(v) => updateField('project_type', v || null)}
              />
            </div>
            {formData.project_type === 'Sonstiges' && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Sonstige Projektart</label>
                <input
                  type="text"
                  value={formData.project_type_other || ''}
                  onChange={(e) => updateField('project_type_other', e.target.value || null)}
                  className="w-full border rounded-lg px-3 py-2 text-sm"
                />
              </div>
            )}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Gebäudetyp</label>
              <EnumSelect
                id="building_type"
                value={formData.building_type || null}
                options={ENUM_OPTIONS.building_type}
                onChange={(v) => updateField('building_type', v || null)}
              />
            </div>
            {formData.building_type === 'Sonstige' && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Sonstiger Gebäudetyp</label>
                <input
                  type="text"
                  value={formData.building_type_other || ''}
                  onChange={(e) => updateField('building_type_other', e.target.value || null)}
                  className="w-full border rounded-lg px-3 py-2 text-sm"
                />
              </div>
            )}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Bauweise</label>
              <EnumSelect
                id="construction_method"
                value={formData.construction_method || null}
                options={ENUM_OPTIONS.construction_method}
                onChange={(v) => updateField('construction_method', v || null)}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Heizung</label>
              <EnumSelect
                id="heating_type"
                value={formData.heating_type || null}
                options={ENUM_OPTIONS.heating_type}
                onChange={(v) => updateField('heating_type', v || null)}
              />
            </div>
            {formData.heating_type === 'Sonstige' && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Sonstige Heizung</label>
                <input
                  type="text"
                  value={formData.heating_type_other || ''}
                  onChange={(e) => updateField('heating_type_other', e.target.value || null)}
                  className="w-full border rounded-lg px-3 py-2 text-sm"
                />
              </div>
            )}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Budget (€)</label>
              <input
                type="number"
                step="0.01"
                value={formData.budget ?? ''}
                onChange={(e) => updateField('budget', e.target.value ? parseFloat(e.target.value) : null)}
                className="w-full border rounded-lg px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Geplanter Baubeginn</label>
              <input
                type="date"
                value={formatDateForInput(formData.planned_start)}
                onChange={(e) => updateField('planned_start', e.target.value || null)}
                className="w-full border rounded-lg px-3 py-2 text-sm"
              />
            </div>
          </div>
        </section>

        {/* Besondere Hinweise */}
        <section className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold mb-4">Besondere Hinweise</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Eigenleistung</label>
              <EnumSelect
                id="own_contribution"
                value={formData.own_contribution || null}
                options={ENUM_OPTIONS.own_contribution}
                onChange={(v) => updateField('own_contribution', v || null)}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Barrierefreiheit</label>
              <EnumSelect
                id="accessibility"
                value={formData.accessibility || null}
                options={ENUM_OPTIONS.accessibility}
                onChange={(v) => updateField('accessibility', v || null)}
              />
            </div>
            <div className="md:col-span-2">
              <label className="block text-sm font-medium text-gray-700 mb-1">Details zur Eigenleistung</label>
              <input
                type="text"
                value={formData.own_contribution_details || ''}
                onChange={(e) => updateField('own_contribution_details', e.target.value || null)}
                className="w-full border rounded-lg px-3 py-2 text-sm"
              />
            </div>
            <div className="md:col-span-2">
              <label className="block text-sm font-medium text-gray-700 mb-1">Außenanlagen</label>
              <textarea
                value={formData.outdoor_area || ''}
                onChange={(e) => updateField('outdoor_area', e.target.value || null)}
                rows={2}
                className="w-full border rounded-lg px-3 py-2 text-sm"
              />
            </div>
            <div className="md:col-span-2">
              <label className="block text-sm font-medium text-gray-700 mb-1">Materialität</label>
              <textarea
                value={formData.materiality || ''}
                onChange={(e) => updateField('materiality', e.target.value || null)}
                rows={2}
                className="w-full border rounded-lg px-3 py-2 text-sm"
              />
            </div>
            <div className="md:col-span-2">
              <label className="block text-sm font-medium text-gray-700 mb-1">Notizen</label>
              <textarea
                value={formData.notes || ''}
                onChange={(e) => updateField('notes', e.target.value || null)}
                rows={3}
                className="w-full border rounded-lg px-3 py-2 text-sm"
              />
            </div>
          </div>
        </section>

        {/* Raumprogramm */}
        <section className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold mb-4">Raumprogramm</h2>
          {project.rooms && project.rooms.length > 0 ? (
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Raumtyp</th>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Fläche (m²)</th>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Anzahl</th>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Besondere Anforderungen</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {project.rooms.map((room) => (
                  <tr key={room.id}>
                    <td className="px-4 py-2 text-sm">{room.room_type || '-'}</td>
                    <td className="px-4 py-2 text-sm">{room.size_m2 || '-'}</td>
                    <td className="px-4 py-2 text-sm">{room.quantity || 1}</td>
                    <td className="px-4 py-2 text-sm">{room.special_requirements || '-'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <p className="text-gray-500 text-sm">Keine Räume vorhanden</p>
          )}
        </section>

        {/* Speichern-Button */}
        <div className="flex justify-end gap-4">
          <button
            type="button"
            onClick={() => navigate(backRoute)}
            className="px-4 py-2 text-gray-700 hover:text-gray-900"
          >
            Abbrechen
          </button>
          <button
            type="submit"
            disabled={updateProject.isPending}
            className="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 disabled:opacity-50"
          >
            {updateProject.isPending ? 'Speichere...' : 'Speichern'}
          </button>
        </div>
      </form>
    </div>
  )
}
