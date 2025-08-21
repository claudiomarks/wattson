import os
import psutil
import uvicorn
import logging
import time
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from threading import Thread

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
    
    return {
        "percent": round(battery.percent),
        "charging": battery.power_plugged,
        "secsleft": battery.secsleft,
        "temperature": temperature
    }

if __name__ == "__main__":
    # Start background monitor
    monitor_thread = Thread(target=battery_monitor, daemon=True)
    monitor_thread.start()

    port = int(os.getenv("PORT", 9090))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)