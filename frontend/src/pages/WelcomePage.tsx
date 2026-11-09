import React from 'react'

export const WelcomePage: React.FC = () => {
  return (
    <div className="min-h-screen bg-bg text-text px-4 py-8 flex flex-col justify-between max-w-[420px] mx-auto font-sans">
      <header className="pt-2">
        <span className="text-sm font-medium uppercase tracking-wider text-muted">
          Студия маникюра
        </span>
        <h1 className="text-4xl font-normal font-heading text-text mt-1">
          Привет
        </h1>
        <p className="text-sm text-muted mt-1">
          Рабочий день готов к планированию
        </p>
      </header>

      {/* Основная карточка */}
      <div className="my-6 bg-surface border border-border rounded-card p-6 shadow-[0_4px_20px_-2px_rgba(46,35,41,0.06)] flex flex-col gap-6">
        <div>
          <h2 className="text-2xl font-heading font-medium text-text">
            Календарь записей
          </h2>
          <p className="text-sm text-muted mt-0.5">
            Контур — рабочие часы, заливка — активная запись
          </p>
        </div>

        {/* Демонстрация календарных кружков */}
        <div className="flex items-center justify-around gap-2 py-2">
          <div className="flex flex-col items-center gap-1.5">
            <span className="text-xs text-muted">Пн</span>
            {/* День с записями: залитый розовый кружок */}
            <div
              className="w-11 h-11 min-w-[44px] min-h-[44px] rounded-full bg-primary text-surface flex items-center justify-center text-sm font-semibold shadow-sm"
              aria-label="9 ноября — день с записями"
            >
              9
            </div>
          </div>

          <div className="flex flex-col items-center gap-1.5">
            <span className="text-xs text-muted">Вт</span>
            {/* День с рабочим временем: розовый контурный кружок */}
            <div
              className="w-11 h-11 min-w-[44px] min-h-[44px] rounded-full border-2 border-primary text-primary flex items-center justify-center text-sm font-semibold"
              aria-label="10 ноября — рабочий день без записей"
            >
              10
            </div>
          </div>

          <div className="flex flex-col items-center gap-1.5">
            <span className="text-xs text-muted">Ср</span>
            {/* Обычный день */}
            <div className="w-11 h-11 min-w-[44px] min-h-[44px] rounded-full border border-border text-muted flex items-center justify-center text-sm">
              11
            </div>
          </div>

          <div className="flex flex-col items-center gap-1.5">
            <span className="text-xs text-muted">Чт</span>
            <div className="w-11 h-11 min-w-[44px] min-h-[44px] rounded-full border border-border text-muted flex items-center justify-center text-sm">
              12
            </div>
          </div>
        </div>

        {/* Карточка записи */}
        <div className="bg-bg/70 border border-border rounded-btn p-4 flex items-center justify-between">
          <div>
            <div className="text-base font-semibold text-text">
              Комплекс маникюра
            </div>
            <div className="text-sm text-muted mt-0.5">
              14:00 • Мария В.
            </div>
          </div>
          <div className="text-right">
            <div className="text-lg font-bold text-text">
              2 500 ₽
            </div>
            <div className="text-xs text-success font-medium">
              Подтверждена
            </div>
          </div>
        </div>
      </div>

      {/* Кнопка действия (зона нажатия >= 44px) */}
      <footer className="w-full pb-4">
        <button
          type="button"
          className="w-full min-h-[44px] py-3.5 px-6 rounded-btn bg-primary hover:bg-[#b3576e] active:bg-[#9e4a60] text-surface font-semibold text-base transition-colors duration-150 flex items-center justify-center cursor-pointer shadow-sm"
        >
          Новая запись
        </button>
      </footer>
    </div>
  )
}
