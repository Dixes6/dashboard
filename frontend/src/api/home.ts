import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from './client'
import type { components } from './schema'

export type SettingResponse = components['schemas']['SettingResponse']
export type SettingUpdate = components['schemas']['SettingUpdate']
export type CalendarDayResponse = components['schemas']['CalendarDayResponse']
export type DayDetailsResponse = components['schemas']['DayDetailsResponse']
export type AppointmentResponse = components['schemas']['AppointmentResponse']
export type IncomeCreate = components['schemas']['IncomeCreate']
export type IncomeResponse = components['schemas']['IncomeResponse']
export type ExpenseCreate = components['schemas']['ExpenseCreate']
export type ExpenseResponse = components['schemas']['ExpenseResponse']

// Settings
export function useSettings() {
  return useQuery<SettingResponse>({
    queryKey: ['settings'],
    queryFn: () => apiClient<SettingResponse>('/api/settings'),
  })
}

export function useUpdateSettings() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (payload: SettingUpdate) => {
      return apiClient<SettingResponse>('/api/settings', {
        method: 'PUT',
        body: payload,
      })
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['settings'] })
    },
  })
}

// Calendar month view
export function useCalendar(month: string) {
  return useQuery<CalendarDayResponse[]>({
    queryKey: ['calendar', month],
    queryFn: () => apiClient<CalendarDayResponse[]>(`/api/calendar?month=${month}`),
    enabled: !!month,
  })
}

// Day details
export function useDay(date: string) {
  return useQuery<DayDetailsResponse>({
    queryKey: ['day', date],
    queryFn: () => apiClient<DayDetailsResponse>(`/api/days/${date}`),
    enabled: !!date,
  })
}

// Next appointment
export function useNextAppointment() {
  return useQuery<AppointmentResponse | null>({
    queryKey: ['appointments', 'next'],
    queryFn: async () => {
      try {
        const response = await fetch('/api/appointments/next', {
          credentials: 'include',
        })

        if (response.status === 204) {
          return null
        }

        if (!response.ok) {
          let detail = 'Произошла ошибка при выполнении запроса'
          const contentType = response.headers.get('content-type')
          if (contentType && contentType.includes('application/json')) {
            try {
              const data = await response.json()
              if (data?.detail) {
                detail = typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail)
              }
            } catch {
              // ignore
            }
          }
          throw new Error(detail)
        }

        const contentType = response.headers.get('content-type')
        if (contentType && contentType.includes('application/json')) {
          return await response.json()
        }
        return null
      } catch (error) {
        if (error instanceof Error && error.message.includes('204')) {
          return null
        }
        throw error
      }
    },
  })
}

// Create income
export function useCreateIncome() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (payload: IncomeCreate) => {
      return apiClient<IncomeResponse>('/api/incomes', {
        method: 'POST',
        body: payload,
      })
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['stats'] })
      queryClient.invalidateQueries({ queryKey: ['day'] })
      queryClient.invalidateQueries({ queryKey: ['calendar'] })
      queryClient.invalidateQueries({ queryKey: ['finance'] })
    },
  })
}

// Create expense
export function useCreateExpense() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (payload: ExpenseCreate) => {
      return apiClient<ExpenseResponse>('/api/expenses', {
        method: 'POST',
        body: payload,
      })
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['stats'] })
      queryClient.invalidateQueries({ queryKey: ['day'] })
      queryClient.invalidateQueries({ queryKey: ['calendar'] })
      queryClient.invalidateQueries({ queryKey: ['finance'] })
    },
  })
}