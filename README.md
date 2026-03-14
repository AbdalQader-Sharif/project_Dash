# project_Dash — AI Predictive Maintenance SCADA Dashboard

A real-time industrial dashboard built with MQTT, FastAPI, InfluxDB, React/TypeScript,
and an MCP server for AI agent integration.

## Services

| Service | Port | Description |
|---------|------|-------------|
| mosquitto | 1883 | MQTT message broker |
| influxdb | 8086 | Time-series database |
| simulator | — | PLC tag simulator (publishes 21 sensor tags via MQTT) |
| plc-connector | — | Real S7-1200 connector (enabled via `--profile real-plc`) |
| backend | 5000 | FastAPI REST + WebSocket API |
| frontend | 3000 | React dashboard (served by nginx) |
| mcp-server | 8090 | MCP tool server for AI agents |

## Quick Start

### Prerequisites
- [Docker](https://docs.docker.com/get-docker/) and [Docker Compose](https://docs.docker.com/compose/install/) installed.

### Run

```bash
git clone https://github.com/AbdalQader-Sharif/project_Dash.git
cd project_Dash
docker-compose up --build
```

Open http://localhost:3000 in your browser.

### Demo Credentials

| Username | Password | Role |
|----------|----------|------|
| developer | dev123 | developer |
| admin | admin123 | admin |
| operator | op123 | user |

## Architecture

```
PLC Simulator ──MQTT──►
                        Mosquitto ──MQTT──► Backend (FastAPI)
S7-1200 PLC  ──MQTT──►      │                     │
  (snap7 or                  │               InfluxDB (history)
  native MQTT)               │                     │
                             │           WebSocket / REST API
                             │                     │
                             │             Frontend (React)
                             │                     │
                             │             MCP Server (AI tools)
```

## MCP Server API

The MCP server exposes the plant data as tools for AI agents:

- `GET /tools` — list available tools
- `POST /tools/call` — invoke a tool

Available tools: `get_sensors`, `get_sensor`, `get_alarms`, `get_history`, `get_health`.

---

## Connecting a Real Siemens S7-1200 PLC

The dashboard ships with a **PLC Connector** service (`plc_connector/`) that reads live tag
values directly from a physical S7-1200 over the S7 communication protocol
([python-snap7](https://python-snap7.readthedocs.io/)) and publishes them to the
same Mosquitto MQTT topics as the simulator.  No changes to the backend are required.

There are **two** supported approaches depending on your hardware/firmware version.

---

### Approach A — python-snap7 bridge (recommended for most setups)

The `plc-connector` Docker service uses **python-snap7** to poll PLC Data Blocks (DBs)
and publish each value to `plant/<tag>` every 2 seconds (configurable).

#### 1. Configure your tags

Edit `plc_connector/tag_config.json`:

```jsonc
{
  "plc": {
    "ip": "192.168.0.1",   // ← your S7-1200 IP address
    "rack": 0,             // always 0 for S7-1200
    "slot": 1,             // always 1 for S7-1200 (CPU in slot 1)
    "poll_interval": 2     // seconds between reads
  },
  "tags": [
    // Map each sensor to a Data Block address in the PLC.
    // "offset" is the byte offset inside the DB; data_type must be REAL, INT, DINT, WORD, or DWORD.
    {"name": "pump1/pressure", "unit": "bar", "db_number": 1, "offset": 0, "data_type": "REAL"},
    {"name": "pump1/temperature", "unit": "°C", "db_number": 1, "offset": 4, "data_type": "REAL"}
    // … add more tags as needed
  ]
}
```

> **TIA Portal note:** In your PLC project, create a Global Data Block (e.g. DB1) and add one
> `REAL` variable per sensor.  Make sure the block is **not** optimised (uncheck *"Optimized block
> access"* in DB properties) so that symbolic offsets match byte offsets used here.

#### 2. Allow S7 PUT/GET access

In TIA Portal → PLC Properties → Protection & Security → enable
**"Permit access with PUT/GET communication from remote partner"**.

#### 3. Start the connector (disable the simulator)

```bash
# Stop the simulator, start the real PLC connector instead:
PLC_IP=192.168.0.1 docker compose --profile real-plc up --build \
    --scale simulator=0
```

Or set a permanent override in a `.env` file:

```dotenv
PLC_IP=192.168.0.1
PLC_RACK=0
PLC_SLOT=1
POLL_INTERVAL=2
```

Then run:

```bash
docker compose --profile real-plc up --build --scale simulator=0
```

The connector retries the PLC connection automatically if it is temporarily unreachable and
reconnects the MQTT broker on drop-outs.

---

### Approach B — S7-1200 Native MQTT client (firmware V4.4 or newer)

From firmware **V4.4** the S7-1200 CPU contains a built-in MQTT client that can publish tag
values directly to Mosquitto — no extra software needed.

Configure the PLC in TIA Portal using the `MQTT_Connect`, `MQTT_Publish`, and `MQTT_Disconnect`
instructions (available in the *Communication* library):

| Instruction parameter | Value |
|-----------------------|-------|
| Broker IP | `<host running Docker, e.g. 192.168.0.100>` |
| Broker port | `1883` |
| Topic | `plant/<tag>` (e.g. `plant/pump1/pressure`) |
| QoS | `0` (At most once) |
| Payload | JSON string matching the schema below |

#### Required JSON payload schema

The backend expects each MQTT message to contain a JSON object with these fields:

```json
{
  "tag":       "pump1/pressure",
  "value":     6.12,
  "unit":      "bar",
  "timestamp": 1710000000.0,
  "anomaly":   false
}
```

Build the payload string inside the PLC using `S_CONV` / `Concat` blocks or a structured
string builder SCL function, then pass it to `MQTT_Publish`.

No changes to the rest of the stack are required — the backend subscribes to `plant/#` and
will immediately start displaying your real PLC data.

---

### Supported tag names

The backend threshold engine and frontend use the following tag names (matching the simulator):

| Tag | Unit | Alarm condition |
|-----|------|----------------|
| `pump1/flow` | m³/h | — |
| `pump1/pressure` | bar | > 8.0 → warning |
| `pump1/temperature` | °C | > 85 → warning |
| `pump1/current` | A | > 25 → critical |
| `pump1/vibration` | mm/s | > 10 → critical |
| `pump2/…` | (same) | (same) |
| `tank1/level` | % | < 10 → warning, > 95 → warning |
| `tank2/level` | % | (same) |
| `compressor/pressure` | bar | > 12 → critical |
| `compressor/temperature` | °C | > 100 → critical |
| `heat_exchanger/inlet_temp` | °C | > 100 → critical |
| `heat_exchanger/outlet_temp` | °C | > 100 → critical |
| `conveyor/speed` | m/min | — |
| `conveyor/current` | A | — |
| `boiler/pressure` | bar | > 15 → critical |
| `boiler/temperature` | °C | > 200 → warning |
| `boiler/flow` | m³/h | — |

You can publish only a subset of tags — the dashboard will show whatever it receives.
