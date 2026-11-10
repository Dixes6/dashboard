import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useNextAppointment } from './home'

const mockFetch = vi.fn()
globalThis.fetch = mockFetch

describe('useNextAppointment', () => {
  beforeEach(() => {
    mockFetch.mockReset()
  })

  it('returns appointment on 200 response', async () => {
    const mockAppointment = {
      id: 1,
      client: { id: 1, name: 'Анна', phone: '+7 (900) 123-45-67' },
      starts_at: '2026-11-15T10:00:00Z',
      ends_at: '2026-11-15T11:30:00Z',
      local_date: '2026-11-15',
      local_start_time: '10:00',
      local_end_time: '11:30',
      status: 'scheduled',
      source: 'manual',
      note: null,
      list_price: 3000,
      final_price: 3000,
      price_overridden: false,
      services: [
        { service_id: 1, name_snapshot: 'Маникюр', price_snapshot: 3000, duration_snapshot: 90, position: 1 },
      ],
      warnings: [],
      created_at: '2026-11-10T10:00:00Z',
      updated_at: '2026-11-10T10:00:00Z',
    }

    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      headers: {
        get: () => 'application/json',
      },
      json: async () => mockAppointment,
    })

    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    })
    const { result } = renderHook(() => useNextAppointment(), {
      wrapper: ({ children }: { children: React.ReactNode }) => (
        <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
      ),
    })

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true)
    })

    expect(result.current.data).toEqual(mockAppointment)
  })

  it('returns null on 204 response', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 204,
      headers: {
        get: () => null,
      },
    })

    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    })
    const { result } = renderHook(() => useNextAppointment(), {
      wrapper: ({ children }: { children: React.ReactNode }) => (
        <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
      ),
    })

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true)
    })

    expect(result.current.data).toBeNull()
  })
})