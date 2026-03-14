import logging
import os
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

INFLUXDB_URL = os.environ.get("INFLUXDB_URL", "http://localhost:8086")
INFLUXDB_TOKEN = os.environ.get("INFLUXDB_TOKEN", "plc-super-secret-auth-token")
INFLUXDB_ORG = os.environ.get("INFLUXDB_ORG", "plc_org")
INFLUXDB_BUCKET = os.environ.get("INFLUXDB_BUCKET", "plc_data")


class InfluxClient:
    def __init__(self):
        self._client = None
        self._write_api = None
        self._query_api = None
        self._available = False
        self._init_client()

    def _init_client(self):
        try:
            from influxdb_client import InfluxDBClient, WriteOptions
            from influxdb_client.client.write_api import SYNCHRONOUS
            self._client = InfluxDBClient(
                url=INFLUXDB_URL,
                token=INFLUXDB_TOKEN,
                org=INFLUXDB_ORG,
            )
            self._write_api = self._client.write_api(write_options=SYNCHRONOUS)
            self._query_api = self._client.query_api()
            self._available = True
            logger.info(f"InfluxDB client initialized: {INFLUXDB_URL}")
        except Exception as e:
            logger.error(f"Failed to initialize InfluxDB client: {e}")
            self._available = False

    def write_sensor_reading(self, sensor) -> bool:
        if not self._available:
            return False
        try:
            from influxdb_client import Point
            point = (
                Point("sensor_reading")
                .tag("tag", sensor.tag)
                .tag("unit", sensor.unit)
                .field("value", float(sensor.value))
                .field("anomaly", int(sensor.anomaly))
            )
            self._write_api.write(bucket=INFLUXDB_BUCKET, org=INFLUXDB_ORG, record=point)
            return True
        except Exception as e:
            logger.error(f"Error writing to InfluxDB: {e}")
            self._available = False
            return False

    def query_historical(self, tag: str, hours: int = 1) -> List[Dict[str, Any]]:
        if not self._available:
            return []
        try:
            query = f'''
from(bucket: "{INFLUXDB_BUCKET}")
  |> range(start: -{hours}h)
  |> filter(fn: (r) => r._measurement == "sensor_reading")
  |> filter(fn: (r) => r.tag == "{tag}")
  |> filter(fn: (r) => r._field == "value")
  |> sort(columns: ["_time"])
'''
            tables = self._query_api.query(query, org=INFLUXDB_ORG)
            results = []
            for table in tables:
                for record in table.records:
                    results.append({
                        "time": record.get_time().isoformat(),
                        "value": record.get_value(),
                    })
            return results
        except Exception as e:
            logger.error(f"Error querying InfluxDB: {e}")
            return []

    def is_healthy(self) -> bool:
        if not self._available:
            return False
        try:
            health = self._client.health()
            return health.status == "pass"
        except Exception:
            return False


influx_client = InfluxClient()
