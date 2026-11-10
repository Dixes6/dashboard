import React, { useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import {
  useSettings,
  useCalendar,
  useDay,
  useNextAppointment,
  useCreateIncome,
  useCreateExpense,
} from '../api'
import type { AppointmentResponse } from '../api'
import { Card, EmptyState, Button, Input, BottomSheet, Spinner, ToastProvider, useToast } from '../components/ui'
import { Calendar } from '../components/Calendar'
import {
  formatMoney,
  formatPhone,
  formatDate,
  formatTime,
  formatDuration,
  formatDayHeader,
  formatNextAppointmentHeader,
  getTodayInTimezone,
} from '../lib/format'

const MAX_AMOUNT = 100_000_000

export const HomePage: React.FC = () => {
  const location = useLocation()
  const navigate = useNavigate()
  const { showToast } = useToast()

  const { data: settings, isLoading: settingsLoading, error: settingsError } = useSettings()
  const timezone = settings?.timezone ?? 'UTC'

  const today = getTodayInTimezone(timezone)

  const urlParams = new URLSearchParams(location.search)
  const [selectedDate, setSelectedDate] = useState<string>(
    urlParams.get('date') || today,
  )

  const monthKey = selectedDate.slice(0, 7) // YYYY-MM

  const { data: calendarDays, isLoading: calendarLoading } = useCalendar(monthKey)
  const { data: day, isLoading: dayLoading, error: dayError } = useDay(selectedDate)

  const { data: nextAppointment, isLoading: nextLoading, error: nextError } = useNextAppointment()

  const createIncome = useCreateIncome()
  const createExpense = useCreateExpense()

  const [selectedAppointment, setSelectedAppointment] = useState<AppointmentResponse | null>(null)
  const [incomeSheetOpen, setIncomeSheetOpen] = useState(false)
  const [expenseSheetOpen, setExpenseSheetOpen] = useState(false)

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

  // Рабочие окна: 10:00–18:00 (тире, ЧЧ:ММ без секунд) или "Рабочее время не задано" (слово Выходной не использовать)
  const workTimeString =
    workWindows.length > 0
      ? `Рабочее время: ${workWindows.map((w) => `${formatTime(w.start_time)}–${formatTime(w.end_time)}`).join(', ')}`
      : 'Рабочее время не задано'

  const hasExpectedIncome = typeof day?.expected_income === 'number' && day.expected_income > 0

  const next = nextAppointment
  const nextTotalDuration = next?.services.reduce((sum, s) => sum + s.duration_snapshot, 0) ?? 0

  return (
    <ToastProvider>
      <div className="w-full max-w-[480px] mx-auto flex flex-col gap-4 pb-28">
        {/* 2. Карточка «Ближайшая запись» */}
        {next ? (
          <button
            type="button"
            onClick={() => setSelectedAppointment(next)}
            className="w-full text-left bg-primary-soft rounded-card p-[14px_16px] transition-opacity hover:opacity-95 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary cursor-pointer flex items-center justify-between gap-3 shadow-soft"
          >
            <div className="flex-1 min-w-0 flex flex-col">
              {/* Строка 1: 12px, жирность 600, цвет --primary-ink */}
              <span className="text-xs font-semibold text-primary-ink leading-normal truncate">
                {formatNextAppointmentHeader(next.local_date, next.local_start_time, timezone)}
              </span>
              {/* Строка 2: 18px, жирность 800, цвет --text, шрифт Manrope (не Cormorant) */}
              <span className="text-[18px] font-extrabold text-text font-sans leading-tight mt-0.5 truncate">
                {next.client.name}
              </span>
              {/* Строка 3: 14px, чуть приглушённый цвет текста */}
              <span className="text-sm text-muted leading-normal mt-0.5 truncate">
                {next.services.map((s) => s.name_snapshot).join(', ')} · {formatDuration(nextTotalDuration)}
              </span>
            </div>
            {/* Справа: итоговая цена 20px, жирность 800 */}
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

        {/* 3. Календарь (отступ карточки календаря 12px по бокам) */}
        <Card className="px-3 py-4">
          <Calendar
            month={monthKey}
            selectedDate={selectedDate}
            days={calendarDays ?? []}
            today={today}
            onDateSelect={(date) => {
              setSelectedDate(date)
            }}
          />
        </Card>

        {/* 4. Блок выбранного дня (6. Карточка дня: без фиксированной или минимальной высоты) */}
        <Card className="p-4 sm:p-5">
          <div className="flex flex-col gap-1.5 mb-3">
            {/* Верхняя строка шапки: Заголовок слева, Доход справа */}
            <div className="flex items-baseline justify-between gap-2">
              <h2 className="font-heading font-bold text-text text-[22px] leading-tight">
                {formatDayHeader(selectedDate, timezone)}
              </h2>
              <span className="text-sm font-extrabold text-text font-sans shrink-0">
                Доход: {formatMoney(day?.total_income ?? 0)}
              </span>
            </div>

            {/* Нижняя строка шапки: Рабочее время слева, Ожидается справа (только при Y > 0) */}
            <div className="flex items-baseline justify-between gap-2 text-xs text-muted">
              <span className="text-muted leading-tight">
                {workTimeString}
              </span>
              {hasExpectedIncome && (
                <span className="text-muted shrink-0 leading-tight">
                  Ожидается: {formatMoney(day.expected_income)}
                </span>
              )}
            </div>
          </div>

          {/* 5. Список записей */}
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
                        {/* Слева: время (--muted 14px), под ним имя (жирность 800, 16px), под ним услуги (13px, --muted) */}
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

                        {/* Справа колонкой, выровнено вправо: цена и компактный чип статуса */}
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

      {/* 7. Нижняя панель (ограничена по ширине 480px, по центру страницы) */}
      <footer className="fixed bottom-0 left-1/2 -translate-x-1/2 w-full max-w-[480px] border-t border-border bg-surface/95 backdrop-blur-md px-4 pt-2 pb-4 [padding-bottom:calc(1rem+env(safe-area-inset-bottom))] z-40">
        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => showToast('Форма записи будет следующим шагом')}
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

      {/* 1. Карточка записи (BottomSheet): показывает диапазон 11:00–13:00 */}
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

            {/* Диапазон времени ЧЧ:ММ–ЧЧ:ММ */}
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
    </ToastProvider>
  )
}
