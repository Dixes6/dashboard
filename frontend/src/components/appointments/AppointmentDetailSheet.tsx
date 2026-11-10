import React, { useState } from 'react'
import { Pencil, Trash2, Phone, MessageCircle } from 'lucide-react'
import { BottomSheet } from '../ui/BottomSheet'
import { Button } from '../ui/Button'
import { ServicePicker } from './ServicePicker'
import { PriceField } from './PriceField'
import { ConflictConfirm } from './ConflictConfirm'
import {
  useUpdateAppointment,
  useDeleteAppointment,
  NeedsConfirmationError,
  type NeedsConfirmationDetail,
  type AppointmentUpdate,
} from '../../api/appointments'
import { useDay, type AppointmentResponse } from '../../api/home'
import { useServices } from '../../api/services'
import type { components } from '../../api/schema'
import { useToast } from '../ui'
import {
  formatMoney,
  formatPhone,
  formatDate,
  formatTime,
  formatDuration,
} from '../../lib'
import { computeTotals, computeEnd, digitsOnly } from '../../lib/appointments'

type SettingResponse = components['schemas']['SettingResponse']
type AppointmentStatus = components['schemas']['AppointmentStatus']

interface AppointmentDetailSheetProps {
  isOpen: boolean
  onClose: () => void
  appointment: AppointmentResponse | null
  settings: SettingResponse
  onUpdated?: (updated: AppointmentResponse) => void
  onDeleted?: () => void
}

const STATUSES: { id: AppointmentStatus; label: string; activeClass: string }[] = [
  {
    id: 'scheduled',
    label: 'Запланирована',
    activeClass: 'bg-primary text-surface shadow-soft border-primary',
  },
  {
    id: 'completed',
    label: 'Состоялась',
    activeClass: 'bg-success text-surface shadow-soft border-success',
  },
  {
    id: 'cancelled',
    label: 'Отменена',
    activeClass: 'bg-muted text-surface shadow-soft border-muted',
  },
  {
    id: 'no_show',
    label: 'Не пришёл',
    activeClass: 'bg-muted text-surface shadow-soft border-muted',
  },
]

// Внутренний компонент: сбрасывает все локальные состояния при переключении записи через key
const AppointmentDetailInner: React.FC<{
  appointment: AppointmentResponse
  settings: SettingResponse
  onClose: () => void
  onUpdated?: (updated: AppointmentResponse) => void
  onDeleted?: () => void
}> = ({ appointment, settings, onClose, onUpdated, onDeleted }) => {
  const { showToast } = useToast()
  const slotStepSeconds = settings.slot_step_minutes * 60

  const updateAppointment = useUpdateAppointment()
  const deleteAppointment = useDeleteAppointment()

  // Режимы редактирования
  const [isEditingDetails, setIsEditingDetails] = useState(false)
  const [isEditingPrice, setIsEditingPrice] = useState(false)
  const [editedPrice, setEditedPrice] = useState(appointment.final_price)
  const [confirmResetPrice, setConfirmResetPrice] = useState(false)
  const [confirmDelete, setConfirmDelete] = useState(false)

  // Поля формы редактирования деталей
  const [editDate, setEditDate] = useState(appointment.local_date)
  const [editTime, setEditTime] = useState(formatTime(appointment.local_start_time))
  const [editServiceIds, setEditServiceIds] = useState<number[]>(
    appointment.services.map((s) => s.service_id),
  )
  const [editNote, setEditNote] = useState(appointment.note ?? '')
  const [editErrors, setEditErrors] = useState<{ services?: string; date?: string; time?: string }>({})

  // Конфликт (409)
  const [conflictDetail, setConflictDetail] = useState<NeedsConfirmationDetail | null>(null)
  const [pendingPayload, setPendingPayload] = useState<AppointmentUpdate | null>(null)

  // Загружаем данные дня для контекста конфликтов (рабочие окна и записи)
  const { data: dayData } = useDay(isEditingDetails ? editDate : appointment.local_date)
  const currentWorkWindows = dayData?.work_windows ?? []
  const currentDayAppointments = dayData?.appointments ?? []

  const { data: allServices } = useServices({ includeArchived: true })

  // Телефон для ссылок WhatsApp и звонка
  const phoneDigits = digitsOnly(appointment.client.phone)

  // Смена статуса (1. Нажатие сразу отправляет PATCH status)
  const handleStatusChange = async (newStatus: AppointmentStatus) => {
    if (newStatus === appointment.status || updateAppointment.isPending) return
    try {
      const updated = await updateAppointment.mutateAsync({
        id: appointment.id,
        payload: { status: newStatus },
      })
      onUpdated?.(updated)
      showToast('Статус обновлён', 'success')
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Не удалось обновить статус'
      showToast(msg, 'danger')
    }
  }

  // Сохранение отредактированной вручную цены (2. PATCH final_price)
  const handleSavePrice = async () => {
    try {
      const updated = await updateAppointment.mutateAsync({
        id: appointment.id,
        payload: { final_price: editedPrice },
      })
      setIsEditingPrice(false)
      onUpdated?.(updated)
      showToast('Цена обновлена', 'success')
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Не удалось сохранить цену'
      showToast(msg, 'danger')
    }
  }

  // Сброс цены к цене по прайсу (2. PATCH reset_price: true)
  const handleResetPrice = async () => {
    try {
      const updated = await updateAppointment.mutateAsync({
        id: appointment.id,
        payload: { reset_price: true },
      })
      setConfirmResetPrice(false)
      onUpdated?.(updated)
      showToast('Цена сброшена к прайсу', 'success')
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Не удалось сбросить цену'
      showToast(msg, 'danger')
    }
  }

  // Сохранение деталей записи (3. Режим Изменить: дата, время, услуги, заметка)
  const handleSaveDetails = async (force = false) => {
    if (editServiceIds.length === 0) {
      setEditErrors({ services: 'Выберите хотя бы одну услугу' })
      return
    }
    if (!editDate) {
      setEditErrors({ date: 'Укажите дату' })
      return
    }
    if (!editTime) {
      setEditErrors({ time: 'Укажите время' })
      return
    }
    setEditErrors({})

    const payload: AppointmentUpdate = { force }

    // 1. Проверяем starts_at
    const origDate = appointment.local_date
    const origTime = formatTime(appointment.local_start_time)
    if (editDate !== origDate || editTime !== origTime) {
      const timeFormatted = editTime.length === 5 ? `${editTime}:00` : editTime
      payload.starts_at = `${editDate}T${timeFormatted}`
    }

    // 2. Проверяем service_ids
    const origServiceIds = appointment.services.map((s) => s.service_id)
    const areServicesEqual =
      origServiceIds.length === editServiceIds.length &&
      origServiceIds.every((id, idx) => id === editServiceIds[idx])
    if (!areServicesEqual) {
      payload.service_ids = editServiceIds
    }

    // 3. Проверяем заметку
    const origNote = appointment.note ?? ''
    if (editNote.trim() !== origNote) {
      payload.note = editNote.trim() ? editNote.trim() : null
    }

    // Если ничего не изменилось и это не force
    if (
      !force &&
      payload.starts_at === undefined &&
      payload.service_ids === undefined &&
      payload.note === undefined
    ) {
      setIsEditingDetails(false)
      return
    }

    try {
      const updated = await updateAppointment.mutateAsync({
        id: appointment.id,
        payload,
      })
      setIsEditingDetails(false)
      setConflictDetail(null)
      setPendingPayload(null)
      onUpdated?.(updated)
      showToast('Запись обновлена', 'success')
    } catch (err) {
      if (err instanceof NeedsConfirmationError) {
        setConflictDetail(err.detail)
        setPendingPayload(payload)
      } else {
        const msg = err instanceof Error ? err.message : 'Не удалось обновить запись'
        showToast(msg, 'danger')
      }
    }
  }

  // Принудительное сохранение при конфликте (4. force=true)
  const handleForceSave = async () => {
    if (!pendingPayload) return
    try {
      const updated = await updateAppointment.mutateAsync({
        id: appointment.id,
        payload: { ...pendingPayload, force: true },
      })
      setIsEditingDetails(false)
      setConflictDetail(null)
      setPendingPayload(null)
      onUpdated?.(updated)
      showToast('Запись сохранена', 'success')
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Не удалось сохранить запись'
      showToast(msg, 'danger')
    }
  }

  // Удаление записи (5. DELETE)
  const handleDelete = async () => {
    try {
      await deleteAppointment.mutateAsync(appointment.id)
      setConfirmDelete(false)
      onClose()
      onDeleted?.()
      showToast('Запись удалена', 'info')
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Не удалось удалить запись'
      showToast(msg, 'danger')
    }
  }

  // Расчёт времени окончания для режима редактирования
  const selectedServicesList = editServiceIds
    .map((id) => (allServices ?? []).find((s) => s.id === id))
    .filter(Boolean) as { price: number; duration_minutes: number }[]
  const editTotals = computeTotals(selectedServicesList)
  const editEndTime = editTime ? computeEnd(editDate, editTime, editTotals.minutes) : ''

  // Проверка: изменился ли набор услуг относительно оригинала при переопределённой цене
  const origServiceIds = appointment.services.map((s) => s.service_id)
  const servicesChanged =
    origServiceIds.length !== editServiceIds.length ||
    origServiceIds.some((id, idx) => id !== editServiceIds[idx])

  return (
    <div className="space-y-4 text-text font-sans pb-2">
      {conflictDetail ? (
        <ConflictConfirm
          detail={conflictDetail}
          dayAppointments={currentDayAppointments}
          workWindows={currentWorkWindows}
          onConfirm={handleForceSave}
          onCancel={() => setConflictDetail(null)}
          isLoading={updateAppointment.isPending}
        />
      ) : isEditingDetails ? (
        /* Режим редактирования деталей записи (3) */
        <div className="space-y-4">
          <div className="flex items-center justify-between pb-2 border-b border-border">
            <h3 className="font-heading font-semibold text-lg text-text">Редактирование записи</h3>
            <span className="text-xs text-muted font-medium">{appointment.client.name}</span>
          </div>

          {/* Дата и время */}
          <div className="space-y-1.5">
            <label className="text-xs text-muted font-medium">Дата и время</label>
            <div className="flex gap-2">
              <input
                type="date"
                value={editDate}
                onChange={(e) => setEditDate(e.target.value)}
                className={`flex-1 h-11 px-3 rounded-btn border bg-surface text-text text-sm focus:outline-none focus:ring-2 focus:ring-primary ${
                  editErrors.date ? 'border-danger' : 'border-border'
                }`}
              />
              <input
                type="time"
                value={editTime}
                step={slotStepSeconds}
                onChange={(e) => setEditTime(e.target.value)}
                className={`flex-1 h-11 px-3 rounded-btn border bg-surface text-text text-sm focus:outline-none focus:ring-2 focus:ring-primary ${
                  editErrors.time ? 'border-danger' : 'border-border'
                }`}
              />
            </div>
            {(editErrors.date || editErrors.time) && (
              <p className="text-xs text-danger font-medium">
                {editErrors.date || editErrors.time}
              </p>
            )}
            {editEndTime && editTotals.minutes > 0 && (
              <p className="text-xs text-muted">
                Окончание:{' '}
                <span className="font-semibold text-text">{editEndTime}</span>
                {' · '}
                {formatDuration(editTotals.minutes)}
              </p>
            )}
          </div>

          {/* Услуги */}
          <div className="space-y-2">
            <ServicePicker
              selectedIds={editServiceIds}
              onChange={setEditServiceIds}
              error={editErrors.services}
            />

            {/* Подсказка: если у записи price_overridden и меняется набор услуг */}
            {appointment.price_overridden && servicesChanged && (
              <div className="p-2.5 rounded-btn bg-primary-soft/50 border border-primary/20 text-xs text-primary-ink leading-relaxed">
                Итоговая цена останется прежней. Чтобы вернуть цену по прайсу, нажмите «Сбросить цену».
              </div>
            )}
          </div>

          {/* Заметка */}
          <div className="space-y-1">
            <label htmlFor="edit-apt-note" className="text-xs text-muted font-medium">
              Заметка
            </label>
            <textarea
              id="edit-apt-note"
              value={editNote}
              onChange={(e) => setEditNote(e.target.value)}
              rows={2}
              maxLength={2000}
              placeholder="Пожелания, особенности…"
              className="w-full px-3 py-2.5 rounded-btn border border-border bg-surface text-text text-sm resize-none focus:outline-none focus:ring-2 focus:ring-primary"
            />
          </div>

          {/* Кнопки сохранения/отмены редактирования */}
          <div className="flex gap-2 pt-2">
            <Button
              type="button"
              variant="primary"
              className="flex-1 min-h-[44px]"
              onClick={() => handleSaveDetails(false)}
              loading={updateAppointment.isPending}
            >
              Сохранить
            </Button>
            <Button
              type="button"
              variant="secondary"
              className="flex-1 min-h-[44px]"
              onClick={() => {
                setEditDate(appointment.local_date)
                setEditTime(formatTime(appointment.local_start_time))
                setEditServiceIds(appointment.services.map((s) => s.service_id))
                setEditNote(appointment.note ?? '')
                setEditErrors({})
                setIsEditingDetails(false)
              }}
              disabled={updateAppointment.isPending}
            >
              Отмена
            </Button>
          </div>
        </div>
      ) : (
        /* Режим просмотра карточки записи (1, 2, 5, 6) */
        <div className="space-y-4">
          {/* Клиент и статус */}
          <div className="flex justify-between items-start gap-2">
            <div className="flex-1 min-w-0">
              <h3 className="text-lg font-extrabold text-text font-sans truncate">
                {appointment.client.name}
              </h3>
              {appointment.client.phone && (
                <p className="text-sm text-muted">
                  {formatPhone(appointment.client.phone)}
                </p>
              )}
            </div>

            <button
              type="button"
              onClick={() => setIsEditingDetails(true)}
              className="inline-flex items-center gap-1.5 text-xs font-semibold text-primary hover:text-primary-ink px-3 py-2 rounded-btn hover:bg-primary-soft/40 transition-colors cursor-pointer min-h-[44px]"
              aria-label="Редактировать запись"
            >
              <Pencil className="w-3.5 h-3.5" />
              <span>Изменить</span>
            </button>
          </div>

          {/* 6. Быстрые действия с клиентом: WhatsApp и Позвонить */}
          {phoneDigits && (
            <div className="flex items-center gap-2">
              <a
                href={`https://wa.me/${phoneDigits}`}
                target="_blank"
                rel="noopener noreferrer"
                className="flex-1 min-h-[44px] h-11 px-3 rounded-btn border border-success/30 bg-success-soft text-success-ink text-xs sm:text-sm font-semibold flex items-center justify-center gap-1.5 hover:bg-success/20 transition-colors"
              >
                <MessageCircle className="w-4 h-4 shrink-0" />
                <span>WhatsApp</span>
              </a>

              <a
                href={`tel:+${phoneDigits}`}
                className="flex-1 min-h-[44px] h-11 px-3 rounded-btn border border-primary/30 bg-primary-soft text-primary-ink text-xs sm:text-sm font-semibold flex items-center justify-center gap-1.5 hover:bg-primary-soft/70 transition-colors"
              >
                <Phone className="w-4 h-4 shrink-0" />
                <span>Позвонить</span>
              </a>
            </div>
          )}

          {/* 1. Статус: четыре кнопки-переключателя в ряд */}
          <div className="space-y-1">
            <label className="text-xs text-muted font-medium">Статус записи</label>
            <div className="grid grid-cols-4 gap-1.5">
              {STATUSES.map((st) => {
                const isActive = appointment.status === st.id
                return (
                  <button
                    key={st.id}
                    type="button"
                    disabled={updateAppointment.isPending}
                    onClick={() => handleStatusChange(st.id)}
                    className={`min-h-[44px] h-11 py-1 px-1 rounded-btn text-[11px] sm:text-xs font-semibold leading-tight flex items-center justify-center text-center transition-all cursor-pointer border select-none ${
                      isActive
                        ? st.activeClass
                        : 'bg-bg text-muted border-border hover:border-primary/40'
                    }`}
                  >
                    {st.label}
                  </button>
                )
              })}
            </div>
            <p className="text-[11px] text-muted leading-tight mt-1">
              В доход идут только состоявшиеся записи.
            </p>
          </div>

          {/* 6. Дата и время */}
          <div className="p-3 bg-bg rounded-btn border border-border">
            <p className="text-xs text-muted font-medium mb-1">Дата и время</p>
            <p className="text-base font-bold text-text">
              {formatDate(appointment.local_date, 'd MMMM yyyy')}, {formatTime(appointment.local_start_time)}–{formatTime(appointment.local_end_time)}
            </p>
          </div>

          {/* 6. Снимки услуг */}
          <div>
            <p className="text-xs text-muted font-medium mb-2">Услуги</p>
            <ul className="divide-y divide-border border border-border rounded-btn overflow-hidden">
              {appointment.services.map((svc, idx) => (
                <li
                  key={`${svc.service_id}-${svc.position ?? idx}`}
                  className="p-3 flex justify-between items-center text-sm bg-surface"
                >
                  <div>
                    <p className="font-semibold text-text">{svc.name_snapshot}</p>
                    <p className="text-xs text-muted">{formatDuration(svc.duration_snapshot)}</p>
                  </div>
                  <span className="font-bold text-text">{formatMoney(svc.price_snapshot)}</span>
                </li>
              ))}
            </ul>
          </div>

          {/* 2. Блок цены */}
          <div className="space-y-2 pt-2 border-t border-border">
            {isEditingPrice ? (
              <div className="p-3 bg-bg rounded-btn border border-border space-y-3">
                <PriceField
                  listPrice={appointment.list_price}
                  value={editedPrice}
                  onChange={(val) => setEditedPrice(val)}
                />
                <div className="flex gap-2">
                  <Button
                    type="button"
                    variant="primary"
                    className="flex-1 min-h-[44px] text-xs"
                    onClick={handleSavePrice}
                    loading={updateAppointment.isPending}
                  >
                    Сохранить
                  </Button>
                  <Button
                    type="button"
                    variant="secondary"
                    className="flex-1 min-h-[44px] text-xs"
                    onClick={() => {
                      setEditedPrice(appointment.final_price)
                      setIsEditingPrice(false)
                    }}
                    disabled={updateAppointment.isPending}
                  >
                    Отмена
                  </Button>
                </div>
              </div>
            ) : (
              <div className="flex items-center justify-between">
                <div>
                  <span className="text-xs text-muted font-medium block">Итого к оплате</span>
                  {(appointment.price_overridden || appointment.final_price !== appointment.list_price) ? (
                    <span className="text-xs text-muted line-through block">
                      По прайсу: {formatMoney(appointment.list_price)}
                    </span>
                  ) : (
                    <span className="text-xs text-muted block">
                      По прайсу: {formatMoney(appointment.list_price)}
                    </span>
                  )}
                  <span className="text-xl font-extrabold text-text font-sans">
                    {formatMoney(appointment.final_price)}
                  </span>
                </div>

                <div className="flex items-center gap-1.5 flex-wrap justify-end">
                  <button
                    type="button"
                    onClick={() => {
                      setEditedPrice(appointment.final_price)
                      setIsEditingPrice(true)
                    }}
                    className="text-xs font-semibold text-primary hover:text-primary-ink px-3 py-2 rounded-btn hover:bg-primary-soft/40 transition-colors cursor-pointer min-h-[44px]"
                  >
                    Изменить цену
                  </button>

                  {appointment.price_overridden && (
                    <button
                      type="button"
                      onClick={() => setConfirmResetPrice(true)}
                      className="text-xs font-semibold text-muted hover:text-text px-3 py-2 rounded-btn hover:bg-border/40 transition-colors cursor-pointer min-h-[44px]"
                    >
                      Сбросить цену
                    </button>
                  )}
                </div>
              </div>
            )}

            {/* Подтверждение сброса цены (2) */}
            {confirmResetPrice && (
              <div className="p-3 bg-primary-soft/50 border border-primary/20 rounded-btn space-y-2.5">
                <p className="text-xs text-text font-medium">
                  Сбросить цену к цене по прайсу ({formatMoney(appointment.list_price)})?
                </p>
                <div className="flex gap-2">
                  <Button
                    type="button"
                    variant="primary"
                    className="flex-1 text-xs h-11 min-h-[44px]"
                    onClick={handleResetPrice}
                    loading={updateAppointment.isPending}
                  >
                    Да, сбросить
                  </Button>
                  <Button
                    type="button"
                    variant="secondary"
                    className="flex-1 text-xs h-11 min-h-[44px]"
                    onClick={() => setConfirmResetPrice(false)}
                  >
                    Отмена
                  </Button>
                </div>
              </div>
            )}
          </div>

          {/* 6. Заметка */}
          {appointment.note && (
            <div className="p-3 bg-bg rounded-btn border border-border text-xs text-muted">
              <p className="font-medium mb-1 text-text">Заметка:</p>
              <p className="whitespace-pre-wrap">{appointment.note}</p>
            </div>
          )}

          {/* 5. Удаление записи */}
          {confirmDelete ? (
            <div className="p-3.5 bg-danger/10 border border-danger/30 rounded-btn space-y-2.5">
              <p className="text-xs text-danger font-semibold">
                Запись будет убрана из календаря и статистики.
              </p>
              <div className="flex gap-2">
                <Button
                  type="button"
                  variant="danger"
                  className="flex-1 text-xs h-11 min-h-[44px]"
                  onClick={handleDelete}
                  loading={deleteAppointment.isPending}
                >
                  Да, удалить
                </Button>
                <Button
                  type="button"
                  variant="secondary"
                  className="flex-1 text-xs h-11 min-h-[44px]"
                  onClick={() => setConfirmDelete(false)}
                >
                  Отмена
                </Button>
              </div>
            </div>
          ) : (
            <div className="pt-2 flex flex-col gap-2">
              <Button
                type="button"
                variant="secondary"
                className="w-full min-h-[44px]"
                onClick={onClose}
              >
                Закрыть
              </Button>
              <button
                type="button"
                onClick={() => setConfirmDelete(true)}
                className="w-full py-2.5 text-xs font-semibold text-danger hover:text-danger/80 transition-colors cursor-pointer min-h-[44px] flex items-center justify-center gap-1.5"
              >
                <Trash2 className="w-3.5 h-3.5" />
                <span>Удалить запись</span>
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

/**
 * Обертка для BottomSheet с key для чистого сброса локальных состояний при смене записи
 */
export const AppointmentDetailSheet: React.FC<AppointmentDetailSheetProps> = ({
  isOpen,
  onClose,
  appointment,
  settings,
  onUpdated,
  onDeleted,
}) => {
  return (
    <BottomSheet
      isOpen={isOpen && !!appointment}
      onClose={onClose}
      title="Карточка записи"
      className="max-h-[92vh]"
    >
      {appointment && (
        <AppointmentDetailInner
          key={`${appointment.id}-${appointment.updated_at}`}
          appointment={appointment}
          settings={settings}
          onClose={onClose}
          onUpdated={onUpdated}
          onDeleted={onDeleted}
        />
      )}
    </BottomSheet>
  )
}
