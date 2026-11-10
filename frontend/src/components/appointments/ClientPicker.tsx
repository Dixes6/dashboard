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
  const [phoneInput, setPhoneInput] = useState(value?.phone ?? '')
  const [debouncedPhone, setDebouncedPhone] = useState('')
  const [showDropdown, setShowDropdown] = useState(false)
  const dropdownRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  // Debounce 300ms
  useEffect(() => {
    const digits = digitsOnly(phoneInput)
    const timer = setTimeout(() => {
      setDebouncedPhone(digits)
    }, 300)
    return () => clearTimeout(timer)
  }, [phoneInput])

  const digits = digitsOnly(phoneInput)
  const isFixed = !!value?.id
  const isNewClient = !isFixed && digits.length >= 10

  const isSearchEnabled = debouncedPhone.length >= 3 && !isFixed
  const { data: clientsData } = useClients(
    { phone: debouncedPhone, limit: 5 },
    { enabled: isSearchEnabled },
  )
  const suggestions = isSearchEnabled ? (clientsData?.items ?? []) : []

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

  const handlePhoneInput = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value
    setPhoneInput(val)
    setShowDropdown(true)
    // Передаём телефон наверх (без id — не зафиксированный клиент)
    onChange(val.trim() ? { phone: val } : null)
  }, [onChange])

  const handleSelectSuggestion = useCallback(
    (client: { id: number; name: string; phone: string }) => {
      onChange({ id: client.id, name: client.name, phone: client.phone })
      setPhoneInput(client.phone)
      setShowDropdown(false)
    },
    [onChange],
  )

  const handleClearClient = useCallback(() => {
    onChange(null)
    setPhoneInput('')
    setDebouncedPhone('')
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
            <span className="text-xs text-muted">{formatPhone(value.phone)}</span>
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
        <label htmlFor="client-phone" className="text-xs text-muted font-medium">
          Телефон
        </label>
        <div className="relative" ref={dropdownRef}>
          <input
            ref={inputRef}
            id="client-phone"
            type="tel"
            inputMode="tel"
            value={phoneInput}
            onChange={handlePhoneInput}
            onFocus={() => setShowDropdown(true)}
            placeholder="+7 (___) ___-__-__"
            className={`w-full h-11 px-3 rounded-btn border bg-surface text-text text-sm focus:outline-none focus:ring-2 focus:ring-primary ${
              error ? 'border-danger' : 'border-border'
            }`}
          />
          {showDropdown && suggestions.length > 0 && (
            <div className="absolute z-20 w-full mt-1 bg-surface border border-border rounded-btn shadow-soft overflow-hidden">
              {suggestions.map((client) => (
                <button
                  key={client.id}
                  type="button"
                  onClick={() => handleSelectSuggestion(client)}
                  className="w-full px-3 py-2.5 text-left text-sm hover:bg-primary-soft/50 transition-colors cursor-pointer border-b border-border last:border-0 min-h-[44px]"
                >
                  <span className="font-semibold text-text block">{client.name}</span>
                  <span className="text-xs text-muted">{formatPhone(client.phone)}</span>
                </button>
              ))}
            </div>
          )}
        </div>
        {error && <p className="text-xs text-danger font-medium">{error}</p>}
      </div>

      {/* Поле "Имя клиента" для нового клиента */}
      {isNewClient && !isFixed && (
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
          {nameError && <p className="text-xs text-danger font-medium">{nameError}</p>}
        </div>
      )}
    </div>
  )
}
