#!/usr/bin/env python3
"""
A simple MQTT broker using the mqtt-broker library.
"""
import asyncio
import logging
import os
import signal
import sys

try:
    from mqtt_broker import BrokerServer
except ImportError:
    print("This script requires the mqtt-broker package.")
    print("Please install it with: pip install mqtt-broker")
    sys.exit(1)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    # Create broker instance
    broker = BrokerServer(address='0.0.0.0', port=1883)
    
    # Start the broker
    logger.info("Starting MQTT broker on port 1883...")
    await broker.start()
    logger.info("MQTT broker is running. Press Ctrl+C to stop.")
    
    # Keep the broker running
    while True:
        await asyncio.sleep(1)

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        logger.info("Shutting down MQTT broker...")
    except Exception as e:
        logger.error(f"Error starting MQTT broker: {e}")
    finally:
        loop.close() 