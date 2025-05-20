#!/bin/bash

cd "$(dirname "$0")"  # Navigate to script directory

# Check if Mosquitto is already running
if pgrep -x "mosquitto" > /dev/null; then
    echo "Mosquitto is already running."
else
    # Create config directory if it doesn't exist
    mkdir -p mqtt_config
    
    # Create a minimal config file
    cat > mqtt_config/mosquitto.conf << EOL
listener 1883
allow_anonymous true
EOL

    # Start Mosquitto with the config file
    echo "Starting Mosquitto MQTT broker..."
    mosquitto -c mqtt_config/mosquitto.conf -d
    
    if [ $? -eq 0 ]; then
        echo "Mosquitto MQTT broker started successfully."
        echo "You can now run the prediction service with:"
        echo "python prediction_service.py"
    else
        echo "Failed to start Mosquitto MQTT broker."
        
        # Try a fallback approach using Python
        echo "Trying to start Python MQTT broker..."
        nohup python simple_mqtt_server.py > mqtt_broker.log 2>&1 &
        BROKER_PID=$!
        
        # Wait for broker to start
        sleep 2
        
        # Check if broker is running
        if ps -p $BROKER_PID > /dev/null; then
            echo "Python MQTT broker started with PID $BROKER_PID"
            echo "You can now run the prediction service with:"
            echo "python prediction_service.py"
            
            # Save PID to a file for later reference
            echo $BROKER_PID > .mqtt_broker.pid
        else
            echo "Failed to start Python MQTT broker."
            echo "Try running the prediction service with MQTT disabled:"
            echo "python prediction_service.py --disable-mqtt"
            exit 1
        fi
    fi
fi

# Display instructions
echo ""
echo "=== Next steps ==="
echo "1. Run prediction service:"
echo "   cd $(pwd)"
echo "   conda activate quants-lab"
echo "   python prediction_service.py"
echo ""
echo "2. In Hummingbot terminal:"
echo "   connect binance_paper_trade"
echo "   run_script ml_signal_listener" 