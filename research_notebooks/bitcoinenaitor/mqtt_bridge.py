#!/usr/bin/env python3
"""
A simple MQTT message relay service that doesn't require a full broker.
This acts as a message store and relay between the prediction service and Hummingbot.
"""
import threading
import time
import logging
import signal
import sys
import json
from queue import Queue, Empty
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("MQTT-Bridge")

class MQTTBridge:
    """A simple message bridge that stores and forwards MQTT-like messages"""
    
    def __init__(self):
        self.running = False
        self.messages = {}  # topic -> list of messages
        self.subscribers = {}  # topic -> list of callbacks
        self.lock = threading.Lock()
        self.message_queue = Queue()
        
    def start(self):
        """Start the MQTT bridge"""
        self.running = True
        
        # Start the processing thread
        self.process_thread = threading.Thread(target=self._process_messages)
        self.process_thread.daemon = True
        self.process_thread.start()
        
        # Start the status thread
        self.status_thread = threading.Thread(target=self._print_status)
        self.status_thread.daemon = True
        self.status_thread.start()
        
        logger.info("MQTT Bridge started")
        return True
        
    def stop(self):
        """Stop the MQTT bridge"""
        self.running = False
        logger.info("MQTT Bridge stopped")
        
    def publish(self, topic, message, retain=False):
        """Publish a message to a topic"""
        msg_obj = {
            'topic': topic,
            'payload': message,
            'timestamp': datetime.now().isoformat(),
            'retain': retain
        }
        
        with self.lock:
            if topic not in self.messages:
                self.messages[topic] = []
                
            self.messages[topic].append(msg_obj)
            # Keep only last 100 messages per topic
            if len(self.messages[topic]) > 100:
                self.messages[topic] = self.messages[topic][-100:]
            
            # Add to processing queue
            self.message_queue.put(msg_obj)
        
        logger.debug(f"Published message to {topic}")
        return True
        
    def subscribe(self, topic, callback):
        """Subscribe to a topic with a callback function"""
        with self.lock:
            if topic not in self.subscribers:
                self.subscribers[topic] = []
                
            self.subscribers[topic].append(callback)
            
            # Send retained messages to the new subscriber
            if topic in self.messages and self.messages[topic]:
                for msg in self.messages[topic]:
                    if msg.get('retain', False):
                        try:
                            callback(msg['topic'], msg['payload'])
                        except Exception as e:
                            logger.error(f"Error in subscriber callback: {e}")
        
        logger.info(f"Subscribed to {topic}")
        return True
        
    def unsubscribe(self, topic, callback):
        """Unsubscribe from a topic"""
        with self.lock:
            if topic in self.subscribers and callback in self.subscribers[topic]:
                self.subscribers[topic].remove(callback)
                if not self.subscribers[topic]:
                    del self.subscribers[topic]
                    
        logger.info(f"Unsubscribed from {topic}")
        return True
        
    def _process_messages(self):
        """Process messages from the queue and distribute to subscribers"""
        while self.running:
            try:
                msg = self.message_queue.get(timeout=1.0)
                topic = msg['topic']
                payload = msg['payload']
                
                # Find subscribers that match this topic
                with self.lock:
                    matching_subscribers = []
                    for sub_topic, callbacks in self.subscribers.items():
                        # Simple wildcard matching
                        if sub_topic == topic or sub_topic == '#':
                            matching_subscribers.extend(callbacks)
                        elif sub_topic.endswith('/#'):
                            prefix = sub_topic[:-2]
                            if topic.startswith(prefix):
                                matching_subscribers.extend(callbacks)
                                
                # Call subscriber callbacks
                for callback in matching_subscribers:
                    try:
                        callback(topic, payload)
                    except Exception as e:
                        logger.error(f"Error in subscriber callback: {e}")
                        
                self.message_queue.task_done()
            except Empty:
                # This is expected with the timeout
                pass
            except Exception as e:
                logger.error(f"Error processing message: {e}")
                
    def _print_status(self):
        """Periodically print bridge status"""
        while self.running:
            time.sleep(10)
            with self.lock:
                topic_count = len(self.messages)
                subscriber_count = sum(len(callbacks) for callbacks in self.subscribers.values())
                message_count = sum(len(msgs) for msgs in self.messages.values())
                
                logger.info(f"Bridge status: {topic_count} topics, {subscriber_count} subscribers, {message_count} messages")
                
                # Print the latest message if available
                for topic, msgs in self.messages.items():
                    if msgs:
                        latest_msg = msgs[-1]
                        logger.info(f"Latest message on {topic}: {latest_msg['payload']}")
                        break

# Global bridge instance
_bridge = None

def get_bridge():
    """Get the global bridge instance"""
    global _bridge
    if _bridge is None:
        _bridge = MQTTBridge()
    return _bridge

def handle_signal(sig, frame):
    """Handle termination signals"""
    logger.info(f"Received signal {sig}, shutting down...")
    if _bridge is not None:
        _bridge.stop()
    sys.exit(0)

if __name__ == "__main__":
    # Register signal handlers
    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)
    
    # Start the bridge
    bridge = get_bridge()
    bridge.start()
    
    # Add a test subscriber
    def test_callback(topic, payload):
        logger.info(f"TEST: Received message on {topic}: {payload}")
    
    bridge.subscribe("hbot/predictions/#", test_callback)
    
    # Keep the main thread running
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        bridge.stop()
        sys.exit(0) 