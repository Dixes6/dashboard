import React, { useState, useEffect, useRef, useCallback } from 'react'
import { useClients } from '../../api/clients'
import { digitsOnly } from '../../lib/appointments'
import { formatPhone } from '../../lib'

export interface SelectedClient {
  id?: number
  name?: string
  phone: string
}

interface ClientPickerProps {
  value: SelectedClient | null
  onChange: (client: SelectedClient | null) => void
  newClientName: string
  onNewClientNameChange: (name: string) => void
  error?: string | null
  nameError?: string | null
}

export const ClientPicker: React.FC<ClientPickerProps> = ({
  value,
  onChange,
  newClientName,
  onNewClientNameChange,
  error,
  nameError,
}) => {
  const [queryInput, setQueryInput] = useState(value?.phone ?? '')
  const [debouncedQuery, setDebouncedQuery] = useState('')
  const [showDropdown, setShowDropdown] = useState(false)
  const dropdownRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  // Debounce ~250ms
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedQuery(queryInput.trim())
    }, 250)
    return () => clearTimeout(timer)
  }, [queryInput])

  const isFixed = Boolean(value?.id)
  const debouncedTrimmed = debouncedQuery.trim()
  const isDebouncedPhone = debouncedTrimmed.startsWith('+') || /^\d/.test(debouncedTrimmed)
  const isSearchEnabled = debouncedTrimmed.length >= 2 && !isFixed

  const searchParams = isDebouncedPhone
    ? { phone: debouncedTrimmed, limit: 5 }
    : { q: debouncedTrimmed, limit: 5 }

  const { data: clientsData, isLoading } = useClients(
    searchParams,
    { enabled: isSearchEnabled },
  )
  const suggestions = isSearchEnabled ? (clientsData?.items ?? []) : []

  const digits = digitsOnly(queryInput)
  const isNewClient = !isFixed && digits.length >= 10

  // Закрытие дропдауна при клике вне
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setShowDropdown(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const handleInputChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const val = e.target.value
      setQueryInput(val)
      setShowDropdown(true)
      const trimmed = val.trim()
      if (!trimmed) {
        onChange(null)
      } else {
        const isPhoneInput = trimmed.startsWith('+') || /^\d/.test(trimmed)
        if (isPhoneInput) {
          onChange({ phone: val })
        } else {
          onChange({ phone: '', name: val })
        }
      }
    },
    [onChange],
  )

  const handleSelectSuggestion = useCallback(
    (client: { id: number; name: string; phone: string }) => {
      onChange({ id: client.id, name: client.name, phone: client.phone })
      setQueryInput(client.name)
      setShowDropdown(false)
    },
    [onChange],
  )

  const handleClearClient = useCallback(() => {
    onChange(null)
    setQueryInput('')
    setDebouncedQuery('')
    onNewClientNameChange('')
    setTimeout(() => inputRef.current?.focus(), 50)
  }, [onChange, onNewClientNameChange])

  // Если клиент выбран — показываем плашку
  if (isFixed && value) {
    return (
      <div className="space-y-1">
        <label className="text-xs text-muted font-medium">Клиент</label>
        <div className="flex items-center gap-2 p-3 bg-primary-soft rounded-btn border border-primary/30">
          <div className="flex-1 min-w-0">
            <span className="text-sm font-bold text-text block truncate">{value.name}</span>
            {value.phone ? (
              <span className="text-xs text-muted">{formatPhone(value.phone)}</span>
            ) : null}
          </div>
          <button
            type="button"
            onClick={handleClearClient}
            className="shrink-0 w-9 h-9 min-w-[36px] min-h-[36px] flex items-center justify-center text-muted hover:text-danger rounded-btn transition-colors cursor-pointer"
            aria-label="Сбросить клиента"
          >
            ✕
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-3">
      <div className="space-y-1">
        <label htmlFor="client-search" className="text-xs text-muted font-medium">
          Клиент
        </label>
        <div className="relative" ref={dropdownRef}>
          <input
            ref={inputRef}
            id="client-search"
            type="text"
            value={queryInput}
            onChange={handleInputChange}
            onFocus={() => setShowDropdown(true)}
            placeholder="Имя или телефон"
            className={`w-full h-11 px-3 rounded-btn border bg-surface text-text text-sm focus:outline-none focus:ring-2 focus:ring-primary ${
              error ? 'border-danger' : 'border-border'
            }`}
          />
          {showDropdown && suggestions.length > 0 ? (
            <div className="absolute z-20 w-full mt-1 bg-surface border border-border rounded-btn shadow-soft overflow-hidden">
              {suggestions.map((client) => (
                <button
                  key={client.id}
                  type="button"
                  onClick={() => handleSelectSuggestion(client)}
                  className="w-full px-3 py-2.5 text-left text-sm hover:bg-primary-soft/50 transition-colors cursor-pointer border-b border-border last:border-0 min-h-[44px]"
                >
                  <span className="font-semibold text-text block">{client.name}</span>
                  {client.phone ? (
                    <span className="text-xs text-muted">{formatPhone(client.phone)}</span>
                  ) : null}
                </button>
              ))}
            </div>
          ) : null}
          {showDropdown && isSearchEnabled && suggestions.length === 0 && !isLoading ? (
            <div className="absolute z-20 w-full mt-1 p-3 bg-surface border border-border rounded-btn shadow-soft text-xs text-muted">
              Клиент не найден
            </div>
          ) : null}
        </div>
        {error ? <p className="text-xs text-danger font-medium">{error}</p> : null}
      </div>

      {/* Поле "Имя клиента" для нового клиента */}
      {isNewClient && !isFixed ? (
        <div className="space-y-1">
          <label htmlFor="client-name" className="text-xs text-muted font-medium">
            Имя клиента <span className="text-primary-ink font-semibold">— новый клиент</span>
          </label>
          <input
            id="client-name"
            type="text"
            value={newClientName}
            onChange={(e) => onNewClientNameChange(e.target.value)}
            placeholder="Введите имя"
            className={`w-full h-11 px-3 rounded-btn border bg-surface text-text text-sm focus:outline-none focus:ring-2 focus:ring-primary ${
              nameError ? 'border-danger' : 'border-border'
            }`}
          />
          {nameError ? <p className="text-xs text-danger font-medium">{nameError}</p> : null}
        </div>
      ) : null}
    </div>
  )
}
