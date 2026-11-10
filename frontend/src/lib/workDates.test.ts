import { describe, it, expect } from 'vitest'
import { calculateBulkWorkDates } from './workDates'

describe('calculateBulkWorkDates', () => {
  it('filters by selected weekdays (e.g. Mon-Fri: 1, 2, 3, 4, 5)', () => {
    // Ноябрь 2026: 1 ноября — воскресенье (7), 2 ноября — понедельник (1), ..., 6 ноября — пятница (5), 7 ноября — суббота (6)
    const dates = calculateBulkWorkDates({
      year: 2026,
      month: 11,
      weekdays: [1, 2, 3, 4, 5],
      existingDates: [],
      onlyFuture: false,
      todayStr: '2026-11-01',
    })

    // В ноябре 2026 года 30 дней: 21 будний день
    expect(dates).toHaveLength(21)
    expect(dates).not.toContain('2026-11-01') // Вс
    expect(dates).toContain('2026-11-02') // Пн
    expect(dates).toContain('2026-11-06') // Пт
    expect(dates).not.toContain('2026-11-07') // Сб
    expect(dates).not.toContain('2026-11-08') // Вс
  })

  it('filters by weekend days (Sat, Sun: 6, 7)', () => {
    const dates = calculateBulkWorkDates({
      year: 2026,
      month: 11,
      weekdays: [6, 7],
      existingDates: [],
      onlyFuture: false,
      todayStr: '2026-11-01',
    })

    // В ноябре 2026 года 9 выходных дней: 1, 7, 8, 14, 15, 21, 22, 28, 29
    expect(dates).toHaveLength(9)
    expect(dates).toContain('2026-11-01')
    expect(dates).toContain('2026-11-07')
    expect(dates).not.toContain('2026-11-02')
  })

  it('skips existing dates with windows', () => {
    const dates = calculateBulkWorkDates({
      year: 2026,
      month: 11,
      weekdays: [1, 2, 3, 4, 5],
      existingDates: ['2026-11-02', '2026-11-03', '2026-11-04'],
      onlyFuture: false,
      todayStr: '2026-11-01',
    })

    expect(dates).not.toContain('2026-11-02')
    expect(dates).not.toContain('2026-11-03')
    expect(dates).not.toContain('2026-11-04')
    expect(dates).toContain('2026-11-05')
    expect(dates).toHaveLength(21 - 3)
  })

  it('works with Set for existingDates', () => {
    const existingSet = new Set(['2026-11-02', '2026-11-03'])
    const dates = calculateBulkWorkDates({
      year: 2026,
      month: 11,
      weekdays: [1, 2, 3, 4, 5],
      existingDates: existingSet,
      onlyFuture: false,
      todayStr: '2026-11-01',
    })

    expect(dates).not.toContain('2026-11-02')
    expect(dates).not.toContain('2026-11-03')
    expect(dates).toContain('2026-11-04')
  })

  it('filters only future days when onlyFuture is true', () => {
    // today is 2026-11-10 (вторник)
    const dates = calculateBulkWorkDates({
      year: 2026,
      month: 11,
      weekdays: [1, 2, 3, 4, 5],
      existingDates: [],
      onlyFuture: true,
      todayStr: '2026-11-10',
    })

    // Проверяем, что даты 1..10 ноября не попали
    expect(dates).not.toContain('2026-11-02')
    expect(dates).not.toContain('2026-11-09')
    expect(dates).not.toContain('2026-11-10') // Сегодня тоже исключается
    // А начиная с завтра (11 ноября) — попадают
    expect(dates).toContain('2026-11-11')
    expect(dates).toContain('2026-11-30')
  })

  it('includes past and today when onlyFuture is false', () => {
    const dates = calculateBulkWorkDates({
      year: 2026,
      month: 11,
      weekdays: [1, 2, 3, 4, 5],
      existingDates: [],
      onlyFuture: false,
      todayStr: '2026-11-10',
    })

    expect(dates).toContain('2026-11-02')
    expect(dates).toContain('2026-11-10')
    expect(dates).toContain('2026-11-11')
  })

  describe('handles month boundaries (28-31 days)', () => {
    it('handles 28-day month (February non-leap year 2025)', () => {
      // Февраль 2025: 28 дней
      const dates = calculateBulkWorkDates({
        year: 2025,
        month: 2,
        weekdays: [1, 2, 3, 4, 5, 6, 7], // все дни
        existingDates: [],
        onlyFuture: false,
        todayStr: '2025-02-01',
      })

      expect(dates).toHaveLength(28)
      expect(dates[0]).toBe('2025-02-01')
      expect(dates[27]).toBe('2025-02-28')
      expect(dates).not.toContain('2025-02-29')
    })

    it('handles 29-day month (February leap year 2028)', () => {
      // Февраль 2028: 29 дней
      const dates = calculateBulkWorkDates({
        year: 2028,
        month: 2,
        weekdays: [1, 2, 3, 4, 5, 6, 7],
        existingDates: [],
        onlyFuture: false,
        todayStr: '2028-02-01',
      })

      expect(dates).toHaveLength(29)
      expect(dates[0]).toBe('2028-02-01')
      expect(dates[28]).toBe('2028-02-29')
      expect(dates).not.toContain('2028-02-30')
    })

    it('handles 30-day month (November 2026)', () => {
      const dates = calculateBulkWorkDates({
        year: 2026,
        month: 11,
        weekdays: [1, 2, 3, 4, 5, 6, 7],
        existingDates: [],
        onlyFuture: false,
        todayStr: '2026-11-01',
      })

      expect(dates).toHaveLength(30)
      expect(dates[29]).toBe('2026-11-30')
      expect(dates).not.toContain('2026-11-31')
    })

    it('handles 31-day month (December 2026)', () => {
      const dates = calculateBulkWorkDates({
        year: 2026,
        month: 12,
        weekdays: [1, 2, 3, 4, 5, 6, 7],
        existingDates: [],
        onlyFuture: false,
        todayStr: '2026-12-01',
      })

      expect(dates).toHaveLength(31)
      expect(dates[30]).toBe('2026-12-31')
      expect(dates).not.toContain('2027-01-01')
    })
  })
})
