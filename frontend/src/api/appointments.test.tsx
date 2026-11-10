import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import {
  useCreateAppointment,
  useUpdateAppointment,
  useDeleteAppointment,
  NeedsConfirmationError,
} from './appointments'

const mockFetch = vi.fn()
globalThis.fetch = mockFetch

describe('appointments API hooks', () => {
  beforeEach(() => {
    mockFetch.mockReset()
  })

  const createWrapper = () => {
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
    })
    return ({ children }: { children: React.ReactNode }) => (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    )
  }

  it('useCreateAppointment sends POST and returns appointment', async () => {
    const mockCreated = { id: 1, local_date: '2026-11-12' }
    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 201,
      headers: { get: () => 'application/json' },
      json: async () => mockCreated,
    })

    const { result } = renderHook(() => useCreateAppointment(), {
      wrapper: createWrapper(),
    })

    await act(async () => {
      await result.current.mutateAsync({
        starts_at: '2026-11-12T10:00:00',
        service_ids: [1],
        force: false,
      })
    })

    expect(mockFetch).toHaveBeenCalledWith(
      '/api/appointments',
      expect.objectContaining({
        method: 'POST',
      }),
    )
  })

  it('useUpdateAppointment sends PATCH and returns updated appointment', async () => {
    const mockUpdated = { id: 1, status: 'completed', local_date: '2026-11-12' }
    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      headers: { get: () => 'application/json' },
      json: async () => mockUpdated,
    })

    const { result } = renderHook(() => useUpdateAppointment(), {
      wrapper: createWrapper(),
    })

    await act(async () => {
      await result.current.mutateAsync({
        id: 1,
        payload: { status: 'completed' },
      })
    })

    expect(mockFetch).toHaveBeenCalledWith(
      '/api/appointments/1',
      expect.objectContaining({
        method: 'PATCH',
      }),
    )
  })

  it('useUpdateAppointment throws NeedsConfirmationError on 409', async () => {
    const mock409Detail = {
      code: 'needs_confirmation',
      warnings: ['outside_work_window'],
      overlapping_ids: [],
    }
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 409,
      headers: { get: () => 'application/json' },
      json: async () => ({ detail: mock409Detail }),
    })

    const { result } = renderHook(() => useUpdateAppointment(), {
      wrapper: createWrapper(),
    })

    let thrownError: unknown = null
    await act(async () => {
      try {
        await result.current.mutateAsync({
          id: 1,
          payload: { starts_at: '2026-11-12T20:00:00' },
        })
      } catch (err) {
        thrownError = err
      }
    })

    expect(thrownError).toBeInstanceOf(NeedsConfirmationError)
    expect((thrownError as NeedsConfirmationError).detail).toEqual(mock409Detail)
  })

  it('useDeleteAppointment sends DELETE and succeeds', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      headers: { get: () => 'application/json' },
      json: async () => ({ status: 'ok' }),
    })

    const { result } = renderHook(() => useDeleteAppointment(), {
      wrapper: createWrapper(),
    })

    await act(async () => {
      await result.current.mutateAsync(1)
    })

    expect(mockFetch).toHaveBeenCalledWith(
      '/api/appointments/1',
      expect.objectContaining({
        method: 'DELETE',
      }),
    )
  })
})
