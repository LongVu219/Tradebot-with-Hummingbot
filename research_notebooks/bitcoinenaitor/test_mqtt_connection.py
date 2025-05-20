#!/usr/bin/env python3
"""
Test MQTT connection to an external broker.
"""
import time
import paho.mqtt.client as mqtt
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Callback when the client connects
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        logger.info("Connected to MQTT broker successfully")
        # Subscribe to a test topic
        client.subscribe("test/topic")
        logger.info("Subscribed to test/topic")
        
        # Publish a test message
        client.publish("test/topic", "Hello from Python", qos=1)
        logger.info("Published test message")
    else:
        logger.error(f"Failed to connect to MQTT broker with code {rc}")

# Callback when a message is received
def on_message(client, userdata, msg):
    logger.info(f"Received message on {msg.topic}: {msg.payload.decode()}")

# Callback when a message is published
def on_publish(client, userdata, mid):
    logger.info(f"Message {mid} published successfully")

# Callback when subscription succeeds
def on_subscribe(client, userdata, mid, granted_qos):
    logger.info(f"Subscribed with QoS {granted_qos}")

# Test connection to an external broker
def test_external_broker():
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message
    client.on_publish = on_publish
    client.on_subscribe = on_subscribe
    
    # Connect to the external broker
    logger.info("Connecting to test.mosquitto.org...")
    client.connect("test.mosquitto.org", 1883, 60)
    
    # Start the network loop
    client.loop_start()
    
    # Wait for a while to observe messages
    try:
        for i in range(10):
            time.sleep(1)
            if i % 3 == 0:
                client.publish("test/topic", f"Periodic message {i}", qos=1)
    except KeyboardInterrupt:
        pass
    finally:
        client.loop_stop()
        client.disconnect()
        logger.info("Disconnected from MQTT broker")

if __name__ == "__main__":
    test_external_broker() 