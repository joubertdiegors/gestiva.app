#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# Backup do Construart — pg_dump + media tarball, com rotação local.
#
# Uso (cron PythonAnywhere às 03:00 todos os dias):
#   0 3 * * * /home/<USER>/construart/scripts/backup.sh >> /home/<USER>/construart/logs/backup.log 2>&1
#
# Variáveis esperadas no environment (defina no .env do projecto e exporte
# no início do cron via `set -a; source .env; set +a` ou em ~/.bashrc):
#   DATABASE_URL          postgres://user:pass@host:5432/dbname
#   BACKUP_DIR            ~/backups/construart   (default abaixo)
#   BACKUP_RETENTION_DAYS 14                     (default abaixo)
#   MEDIA_DIR             caminho absoluto para media/  (opcional)
#
# Off-site upload: TODO — escolher destino (B2 / rclone Drive) e adicionar
# bloco no fim deste script. Ver scripts/restore_test.md.
# ─────────────────────────────────────────────────────────────────────────────

set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-$HOME/backups/construart}"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-14}"
TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"

mkdir -p "$BACKUP_DIR"

if [[ -z "${DATABASE_URL:-}" ]]; then
    echo "[$TIMESTAMP] ERROR: DATABASE_URL not set." >&2
    exit 1
fi

DB_FILE="$BACKUP_DIR/db_${TIMESTAMP}.sql.gz"
MEDIA_FILE="$BACKUP_DIR/media_${TIMESTAMP}.tar.gz"

echo "[$TIMESTAMP] Starting pg_dump → $DB_FILE"
# --no-owner / --no-privileges: torna o dump portável entre instalações.
# pg_dump aceita URI directamente desde a 9.2.
pg_dump --no-owner --no-privileges --format=plain "$DATABASE_URL" \
    | gzip -9 > "$DB_FILE"

if [[ -n "${MEDIA_DIR:-}" && -d "$MEDIA_DIR" ]]; then
    echo "[$TIMESTAMP] Archiving media → $MEDIA_FILE"
    tar --warning=no-file-changed -czf "$MEDIA_FILE" -C "$(dirname "$MEDIA_DIR")" "$(basename "$MEDIA_DIR")"
fi

echo "[$TIMESTAMP] Pruning files older than $RETENTION_DAYS days"
find "$BACKUP_DIR" -maxdepth 1 -type f -name 'db_*.sql.gz'   -mtime +"$RETENTION_DAYS" -delete
find "$BACKUP_DIR" -maxdepth 1 -type f -name 'media_*.tar.gz' -mtime +"$RETENTION_DAYS" -delete

# ─────────────────────────────────────────────────────────────────────────────
# TODO: upload off-site.
# Escolher entre Backblaze B2 (`b2 upload-file`) ou Google Drive via rclone
# (`rclone copy "$DB_FILE" gdrive:construart-backups/`). Sem off-site o backup
# morre com a máquina — útil para crash do app, inútil para crash do disco.
# ─────────────────────────────────────────────────────────────────────────────

echo "[$TIMESTAMP] Backup OK"
