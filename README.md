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
PLC Simulator ──MQTT──► Mosquitto ──MQTT──► Backend (FastAPI)
                                                │
                                          InfluxDB (history)
                                                │
                                    WebSocket / REST API
                                                │
                                        Frontend (React)
                                                │
                                        MCP Server (AI tools)
```

## MCP Server API

The MCP server exposes the plant data as tools for AI agents:

- `GET /tools` — list available tools
- `POST /tools/call` — invoke a tool

Available tools: `get_sensors`, `get_sensor`, `get_alarms`, `get_history`, `get_health`.