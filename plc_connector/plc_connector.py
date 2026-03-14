"""
PLC Connector for Siemens S7-1200.

Reads real PLC tag values via the S7 communication protocol (python-snap7)
and publishes them to the MQTT broker on the same topic/payload schema used
by the simulator (plant/<tag>).  This lets you swap the simulator for a live
PLC with no changes to the backend.

Environment variables (all optional – fall back to tag_config.json / defaults):
    MQTT_BROKER         MQTT broker hostname or IP  (default: localhost)
    MQTT_PORT           MQTT broker port            (default: 1883)
    PLC_IP              S7-1200 IP address          (overrides tag_config.json)
    PLC_RACK            Rack number                 (default: 0)
    PLC_SLOT            Slot number                 (default: 1)
    POLL_INTERVAL       Seconds between reads       (default: 2)
    TAG_CONFIG          Path to tag_config.json     (default: /app/tag_config.json)
"""

import json
import logging
import os
import struct
import time
from typing import Any

import paho.mqtt.client as mqtt
import snap7
from snap7.util import get_real

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# ── Configuration ──────────────────────────────────────────────────────────────
CONFIG_PATH = os.environ.get("TAG_CONFIG", os.path.join(os.path.dirname(__file__), "tag_config.json"))

with open(CONFIG_PATH) as f:
    _config: dict = json.load(f)

_plc_cfg = _config.get("plc", {})
PLC_IP = os.environ.get("PLC_IP", _plc_cfg.get("ip", "192.168.0.1"))
PLC_RACK = int(os.environ.get("PLC_RACK", _plc_cfg.get("rack", 0)))
PLC_SLOT = int(os.environ.get("PLC_SLOT", _plc_cfg.get("slot", 1)))
POLL_INTERVAL = float(os.environ.get("POLL_INTERVAL", _plc_cfg.get("poll_interval", 2)))

MQTT_BROKER = os.environ.get("MQTT_BROKER", "localhost")
MQTT_PORT = int(os.environ.get("MQTT_PORT", 1883))

TAGS: list[dict] = _config.get("tags", [])

# ── Supported data-type readers ────────────────────────────────────────────────
_READERS = {
    "REAL": lambda buf, offset: round(get_real(buf, offset), 3),
    "INT":  lambda buf, offset: struct.unpack_from(">h", buf, offset)[0],
    "DINT": lambda buf, offset: struct.unpack_from(">i", buf, offset)[0],
    "WORD": lambda buf, offset: struct.unpack_from(">H", buf, offset)[0],
    "DWORD": lambda buf, offset: struct.unpack_from(">I", buf, offset)[0],
}

# Byte-size for each type (used to compute how many bytes to read)
_TYPE_SIZE = {
    "REAL": 4,
    "INT":  2,
    "DINT": 4,
    "WORD": 2,
    "DWORD": 4,
}


def _read_tag(plc: snap7.client.Client, tag: dict) -> Any:
    """Read a single tag value from a PLC Data Block."""
    db = tag["db_number"]
    offset = tag["offset"]
    dtype = tag.get("data_type", "REAL").upper()
    size = _TYPE_SIZE.get(dtype, 4)
    data = plc.db_read(db, int(offset), size)
    reader = _READERS.get(dtype)
    if reader is None:
        raise ValueError(f"Unsupported data type '{dtype}' for tag '{tag['name']}'")
    return reader(data, 0)


# ── PLC connection ─────────────────────────────────────────────────────────────
def _connect_plc() -> snap7.client.Client:
    plc = snap7.client.Client()
    while True:
        try:
            plc.connect(PLC_IP, PLC_RACK, PLC_SLOT)
            if plc.get_connected():
                logger.info(f"Connected to S7-1200 at {PLC_IP} (rack={PLC_RACK}, slot={PLC_SLOT})")
                return plc
        except Exception as exc:
            logger.warning(f"Cannot connect to PLC at {PLC_IP} ({exc}), retrying in 5 s…")
        time.sleep(5)


# ── MQTT connection ────────────────────────────────────────────────────────────
def _on_mqtt_connect(client, userdata, flags, rc):
    if rc == 0:
        logger.info(f"Connected to MQTT broker at {MQTT_BROKER}:{MQTT_PORT}")
    else:
        logger.error(f"MQTT connection failed, rc={rc}")


def _connect_mqtt() -> mqtt.Client:
    client = mqtt.Client()
    client.on_connect = _on_mqtt_connect
    while True:
        try:
            client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
            client.loop_start()
            logger.info("MQTT loop started")
            return client
        except Exception as exc:
            logger.warning(f"Cannot reach MQTT broker ({exc}), retrying in 5 s…")
            time.sleep(5)


# ── Main polling loop ──────────────────────────────────────────────────────────
def main():
    if not TAGS:
        logger.error("No tags defined in tag_config.json – exiting.")
        return

    mqtt_client = _connect_mqtt()
    plc = _connect_plc()

    logger.info(f"Starting poll loop: {len(TAGS)} tags every {POLL_INTERVAL} s")

    while True:
        # Reconnect PLC if connection was lost
        if not plc.get_connected():
            logger.warning("PLC connection lost – reconnecting…")
            try:
                plc.destroy()
            except Exception:
                pass
            plc = _connect_plc()

        published = 0
        for tag in TAGS:
            try:
                value = _read_tag(plc, tag)
                payload = json.dumps({
                    "tag": tag["name"],
                    "value": value,
                    "unit": tag.get("unit", ""),
                    "timestamp": time.time(),
                    "anomaly": False,
                })
                topic = f"plant/{tag['name']}"
                result = mqtt_client.publish(topic, payload, qos=0)
                if result.rc != mqtt.MQTT_ERR_SUCCESS:
                    logger.warning(f"Publish failed for '{tag['name']}': rc={result.rc}")
                else:
                    published += 1
            except Exception as exc:
                logger.error(f"Error reading tag '{tag['name']}': {exc}")

        logger.debug(f"Published {published}/{len(TAGS)} tags")
        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
