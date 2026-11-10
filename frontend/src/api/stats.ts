import { useQuery } from '@tanstack/react-query'
import { apiClient } from './client'
import type { components } from './schema'

export type MonthStatsResponse = components['schemas']['MonthStatsResponse']
export type MonthSummaryResponse = components['schemas']['MonthSummaryResponse']
export type TopServiceResponse = components['schemas']['TopServiceResponse']
export type BestDayResponse = components['schemas']['BestDayResponse']

export function useStatsMonth(month?: string) {
  return useQuery<MonthStatsResponse>({
    queryKey: ['stats', 'month', month],
    queryFn: () => {
      const url = month ? `/api/stats/month?month=${encodeURIComponent(month)}` : '/api/stats/month'
      return apiClient<MonthStatsResponse>(url)
    },
  })
}

export function useStatsMonths() {
  return useQuery<MonthSummaryResponse[]>({
    queryKey: ['stats', 'months'],
    queryFn: () => apiClient<MonthSummaryResponse[]>('/api/stats/months'),
  })
}
