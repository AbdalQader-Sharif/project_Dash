import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

from models import User

SECRET_KEY = os.environ.get("SECRET_KEY", "super-secret-jwt-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

# Hardcoded users: username -> {hashed_password, role}
_RAW_USERS = {
    "developer": {"password": "dev123", "role": "developer"},
    "admin": {"password": "admin123", "role": "admin"},
    "operator": {"password": "op123", "role": "user"},
}

USERS = {
    username: {
        "hashed_password": pwd_context.hash(data["password"]),
        "role": data["role"],
    }
    for username, data in _RAW_USERS.items()
}


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def verify_token(token: str) -> Optional[User]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        role: str = payload.get("role")
        if username is None or role is None:
            return None
        return User(username=username, role=role)
    except JWTError:
        return None


def authenticate_user(username: str, password: str) -> Optional[User]:
    user_data = USERS.get(username)
    if not user_data:
        return None
    if not pwd_context.verify(password, user_data["hashed_password"]):
        return None
    return User(username=username, role=user_data["role"])


async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    user = verify_token(token)
    if user is None:
        raise credentials_exception
    return user
