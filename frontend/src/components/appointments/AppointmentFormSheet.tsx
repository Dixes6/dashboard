import React, { useState, useCallback } from 'react'
import { BottomSheet } from '../ui/BottomSheet'
import { ClientPicker, type SelectedClient } from './ClientPicker'
import { ServicePicker } from './ServicePicker'
import { PriceField } from './PriceField'
import { ConflictConfirm } from './ConflictConfirm'
import { useCreateAppointment, NeedsConfirmationError, type NeedsConfirmationDetail } from '../../api/appointments'
import { useDay, type AppointmentResponse } from '../../api/home'
import { useServices } from '../../api/services'
import type { components } from '../../api/schema'
import { formatDate, formatDuration } from '../../lib'
import { computeTotals, computeEnd, digitsOnly } from '../../lib/appointments'

type SettingResponse = components['schemas']['SettingResponse']

interface AppointmentFormSheetProps {
  isOpen: boolean
  onClose: () => void
  selectedDate: string
  settings: SettingResponse
  dayAppointments: AppointmentResponse[]
  onSuccess: (localDate: string) => void
}

interface ValidationErrors {
  client?: string
  clientName?: string
  services?: string
  date?: string
  time?: string
}

// Внутренний компонент: получает key и полностью сбрасывается при изменении isOpen
const AppointmentFormInner: React.FC<AppointmentFormSheetProps> = ({
  isOpen,
  onClose,
  selectedDate,
  settings,
  dayAppointments,
  onSuccess,
}) => {
  const slotStepSeconds = settings.slot_step_minutes * 60

  const [client, setClient] = useState<SelectedClient | null>(null)
  const [newClientName, setNewClientName] = useState('')
  const [selectedServiceIds, setSelectedServiceIds] = useState<number[]>([])
  const [date, setDate] = useState(selectedDate)
  const [time, setTime] = useState('10:00')
  const [finalPrice, setFinalPrice] = useState(0)
  const [priceOverridden, setPriceOverridden] = useState(false)
  const [note, setNote] = useState('')
  const [validationErrors, setValidationErrors] = useState<ValidationErrors>({})
  const [conflictDetail, setConflictDetail] = useState<NeedsConfirmationDetail | null>(null)
  const [submitError, setSubmitError] = useState<string | null>(null)

  const createAppointment = useCreateAppointment()
  const { data: services } = useServices()
  const { data: dayData } = useDay(date || selectedDate)
  const currentWorkWindows = dayData?.work_windows ?? []
  const currentDayAppointments = dayData?.appointments ?? dayAppointments

  const selectedServices = selectedServiceIds.map((id) => {
    const svc = (services ?? []).find((s) => s.id === id)
    return svc ? { price: svc.price, duration_minutes: svc.duration_minutes } : null
  }).filter(Boolean) as { price: number; duration_minutes: number }[]

  const totals = computeTotals(selectedServices)
  const endTime = time ? computeEnd(date || selectedDate, time, totals.minutes) : null

  const handlePriceChange = useCallback((val: number, isOverridden: boolean) => {
    setFinalPrice(val)
    setPriceOverridden(isOverridden)
  }, [])

  const validate = (): ValidationErrors => {
    const errors: ValidationErrors = {}
    if (!client?.id) {
      if (!client) {
        errors.client = 'Выберите клиента или введите номер телефона'
      } else {
        const phoneDigits = digitsOnly(client.phone ?? '')
        if (phoneDigits.length < 10) {
          errors.client = 'Введите номер телефона (минимум 10 цифр)'
        } else if (!newClientName.trim()) {
          errors.clientName = 'Введите имя нового клиента'
        }
      }
    }
    if (selectedServiceIds.length === 0) {
      errors.services = 'Выберите хотя бы одну услугу'
    }
    if (!date) errors.date = 'Укажите дату'
    if (!time) errors.time = 'Укажите время'
    return errors
  }

  const buildPayload = (force: boolean): Parameters<typeof createAppointment.mutateAsync>[0] => {
    const timeFormatted = time.length === 5 ? `${time}:00` : time
    const startsAt = `${date}T${timeFormatted}`

    const payload: Parameters<typeof createAppointment.mutateAsync>[0] = {
      starts_at: startsAt,
      service_ids: selectedServiceIds,
      force,
    }

    if (client?.id) {
      payload.client_id = client.id
    } else {
      payload.client = {
        name: newClientName.trim(),
        phone: digitsOnly(client?.phone ?? ''),
      }
    }

    if (priceOverridden) {
      payload.final_price = finalPrice
    }

    if (note.trim()) {
      payload.note = note.trim()
    }

    return payload
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSubmitError(null)
    setConflictDetail(null)

    const errors = validate()
    if (Object.keys(errors).length > 0) {
      setValidationErrors(errors)
      return
    }
    setValidationErrors({})

    try {
      const result = await createAppointment.mutateAsync(buildPayload(false))
      onSuccess(result.local_date)
    } catch (err) {
      if (err instanceof NeedsConfirmationError) {
        setConflictDetail(err.detail)
      } else if (err instanceof Error) {
        setSubmitError(err.message)
      } else {
        setSubmitError('Не удалось создать запись')
      }
    }
  }

  const handleForceConfirm = async () => {
    setSubmitError(null)
    try {
      const result = await createAppointment.mutateAsync(buildPayload(true))
      onSuccess(result.local_date)
    } catch (err) {
      if (err instanceof NeedsConfirmationError) {
        setConflictDetail(err.detail)
      } else if (err instanceof Error) {
        setSubmitError(err.message)
        setConflictDetail(null)
      }
    }
  }

  const isLoading = createAppointment.isPending
  const digits = digitsOnly(client?.phone ?? '')
  const isNewClient = !client?.id && digits.length >= 10
  const titleDate = formatDate(date || selectedDate, 'd MMMM')

  return (
    <BottomSheet
      isOpen={isOpen}
      onClose={onClose}
      title={`Новая запись, ${titleDate}`}
      className="max-h-[92vh]"
    >
      {conflictDetail ? (
        <ConflictConfirm
          detail={conflictDetail}
          dayAppointments={currentDayAppointments}
          workWindows={currentWorkWindows}
          onConfirm={handleForceConfirm}
          onCancel={() => setConflictDetail(null)}
          isLoading={isLoading}
        />
      ) : (
        <form onSubmit={handleSubmit} className="space-y-5 text-text font-sans pb-2">
          {/* 1. Клиент */}
          <ClientPicker
            value={client}
            onChange={setClient}
            newClientName={newClientName}
            onNewClientNameChange={setNewClientName}
            error={validationErrors.client}
            nameError={validationErrors.clientName}
          />

          {/* 2. Услуги */}
          <ServicePicker
            selectedIds={selectedServiceIds}
            onChange={setSelectedServiceIds}
            error={validationErrors.services}
          />

          {/* 3. Дата и время */}
          <div className="space-y-2">
            <label className="text-xs text-muted font-medium">Дата и время</label>
            <div className="flex gap-2">
              <input
                type="date"
                value={date}
                onChange={(e) => setDate(e.target.value)}
                className={`flex-1 h-11 px-3 rounded-btn border bg-surface text-text text-sm focus:outline-none focus:ring-2 focus:ring-primary ${
                  validationErrors.date ? 'border-danger' : 'border-border'
                }`}
              />
              <input
                type="time"
                value={time}
                step={slotStepSeconds}
                onChange={(e) => setTime(e.target.value)}
                className={`flex-1 h-11 px-3 rounded-btn border bg-surface text-text text-sm focus:outline-none focus:ring-2 focus:ring-primary ${
                  validationErrors.time ? 'border-danger' : 'border-border'
                }`}
              />
            </div>
            {(validationErrors.date || validationErrors.time) && (
              <p className="text-xs text-danger font-medium">
                {validationErrors.date || validationErrors.time}
              </p>
            )}
            {endTime && totals.minutes > 0 && (
              <p className="text-xs text-muted">
                Окончание:{' '}
                <span className="font-semibold text-text">{endTime}</span>
                {' · '}
                {formatDuration(totals.minutes)}
              </p>
            )}
          </div>

          {/* 4. Цена */}
          <PriceField
            listPrice={totals.price}
            value={finalPrice}
            onChange={handlePriceChange}
          />

          {/* 5. Заметка */}
          <div className="space-y-1">
            <label htmlFor="apt-note" className="text-xs text-muted font-medium">
              Заметка
            </label>
            <textarea
              id="apt-note"
              value={note}
              onChange={(e) => setNote(e.target.value)}
              rows={2}
              maxLength={2000}
              placeholder="Пожелания, предупреждения…"
              className="w-full px-3 py-2.5 rounded-btn border border-border bg-surface text-text text-sm resize-none focus:outline-none focus:ring-2 focus:ring-primary"
            />
          </div>

          {isNewClient && (
            <div className="p-2.5 rounded-btn bg-primary-soft/40 border border-primary/20 text-xs text-primary-ink">
              Будет создан новый клиент
              {newClientName.trim() ? ` «${newClientName.trim()}»` : ''}
            </div>
          )}

          {submitError && (
            <p className="text-xs text-danger font-medium">{submitError}</p>
          )}

          <button
            type="submit"
            disabled={isLoading}
            className="w-full h-12 min-h-[48px] bg-primary text-surface rounded-btn text-base font-semibold flex items-center justify-center transition-opacity hover:opacity-90 cursor-pointer disabled:opacity-60"
          >
            {isLoading ? 'Сохраняем…' : 'Создать запись'}
          </button>
        </form>
      )}
    </BottomSheet>
  )
}

/**
 * Обёртка: пересоздаём компонент при каждом открытии через key,
 * чтобы стейт сбрасывался без useEffect + setState.
 */
export const AppointmentFormSheet: React.FC<AppointmentFormSheetProps> = (props) => {
  return <AppointmentFormInner key={props.isOpen ? `open-${props.selectedDate}` : 'closed'} {...props} />
}
