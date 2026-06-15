# IoT Onboard Skill

## Description
Automates the AiOO Sensor Onboarding process: logs into the onboarding portal, searches for a device by MAC address, and returns the result (screenshot + device details).

---

## Requirements
1. **Bitwarden CLI** (`bw`) — authenticated with API key + session unlocked
   - Item name: `AiOO Onboarding` (contains username + password)
2. **Browser** — OpenClaw browser tool with an active tab labeled `onboard`
3. **Python3** — for JSON parsing

---

## Usage

When the user says "run the iot onboard skill with MAC XX:XX:XX:XX:XX:XX":

### 1. Fetch credentials from Bitwarden
```bash
export BW_SESSION="<active_session_token>"
bw get item "AiOO Onboarding"
```
Extract `username` and `password` from the login field.

### 2. Open the onboard page (if not already open)
Open `https://iotadmin-2.eu.aiootech.com/onboard/` in the browser with label `onboard`.

### 3. Login
- Type the username into the `Username` textbox
- Type the password into the `Password` textbox
- Click the `Login` button

### 4. Enter MAC address
- Locate the `Device MAC*` textbox (placeholder: `12:34:56:78:9a:bc`)
- Clear and type the requested MAC address
- Click the `Search` button

### 5. Wait for camera to load
- After Search, snapshot the page
- Check Camera status — if it shows "In progress...", wait a few seconds and snapshot again
- Repeat until Camera status shows "OK" (may take 5-15 seconds)

### 6. Capture result
- Take a full-page screenshot showing device info + camera feed
- Present the result with: hardware, MAC, device state, camera status

---

## Example MACs
- `A1-00-5E-ED-02-7E` — Auvidea JNX42/JNX30, READY state

---

## Notes
- Credentials are fetched from Bitwarden — never hardcoded or stored on disk
- If the session token is expired, re-auth with `bw login --apikey` then `bw unlock`
- Works with any valid MAC address in the system
