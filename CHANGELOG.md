# Changelog

Todas as alterações relevantes do Construart. Formato baseado em
[Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/) e versionamento
[SemVer](https://semver.org/lang/pt-BR/).

A versão corrente está em `core/__init__.py` (`__version__`).

---

## [Não publicado]

## [0.2.0] — 2026-05-08

### Adicionado
- `external_id` (`UUIDField` único) em **Client, Supplier, Subcontractor,
  Project, Contract, Invoice, Budget, Payment** — preparação para
  integrações externas e referências estáveis em PDFs/e-mails sem expor
  a chave primária interna. Migrations `RunPython` populam registos
  pré-existentes em três passos (add nullable → backfill → unique).
- `AuditLog.ip_address`, `AuditLog.user_agent`, `AuditLog.request_id` —
  rastreio completo de quem mexeu em quê, a partir de onde, e em que
  request. `audit/middleware.py` gera `X-Request-ID` na resposta para
  correlação com Sentry.
- Endpoint `GET /healthz/` (sem login, sem CSRF, fora de `i18n_patterns`)
  para UptimeRobot / Better Stack. Devolve 200 com versão + 503 se a DB
  estiver inacessível.
- `core.__version__ = '0.2.0'` — primeira versão semântica registada.
- `scripts/backup.sh` — `pg_dump` comprimido + tarball de `media/` com
  rotação local (default 14 dias). Upload off-site fica como TODO no
  próprio script (B2 ou rclone Drive).
- `scripts/restore_test.md` — checklist trimestral de validação do
  backup.
- GitHub Actions CI (`.github/workflows/ci.yml`): `pytest`,
  `manage.py check --deploy`, `makemigrations --check --dry-run`, `ruff`
  em cada PR contra `main`.

### Alterado
- `audit/middleware.CurrentUserMiddleware` agora também guarda
  `ip`/`user_agent`/`request_id` em thread-local para os signals.

### Documentação
- `.env.example` documenta `BACKUP_DIR`, `BACKUP_RETENTION_DAYS`,
  `MEDIA_DIR`.

---

## [0.1.0] — 2026-05-07 — Sprint 1 "Não rebenta em produção"

### Adicionado
- `transaction.atomic` + `select_for_update` em `Invoice.next_number`,
  `Budget.next_number`, `Payment.save/delete`, `sync_status` de
  `Payable`/`Receivable`. Race conditions em concorrência fechadas.
- `CheckConstraint` XOR no DB: `Contract.contract_counterpart_xor`,
  `Statement.statement_origin_xor`,
  `ProjectCiawParticipant.ciaw_node_entity_xor`.
- `django-axes` (5 tentativas → 1h cooloff por par username+IP).
- `sentry-sdk[django]` — ativo se `SENTRY_DSN` estiver no env.
- Hardening de produção condicionado a `DEBUG=False`: `SECURE_*`,
  HSTS=3600s, `SECURE_SSL_REDIRECT`, `X_FRAME_OPTIONS=DENY`,
  `CSRF_TRUSTED_ORIGINS` via env.

### Alterado
- `Receivable.invoice` `on_delete` mudou de `CASCADE` para `PROTECT`.

[Não publicado]: ./compare/0.2.0...HEAD
[0.2.0]: ./tag/0.2.0
[0.1.0]: ./tag/0.1.0
