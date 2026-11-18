# InfoBeans Agent Hub — Deployment Guide

How to run the Agent Hub and its agents **locally** (Windows) and in **production** (Linux server), and how to ship **code updates** afterwards.

---

## Contents

1. [How it fits together](#1-how-it-fits-together)
2. [Repository layout](#2-repository-layout)
3. [Configuration files](#3-configuration-files)
4. [Local setup (Windows)](#4-local-setup-windows)
5. [Production: first-time deployment](#5-production-first-time-deployment)
6. [Production: future code updates](#6-production-future-code-updates)
7. [Operations: logs, restarts, key rotation](#7-operations-logs-restarts-key-rotation)
8. [Troubleshooting](#8-troubleshooting)
9. [Handover: open items](#9-handover-open-items)

---

## 1. How it fits together

```
Browser ──► https://agenthub.creatingwow.in
              │
            reverse proxy   (production: nginx · local: Caddy)
              ├─ /ppt-validator/*  ─┐  ask the hub: /internal/auth/proposal-validator/
              ├─ /api/v2/*         ─┴► PPT Validator        127.0.0.1:8001
              ├─ /case-study*      ──► ask the hub: /internal/auth/case-study-creation/
              │                        Case Study service   127.0.0.1:8003
              └─ everything else   ──► Django hub           (local :8000 · production :8002)
```

- **The hub owns sign-in and access.** Users sign in with Google on the hub. Before forwarding any agent request, the proxy asks the hub whether the user may use that agent. The hub answers `200` (with the user's identity), `401` (not signed in → login page) or `403` (no access → dashboard).
- **Agents trust the hub.** The proxy passes `X-Auth-User-Id`, `X-Auth-Email` and `X-Auth-Name` to the agent. Agents listen only on `127.0.0.1`, so these headers cannot be forged from outside.
- **Card slugs are part of the routing.** The proxy's access checks use the app slugs below. Never rename them.

| Agent | Card slug | Launch URL | Port |
|---|---|---|---|
| PPT Validator ("Proposal validator") | `proposal-validator` | `https://agenthub.creatingwow.in/ppt-validator/app/` | 8001 |
| Case Study Creator | `case-study-creation` | `https://agenthub.creatingwow.in/case-study/` | 8003 |

### Ports

| Port | Local | Production |
|---|---|---|
| 8000 | Django hub (`runserver`) | Legacy FastAPI hub (stopped; to be disabled) |
| 8001 | PPT Validator | PPT Validator |
| 8002 | — | Django hub (gunicorn) |
| 8003 | Case Study service | Case Study service |
| 443 | Caddy | nginx |

---

## 2. Repository layout

```
poc/
├── agenthub/              # Django project settings, urls, wsgi
├── accounts/              # sign-in (Google), users, groups, signup rules
├── hub/                   # apps, grants, access checks, dashboard
├── templates/  static/    # hub pages and styles
├── apps/
│   ├── ppt_validator/     # PPT Validator (FastAPI) — own venv, own .env
│   └── case_study/        # Case Study service (FastAPI) — own venv, own .env
├── deploy/                # Caddyfile.local, nginx-agenthub.conf, systemd units
├── .env.example           # hub settings (names only)
├── .env.shared.example    # secrets shared by the agents (names only)
├── requirements.txt       # hub packages only
└── manage.py
```

Each part has **its own Python environment** and its own `requirements.txt`. Never install one part's requirements into another's environment.

---

## 3. Configuration files

None of these are committed; each has a committed `*.example` with the names.

| File | Used by | Contains |
|---|---|---|
| `.env` | Django hub | `DJANGO_SECRET_KEY`, `DJANGO_DEBUG`, `DJANGO_ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, `GOOGLE_CLIENT_ID`, `GOOGLE_ALLOWED_DOMAINS`, `SQLITE_PATH` (production) |
| `.env.shared` (local) / `/etc/agenthub/shared.env` (production) | Both agents | `ANTHROPIC_API_KEY`, `ANTHROPIC_AUTH_TOKEN`, `ANTHROPIC_BASE_URL` (the LLM gateway) |
| `apps/ppt_validator/.env` | PPT Validator | Its own settings: `LLM_PROVIDER` (currently `groq`), models, limits, timeouts, `DATABASE_URL`, `GROQ_API_KEY`, `GROQ_MODEL`, `LANGSMITH_*`. **No** `ANTHROPIC_*` lines. |
| `apps/case_study/.env` | Case Study | `CASE_STUDY_LLM_MODEL=claude-sonnet-5` (must be a model the gateway key allows; see 7.2) |

**Rule:** a secret used by **both** agents lives only in the shared file. Settings and secrets used by one app stay in that app's `.env`. The shared file is loaded into the process environment at startup (`--env-file` locally, `EnvironmentFile=` in production), and environment variables take priority over an app's own `.env`.

---

## 4. Local setup (Windows)

Local runs use the production address on your laptop, because the official Google OAuth client only accepts sign-ins from `https://agenthub.creatingwow.in`.

> **While the hosts entry (4.9) is active, `agenthub.creatingwow.in` on your laptop means your local copy, not production.** See 4.13 to switch.

Use **cmd** for the commands below. `<you>` = your Windows user folder name.

### 4.1 Prerequisites

| Tool | Check |
|---|---|
| Python 3.12 | `py -0p` lists 3.12 |
| Git | `git --version` |
| Node.js (only to build the validator UI) | `node --version` |
| Caddy (approved by IT) | `caddy version` |

### 4.2 Get the code

```cmd
cd C:\Users\<you>\Desktop
git clone https://github.com/<owner>/<repo>.git poc
cd poc
```

### 4.3 Django hub

```cmd
cd C:\Users\<you>\Desktop\poc
py -3.12 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
copy .env.example .env
notepad .env
```

Local `.env`:

```ini
DJANGO_SECRET_KEY=<generate: .venv\Scripts\python.exe -c "import secrets; print(secrets.token_urlsafe(50))">
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=agenthub.creatingwow.in,localhost,127.0.0.1
CSRF_TRUSTED_ORIGINS=https://agenthub.creatingwow.in
GOOGLE_CLIENT_ID=<official client id>.apps.googleusercontent.com
GOOGLE_ALLOWED_DOMAINS=
```

```cmd
.venv\Scripts\python.exe manage.py migrate
.venv\Scripts\python.exe manage.py createsuperuser
.venv\Scripts\python.exe -m pytest -q
```

Use your Google email as both username and email in `createsuperuser`, so your first Google sign-in links to that account.

✅ All tests pass.

### 4.4 Shared secrets file

```cmd
cd C:\Users\<you>\Desktop\poc
copy .env.shared.example .env.shared
notepad .env.shared
```

Fill in `ANTHROPIC_API_KEY`, `ANTHROPIC_AUTH_TOKEN` (if used) and `ANTHROPIC_BASE_URL` (the bare gateway address, without `/v1`).

✅ `git check-ignore -v .env.shared` prints the `.env.*` rule (the file is ignored).

### 4.5 PPT Validator

```cmd
cd C:\Users\<you>\Desktop\poc\apps\ppt_validator
py -3.12 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
copy .env.example .env
notepad .env
```

In its `.env`, keep the validator's own settings and **remove** any `ANTHROPIC_API_KEY`, `ANTHROPIC_AUTH_TOKEN` and `ANTHROPIC_BASE_URL` lines (they come from `.env.shared`). Make sure `DATABASE_URL` points to a local path, for example `sqlite:///platform.db`.

One-time database setup:

```cmd
.venv\Scripts\python.exe -c "from db.migrate import run; run()"
```

**Build the UI** (the built files are not in git). The base path **must** be `/ppt-validator/app/`, which the proxy routes expect:

```cmd
cd frontend
npm install
npx vite build --base=/ppt-validator/app/
findstr /i "assets" dist\index.html
cd ..
```

✅ Every asset path in `dist\index.html` starts with `/ppt-validator/app/assets/`.

### 4.6 Case Study service

```cmd
cd C:\Users\<you>\Desktop\poc\apps\case_study
py -3.12 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
copy .env.example .env
.venv\Scripts\python.exe -m pytest -q
```

In `apps\case_study\.env`, set `CASE_STUDY_LLM_MODEL=claude-sonnet-5`.

✅ All tests pass.

### 4.7 Caddy configuration

Use `deploy\Caddyfile.local` (copy it next to `caddy.exe`, named `Caddyfile`):

```
(hub_auth) {
    forward_auth localhost:8000 {
        uri /internal/auth/{args[0]}/
        copy_headers X-Auth-User-Id X-Auth-Email X-Auth-Name
    }
}

agenthub.creatingwow.in {
    tls internal

    # PPT Validator UI (built for /ppt-validator/app/): strip the prefix
    handle_path /ppt-validator/* {
        import hub_auth proposal-validator
        reverse_proxy localhost:8001
    }

    # PPT Validator API (path kept)
    handle /api/v2/* {
        import hub_auth proposal-validator
        request_body {
            max_size 50MB
        }
        reverse_proxy localhost:8001 {
            transport http {
                read_timeout 300s
            }
        }
    }

    # Case Study service (path kept)
    handle /case-study* {
        import hub_auth case-study-creation
        reverse_proxy localhost:8003 {
            transport http {
                read_timeout 120s
            }
        }
    }

    # Everything else: the Django hub
    handle {
        reverse_proxy localhost:8000
    }
}
```

### 4.8 Trust Caddy's local certificate (once)

Start Caddy once (4.10, terminal 4). If Windows does not prompt to install its certificate, run in a second admin terminal while it is running:

```cmd
caddy trust
```

### 4.9 Point the domain at your laptop

Notepad **as Administrator** → open `C:\Windows\System32\drivers\etc\hosts` (file filter: All Files) → add:

```
127.0.0.1  agenthub.creatingwow.in
```

```cmd
ipconfig /flushdns
ping -n 1 agenthub.creatingwow.in
```

✅ Replies from `127.0.0.1`.

### 4.10 Start everything (four terminals)

```cmd
:: 1 — Django hub (poc)
.venv\Scripts\python.exe manage.py runserver 8000

:: 2 — PPT Validator (poc\apps\ppt_validator)
.venv\Scripts\python.exe -m uvicorn app:app --host 127.0.0.1 --port 8001 --reload --env-file ..\..\.env.shared

:: 3 — Case Study (poc\apps\case_study)
.venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8003 --reload --env-file ..\..\.env.shared

:: 4 — Caddy (folder with the Caddyfile)
caddy run
```

### 4.11 Dashboard cards and access

Open `https://agenthub.creatingwow.in/admin/` → **Apps**:

| Card | Slug | Launch URL |
|---|---|---|
| Proposal validator | `proposal-validator` | `https://agenthub.creatingwow.in/ppt-validator/app/` |
| Case study creation | `case-study-creation` | `https://agenthub.creatingwow.in/case-study/` |

Grant yourself access (Users → you → Apps, or via a Group).

### 4.12 Verify

- [ ] `https://agenthub.creatingwow.in` shows the hub login; Google sign-in reaches the dashboard
- [ ] Proposal validator → Launch → a PPT review completes
- [ ] Case study creation → Launch → generate works → Download PPT gives a `.pptx`
- [ ] A user without access is returned to the dashboard

Opening an agent directly on its port (`http://localhost:8001/app/`, `http://localhost:8003/case-study/`) shows broken assets or `401`. That is expected: always go through the hub.

### 4.13 Switching between local and production

| You want | Do this |
|---|---|
| Local | Hosts line active; all four processes running |
| Real production site | Put `#` before the hosts line → `ipconfig /flushdns` → clear `chrome://net-internals/#dns` → reopen the browser |

Which one am I on? F12 → Network → first request → **Remote Address**. `127.0.0.1:443` = local.

---

## 5. Production: first-time deployment

### 5.1 Server facts

| Item | Value |
|---|---|
| Server | `144.79.8.82`, SSH port `28274`, user `infoadmin` |
| Hub code (git checkout, branch `main`) | `/var/www/html/agenthub-django` |
| Hub settings | `/var/www/html/agenthub-django/.env` (owner `infoadmin`, group `www-data`, mode 640) |
| Hub database | `/var/lib/agenthub/db.sqlite3` |
| Hub service | `agenthub-django` — gunicorn on `127.0.0.1:8002`, user `www-data` |
| Case Study service | `agenthub-case-study` — uvicorn on `127.0.0.1:8003`, folder `/var/www/html/agenthub-django/apps/case_study` |
| Shared secrets | `/etc/agenthub/shared.env` (owner `root`, group `www-data`, mode 640) |
| PPT Validator | `infobeans-ppt-validator` on `127.0.0.1:8001`, folder `/var/www/html/ib-ppt-validator` (**separate from the repo**; see 6.5) |
| Legacy hub | `infobeans-agent-hub` (FastAPI, port 8000) — stopped since 13 Nov 2026 |
| nginx site | `/etc/nginx/sites-available/agenthub` (symlinked from `sites-enabled`) |
| nginx copies | `agenthub.before-django` (original) · `agenthub.with-django` (current) |

### 5.2 Before you start (laptop)

1. Everything is merged into `main` and pushed: `git status -sb` shows `## main...origin/main` with no `[ahead …]`.
2. Tests pass (hub and case study).
3. Your hosts entry is **off** (4.13), so the browser tests hit production.

### 5.3 Log in

```cmd
ssh -p 28274 infoadmin@144.79.8.82
```

```bash
sudo -v && echo "sudo OK"
```

### 5.4 Pre-flight checks (read-only)

```bash
systemctl is-active infobeans-ppt-validator nginx
sudo ss -tlnp | grep -E ":(8001|8002|8003) "
ls -l /etc/nginx/sites-available/
```

✅ Validator and nginx `active`; port 8001 in use; 8002 and 8003 free (first install).

### 5.5 Get the code

First install:

```bash
sudo mkdir -p /var/www/html/agenthub-django
sudo chown $USER:$USER /var/www/html/agenthub-django
cd /var/www/html/agenthub-django
git clone https://github.com/<owner>/<repo>.git .
git config credential.helper 'cache --timeout=3600'
```

At the password prompt, paste a GitHub fine-grained token (this repository only, **Contents: Read-only**).

✅ `ls` shows `manage.py`, `agenthub`, `hub`, `accounts`, `apps`; `ls -la` shows no `.env` yet.

> On Linux, `ls` hides names starting with a dot. Use `ls -la` to see `.env` and `.venv`.

### 5.6 Hub: environment, settings, database

```bash
cd /var/www/html/agenthub-django
python3 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt
.venv/bin/python -c "import secrets; print(secrets.token_urlsafe(50))"
nano .env
```

Production `.env`:

```ini
DJANGO_SECRET_KEY=<the key just printed>
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=agenthub.creatingwow.in,127.0.0.1,localhost
CSRF_TRUSTED_ORIGINS=https://agenthub.creatingwow.in
GOOGLE_CLIENT_ID=<official client id>.apps.googleusercontent.com
GOOGLE_ALLOWED_DOMAINS=
SQLITE_PATH=/var/lib/agenthub/db.sqlite3
```

```bash
sudo chown $USER:www-data .env && chmod 640 .env
sudo mkdir -p /var/lib/agenthub
sudo chown www-data:www-data /var/lib/agenthub && sudo chmod 750 /var/lib/agenthub
sudo -u www-data .venv/bin/python manage.py check --deploy
```

✅ `System check identified no issues (1 silenced).` Do not continue until it does.

```bash
sudo -u www-data .venv/bin/python manage.py migrate
.venv/bin/python manage.py collectstatic --noinput
sudo -u www-data .venv/bin/python manage.py createsuperuser
```

### 5.7 Shared secrets

Copied from the validator's existing config, so the key is never typed or shown:

```bash
sudo mkdir -p /etc/agenthub
sudo grep -E '^ANTHROPIC_(API_KEY|AUTH_TOKEN|BASE_URL)=' /var/www/html/ib-ppt-validator/.env \
  | sudo tee /etc/agenthub/shared.env > /dev/null
sudo chown root:www-data /etc/agenthub/shared.env
sudo chmod 640 /etc/agenthub/shared.env
sudo cut -d= -f1 /etc/agenthub/shared.env
```

✅ Prints only the variable names.

### 5.8 Case Study service

```bash
cd /var/www/html/agenthub-django/apps/case_study
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -c "import fastapi, httpx, jinja2, pptx, dotenv; print('packages OK')"
printf 'CASE_STUDY_LLM_MODEL=claude-sonnet-5\n' > .env
sudo chown $USER:www-data .env && chmod 640 .env
```

`/etc/systemd/system/agenthub-case-study.service` (also kept in `deploy/`):

```bash
sudo tee /etc/systemd/system/agenthub-case-study.service > /dev/null <<'EOF'
[Unit]
Description=InfoBeans Case Study Creator (FastAPI)
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/html/agenthub-django/apps/case_study
EnvironmentFile=/etc/agenthub/shared.env
ExecStart=/var/www/html/agenthub-django/apps/case_study/.venv/bin/uvicorn main:app --host 127.0.0.1 --port 8003 --workers 2
Restart=on-failure
RestartSec=5
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
EOF
sudo systemctl daemon-reload
sudo systemctl enable --now agenthub-case-study
sleep 5
curl -s http://127.0.0.1:8003/case-study/health; echo
curl -s -o /dev/null -w "Page without hub: %{http_code}\n" http://127.0.0.1:8003/case-study/
```

✅ `{"status":"ok"}` and `Page without hub: 401`.

### 5.9 Django hub service

`/etc/systemd/system/agenthub-django.service` (also kept in `deploy/`):

```bash
sudo tee /etc/systemd/system/agenthub-django.service > /dev/null <<'EOF'
[Unit]
Description=InfoBeans Agent Hub (Django)
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/html/agenthub-django
ExecStart=/var/www/html/agenthub-django/.venv/bin/gunicorn agenthub.wsgi:application \
    --bind 127.0.0.1:8002 \
    --workers 3 \
    --timeout 60 \
    --access-logfile - \
    --error-logfile -
Restart=on-failure
RestartSec=5
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
EOF
sudo systemctl daemon-reload
sudo systemctl enable --now agenthub-django
sleep 5
H='-H Host:agenthub.creatingwow.in -H X-Forwarded-Proto:https'
curl -s -o /dev/null -w "Dashboard:     %{http_code}\n" $H http://127.0.0.1:8002/
curl -s -o /dev/null -w "Login:         %{http_code}\n" $H http://127.0.0.1:8002/accounts/login/
curl -s -o /dev/null -w "CSS:           %{http_code}\n" $H http://127.0.0.1:8002/static/css/hub.css
curl -s -o /dev/null -w "Auth PPT:      %{http_code}\n" $H http://127.0.0.1:8002/internal/auth/proposal-validator/
curl -s -o /dev/null -w "Auth CaseStdy: %{http_code}\n" $H http://127.0.0.1:8002/internal/auth/case-study-creation/
```

✅ `302`, `200`, `200`, `401`, `401`.

### 5.10 Dashboard cards and first access

Replace `YOUR_EMAIL`:

```bash
cd /var/www/html/agenthub-django
sudo -u www-data .venv/bin/python manage.py shell -c "
from django.contrib.auth import get_user_model
from hub.models import App, AppGrant
cards = {
    'proposal-validator':  ('Proposal validator',  'https://agenthub.creatingwow.in/ppt-validator/app/'),
    'case-study-creation': ('Case study creation', 'https://agenthub.creatingwow.in/case-study/'),
}
me = get_user_model().objects.get(email__iexact='YOUR_EMAIL')
for slug, (name, url) in cards.items():
    app, _ = App.objects.update_or_create(slug=slug, defaults={'name': name, 'launch_url': url, 'is_active': True})
    AppGrant.objects.get_or_create(app=app, user=me)
    print('OK', slug, '->', url)
"
```

### 5.11 nginx configuration

Prepare the new config as a separate file first (not live yet):

```bash
sudo cp /etc/nginx/sites-available/agenthub.before-django /etc/nginx/sites-available/agenthub.with-django
sudo nano /etc/nginx/sites-available/agenthub.with-django
```

Inside the `listen 443 ssl` server block:

1. **Delete** the legacy blocks: `location = /case-study { … }`, `location = /ppt-validator/app { … }` and `location ~ ^/(api/v[12]/)(.*)$ { … }`. The regex one would otherwise capture every `/api/v2/` request.
2. In `location / { … }`, set `proxy_pass http://127.0.0.1:8002;`. Keep its `proxy_set_header Host $host;` and `proxy_set_header X-Forwarded-Proto …;` lines; without them Django redirects forever.
3. Paste this block **above** `location / {` (the full file is kept in `deploy/nginx-agenthub.conf`):

```nginx
    # ═══ Agents behind the Django hub ═══════════════════════════════════

    # Access checks: the hub answers 200 (+ identity), 401 or 403
    location = /_hub_auth_ppt {
        internal;
        proxy_pass http://127.0.0.1:8002/internal/auth/proposal-validator/;
        proxy_method GET;
        proxy_pass_request_body off;
        proxy_set_header Content-Length "";
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Proto https;
    }
    location = /_hub_auth_case_study {
        internal;
        proxy_pass http://127.0.0.1:8002/internal/auth/case-study-creation/;
        proxy_method GET;
        proxy_pass_request_body off;
        proxy_set_header Content-Length "";
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Proto https;
    }

    # PPT Validator UI (built for /ppt-validator/app/): strip /ppt-validator
    location /ppt-validator/ {
        auth_request /_hub_auth_ppt;
        auth_request_set $hub_user_id $upstream_http_x_auth_user_id;
        auth_request_set $hub_email   $upstream_http_x_auth_email;
        auth_request_set $hub_name    $upstream_http_x_auth_name;
        error_page 401 = @hub_login;
        error_page 403 = @hub_home;
        proxy_set_header X-Auth-User-Id $hub_user_id;
        proxy_set_header X-Auth-Email   $hub_email;
        proxy_set_header X-Auth-Name    $hub_name;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Proto https;
        proxy_pass http://127.0.0.1:8001/;          # trailing slash = strip prefix
    }

    # PPT Validator API (path kept)
    location ^~ /api/v2/ {
        auth_request /_hub_auth_ppt;
        auth_request_set $hub_user_id $upstream_http_x_auth_user_id;
        auth_request_set $hub_email   $upstream_http_x_auth_email;
        auth_request_set $hub_name    $upstream_http_x_auth_name;
        error_page 401 = @hub_login;
        error_page 403 = @hub_home;
        proxy_set_header X-Auth-User-Id $hub_user_id;
        proxy_set_header X-Auth-Email   $hub_email;
        proxy_set_header X-Auth-Name    $hub_name;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Proto https;
        client_max_body_size 50m;                   # PPT uploads
        proxy_read_timeout 300s;                    # slow reviews
        proxy_pass http://127.0.0.1:8001;           # no trailing slash = keep path
    }

    # Case Study service (path kept)
    location /case-study {
        auth_request /_hub_auth_case_study;
        auth_request_set $hub_user_id $upstream_http_x_auth_user_id;
        auth_request_set $hub_email   $upstream_http_x_auth_email;
        auth_request_set $hub_name    $upstream_http_x_auth_name;
        error_page 401 = @hub_login;
        error_page 403 = @hub_home;
        proxy_set_header X-Auth-User-Id $hub_user_id;
        proxy_set_header X-Auth-Email   $hub_email;
        proxy_set_header X-Auth-Name    $hub_name;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Proto https;
        proxy_read_timeout 120s;
        proxy_pass http://127.0.0.1:8003;
    }

    # Shared
    location @hub_login { return 302 /accounts/login/; }
    location @hub_home  { return 302 /; }
    location ^~ /internal/ { return 404; }          # the access-check endpoint is for nginx only
    # ════════════════════════════════════════════════════════════════════
```

`proxy_method GET` matters: without it, the access check for an upload would be sent as a POST, which the hub's endpoint rejects.

Check the result:

```bash
sudo grep -nE "proxy_pass|location" /etc/nginx/sites-available/agenthub.with-django
```

✅ `location /` → `127.0.0.1:8002`; the new locations are present; no `location ~ ^/(api/v[12]/)` and no `location = /case-study` remain.

### 5.12 Go live

One command at a time:

```bash
sudo cp /etc/nginx/sites-available/agenthub.with-django /etc/nginx/sites-available/agenthub
sudo nginx -t
```

✅ `syntax is ok` and `test is successful`. **If it fails, do not reload**; fix the file (the live site is untouched until a reload).

```bash
sudo systemctl reload nginx
```

### 5.13 Verify

```bash
R='--resolve agenthub.creatingwow.in:443:127.0.0.1'
curl -s -o /dev/null -w "Home:          %{http_code} -> %{redirect_url}\n" $R https://agenthub.creatingwow.in/
curl -s -o /dev/null -w "Login:         %{http_code}\n"                    $R https://agenthub.creatingwow.in/accounts/login/
curl -s -o /dev/null -w "Validator:     %{http_code} -> %{redirect_url}\n" $R https://agenthub.creatingwow.in/ppt-validator/app/
curl -s -o /dev/null -w "Validator API: %{http_code}\n"                    $R https://agenthub.creatingwow.in/api/v2/health
curl -s -o /dev/null -w "Case study:    %{http_code} -> %{redirect_url}\n" $R https://agenthub.creatingwow.in/case-study/
curl -s -o /dev/null -w "Internal:      %{http_code}\n"                    $R https://agenthub.creatingwow.in/internal/auth/proposal-validator/
```

✅ Home `302` → login · Login `200` · Validator `302` → login · Validator API `302` · Case study `302` → login · Internal `404`.

In a browser (incognito, hosts entry off):

- [ ] Google sign-in reaches the dashboard
- [ ] Proposal validator → Launch → a PPT review completes
- [ ] Case study creation → Launch → generate → Download PPT
- [ ] A user without access is returned to the dashboard

### 5.14 After go-live

```bash
sudo systemctl disable infobeans-agent-hub     # legacy hub: don't start it again after a reboot
```

Then, in the admin: create **Groups**, add members and apps. The hub's database starts empty: users appear on their first sign-in and see no agents until granted.

### 5.15 Rollback

The original nginx config is kept as `agenthub.before-django`, but it points at the **legacy hub, which has been stopped since 13 Nov 2026**. Restoring it would bring back a broken site, so **fix forward**: read the logs (section 7), correct the config or code, and use `sudo nginx -t` before every reload.

---

## 6. Production: future code updates

### 6.1 On your laptop

1. Make the change on a branch; run the tests:

   ```cmd
   .venv\Scripts\python.exe manage.py check
   .venv\Scripts\python.exe -m pytest -q
   cd apps\case_study && .venv\Scripts\python.exe -m pytest -q && cd ..\..
   ```

2. Merge into `main` and push. Check `git status -sb` shows `## main...origin/main` with no `[ahead …]`.
3. If a route changed, update **both** `deploy/Caddyfile.local` and `deploy/nginx-agenthub.conf` in the same commit.

**Never edit code directly on the server.** The server only runs what is on `main`.

### 6.2 On the server: pull the code

```bash
ssh -p 28274 infoadmin@144.79.8.82
cd /var/www/html/agenthub-django
git status                       # must be clean
git pull
git log --oneline -3             # top commit matches your laptop
```

Then run only the sections for the parts that changed.

### 6.3 Django hub changed

```bash
cd /var/www/html/agenthub-django
.venv/bin/pip install -r requirements.txt                      # if requirements.txt changed
sudo -u www-data .venv/bin/python manage.py migrate            # if there are new migrations
.venv/bin/python manage.py collectstatic --noinput             # if templates/static changed
sudo -u www-data .venv/bin/python manage.py check --deploy
sudo systemctl restart agenthub-django
sudo journalctl -u agenthub-django -n 30 --no-pager
```

✅ Three `Booting worker` lines and no traceback.

### 6.4 Case Study service changed

```bash
cd /var/www/html/agenthub-django/apps/case_study
.venv/bin/pip install -r requirements.txt                      # if requirements.txt changed
sudo systemctl restart agenthub-case-study
sleep 5
curl -s http://127.0.0.1:8003/case-study/health; echo
sudo journalctl -u agenthub-case-study -n 30 --no-pager
```

✅ `{"status":"ok"}`.

### 6.5 PPT Validator changed

The production validator still runs from **`/var/www/html/ib-ppt-validator`**, which is **not** the repo checkout. Changes to `apps/ppt_validator` in the repo do **not** reach production by `git pull`. Until the validator is moved (below), update that folder the way it has been maintained so far, then:

```bash
sudo systemctl restart infobeans-ppt-validator
sudo journalctl -u infobeans-ppt-validator -n 30 --no-pager
```

**Planned move (one-off, when convenient):** run the validator from `/var/www/html/agenthub-django/apps/ppt_validator` with its own `.venv` and `.env` (its own settings, no `ANTHROPIC_*` lines), build its UI with `npx vite build --base=/ppt-validator/app/`, and add `EnvironmentFile=/etc/agenthub/shared.env` to its systemd unit with the new `WorkingDirectory` and `ExecStart`. After that, validator updates follow the same `git pull` + restart pattern as 6.4.

### 6.6 Proxy (nginx) changed

```bash
sudo cp /etc/nginx/sites-available/agenthub /etc/nginx/sites-available/agenthub.bak-$(date +%Y%m%d)
sudo nano /etc/nginx/sites-available/agenthub        # apply the change from deploy/nginx-agenthub.conf
sudo nginx -t                                        # must succeed
sudo systemctl reload nginx
```

If `nginx -t` fails, restore the dated backup and do not reload.

### 6.7 After any update

- [ ] Sign in, open the dashboard
- [ ] Launch each agent that changed and run one real action
- [ ] `sudo tail -20 /var/log/nginx/error.log` shows nothing new

---

## 7. Operations: logs, restarts, key rotation

| Task | Command |
|---|---|
| Status of everything | `systemctl is-active agenthub-django agenthub-case-study infobeans-ppt-validator nginx` |
| Hub logs (live) | `sudo journalctl -u agenthub-django -f` |
| Case Study logs | `sudo journalctl -u agenthub-case-study -f` |
| Validator logs | `sudo journalctl -u infobeans-ppt-validator -f` |
| nginx errors | `sudo tail -f /var/log/nginx/error.log` |
| Restart a service | `sudo systemctl restart <service>` |
| Test / reload nginx | `sudo nginx -t && sudo systemctl reload nginx` |
| Promote a user to admin | `cd /var/www/html/agenthub-django && sudo -u www-data .venv/bin/python manage.py dbshell` → `UPDATE accounts_user SET is_superuser = 1, is_staff = 1 WHERE email = '<email>';` |

### 7.1 Editing settings files on the server

Always edit with `sudo` (`sudo nano <file>` or `sudo sed -i …`), then check ownership with `ls -l <file>`:

| File | Must be |
|---|---|
| `/var/www/html/agenthub-django/.env` | `infoadmin www-data`, mode `-rw-r-----` |
| `/var/www/html/agenthub-django/apps/case_study/.env` | `infoadmin www-data`, mode `-rw-r-----` |
| `/etc/agenthub/shared.env` | `root www-data`, mode `-rw-r-----` |

Running `sed -i` **without** `sudo` rewrites the file without the `www-data` group, and the service then fails with `PermissionError … .env`. Fix:

```bash
sudo chown infoadmin:www-data <file> && sudo chmod 640 <file>
sudo systemctl restart <service>
```

### 7.2 LLM models the gateway key allows

As of 18 Nov 2026 the gateway key may only use **`claude-sonnet-5`** and **`claude-haiku-4-5`**. A model outside that list fails with `key_model_access_denied` (HTTP 403). To test a model without showing the key:

```bash
sudo bash -c 'set -a; . /etc/agenthub/shared.env; set +a
curl -s -w "\nHTTP %{http_code}\n" "${ANTHROPIC_BASE_URL%/}/v1/messages" \
  -H "x-api-key: $ANTHROPIC_API_KEY" -H "anthropic-version: 2023-06-01" -H "content-type: application/json" \
  -d "{\"model\":\"claude-sonnet-5\",\"max_tokens\":64,\"messages\":[{\"role\":\"user\",\"content\":\"hi\"}]}" | tail -c 300'
```

`HTTP 200` = usable. The error body names the allowed models when access is denied.

Newer models may reply with a `thinking` block **before** the text. The Case Study service already handles this (`extract_text()` in `apps/case_study/main.py` joins only the `text` blocks). Any other code reading `content[0]` must do the same.

To change the Case Study model: edit `CASE_STUDY_LLM_MODEL` in `apps/case_study/.env` (with `sudo`), then `sudo systemctl restart agenthub-case-study`.

The PPT Validator currently uses **Groq** (`LLM_PROVIDER=groq`, `GROQ_MODEL=openai/gpt-oss-120b`), not the gateway. Test Groq without showing the key:

```bash
sudo bash -c '. <(grep -E "^(GROQ_API_KEY|GROQ_MODEL)=" /var/www/html/ib-ppt-validator/.env)
curl -s -o /dev/null -w "Groq: HTTP %{http_code}\n" https://api.groq.com/openai/v1/chat/completions \
  -H "Authorization: Bearer $GROQ_API_KEY" -H "Content-Type: application/json" \
  -d "{\"model\":\"$GROQ_MODEL\",\"messages\":[{\"role\":\"user\",\"content\":\"hi\"}],\"max_tokens\":64}"'
```

### 7.3 Rotating the LLM gateway key

1. Get the new key from the gateway owner.
2. Production: edit `/etc/agenthub/shared.env` **and**, while the validator still runs from its old folder, `/var/www/html/ib-ppt-validator/.env`:

   ```bash
   sudo nano /etc/agenthub/shared.env
   sudo nano /var/www/html/ib-ppt-validator/.env
   sudo systemctl restart agenthub-case-study infobeans-ppt-validator
   ```

3. Local: update `poc\.env.shared` and restart terminals 2 and 3 (4.10).
4. Ask the gateway owner to revoke the old key.
5. Verify a PPT review and a case study generation.

Never put keys in code, chat or commit messages. Only `.env*` files that git ignores, and the server's `/etc/agenthub/shared.env`.

---

## 8. Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| Site returns **502** | A backend isn't running | `systemctl is-active …` (section 7); start the inactive one; check its log |
| Endless redirects | `X-Forwarded-Proto` missing in `location /`, or `SECURE_PROXY_SSL_HEADER` missing | Add the header (`$scheme` or `https`); keep the setting |
| Google button empty / `origin_mismatch` | Page not opened as `https://agenthub.creatingwow.in` | Use that exact address; locally, hosts entry + Caddy |
| You see local data when expecting production (or the reverse) | Hosts entry on/off | `ping agenthub.creatingwow.in` — `127.0.0.1` = local (4.13) |
| Agent redirects to login / dashboard | Not signed in (401) / no access (403) | Sign in; grant access in the admin |
| Validator page has no styling (asset 404s) | UI built with the wrong base, or opened on port 8001 directly | Build with `--base=/ppt-validator/app/`; open via the hub |
| Case study page has no styling | Stylesheet link not under `/case-study/static/` | Use `/case-study/static/portal.css` in the template |
| Uploads fail, pages load | Access check sent as POST, or file too large | `proxy_method GET` in the auth locations; `client_max_body_size 50m` |
| `check --deploy`: **security.W009** | `DJANGO_SECRET_KEY` missing or short | Full 50+ character key in `.env` |
| `check --deploy`: **mail.E001** | Console `MAILERS` backend in production | Console only when `DEBUG` (already in settings) |
| Agent service `ModuleNotFoundError` | Packages missing from **that** service's `.venv` | `cd` to its folder → `.venv/bin/pip install -r requirements.txt` → restart |
| Agent says it is not configured / LLM errors | Shared env file not loaded or wrong values | Check `sudo cut -d= -f1 /etc/agenthub/shared.env`; `EnvironmentFile=` in the unit; `ANTHROPIC_BASE_URL` without `/v1` |
| `pip install` asks for "Microsoft Visual C++" (Windows) | Python too new for prebuilt packages | Recreate the venv with `py -3.12` |
| `.venv` or `.env` "missing" on the server | `ls` hides dot-files | `ls -la` |
| `git switch` fails: "you need to resolve your current index first" | An unfinished merge | Resolve the conflicted files, `git add`, then commit — never `git merge --abort` with uncommitted work |
| Case Study: `LLM service error` (502); log shows `key_model_access_denied` | Model not allowed for the gateway key | Use an allowed model (7.2) |
| Case Study: `LLM returned an unexpected response` (502) | Reply format not understood | Log line `No text in LLM reply: content_types=…` names what came back; check the model and `max_tokens` |
| Case Study: `422` on generate | A required field is missing from the request | F12 → Network → the `generate` request → Response names the field |
| Service fails to start: `PermissionError … .env` | `.env` lost the `www-data` group (edited without `sudo`) | 7.1 |
| PPT Validator: internal server error | Varies | `sudo systemctl restart infobeans-ppt-validator`; if it persists, follow `sudo journalctl -u infobeans-ppt-validator -f` while running one review, and test Groq (7.2) |

### Watching a service while reproducing a problem

```bash
sudo journalctl -u <service> -f --no-pager      # then reproduce in the browser; Ctrl+C to stop
```

Errors in the last 30 minutes:

```bash
sudo journalctl -u <service> --since "30 min ago" --no-pager | grep -iE "error|exception|traceback"
```

---

## 9. Handover: open items

State at handover (18 Nov 2026): the Django hub, the Case Study service and the PPT Validator are live at `https://agenthub.creatingwow.in`, and all three were verified working. The items below are known and not yet done.

| # | Item | Priority | Where / how |
|---|---|---|---|
| 1 | **Rotate the LLM gateway key.** The current key was hard-coded in the old hub's code and is in git history. | High | 7.3. Update `/etc/agenthub/shared.env` and `/var/www/html/ib-ppt-validator/.env`, restart both agents, then have the old key revoked. |
| 2 | **Disable the legacy FastAPI hub** so it doesn't start again after a reboot. | Medium | `sudo systemctl disable infobeans-agent-hub` |
| 3 | **Set up access.** The hub's user database started empty. | Medium | Admin → Groups: add members and apps; or grant per user. |
| 4 | **Move the PPT Validator into the repo checkout.** Production still runs it from `/var/www/html/ib-ppt-validator`, so `git pull` does not update it. | Medium | 6.5 |
| 5 | **Fix the validator's Claude provider.** `apps/ppt_validator/llm/providers/claude_provider.py` reads `resp.content[0].text`, which fails when a model replies with a `thinking` block first. Not used while `LLM_PROVIDER=groq`. | Low (needed before switching the validator to Claude) | Replace with `raw = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")` |
| 6 | **Validator template path typo.** The validator looks for `/var/www/html/Ib-ppt-validator/slide_templates/Exclude Slides.pptx` (capital **I**); the folder is `ib-ppt-validator`, so that template is never found (logged as `template_not_found`). | Low | `sudo grep -rn "Ib-ppt-validator" /var/www/html/ib-ppt-validator --include=*.py --include=*.yaml --include=.env` and correct the case |
| 7 | **Commit the deployment configs** to `deploy/`: `Caddyfile.local`, `nginx-agenthub.conf`, `agenthub-django.service`, `agenthub-case-study.service`. | Low | Copy from 4.7, 5.11 and the live files on the server |