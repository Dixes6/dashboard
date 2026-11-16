# Отчёт о корректности и соответствии бизнес-правилам (AGENTS.md)

**Дата проведения ревью:** 11 ноября 2026 г.  
**Роль:** Ревьюер корректности  
**Объект проверки:** Исходный код бэкенда (`backend/app`), базы данных (`backend/alembic`), тестов (`backend/tests`) и фронтенда (`frontend/src`) на строгое соответствие бизнес-правилам проекта `manicure-dashboard`.

---

## Резюме

Проведена глубокая верификация кодовой базы проекта по всем 9 ключевым блокам требований AGENTS.md.

В целом архитектура проекта выстроена добротно:
- Бизнес-логика вынесена в сервисный слой (`app/services/`), роутеры FastAPI остаются тонкими контроллерами.
- Финансовые данные рассчитываются целочисленно (`int` в рублях), `final_price` визитов и прочие поступления (`income_entries`) строго разделены и не дублируются.
- Временные метки хранятся в UTC с часовыми поясами (`timestamptz`), все календарные агрегации используют полуинтервалы `[start, next_start)` с привязкой к локальному дню из `settings`.
- Мягкое удаление (`deleted_at`) соблюдается во всех без исключения выборках (календарь, визиты, доходы, расходы, статистика, клиенты).
- На уровне PostgreSQL настроены строгие ограничения: `CHECK`-констрейнты на неотрицательность денег, положительность длительностей, отношение `starts_at < ends_at`, а также уникальный частичный индекс на активные номера телефонов клиентов.
- Фронтенд дисциплинирован: отсутствуют ошибки условного рендера вида `{число && ...}`, форматирование времени и денег строго инкапсулировано в `formatTime` / `formatMoney`, а цветовая палитра на 100% соответствует токенам из `docs/DESIGN.md`.

При этом выявлены дефекты логики обновлений записей и расхождения с регламентом, классифицированные ниже.

---

## Замечания

### Critical
*Критических замечаний (приводящих к утечкам данных, инъекциям, порче БД или полному отказу сервиса) не обнаружено.*

---

### High

#### 1. Пропуск проверки коллизий и рабочих окон при смене только статуса записи
- **Файл:строка:** [`backend/app/services/appointments.py:458-468`](file:///D:/Python%20Code%20Training/PythonProject/manicure-dashboard/backend/app/services/appointments.py#L458-L468)
- **Проблема:** В функции `update_appointment` запуск предупреждений `_run_warnings` обёрнут в условие:
  ```python
  if data.starts_at is not None or data.service_ids is not None or data.ends_at is not None:
      warnings, overlapping_ids = await _run_warnings(...)
  ```
  Если через `PATCH /api/appointments/{id}` обновляется **только** `status` (например, запись была `cancelled`, а мастер переводит её обратно в `scheduled` или `completed`), условие ложно, и `_run_warnings` не вызывается вообще.
- **Как проявится у пользователя:** Если на время отменённой записи мастер уже поставил другого клиента (или если время записи не попадает в рабочие окна), повторная активация записи пройдёт молча без ошибки `409 Conflict (needs_confirmation)`, создав незамеченную накладку двух клиентов на один и тот же слот.
- **Как исправить:** Расширить условие валидации: вызывать `_run_warnings`, если изменились время/услуги **или** если изменился статус (`data.status is not None`):
  ```python
  if any([data.starts_at, data.service_ids, data.ends_at, data.status]):
      warnings, overlapping_ids = await _run_warnings(...)
  ```

#### 2. Отсутствие запрета статусов кроме `scheduled` для будущих записей при PATCH-обновлении
- **Файл:строка:** [`backend/app/services/appointments.py:378-380`](file:///D:/Python%20Code%20Training/PythonProject/manicure-dashboard/backend/app/services/appointments.py#L378-L380) (в сравнении с валидацией при создании на строках [`223-224`](file:///D:/Python%20Code%20Training/PythonProject/manicure-dashboard/backend/app/services/appointments.py#L223-L224))
- **Проблема:** Бизнес-правило AGENTS.md гласит: *«Если starts_at в будущем (относительно текущего момента), статус кроме scheduled запрещён: вернуть 422 с понятным сообщением»*. В `create_appointment` это правило реализовано, однако в `update_appointment` (при PATCH) проверка полностью отсутствует — можно свободно перевести будущую запись в статус `completed` или `no_show`, либо перенести уже завершённую запись на будущую дату.
- **Как проявится у пользователя:** Случайный клик или ошибка клиента переводит будущую запись в статус «Состоялась» (`completed`). Это искажает отчётность: неполученный доход учитывается в статистике и финансовых показателях текущего/будущего месяца как уже заработанный.
- **Как исправить:** В `update_appointment` после вычисления итоговых значений `appointment.starts_at` и `appointment.status` добавить проверку:
  ```python
  now_utc = datetime.now(timezone.utc)
  if appointment.starts_at > now_utc and appointment.status != AppointmentStatus.SCHEDULED:
      raise ValueError("Статус кроме 'scheduled' запрещён для записей в будущем")
  ```

---

### Medium

#### 3. Необработанный `IntegrityError` при гонке создания инлайн-клиента
- **Файл:строка:** [`backend/app/services/appointments.py:105-124`](file:///D:/Python%20Code%20Training/PythonProject/manicure-dashboard/backend/app/services/appointments.py#L105-L124)
- **Проблема:** В `_resolve_client` при создании новой записи с инлайн-клиентом (`data.client`) сначала делается `SELECT` по нормализованному номеру телефона среди неудалённых клиентов, и если клиент не найден, выполняется `db.add(new_client); await db.flush()`. Конкурентные вызовы `create_appointment` сериализованы через advisory-lock, однако внешний запрос `POST /api/clients` не берёт этот замок. Если между `SELECT` в `_resolve_client` и `await db.flush()` параллельный запрос через `POST /api/clients` успеет вставить клиента с таким же телефоном, `flush()` выбросит необработанный `sqlalchemy.exc.IntegrityError` (срабатывание индекса `uq_clients_phone_active`).
- **Как проявится у пользователя:** Сервер вернёт необработанную ошибку `500 Internal Server Error` вместо штатного создания записи или понятного конфликта 409.
- **Как исправить:** Обернуть блок вставки инлайн-клиента в сохранение точки отката (savepoint) или перехват `IntegrityError`:
  ```python
  try:
      new_client = Client(name=inline_client.name, phone=normalized_phone)
      db.add(new_client)
      await db.flush()
      return new_client
  except IntegrityError:
      # Повторно читаем уже созданного параллельным запросом клиента
      stmt = select(Client).where(Client.phone == normalized_phone, Client.deleted_at.is_(None))
      existing = (await db.execute(stmt)).scalar_one_or_none()
      if existing:
          return existing
      raise
  ```

#### 4. Отсутствие в пользовательском интерфейсе экрана смены настроек и предупреждения о смене часового пояса
- **Файл:строка:** [`frontend/src/api/home.ts:23`](file:///D:/Python%20Code%20Training/PythonProject/manicure-dashboard/frontend/src/api/home.ts#L23), [`frontend/src/pages/`](file:///D:/Python%20Code%20Training/PythonProject/manicure-dashboard/frontend/src/pages/)
- **Проблема:** Согласно правилу 63 AGENTS.md: *«Смена часового пояса в настройках меняет локальный день существующих записей в отчётах; интерфейс должен предупреждать об этом при смене»*. Мутация `useUpdateSettings` объявлена в API фронтенда, но страницы или модального окна настроек салона во фронтенде нет вообще (нет ни одного вызова `useUpdateSettings`). Предупреждение о смещении локальных дней записей в интерфейсе не реализовано.
- **Как проявится у пользователя:** Мастер не имеет возможности изменить часовой пояс или шаг сетки через веб-интерфейс. Если функциональность будет выведена без предупреждения, смена таймзоны вызовет неожиданное для пользователя перераспределение визитов по дням в отчётах.
- **Как исправить:** Добавить в интерфейс раздел/модалку настроек салона с обязательным модальным окном подтверждения при изменении часового пояса: *«Внимание: смена часового пояса изменит локальные даты существующих визитов в календаре и финансовых отчётах»*.

---

### Low

#### 5. Несимметричный `downgrade` в миграции `f61d7304ed8b`
- **Файл:строка:** [`backend/alembic/versions/f61d7304ed8b_add_business_rules_indexes.py:50-59`](file:///D:/Python%20Code%20Training/PythonProject/manicure-dashboard/backend/alembic/versions/f61d7304ed8b_add_business_rules_indexes.py#L50-L59)
- **Проблема:** В методе `upgrade()` присутствует блок `op.add_column('income_entries', ... deleted_at)` и `op.add_column('expense_entries', ... deleted_at)` (хотя эти колонки фактически уже были созданы в первоначальной миграции `c99320d8eb8b`). При этом в `downgrade()` удаление этих колонок отсутствует.
- **Как проявится у пользователя:** Пользователь не заметит. При изолированном тестировании миграций или ручном откате ревизии схема остаётся с расхождением.
- **Как исправить:** Удалить избыточный блок проверки колонок в `f61d7304ed8b` или добавить симметричный `drop_column` в `downgrade()` с проверкой существования.

#### 6. Физическое удаление записей в таблице `appointment_services` при обновлении услуг
- **Файл:строка:** [`backend/app/services/appointments.py:415-419`](file:///D:/Python%20Code%20Training/PythonProject/manicure-dashboard/backend/app/services/appointments.py#L415-L419)
- **Проблема:** При вызове PATCH с новым набором `service_ids` старые связки удаляются физически:
  ```python
  for old_svc in list(appointment.appointment_services):
      await db.delete(old_svc)
  ```
  В AGENTS.md зафиксировано: *«Физически ничего не удаляем (никаких DELETE): только deleted_at, у услуг is_active. work_windows — единственное исключение из мягкого удаления»*.
- **Как проявится у пользователя:** Для пользователя всё работает корректно, однако теряется аудит исходного состава услуг визита до редактирования.
- **Как исправить:** Явно зафиксировать в AGENTS.md, что промежуточная таблица связей `appointment_services` при редактировании состава визита является допустимым исключением из правила мягкого удаления (наряду с `work_windows`), либо добавить колонку `deleted_at` в `appointment_services`.

#### 7. Проверка пересечений загружает всю таблицу записей в память Python
- **Файл:строка:** [`backend/app/services/appointments.py:190-205`](file:///D:/Python%20Code%20Training/PythonProject/manicure-dashboard/backend/app/services/appointments.py#L190-L205)
- **Проблема:** При проверке коллизий запрос выбирает абсолютно все неудалённые записи со статусами `scheduled` и `completed` за всё время существования студии:
  ```python
  appt_stmt = select(Appointment).where(
      Appointment.deleted_at.is_(None),
      Appointment.status.in_([AppointmentStatus.SCHEDULED, AppointmentStatus.COMPLETED]),
  )
  ```
  После чего фильтрация пересечений производится в Python через `check_appointment_overlap`.
- **Как проявится у пользователя:** При накоплении нескольких тысяч записей за пару лет операция создания и изменения записей начнёт заметно замедляться и потреблять лишнюю оперативную память бэкенда.
- **Как исправить:** Ограничить SQL-запрос диапазоном дат (например, `starts_at >= :starts_at_utc - interval '1 day' AND starts_at <= :ends_at_utc + interval '1 day'`), либо делегировать проверку пересечений самому PostgreSQL (`starts_at < :ends_at AND ends_at > :starts_at`).

---

## Проверено и в порядке

### 1. Деньги и финансовая логика
- **Доход от визитов:** В [`dashboard.py`](file:///D:/Python%20Code%20Training/PythonProject/manicure-dashboard/backend/app/services/dashboard.py), [`finance.py`](file:///D:/Python%20Code%20Training/PythonProject/manicure-dashboard/backend/app/services/finance.py) и [`stats.py`](file:///D:/Python%20Code%20Training/PythonProject/manicure-dashboard/backend/app/services/stats.py) строго суммируется `final_price` только записей со статусом `completed` и `deleted_at IS NULL`.
- **Прочие поступления (`income_entries`):** Полностью изолированы от визитов. Визиты не попадают в таблицу `income_entries`. В отчётах финансов визиты и ручные поступления объединяются через `UNION ALL` без взаимного задвоения.
- **Чистая прибыль:** Формула `(доход от визитов + прочие доходы) - расходы` соблюдается как в ежемесячном срезе (`net_profit_month`), так и в еженедельном (`net_profit_week`) и историческом (`get_months_summary`).
- **Расчёт `list_price`:** Клиент не передаёт `list_price` в схемах `AppointmentCreate` и `AppointmentUpdate`. Сервер считает `list_price` как сумму снапшотов цен услуг (`sum(s.price)` при создании, `sum(s.price_snapshot)` при обновлении).
- **Логика `price_overridden` и `reset_price`:**
  - При создании: если передан `final_price`, флаг `price_overridden = (final_price != list_price)`. Если не передан — `final_price = list_price`, `price_overridden = False`.
  - При обновлении услуг: если `reset_price=True`, цена сбрасывается к новому `list_price`, флаг становится `False`. Если цена была переопределена ранее (`price_overridden=True`), а `final_price` в запросе не передан — сохранённая ручная цена остаётся неизменной.
  - Если цена не была переопределена ранее, `final_price` автоматически подтягивается к новому `list_price`.
- **Снимки услуг:** При изменении `service_ids` в PATCH старые услуги сохраняют ранее зафиксированные `name_snapshot`, `price_snapshot` и `duration_snapshot`, а новые услуги получают актуальные параметры из каталога `services`.
- **Дубликаты услуг:** Запрос с одинаковыми `service_ids` (например, `[1, 1]`) корректно создает отдельные строки в `appointment_services` с возрастающей позицией, увеличивая итоговую стоимость и длительность.
- **Типы данных:** Все денежные величины строго целочисленные (`Integer` / `bigint`), операции деления целочисленные (`//`), применение `float` отсутствует.

---

### 2. Время и часовые пояса
- **Хранение в UTC:** В моделях SQLAlchemy все временные колонки имеют тип `DateTime(timezone=True)`. База PostgreSQL сохраняет таймстемпы в UTC.
- **Локальные границы суток и месяца:** Все временные выборки (`dashboard.py`, `stats.py`, `finance.py`, `appointments.py`) строятся через полуинтервалы:
  `starts_at >= month_start_utc AND starts_at < next_month_start_utc`.
  Исключительная верхняя граница исключает краевые коллизии на стыке суток и месяцев.
- **Отчётный день:** Отчётным днём визита является локальная дата `starts_at` в часовом поясе салона (`timezone(:tz_name, starts_at)::date`). Для `income_entries` и `expense_entries` используется дата операции `occurred_on`.
- **Записи около полуночи:** Проверка рабочих окон корректно отслеживает переход через полночь (`local_start_date != local_end_date`) и помечает запись предупреждением `outside_work_window`.
- **Отсутствие naive datetime:** Вспомогательные функции [`app/core/time_utils.py`](file:///D:/Python%20Code%20Training/PythonProject/manicure-dashboard/backend/app/core/time_utils.py) преобразуют любые наивные даты из тела запросов к часовому поясу салона, приводя их к UTC-aware объектам до передачи в БД.

---

### 3. Мягкое удаление (Таблица проверенных запросов)

Ниже приведён полный аудит всех запросов к сущностям `clients`, `appointments`, `income_entries`, `expense_entries`, `services`:

| № | Файл и строка | Сущность | Назначение запроса | Фильтрует удалённые (`deleted_at` / `is_active`) |
|---|---|---|---|:---:|
| 1 | `appointments.py:81` | `Appointment` | Получение записи по id (`_load_appointment`) | **Да** (`deleted_at.is_(None)`) |
| 2 | `appointments.py:98` | `Client` | Поиск клиента по id при создании записи | **Да** (`deleted_at.is_(None)`) |
| 3 | `appointments.py:111` | `Client` | Поиск клиента по телефону (инлайн) | **Да** (`deleted_at.is_(None)`) |
| 4 | `appointments.py:133` | `Service` | Загрузка услуг записи по id | **Да** (проверка `svc.is_active` в Python) |
| 5 | `appointments.py:190` | `Appointment` | Проверка пересечений записей (`_run_warnings`) | **Да** (`deleted_at.is_(None)`) |
| 6 | `appointments.py:302` | `Appointment` | Список записей (`list_appointments`) | **Да** (`deleted_at.is_(None)`) |
| 7 | `appointments.py:366` | `Client` | Проверка клиента при обновлении записи | **Да** (`deleted_at.is_(None)`) |
| 8 | `appointments.py:385` | `Service` | Проверка услуг при обновлении записи | **Да** (проверка `svc.is_active` в Python) |
| 9 | `appointments.py:478` | `Appointment` | Удаление записи (`delete_appointment`) | **Да** (`deleted_at.is_(None)`) |
| 10 | `appointments.py:497` | `Appointment` | Ближайшая запись (`get_next_appointment`) | **Да** (`deleted_at.is_(None)`) |
| 11 | `clients.py:19` | `Client` | Получение клиента по id (`get_client_by_id`) | **Да** (`deleted_at.is_(None)`) |
| 12 | `clients.py:26` | `Client`, `Appointment` | Клиент со статистикой (`get_client_with_stats`) | **Да** (у клиента и у визитов `deleted_at.is_(None)`) |
| 13 | `clients.py:84, 90` | `Client`, `Appointment` | Список клиентов со статистикой | **Да** (у клиентов и у визитов `deleted_at.is_(None)`) |
| 14 | `clients.py:129` | `Client` | Проверка дубликата телефона при создании | **Да** (`deleted_at.is_(None)`) |
| 15 | `clients.py:171` | `Client` | Проверка дубликата телефона при обновлении | **Да** (`deleted_at.is_(None)`) |
| 16 | `clients.py:195` | `Client` | Удаление клиента (`delete_client`) | **Да** (через `get_client_by_id`) |
| 17 | `dashboard.py:57` | `Appointment` | Календарь на месяц (`get_calendar_month`) | **Да** (`deleted_at.is_(None)`) |
| 18 | `dashboard.py:107` | `IncomeEntry` | Прочие доходы дня (`get_day_details`) | **Да** (`deleted_at.is_(None)`) |
| 19 | `expenses.py:16` | `ExpenseEntry` | Список расходов (`list_expenses`) | **Да** (`deleted_at.is_(None)`) |
| 20 | `expenses.py:29` | `ExpenseEntry` | Получение расхода по id | **Да** (`deleted_at.is_(None)`) |
| 21 | `finance.py:50` | `Appointment` | Визиты в финансовом журнале | **Да** (`a.deleted_at IS NULL`) |
| 22 | `finance.py:67` | `IncomeEntry` | Доходы в финансовом журнале | **Да** (`deleted_at IS NULL`) |
| 23 | `finance.py:98` | `ExpenseEntry` | Расходы в финансовом журнале | **Да** (`deleted_at IS NULL`) |
| 24 | `incomes.py:16` | `IncomeEntry` | Список доходов (`list_incomes`) | **Да** (`deleted_at IS NULL`) |
| 25 | `incomes.py:29` | `IncomeEntry` | Получение дохода по id | **Да** (`deleted_at IS NULL`) |
| 26 | `services.py:11` | `Service` | Список услуг (`list_services`) | **Да** (`is_active.is_(True)` при `include_archived=False`) |
| 27 | `services.py:20` | `Service` | Получение услуги по id | *Намеренно без фильтра* (позволяет отображать/редактировать архивные) |
| 28 | `stats.py:77` | `Appointment` | Выручка визитов за месяц | **Да** (`deleted_at IS NULL`) |
| 29 | `stats.py:101` | `IncomeEntry` | Прочие доходы за месяц | **Да** (`deleted_at IS NULL`) |
| 30 | `stats.py:119` | `ExpenseEntry` | Расходы за месяц | **Да** (`deleted_at IS NULL`) |
| 31 | `stats.py:159` | `Appointment` | Визиты текущей недели | **Да** (`deleted_at IS NULL`) |
| 32 | `stats.py:165` | `IncomeEntry` | Прочие доходы текущей недели | **Да** (`deleted_at IS NULL`) |
| 33 | `stats.py:170` | `ExpenseEntry` | Расходы текущей недели | **Да** (`deleted_at IS NULL`) |
| 34 | `stats.py:205` | `Appointment` | Популярная услуга месяца | **Да** (`a.deleted_at IS NULL`) |
| 35 | `stats.py:238` | `Appointment` | Визиты для самого прибыльного дня | **Да** (`deleted_at IS NULL`) |
| 36 | `stats.py:249` | `IncomeEntry` | Доходы для самого прибыльного дня | **Да** (`deleted_at IS NULL`) |
| 37 | `stats.py:316` | `Appointment` | Сводка по месяцам: визиты | **Да** (`deleted_at IS NULL`) |
| 38 | `stats.py:325` | `IncomeEntry` | Сводка по месяцам: доходы | **Да** (`deleted_at IS NULL`) |
| 39 | `stats.py:333` | `ExpenseEntry` | Сводка по месяцам: расходы | **Да** (`deleted_at IS NULL`) |

*Примечание:* Таблица `work_windows` физически удаляет строки (`DELETE FROM work_windows WHERE id = ...`), что является документированным и разрешённым исключением в AGENTS.md (правило 59).

---

### 4. Статистика
- **Средний доход за день:** Рассчитывается строго как `доход_от_визитов // число_активных_дней`. Активным днём считается локальный день, где состоялась хотя бы одна запись со статусом `completed` (`COUNT(DISTINCT (timezone(:tz_name, starts_at))::date)`). При отсутствии состоявшихся визитов возвращается `None`.
- **Популярная услуга:** Выбирается по максимальному числу строк в `appointment_services` (`COUNT(aps.id)`), при равенстве — по суммарной выручке из `price_snapshot` (`revenue DESC`).
- **Самый прибыльный день:** Находится через группировку объединённого дохода (`daily_visits` + `daily_other`) по локальной дате, без вычета расходов. При равенстве дохода детерминированно выбирается более ранняя дата (`day_date ASC`).

---

### 5. Записи и рабочие окна
- **Advisory-блокировка:** Вызов `pg_advisory_xact_lock(42_424_242)` берётся на первой строке в транзакции в методах `create_appointment` и `update_appointment` до чтения существующих слотов и автоматически удерживается PostgreSQL до коммита или отката транзакции.
- **Подтверждение коллизий (409 Conflict):** При наличии предупреждений и отсутствии флага `force=True` выбрасывается `NeedsConfirmationError`, трансформирующийся роутером в HTTP 409 с кодом `needs_confirmation`, списком `warnings` и `overlapping_ids`.
- **Вычисление `ends_at`:** По умолчанию устанавливается как `starts_at + sum(duration_snapshot)`. При изменении услуг или времени начала конец автоматически пересчитывается.
- **Массовое заполнение месяца:** Эндпоинт `/api/work-windows/bulk` поддерживает создание нескольких окон в один день (массив `windows: list[WorkWindowTimeSlot]`), проверяет отсутствие внутренних взаимных пересечений слотов и пересечений с уже сохранёнными окнами.
- **Поиск клиентов:** Реализован регистронезависимый поиск по имени (`ILIKE`) с экранированием спецсимволов (`%`, `_`, `\`) и приоритизацией совпадений с начала строки (`STARTS WITH`), а также поиск по префиксу телефона.

---

### 6. Клиенты
- **Нормализация телефона:** Функция [`app/core/phone.py:normalize_phone`](file:///D:/Python%20Code%20Training/PythonProject/manicure-dashboard/backend/app/core/phone.py#L4) приводит 10-значные и 11-значные номера к формату `79XXXXXXXXX`, валидирует российские мобильные префиксы и отклоняет невалидные строки.
- **Уникальность в БД:** В PostgreSQL создан частичный уникальный индекс `uq_clients_phone_active` с предикатом `WHERE deleted_at IS NULL`. Невозможно создать двух активных клиентов с одинаковым номером. При мягком удалении клиента номер освобождается для новой регистрации.

---

### 7. База данных и миграции
- **Ограничения (CHECK):**
  - `appointments`: `starts_at < ends_at`, `list_price >= 0`, `final_price >= 0`.
  - `appointment_services`: `price_snapshot >= 0`, `duration_snapshot > 0`.
  - `clients`: `phone ~ '^[0-9]+$'`.
  - `income_entries` / `expense_entries`: `amount >= 0`.
  - `services`: `price >= 0`, `duration_minutes > 0`.
  - `settings`: `id = 1` (синглтон), `slot_step_minutes > 0`.
  - `work_windows`: `end_time > start_time`.
- **Индексы:** Настроены `ix_appointments_starts_at`, `ix_appointments_client_id`, `ix_appointments_status_starts_at`, `ix_clients_phone` (`text_pattern_ops`), `ix_income_entries_occurred_on`, `ix_expense_entries_occurred_on`, `ix_work_windows_date`.
- **Откат (Downgrade):** Миграции корректно откатываются до `base` и повторно накатываются до `head`, что подтверждено тестом [`test_migrations.py`](file:///D:/Python%20Code%20Training/PythonProject/manicure-dashboard/backend/tests/test_migrations.py).

---

### 8. Фронтенд
- **Условный рендер:** Проверены все компоненты `.tsx`. Запрещённая конструкция `{число && <JSX />}` полностью отсутствует: везде применены тернарные операторы `? :` либо явные сравнения `items.length > 0 && ...`, `count !== null && ...`.
- **Форматирование:** Отображение времени выполняется исключительно через `formatTime`, денег — через `formatMoney`. Ручные конкатенации валюты или времени не используются.
- **Токены дизайна:** Компоненты строго используют семантические CSS-переменные из `docs/DESIGN.md` (`bg`, `surface`, `border`, `text`, `muted`, `primary`, `accent`, `success`, `danger`). Произвольные шестнадцатеричные цвета (`#...`) и стандартные цветовые палитры Tailwind (`blue-500`, `gray-200`) в коде отсутствуют. Все кликабельные элементы имеют минимальную зону нажатия 44px.

---

## Анализ тестов и производительности

### Что реально покрыто
- Авторизация, сессионные куки, защита неавторизованных маршрутов.
- Базовый CRUD и мягкое удаление записей, клиентов, услуг, доходов и расходов.
- Сохранение неизменяемости снимков (`name_snapshot`, `price_snapshot`, `duration_snapshot`) при смене цен в каталоге.
- Расчёты `final_price`, `price_overridden`, сброс цен (`reset_price`).
- Проверка предупреждений о выходе за рабочие окна и пересечениях при создании записей.
- Расчёты статистики за месяц: средний доход за день, популярная услуга с правилом разрешения ничьих по выручке, самый прибыльный день.

### Что не покрыто тестами
1. Обновление (PATCH) статуса записи в будущем на `completed` или `no_show` (проверка отсутствия запрета).
2. Обновление (PATCH) статуса с `cancelled` на `scheduled` в слот с существующей записью (проверка пропуска `_run_warnings`).
3. Конкурентная гонка создания инлайн-клиента в визите параллельно с `POST /api/clients`.
4. Влияние смены часового пояса в настройках на пересчёт локальных дней исторических визитов в отчётах.
5. Граничные значения сумм (максимальные допустимые числа денег).

### Почему тесты выполняются ~2:20 и как их ускорить
Замедление тестового набора вызвано сочетанием трёх факторов в фикстурах [`backend/tests/conftest.py`](file:///D:/Python%20Code%20Training/PythonProject/manicure-dashboard/backend/tests/conftest.py):
1. **Повторное хеширование и верификация Argon2 на каждый тест:**
   - Фикстура `test_user` в каждом тесте вызывает `hash_password("correct_password")` (~100–150 мс CPU).
   - Хелпер `_login` в каждом тесте отправляет запрос на `/api/auth/login`, вызывая `verify_password` (~100–150 мс CPU).
   - При 131 тесте это суммарно даёт **~30–40 секунд чистой нагрузки на процессор** только на расчёт криптографических хешей.
2. **`TRUNCATE TABLE ... CASCADE` перед каждым тестом:**
   - Фикстура `clean_database` (`autouse=True`) открывает отдельное синхронное соединение `psycopg` и выполняет полную очистку 9 таблиц через `TRUNCATE CASCADE`. В PostgreSQL операция `TRUNCATE` захватывает эксклюзивную блокировку `AccessExclusiveLock` и сбрасывает файлы WAL, что занимает 60–100 мс на тест (**~10–15 секунд суммарно**).
3. **Отсутствие пула соединений (`poolclass=NullPool`):**
   - На каждый HTTP-запрос в тестах открывается и закрывается новое физическое TCP-соединение к PostgreSQL.

#### Как ускорить (рекомендации словами):
- **Ускорить пароли в тестах:** захешировать пароль один раз на уровне тестовой сессии (`scope="session"`) и переиспользовать готовый хеш, либо в `_login` генерировать JWT-токен напрямую через `create_access_token` в обход роута логина с проверкой Argon2. Для Argon2 в тестах можно также снизить параметры сложности (`time_cost=1`, `memory_cost=1024`).
- **Изоляция через транзакции вместо TRUNCATE:** оборачивать каждый тест во внешнюю транзакцию с откатом (`session.rollback()`) через savepoint. Это очищает базу мгновенно в оперативной памяти без дисковых операций `TRUNCATE`.
- **Включить пул соединений:** заменить `NullPool` на тестовый пул соединений, чтобы исключить задержки на постоянный TCP handshake.
*Реализация этих мер сократит время прогона тестов с ~2:20 до ~10–15 секунд.*

---

## Не смог проверить
1. **Поведение системы под реальной параллельной нагрузкой:** Advisory-блокировка `pg_advisory_xact_lock` протестирована функционально, однако поведение пула соединений PostgreSQL при массовых параллельных блокировках под нагрузкой требует нагрузочного тестирования.
2. **Предупреждение интерфейса при смене часового пояса:** Проверить визуальное предупреждение невозможно, так как экран настроек и компонент смены часового пояса в текущей версии фронтенда ещё не созданы.
3. **Измерение времени прогона тестов секундомером:** Полный запуск `pytest` не производился согласно явному запрету в системных инструкциях пользователя; оценка 2:20 основана на предоставленных данных и статическом профилировании фикстур.
