# Onboarding — Primeiro Cliente em Produção

**Sprint 5** · 2026-05-09 · Versão `0.5.0`

Checklist passo-a-passo para colocar uma instância nova do Construart em
produção no PythonAnywhere. Cada cliente = uma instância isolada (sem
multi-tenancy de software, ver `analise-roadmap.txt §11`).

Tempo estimado na primeira execução: ~2 horas. A partir do 2º cliente,
~30 min se preparar um script `provision_initial`.

---

## 0. Pré-requisitos

- [ ] Conta PythonAnywhere paga (Hacker plan, ~5 €/mês) com domínio do
      cliente (ex.: `cliente1.construart.eu` em CNAME).
- [ ] Conta SendGrid free tier (100 emails/dia) ou outro SMTP.
- [ ] Conta Sentry free tier (5k eventos/mês). Projeto Django criado.
- [ ] Conta UptimeRobot ou Better Stack free tier.
- [ ] Backup off-site decidido (Backblaze B2 ou Google Drive via rclone).

---

## 1. Provisionar a instância

### 1.1 Banco de dados Postgres

```bash
# No PythonAnywhere → Databases → Create new Postgres database
# Nome sugerido: <cliente>_construart
# Anota DATABASE_URL: postgres://user:pass@host:port/db
```

### 1.2 Clone do código

```bash
cd ~
git clone https://github.com/<org>/construart.git
cd construart
mkvirtualenv --python=python3.11 construart
pip install -r requirements.txt
```

### 1.3 `.env` — copiar de `.env.example` e preencher

Itens obrigatórios:

```env
DEBUG=False
SECRET_KEY=<gerar com python -c "import secrets; print(secrets.token_urlsafe(50))">
ALLOWED_HOSTS=cliente1.construart.eu
CSRF_TRUSTED_ORIGINS=https://cliente1.construart.eu
DATABASE_URL=postgres://...
SECURE_HSTS_SECONDS=3600

# Empresa emissora — usado em PDFs/email
COMPANY_NAME=Cliente Construções SRL
COMPANY_VAT=BE0xxxxxxxxx
COMPANY_ADDRESS=Rue X, 1
COMPANY_POSTAL_CODE=1000
COMPANY_CITY=Bruxelles
COMPANY_PHONE=+32 ...
COMPANY_EMAIL=facturation@cliente.eu
COMPANY_LEGAL_STATUS=SRL

# SMTP
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.sendgrid.net
EMAIL_PORT=587
EMAIL_HOST_USER=apikey
EMAIL_HOST_PASSWORD=SG.xxxxxxxx
EMAIL_USE_TLS=True
DEFAULT_FROM_EMAIL=facturation@cliente.eu

# Sentry
SENTRY_DSN=https://xxx@oXXXX.ingest.sentry.io/XXXX
SENTRY_ENVIRONMENT=production
SENTRY_RELEASE=construart@0.5.0

# 2FA — obrigatório em produção (já é o default quando DEBUG=False)
OTP_REQUIRED_FOR_STAFF=True

# Identificador da instância (aparece como tag no Sentry)
INSTANCE_NAME=cliente1

# Logs estruturados em JSON (preparado para Loki futuro)
LOG_FORMAT=text   # mude para 'json' quando integrar com Loki
```

### 1.4 Migrar e criar superuser inicial

```bash
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py check --deploy   # tem que sair limpo
```

Criar o superuser via URL "secreta" `/setup-inicial-4x9z/`. **Após criar
o utilizador, apague essa rota** ou proteja-a por allowlist de IP em
produção (security through obscurity é insuficiente).

### 1.5 Ativar 2FA imediatamente

Como `OTP_REQUIRED_FOR_STAFF=True`, ao primeiro login o superuser é
redirigido para `/accounts/2fa/setup/`:

1. Abre Google Authenticator (ou 1Password, Authy).
2. Escaneia o QR.
3. Confirma o código de 6 dígitos.
4. Sessão fica verificada. **Daí em diante, sem TOTP não há admin.**

> Se perder o telefone: SSH na instância, abre Django shell e elimina os
> `TOTPDevice` do utilizador (`TOTPDevice.objects.filter(user=u).delete()`).
> No próximo login será forçado novo setup.

---

## 2. Hardening — checklist

- [ ] `python manage.py check --deploy` → 0 issues.
- [ ] HTTPS forçado (PythonAnywhere → Web → Force HTTPS).
- [ ] `SECURE_HSTS_SECONDS=3600` por **2 semanas**, depois sobe para
      `31536000` (1 ano) + `SECURE_HSTS_PRELOAD=True` para entrar nas
      listas HSTS preload.
- [ ] `django-axes` ativo (ver `AXES_FAILURE_LIMIT`, default 5/1h).
- [ ] Sentry recebe um evento de teste:
      `python manage.py shell -c "import sentry_sdk; sentry_sdk.capture_message('init OK')"`.
- [ ] 2FA funciona (login + scan + verify).
- [ ] `/healthz/` devolve `200` com `version` correta.
- [ ] Email de teste enviado (admin → criar fatura draft → enviar para si próprio).

---

## 3. Monitoring externo

### 3.1 UptimeRobot (free tier)

1. Cria monitor **HTTPS** para `https://cliente1.construart.eu/healthz/`.
2. Intervalo: 5 minutos. Keyword monitoring: `"status":"ok"`.
3. Alertas: email + Telegram (opcional).

### 3.2 Sentry — alertas

1. Project Settings → Alerts → "Issue Alerts".
2. Criar regra: "An issue is first seen → email + Slack".
3. Criar regra: "An issue is seen more than 10 times in 1 hour" → urgência.

### 3.3 Better Stack (alternativa) — uptime + log drain

Equivalente a UptimeRobot mas com integração de logs (quando passarmos a
`LOG_FORMAT=json`).

---

## 4. Backup

`scripts/backup.sh` (Sprint 2) já está pronto. Configurar cron no
PythonAnywhere → Tasks:

```
0 3 * * *   /home/<user>/construart/scripts/backup.sh
```

- [ ] Backup local em `BACKUP_DIR` corre todas as noites.
- [ ] Upload off-site (B2 ou Drive) configurado dentro do script.
- [ ] **Restore test feito manualmente** (`scripts/restore_test.md`).
      Sem teste, não há backup.

---

## 5. Janela de update / política

Documentado e comunicado ao cliente:

- **Janela de manutenção:** domingos 22h–23h (Bruxelas).
- **Procedimento de deploy:**
  ```bash
  cd ~/construart
  git pull origin main
  source ~/.virtualenvs/construart/bin/activate
  pip install -r requirements.txt
  python manage.py migrate
  python manage.py collectstatic --noinput
  touch /var/www/<user>_pythonanywhere_com_wsgi.py    # reload
  ```
- **Verificação pós-deploy:** abrir `/healthz/` → 200 + version atualizada.
- **Rollback:** `git reset --hard <último commit estável>` + reload. **NÃO**
  re-rollar migrations sem backup recente.

---

## 6. Onboarding do utilizador final

- [ ] Criar `AccessProfile` "Manager" e "Financeiro" (perms via UI).
- [ ] Criar utilizadores reais. Cada um faz `/accounts/2fa/setup/` no
      primeiro login (forçado para staff; opcional para o resto).
- [ ] Configurar dados base:
  - Unidades de medida (`/catalog/units/`)
  - Categorias de produto e serviço
  - 1-2 produtos teste, 1-2 serviços teste
  - 1 cliente real, 1 obra real
- [ ] Demo: criar orçamento → aprovar (vai criar v1 imutável) → faturar
      `from_budget` → enviar PDF por email.
- [ ] Verificar que o cliente recebe o email com PDF anexo.

---

## 7. Checklist final antes de entregar credenciais

- [ ] HTTPS ativo, sem warnings.
- [ ] `check --deploy` limpo.
- [ ] 2FA exigido para staff.
- [ ] Backup automático corre + upload off-site verificado.
- [ ] UptimeRobot monitoriza `/healthz/`.
- [ ] Sentry recebe eventos de teste.
- [ ] Versão (`__version__`) bate com `SENTRY_RELEASE`.
- [ ] CHANGELOG.md tem a versão atual.
- [ ] Janela de update comunicada ao cliente.
- [ ] Rota `/setup-inicial-4x9z/` removida ou protegida.

---

## Riscos conhecidos / aceitos

- **PythonAnywhere é single-instance.** Se a VM cair, está fora até o
  PythonAnywhere repor. Aceitável para 1-3 clientes pequenos.
- **WeasyPrint** depende do GTK do PythonAnywhere. Se cair, PDFs deixam
  de gerar.
- **Sem fila de tasks.** Email síncrono. Se SMTP demorar, request demora.
- **`media/` em disco.** Sem CDN. OK até alguns GB.

A partir do 3º cliente, reabrir a Secção 11 do `analise-roadmap.txt` e
considerar Docker + multi-instância gerida.
