# Manicure Dashboard

Dashboard для мастера маникюра: календарь записей, учёт доходов и расходов, клиентская база и прайс-лист.

## Стек технологий

- **Backend:** Python 3.12+, FastAPI, SQLAlchemy 2.x (async), Alembic, PostgreSQL, pydantic-settings, pytest
- **Frontend:** React, TypeScript, Vite, Tailwind CSS, @fontsource (Cormorant, Manrope)
- **Инфраструктура:** Docker Compose (PostgreSQL)

---

## Предварительные требования

- Python 3.12+
- Node.js (LTS) & npm
- Docker & Docker Compose
- Git

---

## Быстрый старт

### 1. Настройка переменных окружения

Скопируйте пример файла конфигурации:

```bash
cp .env.example .env
```

При необходимости отредактируйте параметры подключения в `.env`.

---

### 2. Запуск базы данных (PostgreSQL)

Поднимите контейнер с PostgreSQL:

```bash
docker compose up -d
```

Остановка базы:

```bash
docker compose down
```

---

### 3. Запуск Backend (FastAPI)

1. Перейдите в папку бэкенда:
   ```bash
   cd backend
   ```

2. Создайте и активируйте виртуальное окружение (если ещё не создано):
   - **Linux / macOS:**
     ```bash
     python -m venv .venv
     source .venv/bin/activate
     ```
   - **Windows (PowerShell):**
     ```powershell
     py -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```

3. Установите зависимости:
   ```bash
   pip install -r requirements.txt
   ```

4. Запустите сервер разработки:
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```

5. Проверка работы:
   - Healthcheck: [http://localhost:8000/api/health](http://localhost:8000/api/health)
   - Swagger UI: [http://localhost:8000/docs](http://localhost:8000/docs)

6. Запуск тестов:
   ```bash
   pytest
   ```

7. Миграции базы данных (Alembic):
   ```bash
   alembic upgrade head
   ```

---

### 4. Запуск Frontend (Vite + React)

1. Перейдите в папку фронтенда:
   ```bash
   cd frontend
   ```

2. Установите зависимости (если ещё не установлены):
   ```bash
   npm install
   ```

3. Запустите dev-сервер:
   ```bash
   npm run dev
   ```

4. Откройте в браузере: [http://localhost:5173](http://localhost:5173)

5. Сборка для production:
   ```bash
   npm run build
   ```
