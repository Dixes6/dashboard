# Инструкция по восстановлению базы данных из дампа

## 1. Просмотр доступных бэкапов

Вывести список существующих резервных копий:

```bash
ls -lh backups/
```

## 2. Остановка бэкенда

Перед восстановлением рекомендуется временно остановить контейнер с бэкендом, чтобы избежать записи новых данных и блокировок:

```bash
docker compose -f docker-compose.prod.yml stop backend
```

## 3. Восстановление данных

### Вариант А: Восстановление поверх существующей базы

```bash
gunzip -c backups/backup_YYYYMMDD_HHMMSS.sql.gz | \
  docker compose -f docker-compose.prod.yml exec -T db psql -U postgres -d manicure_db
```

### Вариант Б: Чистое восстановление с пересозданием базы (рекомендуется)

Если данные сильно повреждены или нужно гарантировать чистый накат без конфликтов первичных ключей:

1. Завершить активные сессии и пересоздать чистую базу:

```bash
docker compose -f docker-compose.prod.yml exec -T db psql -U postgres -d postgres -c \
  "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = 'manicure_db' AND pid <> pg_backend_pid();"

docker compose -f docker-compose.prod.yml exec -T db psql -U postgres -d postgres -c \
  "DROP DATABASE IF EXISTS manicure_db;"

docker compose -f docker-compose.prod.yml exec -T db psql -U postgres -d postgres -c \
  "CREATE DATABASE manicure_db OWNER postgres;"
```

2. Залить резервную копию:

```bash
gunzip -c backups/backup_YYYYMMDD_HHMMSS.sql.gz | \
  docker compose -f docker-compose.prod.yml exec -T db psql -U postgres -d manicure_db
```

## 4. Запуск бэкенда и проверка

1. Запустить сервис бэкенда:

```bash
docker compose -f docker-compose.prod.yml start backend
```

2. Проверить healthcheck:

```bash
curl -f http://localhost/api/health
```

3. Проверить логи контейнера бэкенда:

```bash
docker compose -f docker-compose.prod.yml logs --tail=50 backend
```
