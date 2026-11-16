import calendar
import random
import zoneinfo
from datetime import date, datetime, time, timedelta

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.appointment import Appointment, AppointmentStatus
from app.models.appointment_service import AppointmentService
from app.models.client import Client
from app.models.expense import ExpenseEntry
from app.models.income import IncomeEntry
from app.models.service import Service
from app.models.user import User
from app.models.work_window import WorkWindow
from app.schemas.appointment import AppointmentCreate
from app.schemas.client import ClientCreate
from app.schemas.financial import ExpenseCreate, IncomeCreate
from app.schemas.service import ServiceCreate
from app.schemas.work_window import WorkWindowCreate
from app.services.appointments import create_appointment
from app.services.clients import create_client
from app.services.expenses import create_expense
from app.services.incomes import create_income
from app.services.services import create_service
from app.services.settings import get_or_create_settings
from app.services.work_windows import create_work_window


async def has_business_data(db: AsyncSession) -> bool:
    """Проверяет наличие записей в таблицах бизнес-данных."""
    models = [Client, Service, Appointment, WorkWindow, IncomeEntry, ExpenseEntry]
    for model in models:
        count = (await db.execute(select(func.count()).select_from(model))).scalar_one()
        if count > 0:
            return True
    return False


async def clear_business_data(db: AsyncSession) -> None:
    """Очищает таблицы бизнес-данных в безопасном порядке.

    Не затрагивает пользователей (users), настройки (settings) и миграции (alembic_version).
    """
    await db.execute(delete(AppointmentService))
    await db.execute(delete(Appointment))
    await db.execute(delete(WorkWindow))
    await db.execute(delete(IncomeEntry))
    await db.execute(delete(ExpenseEntry))
    await db.execute(delete(Client))
    await db.execute(delete(Service))
    await db.commit()


async def upsert_demo_owner(db: AsyncSession, password: str) -> User:
    """Создает или обновляет пользователя demo с указанным паролем."""
    stmt = select(User).where(User.login == "demo")
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    new_hash = hash_password(password)
    if user:
        user.password_hash = new_hash
    else:
        user = User(
            login="demo",
            password_hash=new_hash,
        )
        db.add(user)

    await db.commit()
    await db.refresh(user)
    return user


async def seed_demo_data(db: AsyncSession) -> dict[str, int]:
    """Генерирует детерминированные демо-данные через сервисный слой."""
    rnd = random.Random(42)

    settings_obj = await get_or_create_settings(db)
    tz_name = settings_obj.timezone
    tz = zoneinfo.ZoneInfo(tz_name)
    now_local = datetime.now(tz)
    today_local = now_local.date()

    # 1. Создание 8 реалистичных услуг
    services_to_create = [
        ServiceCreate(
            name="Аппаратный / комбинированный маникюр",
            price=1200,
            duration_minutes=60,
            sort_order=1,
            is_active=True,
        ),
        ServiceCreate(
            name="Маникюр с однотонным покрытием гель-лак",
            price=2200,
            duration_minutes=120,
            sort_order=2,
            is_active=True,
        ),
        ServiceCreate(
            name="Маникюр с дизайном (френч / арт / стемпинг)",
            price=2700,
            duration_minutes=150,
            sort_order=3,
            is_active=True,
        ),
        ServiceCreate(
            name="Наращивание ногтей (длина S-M)",
            price=3500,
            duration_minutes=180,
            sort_order=4,
            is_active=True,
        ),
        ServiceCreate(
            name="Коррекция наращенных ногтей",
            price=2800,
            duration_minutes=150,
            sort_order=5,
            is_active=True,
        ),
        ServiceCreate(
            name="Снятие гель-лака без покрытия",
            price=500,
            duration_minutes=30,
            sort_order=6,
            is_active=True,
        ),
        ServiceCreate(
            name="Ремонт / донаращивание одного ногтя",
            price=300,
            duration_minutes=20,
            sort_order=7,
            is_active=True,
        ),
        ServiceCreate(
            name="SPA-уход и парафинотерапия для рук",
            price=800,
            duration_minutes=40,
            sort_order=8,
            is_active=True,
        ),
    ]

    created_services: list[Service] = []
    for s_data in services_to_create:
        created_services.append(await create_service(db, s_data))

    # 2. Создание 25 клиентов с русскими именами и вымышленными номерами
    clients_to_create = [
        ClientCreate(
            name="Анна Смирнова",
            phone="+79991000001",
            notes="Любит нюдовые оттенки, тонкая кутикула",
        ),
        ClientCreate(
            name="Елена Васильева",
            phone="+79991000002",
            notes="Всегда делает классический френч",
        ),
        ClientCreate(name="Мария Кузнецова", phone="+79991000003", notes=None),
        ClientCreate(
            name="Ольга Попова",
            phone="+79991000004",
            notes="Аллергия на масла с цитрусовыми экстрактами",
        ),
        ClientCreate(
            name="Татьяна Соколова",
            phone="+79991000005",
            notes="Ходит стабильно раз в 3 недели",
        ),
        ClientCreate(name="Наталья Михайлова", phone="+79991000006", notes=None),
        ClientCreate(
            name="Ирина Федорова",
            phone="+79991000007",
            notes="Чувствительные боковые валики, аккуратно фрезой",
        ),
        ClientCreate(
            name="Светлана Морозова",
            phone="+79991000008",
            notes="Предпочитает яркие неоновые оттенки и блестки",
        ),
        ClientCreate(name="Екатерина Волкова", phone="+79991000009", notes=None),
        ClientCreate(
            name="Дарья Алексеева",
            phone="+79991000010",
            notes="Просит напоминать о записи за 2 дня",
        ),
        ClientCreate(
            name="Алина Лебедева",
            phone="+79991000011",
            notes="Форма ногтей — острый миндаль",
        ),
        ClientCreate(name="Юлия Семенова", phone="+79991000012", notes=None),
        ClientCreate(
            name="Ксения Егорова",
            phone="+79991000013",
            notes="Часто берет дополнительно SPA-уход",
        ),
        ClientCreate(
            name="Анастасия Павлова",
            phone="+79991000014",
            notes="Офис в соседнем здании, очень ценит тайминг",
        ),
        ClientCreate(name="Виктория Козлова", phone="+79991000015", notes=None),
        ClientCreate(
            name="Полина Степанова",
            phone="+79991000016",
            notes="Тонкие ногти после снятия, бережный опил",
        ),
        ClientCreate(
            name="Валерия Николаева",
            phone="+79991000017",
            notes="Любит молочные базы и жемчужную втирку",
        ),
        ClientCreate(name="Александра Орлова", phone="+79991000018", notes=None),
        ClientCreate(
            name="Алена Андреева",
            phone="+79991000019",
            notes="Записывается строго на утренние слоты по субботам",
        ),
        ClientCreate(
            name="Маргарита Макарова",
            phone="+79991000020",
            notes="Минималистичный дизайн, точки и геометрия",
        ),
        ClientCreate(name="Вероника Захарова", phone="+79991000021", notes=None),
        ClientCreate(
            name="Кристина Зайцева",
            phone="+79991000022",
            notes="Отличная носка покрытия, держится больше 4 недель",
        ),
        ClientCreate(name="Диана Соловьева", phone="+79991000023", notes="Зеленый чай без сахара"),
        ClientCreate(name="Евгения Борисова", phone="+79991000024", notes=None),
        ClientCreate(name="София Яковлева", phone="+79991000025", notes="Короткий мягкий квадрат"),
    ]

    created_clients: list[dict] = []
    for c_data in clients_to_create:
        created_clients.append(await create_client(db, c_data))

    # 3. Рабочие окна: от 6 недель назад до конца следующего месяца
    # (включая текущий и следующий месяц полностью)
    first_of_current_month = today_local.replace(day=1)
    start_window_date = min(today_local - timedelta(days=45), first_of_current_month)

    if today_local.month == 12:
        next_month_year = today_local.year + 1
        next_month = 1
    else:
        next_month_year = today_local.year
        next_month = today_local.month + 1

    _, last_day_next_month = calendar.monthrange(next_month_year, next_month)
    end_window_date = date(next_month_year, next_month, last_day_next_month)

    created_windows_count = 0
    curr_date = start_window_date
    while curr_date <= end_window_date:
        weekday = curr_date.weekday()
        if weekday < 5:  # Будни: по два рабочих окна
            await create_work_window(
                db,
                WorkWindowCreate(
                    date=curr_date,
                    start_time=time(9, 30),
                    end_time=time(13, 30),
                ),
            )
            await create_work_window(
                db,
                WorkWindowCreate(
                    date=curr_date,
                    start_time=time(14, 30),
                    end_time=time(19, 0),
                ),
            )
            created_windows_count += 2
        elif weekday == 5:  # Суббота: часть рабочих (каждая вторая)
            if (curr_date.day // 7) % 2 == 0:
                await create_work_window(
                    db,
                    WorkWindowCreate(
                        date=curr_date,
                        start_time=time(10, 0),
                        end_time=time(15, 30),
                    ),
                )
                created_windows_count += 1
        # Воскресенье: выходной
        curr_date += timedelta(days=1)

    # 4. Записи за прошедшие 6 недель и ближайшие дни
    created_appointments_count = 0

    # Прошедшие дни: от 42 дней назад до вчерашнего дня
    past_dates = [
        today_local - timedelta(days=i)
        for i in range(42, 0, -1)
        if (today_local - timedelta(days=i)).weekday() in (0, 1, 2, 3, 4)
    ]

    # Индексы для распределения статусов и кастомных цен
    appointment_index = 0

    for p_date in past_dates:
        # 1 или 2 записи в день
        # Слот 1: 10:00
        client_idx = appointment_index % len(created_clients)
        client = created_clients[client_idx]
        appointment_index += 1

        # Определяем статус: большинство completed, пара no_show и cancelled
        if appointment_index == 9:
            status = AppointmentStatus.NO_SHOW
        elif appointment_index == 17:
            status = AppointmentStatus.CANCELLED
        elif appointment_index == 27:
            status = AppointmentStatus.NO_SHOW
        elif appointment_index == 33:
            status = AppointmentStatus.CANCELLED
        else:
            status = AppointmentStatus.COMPLETED

        # Выбираем услуги: основная (маникюр или наращивание)
        main_svc_idx = rnd.choice([0, 1, 2, 3, 4])
        svc_ids = [created_services[main_svc_idx].id]
        if rnd.random() < 0.35:
            # Доп услуга: снятие, ремонт или SPA
            extra_svc_idx = rnd.choice([5, 6, 7])
            svc_ids.append(created_services[extra_svc_idx].id)

        # Кастомная цена (price_overridden): 2 записи
        final_price_override = None
        if appointment_index == 5:
            final_price_override = 2000  # Скидка постоянному клиенту
        elif appointment_index == 21:
            final_price_override = 2500  # Фиксированная цена со скидкой

        starts_at_dt = datetime.combine(p_date, time(10, 0), tzinfo=tz)

        await create_appointment(
            db,
            AppointmentCreate(
                client_id=client["id"],
                service_ids=svc_ids,
                starts_at=starts_at_dt,
                status=status,
                final_price=final_price_override,
                force=True,
            ),
        )
        created_appointments_count += 1

        # Слот 2: 15:00 (делаем в 70% дней)
        if rnd.random() < 0.70:
            client_idx2 = (appointment_index + 7) % len(created_clients)
            client2 = created_clients[client_idx2]
            appointment_index += 1

            if appointment_index == 14:
                status2 = AppointmentStatus.NO_SHOW
            else:
                status2 = AppointmentStatus.COMPLETED

            main_svc_idx2 = rnd.choice([0, 1, 2, 4])
            svc_ids2 = [created_services[main_svc_idx2].id]
            if rnd.random() < 0.25:
                svc_ids2.append(created_services[6].id)

            starts_at_dt2 = datetime.combine(p_date, time(15, 0), tzinfo=tz)

            await create_appointment(
                db,
                AppointmentCreate(
                    client_id=client2["id"],
                    service_ids=svc_ids2,
                    starts_at=starts_at_dt2,
                    status=status2,
                    force=True,
                ),
            )
            created_appointments_count += 1

    # Будущие записи (следующие несколько дней): строго scheduled
    future_days = [
        today_local + timedelta(days=i)
        for i in range(1, 6)
        if (today_local + timedelta(days=i)).weekday() in (0, 1, 2, 3, 4)
    ][:4]

    for f_date in future_days:
        client_future = created_clients[rnd.randint(0, len(created_clients) - 1)]
        future_svc = created_services[rnd.choice([1, 2])]
        starts_future = datetime.combine(f_date, time(10, 30), tzinfo=tz)

        await create_appointment(
            db,
            AppointmentCreate(
                client_id=client_future["id"],
                service_ids=[future_svc.id],
                starts_at=starts_future,
                status=AppointmentStatus.SCHEDULED,
                force=True,
            ),
        )
        created_appointments_count += 1

        # Вторая запись на день через день
        if rnd.random() < 0.6:
            client_future2 = created_clients[rnd.randint(0, len(created_clients) - 1)]
            future_svc2 = created_services[rnd.choice([0, 1, 4])]
            starts_future2 = datetime.combine(f_date, time(15, 0), tzinfo=tz)

            await create_appointment(
                db,
                AppointmentCreate(
                    client_id=client_future2["id"],
                    service_ids=[future_svc2.id],
                    starts_at=starts_future2,
                    status=AppointmentStatus.SCHEDULED,
                    force=True,
                ),
            )
            created_appointments_count += 1

    # 5. Прочие доходы и расходы за последние 2 месяца
    incomes_data = [
        IncomeCreate(
            amount=1500,
            source="Продажа масла для кутикулы и крема",
            occurred_on=today_local - timedelta(days=48),
        ),
        IncomeCreate(
            amount=900,
            source="Чаевые",
            occurred_on=today_local - timedelta(days=32),
        ),
        IncomeCreate(
            amount=2000,
            source="Подарочный сертификат",
            occurred_on=today_local - timedelta(days=20),
        ),
        IncomeCreate(
            amount=1200,
            source="Чаевые от постоянных клиентов",
            occurred_on=today_local - timedelta(days=7),
        ),
    ]

    for inc in incomes_data:
        await create_income(db, inc)

    expenses_data = [
        ExpenseCreate(
            amount=16000,
            description="Аренда кабинета (прошлый месяц)",
            occurred_on=today_local - timedelta(days=55),
        ),
        ExpenseCreate(
            amount=4800,
            description="Расходные материалы (гель-лаки, базы, топы)",
            occurred_on=today_local - timedelta(days=45),
        ),
        ExpenseCreate(
            amount=2100,
            description="Дезинфицирующие средства и крафт-пакеты",
            occurred_on=today_local - timedelta(days=38),
        ),
        ExpenseCreate(
            amount=16000,
            description="Аренда кабинета (текущий месяц)",
            occurred_on=today_local - timedelta(days=25),
        ),
        ExpenseCreate(
            amount=5500,
            description="Пилочки, одноразовые наборы и салфетки",
            occurred_on=today_local - timedelta(days=15),
        ),
        ExpenseCreate(
            amount=1500,
            description="Заточка инструментов",
            occurred_on=today_local - timedelta(days=4),
        ),
    ]

    for exp in expenses_data:
        await create_expense(db, exp)

    return {
        "services": len(created_services),
        "clients": len(created_clients),
        "work_windows": created_windows_count,
        "appointments": created_appointments_count,
        "incomes": len(incomes_data),
        "expenses": len(expenses_data),
    }
