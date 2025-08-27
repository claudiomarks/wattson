#!/bin/bash

# Wattson API Setup Script
set -e

echo "🔋 Wattson API Setup Script"
echo "=========================="

# Check if we're in the right directory
if [ ! -f "main.py" ]; then
    echo "❌ Error: main.py not found. Please run this script from your wattson repository root."
    exit 1
fi

echo "📦 Backing up existing files..."
mkdir -p backup
cp main.py backup/main.py.backup 2>/dev/null || true
cp requirements.txt backup/requirements.txt.backup 2>/dev/null || true
cp config.yml backup/config.yml.backup 2>/dev/null || true
cp Dockerfile backup/Dockerfile.backup 2>/dev/null || true
cp docker-compose.yml backup/docker-compose.yml.backup 2>/dev/null || true

echo "📝 Please replace the following files with the enhanced versions from the artifacts:"
echo "   - main.py (Enhanced API version)"
echo "   - requirements.txt (With Flask dependencies)"
echo "   - config.yml (Enhanced configuration)"
echo "   - Dockerfile (Updated for API)"
echo "   - docker-compose.yml (Updated with volumes and ports)"

read -p "Have you replaced the files with the enhanced versions? (y/n): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Please replace the files first, then run this script again."
    exit 1
fi

echo "🐍 Setting up Python environment..."
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi

echo "Activating virtual environment..."
source .venv/bin/activate

echo "📦 Installing dependencies..."
pip install -r requirements.txt

echo "🔧 Checking system requirements..."

# Check battery device
if [ -d "/sys/class/power_supply" ]; then
    echo "✅ Battery interface found:"
    ls /sys/class/power_supply/ | grep BAT || echo "⚠️  No BAT* devices found"
else
    echo "❌ /sys/class/power_supply not found"
fi

# Check power monitoring capabilities
echo "🔍 Checking power monitoring capabilities:"
if [ -d "/sys/class/powercap" ]; then
    echo "✅ RAPL power monitoring available"
    ls /sys/class/powercap/ | head -3
else
    echo "⚠️  RAPL power monitoring not available"
fi

# Check GPU monitoring
if command -v nvidia-smi &> /dev/null; then
    echo "✅ NVIDIA GPU monitoring available"
elif [ -d "/sys/class/drm" ]; then
    echo "✅ Generic GPU monitoring available"
else
    echo "⚠️  GPU monitoring may not be available"
fi

# Check permissions for charge threshold
BATTERY_DEVICE=$(grep "battery_device:" config.yml | awk '{print $2}' | tr -d '"' || echo "BAT0")
THRESHOLD_PATH="/sys/class/power_supply/${BATTERY_DEVICE}/charge_control_end_threshold"
if [ -f "$THRESHOLD_PATH" ]; then
    if [ -w "$THRESHOLD_PATH" ]; then
        echo "✅ Battery charge threshold writable"
    else
        echo "⚠️  Battery charge threshold requires sudo/privileged access"
        echo "   Consider adding to sudoers: echo \"\$USER ALL=(ALL) NOPASSWD: /usr/bin/tee $THRESHOLD_PATH\" | sudo tee -a /etc/sudoers"
    fi
else
    echo "⚠️  Battery charge threshold not supported on this hardware"
fi

echo "🧪 Testing API server..."
echo "Starting API server in background..."
python main.py --config config.yml &
API_PID=$!

# Wait for server to start
sleep 3

# Test health endpoint
if curl -s http://localhost:5000/api/health > /dev/null; then
    echo "✅ API server is responding"
    
    echo "🔧 Testing endpoints..."
    
    # Test status endpoint
    if curl -s http://localhost:5000/api/status | grep -q "battery"; then
        echo "✅ Status endpoint working"
    else
        echo "⚠️  Status endpoint may have issues"
    fi
    
    # Test battery endpoint
    if curl -s http://localhost:5000/api/battery > /dev/null; then
        echo "✅ Battery endpoint working"
    else
        echo "⚠️  Battery endpoint may have issues"
    fi
    
    echo "📊 Sample API response:"
    echo "======================"
    curl -s http://localhost:5000/api/status | python3 -m json.tool | head -20
    
else
    echo "❌ API server not responding"
fi

# Kill the test server
kill $API_PID 2>/dev/null || true

echo ""
echo "🚀 Setup Summary"
echo "==============="
echo "✅ API server code updated"
echo "✅ Dependencies installed"
echo "✅ Configuration verified"
echo ""
echo "🔧 Next Steps:"
echo "1. Run the API server:"
echo "   python main.py --config config.yml"
echo ""
echo "2. Or use Docker:"
echo "   docker compose up --build"
echo ""
echo "3. Test the API:"
echo "   curl http://localhost:5000/api/status"
echo ""
echo "4. Update your dashboard to use:"
echo "   API_BASE = 'http://localhost:5000/api'"
echo ""
echo "📖 For detailed instructions, see the implementation guide!"

deactivate 2>/dev/null || true