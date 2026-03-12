import json
import os
import random
import threading
import time
import logging
from dataclasses import dataclass
from typing import Optional

import paho.mqtt.client as mqtt

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

MQTT_BROKER = os.environ.get("MQTT_BROKER", "localhost")
MQTT_PORT = 1883


@dataclass
class Tag:
    name: str
    topic: str
    unit: str
    normal_min: float
    normal_max: float
    anomaly_min: float
    anomaly_max: float
    update_interval_seconds: int


TAGS = [
    Tag("pump1/flow", "plant/plc1/pump1/flow", "m3/h", 10.0, 50.0, 60.0, 80.0, 1),
    Tag("pump1/pressure", "plant/plc1/pump1/pressure", "bar", 2.0, 7.0, 9.0, 12.0, 1),
    Tag("pump1/temperature", "plant/plc1/pump1/temperature", "°C", 20.0, 75.0, 90.0, 120.0, 5),
    Tag("pump1/current", "plant/plc1/pump1/current", "A", 5.0, 20.0, 28.0, 40.0, 1),
    Tag("pump1/vibration", "plant/plc1/pump1/vibration", "mm/s", 0.1, 8.0, 12.0, 20.0, 5),
    Tag("pump2/flow", "plant/plc1/pump2/flow", "m3/h", 8.0, 45.0, 55.0, 75.0, 1),
    Tag("pump2/pressure", "plant/plc1/pump2/pressure", "bar", 2.0, 7.0, 9.0, 12.0, 1),
    Tag("pump2/temperature", "plant/plc1/pump2/temperature", "°C", 20.0, 75.0, 90.0, 120.0, 5),
    Tag("pump2/current", "plant/plc1/pump2/current", "A", 5.0, 20.0, 28.0, 40.0, 1),
    Tag("pump2/vibration", "plant/plc1/pump2/vibration", "mm/s", 0.1, 8.0, 12.0, 20.0, 5),
    Tag("tank1/level", "plant/plc1/tank1/level", "%", 20.0, 90.0, 2.0, 8.0, 5),
    Tag("tank2/level", "plant/plc1/tank2/level", "%", 20.0, 90.0, 96.0, 99.0, 5),
    Tag("compressor/pressure", "plant/plc1/compressor/pressure", "bar", 4.0, 10.0, 13.0, 16.0, 30),
    Tag("compressor/temperature", "plant/plc1/compressor/temperature", "°C", 30.0, 90.0, 100.0, 130.0, 30),
    Tag("heat_exchanger/inlet_temp", "plant/plc1/heat_exchanger/inlet_temp", "°C", 40.0, 80.0, 95.0, 115.0, 30),
    Tag("heat_exchanger/outlet_temp", "plant/plc1/heat_exchanger/outlet_temp", "°C", 20.0, 60.0, 75.0, 100.0, 30),
    Tag("conveyor/speed", "plant/plc1/conveyor/speed", "m/min", 1.0, 10.0, 12.0, 18.0, 5),
    Tag("conveyor/current", "plant/plc1/conveyor/current", "A", 2.0, 15.0, 20.0, 30.0, 5),
    Tag("boiler/pressure", "plant/plc1/boiler/pressure", "bar", 5.0, 12.0, 16.0, 20.0, 30),
    Tag("boiler/temperature", "plant/plc1/boiler/temperature", "°C", 80.0, 180.0, 205.0, 250.0, 30),
    Tag("boiler/flow", "plant/plc1/boiler/flow", "m3/h", 5.0, 30.0, 35.0, 50.0, 30),
]

# Global state
anomaly_tags: set[str] = set()
anomaly_lock = threading.Lock()
client: Optional[mqtt.Client] = None
client_lock = threading.Lock()
connected = threading.Event()


def on_connect(mqtt_client, userdata, flags, rc):
    if rc == 0:
        logger.info("Connected to MQTT broker")
        connected.set()
    else:
        logger.error(f"Failed to connect, return code {rc}")


def on_disconnect(mqtt_client, userdata, rc):
    logger.warning(f"Disconnected from MQTT broker (rc={rc})")
    connected.clear()


def create_client():
    c = mqtt.Client()
    c.on_connect = on_connect
    c.on_disconnect = on_disconnect
    return c


def connect_with_retry():
    global client
    while True:
        try:
            with client_lock:
                client = create_client()
                client.connect(MQTT_BROKER, MQTT_PORT, 60)
                client.loop_start()
            connected.wait(timeout=10)
            if connected.is_set():
                return
            logger.warning("Connection timeout, retrying...")
        except Exception as e:
            logger.error(f"Connection error: {e}, retrying in 5s...")
            time.sleep(5)


def publish_tag(tag: Tag):
    while True:
        try:
            with anomaly_lock:
                is_anomaly = tag.name in anomaly_tags

            if is_anomaly:
                value = round(random.uniform(tag.anomaly_min, tag.anomaly_max), 2)
            else:
                value = round(random.uniform(tag.normal_min, tag.normal_max), 2)

            payload = {
                "value": value,
                "unit": tag.unit,
                "timestamp": time.time(),
                "tag": tag.name,
                "anomaly": is_anomaly,
            }

            if connected.is_set():
                with client_lock:
                    if client:
                        client.publish(tag.topic, json.dumps(payload), qos=0)
                        logger.debug(f"Published {tag.name}={value}{tag.unit}")
        except Exception as e:
            logger.error(f"Error publishing {tag.name}: {e}")

        time.sleep(tag.update_interval_seconds)


def anomaly_injector():
    """Every 120 seconds, randomly select 1-3 tags and inject anomaly values."""
    while True:
        time.sleep(120)
        num_anomalies = random.randint(1, 3)
        selected = random.sample(TAGS, num_anomalies)
        with anomaly_lock:
            anomaly_tags.clear()
            for tag in selected:
                anomaly_tags.add(tag.name)
        logger.info(f"Injecting anomalies into: {[t.name for t in selected]}")
        # After 30s, clear anomalies
        time.sleep(30)
        with anomaly_lock:
            anomaly_tags.clear()
        logger.info("Anomaly injection cleared")


def main():
    logger.info(f"Starting simulator, connecting to {MQTT_BROKER}:{MQTT_PORT}")
    connect_with_retry()

    # Start anomaly injector thread
    t = threading.Thread(target=anomaly_injector, daemon=True)
    t.start()

    # Start a thread for each tag
    for tag in TAGS:
        t = threading.Thread(target=publish_tag, args=(tag,), daemon=True)
        t.start()
        # Stagger start slightly to avoid burst
        time.sleep(0.05)

    logger.info(f"Simulator running with {len(TAGS)} tags")

    # Keep main thread alive, handle reconnections
    while True:
        if not connected.is_set():
            logger.info("Reconnecting to MQTT broker...")
            connect_with_retry()
        time.sleep(10)


if __name__ == "__main__":
    main()
