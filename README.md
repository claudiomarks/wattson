# Wattson 🔋
*A lightweight battery management helper for Ubuntu laptop servers.*

Wattson helps you keep a laptop-as-a-server healthy by setting safe charge thresholds and avoiding unnecessary wear when the machine stays plugged in for long periods.

- Prevent overcharging by setting a **maximum charge threshold**.
- (Optional) Warn or act when charge falls below a **minimum threshold**.
- Run as a background service or inside Docker.

> **Note:** Not all laptops expose the same battery controls. Wattson targets systems that provide `/sys/class/power_supply/BAT*/charge_control_end_threshold`. If your hardware doesn’t support this, features that write thresholds won’t work.

---

## 📦 Quick start

### Option A — Run locally (Python)
```bash
git clone https://github.com/claudiomarks/wattson.git
cd wattson
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py --config config.yml
```

### Option B — Run with Docker Compose
Create a `docker-compose.yml` next to the repo (or use the one included) and start it:

```yaml
services:
  wattson:
    build: .
    container_name: wattson
    restart: unless-stopped
    # Wattson needs to see and (optionally) write battery sysfs entries.
    volumes:
      - /sys/class/power_supply:/sys/class/power_supply:rw
      - ./config.yml:/app/config.yml:ro
    # Writing to /sys may require elevated privileges depending on your distro/kernel.
    privileged: true
```

Then:
```bash
docker compose up -d --build
docker logs -f wattson
```

---

## ✅ Prerequisites & permissions

To write a new `charge_control_end_threshold` without being prompted for a password,
allow `tee` to write to that sysfs path via sudoers (use **visudo** to edit safely):

```bash
echo "$USER ALL=(ALL) NOPASSWD: /usr/bin/tee /sys/class/power_supply/BAT*/charge_control_end_threshold" | sudo tee -a /etc/sudoers
```

> ⚠️ **Security note:** Granting passwordless sudo for `tee` to that path gives your user write access to that specific sysfs file. Review before applying, and limit scope to exactly what you need. You can remove it later by editing `/etc/sudoers` with `visudo`.

On some hardware the threshold file may not exist or may be read-only. In that case, consult your vendor/ACPI module docs or consider vendor tools (e.g., TLP, asusctl, etc.).

---

## ⚙️ Configuration

Create a `config.yml` in the project root:

```yaml
# Example config.yml
battery_device: BAT0           # Your battery device (BAT0 or BAT1 are common)
max_charge: 80                 # Stop/limit charging near this % (if supported)
min_charge: 40                 # Optional: warn or act when below this %
check_interval: 60             # Seconds between checks
action_on_low: "log"           # "log" | "notify" | "shutdown" (if you implement)
log_level: "INFO"              # "DEBUG" | "INFO" | "WARNING" | "ERROR"
```

### CLI
```bash
python main.py --config config.yml
```

---

## 🧠 How it works (high level)

- Reads current percentage from `/sys/class/power_supply/${battery_device}/capacity`.
- If `max_charge` is defined and your kernel exposes `charge_control_end_threshold`, Wattson writes the threshold (e.g., 80) so the machine stops charging beyond that value.
- If `min_charge` is set, it can log/notify or take a user-defined action when the current capacity dips below the threshold (optional and up to your implementation).

---

## 🛠️ Systemd service (optional)

Create `/etc/systemd/system/wattson.service`:

```ini
[Unit]
Description=Wattson battery management
After=network.target

[Service]
WorkingDirectory=/opt/wattson
ExecStart=/opt/wattson/.venv/bin/python /opt/wattson/main.py --config /opt/wattson/config.yml
Restart=on-failure
# If you rely on writing to /sys, you may need these:
AmbientCapabilities=CAP_SYS_ADMIN
CapabilityBoundingSet=CAP_SYS_ADMIN

[Install]
WantedBy=multi-user.target
```

Then:
```bash
sudo systemctl daemon-reload
sudo systemctl enable --now wattson
```

---

## 🔍 Troubleshooting

- **`No such file or directory: charge_control_end_threshold`**  
  Your hardware/driver may not support it. Check what’s under `/sys/class/power_supply/` and look for vendor tools.

- **Permission denied when writing to /sys**  
  Revisit the sudoers entry above or run the service with the required capability. Inside Docker, `privileged: true` is often necessary for sysfs writes.

- **Battery device name differs**  
  Set `battery_device` to the actual one you see in `/sys/class/power_supply` (e.g., `BAT1`).

---

## 🗺️ Roadmap / ideas

- Desktop and webhook notifications
- Safer, granular permissions (dropping `privileged`)
- Auto-detection of supported battery controls per vendor
- Tests & CI (pytest + GitHub Actions)
- Packages (PyPI / deb)

---

## 🤝 Contributing

Issues and PRs are welcome! Please open an issue describing the problem/feature first. A `CONTRIBUTING.md` with coding style and dev setup is planned.

---

## 📜 License

MIT © 2025 Claudio Marques
