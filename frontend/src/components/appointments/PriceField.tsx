import React, { useState } from 'react'
import { formatMoney } from '../../lib'

interface PriceFieldProps {
  listPrice: number
  value: number
  onChange: (value: number, isOverridden: boolean) => void
}

export const PriceField: React.FC<PriceFieldProps> = ({ listPrice, value, onChange }) => {
  const [prevValue, setPrevValue] = useState(value)
  const [prevListPrice, setPrevListPrice] = useState(listPrice)
  const [inputValue, setInputValue] = useState(String(value))
  const [userEdited, setUserEdited] = useState(value !== listPrice)

  // Обновляем inputValue при изменении внешнего value (паттерн adjusting state during render)
  if (value !== prevValue) {
    setPrevValue(value)
    setInputValue(String(value))
    setUserEdited(value !== listPrice)
  }

  // Обновляем цену при смене listPrice, если пользователь не менял вручную
  if (listPrice !== prevListPrice) {
    setPrevListPrice(listPrice)
    if (!userEdited) {
      setInputValue(String(listPrice))
      onChange(listPrice, false)
    }
  }

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const raw = e.target.value.replace(/\D/g, '')
    setInputValue(raw)
    setUserEdited(true)
    const num = parseInt(raw, 10)
    if (!isNaN(num) && num >= 0 && num <= 10_000_000) {
      onChange(num, num !== listPrice)
    }
  }

  const handleBlur = () => {
    const num = parseInt(inputValue, 10)
    if (isNaN(num) || num < 0) {
      setInputValue(String(listPrice))
      setUserEdited(false)
      onChange(listPrice, false)
    } else if (num > 10_000_000) {
      setInputValue('10000000')
      onChange(10_000_000, 10_000_000 !== listPrice)
    }
  }

  const isOverridden = value !== listPrice

  return (
    <div className="space-y-1.5 font-sans">
      <div className="flex items-center justify-between gap-2">
        <label htmlFor="final-price" className="text-xs text-muted font-medium">
          Итого, ₽
        </label>
        <span className={`text-xs ${isOverridden ? 'line-through text-muted' : 'text-muted'}`}>
          По прайсу: {formatMoney(listPrice)}
        </span>
      </div>
      <input
        id="final-price"
        type="text"
        inputMode="numeric"
        value={inputValue}
        onChange={handleChange}
        onBlur={handleBlur}
        placeholder={String(listPrice)}
        className="w-full h-11 px-3 rounded-btn border border-border bg-surface text-text text-sm focus:outline-none focus:ring-2 focus:ring-primary"
      />
    </div>
  )
}
