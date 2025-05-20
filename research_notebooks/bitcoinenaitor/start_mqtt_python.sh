#!/bin/bash

cd "$(dirname "$0")"  # Navigate to script directory

# Activate conda environment
eval "$($HOME/miniconda3/bin/conda shell.bash hook)"
conda activate quants-lab

# Check if mqtt-broker is installed
if ! python -c "import mqtt_broker" &>/dev/null; then
    echo "Installing mqtt-broker..."
    pip install mqtt-broker
fi

# Start the MQTT broker in the background
echo "Starting Python MQTT broker..."
python simple_mqtt_broker.py &
BROKER_PID=$!

# Wait for broker to start
sleep 2

# Check if broker is running
if ps -p $BROKER_PID > /dev/null; then
    echo "MQTT broker is running with PID $BROKER_PID"
    echo "You can now run the prediction service with:"
    echo "python prediction_service.py"
    echo ""
    echo "To stop the broker, run:"
    echo "kill $BROKER_PID"
    
    # Save PID to a file for later reference
    echo $BROKER_PID > .mqtt_broker.pid
else
    echo "Failed to start MQTT broker."
    exit 1
fi 