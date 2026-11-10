import React, { useState } from 'react'
import { Trash2 } from 'lucide-react'
import { BottomSheet } from '../ui/BottomSheet'
import { Button } from '../ui/Button'
import { Input } from '../ui/Input'
import { useToast } from '../ui'
import {
  useCreateIncome,
  useCreateExpense,
  useUpdateIncome,
  useUpdateExpense,
  useDeleteIncome,
  useDeleteExpense,
} from '../../api'

const MAX_AMOUNT = 100_000_000

export interface EntryInitialData {
  id: number
  amount: number
  text: string // source for income, description for expense
  occurredOn: string
}

export interface EntrySheetProps {
  isOpen: boolean
  onClose: () => void
  type: 'income' | 'expense'
  mode?: 'create' | 'edit'
  initialData?: EntryInitialData | null
  defaultDate?: string
  onSuccess?: () => void
}

const EntrySheetInner: React.FC<{
  type: 'income' | 'expense'
  mode: 'create' | 'edit'
  initialData?: EntryInitialData | null
  defaultDate: string
  onClose: () => void
  onSuccess?: () => void
}> = ({ type, mode, initialData, defaultDate, onClose, onSuccess }) => {
  const { showToast } = useToast()

  const isIncome = type === 'income'
  const isEdit = mode === 'edit'

  const [amount, setAmount] = useState(initialData ? String(initialData.amount) : '')
  const [text, setText] = useState(initialData ? initialData.text : '')
  const [occurredOn, setOccurredOn] = useState(
    initialData ? initialData.occurredOn : defaultDate,
  )

  const [amountError, setAmountError] = useState<string | null>(null)
  const [textError, setTextError] = useState<string | null>(null)
  const [confirmDelete, setConfirmDelete] = useState(false)

  // Mutations
  const createIncome = useCreateIncome()
  const createExpense = useCreateExpense()
  const updateIncome = useUpdateIncome()
  const updateExpense = useUpdateExpense()
  const deleteIncome = useDeleteIncome()
  const deleteExpense = useDeleteExpense()

  const isPending =
    createIncome.isPending ||
    createExpense.isPending ||
    updateIncome.isPending ||
    updateExpense.isPending ||
    deleteIncome.isPending ||
    deleteExpense.isPending

  const validate = (): boolean => {
    let valid = true
    setAmountError(null)
    setTextError(null)

    const num = Number(amount)
    if (!amount.trim() || isNaN(num) || num < 1 || num > MAX_AMOUNT) {
      setAmountError('Сумма должна быть от 1 до 100 000 000 рублей')
      valid = false
    }

    if (!text.trim()) {
      setTextError(isIncome ? 'Укажите источник дохода' : 'Укажите, что куплено')
      valid = false
    } else if (text.trim().length > 300) {
      setTextError('Максимум 300 символов')
      valid = false
    }

    return valid
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!validate() || isPending) return

    const numAmount = Math.round(Number(amount))
    const trimmedText = text.trim()
    const targetDate = occurredOn || defaultDate

    try {
      if (isEdit && initialData) {
        if (isIncome) {
          await updateIncome.mutateAsync({
            id: initialData.id,
            payload: {
              amount: numAmount,
              source: trimmedText,
              occurred_on: targetDate,
            },
          })
          showToast('Доход обновлён', 'success')
        } else {
          await updateExpense.mutateAsync({
            id: initialData.id,
            payload: {
              amount: numAmount,
              description: trimmedText,
              occurred_on: targetDate,
            },
          })
          showToast('Расход обновлён', 'success')
        }
      } else {
        if (isIncome) {
          await createIncome.mutateAsync({
            amount: numAmount,
            source: trimmedText,
            occurred_on: targetDate,
          })
          showToast('Доход добавлен', 'success')
        } else {
          await createExpense.mutateAsync({
            amount: numAmount,
            description: trimmedText,
            occurred_on: targetDate,
          })
          showToast('Расход добавлен', 'success')
        }
      }
      onClose()
      onSuccess?.()
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Произошла ошибка'
      showToast(msg, 'danger')
    }
  }

  const handleDelete = async () => {
    if (!initialData || isPending) return
    try {
      if (isIncome) {
        await deleteIncome.mutateAsync(initialData.id)
        showToast('Доход удалён', 'info')
      } else {
        await deleteExpense.mutateAsync(initialData.id)
        showToast('Расход удалён', 'info')
      }
      setConfirmDelete(false)
      onClose()
      onSuccess?.()
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Не удалось удалить запись'
      showToast(msg, 'danger')
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4 font-sans text-text">
      <Input
        label="Сумма (₽)"
        value={amount}
        onChange={(e) => {
          setAmount(e.target.value.replace(/\D/g, ''))
          if (amountError) setAmountError(null)
        }}
        error={amountError}
        inputMode="numeric"
        placeholder="0"
        autoFocus
      />

      <Input
        label={isIncome ? 'Источник' : 'Что куплено'}
        value={text}
        onChange={(e) => {
          setText(e.target.value)
          if (textError) setTextError(null)
        }}
        maxLength={300}
        error={textError}
        placeholder={isIncome ? 'Например: чаевые, продажа масла' : 'Например: перчатки, база, аренда'}
      />

      <Input
        label="Дата"
        type="date"
        value={occurredOn}
        onChange={(e) => setOccurredOn(e.target.value)}
      />

      {confirmDelete ? (
        <div className="p-3.5 bg-danger/10 border border-danger/30 rounded-btn space-y-2.5">
          <p className="text-xs text-danger font-semibold">
            Запись будет убрана из учёта.
          </p>
          <div className="flex gap-2">
            <Button
              type="button"
              variant="danger"
              className="flex-1 text-xs h-11 min-h-[44px]"
              onClick={handleDelete}
              loading={isPending}
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
            type="submit"
            variant="primary"
            className="w-full min-h-[44px]"
            loading={isPending}
          >
            Сохранить
          </Button>

          {isEdit && (
            <button
              type="button"
              onClick={() => setConfirmDelete(true)}
              className="w-full py-2.5 text-xs font-semibold text-danger hover:text-danger/80 transition-colors cursor-pointer min-h-[44px] flex items-center justify-center gap-1.5"
            >
              <Trash2 className="w-3.5 h-3.5" />
              <span>Удалить</span>
            </button>
          )}
        </div>
      )}
    </form>
  )
}

export const EntrySheet: React.FC<EntrySheetProps> = ({
  isOpen,
  onClose,
  type,
  mode = 'create',
  initialData,
  defaultDate = '',
  onSuccess,
}) => {
  const isIncome = type === 'income'
  const isEdit = mode === 'edit'

  const title = isEdit
    ? isIncome
      ? 'Редактировать доход'
      : 'Редактировать расход'
    : isIncome
      ? 'Доход'
      : 'Расход'

  return (
    <BottomSheet isOpen={isOpen} onClose={onClose} title={title}>
      {isOpen && (
        <EntrySheetInner
          key={`${type}-${mode}-${initialData?.id ?? 'new'}`}
          type={type}
          mode={mode}
          initialData={initialData}
          defaultDate={defaultDate}
          onClose={onClose}
          onSuccess={onSuccess}
        />
      )}
    </BottomSheet>
  )
}
