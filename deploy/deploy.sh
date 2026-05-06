#!/bin/bash
# Script de deploy para PythonAnywhere
# Executar no console Bash do PythonAnywhere:
#   cd ~/SEU_PROJETO && bash deploy/deploy.sh

set -e

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_DIR"

echo "==> Directório: $PROJECT_DIR"

echo "==> git pull..."
git pull

echo "==> Instalar dependências..."
pip install -r requirements.txt --quiet

echo "==> collectstatic..."
python manage.py collectstatic --noinput

echo "==> Migrações..."
python manage.py migrate --run-syncdb

echo ""
echo "✓ Deploy concluído. Clique em 'Reload' no painel Web do PythonAnywhere."
