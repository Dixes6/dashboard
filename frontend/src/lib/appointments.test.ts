import { describe, it, expect } from 'vitest'
import { computeTotals, computeEnd, digitsOnly } from './appointments'

describe('computeTotals', () => {
  it('возвращает нули для пустого списка', () => {
    expect(computeTotals([])).toEqual({ price: 0, minutes: 0 })
  })

  it('одна услуга', () => {
    expect(computeTotals([{ price: 1500, duration_minutes: 60 }])).toEqual({
      price: 1500,
      minutes: 60,
    })
  })

  it('несколько услуг суммируются', () => {
    const services = [
      { price: 1500, duration_minutes: 60 },
      { price: 500, duration_minutes: 30 },
      { price: 1000, duration_minutes: 90 },
    ]
    expect(computeTotals(services)).toEqual({ price: 3000, minutes: 180 })
  })

  it('одинаковые услуги (дубликаты) учитываются отдельно', () => {
    const services = [
      { price: 1500, duration_minutes: 60 },
      { price: 1500, duration_minutes: 60 },
    ]
    expect(computeTotals(services)).toEqual({ price: 3000, minutes: 120 })
  })
})

describe('computeEnd', () => {
  it('нормальный случай: 11:00 + 120 мин = 13:00', () => {
    expect(computeEnd('2026-11-12', '11:00', 120)).toBe('13:00')
  })

  it('нулевая длительность', () => {
    expect(computeEnd('2026-11-12', '10:30', 0)).toBe('10:30')
  })

  it('переход через полночь: 23:00 + 90 мин = 00:30', () => {
    expect(computeEnd('2026-11-12', '23:00', 90)).toBe('00:30')
  })

  it('30 минут', () => {
    expect(computeEnd('2026-11-12', '15:30', 30)).toBe('16:00')
  })
})

describe('digitsOnly', () => {
  it('убирает все нецифровые символы', () => {
    expect(digitsOnly('+7 (912) 345-67-89')).toBe('79123456789')
  })

  it('пустая строка', () => {
    expect(digitsOnly('')).toBe('')
  })

  it('только цифры остаются как есть', () => {
    expect(digitsOnly('12345')).toBe('12345')
  })

  it('только нецифровые символы → пустая строка', () => {
    expect(digitsOnly('abc-def')).toBe('')
  })
})
