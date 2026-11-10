import React from 'react'
import type { NeedsConfirmationDetail } from '../../api/appointments'
import type { AppointmentResponse, WorkWindowResponse } from '../../api'
import { formatTime } from '../../lib'

interface ConflictConfirmProps {
  detail: NeedsConfirmationDetail
  dayAppointments: AppointmentResponse[]
  workWindows?: WorkWindowResponse[]
  onConfirm: () => void
  onCancel: () => void
  isLoading?: boolean
}

export const ConflictConfirm: React.FC<ConflictConfirmProps> = ({
  detail,
  dayAppointments,
  workWindows = [],
  onConfirm,
  onCancel,
  isLoading,
}) => {
  const hasWorkWindowWarning = detail.warnings.includes('outside_work_window')
  const hasOverlapWarning =
    detail.warnings.includes('overlaps_existing') || detail.overlapping_ids.length > 0

  const isDayOff = hasWorkWindowWarning && workWindows.length === 0
  const isOutsideHours = hasWorkWindowWarning && workWindows.length > 0

  // Заголовок карточки предупреждения в зависимости от конкретных причин
  let title = 'Предупреждение'
  if (isDayOff && !hasOverlapWarning) {
    title = 'Нерабочий день'
  } else if (isOutsideHours && !hasOverlapWarning) {
    title = 'Вне рабочего времени'
  } else if (hasOverlapWarning && !hasWorkWindowWarning) {
    title = 'Пересечение записей'
  } else if (hasWorkWindowWarning && hasOverlapWarning) {
    title = 'Запись вне графика и пересечение'
  }

  const getOverlapInfo = (id: number): string => {
    const apt = dayAppointments.find((a) => a.id === id)
    if (!apt) return `Запись #${id}`
    const services = apt.services.map((s) => s.name_snapshot).join(', ')
    const timeStr = `${formatTime(apt.local_start_time)}–${formatTime(apt.local_end_time)}`
    return `${apt.client.name}, ${timeStr}${services ? ` (${services})` : ''}`
  }

  // Нестандартные предупреждения (если бэкенд вернёт что-то новое)
  const unknownWarnings = detail.warnings.filter(
    (w) => w !== 'outside_work_window' && w !== 'overlaps_existing',
  )

  return (
    <div className="space-y-4 font-sans text-text">
      <div className="p-3.5 bg-danger/10 border border-danger/30 rounded-btn space-y-3">
        <p className="text-sm font-bold text-danger leading-tight">{title}</p>

        {/* 1. Случай: нерабочий день (нет окон вообще) */}
        {isDayOff && (
          <p className="text-xs text-text leading-relaxed">
            На этот день не задано рабочее время (день отмечен как выходной).
          </p>
        )}

        {/* 2. Случай: окна есть, но время сверх них */}
        {isOutsideHours && (
          <div className="space-y-1 text-xs">
            <p className="text-text leading-relaxed">
              Время записи выходит за рамки рабочего времени мастера.
            </p>
            <p className="text-muted">
              Рабочее время дня:{' '}
              <span className="font-semibold text-text">
                {workWindows
                  .map((w) => `${formatTime(w.start_time)}–${formatTime(w.end_time)}`)
                  .join(', ')}
              </span>
            </p>
          </div>
        )}

        {/* 3. Случай: пересечение с существующими записями */}
        {hasOverlapWarning && (
          <div className="space-y-1.5 text-xs">
            <p className="text-text font-medium leading-relaxed">
              Время записи пересекается с другими записями:
            </p>
            <div className="space-y-1 pl-1">
              {detail.overlapping_ids.map((id) => (
                <div key={id} className="text-text leading-tight flex items-start gap-1.5">
                  <span className="text-danger font-bold select-none">•</span>
                  <span>{getOverlapInfo(id)}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* 4. Неизвестные предупреждения на случай расширения бэкенда */}
        {unknownWarnings.length > 0 && (
          <div className="space-y-1 text-xs text-muted">
            {unknownWarnings.map((w, i) => (
              <p key={i}>• {w}</p>
            ))}
          </div>
        )}
      </div>

      <div className="flex gap-2">
        <button
          type="button"
          onClick={onConfirm}
          disabled={isLoading}
          className="flex-1 h-11 min-h-[44px] bg-primary text-surface rounded-btn text-sm font-semibold flex items-center justify-center transition-opacity hover:opacity-90 cursor-pointer disabled:opacity-60"
        >
          {isLoading ? 'Сохраняем…' : 'Всё равно записать'}
        </button>
        <button
          type="button"
          onClick={onCancel}
          disabled={isLoading}
          className="flex-1 h-11 min-h-[44px] bg-surface border border-border text-text rounded-btn text-sm font-semibold flex items-center justify-center transition-colors hover:bg-bg cursor-pointer disabled:opacity-60"
        >
          Изменить время
        </button>
      </div>
    </div>
  )
}
