# Postgres em desenvolvimento

> **Porquê?** Em produção (PythonAnywhere) corre Postgres. Localmente em
> SQLite. Algumas coisas comportam-se de forma diferente entre os dois — e
> só descobres isso quando rebenta em produção.
>
> Em particular, **`select_for_update` (usado nos `next_number()` para evitar
> faturas duplicadas) é silenciosamente ignorado em SQLite**. Os testes de
> concorrência só são honestos contra Postgres real.

Esta página documenta como subir um Postgres local em < 5 min.

---

## Opção A — Docker (recomendado)

Requer Docker Desktop instalado.

```powershell
docker run -d `
  --name construart-pg `
  -e POSTGRES_USER=construart `
  -e POSTGRES_PASSWORD=construart `
  -e POSTGRES_DB=construart `
  -p 5432:5432 `
  postgres:16
```

Para parar / reiniciar:

```powershell
docker stop construart-pg
docker start construart-pg
```

Para apagar e recomeçar do zero (apaga TODOS os dados):

```powershell
docker rm -f construart-pg
```

---

## Opção B — Postgres.app (macOS) / instalador nativo (Windows)

- macOS: <https://postgresapp.com/>
- Windows: <https://www.postgresql.org/download/windows/>

Após instalar, criar a base e o utilizador:

```sql
CREATE USER construart WITH PASSWORD 'construart';
CREATE DATABASE construart OWNER construart;
```

---

## Configurar o `.env`

Adicionar (ou descomentar) no `.env`:

```ini
DATABASE_URL=postgres://construart:construart@localhost:5432/construart
```

O `core/settings.py` já está preparado: se `DATABASE_URL` estiver definido,
usa Postgres; caso contrário cai em SQLite.

---

## Migrar dados existentes do SQLite (opcional)

Se já tens dados no `db.sqlite3` e quiseres preservá-los:

```powershell
# 1. Ainda em SQLite (DATABASE_URL vazio no .env), exporta:
python manage.py dumpdata `
  --natural-foreign --natural-primary `
  --exclude=contenttypes --exclude=auth.Permission `
  --indent=2 -o backup.json

# 2. Aponta DATABASE_URL para Postgres no .env. Aplica migrations:
python manage.py migrate

# 3. Carrega os dados:
python manage.py loaddata backup.json
```

---

## Verificar que estás mesmo em Postgres

```powershell
python manage.py dbshell
```

Deve abrir um prompt `construart=#`. Se abrir `sqlite>`, ainda estás em
SQLite — confirma o `.env`.

Ou no shell Django:

```python
from django.db import connection
print(connection.vendor)   # 'postgresql' ✓
```
