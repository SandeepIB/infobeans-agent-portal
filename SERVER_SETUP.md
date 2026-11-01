# InfoBeans Agent Hub — Server Setup Guide

**Target server:** `agenthub-new` (144.79.8.82, user: `infoadmin`, port: 28274)  
**Project path:** `/var/www/html/infobeans-agent-portal`  
**PPT Validator path:** `/var/www/html/ib-ppt-validator`

Run all commands as `infoadmin` unless noted. Commands marked `[sudo]` require `sudo`.

---

## Local Development Setup

> **Use this section when running the site on your own machine** (e.g. `IB-Pune-LAP-580`).  
> The production setup guide (Sections 1–11 below) is for the remote server.

### How the local stack works

```
Browser → /etc/hosts → 127.0.0.1:443
       → Docker nginx container (port 443, network docker-local_tid-local)
       → proxy_pass http://172.26.0.1:8000   ← Docker bridge gateway = this host
       → uvicorn (Agent Hub, 0.0.0.0:8000)
       → PPT Validator (0.0.0.0:8001, called internally by Hub)
```

The nginx that serves `agenthub.creatingwow.in` runs **inside a Docker container**.  
From inside that container `127.0.0.1` is the container's loopback — not the host's.  
The correct proxy address is `172.26.0.1:8000` (the Docker bridge gateway to the host).  
This is already set in `config/nginx.conf`. **Do not change it back to `127.0.0.1`.**

---

### Step L1 — Fix `/etc/hosts`

The domain must resolve to this machine's loopback, not a remote IP.

```bash
# Check current entry
grep agenthub /etc/hosts

# If missing, add it:
echo "127.0.0.1 agenthub.creatingwow.in" | sudo tee -a /etc/hosts

# If it points to the wrong IP (e.g. 192.168.1.12), fix it:
sudo sed -i 's/192\.168\.1\.12.*agenthub\.creatingwow\.in/127.0.0.1 agenthub.creatingwow.in/' /etc/hosts

# Verify — should print 127.0.0.1:
ping -c1 agenthub.creatingwow.in | head -1
```

---

### Step L2 — Start the app (manual / one-shot)

Use `start-all-local.sh` whenever you want to start or restart both services:

```bash
cd /var/www/html/infobeans-agent-portal

# Normal mode
bash start-all-local.sh

# Debug mode — verbose logging + hot-reload watches all file changes
bash start-all-local.sh --debug

# Start and immediately tail both logs (Ctrl+C stops tailing; apps keep running)
bash start-all-local.sh --logs

# Both together
bash start-all-local.sh --debug --logs
```

The script:
1. Warns if `/etc/hosts` is wrong
2. Runs Alembic migrations
3. Kills any existing process on ports 8000 / 8001
4. Starts Agent Hub on `0.0.0.0:8000`
5. Starts PPT Validator on `0.0.0.0:8001`
6. Reloads Docker nginx so it picks up config changes
7. Verifies both services return HTTP 200

**Log files:**

| Service | Log file |
|---|---|
| Agent Hub | `/tmp/hub.log` |
| PPT Validator | `/tmp/ppt-validator.log` |

```bash
# Live tail both at once
tail -f /tmp/hub.log /tmp/ppt-validator.log

# Stop everything
kill $(lsof -ti :8000 :8001 2>/dev/null)
```

---

### Step L3 — Debug mode explained

| Flag | Effect |
|---|---|
| *(none)* | `--log-level info`, hot-reload on |
| `--debug` | `--log-level debug` — shows every request, SQL query, and framework event |

To enable debug logging **without restarting**, you can also set the env var before calling the script:

```bash
LOG_LEVEL=debug bash start-all-local.sh
```

What `debug` level adds over `info`:
- Full HTTP request/response cycle details
- FastAPI dependency injection traces
- SQLAlchemy query logs (if configured)
- Uvicorn keep-alive and connection lifecycle events

---

### Step L4 — Auto-restart on system reboot (systemd user service)

This is the recommended approach so the app comes back up automatically after a restart without needing to run `start-all-local.sh` manually.

**Install the services (run once):**

```bash
# Create the user systemd directory
mkdir -p ~/.config/systemd/user

# Link the service files (symlinked so git updates apply automatically)
ln -sf /var/www/html/infobeans-agent-portal/config/infobeans-hub-local.service \
        ~/.config/systemd/user/infobeans-hub-local.service

ln -sf /var/www/html/infobeans-agent-portal/config/infobeans-pptvalidator-local.service \
        ~/.config/systemd/user/infobeans-pptvalidator-local.service

# Reload systemd and enable both services
systemctl --user daemon-reload
systemctl --user enable --now infobeans-hub-local.service
systemctl --user enable --now infobeans-pptvalidator-local.service
```

**Enable auto-start at boot** (without needing to log in first):

```bash
loginctl enable-linger $USER
```

This tells systemd to start your user services at boot time even before you log in.

**Check status:**

```bash
systemctl --user status infobeans-hub-local
systemctl --user status infobeans-pptvalidator-local
```

**Useful commands after install:**

| Action | Command |
|---|---|
| View live logs | `journalctl --user -u infobeans-hub-local -f` |
| View PPT validator logs | `journalctl --user -u infobeans-pptvalidator-local -f` |
| Log files on disk | `tail -f /tmp/infobeans-hub.log /tmp/infobeans-ppt.log` |
| Restart hub | `systemctl --user restart infobeans-hub-local` |
| Restart PPT validator | `systemctl --user restart infobeans-pptvalidator-local` |
| Stop both | `systemctl --user stop infobeans-hub-local infobeans-pptvalidator-local` |
| Disable auto-start | `systemctl --user disable infobeans-hub-local infobeans-pptvalidator-local` |

---

### Step L5 — Switch to debug mode via systemd

To enable debug logging through the systemd service without editing the service file:

```bash
# Open a drop-in override (saved at ~/.config/systemd/user/infobeans-hub-local.service.d/override.conf)
systemctl --user edit infobeans-hub-local
```

Add these lines in the editor that opens:

```ini
[Service]
Environment=LOG_LEVEL=debug
```

Save and restart:

```bash
systemctl --user restart infobeans-hub-local
journalctl --user -u infobeans-hub-local -f
```

To revert to normal logging:

```bash
systemctl --user edit infobeans-hub-local   # delete the override lines
systemctl --user restart infobeans-hub-local
```

---

### Step L6 — After a system restart: what to check

After rebooting, if the site doesn't load:

```bash
# 1. Are services running?
systemctl --user status infobeans-hub-local infobeans-pptvalidator-local

# 2. Quick HTTP check
curl -s -o /dev/null -w "Hub:          HTTP %{http_code}\n" http://127.0.0.1:8000/
curl -s -o /dev/null -w "PPT Validator: HTTP %{http_code}\n" http://127.0.0.1:8001/

# 3. Is Docker nginx up?
docker ps --filter "network=docker-local_tid-local"

# 4. Can nginx reach the hub through the Docker bridge?
curl -sk -o /dev/null -w "nginx → hub: HTTP %{http_code}\n" \
  https://127.0.0.1/ -H "Host: agenthub.creatingwow.in"
```

If services are not running, start them manually with `bash start-all-local.sh`  
and then install the systemd services (Step L4) so it doesn't happen again.

---

## 1. Create the `.env` file

```bash
cd /var/www/html/infobeans-agent-portal
nano .env
```

Paste and fill in the values below. Replace every `CHANGE_ME` with the real value:

```env
APP_NAME=InfoBeans Agent Hub
APP_ENV=production
APP_DEBUG=false
APP_BASE_URL=https://agenthub.creatingwow.in

SECRET_KEY=CHANGE_ME_64_char_random_hex

 

SESSION_COOKIE_SECURE=true
SESSION_COOKIE_HTTPONLY=true
SESSION_COOKIE_SAMESITE=lax
SESSION_MAX_AGE_SECONDS=28800

MAX_UPLOAD_SIZE_MB=50
PPT_VALIDATOR_INTERNAL_URL=http://127.0.0.1:8001
```

To generate a secure `SECRET_KEY`:
```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

---

## 2. Set up the MySQL database

Run as a MySQL admin (use `sudo mysql` or your admin credentials):

```sql
CREATE DATABASE IF NOT EXISTS infobeans_agent_hub CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS 'ib_agent_hub'@'localhost' IDENTIFIED BY 'CHANGE_ME_DB_PASS';
GRANT ALL PRIVILEGES ON infobeans_agent_hub.* TO 'ib_agent_hub'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

Update the `DATABASE_URL` in `.env` with the same password you used above.

---

## 3. Fix the virtual environment path

The systemd service expects `.venv` but the server has `venv`. Create a symlink:

```bash
cd /var/www/html/infobeans-agent-portal
ln -s venv .venv
```

Verify:
```bash
ls -la .venv/bin/gunicorn
```

---

## 4. Install / verify Python dependencies

```bash
cd /var/www/html/infobeans-agent-portal
venv/bin/pip install -r requirements.txt
```

---

## 5. Run database migrations

```bash
cd /var/www/html/infobeans-agent-portal
venv/bin/alembic upgrade head
```

Expected output: `Running upgrade -> <revision_id>, Initial schema`

---

## 6. Set up the log directory

```bash
sudo mkdir -p /var/log/infobeans
sudo chown www-data:www-data /var/log/infobeans
sudo chmod 755 /var/log/infobeans
```

---

## 7. Fix nginx proxy IP

The nginx config currently proxies to `172.26.0.1:8000` (a Docker/WSL bridge IP).  
On this server, update it to `127.0.0.1:8000`:

```bash
sudo nano /etc/nginx/sites-available/agenthub
```

Replace all occurrences of `172.26.0.1:8000` with `127.0.0.1:8000`.

If the nginx site config doesn't exist yet, install it:

```bash
sudo cp /var/www/html/infobeans-agent-portal/config/nginx-agenthub.conf \
        /etc/nginx/sites-available/agenthub

# Edit the file to fix the IP (see above)
sudo sed -i 's/172\.26\.0\.1:8000/127.0.0.1:8000/g' /etc/nginx/sites-available/agenthub

sudo ln -sf /etc/nginx/sites-available/agenthub /etc/nginx/sites-enabled/agenthub
```

---

## 8. Install SSL certificates

```bash
sudo mkdir -p /etc/ssl/creatingwow
sudo cp /var/www/html/infobeans-agent-portal/config/ssl/fullchain.crt \
        /etc/ssl/creatingwow/fullchain.crt
sudo cp /var/www/html/infobeans-agent-portal/config/ssl/creatingwow.in.key \
        /etc/ssl/creatingwow/creatingwow.in.key
sudo chmod 600 /etc/ssl/creatingwow/creatingwow.in.key
```

Test nginx config:
```bash
sudo nginx -t
```

---

## 9. Install the Agent Hub systemd service

```bash
sudo cp /var/www/html/infobeans-agent-portal/config/infobeans-agent-hub.service \
        /etc/systemd/system/infobeans-agent-hub.service

sudo systemctl daemon-reload
sudo systemctl enable infobeans-agent-hub
sudo systemctl start infobeans-agent-hub
sudo systemctl status infobeans-agent-hub
```

---

## 10. Set up the PPT Validator service

The PPT Validator lives at `/var/www/html/ib-ppt-validator` and binds to `127.0.0.1:8001`.

**Option A — if it already runs via its own `start.sh`:**
```bash
cd /var/www/html/ib-ppt-validator
head -40 start.sh   # check what port it uses and how it starts
```

**Option B — install the systemd service:**  
Edit the service file first (the template has `ExecStart=/usr/bin/node server.js`; update to match the actual start command):

```bash
sudo cp /var/www/html/infobeans-agent-portal/config/infobeans-ppt-validator.service \
        /etc/systemd/system/infobeans-ppt-validator.service

# Edit WorkingDirectory and ExecStart to match the real ppt-validator setup:
sudo nano /etc/systemd/system/infobeans-ppt-validator.service
# WorkingDirectory=/var/www/html/ib-ppt-validator
# ExecStart=<correct start command>
# Environment=PORT=8001
# Environment=HOST=127.0.0.1

sudo systemctl daemon-reload
sudo systemctl enable infobeans-ppt-validator
sudo systemctl start infobeans-ppt-validator
sudo systemctl status infobeans-ppt-validator
```

---

## 11. Reload nginx and verify

```bash
sudo systemctl reload nginx
```

Check both services are up:
```bash
curl -s -o /dev/null -w "Hub:           HTTP %{http_code}\n" http://127.0.0.1:8000/
curl -s -o /dev/null -w "PPT Validator: HTTP %{http_code}\n" http://127.0.0.1:8001/
```

Then test from outside:
```
https://agenthub.creatingwow.in/
```

---

## Useful commands after setup

| Action | Command |
|--------|---------|
| View hub logs | `sudo journalctl -u infobeans-agent-hub -f` |
| View hub access log | `sudo tail -f /var/log/infobeans/hub-access.log` |
| Restart hub | `sudo systemctl restart infobeans-agent-hub` |
| Restart PPT validator | `sudo systemctl restart infobeans-ppt-validator` |
| Nginx status | `sudo systemctl status nginx` |

---

## Troubleshooting

**Hub won't start — missing env var:**  
Check `/var/log/infobeans/hub-error.log` or `journalctl -u infobeans-agent-hub -n 50`

**502 Bad Gateway from nginx:**  
The hub service isn't running. Run `sudo systemctl start infobeans-agent-hub` and check status.

**Alembic error — can't connect to DB:**  
Confirm the `DATABASE_URL` in `.env` matches the MySQL user/password you created in Step 2.

**PPT Validator not reachable at 8001:**  
Confirm it's bound to `127.0.0.1:8001`. The Agent Hub's `PPT_VALIDATOR_INTERNAL_URL` must match.

---

## Operations Runbook — "Site is down, what do I do?"

Use this section whenever `https://agenthub.creatingwow.in` is unreachable or returning an error.

### Step 1 — Quick health check (run these first)

```bash
# Are the backend services running?
sudo systemctl status infobeans-agent-hub      # should say: active (running)
sudo systemctl status infobeans-ppt-validator  # should say: active (running)
sudo systemctl status nginx                    # should say: active (running)

# Is the hub actually responding on its port?
curl -s -o /dev/null -w "Hub (8000):          HTTP %{http_code}\n" http://127.0.0.1:8000/
curl -s -o /dev/null -w "PPT Validator (8001): HTTP %{http_code}\n" http://127.0.0.1:8001/
```

**What the HTTP codes mean:**
| Code | Meaning |
|------|---------|
| 200 / 30x | Service is up and responding |
| 000 | Nothing is listening on that port — service is down |
| 502 | Nginx is up but the backend is down |
| 503 | Nginx is up but backend is overloaded or restarting |

---

### Step 2 — Start a stopped service

If `systemctl status` shows `inactive` or `failed`:

```bash
# Start the hub
sudo systemctl start infobeans-agent-hub
sudo systemctl status infobeans-agent-hub   # confirm it's now running

# Start the PPT validator
sudo systemctl start infobeans-ppt-validator
sudo systemctl status infobeans-ppt-validator

# Reload nginx if its config changed
sudo nginx -t                   # validate config first — must say "test is successful"
sudo systemctl reload nginx
```

If the service starts but immediately dies (status shows `failed`), go to Step 3.

---

### Step 3 — Reading logs

**Hub application logs** (most useful for errors):
```bash
# Live tail — shows new lines as they arrive (Ctrl+C to stop)
sudo tail -f /var/log/infobeans/hub-error.log

# Last 50 lines of access log
sudo tail -50 /var/log/infobeans/hub-access.log

# Systemd journal — includes startup failures that happen before file logging begins
sudo journalctl -u infobeans-agent-hub -n 100 --no-pager

# Follow the journal in real time while you try to start the service
sudo journalctl -u infobeans-agent-hub -f
```

**PPT Validator logs:**
```bash
sudo journalctl -u infobeans-ppt-validator -n 100 --no-pager
sudo journalctl -u infobeans-ppt-validator -f
```

**Nginx logs:**
```bash
sudo tail -f /var/log/nginx/error.log    # proxy and config errors
sudo tail -f /var/log/nginx/access.log  # incoming requests
```

**What to look for in log output:**

| Log pattern | Likely cause | Fix |
|-------------|--------------|-----|
| `KeyError` or `ValidationError` on env var | Missing or wrong value in `.env` | Edit `.env`, then `sudo systemctl restart infobeans-agent-hub` |
| `Can't connect to MySQL` / `OperationalError` | DB is down or wrong credentials | Check `sudo systemctl status mysql` and `DATABASE_URL` in `.env` |
| `Address already in use` on port 8000 | Another process grabbed the port | `sudo lsof -i :8000` to find it, then kill or stop it |
| `ModuleNotFoundError` | Missing Python package | `cd /var/www/html/infobeans-agent-portal && .venv/bin/pip install -r requirements.txt` |
| `SSL` errors in nginx log | Certificate expired or wrong path | Check cert expiry: `openssl x509 -enddate -noout -in config/ssl/fullchain.crt` |
| `connect() failed (111: Connection refused)` in nginx | Hub backend is down | Restart `infobeans-agent-hub` |

---

### Step 4 — Restart everything in order

When in doubt, restart in this order (bottom of the stack first):

```bash
# 1. Database (if it was restarted or crashed)
sudo systemctl restart mysql

# 2. Hub backend
sudo systemctl restart infobeans-agent-hub
sleep 3
curl -s -o /dev/null -w "Hub: HTTP %{http_code}\n" http://127.0.0.1:8000/

# 3. PPT Validator
sudo systemctl restart infobeans-ppt-validator
sleep 3
curl -s -o /dev/null -w "PPT Validator: HTTP %{http_code}\n" http://127.0.0.1:8001/

# 4. Nginx last (only after backends are confirmed up)
sudo nginx -t && sudo systemctl reload nginx
```

---

### Step 5 — If the systemd service isn't installed yet

If `systemctl status infobeans-agent-hub` says `Unit not found`, the service was never installed:

```bash
sudo cp /var/www/html/infobeans-agent-portal/config/infobeans-agent-hub.service \
        /etc/systemd/system/infobeans-agent-hub.service

sudo mkdir -p /var/log/infobeans
sudo chown www-data:www-data /var/log/infobeans

sudo systemctl daemon-reload
sudo systemctl enable infobeans-agent-hub    # auto-start on reboot
sudo systemctl start infobeans-agent-hub
sudo systemctl status infobeans-agent-hub
```

---

### Emergency: manual start (no sudo / no systemd)

If you cannot use systemd and just need the site up immediately:

```bash
cd /var/www/html/infobeans-agent-portal
bash start-all.sh
```

This starts both services in the background and prints their PIDs and HTTP status. Logs go to `/tmp/hub.log` and `/tmp/ppt-validator.log`. **This does not survive a reboot** — install the systemd service as soon as possible.

---

### Useful one-liners reference

```bash
# Check what's listening on port 8000
sudo lsof -i :8000

# Check what's listening on port 8001
sudo lsof -i :8001

# Check SSL certificate expiry
openssl x509 -enddate -noout \
  -in /var/www/html/infobeans-agent-portal/config/ssl/fullchain.crt

# View last 20 lines of all infobeans logs together
sudo tail -20 /var/log/infobeans/hub-error.log \
              /var/log/infobeans/hub-access.log

# Test the full HTTPS stack end-to-end
curl -I https://agenthub.creatingwow.in/
```
