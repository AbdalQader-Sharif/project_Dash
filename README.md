# project_Dash — AI Predictive Maintenance SCADA Dashboard

A real-time industrial dashboard built with MQTT, FastAPI, InfluxDB, React/TypeScript,
and an MCP server for AI agent integration.

## Services

| Service | Port | Description |
|---------|------|-------------|
| mosquitto | 1883 | MQTT message broker |
| influxdb | 8086 | Time-series database |
| simulator | — | PLC tag simulator (publishes 21 sensor tags via MQTT) |
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
 (Siemens LMQTT             │               InfluxDB (history)
  library)                  │                     │
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

The S7-1200 CPU (firmware **V4.4 or newer**) contains a built-in MQTT client that can publish
tag values directly to Mosquitto using the **Siemens LMQTT library** in TIA Portal — no extra
software or Docker services needed.

Configure the PLC in TIA Portal using the `MQTT_Connect`, `MQTT_Publish`, and `MQTT_Disconnect`
function blocks from the LMQTT library (add via *Options → Manage general libraries →
LMQTT_Client* in TIA Portal V17+):

| Parameter | Value |
|-----------|-------|
| BROKER_ADDRESS | IP of the host running Docker, e.g. `192.168.0.100` |
| BROKER_PORT | `1883` |
| Topic | `plant/<tag>` (e.g. `plant/pump1/pressure`) |
| QoS | `0` (at most once; in SCL: `USINT#0`) |
| Payload | JSON string — assembled by `FC_BuildJsonPayload` (see below) |

#### Required JSON payload schema

The backend expects each MQTT message to carry a JSON object with these fields:

```json
{
  "tag":       "pump1/pressure",
  "value":     6.12,
  "unit":      "bar",
  "timestamp": 1710000000.0,
  "anomaly":   false
}
```

#### SCL blocks — ready to import into TIA Portal

The `plc_connector/scl/` directory contains six SCL source files that implement the complete
payload-building and MQTT-publishing pipeline on the S7-1200:

| File | Description |
|------|-------------|
| [`DB_MqttConfig.scl`](plc_connector/scl/DB_MqttConfig.scl) | Global Data Block — broker IP/port, keep-alive, Unix epoch offset, and tag name/unit table for all 21 sensors |
| [`DB_SensorValues.scl`](plc_connector/scl/DB_SensorValues.scl) | Global Data Block — one `REAL` member per sensor tag; your process program writes live readings here each scan |
| [`FC_RealToDecStr.scl`](plc_connector/scl/FC_RealToDecStr.scl) | Converts a `REAL` to a compact decimal string (`"6.12"`) — avoids the leading space and E-notation produced by `REAL_TO_STRING` |
| [`FC_BuildJsonPayload.scl`](plc_connector/scl/FC_BuildJsonPayload.scl) | Assembles the full JSON string via a chain of `CONCAT` calls (S_CONV + Concat block pattern) |
| [`FB_MqttTagPublisher.scl`](plc_connector/scl/FB_MqttTagPublisher.scl) | Main Function Block — manages `MQTT_Connect` (with `R_TRIG`-based REQ), iterates over all tags once per interval, calls `FC_BuildJsonPayload`, and fires `MQTT_Publish`; disconnects gracefully when `enable` goes `FALSE` |
| [`OB1_Main.scl`](plc_connector/scl/OB1_Main.scl) | Main Organisation Block — shows how to scale analog inputs into `DB_SensorValues` and call `FB_MqttTagPublisher`; includes a full 7-step TIA Portal setup guide in the header |

#### How to import into TIA Portal

1. Right-click **Program blocks → External source files → Add new external file** and add each
   `.scl` file from `plc_connector/scl/`.
2. Right-click each added source → **Generate blocks from source** — TIA Portal compiles the
   SCL and creates the FC / FB / DB automatically.  Import in this order:
   `DB_MqttConfig` → `DB_SensorValues` → `FC_RealToDecStr` → `FC_BuildJsonPayload` → `FB_MqttTagPublisher` → `OB1_Main`.
3. Update `DB_MqttConfig` in the data view:
   - Set `brokerIp` to the IP of the host running Docker (e.g. `'192.168.1.100'`).
   - Set `clientId` to a unique name for this PLC.
   - Set `unixEpochOffset` = current Unix timestamp − PLC uptime in seconds (see the
     header comment in `DB_MqttConfig.scl` for the exact calculation).
4. In `OB1_Main`, replace the `0.0` placeholders in Section A with the scaled analog-input
   values for your actual hardware (NORM_X + SCALE_X chain, or direct REAL reads from
   another DB).  `DB_SensorValues.scl` includes a LAD wiring example in its header.
5. Download and go online — the dashboard will immediately start showing live PLC data.

#### How `FC_BuildJsonPayload` works (S_CONV / Concat pattern)

```
                  ┌──────────────────────────────────────────────────────────────┐
                  │                  FC_BuildJsonPayload                         │
                  │                                                               │
  REAL tagValue ──┤──► FC_RealToDecStr ──► sValue                               │
                  │        (≡ S_CONV block)                                      │
                  │                                   buf := '{"tag":"'          │
  STRING tagName ─┤──────────────────────────────────► buf := CONCAT(buf, tag)   │
                  │                                   buf := CONCAT(buf, ...)    │
  REAL tagValue ──┤──► sValue ─────────────────────── ► buf := CONCAT(buf, val)  │
                  │                                   buf := CONCAT(buf, ...)    │
  STRING unit ────┤──────────────────────────────────► buf := CONCAT(buf, unit)  │
                  │        (each CONCAT ≡ one Concat  buf := CONCAT(buf, ...)    │
  LREAL timestamp ┤──► LREAL_TO_STRING ─────────────► buf := CONCAT(buf, ts)    │
                  │         block in LAD/FBD)         buf := CONCAT(buf, ...)    │
  BOOL anomaly ───┤──► IF/ELSE → "true"/"false" ────► buf := CONCAT(buf, bool)  │
                  │                                   buf := CONCAT(buf, '}')   │
                  │                                             │                │
                  └─────────────────────────────────────────────┼────────────────┘
                                                                ▼
                                                      MQTT_Publish.PAYLOAD
```

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
