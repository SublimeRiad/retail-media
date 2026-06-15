# IoT Health Skill

## Description
Checks connectivity and status of all known IoT devices — ping, SSH access, and camera status.

Usage: `bash skills/iot-health/health.sh`

---

## Output
```
🔍 Health check for 3 IoT devices...

📍 192.168.30.109 (3C:6D:66:BA:54:3F)
   ✅ Ping OK
   ✅ SSH OK (aioo_j30_2026)
   ❌ Camera KO (A1-00-5E-ED-01-6D)

📍 192.168.30.161 (3C:6D:66:BA:47:B4)
   ✅ Ping OK
   ✅ SSH OK
   ❌ Camera KO (A1-00-5E-ED-01-6C)

📍 192.168.31.6 (3C:6D:66:BA:57:87)
   ✅ Ping OK
   ✅ SSH OK
   ❌ Camera KO (A1-00-5E-ED-02-DF)

━━━━━━━━━━━━━━━━━━
3/3 online  |  0/3 cameras OK
```
