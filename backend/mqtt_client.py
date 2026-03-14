import asyncio
import json
import logging
import os
import threading
import time
import uuid
from typing import Dict, List, Optional, Set

import paho.mqtt.client as mqtt

from models import Alarm, SensorReading

logger = logging.getLogger(__name__)

MQTT_BROKER = os.environ.get("MQTT_BROKER", "localhost")
MQTT_PORT = 1883

# Global state
SENSOR_STORE: Dict[str, SensorReading] = {}
ALARM_LIST: List[Alarm] = []
_store_lock = threading.Lock()
_alarm_lock = threading.Lock()

# Will be set by main.py
_event_loop: Optional[asyncio.AbstractEventLoop] = None
_websocket_connections: Optional[Set] = None
_broadcast_func = None


def set_event_loop(loop: asyncio.AbstractEventLoop):
    global _event_loop
    _event_loop = loop


def set_broadcast(connections: Set, broadcast_fn):
    global _websocket_connections, _broadcast_func
    _websocket_connections = connections
    _broadcast_func = broadcast_fn


def _check_thresholds(reading: SensorReading) -> Optional[Alarm]:
    tag = reading.tag
    value = reading.value
    severity = None
    message = None

    if "pump" in tag and tag.endswith("/pressure") and value > 8.0:
        severity = "warning"
        message = f"High pressure: {value:.1f} bar"
    elif "pump" in tag and tag.endswith("/temperature") and value > 85.0:
        severity = "warning"
        message = f"High temperature: {value:.1f} °C"
    elif "pump" in tag and tag.endswith("/current") and value > 25.0:
        severity = "critical"
        message = f"Overcurrent: {value:.1f} A"
    elif "pump" in tag and tag.endswith("/vibration") and value > 10.0:
        severity = "critical"
        message = f"High vibration: {value:.1f} mm/s"
    elif "tank" in tag and tag.endswith("/level") and value < 10.0:
        severity = "warning"
        message = f"Low level: {value:.1f}%"
    elif "tank" in tag and tag.endswith("/level") and value > 95.0:
        severity = "warning"
        message = f"High level: {value:.1f}%"
    elif tag == "compressor/pressure" and value > 12.0:
        severity = "critical"
        message = f"High compressor pressure: {value:.1f} bar"
    elif tag == "boiler/pressure" and value > 15.0:
        severity = "critical"
        message = f"High boiler pressure: {value:.1f} bar"
    elif tag == "boiler/temperature" and value > 200.0:
        severity = "warning"
        message = f"High boiler temperature: {value:.1f} °C"
    elif "temperature" in tag and value > 100.0:
        severity = "critical"
        message = f"Critical temperature: {value:.1f} °C"

    if severity and message:
        return Alarm(
            id=str(uuid.uuid4()),
            tag=tag,
            message=message,
            severity=severity,
            timestamp=reading.timestamp,
            acknowledged=False,
        )
    return None


def _has_active_alarm(tag: str) -> bool:
    with _alarm_lock:
        for alarm in ALARM_LIST:
            if alarm.tag == tag and not alarm.acknowledged:
                return True
    return False


def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())
        tag = payload.get("tag")
        if not tag:
            return

        reading = SensorReading(
            tag=tag,
            value=float(payload.get("value", 0)),
            unit=payload.get("unit", ""),
            timestamp=float(payload.get("timestamp", time.time())),
            anomaly=bool(payload.get("anomaly", False)),
        )

        with _store_lock:
            SENSOR_STORE[tag] = reading

        # Check thresholds
        alarm = _check_thresholds(reading)
        if alarm and not _has_active_alarm(tag):
            with _alarm_lock:
                ALARM_LIST.append(alarm)
            logger.info(f"New alarm: [{alarm.severity.upper()}] {alarm.tag} - {alarm.message}")

        # Write to InfluxDB
        try:
            from influx_client import influx_client
            influx_client.write_sensor_reading(reading)
        except Exception as e:
            logger.debug(f"InfluxDB write skipped: {e}")

        # Broadcast via WebSocket
        if _event_loop and _broadcast_func:
            data = reading.model_dump()
            asyncio.run_coroutine_threadsafe(
                _broadcast_func(data),
                _event_loop,
            )

    except Exception as e:
        logger.error(f"Error processing MQTT message: {e}")


def on_connect(client, userdata, flags, rc):
    if rc == 0:
        logger.info("MQTT client connected to broker")
        client.subscribe("plant/#")
    else:
        logger.error(f"MQTT connection failed with code {rc}")


def on_disconnect(client, userdata, rc):
    logger.warning(f"MQTT client disconnected (rc={rc})")


def _mqtt_thread():
    while True:
        try:
            client = mqtt.Client()
            client.on_connect = on_connect
            client.on_message = on_message
            client.on_disconnect = on_disconnect
            client.connect(MQTT_BROKER, MQTT_PORT, 60)
            logger.info(f"Connecting to MQTT broker at {MQTT_BROKER}:{MQTT_PORT}")
            client.loop_forever()
        except Exception as e:
            logger.error(f"MQTT thread error: {e}, retrying in 5s...")
            time.sleep(5)


async def start_mqtt_client():
    global _event_loop
    _event_loop = asyncio.get_event_loop()
    t = threading.Thread(target=_mqtt_thread, daemon=True)
    t.start()
    logger.info("MQTT client started in background thread")
