import React, { useState, useMemo } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { Pencil, Trash2 } from 'lucide-react'
import {
  useSettings,
  useCalendar,
  useDay,
  useNextAppointment,
  useCreateIncome,
  useCreateExpense,
  useCreateWindow,
  useUpdateWindow,
  useDeleteWindow,
  useBulkCreateWindows,
  ApiError,
} from '../api'
import type { AppointmentResponse, WorkWindowResponse } from '../api'
import { Card, EmptyState, Button, Input, BottomSheet, Spinner, ToastProvider, useToast } from '../components/ui'
import { Calendar } from '../components/Calendar'
import { AppointmentFormSheet } from '../components/appointments/AppointmentFormSheet'
import {
  formatMoney,
  formatPhone,
  formatDate,
  formatTime,
  formatDuration,
  formatDayHeader,
  formatNextAppointmentHeader,
  getTodayInTimezone,
  calculateBulkWorkDates,
} from '../lib'

const MAX_AMOUNT = 100_000_000
const WORK_WINDOW_STORAGE_KEY = 'last_work_window_time'

interface EditableWindow {
  id?: number
  start_time: string
  end_time: string
}

function getLastUsedWorkWindow(): { start_time: string; end_time: string } {
  try {
    const raw = localStorage.getItem(WORK_WINDOW_STORAGE_KEY)
    if (raw) {
      const parsed = JSON.parse(raw)
      if (typeof parsed?.start_time === 'string' && typeof parsed?.end_time === 'string') {
        return { start_time: parsed.start_time, end_time: parsed.end_time }
      }
    }
  } catch {
    // ignore localStorage error
  }
  return { start_time: '10:00', end_time: '18:00' }
}

function saveLastUsedWorkWindow(start_time: string, end_time: string): void {
  try {
    localStorage.setItem(WORK_WINDOW_STORAGE_KEY, JSON.stringify({ start_time, end_time }))
  } catch {
    // ignore localStorage error
  }
}

const WEEKDAYS = [
  { id: 1, label: 'Пн' },
  { id: 2, label: 'Вт' },
  { id: 3, label: 'Ср' },
  { id: 4, label: 'Чт' },
  { id: 5, label: 'Пт' },
  { id: 6, label: 'Сб' },
  { id: 7, label: 'Вс' },
]

export const HomePage: React.FC = () => {
  const location = useLocation()
  const navigate = useNavigate()
  const { showToast } = useToast()

  const { data: settings, isLoading: settingsLoading, error: settingsError } = useSettings()
  const timezone = settings?.timezone ?? 'UTC'
  const slotStepMinutes = settings?.slot_step_minutes ?? 15
  const slotStepSeconds = slotStepMinutes * 60

  const today = getTodayInTimezone(timezone)

  const urlParams = new URLSearchParams(location.search)
  const [selectedDate, setSelectedDate] = useState<string>(
    urlParams.get('date') || today,
  )

  const monthKey = selectedDate.slice(0, 7) // YYYY-MM
  const [currentYear, currentMonthNum] = monthKey.split('-').map(Number)

  const { data: calendarDays, isLoading: calendarLoading } = useCalendar(monthKey)
  const { data: day, isLoading: dayLoading, error: dayError } = useDay(selectedDate)

  const { data: nextAppointment, isLoading: nextLoading, error: nextError } = useNextAppointment()

  const createIncome = useCreateIncome()
  const createExpense = useCreateExpense()

  const createWindow = useCreateWindow()
  const updateWindow = useUpdateWindow()
  const deleteWindow = useDeleteWindow()
  const bulkCreateWindows = useBulkCreateWindows()

  const [selectedAppointment, setSelectedAppointment] = useState<AppointmentResponse | null>(null)
  const [incomeSheetOpen, setIncomeSheetOpen] = useState(false)
  const [expenseSheetOpen, setExpenseSheetOpen] = useState(false)
  const [appointmentSheetOpen, setAppointmentSheetOpen] = useState(false)

  // Управление окнами выбранного дня
  const [workWindowsSheetOpen, setWorkWindowsSheetOpen] = useState(false)
  const [dayWindows, setDayWindows] = useState<EditableWindow[]>([])
  const [initialDayWindows, setInitialDayWindows] = useState<WorkWindowResponse[]>([])
  const [workWindowsError, setWorkWindowsError] = useState<string | null>(null)
  const [confirmDayOff, setConfirmDayOff] = useState(false)

  // Заполнить месяц
  const [bulkSheetOpen, setBulkSheetOpen] = useState(false)
  const [bulkWeekdays, setBulkWeekdays] = useState<number[]>([1, 2, 3, 4, 5])
  const [bulkStartTime, setBulkStartTime] = useState('10:00')
  const [bulkEndTime, setBulkEndTime] = useState('18:00')
  const [bulkOnlyFuture, setBulkOnlyFuture] = useState(true)
  const [bulkError, setBulkError] = useState<string | null>(null)

  const [incomeForm, setIncomeForm] = useState<{
    amount: string
    source: string
    occurredOn: string
  }>({ amount: '', source: '', occurredOn: today })

  const [expenseForm, setExpenseForm] = useState<{
    amount: string
    description: string
    occurredOn: string
  }>({ amount: '', description: '', occurredOn: today })

  const [incomeError, setIncomeError] = useState<string | null>(null)
  const [expenseError, setExpenseError] = useState<string | null>(null)

  // Sync selected date with URL
  React.useEffect(() => {
    const currentParams = new URLSearchParams(location.search)
    if (currentParams.get('date') !== selectedDate) {
      navigate(`?date=${selectedDate}`, { replace: true })
    }
  }, [selectedDate, navigate, location.search])

  const handleIncomeSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    setIncomeError(null)
    const amount = Number(incomeForm.amount)
    if (!amount || amount < 1 || amount > MAX_AMOUNT) {
      setIncomeError('Сумма должна быть от 1 до 100 000 000 рублей')
      return
    }
    if (!incomeForm.source.trim()) {
      setIncomeError('Укажите источник дохода')
      return
    }
    createIncome.mutate(
      {
        amount,
        source: incomeForm.source.trim(),
        occurred_on: incomeForm.occurredOn,
      },
      {
        onSuccess: () => {
          setIncomeSheetOpen(false)
          resetIncomeForm()
          showToast('Доход добавлен', 'success')
        },
      },
    )
  }

  const handleExpenseSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    setExpenseError(null)
    const amount = Number(expenseForm.amount)
    if (!amount || amount < 1 || amount > MAX_AMOUNT) {
      setExpenseError('Сумма должна быть от 1 до 100 000 000 рублей')
      return
    }
    if (!expenseForm.description.trim()) {
      setExpenseError('Укажите, что куплено')
      return
    }
    createExpense.mutate(
      {
        amount,
        description: expenseForm.description.trim(),
        occurred_on: expenseForm.occurredOn,
      },
      {
        onSuccess: () => {
          setExpenseSheetOpen(false)
          resetExpenseForm()
          showToast('Расход добавлен', 'success')
        },
      },
    )
  }

  const resetIncomeForm = () => {
    setIncomeForm({ amount: '', source: '', occurredOn: today })
    setIncomeError(null)
  }

  const resetExpenseForm = () => {
    setExpenseForm({ amount: '', description: '', occurredOn: today })
    setExpenseError(null)
  }

  const statusLabels: Record<string, string> = {
    scheduled: 'Запланирована',
    completed: 'Состоялась',
    cancelled: 'Отменена',
    no_show: 'Не пришёл',
  }

  // Открытие BottomSheet рабочего времени выбранного дня
  const handleOpenWorkWindowsSheet = () => {
    const current = day?.work_windows ?? []
    setInitialDayWindows(current)
    setDayWindows(
      current.map((w) => ({
        id: w.id,
        start_time: formatTime(w.start_time),
        end_time: formatTime(w.end_time),
      })),
    )
    setWorkWindowsError(null)
    setConfirmDayOff(false)
    setWorkWindowsSheetOpen(true)
  }

  const handleAddDayWindow = () => {
    const lastUsed = getLastUsedWorkWindow()
    setDayWindows((prev) => [
      ...prev,
      {
        start_time: lastUsed.start_time,
        end_time: lastUsed.end_time,
      },
    ])
    setWorkWindowsError(null)
  }

  const handleRemoveDayWindow = (index: number) => {
    setDayWindows((prev) => prev.filter((_, idx) => idx !== index))
    setWorkWindowsError(null)
  }

  const handleDayWindowChange = (index: number, field: 'start_time' | 'end_time', value: string) => {
    setDayWindows((prev) =>
      prev.map((w, idx) => (idx === index ? { ...w, [field]: value } : w)),
    )
    setWorkWindowsError(null)
  }

  const validateDayWindows = (windows: EditableWindow[]): string | null => {
    for (let i = 0; i < windows.length; i++) {
      const w = windows[i]
      if (!w.start_time || !w.end_time) {
        return 'Заполните время начала и окончания'
      }
      if (w.end_time <= w.start_time) {
        return 'Конец рабочего окна должен быть позже начала'
      }
    }

    for (let i = 0; i < windows.length; i++) {
      for (let j = i + 1; j < windows.length; j++) {
        const a = windows[i]
        const b = windows[j]
        // Два полуинтервала [s1, e1) и [s2, e2) пересекаются, если s1 < e2 && s2 < e1
        if (a.start_time < b.end_time && b.start_time < a.end_time) {
          return 'Рабочие окна одного дня не должны пересекаться'
        }
      }
    }

    return null
  }

  const handleSaveDayWindows = async () => {
    setWorkWindowsError(null)
    const validationError = validateDayWindows(dayWindows)
    if (validationError) {
      setWorkWindowsError(validationError)
      return
    }

    try {
      // 1. Удаляем окна, отсутствующие в новом списке
      const currentIds = new Set(dayWindows.map((w) => w.id).filter(Boolean))
      const toDelete = initialDayWindows.filter((w) => !currentIds.has(w.id))
      for (const w of toDelete) {
        await deleteWindow.mutateAsync(w.id)
      }

      // 2. Добавляем новые окна (без id)
      const toCreate = dayWindows.filter((w) => !w.id)
      for (const w of toCreate) {
        await createWindow.mutateAsync({
          date: selectedDate,
          start_time: w.start_time.length === 5 ? `${w.start_time}:00` : w.start_time,
          end_time: w.end_time.length === 5 ? `${w.end_time}:00` : w.end_time,
        })
      }

      // 3. Изменяем существующие окна
      const toUpdate = dayWindows.filter((w) => {
        if (!w.id) return false
        const orig = initialDayWindows.find((init) => init.id === w.id)
        if (!orig) return false
        return (
          formatTime(orig.start_time) !== w.start_time ||
          formatTime(orig.end_time) !== w.end_time
        )
      })
      for (const w of toUpdate) {
        await updateWindow.mutateAsync({
          id: w.id!,
          data: {
            start_time: w.start_time.length === 5 ? `${w.start_time}:00` : w.start_time,
            end_time: w.end_time.length === 5 ? `${w.end_time}:00` : w.end_time,
          },
        })
      }

      if (dayWindows.length > 0) {
        const last = dayWindows[dayWindows.length - 1]
        saveLastUsedWorkWindow(last.start_time, last.end_time)
      }

      showToast('Рабочее время сохранено', 'success')
      setWorkWindowsSheetOpen(false)
    } catch (err: unknown) {
      let msg = 'Не удалось сохранить рабочее время'
      if (err instanceof ApiError) {
        msg = err.detail
      } else if (err instanceof Error) {
        msg = err.message
      }
      setWorkWindowsError(msg)
    }
  }

  const handleMakeDayOff = async () => {
    setWorkWindowsError(null)
    try {
      for (const w of initialDayWindows) {
        await deleteWindow.mutateAsync(w.id)
      }
      showToast('Рабочее время удалено', 'info')
      setConfirmDayOff(false)
      setWorkWindowsSheetOpen(false)
    } catch (err: unknown) {
      let msg = 'Не удалось удалить рабочее время'
      if (err instanceof ApiError) {
        msg = err.detail
      } else if (err instanceof Error) {
        msg = err.message
      }
      setWorkWindowsError(msg)
    }
  }

  // Открытие BottomSheet «Заполнить месяц»
  const handleOpenBulkSheet = () => {
    const lastUsed = getLastUsedWorkWindow()
    setBulkStartTime(lastUsed.start_time)
    setBulkEndTime(lastUsed.end_time)
    setBulkWeekdays([1, 2, 3, 4, 5])
    setBulkOnlyFuture(true)
    setBulkError(null)
    setBulkSheetOpen(true)
  }

  const toggleBulkWeekday = (dayId: number) => {
    setBulkWeekdays((prev) =>
      prev.includes(dayId) ? prev.filter((d) => d !== dayId) : [...prev, dayId].sort(),
    )
  }

  const existingWindowDates = useMemo(() => {
    return (calendarDays ?? []).filter((d) => d.has_work_window).map((d) => d.date)
  }, [calendarDays])

  const targetBulkDates = useMemo(() => {
    return calculateBulkWorkDates({
      year: currentYear,
      month: currentMonthNum,
      weekdays: bulkWeekdays,
      existingDates: existingWindowDates,
      onlyFuture: bulkOnlyFuture,
      todayStr: today,
    })
  }, [currentYear, currentMonthNum, bulkWeekdays, existingWindowDates, bulkOnlyFuture, today])

  const handleBulkSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setBulkError(null)

    if (targetBulkDates.length === 0) {
      return
    }

    if (!bulkStartTime || !bulkEndTime) {
      setBulkError('Укажите время начала и окончания')
      return
    }

    if (bulkEndTime <= bulkStartTime) {
      setBulkError('Время окончания должно быть позже времени начала')
      return
    }

    try {
      await bulkCreateWindows.mutateAsync({
        dates: targetBulkDates,
        start_time: bulkStartTime.length === 5 ? `${bulkStartTime}:00` : bulkStartTime,
        end_time: bulkEndTime.length === 5 ? `${bulkEndTime}:00` : bulkEndTime,
      })

      saveLastUsedWorkWindow(bulkStartTime, bulkEndTime)
      showToast(`Рабочие окна добавлены: ${targetBulkDates.length} дн.`, 'success')
      setBulkSheetOpen(false)
    } catch (err: unknown) {
      let msg = 'Не удалось заполнить месяц'
      if (err instanceof ApiError) {
        msg = err.detail
      } else if (err instanceof Error) {
        msg = err.message
      }
      setBulkError(msg)
    }
  }

  if (settingsLoading || calendarLoading || dayLoading || nextLoading) {
    return (
      <div className="w-full max-w-[480px] mx-auto flex-1 flex flex-col gap-4">
        <Card className="flex-1 flex items-center justify-center p-6">
          <Spinner size="lg" />
        </Card>
      </div>
    )
  }

  if (settingsError || dayError || nextError) {
    return (
      <div className="w-full max-w-[480px] mx-auto flex-1 flex flex-col gap-4">
        <Card className="p-6">
          <h2 className="text-lg font-heading font-semibold text-text mb-2">Ошибка загрузки</h2>
          <Button onClick={() => window.location.reload()}>Повторить</Button>
        </Card>
      </div>
    )
  }

  const appointments = day?.appointments ?? []
  const workWindows = day?.work_windows ?? []

  const workTimeString =
    workWindows.length > 0
      ? `Рабочее время: ${workWindows.map((w) => `${formatTime(w.start_time)}–${formatTime(w.end_time)}`).join(', ')}`
      : 'Рабочее время не задано'

  const hasExpectedIncome = typeof day?.expected_income === 'number' && day.expected_income > 0

  const next = nextAppointment
  const nextTotalDuration = next?.services.reduce((sum, s) => sum + s.duration_snapshot, 0) ?? 0

  const isSavingDayWindows =
    createWindow.isPending || updateWindow.isPending || deleteWindow.isPending

  return (
    <ToastProvider>
      <div className="w-full max-w-[480px] mx-auto flex flex-col gap-4 pb-28">
        {/* Карточка «Ближайшая запись» */}
        {next ? (
          <button
            type="button"
            onClick={() => setSelectedAppointment(next)}
            className="w-full text-left bg-primary-soft rounded-card p-[14px_16px] transition-opacity hover:opacity-95 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary cursor-pointer flex items-center justify-between gap-3 shadow-soft"
          >
            <div className="flex-1 min-w-0 flex flex-col">
              <span className="text-xs font-semibold text-primary-ink leading-normal truncate">
                {formatNextAppointmentHeader(next.local_date, next.local_start_time, timezone)}
              </span>
              <span className="text-[18px] font-extrabold text-text font-sans leading-tight mt-0.5 truncate">
                {next.client.name}
              </span>
              <span className="text-sm text-muted leading-normal mt-0.5 truncate">
                {next.services.map((s) => s.name_snapshot).join(', ')} · {formatDuration(nextTotalDuration)}
              </span>
            </div>
            <div className="shrink-0 text-right">
              <span className="text-[20px] font-extrabold text-text font-sans">
                {formatMoney(next.final_price)}
              </span>
            </div>
          </button>
        ) : (
          <div className="w-full bg-primary-soft rounded-card p-[14px_16px]">
            <span className="text-xs font-semibold text-primary-ink">
              Ближайших записей нет
            </span>
          </div>
        )}

        {/* Календарь с кнопкой «Заполнить месяц» */}
        <Card className="px-3 py-4">
          <Calendar
            month={monthKey}
            selectedDate={selectedDate}
            days={calendarDays ?? []}
            today={today}
            onDateSelect={(date) => {
              setSelectedDate(date)
            }}
            onFillMonthClick={handleOpenBulkSheet}
          />
        </Card>

        {/* Блок выбранного дня */}
        <Card className="p-4 sm:p-5">
          <div className="flex flex-col gap-1.5 mb-3">
            <div className="flex items-baseline justify-between gap-2">
              <h2 className="font-heading font-bold text-text text-[22px] leading-tight">
                {formatDayHeader(selectedDate, timezone)}
              </h2>
              <span className="text-sm font-extrabold text-text font-sans shrink-0">
                Доход: {formatMoney(day?.total_income ?? 0)}
              </span>
            </div>

            {/* Нижняя строка шапки: Рабочее время и кнопка «Изменить» */}
            <div className="flex items-center justify-between gap-2 text-xs text-muted flex-wrap">
              <div className="flex items-center gap-1.5 flex-wrap">
                <span className="text-muted leading-tight">
                  {workTimeString}
                </span>
                <button
                  type="button"
                  onClick={handleOpenWorkWindowsSheet}
                  className="inline-flex items-center gap-1 text-xs font-semibold text-primary hover:text-primary-ink px-2 py-1 rounded-btn hover:bg-primary-soft/40 transition-colors cursor-pointer min-h-[32px]"
                  aria-label="Изменить рабочее время"
                >
                  <Pencil className="w-3.5 h-3.5" />
                  <span>Изменить</span>
                </button>
              </div>

              {hasExpectedIncome && (
                <span className="text-muted shrink-0 leading-tight">
                  Ожидается: {formatMoney(day.expected_income)}
                </span>
              )}
            </div>
          </div>

          {/* Список записей */}
          <div>
            {appointments.length === 0 ? (
              <EmptyState title="На этот день записей нет" />
            ) : (
              <ul className="divide-y divide-border border-t border-border mt-1">
                {appointments.map((apt) => {
                  const isCancelledOrNoShow = apt.status === 'cancelled' || apt.status === 'no_show'
                  const label = statusLabels[apt.status]

                  let statusChipClasses =
                    'inline-flex items-center text-xs font-semibold rounded-[8px] py-[3px] px-2 leading-none'
                  if (apt.status === 'scheduled') {
                    statusChipClasses += ' bg-primary-soft text-primary-ink'
                  } else if (apt.status === 'completed') {
                    statusChipClasses += ' bg-success-soft text-success-ink'
                  } else {
                    statusChipClasses += ' bg-border text-muted'
                  }

                  return (
                    <li key={apt.id}>
                      <button
                        type="button"
                        onClick={() => setSelectedAppointment(apt)}
                        className="w-full py-3 flex items-start justify-between text-left cursor-pointer transition-colors hover:bg-border/20 rounded-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary min-h-[44px]"
                      >
                        <div className="flex-1 min-w-0 flex flex-col pr-2">
                          <span className="text-sm text-muted leading-tight">
                            {formatTime(apt.local_start_time)}
                          </span>
                          <span className="text-base font-extrabold text-text font-sans leading-tight mt-0.5 truncate">
                            {apt.client.name}
                          </span>
                          <span className="text-[13px] text-muted leading-tight mt-0.5 truncate">
                            {apt.services.map((s) => s.name_snapshot).join(', ')}
                          </span>
                        </div>

                        <div className="flex flex-col items-end gap-1.5 shrink-0 min-w-fit">
                          <div className="flex items-baseline justify-end gap-1.5">
                            {apt.price_overridden && (
                              <span className="text-[13px] text-muted line-through font-normal">
                                {formatMoney(apt.list_price)}
                              </span>
                            )}
                            <span
                              className={`text-base font-extrabold font-sans ${isCancelledOrNoShow ? 'text-muted' : 'text-text'}`}
                            >
                              {formatMoney(apt.final_price)}
                            </span>
                          </div>
                          <span className={statusChipClasses}>
                            {label}
                          </span>
                        </div>
                      </button>
                    </li>
                  )
                })}
              </ul>
            )}
          </div>
        </Card>
      </div>

      {/* Нижняя панель */}
      <footer className="fixed bottom-0 left-1/2 -translate-x-1/2 w-full max-w-[480px] border-t border-border bg-surface/95 backdrop-blur-md px-4 pt-2 pb-4 [padding-bottom:calc(1rem+env(safe-area-inset-bottom))] z-40">
        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => setAppointmentSheetOpen(true)}
            className="flex-1 bg-primary text-surface h-12 min-h-[48px] rounded-btn font-medium text-base flex items-center justify-center gap-2 shadow-soft hover:opacity-95 transition-opacity cursor-pointer"
          >
            <span className="text-lg leading-none">+</span>
            Запись
          </button>
          <button
            type="button"
            onClick={() => setIncomeSheetOpen(true)}
            className="flex-1 bg-surface border-[1.5px] border-primary text-primary-ink font-bold h-12 min-h-[48px] rounded-btn text-base flex items-center justify-center gap-2 hover:bg-primary-soft/30 transition-colors cursor-pointer"
          >
            <span className="text-lg leading-none">+</span>
            Доход
          </button>
          <button
            type="button"
            onClick={() => setExpenseSheetOpen(true)}
            className="flex-1 bg-surface border-[1.5px] border-primary text-primary-ink font-bold h-12 min-h-[48px] rounded-btn text-base flex items-center justify-center gap-2 hover:bg-primary-soft/30 transition-colors cursor-pointer"
          >
            <span className="text-lg leading-none">+</span>
            Расход
          </button>
        </div>
      </footer>

      {/* 2. BottomSheet: Рабочее время выбранного дня */}
      <BottomSheet
        isOpen={workWindowsSheetOpen}
        onClose={() => setWorkWindowsSheetOpen(false)}
        title={`Рабочее время, ${formatDate(selectedDate, 'd MMMM')}`}
      >
        <div className="space-y-4 text-text font-sans">
          {appointments.length > 0 && (
            <div className="p-3 rounded-btn bg-primary-soft/50 border border-primary/20 text-xs text-primary-ink">
              На этот день уже есть записи ({appointments.length}), они останутся.
            </div>
          )}

          {dayWindows.length === 0 ? (
            <p className="text-sm text-muted py-2 text-center">
              Рабочих окон нет (день свободный)
            </p>
          ) : (
            <div className="space-y-3">
              {dayWindows.map((w, idx) => (
                <div key={idx} className="flex items-center gap-2">
                  <input
                    type="time"
                    step={slotStepSeconds}
                    value={w.start_time}
                    onChange={(e) => handleDayWindowChange(idx, 'start_time', e.target.value)}
                    className="flex-1 h-11 px-3 rounded-btn border border-border bg-surface text-text text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                  />
                  <span className="text-xs text-muted font-medium select-none">до</span>
                  <input
                    type="time"
                    step={slotStepSeconds}
                    value={w.end_time}
                    onChange={(e) => handleDayWindowChange(idx, 'end_time', e.target.value)}
                    className="flex-1 h-11 px-3 rounded-btn border border-border bg-surface text-text text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                  />
                  <button
                    type="button"
                    onClick={() => handleRemoveDayWindow(idx)}
                    className="w-11 h-11 min-w-[44px] min-h-[44px] flex items-center justify-center text-muted hover:text-danger rounded-btn transition-colors cursor-pointer"
                    aria-label="Удалить окно"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              ))}
            </div>
          )}

          <button
            type="button"
            onClick={handleAddDayWindow}
            className="w-full py-2.5 px-3 border border-dashed border-primary/60 text-primary-ink hover:bg-primary-soft/40 rounded-btn text-sm font-semibold flex items-center justify-center gap-1.5 transition-colors cursor-pointer min-h-[44px]"
          >
            + Добавить окно
          </button>

          {workWindowsError && (
            <p className="text-xs text-danger font-medium">{workWindowsError}</p>
          )}

          {confirmDayOff ? (
            <div className="p-3 bg-danger/10 border border-danger/30 rounded-btn space-y-2.5">
              <p className="text-xs text-danger font-semibold">
                {appointments.length > 0
                  ? `На этот день уже есть записи (${appointments.length}), они останутся. Удалить все рабочие окна дня?`
                  : 'Удалить все рабочие окна этого дня?'}
              </p>
              <div className="flex gap-2">
                <Button
                  type="button"
                  variant="danger"
                  className="flex-1 text-xs h-10 min-h-[40px]"
                  onClick={handleMakeDayOff}
                  loading={deleteWindow.isPending}
                >
                  Да, сделать выходным
                </Button>
                <Button
                  type="button"
                  variant="secondary"
                  className="flex-1 text-xs h-10 min-h-[40px]"
                  onClick={() => setConfirmDayOff(false)}
                >
                  Отмена
                </Button>
              </div>
            </div>
          ) : (
            <div className="flex gap-2 pt-2">
              <Button
                type="button"
                variant="primary"
                className="flex-1"
                onClick={handleSaveDayWindows}
                loading={isSavingDayWindows}
              >
                Сохранить
              </Button>
              <Button
                type="button"
                variant="secondary"
                className="border-danger/30 text-danger hover:bg-danger/10"
                onClick={() => setConfirmDayOff(true)}
              >
                Сделать выходным
              </Button>
            </div>
          )}
        </div>
      </BottomSheet>

      {/* 3. BottomSheet: Заполнить месяц */}
      <BottomSheet
        isOpen={bulkSheetOpen}
        onClose={() => setBulkSheetOpen(false)}
        title="Заполнить месяц"
      >
        <form onSubmit={handleBulkSubmit} className="space-y-4 text-text font-sans">
          {/* Семь кнопок-переключателей Пн–Вс */}
          <div>
            <p className="text-xs text-muted font-medium mb-2">Дни недели</p>
            <div className="flex gap-1">
              {WEEKDAYS.map((wd) => {
                const isSelected = bulkWeekdays.includes(wd.id)
                return (
                  <button
                    key={wd.id}
                    type="button"
                    onClick={() => toggleBulkWeekday(wd.id)}
                    className={`flex-1 h-10 min-h-[40px] rounded-btn font-semibold text-xs transition-colors cursor-pointer select-none ${
                      isSelected
                        ? 'bg-primary text-surface shadow-soft'
                        : 'bg-bg text-muted border border-border hover:border-primary/50'
                    }`}
                  >
                    {wd.label}
                  </button>
                )
              })}
            </div>
          </div>

          {/* Время с ... до ... */}
          <div>
            <p className="text-xs text-muted font-medium mb-2">Рабочие часы</p>
            <div className="flex items-center gap-2">
              <input
                type="time"
                step={slotStepSeconds}
                value={bulkStartTime}
                onChange={(e) => setBulkStartTime(e.target.value)}
                className="flex-1 h-11 px-3 rounded-btn border border-border bg-surface text-text text-sm focus:outline-none focus:ring-2 focus:ring-primary"
              />
              <span className="text-xs text-muted font-medium select-none">до</span>
              <input
                type="time"
                step={slotStepSeconds}
                value={bulkEndTime}
                onChange={(e) => setBulkEndTime(e.target.value)}
                className="flex-1 h-11 px-3 rounded-btn border border-border bg-surface text-text text-sm focus:outline-none focus:ring-2 focus:ring-primary"
              />
            </div>
          </div>

          {/* Переключатель «Только будущие дни» */}
          <label className="flex items-center justify-between p-3 rounded-btn bg-bg border border-border cursor-pointer select-none">
            <div>
              <span className="text-sm font-medium text-text block">Только будущие дни</span>
              <span className="text-xs text-muted">Не затронет прошедшие дни и сегодня</span>
            </div>
            <input
              type="checkbox"
              checked={bulkOnlyFuture}
              onChange={(e) => setBulkOnlyFuture(e.target.checked)}
              className="w-5 h-5 accent-primary rounded cursor-pointer"
            />
          </label>

          {/* Итог: Будет добавлено: N дн. */}
          <div className="p-3 rounded-btn bg-primary-soft/50 border border-primary/20 flex items-center justify-between">
            <span className="text-sm text-primary-ink font-semibold">
              Будет добавлено: {targetBulkDates.length} дн.
            </span>
          </div>

          {bulkError && <p className="text-xs text-danger font-medium">{bulkError}</p>}

          <Button
            type="submit"
            variant="primary"
            className="w-full"
            disabled={targetBulkDates.length === 0 || bulkCreateWindows.isPending}
            loading={bulkCreateWindows.isPending}
          >
            {targetBulkDates.length === 0 ? 'Нечего добавлять' : 'Добавить'}
          </Button>
        </form>
      </BottomSheet>

      {/* Карточка записи (BottomSheet) */}
      <BottomSheet
        isOpen={!!selectedAppointment}
        onClose={() => setSelectedAppointment(null)}
        title="Карточка записи"
      >
        {selectedAppointment && (
          <div className="space-y-4 text-text font-sans">
            <div className="flex justify-between items-start gap-2">
              <div>
                <h3 className="text-lg font-extrabold text-text font-sans">
                  {selectedAppointment.client.name}
                </h3>
                {selectedAppointment.client.phone && (
                  <p className="text-sm text-muted">
                    {formatPhone(selectedAppointment.client.phone)}
                  </p>
                )}
              </div>
              <span
                className={`inline-flex items-center text-xs font-semibold rounded-[8px] py-[3px] px-2 leading-none ${
                  selectedAppointment.status === 'scheduled'
                    ? 'bg-primary-soft text-primary-ink'
                    : selectedAppointment.status === 'completed'
                      ? 'bg-success-soft text-success-ink'
                      : 'bg-border text-muted'
                }`}
              >
                {statusLabels[selectedAppointment.status]}
              </span>
            </div>

            <div className="p-3 bg-bg rounded-btn border border-border">
              <p className="text-xs text-muted font-medium mb-1">Дата и время</p>
              <p className="text-base font-bold text-text">
                {formatDate(selectedAppointment.local_date, 'd MMMM yyyy')}, {formatTime(selectedAppointment.local_start_time)}–{formatTime(selectedAppointment.local_end_time)}
              </p>
            </div>

            <div>
              <p className="text-xs text-muted font-medium mb-2">Услуги</p>
              <ul className="divide-y divide-border border border-border rounded-btn overflow-hidden">
                {selectedAppointment.services.map((svc, idx) => (
                  <li key={`${svc.service_id}-${svc.position ?? idx}`} className="p-3 flex justify-between items-center text-sm bg-surface">
                    <div>
                      <p className="font-semibold text-text">{svc.name_snapshot}</p>
                      <p className="text-xs text-muted">{formatDuration(svc.duration_snapshot)}</p>
                    </div>
                    <span className="font-bold text-text">{formatMoney(svc.price_snapshot)}</span>
                  </li>
                ))}
              </ul>
            </div>

            <div className="flex justify-between items-center pt-2 border-t border-border">
              <div>
                <span className="text-sm text-muted">Итого</span>
                {selectedAppointment.price_overridden && (
                  <span className="text-xs text-muted line-through block">
                    По прайсу: {formatMoney(selectedAppointment.list_price)}
                  </span>
                )}
              </div>
              <span className="text-xl font-extrabold text-text">
                {formatMoney(selectedAppointment.final_price)}
              </span>
            </div>

            {selectedAppointment.note && (
              <div className="p-3 bg-bg rounded-btn border border-border text-xs text-muted">
                <p className="font-medium mb-1 text-text">Заметка:</p>
                <p>{selectedAppointment.note}</p>
              </div>
            )}

            <Button
              variant="secondary"
              className="w-full"
              onClick={() => setSelectedAppointment(null)}
            >
              Закрыть
            </Button>
          </div>
        )}
      </BottomSheet>

      {/* BottomSheet: Доход */}
      <BottomSheet
        isOpen={incomeSheetOpen}
        onClose={() => setIncomeSheetOpen(false)}
        title="Доход"
      >
        <form onSubmit={handleIncomeSubmit} className="space-y-4">
          <Input
            label="Сумма (₽)"
            value={incomeForm.amount}
            onChange={(e) => setIncomeForm({ ...incomeForm, amount: e.target.value })}
            error={incomeError}
            inputMode="numeric"
          />
          <Input
            label="Источник"
            value={incomeForm.source}
            onChange={(e) => setIncomeForm({ ...incomeForm, source: e.target.value })}
          />
          <Input
            label="Дата"
            value={incomeForm.occurredOn}
            onChange={(e) => setIncomeForm({ ...incomeForm, occurredOn: e.target.value })}
            type="date"
          />
          <Button type="submit" variant="primary" loading={createIncome.isPending}>
            Сохранить
          </Button>
        </form>
      </BottomSheet>

      {/* BottomSheet: Расход */}
      <BottomSheet
        isOpen={expenseSheetOpen}
        onClose={() => setExpenseSheetOpen(false)}
        title="Расход"
      >
        <form onSubmit={handleExpenseSubmit} className="space-y-4">
          <Input
            label="Сумма (₽)"
            value={expenseForm.amount}
            onChange={(e) => setExpenseForm({ ...expenseForm, amount: e.target.value })}
            error={expenseError}
            inputMode="numeric"
          />
          <Input
            label="Что куплено"
            value={expenseForm.description}
            onChange={(e) => setExpenseForm({ ...expenseForm, description: e.target.value })}
          />
          <Input
            label="Дата"
            value={expenseForm.occurredOn}
            onChange={(e) => setExpenseForm({ ...expenseForm, occurredOn: e.target.value })}
            type="date"
          />
          <Button type="submit" variant="primary" loading={createExpense.isPending}>
            Сохранить
          </Button>
        </form>
      </BottomSheet>
      {/* BottomSheet: Форма создания записи */}
      {settings && (
        <AppointmentFormSheet
          isOpen={appointmentSheetOpen}
          onClose={() => setAppointmentSheetOpen(false)}
          selectedDate={selectedDate}
          settings={settings}
          dayAppointments={appointments}
          onSuccess={(localDate) => {
            setAppointmentSheetOpen(false)
            setSelectedDate(localDate)
            showToast('Запись добавлена', 'success')
          }}
        />
      )}
    </ToastProvider>
  )
}
