import { useQuery, useInfiniteQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from './client'
import type { components } from './schema'

export type ClientResponse = components['schemas']['ClientResponse']
export type ClientListResponse = components['schemas']['ClientListResponse']
export type ClientCreate = components['schemas']['ClientCreate']
export type ClientUpdate = components['schemas']['ClientUpdate']

export interface ClientsQueryParams {
  q?: string
  phone?: string
  limit?: number
  offset?: number
}

function buildClientsUrl(params: ClientsQueryParams): string {
  const searchParams = new URLSearchParams()
  if (params.q) searchParams.set('q', params.q)
  if (params.phone) searchParams.set('phone', params.phone)
  if (params.limit !== undefined) searchParams.set('limit', params.limit.toString())
  if (params.offset !== undefined) searchParams.set('offset', params.offset.toString())
  const qs = searchParams.toString()
  return `/api/clients${qs ? `?${qs}` : ''}`
}

export function useClients(params: ClientsQueryParams = {}) {
  return useQuery<ClientListResponse>({
    queryKey: ['clients', 'list', params],
    queryFn: () => apiClient<ClientListResponse>(buildClientsUrl(params)),
  })
}

export function useClientsTotalCount() {
  return useQuery<number>({
    queryKey: ['clients', 'total-count'],
    queryFn: async () => {
      const res = await apiClient<ClientListResponse>('/api/clients?limit=1')
      return res.total
    },
  })
}

export interface UseInfiniteClientsParams {
  q?: string
  phone?: string
  limit?: number
}

export function useInfiniteClients({
  q,
  phone,
  limit = 30,
}: UseInfiniteClientsParams = {}) {
  return useInfiniteQuery<ClientListResponse>({
    queryKey: ['clients', 'infinite', { q, phone, limit }],
    initialPageParam: 0,
    queryFn: ({ pageParam }) => {
      return apiClient<ClientListResponse>(
        buildClientsUrl({ q, phone, limit, offset: pageParam as number }),
      )
    },
    getNextPageParam: (lastPage) => {
      const nextOffset = lastPage.offset + lastPage.limit
      return nextOffset < lastPage.total ? nextOffset : undefined
    },
  })
}

export function useCreateClient() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (payload: ClientCreate) => {
      return apiClient<ClientResponse>('/api/clients', {
        method: 'POST',
        body: payload,
      })
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['clients'] })
    },
  })
}

export interface UpdateClientParams {
  id: number
  payload: ClientUpdate
}

export function useUpdateClient() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({ id, payload }: UpdateClientParams) => {
      return apiClient<ClientResponse>(`/api/clients/${id}`, {
        method: 'PATCH',
        body: payload,
      })
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['clients'] })
    },
  })
}

export function useDeleteClient() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (id: number) => {
      return apiClient<{ status: string }>(`/api/clients/${id}`, {
        method: 'DELETE',
      })
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['clients'] })
    },
  })
}
