import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useProjects } from '@/lib/queries'
import { STATUS_LABELS, type ProjectStatus } from '@/types'

function StatusBadge({ status }: { status: ProjectStatus }) {
  const colors: Record<ProjectStatus, string> = {
    raw_extracted: 'bg-yellow-100 text-yellow-800',
    needs_review: 'bg-orange-100 text-orange-800',
    verified_by_architect: 'bg-green-100 text-green-800',
  }

  return (
    <span className={`px-2 py-1 rounded-full text-xs font-medium ${colors[status]}`}>
      {STATUS_LABELS[status]}
    </span>
  )
}

function formatDate(dateString: string | null | undefined): string {
  if (!dateString) return '-'
  return new Date(dateString).toLocaleDateString('de-DE', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
  })
}

export default function ProjectList() {
  const [statusFilter, setStatusFilter] = useState<ProjectStatus | ''>('')
  const { data, isLoading, error } = useProjects(statusFilter || null)

  return (
    <div className="max-w-6xl mx-auto p-6">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">Projekte</h1>
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value as ProjectStatus | '')}
          className="border rounded-lg px-3 py-2 text-sm"
        >
          <option value="">Alle Status</option>
          <option value="raw_extracted">Rohdaten</option>
          <option value="needs_review">Prüfung erforderlich</option>
          <option value="verified_by_architect">Verifiziert</option>
        </select>
      </div>

      {error && (
        <div className="bg-red-50 text-red-700 p-4 rounded-lg mb-4">
          Fehler beim Laden: {(error as Error).message}
        </div>
      )}

      <div className="bg-white rounded-lg shadow overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Kunde
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Adresse
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Status
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Erstellt
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {isLoading ? (
              <tr>
                <td colSpan={4} className="px-6 py-4 text-center text-gray-500">
                  Lade Projekte...
                </td>
              </tr>
            ) : !data?.projects.length ? (
              <tr>
                <td colSpan={4} className="px-6 py-4 text-center text-gray-500">
                  Keine Projekte gefunden
                </td>
              </tr>
            ) : (
              data.projects.map((project) => (
                <tr
                  key={project.id}
                  className="hover:bg-gray-50 cursor-pointer"
                >
                  <td className="px-6 py-4 whitespace-nowrap">
                    <Link to={`/projects/${project.id}`} className="text-blue-600 hover:underline">
                      {project.client_name || '-'}
                    </Link>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {project.address || '-'}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <StatusBadge status={project.status_id} />
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {formatDate(project.created_at)}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
