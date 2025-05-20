#!/bin/bash

cd "$(dirname "$0")"  # Navigate to script directory

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if the MQTT broker is already running
if docker ps | grep -q mqtt-host; then
    echo "MQTT broker is already running."
else
    # Start the MQTT broker using docker run with host networking
    echo "Starting MQTT broker..."
    
    docker run -d \
        --name mqtt-host \
        --network host \
        -e "MQTT_ALLOW_ANONYMOUS=true" \
        eclipse-mosquitto:latest
    
    if [ $? -eq 0 ]; then
        echo "MQTT broker started successfully with host networking."
        echo "You can now run the prediction service with:"
        echo "python prediction_service.py"
    else
        echo "Failed to start MQTT broker."
        exit 1
    fi
fi

# Show the status
docker ps | grep mqtt-host 