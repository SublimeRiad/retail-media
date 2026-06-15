# TOOLS.md - Local Notes

## IoT Admin Console
- URL: https://iotadmin-2.eu.aiootech.com/aioo_iot_admin_console/app/login
- Username: Riad
- Password: LKLJ54jPOHLKH
- Login fields: input[name="dashboard_login"], input[name="dashboard_password"]

## Gotify Push Notifications
- URL: http://localhost:8090
- Token: Ac8-pylKp3tvcMd
- Installé via systemd user service (port 8090)
- Notifie sur succès/échec des builds dashboards

## IoT Camera Capture
Script Puppeteer qui capture automatiquement les caméras IoT.

**Emplacement:** `~/workspace/iot-camera/capture-cameras.js`
**Images sauvegardées:**
- `~/workspace/iot-camera/ummu-suqeim/` — 15 appareils
- `~/workspace/iot-camera/al-warqa/` — 15 appareils

**Cron:** Toutes les 2h (crontab + OpenClaw job)

## What Goes Here

Things like:

- Camera names and locations
- SSH hosts and aliases
- Preferred voices for TTS
- Speaker/room names
- Device nicknames
- Anything environment-specific

## Examples

```markdown
### Cameras

- living-room → Main area, 180° wide angle
- front-door → Entrance, motion-triggered

### SSH

- home-server → 192.168.1.100, user: admin

### TTS

- Preferred voice: "Nova" (warm, slightly British)
- Default speaker: Kitchen HomePod
```

## Why Separate?

Skills are shared. Your setup is yours. Keeping them apart means you can update skills without losing your notes, and share skills without leaking your infrastructure.

---

Add whatever helps you do your job. This is your cheat sheet.
