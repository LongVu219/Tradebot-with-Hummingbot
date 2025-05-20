#!/bin/bash

# Navigate to script directory
cd "$(dirname "$0")"

# Get the full path to Python
PYTHON_PATH=$(which python)
echo "Using Python from: $PYTHON_PATH"

# Start MQTT bridge in the background
echo "Starting MQTT bridge..."
$PYTHON_PATH mqtt_bridge.py > mqtt_bridge.log 2>&1 &
BRIDGE_PID=$!
echo "Bridge process started with PID $BRIDGE_PID"

# Wait for bridge to start
sleep 5

# Check if bridge is running
if ps -p $BRIDGE_PID > /dev/null; then
    echo "MQTT bridge started with PID $BRIDGE_PID"
    echo $BRIDGE_PID > .mqtt_bridge.pid
else
    echo "Failed to start MQTT bridge"
    echo "Check mqtt_bridge.log for details"
    cat mqtt_bridge.log
    exit 1
fi

# Create a simple wrapper script to ensure adapter is loaded
echo "Creating prediction service wrapper..."
cat > run_prediction_service.py << 'EOF'
#!/usr/bin/env python3
# Import adapter first to patch MQTT client
import prediction_service_adapter
print("Adapter loaded and MQTT client patched")

# Now run the prediction service
import prediction_service
import asyncio

if __name__ == "__main__":
    print("Starting prediction service with patched MQTT client")
    asyncio.run(prediction_service.main())
EOF

# Make the wrapper executable
chmod +x run_prediction_service.py

# Display instructions for starting the prediction service
echo ""
echo "=== ML Trading Pipeline Setup ====="
echo "1. MQTT Bridge is running with PID $BRIDGE_PID"
echo "2. To run the prediction service with MQTT support:"
echo "   conda activate quants-lab"
echo "   $PYTHON_PATH run_prediction_service.py"
echo ""
echo "3. In Hummingbot terminal:"
echo "   connect kucoin_paper_trade"
echo "   run_script ml_signal_listener"
echo ""
echo "To stop the MQTT bridge when done:"
echo "   kill $(cat .mqtt_bridge.pid)" 