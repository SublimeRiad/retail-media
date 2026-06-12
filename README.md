# Retail Media — IoT Device Status Dashboard

Live dashboard for monitoring retail IoT devices across Union Coop, Lulu, and Carrefour venues in Dubai.

## 🔗 Dashboard

**[sublimeriad.github.io/retail-media/rmstatus.html](https://sublimeriad.github.io/retail-media/rmstatus.html)**

## 📊 What It Shows

- **Global metrics**: total devices, ok, warnings, errors, platform info
- **Per-brand cards**: Union Coop (Umm Suqeim, Al Warqa), Lulu (Al Wahda)
- **Camera carousels**: rotating CCTV snapshots per venue (CSS-only, no JS)
- **Alerts table**: devices with errors/warnings needing attention

## 🔄 Auto-Update

The dashboard is automatically rebuilt and deployed **every 2 hours** via cron:

```bash
*/120 * * * * /home/iots/.openclaw/workspace/iot-camera/scripts/update-rmstatus.sh
```

The script:
1. Scrapes latest device status from IoT Admin Console
2. Generates rmstatus.html with embedded camera images
3. Pushes to GitHub Pages

## 🏪 Venues

| Brand | Location | Devices |
|-------|----------|--------|
| Union Coop | Umm Suqeim | 27 |
| Union Coop | Al Warqa | 33 |
| Lulu | Al Wahda | 37 |
| **Total** | | **97** |

## 🛠 Tech

- **Runtime**: Node.js + sharp for image processing
- **Hosting**: GitHub Pages
- **Automation**: OpenClaw cron
- **Data source**: IoT Admin Console API

---

*Maintained by AiOO Tech Dubai*
