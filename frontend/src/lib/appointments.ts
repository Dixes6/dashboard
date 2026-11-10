/**
 * Чистые функции для работы с записями.
 */

export interface SelectedService {
  price: number
  duration_minutes: number
}

export interface Totals {
  price: number
  minutes: number
}

/**
 * Вычисляет суммарную цену и длительность списка выбранных услуг.
 */
export function computeTotals(services: SelectedService[]): Totals {
  return services.reduce(
    (acc, svc) => ({
      price: acc.price + svc.price,
      minutes: acc.minutes + svc.duration_minutes,
    }),
    { price: 0, minutes: 0 },
  )
}

/**
 * Вычисляет время окончания записи в формате "HH:MM".
 * @param date - дата в формате "YYYY-MM-DD"
 * @param startTime - время начала в формате "HH:MM"
 * @param totalMinutes - продолжительность в минутах
 */
export function computeEnd(date: string, startTime: string, totalMinutes: number): string {
  const [hours, minutes] = startTime.split(':').map(Number)
  const startMs = new Date(`${date}T${startTime}:00`).getTime()
  const endMs = startMs + totalMinutes * 60 * 1000
  const endDate = new Date(endMs)
  // Используем локальные часы/минуты объекта Date (он построен из локальной строки)
  const h = endDate.getHours().toString().padStart(2, '0')
  const m = endDate.getMinutes().toString().padStart(2, '0')
  // Suppress unused variable warning
  void hours
  void minutes
  return `${h}:${m}`
}

/**
 * Возвращает строку, содержащую только цифры.
 */
export function digitsOnly(str: string): string {
  return str.replace(/\D/g, '')
}
