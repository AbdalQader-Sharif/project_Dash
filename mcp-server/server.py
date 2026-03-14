"""
MCP (Model Context Protocol) server that exposes the PLC dashboard data
as tools accessible to AI agents.

Endpoints follow a simple JSON-RPC style:
  GET  /tools          – list available tools
  POST /tools/call     – call a tool by name with arguments
  GET  /health         – health check
"""
import logging
import os
from typing import Any, Dict, List, Optional

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BACKEND_URL = os.environ.get("BACKEND_URL", "http://backend:5000")

app = FastAPI(title="PLC MCP Server", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Tool definitions
# ---------------------------------------------------------------------------

TOOLS: List[Dict[str, Any]] = [
    {
        "name": "get_sensors",
        "description": "Retrieve the latest reading for all sensors in the plant.",
        "parameters": {},
    },
    {
        "name": "get_sensor",
        "description": "Retrieve the latest reading for a specific sensor tag.",
        "parameters": {
            "tag": {
                "type": "string",
                "description": "Sensor tag path, e.g. 'pump1/pressure'",
                "required": True,
            }
        },
    },
    {
        "name": "get_alarms",
        "description": "Retrieve the current alarm list. Optionally filter by acknowledged state.",
        "parameters": {
            "acknowledged": {
                "type": "boolean",
                "description": "If true, return only acknowledged alarms. If false, only active alarms. Omit for all.",
                "required": False,
            }
        },
    },
    {
        "name": "get_history",
        "description": "Retrieve historical time-series data for a sensor tag from InfluxDB.",
        "parameters": {
            "tag": {
                "type": "string",
                "description": "Sensor tag path, e.g. 'pump1/pressure'",
                "required": True,
            },
            "hours": {
                "type": "integer",
                "description": "Number of hours of history to retrieve (default 1).",
                "required": False,
            },
        },
    },
    {
        "name": "get_health",
        "description": "Check the health of the backend service.",
        "parameters": {},
    },
]


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------

class ToolCallRequest(BaseModel):
    name: str
    arguments: Optional[Dict[str, Any]] = {}


class ToolCallResponse(BaseModel):
    tool: str
    result: Any
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/tools")
async def list_tools():
    return {"tools": TOOLS}


@app.post("/tools/call", response_model=ToolCallResponse)
async def call_tool(request: ToolCallRequest):
    name = request.name
    args = request.arguments or {}

    async with httpx.AsyncClient(base_url=BACKEND_URL, timeout=10.0) as client:
        try:
            if name == "get_sensors":
                resp = await client.get("/api/sensors")
                resp.raise_for_status()
                return ToolCallResponse(tool=name, result=resp.json())

            elif name == "get_sensor":
                tag = args.get("tag")
                if not tag:
                    raise HTTPException(status_code=400, detail="'tag' argument is required")
                resp = await client.get(f"/api/sensors/{tag}")
                resp.raise_for_status()
                return ToolCallResponse(tool=name, result=resp.json())

            elif name == "get_alarms":
                params: Dict[str, Any] = {}
                if "acknowledged" in args:
                    params["acknowledged"] = str(args["acknowledged"]).lower()
                resp = await client.get("/api/alarms", params=params)
                resp.raise_for_status()
                return ToolCallResponse(tool=name, result=resp.json())

            elif name == "get_history":
                tag = args.get("tag")
                if not tag:
                    raise HTTPException(status_code=400, detail="'tag' argument is required")
                hours = int(args.get("hours", 1))
                resp = await client.get(f"/api/history/{tag}", params={"hours": hours})
                resp.raise_for_status()
                return ToolCallResponse(tool=name, result=resp.json())

            elif name == "get_health":
                resp = await client.get("/api/health")
                resp.raise_for_status()
                return ToolCallResponse(tool=name, result=resp.json())

            else:
                raise HTTPException(status_code=404, detail=f"Unknown tool: '{name}'")

        except HTTPException:
            raise
        except Exception as exc:
            logger.error(f"Tool '{name}' error: {exc}")
            return ToolCallResponse(tool=name, result=None, error=str(exc))


@app.get("/health")
async def health():
    return {"status": "ok", "service": "mcp-server"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8090)
