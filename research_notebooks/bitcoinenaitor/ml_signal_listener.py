#!/usr/bin/env python

"""
This script listens for ML signals from the MQTT broker and executes trades based on those signals.
It subscribes to the topic "hbot/predictions/{trading_pair}/ML_SIGNALS" and places orders
according to the prediction signals received.
"""

import asyncio
import json
import time
import logging
from decimal import Decimal
from typing import Dict, Any, List, Optional

import paho.mqtt.client as mqtt
from hummingbot.core.event.events import OrderType, TradeType
from hummingbot.core.data_type.limit_order import LimitOrder
from hummingbot.core.event.event_logger import EventLogger
from hummingbot.logger import HummingbotLogger
from hummingbot.core.network_iterator import NetworkStatus
from hummingbot.core.utils.async_utils import safe_ensure_future
from hummingbot.client.hummingbot_application import HummingbotApplication
from hummingbot.client.settings import AllConnectorSettings

class MlSignalListener:
    """
    This class listens for ML signals from an MQTT broker and executes trades
    based on those signals.
    """
    
    # Default parameters
    DEFAULT_ORDER_AMOUNT = Decimal("0.001")  # Conservative BTC amount
    DEFAULT_ORDER_PRICE_SPREAD = Decimal("0.0025")  # 0.25% spread
    DEFAULT_MQTT_HOST = "localhost"
    DEFAULT_MQTT_PORT = 1883
    DEFAULT_MQTT_TOPIC = "hbot/predictions/#"  # Subscribe to all predictions
    
    def __init__(self):
        """Initializes the ML signal listener."""
        self._trading_pair = None
        self._hb = HummingbotApplication.main_application()
        self._mqtt_client = None
        self._market = None
        self._event_logger = EventLogger()
        self._trading_rules = {}
        self._last_trade_time = 0
        self._min_trade_interval = 30  # Minimum time between trades in seconds
        
        # Settings
        self._order_amount = self.DEFAULT_ORDER_AMOUNT
        self._order_price_spread = self.DEFAULT_ORDER_PRICE_SPREAD
        
        # Trade management
        self._open_orders = {}
        self._position_side = None  # "long" or "short"
        
    async def start(self):
        """Start the ML signal listener."""
        self._hb.notify("Starting ML Signal Listener...")
        
        # Connect to the market
        if not self._check_market_connection():
            self._hb.notify("No market is connected. Please connect to a market first.")
            return
            
        self._hb.notify(f"Connected to market: {self._market.name}")
        self._hb.notify(f"Setting up MQTT connection to {self.DEFAULT_MQTT_HOST}:{self.DEFAULT_MQTT_PORT}")
        
        # Start MQTT connection
        self._setup_mqtt()
        
        # Start order monitoring loop
        safe_ensure_future(self._monitor_orders())
        
        self._hb.notify("ML Signal Listener started. Waiting for signals...")
    
    def _check_market_connection(self) -> bool:
        """Check if a market is connected and ready for trading."""
        connected_exchanges = [ex for ex in self._hb.markets.keys() if self._hb.markets[ex].ready]
        
        if not connected_exchanges:
            self._hb.notify("No exchanges are connected.")
            return False
            
        self._market = self._hb.markets[connected_exchanges[0]]
        self._trading_pair = self._get_active_trading_pair()
        
        if not self._trading_pair:
            self._hb.notify("No trading pair is active. Please configure a trading pair.")
            return False
            
        self._hb.notify(f"Using trading pair: {self._trading_pair}")
        return True
        
    def _get_active_trading_pair(self) -> Optional[str]:
        """Get the active trading pair from the connected market."""
        if not self._market:
            return None
            
        trading_pairs = self._market.trading_pairs
        
        if not trading_pairs:
            # Try to find a common pair
            for pair in ["BTC-USDT", "ETH-USDT", "BTC-USD"]:
                if pair in self._market.get_trading_pairs():
                    return pair
            return None
            
        return trading_pairs[0]
        
    def _setup_mqtt(self):
        """Set up the MQTT client and connect to the broker."""
        self._mqtt_client = mqtt.Client()
        self._mqtt_client.on_connect = self._on_mqtt_connect
        self._mqtt_client.on_message = self._on_mqtt_message
        self._mqtt_client.on_disconnect = self._on_mqtt_disconnect
        
        try:
            self._mqtt_client.connect(self.DEFAULT_MQTT_HOST, self.DEFAULT_MQTT_PORT)
            self._mqtt_client.loop_start()
        except Exception as e:
            self._hb.notify(f"Failed to connect to MQTT broker: {e}")
            
    def _on_mqtt_connect(self, client, userdata, flags, rc):
        """Callback when MQTT client connects to the broker."""
        if rc == 0:
            self._hb.notify("Connected to MQTT broker")
            # Subscribe to all prediction topics
            client.subscribe(self.DEFAULT_MQTT_TOPIC)
            self._hb.notify(f"Subscribed to topic: {self.DEFAULT_MQTT_TOPIC}")
        else:
            self._hb.notify(f"Failed to connect to MQTT broker with code {rc}")
            
    def _on_mqtt_disconnect(self, client, userdata, rc):
        """Callback when MQTT client disconnects from the broker."""
        if rc != 0:
            self._hb.notify(f"Unexpected disconnection from MQTT broker: {rc}")
            self._hb.notify("Attempting to reconnect...")
            
    def _on_mqtt_message(self, client, userdata, msg):
        """Callback when MQTT client receives a message."""
        try:
            payload = json.loads(msg.payload.decode())
            self._hb.notify(f"Received prediction for {payload.get('trading_pair', 'unknown')}")
            
            # Process the prediction
            asyncio.create_task(self._process_prediction(payload))
        except Exception as e:
            self._hb.notify(f"Error processing MQTT message: {e}")
            
    async def _process_prediction(self, prediction: Dict[str, Any]):
        """Process a prediction from the ML model and execute a trade if appropriate."""
        # Ignore if trading pair doesn't match or probabilities not provided
        if 'trading_pair' not in prediction or 'probabilities' not in prediction:
            return
            
        # Check if enough time has passed since last trade
        current_time = time.time()
        if current_time - self._last_trade_time < self._min_trade_interval:
            self._hb.notify(f"Skipping signal - minimum trade interval not reached")
            return
            
        # Extract prediction probabilities
        probabilities = prediction['probabilities']
        
        # Simple strategy: if probability of up is > 65%, go long
        # if probability of down is > 65%, go short
        if len(probabilities) >= 3:  # Assuming format is [down, neutral, up]
            down_prob, neutral_prob, up_prob = probabilities[0], probabilities[1], probabilities[2]
            
            self._hb.notify(f"Prediction: Down={down_prob:.2f}, Neutral={neutral_prob:.2f}, Up={up_prob:.2f}")
            
            # Get current market price
            market_price = await self._get_market_price()
            if not market_price:
                self._hb.notify("Failed to get market price")
                return
                
            # Determine trade action
            if up_prob > 0.65 and (self._position_side is None or self._position_side == "short"):
                # Go long or close short
                await self._execute_trade(TradeType.BUY, market_price)
                self._position_side = "long"
                self._last_trade_time = current_time
                
            elif down_prob > 0.65 and (self._position_side is None or self._position_side == "long"):
                # Go short or close long
                await self._execute_trade(TradeType.SELL, market_price)
                self._position_side = "short"
                self._last_trade_time = current_time
                
            else:
                self._hb.notify("Signal not strong enough for trade")
                
    async def _get_market_price(self) -> Optional[Decimal]:
        """Get the current market price for the trading pair."""
        if not self._market or not self._trading_pair:
            return None
            
        ticker = await self._market.get_ticker(self._trading_pair)
        if ticker is None:
            return None
            
        # Use the mid price
        return (ticker.bid_price + ticker.ask_price) / Decimal('2')
        
    async def _execute_trade(self, trade_type: TradeType, market_price: Decimal):
        """Execute a trade based on the prediction."""
        if not self._market or not self._trading_pair:
            self._hb.notify("Cannot execute trade - market or trading pair not set")
            return
            
        # Calculate order price with spread
        order_price = (
            market_price * (Decimal('1') + self._order_price_spread)
            if trade_type is TradeType.BUY
            else market_price * (Decimal('1') - self._order_price_spread)
        )
        
        # Place the order
        self._hb.notify(f"Placing {trade_type.name} order for {self._order_amount} {self._trading_pair} at {order_price}")
        
        order_id = await self._market.place_order(
            self._trading_pair,
            self._order_amount,
            OrderType.LIMIT,
            trade_type,
            order_price
        )
        
        if order_id:
            self._hb.notify(f"Order placed with ID: {order_id}")
            # Track the order
            self._open_orders[order_id] = {
                "trading_pair": self._trading_pair,
                "amount": self._order_amount,
                "price": order_price,
                "trade_type": trade_type,
                "time": time.time()
            }
        else:
            self._hb.notify("Failed to place order")
            
    async def _monitor_orders(self):
        """Monitor open orders and update status."""
        while True:
            if self._market and self._open_orders:
                # Get updated status for all open orders
                open_orders = await self._market.get_open_orders()
                order_ids = {order.client_order_id for order in open_orders}
                
                # Check if any of our tracked orders are no longer open
                completed_orders = [
                    order_id for order_id in list(self._open_orders.keys())
                    if order_id not in order_ids
                ]
                
                # Update status for completed orders
                for order_id in completed_orders:
                    order_info = self._open_orders.pop(order_id)
                    self._hb.notify(
                        f"Order {order_id} for {order_info['trade_type'].name} "
                        f"{order_info['amount']} {order_info['trading_pair']} completed"
                    )
                    
            await asyncio.sleep(5)  # Check every 5 seconds
            
    def stop(self):
        """Stop the ML signal listener."""
        if self._mqtt_client:
            self._mqtt_client.loop_stop()
            self._mqtt_client.disconnect()
            self._hb.notify("ML Signal Listener stopped")

# Define script entry functions required by Hummingbot script system

def start():
    """Start the ML signal listener."""
    listener = MlSignalListener()
    safe_ensure_future(listener.start())
    
    # Store listener instance for stop function
    global _listener_instance
    _listener_instance = listener
    
def stop():
    """Stop the ML signal listener."""
    global _listener_instance
    if _listener_instance:
        _listener_instance.stop()
        _listener_instance = None

# Global variable to store listener instance
_listener_instance = None 