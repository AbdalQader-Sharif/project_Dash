# AI Predictive Maintenance SCADA Dashboard

A complete SCADA-like dashboard for industrial IoT with AI predictive maintenance capabilities.

## Architecture

```
┌─────────────┐     MQTT      ┌─────────────┐     HTTP/WS    ┌─────────────┐
│  Simulator  │ ──────────── ▶│   Backend   │ ◀────────────  │  Frontend   │
│  (25 tags)  │               │  (FastAPI)  │                │  (React/TS) │
└─────────────┘               └──────┬──────┘                └─────────────┘
                                     │
                    ┌────────────────┼────────────────┐
                    ▼                ▼                 ▼
             ┌──────────┐   ┌──────────────┐   ┌──────────────┐
             │ Mosquitto│   │   InfluxDB   │   │  MCP Server  │
             │  (MQTT)  │   │ (Time-series)│   │  (AI Tools)  │
             └──────────┘   └──────────────┘   └──────────────┘
```

## Services

| Service | Port | Description |
|---------|------|-------------|
| Frontend | 3000 | React dashboard |
| Backend | 5000 | FastAPI REST + WebSocket |
| InfluxDB | 8086 | Time-series database |
| Mosquitto | 1883 | MQTT broker |
| MCP Server | 8090 | AI tool server |

## Quick Start

```bash
docker-compose up --build
```

Open http://localhost:3000

### Demo Credentials

| Username | Password | Role |
|----------|----------|------|
| developer | dev123 | developer |
| admin | admin123 | admin |
| operator | op123 | user |

## Features

- **Real-time monitoring**: 25 industrial sensors via MQTT + WebSocket
- **Anomaly detection**: Simulator injects anomalies every 2 minutes
- **Alarm management**: Threshold-based alarms with severity levels
- **Historical data**: InfluxDB time-series storage and visualization
- **JWT authentication**: Role-based access control
- **MCP Server**: AI agent tool access for LLM integrations
- **Docker Compose**: One-command deployment

## MCP Tools

The MCP server exposes tools for AI agents at http://localhost:8090:

- `read_plc_tag` - Read current sensor value
- `get_alarms` - Get active/acknowledged alarms
- `get_historical_data` - Query time-series data
- `get_system_summary` - Get full system state
