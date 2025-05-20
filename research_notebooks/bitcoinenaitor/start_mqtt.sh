#!/bin/bash

cd "$(dirname "$0")"  # Navigate to script directory

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "Docker is not installed. Please install Docker first."
    exit 1
fi

# Make sure the directories exist
mkdir -p mosquitto/config mosquitto/data mosquitto/log

# Copy the configuration if it doesn't exist
if [ ! -f "mosquitto/config/mosquitto.conf" ]; then
    cat > mosquitto/config/mosquitto.conf << EOL
# Mosquitto MQTT broker configuration
listener 1883
allow_anonymous true

# Persistence
persistence true
persistence_location /mosquitto/data/

# Logging
log_dest file /mosquitto/log/mosquitto.log
log_dest stdout
EOL
    echo "Created mosquitto configuration file."
fi

# Clean up any existing stopped container with the same name
docker rm -f mqtt-broker 2>/dev/null || true

# Check if the MQTT broker is already running
if docker ps | grep -q mqtt-broker; then
    echo "MQTT broker is already running."
else
    # Start the MQTT broker using docker run with minimal options
    echo "Starting MQTT broker..."
    
    docker run -d \
        --name mqtt-broker \
        -p 1883:1883 \
        -v "$(pwd)/mosquitto/config:/mosquitto/config" \
        eclipse-mosquitto:latest
    
    if [ $? -eq 0 ]; then
        echo "MQTT broker started successfully."
        echo "You can now run the prediction service with:"
        echo "python prediction_service.py"
    else
        echo "Failed to start MQTT broker."
        exit 1
    fi
fi

# Show the status
docker ps | grep mqtt-broker 