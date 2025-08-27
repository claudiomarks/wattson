#!/usr/bin/env python3
"""
Test script for Wattson API
Tests all endpoints and displays formatted results
"""

import requests
import json
import time
from datetime import datetime

API_BASE = "http://localhost:5000/api"

def test_endpoint(endpoint, method="GET", data=None):
    """Test an API endpoint"""
    url = f"{API_BASE}{endpoint}"
    try:
        if method == "GET":
            response = requests.get(url, timeout=10)
        elif method == "POST":
            response = requests.post(url, json=data, timeout=10)
        
        if response.status_code == 200:
            return True, response.json()
        else:
            return False, f"HTTP {response.status_code}: {response.text}"
    except requests.exceptions.RequestException as e:
        return False, str(e)

def format_battery_info(battery_data):
    """Format battery information for display"""
    if not battery_data:
        return "No battery data available"
    
    lines = [
        f"🔋 Battery Status: {battery_data.get('status', 'Unknown')}",
        f"📊 Capacity: {battery_data.get('capacity', 'N/A')}%",
    ]
    
    if battery_data.get('voltage_now'):
        lines.append(f"⚡ Voltage: {battery_data['voltage_now']:.2f}V")
    
    if battery_data.get('current_now'):
        lines.append(f"🔌 Current: {battery_data['current_now']:.2f}A")
    
    if battery_data.get('power_now'):
        lines.append(f"💡 Power: {battery_data['power_now']:.1f}W")
    
    if battery_data.get('charge_control_end_threshold'):
        lines.append(f"🎯 Charge Limit: {battery_data['charge_control_end_threshold']}%")
    
    return "\n".join(lines)

def format_power_info(power_data):
    """Format power information for display"""
    if not power_data:
        return "No power data available"
    
    lines = []
    
    if power_data.get('cpu_power'):
        lines.append(f"💻 CPU Power: {power_data['cpu_power']:.1f}W")
    
    if power_data.get('gpu_power'):
        lines.append(f"🎮 GPU Power: {power_data['gpu_power']:.1f}W")
    
    if power_data.get('total_system_power'):
        lines.append(f"🔥 Total System: {power_data['total_system_power']:.1f}W")
    
    if not lines:
        return "⚠️  Power monitoring data not available"
    
    return "\n".join(lines)

def main():
    print("🔋 Wattson API Test Suite")
    print("=" * 50)
    
    # Test health endpoint
    print("\n1. Testing Health Check...")
    success, data = test_endpoint("/health")
    if success:
        print(f"✅ Health check passed")
        print(f"   Status: {data.get('status')}")
        print(f"   Monitoring: {data.get('monitoring')}")
    else:
        print(f"❌ Health check failed: {data}")
        return
    
    # Test status endpoint
    print("\n2. Testing Status Endpoint...")
    success, data = test_endpoint("/status")
    if success:
        print("✅ Status endpoint working")
        
        battery = data.get('battery')
        power = data.get('power')
        config = data.get('config')
        
        print("\n📋 Current Status:")
        print("-" * 30)
        print(format_battery_info(battery))
        print()
        print(format_power_info(power))
        
        if config:
            print(f"\n⚙️  Configuration:")
            print(f"   Max Charge: {config.get('max_charge', 'N/A')}%")
            print(f"   Min Charge: {config.get('min_charge', 'N/A')}%")
            print(f"   Device: {config.get('battery_device', 'N/A')}")
    else:
        print(f"❌ Status endpoint failed: {data}")
    
    # Test individual endpoints
    print("\n3. Testing Individual Endpoints...")
    
    # Battery endpoint
    success, data = test_endpoint("/battery")
    if success:
        print("✅ Battery endpoint working")
    else:
        print(f"❌ Battery endpoint failed: {data}")
    
    # Power endpoint  
    success, data = test_endpoint("/power")
    if success:
        print("✅ Power endpoint working")
    else:
        print(f"❌ Power endpoint failed: {data}")
    
    # Config endpoint
    success, data = test_endpoint("/config")
    if success:
        print("✅ Config endpoint working")
    else:
        print(f"❌ Config endpoint failed: {data}")
    
    # History endpoint
    success, data = test_endpoint("/history?hours=1")
    if success:
        battery_history = data.get('battery_history', [])
        power_history = data.get('power_history', [])
        print(f"✅ History endpoint working ({len(battery_history)} battery entries, {len(power_history)} power entries)")
    else:
        print(f"❌ History endpoint failed: {data}")
    
    # Test configuration update
    print("\n4. Testing Configuration Update...")
    test_config = {
        "max_charge": 85,
        "min_charge": 25
    }
    
    success, data = test_endpoint("/config", "POST", test_config)
    if success:
        print("✅ Configuration update working")
        print(f"   Message: {data.get('message')}")
        
        # Verify the update
        time.sleep(1)
        success, verify_data = test_endpoint("/config")
        if success and verify_data.get('max_charge') == 85:
            print("✅ Configuration update verified")
        else:
            print("⚠️  Configuration update not verified")
    else:
        print(f"❌ Configuration update failed: {data}")
    
    print("\n5. Testing Real-time Monitoring...")
    print("Collecting 3 samples over 6 seconds...")
    
    for i in range(3):
        success, data = test_endpoint("/status")
        if success:
            battery = data.get('battery', {})
            power = data.get('power', {})
            
            timestamp = datetime.now().strftime("%H:%M:%S")
            battery_power = battery.get('power_now', 0) or 0
            system_power = power.get('total_system_power', 0) or 0
            
            print(f"   {timestamp}: Battery={battery.get('capacity', 'N/A')}% "
                  f"({battery_power:.1f}W), System={system_power:.1f}W")
        
        if i < 2:  # Don't sleep after last iteration
            time.sleep(2)
    
    print("\n" + "=" * 50)
    print("🎉 Test Suite Complete!")
    print("\n🚀 If all tests passed, your Wattson API is ready!")
    print("📱 You can now connect your dashboard to: http://localhost:5000/api")
    print("\n📝 API Endpoints Available:")
    print("   GET  /api/health   - Health check")
    print("   GET  /api/status   - Complete status")
    print("   GET  /api/battery  - Battery details")
    print("   GET  /api/power    - Power consumption")
    print("   GET  /api/history  - Historical data")
    print("   GET  /api/config   - Current configuration")
    print("   POST /api/config   - Update configuration")

if __name__ == "__main__":
    main()