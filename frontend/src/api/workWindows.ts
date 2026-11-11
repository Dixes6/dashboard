import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from './client'
import type { components } from './schema'

export type WorkWindowResponse = components['schemas']['WorkWindowResponse']
export type WorkWindowCreate = components['schemas']['WorkWindowCreate']
export type WorkWindowBulkCreate = components['schemas']['WorkWindowBulkCreate']
export type WorkWindowUpdate = components['schemas']['WorkWindowUpdate']
export type WorkWindowTimeSlot = components['schemas']['WorkWindowTimeSlot']

export function useWorkWindows(dateFrom?: string, dateTo?: string) {
  const query = new URLSearchParams()
  if (dateFrom) query.set('date_from', dateFrom)
  if (dateTo) query.set('date_to', dateTo)
  const queryStr = query.toString() ? `?${query.toString()}` : ''

  return useQuery<WorkWindowResponse[]>({
    queryKey: ['work-windows', dateFrom, dateTo],
    queryFn: () => apiClient<WorkWindowResponse[]>(`/api/work-windows${queryStr}`),
  })
}

export function useCreateWindow() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (payload: WorkWindowCreate) =>
      apiClient<WorkWindowResponse>('/api/work-windows', {
        method: 'POST',
        body: payload,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['day'] })
      queryClient.invalidateQueries({ queryKey: ['calendar'] })
      queryClient.invalidateQueries({ queryKey: ['work-windows'] })
    },
  })
}

export function useUpdateWindow() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: WorkWindowUpdate }) =>
      apiClient<WorkWindowResponse>(`/api/work-windows/${id}`, {
        method: 'PATCH',
        body: data,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['day'] })
      queryClient.invalidateQueries({ queryKey: ['calendar'] })
      queryClient.invalidateQueries({ queryKey: ['work-windows'] })
    },
  })
}

export function useDeleteWindow() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (id: number) =>
      apiClient<void>(`/api/work-windows/${id}`, {
        method: 'DELETE',
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['day'] })
      queryClient.invalidateQueries({ queryKey: ['calendar'] })
      queryClient.invalidateQueries({ queryKey: ['work-windows'] })
    },
  })
}

export function useBulkCreateWindows() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (payload: WorkWindowBulkCreate) =>
      apiClient<WorkWindowResponse[]>('/api/work-windows/bulk', {
        method: 'POST',
        body: payload,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['day'] })
      queryClient.invalidateQueries({ queryKey: ['calendar'] })
      queryClient.invalidateQueries({ queryKey: ['work-windows'] })
    },
  })
}
