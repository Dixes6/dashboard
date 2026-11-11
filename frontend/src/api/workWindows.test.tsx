import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, waitFor, act } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import {
  useWorkWindows,
  useCreateWindow,
  useBulkCreateWindows,
  useUpdateWindow,
  useDeleteWindow,
} from './workWindows'

const mockFetch = vi.fn()
globalThis.fetch = mockFetch

describe('workWindows API hooks', () => {
  beforeEach(() => {
    mockFetch.mockReset()
  })

  const createWrapper = () => {
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    })
    return ({ children }: { children: React.ReactNode }) => (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    )
  }

  it('useWorkWindows fetches list of windows', async () => {
    const mockWindows = [
      { id: 1, date: '2026-11-12', start_time: '10:00:00', end_time: '18:00:00' },
    ]

    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      headers: { get: () => 'application/json' },
      json: async () => mockWindows,
    })

    const { result } = renderHook(() => useWorkWindows('2026-11-01', '2026-11-30'), {
      wrapper: createWrapper(),
    })

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true)
    })

    expect(result.current.data).toEqual(mockWindows)
  })

  it('useCreateWindow sends POST request and invalidates queries', async () => {
    const newWindow = { id: 2, date: '2026-11-15', start_time: '10:00:00', end_time: '18:00:00' }

    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 201,
      headers: { get: () => 'application/json' },
      json: async () => newWindow,
    })

    const { result } = renderHook(() => useCreateWindow(), {
      wrapper: createWrapper(),
    })

    let createdData: unknown = null
    await act(async () => {
      createdData = await result.current.mutateAsync({
        date: '2026-11-15',
        start_time: '10:00:00',
        end_time: '18:00:00',
      })
    })

    expect(createdData).toEqual(newWindow)
  })

  it('useBulkCreateWindows sends bulk POST request', async () => {
    const bulkWindows = [
      { id: 3, date: '2026-11-16', start_time: '10:00:00', end_time: '18:00:00' },
      { id: 4, date: '2026-11-17', start_time: '10:00:00', end_time: '18:00:00' },
    ]

    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 201,
      headers: { get: () => 'application/json' },
      json: async () => bulkWindows,
    })

    const { result } = renderHook(() => useBulkCreateWindows(), {
      wrapper: createWrapper(),
    })

    let createdList: unknown = null
    await act(async () => {
      createdList = await result.current.mutateAsync({
        dates: ['2026-11-16', '2026-11-17'],
        start_time: '10:00:00',
        end_time: '18:00:00',
      })
    })

    expect(createdList).toEqual(bulkWindows)
  })

  it('useBulkCreateWindows sends bulk POST request with multiple windows', async () => {
    const bulkWindows = [
      { id: 3, date: '2026-11-16', start_time: '10:00:00', end_time: '13:00:00' },
      { id: 4, date: '2026-11-16', start_time: '14:00:00', end_time: '18:00:00' },
    ]

    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 201,
      headers: { get: () => 'application/json' },
      json: async () => bulkWindows,
    })

    const { result } = renderHook(() => useBulkCreateWindows(), {
      wrapper: createWrapper(),
    })

    let createdList: unknown = null
    await act(async () => {
      createdList = await result.current.mutateAsync({
        dates: ['2026-11-16'],
        windows: [
          { start_time: '10:00:00', end_time: '13:00:00' },
          { start_time: '14:00:00', end_time: '18:00:00' },
        ],
      })
    })

    expect(createdList).toEqual(bulkWindows)
    expect(mockFetch).toHaveBeenCalledWith(
      '/api/work-windows/bulk',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({
          dates: ['2026-11-16'],
          windows: [
            { start_time: '10:00:00', end_time: '13:00:00' },
            { start_time: '14:00:00', end_time: '18:00:00' },
          ],
        }),
      }),
    )
  })

  it('useUpdateWindow sends PATCH request', async () => {
    const updated = { id: 5, date: '2026-11-18', start_time: '11:00:00', end_time: '19:00:00' }

    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      headers: { get: () => 'application/json' },
      json: async () => updated,
    })

    const { result } = renderHook(() => useUpdateWindow(), {
      wrapper: createWrapper(),
    })

    let res: unknown = null
    await act(async () => {
      res = await result.current.mutateAsync({
        id: 5,
        data: { start_time: '11:00:00', end_time: '19:00:00' },
      })
    })

    expect(res).toEqual(updated)
  })

  it('useDeleteWindow sends DELETE request', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 204,
      headers: { get: () => null },
      text: async () => '',
    })

    const { result } = renderHook(() => useDeleteWindow(), {
      wrapper: createWrapper(),
    })

    await act(async () => {
      await result.current.mutateAsync(5)
    })

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true)
    })
  })
})
