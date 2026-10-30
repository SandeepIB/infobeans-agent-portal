# InfoBeans Agent Hub — Server Setup Guide

**Target server:** `agenthub-new` (144.79.8.82, user: `infoadmin`, port: 28274)  
**Project path:** `/var/www/html/infobeans-agent-portal`  
**PPT Validator path:** `/var/www/html/ib-ppt-validator`

Run all commands as `infoadmin` unless noted. Commands marked `[sudo]` require `sudo`.

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
