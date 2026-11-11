#!/usr/bin/env bash
set -euo pipefail

# Определяем пути к проекту и директории бэкапов
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
BACKUP_DIR="${PROJECT_DIR}/backups"
COMPOSE_FILE="${PROJECT_DIR}/docker-compose.prod.yml"

mkdir -p "$BACKUP_DIR"

# Подгружаем переменные окружения, если файл .env.production существует
if [ -f "${PROJECT_DIR}/.env.production" ]; then
    set -a
    # shellcheck disable=SC1091
    source "${PROJECT_DIR}/.env.production"
    set +a
fi

DB_USER="${POSTGRES_USER:-postgres}"
DB_NAME="${POSTGRES_DB:-manicure_db}"
TIMESTAMP="$(date +"%Y%m%d_%H%M%S")"
BACKUP_FILE="${BACKUP_DIR}/backup_${TIMESTAMP}.sql.gz"

echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] Starting database backup for '${DB_NAME}'..."

# Создаём дамп базы через docker compose exec и сжимаем gzip
docker compose -f "$COMPOSE_FILE" exec -T db pg_dump -U "$DB_USER" -d "$DB_NAME" | gzip > "$BACKUP_FILE"

# Проверяем, что файл создан и не пустой
if [ ! -s "$BACKUP_FILE" ]; then
    echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] ERROR: Backup file is empty or was not created!" >&2
    rm -f "$BACKUP_FILE"
    exit 1
fi

echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] Backup successfully created: ${BACKUP_FILE}"

# Удаляем бэкапы старше 14 дней
echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] Cleaning up backups older than 14 days..."
find "$BACKUP_DIR" -type f -name "backup_*.sql.gz" -mtime +14 -exec rm -vf {} +

echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] Backup process completed successfully."
