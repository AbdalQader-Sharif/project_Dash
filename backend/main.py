import asyncio
import logging
import os
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Depends, status
from fastapi.middleware.cors import CORSMiddleware

from models import LoginRequest, Token, AcknowledgeRequest, User
from auth import authenticate_user, create_access_token, get_current_user
import mqtt_client as mqtt_state
from mqtt_client import SENSOR_STORE, ALARM_LIST, start_mqtt_client, set_broadcast

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CORS_ORIGINS = os.environ.get(
    "CORS_ORIGINS",
    "http://localhost:3000,http://localhost:80,http://frontend"
).split(",")

# WebSocket connections
websocket_connections: set = set()


async def broadcast_sensor_update(data: dict):
    if not websocket_connections:
        return
    dead = set()
    for ws in websocket_connections.copy():
        try:
            await ws.send_json(data)
        except Exception:
            dead.add(ws)
    for ws in dead:
        websocket_connections.discard(ws)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Set broadcast function in mqtt_client
    set_broadcast(websocket_connections, broadcast_sensor_update)
    # Start MQTT client
    await start_mqtt_client()
    logger.info("Application startup complete")
    yield
    logger.info("Application shutting down")


app = FastAPI(title="PLC Dashboard API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/api/auth/login", response_model=Token)
async def login(request: LoginRequest):
    user = authenticate_user(request.username, request.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )
    access_token = create_access_token({"sub": user.username, "role": user.role})
    return Token(
        access_token=access_token,
        token_type="bearer",
        role=user.role,
        username=user.username,
    )


@app.get("/api/sensors")
async def get_sensors():
    return {tag: reading.model_dump() for tag, reading in SENSOR_STORE.items()}


@app.get("/api/sensors/{tag:path}")
async def get_sensor(tag: str):
    reading = SENSOR_STORE.get(tag)
    if not reading:
        raise HTTPException(status_code=404, detail=f"Sensor '{tag}' not found")
    return reading.model_dump()


@app.get("/api/alarms")
async def get_alarms(acknowledged: Optional[bool] = None):
    with mqtt_state._alarm_lock:
        alarms = list(ALARM_LIST)
    if acknowledged is None:
        return [a.model_dump() for a in alarms]
    return [a.model_dump() for a in alarms if a.acknowledged == acknowledged]


@app.post("/api/alarms/{alarm_id}/acknowledge")
async def acknowledge_alarm(
    alarm_id: str,
    request: AcknowledgeRequest = AcknowledgeRequest(),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in ("admin", "developer"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    import time
    with mqtt_state._alarm_lock:
        for alarm in ALARM_LIST:
            if alarm.id == alarm_id:
                alarm.acknowledged = True
                alarm.acknowledged_by = request.username or current_user.username
                alarm.acknowledged_at = time.time()
                return {"status": "ok", "alarm_id": alarm_id}

    raise HTTPException(status_code=404, detail="Alarm not found")


@app.get("/api/history/{tag:path}")
async def get_history(tag: str, hours: int = 1):
    try:
        from influx_client import influx_client
        data = influx_client.query_historical(tag, hours)
        return data
    except Exception as e:
        logger.error(f"Error fetching history: {e}")
        return []


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    websocket_connections.add(websocket)
    logger.info(f"WebSocket connected, total: {len(websocket_connections)}")
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        websocket_connections.discard(websocket)
        logger.info(f"WebSocket disconnected, total: {len(websocket_connections)}")


@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "sensors": len(SENSOR_STORE),
        "alarms": len(ALARM_LIST),
    }
