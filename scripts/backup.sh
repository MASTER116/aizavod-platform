#!/bin/bash
# P0 4.9: Backup / DR — pg_dump daily + Redis RDB copy
# ГОСТ РВ 0015-002-2020: управление на стадиях ЖЦ, обеспечение безопасности
# MIL-HDBK-338B: Reliability, fault tolerance
#
# Usage: crontab -e → 0 3 * * * /opt/ai-altyn/scripts/backup.sh
# Or: docker exec -it ai-altyn-postgres-1 bash /scripts/backup.sh

set -euo pipefail

BACKUP_DIR="/opt/ai-altyn/backups"
DATE=$(date +%Y-%m-%d_%H%M)
RETENTION_DAYS=30
DB_NAME="aizavod"
DB_USER="aizavod"

# Create backup directory
mkdir -p "$BACKUP_DIR"

echo "[$(date)] Starting backup..."

# === PostgreSQL dump ===
PG_BACKUP="$BACKUP_DIR/pg_${DB_NAME}_${DATE}.sql.gz"
if command -v pg_dump &> /dev/null; then
    pg_dump -U "$DB_USER" -d "$DB_NAME" | gzip > "$PG_BACKUP"
else
    # Run via Docker
    docker exec ai-altyn-postgres-1 pg_dump -U "$DB_USER" -d "$DB_NAME" | gzip > "$PG_BACKUP"
fi
echo "[$(date)] PostgreSQL backup: $PG_BACKUP ($(du -sh "$PG_BACKUP" | cut -f1))"

# === Redis RDB copy ===
REDIS_BACKUP="$BACKUP_DIR/redis_dump_${DATE}.rdb"
if docker exec ai-altyn-redis-1 redis-cli BGSAVE 2>/dev/null; then
    sleep 2
    docker cp ai-altyn-redis-1:/data/dump.rdb "$REDIS_BACKUP" 2>/dev/null || true
    if [ -f "$REDIS_BACKUP" ]; then
        echo "[$(date)] Redis backup: $REDIS_BACKUP ($(du -sh "$REDIS_BACKUP" | cut -f1))"
    fi
fi

# === Cleanup old backups ===
find "$BACKUP_DIR" -name "pg_*.sql.gz" -mtime +$RETENTION_DAYS -delete 2>/dev/null || true
find "$BACKUP_DIR" -name "redis_*.rdb" -mtime +$RETENTION_DAYS -delete 2>/dev/null || true
echo "[$(date)] Cleaned backups older than $RETENTION_DAYS days"

# === Summary ===
BACKUP_COUNT=$(ls -1 "$BACKUP_DIR" 2>/dev/null | wc -l)
BACKUP_SIZE=$(du -sh "$BACKUP_DIR" 2>/dev/null | cut -f1)
echo "[$(date)] Backup complete. $BACKUP_COUNT files, $BACKUP_SIZE total"
echo "[$(date)] RTO target: 15 min (restore from latest backup)"
echo "[$(date)] RPO target: 24 hours (daily backup)"
