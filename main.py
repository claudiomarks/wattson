import os
import psutil
import uvicorn
import logging
import time
import glob
import subprocess
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from threading import Thread
from pydantic import BaseModel

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# Configure logging
logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(message)s",
    level=logging.INFO
)

# Global state for monitoring
last_status = {
    "percent": None,
    "charging": None
}

class ChargeLimit(BaseModel):
    limit: int

def detect_charge_limit_support():
    """Detect if the system supports charge limiting."""
    # Common paths for different laptop brands
    paths_to_check = [
        # ThinkPad
        "/sys/class/power_supply/BAT*/charge_control_end_threshold",
        "/sys/class/power_supply/BAT*/charge_stop_threshold",
        # ASUS
        "/sys/class/power_supply/BAT*/charge_control_end_threshold",
        # Dell
        "/sys/class/power_supply/BAT*/charge_control_end_threshold",
        # HP
        "/sys/class/power_supply/BAT*/charge_control_end_threshold",
    ]
    
    for path_pattern in paths_to_check:
        matching_paths = glob.glob(path_pattern)
        if matching_paths:
            # Test if we can read/write
            for path in matching_paths:
                try:
                    with open(path, 'r') as f:
                        current_value = f.read().strip()
                    return {"supported": True, "path": path, "current": int(current_value)}
                except (OSError, ValueError, PermissionError):
                    continue
    
    return {"supported": False, "path": None, "current": None}

def get_charge_limit():
    """Get current charge limit setting."""
    support_info = detect_charge_limit_support()
    if support_info["supported"]:
        return support_info["current"]
    return None

def set_charge_limit(limit: int):
    """Set charge limit (requires root privileges)."""
    support_info = detect_charge_limit_support()
    
    if not support_info["supported"]:
        raise Exception("Charge limiting not supported on this system")
    
    if not (20 <= limit <= 100):
        raise Exception("Limit must be between 20 and 100")
    
    try:
        # Try to write directly (if running with sufficient privileges)
        with open(support_info["path"], 'w') as f:
            f.write(str(limit))
        return True
    except PermissionError:
        # Try using sudo
        try:
            cmd = ["sudo", "tee", support_info["path"]]
            process = subprocess.run(cmd, input=str(limit), text=True, 
                                   capture_output=True, check=True)
            return True
        except subprocess.CalledProcessError as e:
            raise Exception(f"Failed to set charge limit: {e}")

def get_battery_temperature():
    """Get battery temperature if available."""
    try:
        temps = psutil.sensors_temperatures()
        # Try common battery temperature sensor names
        for name, sensors in temps.items():
            if 'bat' in name.lower() or 'battery' in name.lower():
                for sensor in sensors:
                    return round(sensor.current, 1)
        
        # Fallback: try ACPI thermal zones which might include battery
        if 'acpi_thermal_zone' in temps:
            for sensor in temps['acpi_thermal_zone']:
                if 'battery' in sensor.label.lower() or 'bat' in sensor.label.lower():
                    return round(sensor.current, 1)
        
        # If no specific battery temp found, try coretemp as fallback
        if 'coretemp' in temps and temps['coretemp']:
            return round(temps['coretemp'][0].current, 1)
            
    except Exception as e:
        logging.debug(f"Could not get battery temperature: {e}")
    
    return None

def battery_monitor():
    """Background thread that logs battery events."""
    global last_status
    while True:
        battery = psutil.sensors_battery()
        if not battery:
            logging.warning("No battery detected.")
            time.sleep(30)
            continue

        # Detect changes
        if battery.percent != last_status["percent"]:
            logging.info(f"Battery level: {battery.percent}%")
            last_status["percent"] = battery.percent

            if battery.percent <= 20 and not battery.power_plugged:
                logging.warning("⚠️ Battery low (<=20%)!")

        if battery.power_plugged != last_status["charging"]:
            status = "⚡ Charging" if battery.power_plugged else "🔋 Discharging"
            logging.info(f"Power state changed: {status}")
            last_status["charging"] = battery.power_plugged

        time.sleep(60)  # check every minute

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/api/battery")
def battery_status():
    battery = psutil.sensors_battery()
    temperature = get_battery_temperature()
    charge_limit = get_charge_limit()
    support_info = detect_charge_limit_support()
    
    return {
        "percent": round(battery.percent),
        "charging": battery.power_plugged,
        "secsleft": battery.secsleft,
        "temperature": temperature,
        "charge_limit": charge_limit,
        "charge_limit_supported": support_info["supported"]
    }

@app.post("/api/charge-limit")
async def set_battery_limit(charge_limit: ChargeLimit):
    """Set battery charge limit."""
    try:
        success = set_charge_limit(charge_limit.limit)
        if success:
            logging.info(f"Charge limit set to {charge_limit.limit}%")
            return {"success": True, "message": f"Charge limit set to {charge_limit.limit}%"}
    except Exception as e:
        logging.error(f"Failed to set charge limit: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/charge-limit")
def get_battery_limit():
    """Get current charge limit."""
    support_info = detect_charge_limit_support()
    return {
        "supported": support_info["supported"],
        "current_limit": support_info["current"]
    }

if __name__ == "__main__":
    # Check charge limit support on startup
    support = detect_charge_limit_support()
    if support["supported"]:
        logging.info(f"⚡ Charge limiting supported! Current limit: {support['current']}%")
        logging.info(f"📁 Using path: {support['path']}")
    else:
        logging.warning("⚠️ Charge limiting not supported on this system")
    
    # Start background monitor
    monitor_thread = Thread(target=battery_monitor, daemon=True)
    monitor_thread.start()

    port = int(os.getenv("PORT", 9090))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)