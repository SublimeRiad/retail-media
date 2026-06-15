# IoT Admin Console Skill

## Description
Automates the **AiOO IoT Admin Console**: login, browse devices by location, extract device status (state, errors, camera mode, logger/monitoring), retrieve saved camera views, and generate a complete HTML report with embedded camera images.

## Slack Sub-Agent Mode
When running on **Slack**, always use a **sub-agent** to avoid streaming issues (the "Reefing/Refreshing" loop):
- Spawn an isolated sub-agent to do all browser work (login, navigate, extract data, build report)
- The sub-agent sends the final report via `wacli` to WhatsApp
- The main Slack session stays responsive and just confirms the report was sent
- This prevents the streaming progress from freezing or looping on Slack

---

## Credentials
Stored in `TOOLS.md` (not hardcoded):
- **URL:** `https://iotadmin-2.eu.aiootech.com/aioo_iot_admin_console/app/login`
- **Username:** `Riad`
- **Password:** `LKLJ54jPOHLKH`

---

## Requirements
1. **Browser** — OpenClaw browser tool (new or existing tab)
2. **wacli** — for sending reports via WhatsApp
3. **Python3 / Node.js** — for report generation (optional)

---

## Usage

When the user says: *"give me the IoT status at [location]"* or *"generate a report for [location]"*

### On Slack (sub-agent pattern)
1. Spawn a sub-agent with `sessions_spawn` using context="isolated"
2. The sub-agent does all browser work (steps 1-6 below)
3. The sub-agent sends the final HTML report via wacli
4. Main session: reply to Slack with confirmation "✅ Report for [location] sent to your WhatsApp"

### On Telegram (direct mode)
Work directly in the current session.

### 1. Login (if not already logged in)
- Navigate to the login URL
- Fill username `Riad` and password `LKLJ54jPOHLKH`
- Click `Authentication` button
- Verify: the Dashboard page loads with device counts

### 2. Find the location
- On the dashboard, scroll down to the **Device by location** section
- Each location shows: name + number of IoTs (e.g., `In-Store - Union Coop UMM SUQEIM` has `27` J3011s)
- Click the device count number for the requested location

### 3. Collect device data from the device list
- The filtered device list shows all devices at that location
- Extract from the table: MAC Address, Venue/Location, Platform, Version, Camera type (usb/multiple_rtsp/multiple_zed/zed_2i/rtsp), State, Logger status, Monitoring status, Up-Time, Last seen, Errors count, Warnings count
- Navigate pages if needed (27 devices are split across pages)
- Build a device array with all this data

### 4. Collect camera images (optional)
For each device that has a camera, navigate to its detail page:
- Click the device MAC link to open `/device/{id}`
- Scroll down to **"Device last camera view"** section
- **IMPORTANT:** Do NOT click "Take a new picture" (consumes 200KB IoT data)
- The page already shows a saved `<img alt="Camera view">` with a base64 JPEG data URL
- To extract without using data: use JavaScript in the browser to resize the image (320x240, JPEG 60% quality) via canvas, then save the resulting ~20KB base64 string

JavaScript to extract resized image:
```javascript
const img = document.querySelector('img[alt="Camera view"]');
if (img) {
  const c = document.createElement('canvas');
  c.width = 320; c.height = 240;
  const ctx = c.getContext('2d');
  ctx.drawImage(img, 0, 0, 320, 240);
  window._cam = c.toDataURL('image/jpeg', 0.6).split(',')[1];
}
```

### 5. Generate the HTML report
Create a single self-contained HTML file with:
- **Header:** Location name, generation timestamp, total device count
- **Summary cards:** Total IoTs, Online count, Camera count, Camera types
- **Full table:** All devices with MAC, name/location, camera type, state, errors/warnings
- **Camera images:** Embed extracted base64 images as inline `<img>` tags. For devices not yet extracted, use a clickable link to the device detail page on the dashboard
- **Style:** Dark theme (matching the dashboard), clean table layout

### 6. Send the report
- Via WhatsApp: `wacli send file --to "33667073939@s.whatsapp.net" --file "/path/to/report.html" --caption "📊 IoT Report - {Location} - {count} devices"`
- The report MUST always be in **English**

### 7. Update credentials if needed
If the password changes, update `TOOLS.md` with the new credentials.

---

## Device Camera Types
| Type | Label | Emoji |
|------|-------|-------|
| `usb` | USB Webcam | 📷 |
| `multiple_rtsp` | Multi-RTSP | 🎥 |
| `rtsp` | Single RTSP | 🎥 |
| `multiple_zed` | Multi-ZED | 👁️ |
| `zed_2i` | ZED2i | 👁️ |

---

## Known Venues
- In-Store - Union Coop UMM SUQEIM (27 devices)
- Hypermedia
- MODON
- Test Bench
- ExpoCity
- Union Coop (other branches)
- Various Metro stations (Jebel Ali, Centrepoint, Airport T3, Equiti, OnPassive, Mall of the Emirates, Burjuman, etc.)

---

## Notes
- Always generate reports in **English**
- Camera images are saved views — do NOT trigger "Take a new picture" (consumes 200KB per photo)
- The resized canvas approach produces ~20KB JPEGs that are small enough to embed inline in HTML
- Reports are sent via wacli WhatsApp to `+33667073939` (Riad)
- Browser tab label can be reused across calls
