#!/usr/bin/env python3
"""
Adapter to connect the prediction service to the MQTT bridge.
This allows the prediction service to send signals to Hummingbot without a full MQTT broker.
"""
import time
import json
import threading
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MQTTClientAdapter:
    """
    Adapter class that mimics the MQTT client interface used by prediction_service.py
    but connects to our custom message bridge instead of a real MQTT broker.
    """
    
    def __init__(self):
        self.connected = False
        self.message_callbacks = []
        self.connect_callbacks = []
        self.disconnect_callbacks = []
        self.subscriptions = set()
        
    def connect(self, host, port):
        """Connect to the message bridge"""
        try:
            # Import the bridge here to avoid circular imports
            from mqtt_bridge import get_bridge
            self.bridge = get_bridge()
            
            # Make sure the bridge is running
            if not getattr(self.bridge, 'running', False):
                self.bridge.start()
                
            self.connected = True
            
            # Call the connect callbacks with success code (0)
            for callback in self.connect_callbacks:
                callback(self, None, None, 0)
                
            logger.info(f"Connected to message bridge")
            return 0
        except Exception as e:
            logger.error(f"Failed to connect to message bridge: {e}")
            return 1
            
    def disconnect(self):
        """Disconnect from the message bridge"""
        if self.connected:
            self.connected = False
            
            # Call the disconnect callbacks with success code (0)
            for callback in self.disconnect_callbacks:
                callback(self, None, 0)
                
            logger.info("Disconnected from message bridge")
            
    def loop_start(self):
        """Start the message loop"""
        # Nothing to do, the bridge handles this
        pass
        
    def loop_stop(self):
        """Stop the message loop"""
        # Nothing to do, the bridge handles this
        pass
        
    def on_connect(self, callback):
        """Register a callback for when the client connects"""
        self.connect_callbacks.append(callback)
        
    def on_disconnect(self, callback):
        """Register a callback for when the client disconnects"""
        self.disconnect_callbacks.append(callback)
        
    def on_message(self, callback):
        """Register a callback for when a message is received"""
        self.message_callbacks.append(callback)
        
    def publish(self, topic, payload, qos=0, retain=False):
        """Publish a message to a topic"""
        if not self.connected:
            logger.error("Cannot publish: not connected")
            class Result:
                rc = 1  # Error code
            return Result()
            
        try:
            # Convert payload to string if needed
            if isinstance(payload, bytes):
                payload = payload.decode('utf-8')
            elif not isinstance(payload, str):
                payload = json.dumps(payload)
                
            # Publish via the bridge
            self.bridge.publish(topic, payload, retain=retain)
            
            class Result:
                rc = 0  # Success code
            return Result()
        except Exception as e:
            logger.error(f"Failed to publish message: {e}")
            class Result:
                rc = 1  # Error code
            return Result()
            
    def subscribe(self, topic):
        """Subscribe to a topic"""
        if not self.connected:
            logger.error("Cannot subscribe: not connected")
            return 1
            
        try:
            # Create a callback that will route messages to all registered on_message callbacks
            def bridge_callback(topic, payload):
                class Message:
                    def __init__(self, t, p):
                        self.topic = t
                        self.payload = p.encode('utf-8') if isinstance(p, str) else p
                        
                    def decode(self):
                        return self.payload.decode('utf-8') if isinstance(self.payload, bytes) else self.payload
                        
                msg = Message(topic, payload)
                for callback in self.message_callbacks:
                    callback(self, None, msg)
                    
            # Subscribe via the bridge
            self.bridge.subscribe(topic, bridge_callback)
            self.subscriptions.add((topic, bridge_callback))
            
            logger.info(f"Subscribed to {topic}")
            return 0
        except Exception as e:
            logger.error(f"Failed to subscribe to {topic}: {e}")
            return 1

# Monkey patch the mqtt.Client class to use our adapter
try:
    import paho.mqtt.client as mqtt
    
    # Save the original Client class
    OriginalClient = mqtt.Client
    
    # Replace with our adapter
    def patched_client(*args, **kwargs):
        return MQTTClientAdapter()
        
    mqtt.Client = patched_client
    logger.info("Successfully patched MQTT client")
except ImportError:
    logger.warning("Could not patch MQTT client: paho.mqtt not found")
    
if __name__ == "__main__":
    # Test the adapter
    import sys
    
    # Start the bridge
    from mqtt_bridge import get_bridge
    bridge = get_bridge()
    bridge.start()
    
    # Create an adapter instance
    client = MQTTClientAdapter()
    
    # Define callbacks
    def on_connect(client, userdata, flags, rc):
        print(f"Connected with result code {rc}")
        client.subscribe("test/topic")
        
    def on_message(client, userdata, msg):
        print(f"Received message on {msg.topic}: {msg.decode()}")
        
    # Register callbacks
    client.on_connect = on_connect
    client.on_message = on_message
    
    # Connect to the bridge
    client.connect("localhost", 1883)
    client.loop_start()
    
    # Publish a message every second for 10 seconds
    for i in range(10):
        client.publish("test/topic", f"Test message {i}")
        time.sleep(1)
        
    # Disconnect
    client.loop_stop()
    client.disconnect()
    
    print("Test completed successfully") 