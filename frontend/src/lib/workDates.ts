export interface CalculateBulkWorkDatesOptions {
  year: number
  month: number // 1-12
  weekdays: number[] // 1 = Понедельник, 2 = Вторник, ..., 7 = Воскресенье
  existingDates: string[] | Set<string> // даты YYYY-MM-DD, где уже есть окна
  onlyFuture: boolean
  todayStr: string // YYYY-MM-DD
}

/**
 * Подбирает даты месяца для массового создания рабочих окон.
 *
 * @param options.year Год (например 2026)
 * @param options.month Месяц (1-12)
 * @param options.weekdays Массив дней недели (1 = Пн, 2 = Вт, ..., 7 = Вс)
 * @param options.existingDates Список или Set дат, где уже есть окна (пропускаются)
 * @param options.onlyFuture Если true — только дни строго в будущем (> todayStr)
 * @param options.todayStr Текущая дата YYYY-MM-DD по часовому поясу из настроек
 * @returns Массив подходящих дат в формате YYYY-MM-DD
 */
export function calculateBulkWorkDates(options: CalculateBulkWorkDatesOptions): string[] {
  const { year, month, weekdays, existingDates, onlyFuture, todayStr } = options

  const existingSet = existingDates instanceof Set ? existingDates : new Set(existingDates)
  const weekdaysSet = new Set(weekdays)

  // Количество дней в месяце
  const daysInMonth = new Date(year, month, 0).getDate()

  const result: string[] = []

  for (let day = 1; day <= daysInMonth; day++) {
    const dayStr = String(day).padStart(2, '0')
    const monthStr = String(month).padStart(2, '0')
    const dateStr = `${year}-${monthStr}-${dayStr}`

    // Вычисляем ISO день недели: 1 (Пн) .. 7 (Вс)
    const d = new Date(year, month - 1, day)
    const jsDay = d.getDay() // 0 = Вс, 1 = Пн .. 6 = Сб
    const isoDay = jsDay === 0 ? 7 : jsDay

    // 1. Проверяем день недели
    if (!weekdaysSet.has(isoDay)) {
      continue
    }

    // 2. Если включен режим «Только будущие дни» — пропускаем дни <= todayStr
    if (onlyFuture && dateStr <= todayStr) {
      continue
    }

    // 3. Пропускаем даты, где уже есть рабочие окна
    if (existingSet.has(dateStr)) {
      continue
    }

    result.push(dateStr)
  }

  return result
}
