import { format, parseISO, isValid, differenceInCalendarMonths } from 'date-fns'
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
  return `${isNegative ? '\u2212' : ''}${formatted}\u00A0₽`
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
 * Форматирует время в формате ЧЧ:ММ.
 * Принимает "11:00:00", "11:00" и ISO-строку/Date, возвращает "11:00".
 */
export function formatTime(date: Date | string): string {
  if (typeof date === 'string') {
    const trimmed = date.trim()
    const timeMatch = trimmed.match(/^(\d{1,2}):(\d{2})(?::\d{2})?$/)
    if (timeMatch) {
      const hours = timeMatch[1].padStart(2, '0')
      const minutes = timeMatch[2]
      return `${hours}:${minutes}`
    }
  }

  const d = toValidDate(date)
  if (!d) return ''
  return format(d, 'HH:mm', { locale: ru })
}

/**
 * Форматирует длительность в минутах в человекочитаемый вид (напр. "1 ч 30 мин", "1 ч", "45 мин")
 */
export function formatDuration(minutes: number): string {
  if (isNaN(minutes) || minutes <= 0) {
    return '0 мин'
  }
  const rounded = Math.round(minutes)
  const hours = Math.floor(rounded / 60)
  const mins = rounded % 60

  if (hours > 0 && mins > 0) {
    return `${hours} ч ${mins} мин`
  }
  if (hours > 0) {
    return `${hours} ч`
  }
  return `${mins} мин`
}

/**
 * Определяет локальную дату «сегодня» по часовому поясу из настроек.
 * Использует Intl.DateTimeFormat с переданным timeZone.
 */
export function getTodayInTimezone(timezone: string): string {
  const formatter = new Intl.DateTimeFormat('ru-RU', {
    timeZone: timezone,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  })
  const parts = formatter.formatToParts(new Date())
  const year = parts.find((p) => p.type === 'year')?.value
  const month = parts.find((p) => p.type === 'month')?.value
  const day = parts.find((p) => p.type === 'day')?.value
  return `${year}-${month}-${day}`
}

/**
 * Определяет локальную дату «завтра» по часовому поясу из настроек.
 */
export function getTomorrowInTimezone(timezone: string): string {
  const today = getTodayInTimezone(timezone)
  const d = new Date(today + 'T00:00:00')
  d.setDate(d.getDate() + 1)
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

/**
 * Форматирует заголовок дня относительно сегодня/завтра в часовом поясе из настроек.
 * Возвращает строку вида "Сегодня", "Завтра" или "d MMMM".
 */
export function formatRelativeDay(date: Date | string, timezone: string): string {
  const d = toValidDate(date)
  if (!d) return ''
  const todayStr = getTodayInTimezone(timezone)
  const tomorrowStr = getTomorrowInTimezone(timezone)
  const targetStr = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`

  if (targetStr === todayStr) return 'Сегодня'
  if (targetStr === tomorrowStr) return 'Завтра'
  return format(d, 'd MMMM', { locale: ru })
}

/**
 * Форматирует заголовок выбранного дня:
 * для сегодняшнего — "Сегодня, 10 ноября", для остальных — "12 ноября, четверг".
 */
export function formatDayHeader(date: Date | string, timezone: string): string {
  const d = toValidDate(date)
  if (!d) return ''
  const todayStr = getTodayInTimezone(timezone)
  const targetStr = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`

  if (targetStr === todayStr) {
    return `Сегодня, ${format(d, 'd MMMM', { locale: ru })}`
  }
  return `${format(d, 'd MMMM', { locale: ru })}, ${format(d, 'EEEE', { locale: ru })}`
}

/**
 * Форматирует строку ближайшей записи: "Ближайшая запись · завтра, 11:00"
 * (варианты: "сегодня, 15:00", "завтра, 11:00", "12 ноября, 11:00")
 */
export function formatNextAppointmentHeader(
  dateStr: string,
  timeStr: string,
  timezone: string,
): string {
  const time = formatTime(timeStr)
  let dayPart = ''
  if (isTodayInTimezone(dateStr, timezone)) {
    dayPart = 'сегодня'
  } else if (isTomorrowInTimezone(dateStr, timezone)) {
    dayPart = 'завтра'
  } else {
    dayPart = formatDate(dateStr, 'd MMMM')
  }
  return `Ближайшая запись · ${dayPart}, ${time}`
}

/**
 * Проверяет, попадает ли дата на «сегодня» в часовом поясе из настроек.
 */
export function isTodayInTimezone(date: Date | string, timezone: string): boolean {
  const d = toValidDate(date)
  if (!d) return false
  const targetStr = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
  return targetStr === getTodayInTimezone(timezone)
}

/**
 * Проверяет, попадает ли дата на «завтра» в часовом поясе из настроек.
 */
export function isTomorrowInTimezone(date: Date | string, timezone: string): boolean {
  const d = toValidDate(date)
  if (!d) return false
  const targetStr = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
  return targetStr === getTomorrowInTimezone(timezone)
}

/**
 * Проверяет, изменился ли месяц между двумя датами (границу месяца).
 */
export function isMonthBoundary(a: Date | string, b: Date | string): boolean {
  const da = toValidDate(a)
  const db = toValidDate(b)
  if (!da || !db) return false
  return differenceInCalendarMonths(da, db) !== 0
}

/**
 * Склонение существительных с числительными (напр. 1 раз, 2 раза, 5 раз, 11 раз, 21 раз).
 */
export function pluralRu(n: number, one: string, few: string, many: string): string {
  const abs = Math.abs(Math.round(n))
  const mod100 = abs % 100
  const mod10 = abs % 10

  let word = many
  if (mod100 < 11 || mod100 > 19) {
    if (mod10 === 1) {
      word = one
    } else if (mod10 >= 2 && mod10 <= 4) {
      word = few
    }
  }
  return `${n} ${word}`
}

/**
 * Форматирует месяц "YYYY-MM" в заголовок вида "Ноябрь 2026" (с заглавной буквы, без "г.").
 */
export function formatMonthTitle(monthStr: string): string {
  if (!monthStr || !/^\d{4}-\d{2}$/.test(monthStr)) {
    return monthStr
  }
  const [year, month] = monthStr.split('-').map(Number)
  const d = new Date(year, month - 1, 1)
  const raw = format(d, 'LLLL yyyy', { locale: ru })
  return raw.charAt(0).toUpperCase() + raw.slice(1)
}

/**
 * Краткий формат даты, напр. "10 нояб."
 */
export function formatShortDate(date: Date | string): string {
  const d = toValidDate(date)
  if (!d) return ''
  return format(d, 'd MMM', { locale: ru })
}

