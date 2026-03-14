import logging
import os
from typing import Any, Dict, Optional

import httpx
from fastapi import FastAPI
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:5000")

app = FastAPI(title="MCP Tool Server")

TOOLS = [
    {
        "name": "read_plc_tag",
        "description": "Read the current value of a PLC/sensor tag by name",
        "parameters": {"tag_name": "string - the tag name, e.g. pump1/flow"},
    },
    {
        "name": "get_alarms",
        "description": "Get alarms filtered by status",
        "parameters": {"status": "string - 'active', 'acknowledged', or 'all'"},
    },
    {
        "name": "get_historical_data",
        "description": "Get historical sensor readings for a tag",
        "parameters": {
            "tag_name": "string - the tag name",
            "hours": "integer - number of hours of history (default 1)",
        },
    },
    {
        "name": "get_system_summary",
        "description": "Get a summary of the entire system state",
        "parameters": {},
    },
]


class ReadTagRequest(BaseModel):
    tag_name: str


class GetAlarmsRequest(BaseModel):
    status: str = "all"


class GetHistoricalRequest(BaseModel):
    tag_name: str
    hours: int = 1


def tool_response(tool_name: str, result: Any = None, error: Optional[str] = None) -> Dict:
    return {"tool": tool_name, "result": result, "error": error}


@app.get("/tools")
async def list_tools():
    return {"tools": TOOLS}


@app.post("/tools/read_plc_tag")
async def read_plc_tag(request: ReadTagRequest):
    tool_name = "read_plc_tag"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{BACKEND_URL}/api/sensors/{request.tag_name}")
            if resp.status_code == 404:
                return tool_response(tool_name, error=f"Tag '{request.tag_name}' not found")
            resp.raise_for_status()
            return tool_response(tool_name, result=resp.json())
    except Exception as e:
        logger.error(f"Error reading tag: {e}")
        return tool_response(tool_name, error=str(e))


@app.post("/tools/get_alarms")
async def get_alarms(request: GetAlarmsRequest):
    tool_name = "get_alarms"
    try:
        params = {}
        if request.status == "active":
            params["acknowledged"] = "false"
        elif request.status == "acknowledged":
            params["acknowledged"] = "true"

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{BACKEND_URL}/api/alarms", params=params)
            resp.raise_for_status()
            return tool_response(tool_name, result=resp.json())
    except Exception as e:
        logger.error(f"Error fetching alarms: {e}")
        return tool_response(tool_name, error=str(e))


@app.post("/tools/get_historical_data")
async def get_historical_data(request: GetHistoricalRequest):
    tool_name = "get_historical_data"
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                f"{BACKEND_URL}/api/history/{request.tag_name}",
                params={"hours": request.hours},
            )
            resp.raise_for_status()
            return tool_response(tool_name, result=resp.json())
    except Exception as e:
        logger.error(f"Error fetching history: {e}")
        return tool_response(tool_name, error=str(e))


@app.post("/tools/get_system_summary")
async def get_system_summary():
    tool_name = "get_system_summary"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            sensors_resp = await client.get(f"{BACKEND_URL}/api/sensors")
            alarms_resp = await client.get(f"{BACKEND_URL}/api/alarms", params={"acknowledged": "false"})
            sensors_resp.raise_for_status()
            alarms_resp.raise_for_status()

            sensors = sensors_resp.json()
            active_alarms = alarms_resp.json()

            sensors_in_alarm = [a["tag"] for a in active_alarms]

            return tool_response(tool_name, result={
                "total_sensors": len(sensors),
                "active_alarms": len(active_alarms),
                "sensors_in_alarm": sensors_in_alarm,
                "current_readings": sensors,
            })
    except Exception as e:
        logger.error(f"Error getting system summary: {e}")
        return tool_response(tool_name, error=str(e))


@app.get("/health")
async def health():
    return {"status": "ok"}
