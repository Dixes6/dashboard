import { useMutation, useQueryClient } from '@tanstack/react-query'
import type { components } from './schema'

// AppointmentResponse экспортируется из home.ts, здесь используем напрямую
type AppointmentResponse = components['schemas']['AppointmentResponse']
export type AppointmentCreate = components['schemas']['AppointmentCreate']
export type AppointmentUpdate = Partial<components['schemas']['AppointmentUpdate']>

/** Тип ответа 409 "needs_confirmation" — не в schema.d.ts, описан по коду бэкенда */
export interface NeedsConfirmationDetail {
  code: 'needs_confirmation'
  warnings: string[]
  overlapping_ids: number[]
}

export class NeedsConfirmationError extends Error {
  detail: NeedsConfirmationDetail

  constructor(detail: NeedsConfirmationDetail) {
    super('needs_confirmation')
    this.name = 'NeedsConfirmationError'
    this.detail = detail
  }
}

export function useCreateAppointment() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (payload: AppointmentCreate): Promise<AppointmentResponse> => {
      const response = await fetch('/api/appointments', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })

      if (response.status === 409) {
        const data = await response.json()
        if (data?.detail?.code === 'needs_confirmation') {
          throw new NeedsConfirmationError(data.detail as NeedsConfirmationDetail)
        }
        // Другая 409 — пробрасываем как обычную ошибку
        const msg = data?.detail ?? 'Конфликт при создании записи'
        throw new Error(typeof msg === 'string' ? msg : JSON.stringify(msg))
      }

      if (!response.ok) {
        const data = await response.json().catch(() => ({}))
        const msg = data?.detail ?? `Ошибка ${response.status}`
        throw new Error(typeof msg === 'string' ? msg : JSON.stringify(msg))
      }

      return response.json() as Promise<AppointmentResponse>
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['calendar'] })
      queryClient.invalidateQueries({ queryKey: ['day', data.local_date] })
      queryClient.invalidateQueries({ queryKey: ['appointments', 'next'] })
      queryClient.invalidateQueries({ queryKey: ['clients'] })
    },
  })
}

export interface UpdateAppointmentVariables {
  id: number
  payload: AppointmentUpdate
}

export function useUpdateAppointment() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({ id, payload }: UpdateAppointmentVariables): Promise<AppointmentResponse> => {
      const response = await fetch(`/api/appointments/${id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })

      if (response.status === 409) {
        const data = await response.json()
        if (data?.detail?.code === 'needs_confirmation') {
          throw new NeedsConfirmationError(data.detail as NeedsConfirmationDetail)
        }
        const msg = data?.detail ?? 'Конфликт при обновлении записи'
        throw new Error(typeof msg === 'string' ? msg : JSON.stringify(msg))
      }

      if (!response.ok) {
        const data = await response.json().catch(() => ({}))
        const msg = data?.detail ?? `Ошибка ${response.status}`
        throw new Error(typeof msg === 'string' ? msg : JSON.stringify(msg))
      }

      return response.json() as Promise<AppointmentResponse>
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['calendar'] })
      queryClient.invalidateQueries({ queryKey: ['day'] })
      queryClient.invalidateQueries({ queryKey: ['appointments', 'next'] })
      queryClient.invalidateQueries({ queryKey: ['clients'] })
    },
  })
}

export function useDeleteAppointment() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (id: number): Promise<{ status: string }> => {
      const response = await fetch(`/api/appointments/${id}`, {
        method: 'DELETE',
      })

      if (!response.ok) {
        const data = await response.json().catch(() => ({}))
        const msg = data?.detail ?? `Ошибка ${response.status}`
        throw new Error(typeof msg === 'string' ? msg : JSON.stringify(msg))
      }

      return response.json() as Promise<{ status: string }>
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['calendar'] })
      queryClient.invalidateQueries({ queryKey: ['day'] })
      queryClient.invalidateQueries({ queryKey: ['appointments', 'next'] })
      queryClient.invalidateQueries({ queryKey: ['clients'] })
    },
  })
}

