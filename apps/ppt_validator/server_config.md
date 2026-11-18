# Server Configuration — InfoBeans PPT Validator

**Server:** `192.168.4.144`
**App URL:** `http://192.168.4.144:8080/app/`
**API Docs:** `http://192.168.4.144:8080/docs`
**Legacy UI:** `http://192.168.4.144:8080/`

---

## Service Management

```bash
# Start
systemctl --user start ppt-validator

# Stop
systemctl --user stop ppt-validator

# Restart
systemctl --user restart ppt-validator

# Status
systemctl --user status ppt-validator
```

---

## Logs

```bash
# Live log stream
journalctl --user -u ppt-validator -f

# Last 100 lines
journalctl --user -u ppt-validator -n 100

# Logs since last boot
journalctl --user -u ppt-validator -b
```

---

## Rebuild Frontend (after UI changes)

```bash
source ~/.nvm/nvm.sh && nvm use 22
cd /var/www/html/ib-ppt-validator/frontend
npm run build
systemctl --user restart ppt-validator
```

---

## Auto-start on Reboot

The service is managed by **systemd user service** with linger enabled.
It starts automatically on boot without requiring a login session.

Service file: `~/.config/systemd/user/ppt-validator.service`

```bash
# Check linger status
loginctl show-user sgupta | grep Linger

# Enable auto-start (already done)
systemctl --user enable ppt-validator
```
