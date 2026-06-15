# NSOC Skill

## Description
Monitors **NUC/media player status and SIM data consumption** via GLPI, and is also used for **PC status requests**. Shows which devices (NUCs or PCs) are **online/offline** and their **data usage percentage** from the SIM card — helping identify connectivity issues and data depletion at a glance.

> 🎯 **Cible principale :** NUCs / media players
> 🖥️ **Usage secondaire :** répond aux demandes de statut des PCs

---

## What It Shows
| Data | Source | Example |
|---|---|---|
| Device Name | GLPI Computer name | `uMM-SUQEIM-H-C` |
| Tag (Agent ID) | `otherserial` | `845327152` |
| Location | GLPI Location | `Union Coop UMM SUQEIM` |
| Device Status | Online / Offline 🟢🔴 | `1227 online / 91 offline` |
| Data Consumption % | `percentfield` from `glpi_plugin_fields_computerdatas` | `98.68 % 🔴` |
| Comment | GLPI Comment | `Windows 10 Pro` |

---

## Requirements
1. **GLPI API Credentials** (set via env vars):
   - `GLPI_API_URL`: The URL of your GLPI API
   - `GLPI_APP_TOKEN`: Your GLPI application token
   - `GLPI_USER_TOKEN`: Your GLPI user token

2. **Dependencies**:
   - `curl`: For making HTTP requests.
   - `python3`: For parsing JSON responses.

---

## Usage

### 1. Source credentials
```bash
source .nsoc_creds
```

### 2. Run — Normal output
```bash
./skills/nsoc/nsoc.sh
```

### 3. Run — Client-friendly (for Slack)
```bash
./skills/nsoc/nsoc.sh --slack
```

### Slack Output Format
```
📡 NSOC Device Status
===================================
Online: 1227    Offline: 91

❌ uMM-SUQEIM-H-C
   Tag: 845327152
   Location: Union Coop UMM SUQEIM
   Data: 98.68 % 🔴
   Windows 10 Pro
===================================
Total: 1318 NUCs | 91 offline
```

Data % color coding:
- 🟢 0–50% — Low consumption
- 🟡 51–80% — Moderate consumption
- 🔴 >80% — High consumption (needs attention)

---

## Security
- **No hardcoded tokens** — credentials stored in `.nsoc_creds` (chmod 600)
- Source the creds file before running, or export the env vars yourself
- Never commit `.nsoc_creds` to version control

---

## Notes
- The script filters devices that are **not** in the "🟢" (green/online) state.
- This monitors **NUCs / media players** and can also answer **PC status requests**.
- If the API response is malformed, the script will display an error message.
- Ensure your GLPI instance is accessible from the machine running this script.
