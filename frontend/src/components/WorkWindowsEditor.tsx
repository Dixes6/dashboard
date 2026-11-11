import React from 'react'
import { Trash2 } from 'lucide-react'
import type { EditableWindow } from '../lib/workWindows'

export interface WorkWindowsEditorProps {
  windows: EditableWindow[]
  onChange: (windows: EditableWindow[]) => void
  slotStepSeconds?: number
  emptyMessage?: string
  onAddWindow?: () => void
}

export const WorkWindowsEditor: React.FC<WorkWindowsEditorProps> = ({
  windows,
  onChange,
  slotStepSeconds = 900,
  emptyMessage = 'Рабочих окон нет (день свободный)',
  onAddWindow,
}) => {
  const handleChange = (index: number, field: 'start_time' | 'end_time', value: string) => {
    onChange(
      windows.map((w, idx) => (idx === index ? { ...w, [field]: value } : w)),
    )
  }

  const handleRemove = (index: number) => {
    onChange(windows.filter((_, idx) => idx !== index))
  }

  const handleAdd = () => {
    if (onAddWindow) {
      onAddWindow()
      return
    }
    onChange([
      ...windows,
      { start_time: '10:00', end_time: '18:00' },
    ])
  }

  return (
    <div className="space-y-3">
      {windows.length === 0 ? (
        <p className="text-sm text-muted py-2 text-center">{emptyMessage}</p>
      ) : (
        <div className="space-y-3">
          {windows.map((w, idx) => (
            <div key={w.id ?? idx} className="flex items-center gap-2">
              <input
                type="time"
                step={slotStepSeconds}
                value={w.start_time}
                onChange={(e) => handleChange(idx, 'start_time', e.target.value)}
                className="flex-1 h-11 px-3 rounded-btn border border-border bg-surface text-text text-sm focus:outline-none focus:ring-2 focus:ring-primary"
              />
              <span className="text-xs text-muted font-medium select-none">до</span>
              <input
                type="time"
                step={slotStepSeconds}
                value={w.end_time}
                onChange={(e) => handleChange(idx, 'end_time', e.target.value)}
                className="flex-1 h-11 px-3 rounded-btn border border-border bg-surface text-text text-sm focus:outline-none focus:ring-2 focus:ring-primary"
              />
              <button
                type="button"
                onClick={() => handleRemove(idx)}
                className="w-11 h-11 min-w-[44px] min-h-[44px] flex items-center justify-center text-muted hover:text-danger rounded-btn transition-colors cursor-pointer"
                aria-label="Удалить окно"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            </div>
          ))}
        </div>
      )}

      <button
        type="button"
        onClick={handleAdd}
        className="w-full py-2.5 px-3 border border-dashed border-primary/60 text-primary-ink hover:bg-primary-soft/40 rounded-btn text-sm font-semibold flex items-center justify-center gap-1.5 transition-colors cursor-pointer min-h-[44px]"
      >
        + Добавить окно
      </button>
    </div>
  )
}
