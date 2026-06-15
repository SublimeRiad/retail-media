# IoT Deploy Skill

## Description
Finds **IoT devices (NVIDIA J30 modules)** on the network and optionally deploys the software stack.

- 🔍 **Scan mode** — Just find & list IoTs on the network
- 🚀 **Deploy mode** — Find IoTs, install software, collect data, report to Telegram

---

## Usage

### Scan — Find IoTs on the network
```bash
source .iot_deploy_creds
bash skills/iot-deploy/deploy.sh --scan
```

Output:
```
🔍 Scanning network for IoT devices...
✅ Found 3 IoT device(s):

   📍 192.168.31.100  →  3c:6d:ff:ab:cd:ef
   📍 192.168.31.101  →  54:ef:33:12:34:56
   📍 192.168.31.102  →  3c:6d:ff:98:76:54

────────────────────────────────
Total: 3 IoT device(s) detected
```

### Deploy — Install software on all found IoTs
```bash
source .iot_deploy_creds
bash skills/iot-deploy/deploy.sh
```

---

## What It Does
| Step | Description |
|---|---|
| 1. Scan | `nmap` sweep across configured network ranges |
| 2. Filter | Only NVIDIA / `3c:6d` / `54:ef:33` MACs |
| 3. Connect | SSH with initial password, copy install scripts |
| 4. Install | Download bootstrap from GitHub, run it |
| 5. Collect | Read device ID + Ethernet MAC from each IoT |
| 6. Report | Send inventory to Telegram |

---

## Files
| File | Purpose |
|---|---|
| `skills/iot-deploy/deploy.sh` | Main script (scan & deploy) |
| `skills/iot-deploy/SKILL.md` | This file |
| `iot_s/scp_info_send.sh` | Runs on each device to collect ID + MAC |
| `iot_s/All_in_one.sh` | Additional install script |
| `.iot_deploy_creds` | All credentials (env vars, chmod 644) |
