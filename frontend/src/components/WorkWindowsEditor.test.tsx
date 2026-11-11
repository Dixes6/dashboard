import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { WorkWindowsEditor } from './WorkWindowsEditor'
import { validateWorkWindows, type EditableWindow } from '../lib/workWindows'

describe('validateWorkWindows', () => {
  it('returns null for valid non-overlapping windows', () => {
    const windows: EditableWindow[] = [
      { start_time: '10:00', end_time: '13:00' },
      { start_time: '14:00', end_time: '18:00' },
    ]
    expect(validateWorkWindows(windows)).toBeNull()
  })

  it('allows adjacent non-overlapping windows', () => {
    const windows: EditableWindow[] = [
      { start_time: '10:00', end_time: '13:00' },
      { start_time: '13:00', end_time: '18:00' },
    ]
    expect(validateWorkWindows(windows)).toBeNull()
  })

  it('returns error when start_time or end_time is empty', () => {
    const windows: EditableWindow[] = [
      { start_time: '', end_time: '13:00' },
    ]
    expect(validateWorkWindows(windows)).toBe('Заполните время начала и окончания')
  })

  it('returns error when end_time <= start_time', () => {
    const windows: EditableWindow[] = [
      { start_time: '14:00', end_time: '10:00' },
    ]
    expect(validateWorkWindows(windows)).toBe('Конец рабочего окна должен быть позже начала')
  })

  it('returns error when windows overlap', () => {
    const windows: EditableWindow[] = [
      { start_time: '10:00', end_time: '14:00' },
      { start_time: '13:00', end_time: '17:00' },
    ]
    expect(validateWorkWindows(windows)).toBe('Рабочие окна одного дня не должны пересекаться')
  })
})

describe('WorkWindowsEditor', () => {
  it('renders empty message when no windows', () => {
    render(
      <WorkWindowsEditor
        windows={[]}
        onChange={vi.fn()}
        emptyMessage="Окон нет"
      />,
    )
    expect(screen.getByText('Окон нет')).toBeDefined()
  })

  it('renders window inputs and triggers onChange on edit and remove', () => {
    const onChange = vi.fn()
    const windows: EditableWindow[] = [
      { start_time: '10:00', end_time: '13:00' },
    ]
    render(
      <WorkWindowsEditor
        windows={windows}
        onChange={onChange}
      />,
    )

    const inputs = screen.getAllByDisplayValue(/10:00|13:00/)
    expect(inputs).toHaveLength(2)

    // Edit start_time
    fireEvent.change(inputs[0], { target: { value: '09:00' } })
    expect(onChange).toHaveBeenCalledWith([{ start_time: '09:00', end_time: '13:00' }])

    // Remove window
    const deleteButton = screen.getByRole('button', { name: 'Удалить окно' })
    fireEvent.click(deleteButton)
    expect(onChange).toHaveBeenCalledWith([])
  })

  it('triggers onAddWindow when clicking add button', () => {
    const onAdd = vi.fn()
    render(
      <WorkWindowsEditor
        windows={[]}
        onChange={vi.fn()}
        onAddWindow={onAdd}
      />,
    )

    const addButton = screen.getByRole('button', { name: /\+ Добавить окно/ })
    fireEvent.click(addButton)
    expect(onAdd).toHaveBeenCalledTimes(1)
  })
})
