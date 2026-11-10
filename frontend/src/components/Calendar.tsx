import React from 'react'
import { ChevronLeft, ChevronRight } from 'lucide-react'
import { format } from 'date-fns'
import { ru } from 'date-fns/locale'

export interface CalendarProps {
  month: string // YYYY-MM
  selectedDate: string // YYYY-MM-DD
  days: { date: string; has_work_window: boolean; appointments_count: number; completed_income: number }[]
  today: string // YYYY-MM-DD
  onDateSelect: (date: string) => void
  onFillMonthClick?: () => void
}

export const Calendar: React.FC<CalendarProps> = ({
  month,
  selectedDate,
  days,
  today,
  onDateSelect,
  onFillMonthClick,
}) => {
  const [year, monthNum] = month.split('-').map(Number)

  const prevMonth = monthNum === 1 ? { year: year - 1, month: 12 } : { year, month: monthNum - 1 }
  const nextMonth = monthNum === 12 ? { year: year + 1, month: 1 } : { year, month: monthNum + 1 }

  const firstDay = new Date(year, monthNum - 1, 1)
  const startOffset = (firstDay.getDay() + 6) % 7 // Monday = 0
  const daysInMonth = new Date(year, monthNum, 0).getDate()

  const dayByDate = new Map<string, (typeof days)[number]>()
  days.forEach((d) => dayByDate.set(d.date, d))

  const allDates: (string | null)[] = []
  for (let i = 0; i < startOffset; i++) {
    allDates.push(null)
  }
  for (let d = 1; d <= daysInMonth; d++) {
    allDates.push(`${year}-${String(monthNum).padStart(2, '0')}-${String(d).padStart(2, '0')}`)
  }

  const rawMonth = format(firstDay, 'LLLL yyyy', { locale: ru })
  const monthTitle = rawMonth.charAt(0).toUpperCase() + rawMonth.slice(1)

  return (
    <div className="flex flex-col gap-3">
      {/* Заголовок месяца: Ноябрь 2026 (первая буква заглавная, без «г.»), Cormorant, 22px, жирный */}
      <div className="flex items-center justify-between gap-1 flex-wrap sm:flex-nowrap">
        <div className="flex items-center gap-1">
          <button
            type="button"
            onClick={() => onDateSelect(`${String(prevMonth.year).padStart(4, '0')}-${String(prevMonth.month).padStart(2, '0')}-01`)}
            className="w-10 h-10 min-w-[40px] min-h-[40px] flex items-center justify-center text-text hover:text-primary transition-colors cursor-pointer rounded-full"
            aria-label="Предыдущий месяц"
          >
            <ChevronLeft className="w-5 h-5" />
          </button>
          <h2 className="font-heading font-bold text-text text-[20px] sm:text-[22px] select-none">
            {monthTitle}
          </h2>
          <button
            type="button"
            onClick={() => onDateSelect(`${String(nextMonth.year).padStart(4, '0')}-${String(nextMonth.month).padStart(2, '0')}-01`)}
            className="w-10 h-10 min-w-[40px] min-h-[40px] flex items-center justify-center text-text hover:text-primary transition-colors cursor-pointer rounded-full"
            aria-label="Следующий месяц"
          >
            <ChevronRight className="w-5 h-5" />
          </button>
        </div>

        {onFillMonthClick && (
          <button
            type="button"
            onClick={onFillMonthClick}
            className="text-xs font-semibold text-primary-ink bg-primary-soft hover:bg-primary-soft/80 px-2.5 py-1.5 rounded-btn transition-colors cursor-pointer min-h-[36px] flex items-center gap-1 shrink-0"
          >
            Заполнить месяц
          </button>
        )}
      </div>

      {/* Названия дней недели: цвет --muted, 12px */}
      <div className="grid grid-cols-[repeat(7,minmax(0,1fr))] text-center">
        {['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс'].map((dayName) => (
          <div key={dayName} className="text-[12px] leading-normal text-muted font-normal select-none">
            {dayName}
          </div>
        ))}
      </div>

      {/* Сетка из 7 равных колонок (minmax(0, 1fr)), зазор между строками 4px */}
      <div className="grid grid-cols-[repeat(7,minmax(0,1fr))] gap-y-1">
        {allDates.map((date, index) => {
          if (!date) {
            return <div key={`empty-${index}`} className="min-h-[44px] w-full" />
          }

          const day = dayByDate.get(date)
          const isSelected = date === selectedDate
          const isCurrentToday = date === today
          const hasWorkWindow = day?.has_work_window ?? false
          const hasAppointments = (day?.appointments_count ?? 0) > 0

          let markerClasses =
            'relative z-10 w-[min(34px,calc(100%-4px))] aspect-square rounded-full flex items-center justify-center text-sm font-medium transition-colors select-none'

          if (hasAppointments) {
            // Залитый --primary с белой цифрой для дней с записями
            markerClasses += ' bg-primary text-surface border-2 border-primary'
          } else if (hasWorkWindow) {
            // Контурный круг (2px, --primary) для рабочих дней без записей
            markerClasses += ' border-2 border-primary bg-transparent text-text'
          } else {
            // Дни без меток
            markerClasses += ' text-text'
          }

          if (isCurrentToday) {
            // Золотая обводка --accent у сегодняшнего
            markerClasses += ' ring-2 ring-accent'
          }

          return (
            <button
              key={date}
              type="button"
              onClick={() => onDateSelect(date)}
              className="relative flex items-center justify-center min-h-[44px] w-full cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary rounded-full"
              aria-label={date}
              aria-pressed={isSelected}
            >
              {/* Подложка --primary-soft (диаметр 40px) под маркером выбранного дня */}
              {isSelected && (
                <span
                  className="absolute w-[min(40px,100%)] aspect-square rounded-full bg-primary-soft pointer-events-none"
                  aria-hidden="true"
                />
              )}
              <span className={markerClasses}>
                {date.split('-')[2].replace(/^0/, '')}
              </span>
            </button>
          )
        })}
      </div>
    </div>
  )
}
