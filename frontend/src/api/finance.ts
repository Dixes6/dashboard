import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from './client'
import type { components } from './schema'
import type { IncomeResponse, ExpenseResponse } from './home'

export type FinanceEntriesListResponse = components['schemas']['FinanceEntriesListResponse']
export type FinanceEntryResponse = components['schemas']['FinanceEntryResponse']
export type IncomeUpdate = components['schemas']['IncomeUpdate']
export type ExpenseUpdate = components['schemas']['ExpenseUpdate']

export function useFinanceEntries(type: 'income' | 'expense', month?: string) {
  return useQuery<FinanceEntriesListResponse>({
    queryKey: ['finance', 'entries', type, month],
    queryFn: () => {
      const params = new URLSearchParams({ type })
      if (month) params.set('month', month)
      return apiClient<FinanceEntriesListResponse>(`/api/finance/entries?${params.toString()}`)
    },
  })
}

export interface UpdateIncomeVariables {
  id: number
  payload: IncomeUpdate
}

export function useUpdateIncome() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({ id, payload }: UpdateIncomeVariables) => {
      return apiClient<IncomeResponse>(`/api/incomes/${id}`, {
        method: 'PATCH',
        body: payload,
      })
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['stats'] })
      queryClient.invalidateQueries({ queryKey: ['finance'] })
      queryClient.invalidateQueries({ queryKey: ['day'] })
      queryClient.invalidateQueries({ queryKey: ['calendar'] })
    },
  })
}

export function useDeleteIncome() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (id: number) => {
      return apiClient<{ status: string }>(`/api/incomes/${id}`, {
        method: 'DELETE',
      })
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['stats'] })
      queryClient.invalidateQueries({ queryKey: ['finance'] })
      queryClient.invalidateQueries({ queryKey: ['day'] })
      queryClient.invalidateQueries({ queryKey: ['calendar'] })
    },
  })
}

export interface UpdateExpenseVariables {
  id: number
  payload: ExpenseUpdate
}

export function useUpdateExpense() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({ id, payload }: UpdateExpenseVariables) => {
      return apiClient<ExpenseResponse>(`/api/expenses/${id}`, {
        method: 'PATCH',
        body: payload,
      })
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['stats'] })
      queryClient.invalidateQueries({ queryKey: ['finance'] })
      queryClient.invalidateQueries({ queryKey: ['day'] })
      queryClient.invalidateQueries({ queryKey: ['calendar'] })
    },
  })
}

export function useDeleteExpense() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (id: number) => {
      return apiClient<{ status: string }>(`/api/expenses/${id}`, {
        method: 'DELETE',
      })
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['stats'] })
      queryClient.invalidateQueries({ queryKey: ['finance'] })
      queryClient.invalidateQueries({ queryKey: ['day'] })
      queryClient.invalidateQueries({ queryKey: ['calendar'] })
    },
  })
}

