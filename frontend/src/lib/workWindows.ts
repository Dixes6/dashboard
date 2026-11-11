export interface EditableWindow {
  id?: number
  start_time: string
  end_time: string
}

export function validateWorkWindows(windows: EditableWindow[]): string | null {
  for (let i = 0; i < windows.length; i++) {
    const w = windows[i]
    if (!w.start_time || !w.end_time) {
      return 'Заполните время начала и окончания'
    }
    if (w.end_time <= w.start_time) {
      return 'Конец рабочего окна должен быть позже начала'
    }
  }

  for (let i = 0; i < windows.length; i++) {
    for (let j = i + 1; j < windows.length; j++) {
      const a = windows[i]
      const b = windows[j]
      // Два полуинтервала [s1, e1) и [s2, e2) пересекаются, если s1 < e2 && s2 < e1
      if (a.start_time < b.end_time && b.start_time < a.end_time) {
        return 'Рабочие окна одного дня не должны пересекаться'
      }
    }
  }

  return null
}
