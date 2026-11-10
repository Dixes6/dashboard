import React, { useState, useId } from 'react'
import { ChevronUp, ChevronDown, Sparkles } from 'lucide-react'
import { useServices, useCreateService, useUpdateService } from '../api'
import type { ServiceResponse } from '../api'
import { ApiError } from '../api/client'
import { Button, Input, Card, Spinner, EmptyState, BottomSheet, useToast } from '../components/ui'
import { formatMoney, formatDuration } from '../lib'

const QUICK_DURATIONS = [30, 45, 60, 90, 120]

export const ServicesPage: React.FC = () => {
  const [showArchived, setShowArchived] = useState(false)
  const { data: services = [], isLoading, isError, error, refetch } = useServices({
    includeArchived: showArchived,
  })

  const createServiceMutation = useCreateService()
  const updateServiceMutation = useUpdateService()
  const { showToast } = useToast()

  // BottomSheet modal state
  const [isSheetOpen, setSheetOpen] = useState(false)
  const [editingService, setEditingService] = useState<ServiceResponse | null>(null)

  // Form states
  const [name, setName] = useState('')
  const [price, setPrice] = useState('')
  const [duration, setDuration] = useState(60)

  // Form validation errors
  const [nameError, setNameError] = useState<string | null>(null)
  const [priceError, setPriceError] = useState<string | null>(null)
  const [durationError, setDurationError] = useState<string | null>(null)
  const [generalError, setGeneralError] = useState<string | null>(null)

  // Confirm archive dialog state
  const [isConfirmingArchive, setIsConfirmingArchive] = useState(false)

  const showArchivedCheckboxId = useId()

  const activeServices = services.filter((s) => s.is_active)
  const archivedServices = services.filter((s) => !s.is_active)

  const handleOpenCreate = () => {
    setEditingService(null)
    setName('')
    setPrice('')
    setDuration(60)
    setNameError(null)
    setPriceError(null)
    setDurationError(null)
    setGeneralError(null)
    setIsConfirmingArchive(false)
    setSheetOpen(true)
  }

  const handleOpenEdit = (service: ServiceResponse) => {
    setEditingService(service)
    setName(service.name)
    setPrice(service.price.toString())
    setDuration(service.duration_minutes)
    setNameError(null)
    setPriceError(null)
    setDurationError(null)
    setGeneralError(null)
    setIsConfirmingArchive(false)
    setSheetOpen(true)
  }

  const handleCloseSheet = () => {
    setSheetOpen(false)
    setIsConfirmingArchive(false)
  }

  const validateForm = (): boolean => {
    let isValid = true
    setNameError(null)
    setPriceError(null)
    setDurationError(null)
    setGeneralError(null)

    const trimmedName = name.trim()
    if (!trimmedName) {
      setNameError('Название услуги не может быть пустым')
      isValid = false
    } else if (trimmedName.length > 200) {
      setNameError('Название не должно превышать 200 символов')
      isValid = false
    }

    const parsedPrice = parseInt(price, 10)
    if (isNaN(parsedPrice) || parsedPrice < 0 || parsedPrice > 10_000_000) {
      setPriceError('Цена должна быть от 0 до 10 000 000 ₽')
      isValid = false
    }

    if (isNaN(duration) || duration < 1 || duration > 1440) {
      setDurationError('Длительность должна быть от 1 до 1440 минут')
      isValid = false
    }

    return isValid
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!validateForm()) return

    const trimmedName = name.trim()
    const parsedPrice = parseInt(price, 10)
    const durationMinutes = Math.round(duration)

    try {
      if (editingService) {
        await updateServiceMutation.mutateAsync({
          id: editingService.id,
          payload: {
            name: trimmedName,
            price: parsedPrice,
            duration_minutes: durationMinutes,
          },
        })
        showToast('Услуга успешно обновлена', 'success')
      } else {
        const nextSortOrder = activeServices.length
        await createServiceMutation.mutateAsync({
          name: trimmedName,
          price: parsedPrice,
          duration_minutes: durationMinutes,
          sort_order: nextSortOrder,
          is_active: true,
        })
        showToast('Услуга успешно создана', 'success')
      }
      handleCloseSheet()
    } catch (err) {
      let message = 'Не удалось сохранить услугу'
      if (err instanceof ApiError) {
        message = err.detail
      }
      setGeneralError(message)
      showToast(message, 'danger')
    }
  }

  const handleArchive = async () => {
    if (!editingService) return
    try {
      await updateServiceMutation.mutateAsync({
        id: editingService.id,
        payload: { is_active: false },
      })
      showToast('Услуга перемещена в архив', 'info')
      handleCloseSheet()
    } catch (err) {
      let message = 'Не удалось архивировать услугу'
      if (err instanceof ApiError) {
        message = err.detail
      }
      showToast(message, 'danger')
    }
  }

  const handleRestore = async () => {
    if (!editingService) return
    try {
      await updateServiceMutation.mutateAsync({
        id: editingService.id,
        payload: { is_active: true },
      })
      showToast('Услуга возвращена из архива', 'success')
      handleCloseSheet()
    } catch (err) {
      let message = 'Не удалось вернуть услугу из архива'
      if (err instanceof ApiError) {
        message = err.detail
      }
      showToast(message, 'danger')
    }
  }

  const handleMove = async (index: number, direction: 'up' | 'down') => {
    const targetIndex = direction === 'up' ? index - 1 : index + 1
    if (targetIndex < 0 || targetIndex >= activeServices.length) return

    const reordered = [...activeServices]
    const [movedItem] = reordered.splice(index, 1)
    reordered.splice(targetIndex, 0, movedItem)

    // Send PATCH only for items whose index actually changed
    const updates: Promise<unknown>[] = []
    reordered.forEach((service, newIndex) => {
      if (service.sort_order !== newIndex) {
        updates.push(
          updateServiceMutation.mutateAsync({
            id: service.id,
            payload: { sort_order: newIndex },
          }),
        )
      }
    })

    try {
      await Promise.all(updates)
    } catch (err) {
      let message = 'Не удалось сохранить новый порядок услуг'
      if (err instanceof ApiError) {
        message = err.detail
      }
      showToast(message, 'danger')
    }
  }

  const isSubmitting = createServiceMutation.isPending || updateServiceMutation.isPending

  if (isLoading) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center py-16">
        <Spinner size="lg" />
        <span className="text-sm text-muted mt-3">Загрузка услуг...</span>
      </div>
    )
  }

  if (isError) {
    return (
      <div className="flex-1 flex flex-col justify-center items-center py-12">
        <Card className="w-full text-center p-6 flex flex-col items-center gap-3">
          <p className="text-danger font-medium">
            {error instanceof ApiError ? error.detail : 'Не удалось загрузить список услуг'}
          </p>
          <Button variant="secondary" onClick={() => refetch()} className="min-h-[44px]">
            Повторить
          </Button>
        </Card>
      </div>
    )
  }

  return (
    <div className="flex-1 flex flex-col gap-5 pb-6">
      {/* Header section */}
      <div className="flex items-center justify-between gap-3">
        <h2 className="text-2xl font-heading font-semibold text-text">Услуги</h2>
        <Button
          variant="primary"
          onClick={handleOpenCreate}
          className="min-h-[44px] h-11 px-3.5 sm:px-4 text-sm whitespace-nowrap"
        >
          <span>Добавить услугу</span>
        </Button>
      </div>

      {/* Active services list */}
      {activeServices.length === 0 ? (
        <EmptyState
          icon={<Sparkles className="w-10 h-10" />}
          title="Добавьте первую услугу"
          description="Услуги будут отображаться в календаре записей и в отчётах о доходах."
          action={
            <Button variant="primary" onClick={handleOpenCreate} className="min-h-[44px] mt-2">
              Добавить услугу
            </Button>
          }
        />
      ) : (
        <div className="flex flex-col gap-2.5" role="list" aria-label="Активные услуги">
          {activeServices.map((service, index) => {
            const isFirst = index === 0
            const isLast = index === activeServices.length - 1

            return (
              <div
                key={service.id}
                role="listitem"
                onClick={() => handleOpenEdit(service)}
                className="bg-surface border border-border rounded-card p-3.5 sm:p-4 shadow-soft hover:border-primary/40 transition-colors duration-150 cursor-pointer flex items-center justify-between gap-2.5 select-none"
              >
                {/* Left: Info */}
                <div className="flex-1 min-w-0 pr-2">
                  <h3 className="text-base font-semibold text-text truncate">
                    {service.name}
                  </h3>
                  <div className="text-xs text-muted mt-0.5">
                    {formatDuration(service.duration_minutes)}
                  </div>
                </div>

                {/* Right: Price & Order buttons */}
                <div className="flex items-center gap-2 sm:gap-3 shrink-0">
                  <span className="text-base sm:text-lg font-bold text-text whitespace-nowrap">
                    {formatMoney(service.price)}
                  </span>

                  <div className="flex flex-col gap-0.5 shrink-0" onClick={(e) => e.stopPropagation()}>
                    {!isFirst ? (
                      <button
                        type="button"
                        onClick={() => handleMove(index, 'up')}
                        aria-label={`Переместить ${service.name} выше`}
                        className="w-11 h-6 min-w-[44px] flex items-center justify-center text-muted hover:text-text rounded transition-colors cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
                      >
                        <ChevronUp className="w-4 h-4" />
                      </button>
                    ) : (
                      <div className="w-11 h-6 min-w-[44px]" aria-hidden="true" />
                    )}

                    {!isLast ? (
                      <button
                        type="button"
                        onClick={() => handleMove(index, 'down')}
                        aria-label={`Переместить ${service.name} ниже`}
                        className="w-11 h-6 min-w-[44px] flex items-center justify-center text-muted hover:text-text rounded transition-colors cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
                      >
                        <ChevronDown className="w-4 h-4" />
                      </button>
                    ) : (
                      <div className="w-11 h-6 min-w-[44px]" aria-hidden="true" />
                    )}
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      )}

      {/* Show archived toggle */}
      <div className="pt-2 border-t border-border mt-2">
        <label
          htmlFor={showArchivedCheckboxId}
          className="flex items-center gap-3 cursor-pointer select-none min-h-[44px] py-1 text-sm font-medium text-text"
        >
          <input
            id={showArchivedCheckboxId}
            type="checkbox"
            checked={showArchived}
            onChange={(e) => setShowArchived(e.target.checked)}
            className="w-5 h-5 rounded border-border accent-primary cursor-pointer focus-visible:ring-2 focus-visible:ring-primary"
          />
          <span>Показать архивные</span>
        </label>
      </div>

      {/* Archived services list */}
      {showArchived && (
        <div className="flex flex-col gap-2.5 mt-1">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-muted">
            Архив ({archivedServices.length})
          </h3>

          {archivedServices.length === 0 ? (
            <p className="text-xs text-muted py-2">В архиве пока нет услуг</p>
          ) : (
            <div className="flex flex-col gap-2" role="list" aria-label="Архивные услуги">
              {archivedServices.map((service) => (
                <div
                  key={service.id}
                  role="listitem"
                  onClick={() => handleOpenEdit(service)}
                  className="p-3.5 rounded-card border border-border/80 bg-surface/50 text-muted cursor-pointer hover:border-border transition-colors flex items-center justify-between gap-3 select-none"
                >
                  <div className="flex-1 min-w-0">
                    <h4 className="text-sm font-medium text-muted line-through truncate">
                      {service.name}
                    </h4>
                    <span className="text-xs text-muted/70">
                      {formatDuration(service.duration_minutes)}
                    </span>
                  </div>

                  <div className="text-right shrink-0">
                    <div className="text-sm font-medium text-muted whitespace-nowrap">
                      {formatMoney(service.price)}
                    </div>
                    <span className="text-[11px] text-accent font-medium">В архиве</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* BottomSheet for create / edit */}
      <BottomSheet
        isOpen={isSheetOpen}
        onClose={handleCloseSheet}
        title={
          editingService
            ? editingService.is_active
              ? 'Редактирование услуги'
              : 'Архивная услуга'
            : 'Новая услуга'
        }
      >
        <form onSubmit={handleSubmit} className="flex flex-col gap-4 pt-1">
          <Input
            label="Название"
            placeholder="Например, Снятие + маникюр"
            value={name}
            onChange={(e) => {
              setName(e.target.value)
              if (nameError) setNameError(null)
            }}
            error={nameError || undefined}
            maxLength={200}
            required
          />

          <Input
            label="Цена (₽)"
            type="number"
            inputMode="numeric"
            placeholder="0"
            min={0}
            max={10000000}
            step={1}
            value={price}
            onChange={(e) => {
              setPrice(e.target.value)
              if (priceError) setPriceError(null)
            }}
            error={priceError || undefined}
            required
          />

          {/* Duration section */}
          <div className="flex flex-col gap-2">
            <Input
              label="Длительность (минут)"
              type="number"
              inputMode="numeric"
              placeholder="60"
              min={1}
              max={1440}
              step={1}
              value={duration.toString()}
              onChange={(e) => {
                const val = parseInt(e.target.value, 10)
                setDuration(isNaN(val) ? 0 : val)
                if (durationError) setDurationError(null)
              }}
              error={durationError || undefined}
              required
            />

            {/* Quick duration presets */}
            <div className="flex items-center gap-1.5 flex-wrap pt-0.5">
              {QUICK_DURATIONS.map((mins) => {
                const isSelected = duration === mins
                return (
                  <button
                    key={mins}
                    type="button"
                    onClick={() => {
                      setDuration(mins)
                      if (durationError) setDurationError(null)
                    }}
                    className={`min-h-[44px] px-3 py-1.5 rounded-btn text-xs font-semibold transition-colors duration-150 cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary ${
                      isSelected
                        ? 'bg-primary text-surface shadow-soft'
                        : 'bg-primary-soft text-primary hover:bg-border/60'
                    }`}
                  >
                    {mins} мин
                  </button>
                )
              })}
            </div>
          </div>

          {generalError ? (
            <div
              role="alert"
              className="text-xs text-danger font-medium p-2.5 rounded-btn bg-danger/10 border border-danger/20 text-center"
            >
              {generalError}
            </div>
          ) : null}

          {/* Actions */}
          <div className="flex flex-col gap-2.5 mt-2">
            <Button
              type="submit"
              variant="primary"
              loading={isSubmitting}
              className="w-full"
            >
              Сохранить
            </Button>

            {/* Edit mode: Archive / Restore / Confirm */}
            {editingService && editingService.is_active && (
              <>
                {!isConfirmingArchive ? (
                  <Button
                    type="button"
                    variant="secondary"
                    onClick={() => setIsConfirmingArchive(true)}
                    className="w-full"
                  >
                    Убрать в архив
                  </Button>
                ) : (
                  <div className="p-3 rounded-btn border border-danger/30 bg-danger/5 flex flex-col gap-2.5 animate-in fade-in duration-150">
                    <p className="text-xs text-text text-center font-medium">
                      Убрать услугу «{editingService.name}» в архив?
                    </p>
                    <div className="flex items-center gap-2">
                      <Button
                        type="button"
                        variant="danger"
                        onClick={handleArchive}
                        loading={isSubmitting}
                        className="flex-1 min-h-[44px] h-11 text-sm"
                      >
                        Да, убрать
                      </Button>
                      <Button
                        type="button"
                        variant="secondary"
                        onClick={() => setIsConfirmingArchive(false)}
                        className="flex-1 min-h-[44px] h-11 text-sm"
                      >
                        Отмена
                      </Button>
                    </div>
                  </div>
                )}
              </>
            )}

            {editingService && !editingService.is_active && (
              <Button
                type="button"
                variant="secondary"
                onClick={handleRestore}
                loading={isSubmitting}
                className="w-full"
              >
                Вернуть из архива
              </Button>
            )}
          </div>
        </form>
      </BottomSheet>
    </div>
  )
}
