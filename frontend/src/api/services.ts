import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from './client'
import type { components } from './schema'

export type ServiceResponse = components['schemas']['ServiceResponse']
export type ServiceCreate = components['schemas']['ServiceCreate']
export type ServiceUpdate = components['schemas']['ServiceUpdate']

export interface UseServicesOptions {
  includeArchived?: boolean
}

export function useServices(options: UseServicesOptions = {}) {
  const { includeArchived = false } = options

  return useQuery<ServiceResponse[]>({
    queryKey: ['services', { includeArchived }],
    queryFn: async () => {
      const queryParam = includeArchived ? '?include_archived=true' : '?include_archived=false'
      const data = await apiClient<ServiceResponse[]>(`/api/services${queryParam}`)
      return [...data].sort((a, b) => a.sort_order - b.sort_order)
    },
  })
}

export function useCreateService() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (payload: ServiceCreate) => {
      return apiClient<ServiceResponse>('/api/services', {
        method: 'POST',
        body: payload,
      })
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['services'] })
    },
  })
}

export interface UpdateServiceParams {
  id: number
  payload: ServiceUpdate
}

export function useUpdateService() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({ id, payload }: UpdateServiceParams) => {
      return apiClient<ServiceResponse>(`/api/services/${id}`, {
        method: 'PATCH',
        body: payload,
      })
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['services'] })
    },
  })
}
