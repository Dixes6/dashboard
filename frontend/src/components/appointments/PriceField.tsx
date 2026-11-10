import React, { useEffect, useState } from 'react'
import { formatMoney } from '../../lib'

interface PriceFieldProps {
  listPrice: number
  value: number
  onChange: (value: number, isOverridden: boolean) => void
}

export const PriceField: React.FC<PriceFieldProps> = ({ listPrice, value, onChange }) => {
  const [userEdited, setUserEdited] = useState(false)
  const [inputValue, setInputValue] = useState(String(value))

  // Когда list_price меняется — сбрасываем к нему, если пользователь не редактировал
  useEffect(() => {
    if (!userEdited) {
      setInputValue(String(listPrice))
      onChange(listPrice, false)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [listPrice, userEdited])

  // Синхронизируем inputValue при внешнем сбросе value
  useEffect(() => {
    if (!userEdited) {
      setInputValue(String(value))
    }
  }, [value, userEdited])

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

  const isOverridden = userEdited && value !== listPrice

  return (
    <div className="space-y-1.5">
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
