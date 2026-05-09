# Changelog

Todas as alterações relevantes do Construart. Formato baseado em
[Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/) e versionamento
[SemVer](https://semver.org/lang/pt-BR/).

A versão corrente está em `core/__init__.py` (`__version__`).

---

## [Não publicado]

## [0.5.0] — 2026-05-09 — Sprint 5 "1º cliente em produção"

### Adicionado
- **2FA TOTP via `django-otp`**:
  - Novos apps: `django_otp`, `django_otp.plugins.otp_totp`,
    `django_otp.plugins.otp_static`. `OTPMiddleware` aplica `is_verified()`
    em `request.user`.
  - **`accounts.middleware.OTPGateMiddleware`** força staff/superusers sem
    sessão verificada a passar por `/accounts/2fa/setup/` ou
    `/accounts/2fa/verify/`. Default em produção; `OTP_REQUIRED_FOR_STAFF`
    pode ser desligado em DEV.
  - Páginas auto-serviço:
    - `GET/POST /accounts/2fa/setup/` — QR code TOTP + confirmação.
    - `GET/POST /accounts/2fa/verify/` — verificação por sessão.
    - `POST /accounts/2fa/disable/` — só com sessão já verificada.
  - Decorador `accounts.decorators.otp_required(force=False)` para proteger
    pontualmente views super-sensíveis (default protege staff/superuser).
  - Settings: `OTP_REQUIRED_FOR_STAFF` (default = `not DEBUG`),
    `OTP_TOTP_ISSUER` (aparece na app authenticator).
- **Versioning de orçamentos (lock + snapshot imutável)**:
  - Campos novos em `Budget`: `is_locked` (db_index), `locked_at`,
    `locked_by` (FK User SET_NULL).
  - Modelo novo `budget.BudgetVersion` (`budget`, `version_number`,
    `locked_at`, `locked_by`, `reason`, `snapshot=JSONField`). Unique
    `(budget, version_number)`.
  - `budget.services.lock_budget(budget, user, reason=...)` —
    cria `BudgetVersion` com `snapshot_budget()` (cabeçalho + capítulos +
    linhas + materiais + totais). Idempotente.
  - `unlock_budget(budget, user)` — limpa flags. As versões anteriores
    ficam preservadas; próximo lock cria v(N+1).
  - `assert_editable(budget)` lança `BudgetLockedError` se locked.
  - Views `budget_update`, `chapter_save/delete`, `item_save/delete`
    rejeitam mutações em orçamentos locked (HTTP 409 nas AJAX, redirect
    com mensagem nas non-AJAX).
  - Action `POST /budget/<pk>/approve/` muda status para APPROVED + lock
    (uma só transação) + cria v1.
  - Action `POST /budget/<pk>/unlock/` reabre.
  - Páginas `/budget/<pk>/versions/` e `/budget/<pk>/versions/<n>/` para
    histórico read-only.
- **Monitoring básico**:
  - Sentry `before_send` enriquece eventos com `request_id` (do
    `audit/middleware.py`) e `instance` (`INSTANCE_NAME` em settings).
    Permite cruzar Sentry ↔ logs ↔ resposta HTTP.
  - `core/logging_json.py::JSONFormatter` opt-in via `LOG_FORMAT=json`.
    Inclui `request_id` automaticamente. Pronto para Loki sem refactor.
- **`docs/onboarding-cliente.md`**: checklist passo-a-passo para colocar
  uma instância nova em produção no PythonAnywhere (Postgres, .env,
  hardening, 2FA, UptimeRobot, Sentry, backup, janela de update).
- **16 testes pytest novos** em `tests/test_sprint5.py`:
  - Lock idempotente, unlock + re-lock cria v2, snapshot imutável.
  - `assert_editable` lança quando locked.
  - View `budget_approve` define APPROVED + lock + cria v1 numa transação.
  - View `item_save` devolve 409 em orçamento locked.
  - `OTPGateMiddleware`: redireciona staff sem TOTP, isenta `/healthz/`,
    no-op em DEV.
  - Decorador `otp_required`: redireciona unverified, passa verified,
    no-op em DEV.

### Alterado
- `requirements.txt`: adicionados `django-otp==1.5.4`, `qrcode==7.4.2`.
- `core/__init__.py`: `__version__ = '0.5.0'`.
- `core/settings.py`: settings `LOG_FORMAT`, `OTP_REQUIRED_FOR_STAFF`,
  `OTP_TOTP_ISSUER`. Sentry `before_send` adiciona tags `request_id` e
  `instance`. `INSTANCE_NAME` lido do .env.
- `.env.example`: documenta `OTP_REQUIRED_FOR_STAFF`, `OTP_TOTP_ISSUER`,
  `LOG_FORMAT`, `INSTANCE_NAME`.
- `budget/templates/budget/budget_detail.html`: badge "🔒 Bloqueado",
  botões "Aprovar e bloquear" / "Desbloquear" / "Versões".

### Migrations
- `budget.0006_budget_is_locked_budget_locked_at_budget_locked_by_and_more`
  (`is_locked`, `locked_at`, `locked_by`, `BudgetVersion`).
- `otp_static.0001..0003`, `otp_totp.0001..0003` (django-otp).

### Notas operacionais
- Em DEV, `OTP_REQUIRED_FOR_STAFF` é `False` por default — desenvolvimento
  local não exige 2FA. Em produção (`DEBUG=False`) entra automaticamente.
- Para cancelar o 2FA de um utilizador que perdeu o telefone:
  `TOTPDevice.objects.filter(user=u).delete()` no Django shell.
- WeasyPrint continua a precisar de GTK em produção. A geração de PDF de
  versões antigas (snapshot) **não foi adicionada neste sprint** — quando
  precisar, gerar a partir do `BudgetVersion.snapshot` em vez do estado
  vivo.

---

## [0.4.0] — 2026-05-09 — Sprint 4 "Pronto para vender"

### Adicionado
- **WeasyPrint para PDFs server-side**:
  - Endpoint `GET /invoicing/<pk>/pdf/` devolve `application/pdf` reutilizando
    o template `invoice_print.html` (flag `is_pdf=True` esconde toolbar/script
    e aplica `@page A4`). `?inline=1` mostra inline em iframe.
  - Endpoint `GET /budget/<pk>/pdf/` com template dedicado `budget_pdf.html`
    que respeita capítulos via `{% regroup %}`.
- **Email síncrono de fatura**:
  - `POST /invoicing/<pk>/email/` (`invoice_send_email`) gera o PDF, anexa-o
    e envia por SMTP. Marca a fatura como `SENT` e cria `Receivable` no
    sucesso. Falha de SMTP devolve 502 sem rebentar a transação.
  - `invoicing/tasks.py::send_invoice_email_task(invoice_id, to=[...])` —
    assinatura "fingida-Celery": recebe IDs, é idempotente, fácil de
    `@shared_task` no futuro.
  - Configuração via env: `EMAIL_BACKEND`, `EMAIL_HOST`, `EMAIL_PORT`,
    `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `EMAIL_USE_TLS`,
    `DEFAULT_FROM_EMAIL`, `EMAIL_TIMEOUT`, mais bloco `COMPANY_*` para
    cabeçalho dos PDFs.
  - Template `invoicing/templates/invoicing/email/invoice_body.txt`.
- **`SoftDeleteMixin` em `core/models.py`** (`is_deleted`, `deleted_at`,
  `deleted_by`) com `objects` (vivos) + `all_objects` (todos) e métodos
  `delete(hard=False)` / `restore()`. Aplicado a **Client, Supplier,
  Subcontractor, Project, Invoice, Budget** (6 migrations). Apoia retenção
  fiscal belga 7-10 anos sem perder histórico.
- **Validação VAT BE com `python-stdnum`**: `Client.clean()`,
  `Supplier.clean()`, `Subcontractor.clean()` rejeitam VAT inválido e
  normalizam para `BE0XXXXXXXXX` (helper `core/validators.py`).
- **Wizard de fatura — fluxos `from_budget` e `credit_note`**:
  - `invoicing.services.create_invoice_from_budget(budget, user)` copia
    linhas (com `effective_unit_price`) e adiciona linhas-título por
    capítulo. `Invoice.budget` é preenchido para rastreabilidade.
  - `invoicing.services.create_credit_note_from_invoice(origin, user)` cria
    nota de crédito com quantidades **negadas** (totais saem negativos
    automaticamente) e `credit_note_origin` apontando à fatura origem
    (`PROTECT`).
  - View `invoice_create` deteta `?type=from_budget&budget=<id>` e
    `?type=credit_note&origin=<id>` e cria + redireciona para detalhe.
- **`Invoice.credit_note_origin`** (FK reflexivo, `PROTECT`).
- **16 testes pytest novos** em `tests/test_sprint4.py`: soft delete
  (manager default + restore + bulk + hard), validação VAT BE,
  `create_invoice_from_budget` (preço efetivo + numeração),
  `create_credit_note_from_invoice` (quantidade negada + total mirrored).

### Alterado
- `requirements.txt`: adicionados `weasyprint==62.3` e `python-stdnum==1.20`.
- `factories.ClientFactory.vat_number` e `SubcontractorFactory.vat_number`
  passaram a `None` por defeito (a validação BE só corre via `full_clean()`;
  testes específicos de VAT atribuem números válidos).

### Notas operacionais
- **WeasyPrint no Windows** requer GTK runtime. Em PythonAnywhere já vem
  instalado. Os testes locais não exercitam a geração de PDF nem o envio
  SMTP — confirmar manualmente no staging do PythonAnywhere.

---

## [0.3.0] — 2026-05-08 — Sprint 3 "Confiar nos números"

### Adicionado
- **Camada de serviço incremental**: `invoicing/services.py`
  (`compute_invoice_totals`, `ensure_receivable_for_invoice`),
  `finance/services.py` (`sync_payable_status`, `sync_receivable_status`),
  `budget/services.py` (`compute_item_unit_price`,
  `compute_budget_totals`). Regras de negócio críticas extraídas das views
  para serem testadas em isolamento.
- **Suite de testes pytest + factory-boy** em `tests/` (50 testes,
  cobertura ~90% em `invoicing/models.py`, `finance/models.py`,
  `budget/models.py`, `timesheets/models.py` e 100% nos novos
  `services.py`). Cobre Invoice totals, Payment sync,
  Payable/Receivable status, BudgetItem computed price, Timesheet
  effective rate / hourly_rate snapshot.
- Dependências de dev: `factory-boy>=3.3`, `pytest-cov>=5.0`.

### Alterado
- **`Timesheet` é agora a fonte única de mão-de-obra**. `ProjectLabourEntry`
  removido; a vista do projecto (`labour_save`/`labour_delete` e o tab
  "Mão-de-obra" em `project_detail.html`) opera directamente sobre
  `Timesheet`. Migration `projects.0007_drop_projectlabourentry` copia
  cada entrada para `Timesheet` (preservando rate como
  `hourly_rate_snapshot` e multiplicador como `overtime_rate`) e remove o
  modelo a seguir.
- `audit/signals.is_migration_running` deteta também `pytest` para evitar
  que os signals tentem gravar `AuditLog` antes de a sua tabela existir
  durante o setup do teste.

### Removido
- `projects.ProjectLabourEntry` (modelo + view fields). Dados existentes
  migrados via `RunPython`.

---

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

[Não publicado]: ./compare/0.5.0...HEAD
[0.5.0]: ./tag/0.5.0
[0.4.0]: ./tag/0.4.0
[0.3.0]: ./tag/0.3.0
[0.2.0]: ./tag/0.2.0
[0.1.0]: ./tag/0.1.0
