from typing import Optional
from pydantic import BaseModel


class SensorReading(BaseModel):
    tag: str
    value: float
    unit: str
    timestamp: float
    anomaly: bool


class Alarm(BaseModel):
    id: str
    tag: str
    message: str
    severity: str  # 'critical', 'warning', 'info'
    timestamp: float
    acknowledged: bool = False
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[float] = None


class LoginRequest(BaseModel):
    username: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str
    role: str
    username: str


class User(BaseModel):
    username: str
    role: str  # 'developer', 'admin', 'user'


class AcknowledgeRequest(BaseModel):
    username: Optional[str] = None
