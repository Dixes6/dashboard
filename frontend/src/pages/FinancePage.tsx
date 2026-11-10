import React, { useState, useMemo } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import {
  useSettings,
  useStatsMonth,
  useStatsMonths,
  useFinanceEntries,
} from '../api'
import type { FinanceEntryResponse } from '../api'
import { Card, EmptyState, Button, BottomSheet, Spinner } from '../components/ui'
import { EntrySheet, type EntryInitialData } from '../components/finance/EntrySheet'
import {
  formatMoney,
  formatDate,
  formatMonthTitle,
  formatShortDate,
  pluralRu,
  getTodayInTimezone,
} from '../lib'

export const FinancePage: React.FC = () => {
  const location = useLocation()
  const navigate = useNavigate()

  const { data: settings, isLoading: settingsLoading, error: settingsError, refetch: refetchSettings } = useSettings()
  const timezone = settings?.timezone ?? 'UTC'
  const today = getTodayInTimezone(timezone)
  const currentMonth = today.slice(0, 7) // "YYYY-MM"

  const urlParams = useMemo(() => new URLSearchParams(location.search), [location.search])
  const queryMonth = urlParams.get('month')
  const [selectedMonth, setSelectedMonth] = useState<string>(
    queryMonth && /^\d{4}-\d{2}$/.test(queryMonth) ? queryMonth : currentMonth,
  )

  // Синхронизация месяца с URL
  React.useEffect(() => {
    const currentParams = new URLSearchParams(location.search)
    if (currentParams.get('month') !== selectedMonth) {
      navigate(`?month=${selectedMonth}`, { replace: true })
    }
  }, [selectedMonth, navigate, location.search])

  // Вкладка: Доходы или Расходы
  const [activeTab, setActiveTab] = useState<'income' | 'expense'>('income')
  const [showAllEntries, setShowAllEntries] = useState(false)

  // Запросы данных
  const {
    data: stats,
    isLoading: statsLoading,
    error: statsError,
    refetch: refetchStats,
  } = useStatsMonth(selectedMonth)

  const {
    data: entriesData,
    isLoading: entriesLoading,
    error: entriesError,
    refetch: refetchEntries,
  } = useFinanceEntries(activeTab, selectedMonth)

  const {
    data: monthsData,
    isLoading: monthsLoading,
  } = useStatsMonths()

  // Модальные окна
  const [entrySheetOpen, setEntrySheetOpen] = useState(false)
  const [editingEntry, setEditingEntry] = useState<EntryInitialData | null>(null)
  const [monthsSheetOpen, setMonthsSheetOpen] = useState(false)

  // Список записей и видимые строки (первые 8 или все)
  const entriesList: FinanceEntryResponse[] = useMemo(() => {
    return entriesData?.items ?? entriesData?.entries ?? []
  }, [entriesData])

  const displayedEntries = useMemo(() => {
    return showAllEntries ? entriesList : entriesList.slice(0, 8)
  }, [showAllEntries, entriesList])

  // Дефолтная дата для новой записи
  const defaultEntryDate = selectedMonth === currentMonth ? today : `${selectedMonth}-01`

  if (settingsLoading || (statsLoading && !stats) || (entriesLoading && !entriesData)) {
    return (
      <div className="w-full max-w-[480px] mx-auto flex-1 flex flex-col gap-4">
        <Card className="flex-1 flex items-center justify-center p-8">
          <Spinner size="lg" />
        </Card>
      </div>
    )
  }

  if (settingsError || statsError || entriesError) {
    return (
      <div className="w-full max-w-[480px] mx-auto flex-1 flex flex-col gap-4">
        <Card className="p-6 text-center flex flex-col items-center gap-3">
          <h2 className="text-lg font-heading font-semibold text-text">Ошибка загрузки</h2>
          <p className="text-sm text-muted">Не удалось получить финансовые данные за выбранный период.</p>
          <Button
            onClick={() => {
              refetchSettings()
              refetchStats()
              refetchEntries()
            }}
          >
            Повторить
          </Button>
        </Card>
      </div>
    )
  }

  const netProfitMonth = stats?.net_profit_month ?? 0
  const isNetProfitPositive = netProfitMonth >= 0

  return (
    <div className="w-full max-w-[480px] mx-auto flex flex-col gap-4 pb-20">
      {/* 1. Заголовок-блок месяца */}
      <div className="flex items-center justify-between gap-2 px-1">
        <h2 className="font-heading font-bold text-text text-[22px] leading-tight">
          {formatMonthTitle(selectedMonth)}
        </h2>
        {selectedMonth !== currentMonth ? (
          <button
            type="button"
            onClick={() => {
              setSelectedMonth(currentMonth)
              setShowAllEntries(false)
            }}
            className="text-xs font-semibold text-primary hover:text-primary-ink px-2.5 py-1.5 rounded-btn hover:bg-primary-soft/40 transition-colors cursor-pointer min-h-[44px] flex items-center justify-center"
          >
            К текущему месяцу
          </button>
        ) : null}
      </div>

      {/* 2. Переключатель из двух кнопок Доходы и Расходы + список записей */}
      <Card className="p-4 sm:p-5 flex flex-col gap-3">
        {/* Сегментированный переключатель */}
        <div className="flex p-1 bg-bg rounded-btn border border-border">
          <button
            type="button"
            onClick={() => {
              setActiveTab('income')
              setShowAllEntries(false)
            }}
            className={`flex-1 h-11 min-h-[44px] rounded-btn text-sm font-semibold transition-all cursor-pointer flex items-center justify-center ${
              activeTab === 'income'
                ? 'bg-primary text-surface shadow-soft'
                : 'text-muted hover:text-text'
            }`}
          >
            Доходы
          </button>
          <button
            type="button"
            onClick={() => {
              setActiveTab('expense')
              setShowAllEntries(false)
            }}
            className={`flex-1 h-11 min-h-[44px] rounded-btn text-sm font-semibold transition-all cursor-pointer flex items-center justify-center ${
              activeTab === 'expense'
                ? 'bg-primary text-surface shadow-soft'
                : 'text-muted hover:text-text'
            }`}
          >
            Расходы
          </button>
        </div>

        {/* Всего за месяц и кнопка Добавить */}
        <div className="flex items-center justify-between gap-2 pt-1">
          <span className="text-sm font-extrabold text-text font-sans">
            Всего за месяц: {formatMoney(entriesData?.total ?? 0)}
          </span>
          <Button
            type="button"
            variant="secondary"
            className="text-xs h-9 min-h-[44px] px-3.5 border-primary/30 text-primary hover:bg-primary-soft/40 font-semibold"
            onClick={() => {
              setEditingEntry(null)
              setEntrySheetOpen(true)
            }}
          >
            Добавить
          </Button>
        </div>

        {/* Список записей */}
        {entriesList.length === 0 ? (
          <EmptyState
            title={
              activeTab === 'income'
                ? 'Пока нет доходов за этот месяц'
                : 'Пока нет расходов за этот месяц'
            }
          />
        ) : (
          <ul className="divide-y divide-border border-t border-border mt-1">
            {displayedEntries.map((item, idx) => {
              const isVisit = item.kind === 'visit'
              return (
                <li key={`${item.kind}-${item.ref_id}-${item.date}-${idx}`}>
                  <button
                    type="button"
                    onClick={() => {
                      if (isVisit) {
                        navigate(`/?date=${item.date}`)
                      } else {
                        setEditingEntry({
                          id: item.ref_id,
                          amount: item.amount,
                          text: item.label,
                          occurredOn: String(item.date),
                        })
                        setEntrySheetOpen(true)
                      }
                    }}
                    className="w-full py-3 flex items-center justify-between text-left cursor-pointer transition-colors hover:bg-border/20 rounded-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary min-h-[44px] gap-2"
                  >
                    <div className="flex-1 min-w-0 flex flex-col pr-2">
                      <span className="text-xs text-muted leading-tight">
                        {formatShortDate(item.date)}
                      </span>
                      <div className="flex items-center gap-1.5 mt-0.5 flex-wrap">
                        <span className="text-sm font-bold text-text font-sans truncate">
                          {item.label}
                        </span>
                        {isVisit ? (
                          <span className="inline-flex items-center text-[11px] font-semibold bg-primary-soft text-primary-ink rounded-full px-2 py-0.5 leading-none">
                            Визит
                          </span>
                        ) : null}
                      </div>
                    </div>
                    <span
                      className={`text-sm font-extrabold font-sans shrink-0 ${
                        activeTab === 'income' ? 'text-success-ink' : 'text-danger'
                      }`}
                    >
                      {formatMoney(item.amount)}
                    </span>
                  </button>
                </li>
              )
            })}
          </ul>
        )}

        {/* Кнопка «Показать все (N)» */}
        {entriesList.length > 8 ? (
          <button
            type="button"
            onClick={() => setShowAllEntries((prev) => !prev)}
            className="w-full py-2.5 text-xs font-semibold text-primary hover:text-primary-ink transition-colors cursor-pointer min-h-[44px] flex items-center justify-center rounded-btn"
          >
            {showAllEntries ? 'Свернуть' : `Показать все (${entriesList.length})`}
          </button>
        ) : null}
      </Card>

      {/* 4. Блок статистики */}
      <div className="flex flex-col gap-3">
        {/* Крупная карточка «Чистая прибыль за месяц» */}
        <Card className="p-4 sm:p-5">
          <span className="text-xs text-muted font-medium block mb-1">
            Чистая прибыль за месяц
          </span>
          <span
            className={`text-[32px] font-extrabold font-sans leading-tight block ${
              isNetProfitPositive ? 'text-success-ink' : 'text-danger'
            }`}
          >
            {formatMoney(netProfitMonth)}
          </span>
        </Card>

        {/* Сетка 2 колонки */}
        <div className="grid grid-cols-2 gap-3">
          {stats?.net_profit_week !== null && stats?.net_profit_week !== undefined ? (
            <Card className="p-3.5 flex flex-col justify-between col-span-2">
              <span className="text-xs text-muted font-medium">Чистая прибыль за неделю</span>
              <span
                className={`text-xl font-bold font-sans mt-1 ${
                  stats.net_profit_week >= 0 ? 'text-success-ink' : 'text-danger'
                }`}
              >
                {formatMoney(stats.net_profit_week)}
              </span>
              <span className="text-[11px] text-muted mt-0.5">текущая неделя, пн–вс</span>
            </Card>
          ) : null}

          <Card className="p-3.5 flex flex-col justify-between">
            <span className="text-xs text-muted font-medium">Доходы за месяц</span>
            <span className="text-xl font-bold font-sans text-text mt-1">
              {formatMoney(stats?.income_total ?? 0)}
            </span>
          </Card>

          <Card className="p-3.5 flex flex-col justify-between">
            <span className="text-xs text-muted font-medium">Расходы за месяц</span>
            <span className="text-xl font-bold font-sans text-text mt-1">
              {formatMoney(stats?.expenses_total ?? 0)}
            </span>
          </Card>
        </div>

        {/* Три строки-карточки */}
        <div className="flex flex-col gap-2">
          {/* Средний доход в день */}
          <Card className="p-3.5 flex flex-col">
            <span className="text-xs text-muted font-medium">Средний доход в день</span>
            <span className="text-base font-bold text-text font-sans mt-0.5">
              {stats?.avg_income_per_day !== null && stats?.avg_income_per_day !== undefined
                ? formatMoney(stats.avg_income_per_day)
                : '—'}
            </span>
            <span className="text-[11px] text-muted mt-0.5">
              по дням, когда были визиты
            </span>
          </Card>

          {/* Популярная услуга */}
          <Card className="p-3.5 flex flex-col">
            <span className="text-xs text-muted font-medium">Популярная услуга</span>
            <span className="text-base font-bold text-text font-sans mt-0.5">
              {stats?.top_service ? (
                `${stats.top_service.name} · ${pluralRu(stats.top_service.count, 'раз', 'раза', 'раз')} · ${formatMoney(stats.top_service.revenue)}`
              ) : (
                '—'
              )}
            </span>
          </Card>

          {/* Самый прибыльный день */}
          <Card className="p-3.5 flex flex-col">
            <span className="text-xs text-muted font-medium">Самый прибыльный день</span>
            <span className="text-base font-bold text-text font-sans mt-0.5">
              {stats?.best_day ? (
                `${formatDate(stats.best_day.date, 'd MMMM')} · ${formatMoney(stats.best_day.income)}`
              ) : (
                '—'
              )}
            </span>
          </Card>
        </div>
      </div>

      {/* 5. Кнопка «Прошлые месяцы» */}
      <Button
        type="button"
        variant="secondary"
        className="w-full min-h-[44px] mt-1"
        onClick={() => setMonthsSheetOpen(true)}
      >
        Прошлые месяцы
      </Button>

      {/* 3. Форма добавления/правки доходов и расходов (EntrySheet) */}
      <EntrySheet
        isOpen={entrySheetOpen}
        onClose={() => {
          setEntrySheetOpen(false)
          setEditingEntry(null)
        }}
        type={activeTab}
        mode={editingEntry ? 'edit' : 'create'}
        initialData={editingEntry}
        defaultDate={defaultEntryDate}
      />

      {/* 5. BottomSheet: Прошлые месяцы */}
      <BottomSheet
        isOpen={monthsSheetOpen}
        onClose={() => setMonthsSheetOpen(false)}
        title="Прошлые месяцы"
      >
        {monthsLoading ? (
          <div className="flex justify-center p-6">
            <Spinner size="md" />
          </div>
        ) : (monthsData ?? []).length === 0 ? (
          <EmptyState title="Нет данных за прошлые месяцы" />
        ) : (
          <div className="space-y-2 font-sans">
            {(monthsData ?? []).map((m) => {
              const isCurrentSelected = m.month === selectedMonth
              return (
                <button
                  key={m.month}
                  type="button"
                  onClick={() => {
                    setSelectedMonth(m.month)
                    setShowAllEntries(false)
                    setMonthsSheetOpen(false)
                  }}
                  className={`w-full text-left p-3.5 rounded-card border transition-all cursor-pointer min-h-[52px] flex items-center justify-between gap-3 ${
                    isCurrentSelected
                      ? 'bg-primary-soft border-primary/50 text-text'
                      : 'bg-surface border-border hover:border-primary/30 text-text'
                  }`}
                >
                  <div className="flex flex-col">
                    <span className="font-heading font-semibold text-base text-text">
                      {formatMonthTitle(m.month)}
                    </span>
                    <span className="text-xs text-muted">
                      Доход: {formatMoney(m.income_total)} · Расход: {formatMoney(m.expenses_total)}
                    </span>
                  </div>
                  <div className="text-right shrink-0">
                    <span className="text-xs text-muted block">Прибыль</span>
                    <span
                      className={`text-sm font-bold ${
                        m.net_profit >= 0 ? 'text-success-ink' : 'text-danger'
                      }`}
                    >
                      {formatMoney(m.net_profit)}
                    </span>
                  </div>
                </button>
              )
            })}
          </div>
        )}
      </BottomSheet>
    </div>
  )
}
