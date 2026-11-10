import React from 'react'
import { useServices } from '../../api/services'
import type { ServiceResponse } from '../../api/services'
import { formatMoney, formatDuration } from '../../lib'
import { computeTotals } from '../../lib/appointments'

interface ServicePickerProps {
  selectedIds: number[]
  onChange: (ids: number[]) => void
  error?: string | null
}

export const ServicePicker: React.FC<ServicePickerProps> = ({ selectedIds, onChange, error }) => {
  const { data: services, isLoading } = useServices()

  const activeServices = (services ?? []).filter((s: ServiceResponse) => s.is_active)

  const toggle = (id: number) => {
    onChange(
      selectedIds.includes(id)
        ? selectedIds.filter((sid) => sid !== id)
        : [...selectedIds, id],
    )
  }

  const selectedServices = selectedIds.map((id) => {
    const svc = activeServices.find((s) => s.id === id)
    return svc ? { price: svc.price, duration_minutes: svc.duration_minutes } : null
  }).filter(Boolean) as { price: number; duration_minutes: number }[]

  const totals = computeTotals(selectedServices)

  if (isLoading) {
    return <div className="text-sm text-muted py-2">Загрузка услуг…</div>
  }

  return (
    <div className="space-y-2">
      <label className="text-xs text-muted font-medium">Услуги</label>

      {activeServices.length === 0 ? (
        <p className="text-sm text-muted py-2">Нет активных услуг</p>
      ) : (
        <div className="space-y-2">
          {activeServices.map((svc: ServiceResponse) => {
            const isSelected = selectedIds.includes(svc.id)
            return (
              <button
                key={svc.id}
                type="button"
                onClick={() => toggle(svc.id)}
                className={`w-full text-left p-3 rounded-btn border transition-colors cursor-pointer min-h-[52px] flex items-center justify-between gap-2 ${
                  isSelected
                    ? 'bg-primary-soft border-primary/50 text-text'
                    : 'bg-surface border-border hover:border-primary/30 hover:bg-primary-soft/20 text-text'
                }`}
              >
                <div className="flex-1 min-w-0">
                  <span className="text-sm font-semibold block truncate">{svc.name}</span>
                  <span className="text-xs text-muted">{formatDuration(svc.duration_minutes)}</span>
                </div>
                <div className="shrink-0 flex items-center gap-2">
                  <span className="text-sm font-bold text-text">{formatMoney(svc.price)}</span>
                  {isSelected && (
                    <span className="w-5 h-5 rounded-full bg-primary text-surface text-xs flex items-center justify-center font-bold leading-none">
                      ✓
                    </span>
                  )}
                </div>
              </button>
            )
          })}
        </div>
      )}

      {error && <p className="text-xs text-danger font-medium">{error}</p>}

      {selectedIds.length > 0 && (
        <div className="p-3 rounded-btn bg-bg border border-border text-sm text-text font-medium">
          Итого по прайсу:{' '}
          <span className="font-bold">{formatMoney(totals.price)}</span>
          {totals.minutes > 0 && (
            <span className="text-muted"> · {formatDuration(totals.minutes)}</span>
          )}
        </div>
      )}
    </div>
  )
}
