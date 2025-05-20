#!/usr/bin/env python3
"""
A simple MQTT broker using Python socket programming.
This is a very basic implementation that relays messages between clients.
"""
import socket
import threading
import time
import logging
import sys
import json
import select
import signal
from typing import Dict, List, Set, Any

try:
    import paho.mqtt.client as mqtt
except ImportError:
    print("This script requires the paho-mqtt package.")
    print("Please install it with: pip install paho-mqtt")
    sys.exit(1)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SimpleMQTTBroker:
    def __init__(self, host="0.0.0.0", port=1883):
        self.host = host
        self.port = port
        self.running = False
        self.server_socket = None
        self.clients = {}  # client_id -> socket
        self.subscriptions = {}  # topic -> set(client_id)
        self.retained_messages = {}  # topic -> message
        self.lock = threading.Lock()
        self.messages = []  # List of received messages
        
    def start(self):
        """Start the MQTT broker."""
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            # Allow reuse of address
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            
            # Try binding to the port, if it fails, try a different port
            try:
                self.server_socket.bind((self.host, self.port))
            except OSError:
                # Port might be in use, try another one
                self.port = 1884  # Try an alternative port
                logger.info(f"Port 1883 is in use, trying port {self.port}")
                self.server_socket.bind((self.host, self.port))
                
            self.server_socket.listen(5)
            logger.info(f"MQTT broker listening on {self.host}:{self.port}")
            self.running = True
            
            # Start a monitoring thread
            monitor_thread = threading.Thread(target=self._monitor_thread)
            monitor_thread.daemon = True
            monitor_thread.start()
            
            # Accept client connections
            while self.running:
                try:
                    ready_sockets, _, _ = select.select([self.server_socket], [], [], 1.0)
                    if ready_sockets:
                        client_socket, address = self.server_socket.accept()
                        client_thread = threading.Thread(target=self._handle_client, args=(client_socket, address))
                        client_thread.daemon = True
                        client_thread.start()
                except select.error:
                    if self.running:
                        logger.error("Error in select()")
                except Exception as e:
                    if self.running:
                        logger.error(f"Error accepting client connection: {e}")
        except Exception as e:
            logger.error(f"Error starting MQTT broker: {e}")
        finally:
            self.stop()
    
    def _monitor_thread(self):
        """Periodically outputs broker status"""
        while self.running:
            time.sleep(10)
            with self.lock:
                logger.info(f"MQTT Broker Status: {len(self.clients)} connected clients, {len(self.subscriptions)} active topics")
                
                # If we have messages, print the last few
                if self.messages:
                    logger.info(f"Last message: {self.messages[-1]}")
    
    def _handle_client(self, client_socket, address):
        """Handle a client connection."""
        logger.info(f"New client connected: {address}")
        client_id = f"client-{address[0]}-{address[1]}"
        
        with self.lock:
            self.clients[client_id] = client_socket
        
        try:
            # In a real implementation, we would parse MQTT protocol messages here
            # For now, just keep the connection open and echo back any data received
            client_socket.settimeout(1.0)
            
            while self.running:
                try:
                    data = client_socket.recv(1024)
                    if not data:
                        # Client closed connection
                        break
                    
                    # Echo back the data (this is not proper MQTT, just for testing)
                    client_socket.send(data)
                    
                    with self.lock:
                        self.messages.append(f"Data from {client_id}: {len(data)} bytes")
                        if len(self.messages) > 100:
                            self.messages = self.messages[-100:]  # Keep only last 100 messages
                            
                except socket.timeout:
                    # This is expected with the timeout
                    pass
                except Exception as e:
                    logger.error(f"Error reading from client {client_id}: {e}")
                    break
        except Exception as e:
            logger.error(f"Error handling client {client_id}: {e}")
        finally:
            with self.lock:
                if client_id in self.clients:
                    del self.clients[client_id]
                    
                # Remove client from all subscriptions
                for topic in list(self.subscriptions.keys()):
                    if client_id in self.subscriptions[topic]:
                        self.subscriptions[topic].remove(client_id)
                        if not self.subscriptions[topic]:
                            del self.subscriptions[topic]
            
            try:
                client_socket.close()
            except:
                pass
            
            logger.info(f"Client {client_id} disconnected")

    def stop(self):
        """Stop the MQTT broker."""
        self.running = False
        
        # Close all client connections
        with self.lock:
            for client_id, socket in self.clients.items():
                try:
                    socket.close()
                except:
                    pass
            self.clients.clear()
            self.subscriptions.clear()
            self.retained_messages.clear()
        
        # Close server socket
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass
            self.server_socket = None
        
        logger.info("MQTT broker stopped")

def handle_signal(sig, frame):
    """Handle termination signals"""
    logger.info(f"Received signal {sig}, shutting down...")
    if 'broker' in globals():
        broker.stop()
    sys.exit(0)

if __name__ == "__main__":
    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)
    
    # Create and start the broker
    broker = SimpleMQTTBroker()
    try:
        logger.info("Starting MQTT broker...")
        broker.start()
    except KeyboardInterrupt:
        logger.info("Shutting down MQTT broker...")
    finally:
        broker.stop() 