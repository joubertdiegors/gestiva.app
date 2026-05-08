# Restore test — checklist manual

> **Why:** um backup que nunca foi restaurado é uma fé, não uma garantia.
> Correr este procedimento pelo menos **uma vez por trimestre**, ou após
> qualquer mudança em `scripts/backup.sh` ou na infraestrutura de DB.

## 1. Preparar ambiente isolado

Não restaurar sobre a base de produção. Criar uma DB descartável:

```bash
createdb construart_restore_test
```

Ou, se estiver em Docker local:

```bash
docker run --rm -d --name pg_restore_test \
    -e POSTGRES_PASSWORD=test -p 55432:5432 postgres:16
```

## 2. Obter o dump mais recente

No PythonAnywhere:

```bash
ls -lh ~/backups/construart/db_*.sql.gz | tail -n 5
```

Copiar o ficheiro para a máquina onde se vai testar o restore.

## 3. Restaurar

```bash
gunzip -c db_YYYYMMDDTHHMMSSZ.sql.gz | psql "$RESTORE_DATABASE_URL"
```

Esperar 0 erros no fim. Avisos sobre `extension` ou `role` já existentes
podem ser ignorados — o `--no-owner --no-privileges` no `pg_dump` foi
escolhido precisamente para isso.

## 4. Verificar integridade

Correr o `manage.py` apontado para a DB restaurada:

```bash
DATABASE_URL="$RESTORE_DATABASE_URL" python manage.py check
DATABASE_URL="$RESTORE_DATABASE_URL" python manage.py showmigrations | tail -n 20
DATABASE_URL="$RESTORE_DATABASE_URL" python manage.py shell -c "
from invoicing.models import Invoice
from finance.models import Payment, Receivable
from clients.models import Client
print('Clients:    ', Client.objects.count())
print('Invoices:   ', Invoice.objects.count())
print('Receivables:', Receivable.objects.count())
print('Payments:   ', Payment.objects.count())
"
```

Comparar com os números de produção (`/admin/` ou query directa). Devem
bater dentro da janela do dump.

## 5. Smoke test funcional

- Login com superuser conhecido.
- Abrir lista de Faturas — devem aparecer as últimas registadas.
- Abrir uma Receivable e validar `amount_paid` / `status`.

## 6. Limpar

```bash
dropdb construart_restore_test
# ou
docker stop pg_restore_test
```

## 7. Registar no CHANGELOG

Mencionar a data do último restore-test. Se algum passo falhou, registar
o motivo e bloquear deploys até corrigir.
