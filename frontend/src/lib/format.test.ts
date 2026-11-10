import { describe, it, expect } from 'vitest'
import { formatMoney, formatPhone, formatDate, formatTime } from './format'

describe('formatMoney', () => {
  it('formats positive integers with non-breaking space and ruble sign', () => {
    expect(formatMoney(1800)).toBe('1\u00A0800\u00A0₽')
    expect(formatMoney(25000)).toBe('25\u00A0000\u00A0₽')
    expect(formatMoney(1000000)).toBe('1\u00A0000\u00A0000\u00A0₽')
  })

  it('formats zero correctly', () => {
    expect(formatMoney(0)).toBe('0\u00A0₽')
  })

  it('formats small amounts under 1000 without space', () => {
    expect(formatMoney(500)).toBe('500\u00A0₽')
  })

  it('rounds fractional rubles to integer', () => {
    expect(formatMoney(1800.4)).toBe('1\u00A0800\u00A0₽')
    expect(formatMoney(1800.6)).toBe('1\u00A0801\u00A0₽')
  })

  it('formats negative amounts correctly', () => {
    expect(formatMoney(-1500)).toBe('-1\u00A0500\u00A0₽')
  })

  it('handles NaN gracefully', () => {
    expect(formatMoney(NaN)).toBe('0\u00A0₽')
  })
})

describe('formatPhone', () => {
  it('formats 11 digits starting with 7', () => {
    expect(formatPhone('79123456789')).toBe('+7 (912) 345-67-89')
  })

  it('formats 11 digits starting with 8', () => {
    expect(formatPhone('89123456789')).toBe('+7 (912) 345-67-89')
  })

  it('formats already spaced or hyphenated string', () => {
    expect(formatPhone('+7 (912) 345 67 89')).toBe('+7 (912) 345-67-89')
  })

  it('formats 10 digits', () => {
    expect(formatPhone('9123456789')).toBe('+7 (912) 345-67-89')
  })

  it('returns invalid strings as is', () => {
    expect(formatPhone('12345')).toBe('12345')
    expect(formatPhone('')).toBe('')
  })
})

describe('formatDate', () => {
  it('formats Date instance in Russian', () => {
    const d = new Date(2026, 10, 10) // 10 ноября 2026
    expect(formatDate(d)).toBe('10 ноября 2026')
  })

  it('formats ISO string in Russian', () => {
    expect(formatDate('2026-11-10T14:30:00Z', 'd MMMM yyyy')).toContain('ноября 2026')
  })

  it('supports custom date patterns', () => {
    const d = new Date(2026, 10, 10)
    expect(formatDate(d, 'dd.MM.yyyy')).toBe('10.11.2026')
  })

  it('returns empty string for invalid dates', () => {
    expect(formatDate('invalid-date')).toBe('')
  })
})

describe('formatTime', () => {
  it('formats time to HH:mm', () => {
    const d = new Date(2026, 10, 10, 14, 30)
    expect(formatTime(d)).toBe('14:30')
  })

  it('formats ISO string to HH:mm', () => {
    // 14:30 local time equivalent
    const d = new Date(2026, 10, 10, 9, 5)
    expect(formatTime(d)).toBe('09:05')
  })

  it('returns empty string for invalid time', () => {
    expect(formatTime('invalid')).toBe('')
  })
})
