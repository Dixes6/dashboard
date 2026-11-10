import { format, parseISO, isValid } from 'date-fns'
import { ru } from 'date-fns/locale'

/**
 * Форматирует сумму в целых рублях с неразрывным пробелом (напр. 1 800 ₽)
 */
export function formatMoney(amount: number): string {
  if (isNaN(amount)) {
    return '0\u00A0₽'
  }
  const rounded = Math.round(amount)
  const isNegative = rounded < 0
  const absStr = Math.abs(rounded).toString()
  const formatted = absStr.replace(/\B(?=(\d{3})+(?!\d))/g, '\u00A0')
  return `${isNegative ? '-' : ''}${formatted}\u00A0₽`
}

/**
 * Форматирует номер телефона в формат +7 (XXX) XXX-XX-XX
 */
export function formatPhone(phone: string): string {
  if (!phone) return ''
  const digits = phone.replace(/\D/g, '')

  if (digits.length === 11 && (digits.startsWith('7') || digits.startsWith('8'))) {
    const local = digits.slice(1)
    return `+7 (${local.slice(0, 3)}) ${local.slice(3, 6)}-${local.slice(6, 8)}-${local.slice(8, 10)}`
  }

  if (digits.length === 10) {
    return `+7 (${digits.slice(0, 3)}) ${digits.slice(3, 6)}-${digits.slice(6, 8)}-${digits.slice(8, 10)}`
  }

  return phone
}

function toValidDate(date: Date | string): Date | null {
  if (date instanceof Date) {
    return isValid(date) ? date : null
  }
  if (typeof date === 'string') {
    const parsed = parseISO(date)
    if (isValid(parsed)) return parsed
    const fromConstructor = new Date(date)
    if (isValid(fromConstructor)) return fromConstructor
  }
  return null
}

/**
 * Форматирует дату на русском языке (по умолчанию "d MMMM yyyy")
 */
export function formatDate(date: Date | string, pattern = 'd MMMM yyyy'): string {
  const d = toValidDate(date)
  if (!d) return ''
  return format(d, pattern, { locale: ru })
}

/**
 * Форматирует время в формате ЧЧ:ММ
 */
export function formatTime(date: Date | string): string {
  const d = toValidDate(date)
  if (!d) return ''
  return format(d, 'HH:mm', { locale: ru })
}
