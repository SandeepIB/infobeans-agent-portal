# InfoBeans Agent Hub

A Django portal at **https://agenthub.creatingwow.in** where InfoBeans users sign in with Google and launch the AI agents they have been given access to. Administrators control access per user or per group from the Django admin. Agents such as the **PPT Validator** run as separate services behind the hub, which checks access and passes the user's identity on.

---

## Contents

1. [Architecture](#architecture)
2. [Features](#features)
3. [Project structure](#project-structure)
4. [Configuration](#configuration)
5. [Local development (Windows)](#local-development-windows)
6. [Admin guide](#admin-guide)
7. [Production deployment](#production-deployment)
8. [Deploying updates](#deploying-updates)
9. [Testing](#testing)
10. [Troubleshooting](#troubleshooting)

---

## Architecture

```
Browser ──► https://agenthub.creatingwow.in
              │
            reverse proxy  (production: nginx · local: Caddy)
              ├─ /ppt-validator/*  ─┐  1. ask the hub: GET /internal/auth/proposal-validator/
              ├─ /api/v2/*         ─┤     ◄─ 200 + X-Auth-User-Id / X-Auth-Email / X-Auth-Name
              │                     │     ◄─ 401 (not signed in) → redirect to login
              │                     │     ◄─ 403 (no access)     → redirect to dashboard
              │                     └► 2. forward to PPT Validator (FastAPI, 127.0.0.1:8001)
              │                           with the identity headers attached
              └─ everything else ──────► Django hub (gunicorn; local: runserver)
```

**The access rule lives in one place.** `access_condition()` in `hub/models.py` grants access when the app is active **and** the user has either a current direct grant or membership of a group that has the app. The dashboard, the launch view, the reverse-proxy permission check and the admin's "Effective" column all use it.

**Agents stay private.** The validator listens only on `127.0.0.1`, so the identity headers cannot be forged: the proxy always overwrites them, and nothing else can reach the service.

---

## Features

| Area | What it does |
|---|---|
| **Google sign-in** | Google Identity Services in **popup mode**. The ID token is verified server-side with `google-auth`. Users are matched by Google `sub`, then by email (so admin-created users are linked on first sign-in). Optional domain restriction. |
| **Per-user access** | `AppGrant` records who granted access, when, and an optional **expiry date**. Expired grants disappear automatically. |
| **Group access** | Assign members and apps on one Group page; everyone in the group sees those apps. |
| **Signup group rules** | Optionally add users to a group on their **first** sign-in, based on their email domain. Never re-applied on later sign-ins. |
| **Access requests** | Users request access from the dashboard. Admins approve or reject in bulk; approval creates or renews the grant. One pending request per user per app is enforced by a database constraint. |
| **Launch logging** | Every successful launch is recorded in `LaunchEvent` (read-only in the admin). Denied launches are not logged. |
| **Effective access** | The Users list shows direct and effective app counts; each user's page shows *which* apps they can see and *why* (direct, with expiry, or via a named group). |
| **Agent integration** | Agents on the same server are put behind the hub with `auth_request` (nginx) or `forward_auth` (Caddy) and receive the user's identity as headers. |

---

## Project structure

```
poc/
├── agenthub/              # project config: settings, urls, wsgi/asgi
├── accounts/              # identity: custom User, Google sign-in, signup group rules
│   ├── services.py        #   token verification, user resolution, group rules
│   └── admin.py           #   Users (app picker, effective access) and Groups admin
├── hub/                   # authorization and dashboard
│   ├── models.py          #   App, AppGrant, LaunchEvent, AccessRequest, access_condition()
│   ├── services.py        #   access-request workflow (create / approve / reject / cancel)
│   ├── views.py           #   dashboard, launch, request access, nginx_auth
│   ├── admin.py           #   Apps, App access grants, Access requests, Launch events
│   └── tests/
├── templates/             # base, login, dashboard, partials
├── static/                # css/hub.css, img/infobeans-logo.png
├── deploy/                # keep the local Caddyfile and production nginx block here
├── conftest.py            # test-only settings (plain static storage)
├── pytest.ini
└── requirements.txt
```

### Data model

| Model | Purpose |
|---|---|
| `accounts.User` | Custom user. Username is the email; `google_sub` is the stable Google identity. |
| `accounts.SignupGroupRule` | Email domain (blank = everyone) → group, applied on first sign-in. |
| `hub.App` | An agent: name, slug, launch URL, SVG icon, order, active flag, allowed users (through `AppGrant`) and groups. |
| `hub.AppGrant` | One user's direct access to one app, with `granted_by`, `granted_at`, `expires_at`, `note`. Reuses the table `hub_app_allowed_users`. |
| `hub.AccessRequest` | A user's request for an app, with status and decision details. |
| `hub.LaunchEvent` | Audit log of launches. |

---

## Configuration

Settings are read from a `.env` file next to `manage.py`. It is **never committed**; see `.env.example` for the variable names.

| Variable | Example | Notes |
|---|---|---|
| `DJANGO_SECRET_KEY` | *(50+ random characters)* | Required. Generate with `python -c "import secrets; print(secrets.token_urlsafe(50))"`. Use a different key per environment. |
| `DJANGO_DEBUG` | `False` | `True` only on a developer machine. |
| `DJANGO_ALLOWED_HOSTS` | `agenthub.creatingwow.in,127.0.0.1,localhost` | Comma-separated. |
| `CSRF_TRUSTED_ORIGINS` | `https://agenthub.creatingwow.in` | Comma-separated, with scheme. |
| `GOOGLE_CLIENT_ID` | `…apps.googleusercontent.com` | The Web client whose Authorized JavaScript origin is `https://agenthub.creatingwow.in`. |
| `GOOGLE_ALLOWED_DOMAINS` | `infobeans.com` | Optional. Empty = any Google account (users still see no apps until granted). |
| `SQLITE_PATH` | `/var/lib/agenthub/db.sqlite3` | Optional. Defaults to `db.sqlite3` in the project folder. |

Settings worth knowing about in `agenthub/settings.py`:

| Setting | Why |
|---|---|
| `SECURE_CROSS_ORIGIN_OPENER_POLICY = "same-origin-allow-popups"` | Django's default breaks the Google sign-in popup. |
| `SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"` | Google needs the page's origin in the `Referer` to render the button. |
| `SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")` | Django sits behind a proxy; without it every request looks like plain HTTP and redirects forever. Set unconditionally. |
| `HUB_SUPERUSER_SEES_ALL = False` | Superusers see only apps granted to them, like everyone else. |
| `MAILERS` | Console backend when `DEBUG`, SMTP otherwise (Django 6.1 `check --deploy` rejects dev backends). The app does not send email yet. |
| `STORAGES["staticfiles"]` | WhiteNoise compressed manifest storage; Django serves its own static files. |

---

## Local development (Windows)

Local runs use the **production domain on your laptop**: the official Google client only accepts sign-ins from `https://agenthub.creatingwow.in`.

```
Browser → https://agenthub.creatingwow.in
            │  hosts file: → 127.0.0.1
            ▼
          Caddy (local HTTPS)
            ├─ /ppt-validator/*, /api/v2/*  → access check → PPT Validator :8001
            └─ everything else              → Django :8000
```

> While the hosts entry is active, `agenthub.creatingwow.in` on your laptop means **your local copy**, not production. To reach the real site, comment the line out (`#`), run `ipconfig /flushdns`, and clear `chrome://net-internals/#dns`.

### 1. Python

Use **Python 3.12** (the server's version). Newer versions may lack prebuilt Windows packages and try to compile from source.

```cmd
py -0p                           :: list installed versions
```

### 2. Hub

```cmd
cd C:\Users\<you>\Desktop\poc
py -3.12 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Create `.env`:

```ini
DJANGO_SECRET_KEY=<local random key>
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=agenthub.creatingwow.in,localhost,127.0.0.1
CSRF_TRUSTED_ORIGINS=https://agenthub.creatingwow.in
GOOGLE_CLIENT_ID=<official client id>
GOOGLE_ALLOWED_DOMAINS=
```

```cmd
.venv\Scripts\python.exe manage.py migrate
.venv\Scripts\python.exe manage.py createsuperuser     :: use your Google email as username and email
```

### 3. PPT Validator

The validator is a **separate project** and must live outside the hub's folder (it has its own `.env` with secrets).

```
Desktop\
├── poc\                ← Django hub
└── ib-ppt-validator\   ← PPT Validator
```

To download it from the server (once):

```bash
# on the server
sudo tar -czf /tmp/ib-ppt-validator.tgz -C /var/www/html \
  --exclude='ib-ppt-validator/venv' --exclude='ib-ppt-validator/.venv' \
  --exclude='__pycache__' --exclude='node_modules' --exclude='*.pyc' \
  ib-ppt-validator
sudo chown $USER:$USER /tmp/ib-ppt-validator.tgz
```

```cmd
:: on your laptop
cd C:\Users\<you>\Desktop
scp -P 28274 <user>@144.79.8.82:/tmp/ib-ppt-validator.tgz .
tar -xzf ib-ppt-validator.tgz
del ib-ppt-validator.tgz
```

Then remove the archive from the server (`rm /tmp/ib-ppt-validator.tgz`), and set the validator up:

```cmd
cd C:\Users\<you>\Desktop\ib-ppt-validator
py -3.12 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -c "from db.migrate import run; run()"
```

**About the validator's UI build:** `frontend/dist` is built for the base path **`/ppt-validator/app/`**, and the UI calls its API at **`/api/v2/…`**. Opening `http://localhost:8001/app/` directly therefore shows missing assets; always open it through the hub.

### 4. Caddy

`deploy/Caddyfile.local`:

```
(hub_auth) {
    forward_auth localhost:8000 {
        uri /internal/auth/proposal-validator/
        copy_headers X-Auth-User-Id X-Auth-Email X-Auth-Name
    }
}

agenthub.creatingwow.in {
    tls internal

    # Validator UI: strip "/ppt-validator" so the validator receives /app/...
    handle_path /ppt-validator/* {
        import hub_auth
        reverse_proxy localhost:8001
    }

    # Validator API, called by the UI at /api/v2/...
    handle /api/v2/* {
        import hub_auth
        request_body {
            max_size 50MB
        }
        reverse_proxy localhost:8001 {
            transport http {
                read_timeout 300s
            }
        }
    }

    # Everything else: the Django hub
    handle {
        reverse_proxy localhost:8000
    }
}
```

Add to `C:\Windows\System32\drivers\etc\hosts` (Notepad as Administrator), then run `ipconfig /flushdns`:

```
127.0.0.1  agenthub.creatingwow.in
```

### 5. Run (three terminals)

```cmd
:: 1. Validator (ib-ppt-validator folder)
.venv\Scripts\python.exe -m uvicorn app:app --host 127.0.0.1 --port 8001 --reload

:: 2. Hub (poc folder)
.venv\Scripts\python.exe manage.py runserver 8000

:: 3. Caddy (folder containing the Caddyfile)
caddy run
```

Open **https://agenthub.creatingwow.in**, sign in with Google, and launch **Proposal validator**.

In the **local** admin, the validator card must have:

| Field | Value |
|---|---|
| Slug | `proposal-validator` |
| Launch URL | `https://agenthub.creatingwow.in/ppt-validator/app/` |

---

## Admin guide

Admin site: **https://agenthub.creatingwow.in/admin/**. Sign in with Google first, then open `/admin/` (Google-created accounts have no password).

| Task | Where |
|---|---|
| Give one user several apps | **Users** → user → **Apps** picker → Save |
| Give one app to several users | **Apps** → app → **Allowed users** → Save |
| Grant or revoke apps for many users at once | **Users** list → tick users → action **Grant / revoke apps** (add, replace or remove) |
| Bulk access by team | **Groups** → group → add **Members** and **Apps** → Save |
| Temporary access / see who granted what | **App access grants**: edit **Expires at** inline; filter by Current / Expired. Deleting a row revokes that user's access only. |
| See exactly what a user can open | **Users** → **Effective** count, or the breakdown table on the user's page |
| Handle access requests | **Access requests** (pending first) → tick → **Approve** or **Reject** |
| Auto-assign groups to new users | **Signup group rules**: email domain (blank = everyone) → group. To backfill existing users: **Users** → tick → **Apply signup group rules**. |
| Retire an app | Untick **Is active** on the app. Apps cannot be deleted from the admin; grants are kept, so reactivating restores everyone's access. |

Superuser status from the command line:

```sql
-- python manage.py dbshell
UPDATE accounts_user SET is_superuser = 1, is_staff = 1 WHERE email = 'someone@infobeans.com';  -- promote
UPDATE accounts_user SET is_superuser = 0, is_staff = 0 WHERE email = 'someone@infobeans.com';  -- demote
```

---

## Production deployment

| Item | Value |
|---|---|
| Server | `144.79.8.82`, SSH port `28274` |
| Hub code | `/var/www/html/agenthub-django` |
| Hub `.env` | `/var/www/html/agenthub-django/.env` (owner you, group `www-data`, mode `640`) |
| Database | `/var/lib/agenthub/db.sqlite3` (folder owned by `www-data`) |
| Hub service | `agenthub-django` → gunicorn on `127.0.0.1:8002`, user `www-data` |
| PPT Validator | `/var/www/html/ib-ppt-validator`, service `infobeans-ppt-validator` on `127.0.0.1:8001` |
| Legacy hub | FastAPI, service `infobeans-agent-hub` on `127.0.0.1:8000` (to be retired) |
| nginx site | `/etc/nginx/sites-available/agenthub` (symlinked from `sites-enabled`) |
| nginx backups | `agenthub.before-django` (original) · `agenthub.with-django` (prepared cutover config) |

### First-time setup (summary)

```bash
cd /var/www/html/agenthub-django
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
nano .env && sudo chown $USER:www-data .env && chmod 640 .env
sudo mkdir -p /var/lib/agenthub && sudo chown www-data:www-data /var/lib/agenthub && sudo chmod 750 /var/lib/agenthub
sudo -u www-data .venv/bin/python manage.py check --deploy     # must report no issues
sudo -u www-data .venv/bin/python manage.py migrate
.venv/bin/python manage.py collectstatic --noinput
sudo -u www-data .venv/bin/python manage.py createsuperuser
```

### systemd service

`/etc/systemd/system/agenthub-django.service`:

```ini
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
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now agenthub-django
```

### nginx

Inside the `listen 443 ssl` server block for `agenthub.creatingwow.in`:

- `location /` must `proxy_pass http://127.0.0.1:8002;` and send `Host` and `X-Forwarded-Proto`.
- **Remove** the legacy rules `location = /ppt-validator/app { … }` and `location ~ ^/(api/v[12]/)(.*)$ { … }`. The regex rule would otherwise capture all `/api/v2/` traffic.
- Add the validator block below, **above** `location / {`.

```nginx
    # ── PPT Validator behind the Django hub ─────────────────────────────
    location = /_hub_auth_ppt {
        internal;
        proxy_pass http://127.0.0.1:8002/internal/auth/proposal-validator/;
        proxy_method GET;
        proxy_pass_request_body off;
        proxy_set_header Content-Length "";
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Proto https;
    }

    # New UI (built for /ppt-validator/app/): strip /ppt-validator → validator /app/
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

    # Validator API, called by the UI at /api/v2/...
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

    location @hub_login { return 302 /accounts/login/; }
    location @hub_home  { return 302 /; }
    location ^~ /internal/ { return 404; }          # the permission endpoint is for nginx only
    # ────────────────────────────────────────────────────────────────────
```

`proxy_method GET` matters: without it, the permission check for an upload would be sent as a POST, which the Django endpoint rejects.

### Cutover

```bash
sudo systemctl enable --now agenthub-django
sudo cp /etc/nginx/sites-available/agenthub.with-django /etc/nginx/sites-available/agenthub
sudo nginx -t && sudo systemctl reload nginx
```

Then, in the production admin, set the validator card's Launch URL to `https://agenthub.creatingwow.in/ppt-validator/app/` and grant access.

> **Before retiring the FastAPI hub:** the legacy config also has `location = /case-study`, which points at the old hub. Confirm what it serves first.

### Rollback

```bash
sudo cp /etc/nginx/sites-available/agenthub.before-django /etc/nginx/sites-available/agenthub
sudo nginx -t && sudo systemctl reload nginx
```

The legacy hub takes over again; Django keeps running on 8002 for the next attempt.

### Verify

```bash
R='--resolve agenthub.creatingwow.in:443:127.0.0.1'
curl -s -o /dev/null -w "Home:      %{http_code} → %{redirect_url}\n" $R https://agenthub.creatingwow.in/
curl -s -o /dev/null -w "Login:     %{http_code}\n"                   $R https://agenthub.creatingwow.in/accounts/login/
curl -s -o /dev/null -w "Validator: %{http_code} → %{redirect_url}\n" $R https://agenthub.creatingwow.in/ppt-validator/app/
curl -s -o /dev/null -w "Internal:  %{http_code}\n"                   $R https://agenthub.creatingwow.in/internal/auth/proposal-validator/
```

Expected: Home `302` to login · Login `200` · Validator `302` to login · Internal `404`.

---

## Deploying updates

Never edit code on the server. Change it locally, push, then pull on the server.

```bash
cd /var/www/html/agenthub-django
git pull
.venv/bin/pip install -r requirements.txt                    # if requirements changed
sudo -u www-data .venv/bin/python manage.py migrate          # if there are new migrations
.venv/bin/python manage.py collectstatic --noinput           # if static files changed
sudo systemctl restart agenthub-django
sudo journalctl -u agenthub-django -n 30 --no-pager          # check it started cleanly
```

To avoid pasting the GitHub token on every pull: `git config credential.helper 'cache --timeout=3600'`.

---

## Testing

```cmd
.venv\Scripts\python.exe -m pytest -q
```

- `pytest.ini` sets `DJANGO_SETTINGS_MODULE` and puts the project root on the path.
- The root `conftest.py` switches tests to plain static storage (the manifest storage needs `collectstatic`, which tests do not run).
- Shared fixtures (`app`, `user`, `superuser`) live in `hub/tests/conftest.py`.
- Key tests assert that the admin's effective-access count and the dashboard rule always agree, and that unassigning an app from one user never affects the app or other users.

---

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| Google button area is empty; console says `Unsecured login_uri` | Page opened over plain HTTP on a non-`localhost` host | Use `https://agenthub.creatingwow.in` |
| `origin is not allowed for the given client ID` / `origin_mismatch` | The page's origin is not an Authorized JavaScript origin of the client in use | Use the domain the client allows; Console changes take about 5 minutes |
| Sign-in popup opens and closes, nothing happens | `Cross-Origin-Opener-Policy` is not `same-origin-allow-popups` | Check the setting and the response headers |
| You see local data when expecting production (or the reverse) | The hosts-file entry is (or isn't) active | `ping agenthub.creatingwow.in`: `127.0.0.1` means local |
| `check --deploy`: **mail.E001** | Django 6.1's project template uses the console mail backend | Console only when `DEBUG` (see `MAILERS`) |
| `check --deploy`: **security.W009** | `DJANGO_SECRET_KEY` missing or short in `.env` | Set a 50+ character key; read it with `os.environ[...]` |
| Endless redirects behind the proxy | `X-Forwarded-Proto` not sent, or `SECURE_PROXY_SSL_HEADER` missing | Send the header from nginx/Caddy; keep the setting unconditional |
| Validator assets return 404 | The UI is built for `/ppt-validator/app/` | Open it through the hub, not on port 8001 directly |
| Validator returns 401 / 403 | Not signed in to the hub / no access to `proposal-validator` | Sign in first; grant access in the admin |
| `pip install` tries to compile and asks for "Microsoft Visual C++" | Python version too new for prebuilt packages | Use Python 3.12 |
| `Missing staticfiles manifest entry` in tests | Manifest storage in tests | Root `conftest.py` (already in place) |
| `database is locked` | A SQLite browser holds uncommitted changes | Close the tool or write the changes |