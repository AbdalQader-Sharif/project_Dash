"""
PLC Simulator: publishes 21 sensor tags to MQTT broker on topic plant/<tag>.
Simulates normal operating values with occasional anomaly injection.
"""
import json
import logging
import math
import os
import random
import time

import paho.mqtt.client as mqtt

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

MQTT_BROKER = os.environ.get("MQTT_BROKER", "localhost")
MQTT_PORT = 1883
PUBLISH_INTERVAL = 2  # seconds between updates

# Sensor definitions: tag -> (unit, base_value, noise_amplitude, anomaly_multiplier)
SENSORS = {
    "pump1/flow":         ("m3/h",  50.0,  5.0,  2.0),
    "pump1/pressure":     ("bar",    6.0,  0.5,  2.0),
    "pump1/temperature":  ("°C",    70.0,  5.0,  1.5),
    "pump1/current":      ("A",     18.0,  2.0,  1.8),
    "pump1/vibration":    ("mm/s",   4.0,  1.0,  3.5),
    "pump2/flow":         ("m3/h",  45.0,  4.0,  2.0),
    "pump2/pressure":     ("bar",    5.5,  0.5,  2.0),
    "pump2/temperature":  ("°C",    68.0,  5.0,  1.5),
    "pump2/current":      ("A",     16.0,  2.0,  1.8),
    "pump2/vibration":    ("mm/s",   3.5,  1.0,  3.5),
    "tank1/level":        ("%",     60.0, 10.0, -0.6),
    "tank2/level":        ("%",     55.0,  8.0, -0.6),
    "compressor/pressure":    ("bar",   9.0,  0.8,  1.5),
    "compressor/temperature": ("°C",   85.0,  5.0,  1.4),
    "heat_exchanger/inlet_temp":  ("°C",  80.0,  3.0,  1.5),
    "heat_exchanger/outlet_temp": ("°C",  40.0,  3.0,  1.5),
    "conveyor/speed":     ("m/min", 30.0,  3.0,  2.0),
    "conveyor/current":   ("A",     12.0,  1.5,  2.0),
    "boiler/pressure":    ("bar",   12.0,  1.0,  1.4),
    "boiler/temperature": ("°C",   160.0,  8.0,  1.4),
    "boiler/flow":        ("m3/h",  20.0,  2.0,  2.0),
}

# Anomaly state per tag: None or countdown ticks
_anomaly_state: dict = {}


def _next_value(tag: str, t: float) -> tuple:
    """Return (value, is_anomaly) for the given tag and time."""
    unit, base, noise, anomaly_mult = SENSORS[tag]

    # Decide whether to start an anomaly (1% chance per tick per sensor)
    if _anomaly_state.get(tag, 0) <= 0:
        if random.random() < 0.01:
            _anomaly_state[tag] = random.randint(5, 15)  # lasts 5-15 ticks
    else:
        _anomaly_state[tag] -= 1

    is_anomaly = _anomaly_state.get(tag, 0) > 0

    # Simulate sinusoidal drift + random noise
    drift = noise * 0.3 * math.sin(t / 30.0 + hash(tag) % 10)
    rand_noise = random.gauss(0, noise * 0.1)
    value = base + drift + rand_noise

    if is_anomaly:
        if anomaly_mult < 0:
            # Negative multiplier means we drive towards an extreme low (e.g. tank level)
            value = base * (1 + anomaly_mult) + random.gauss(0, noise * 0.05)
        else:
            value = base * anomaly_mult + random.gauss(0, noise * 0.1)

    # Clamp to non-negative
    value = max(0.0, value)
    return round(value, 3), is_anomaly


def _on_connect(client, userdata, flags, rc):
    if rc == 0:
        logger.info(f"Connected to MQTT broker at {MQTT_BROKER}:{MQTT_PORT}")
    else:
        logger.error(f"MQTT connection failed, rc={rc}")


def _connect_with_retry() -> mqtt.Client:
    client = mqtt.Client()
    client.on_connect = _on_connect
    while True:
        try:
            client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
            client.loop_start()
            logger.info("MQTT loop started")
            return client
        except Exception as exc:
            logger.warning(f"Cannot reach broker ({exc}), retrying in 5s...")
            time.sleep(5)


def main():
    client = _connect_with_retry()
    t = 0.0
    while True:
        for tag, (unit, *_) in SENSORS.items():
            value, is_anomaly = _next_value(tag, t)
            payload = json.dumps({
                "tag": tag,
                "value": value,
                "unit": unit,
                "timestamp": time.time(),
                "anomaly": is_anomaly,
            })
            topic = f"plant/{tag}"
            result = client.publish(topic, payload, qos=0)
            if result.rc != mqtt.MQTT_ERR_SUCCESS:
                logger.warning(f"Publish failed for {tag}: rc={result.rc}")

        logger.debug(f"Published {len(SENSORS)} tags (t={t:.0f}s)")
        t += PUBLISH_INTERVAL
        time.sleep(PUBLISH_INTERVAL)


if __name__ == "__main__":
    main()
