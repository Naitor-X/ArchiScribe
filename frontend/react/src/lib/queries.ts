import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from './api'
import type { ProjectStatus, ProjectUpdate } from '@/types'

export function useProjects(status: ProjectStatus | null) {
  return useQuery({
    queryKey: ['projects', status],
    queryFn: () => api.getProjects(status),
  })
}

export function useProject(id: string) {
  return useQuery({
    queryKey: ['project', id],
    queryFn: () => api.getProject(id),
    enabled: !!id,
  })
}

export function useUpdateProject() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: ProjectUpdate }) =>
      api.updateProject(id, data),
    onSuccess: (updatedProject) => {
      // Projekt-Cache aktualisieren
      queryClient.setQueryData(['project', updatedProject.id], updatedProject)
      // Liste invalidieren für Status-Updates
      queryClient.invalidateQueries({ queryKey: ['projects'] })
    },
  })
}

export function useUpdateProjectStatus() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ id, status }: { id: string; status: ProjectStatus }) =>
      api.updateProjectStatus(id, status),
    onSuccess: (updatedProject) => {
      // Projekt und Liste invalidieren
      queryClient.invalidateQueries({ queryKey: ['project', updatedProject.id] })
      queryClient.invalidateQueries({ queryKey: ['projects'] })
    },
  })
}
