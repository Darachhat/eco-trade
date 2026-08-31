"""
app/core/security.py
─────────────────────
API key authentication and secret management utilities.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
import time
from typing import Optional

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("app")

API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(api_key: Optional[str] = Security(API_KEY_HEADER)) -> str:
    """
    FastAPI dependency: validates the X-API-Key header against APP_SECRET_KEY.
    Returns the key on success or raises 403.
    """
    if not api_key or not hmac.compare_digest(api_key, settings.app_secret_key):
        logger.warning("Unauthorized API key attempt")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or missing API key",
        )
    return api_key


def generate_signal_id(symbol: str, sequence: int) -> str:
    """
    Generate a deterministic signal ID.
    Format: AI-YYYYMMDD-SYMBOL-NNNNNN
    e.g.    AI-20260830-BTCUSDT-000001
    """
    import datetime

    today = datetime.datetime.utcnow().strftime("%Y%m%d")
    base_symbol = symbol.replace("USDT", "").replace("USD", "")
    return f"AI-{today}-{base_symbol}-{sequence:06d}"


def create_bybit_signature(secret: str, params: str, timestamp: int) -> str:
    """
    Creates a HMAC-SHA256 signature for Bybit private API requests.
    """
    param_str = f"{timestamp}{settings.bybit_api_key}5000{params}"
    return hmac.new(
        secret.encode("utf-8"),
        param_str.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def get_bybit_headers(params: str = "") -> dict[str, str]:
    """
    Returns headers required for authenticated Bybit REST requests.
    """
    timestamp = int(time.time() * 1000)
    signature = create_bybit_signature(settings.bybit_api_secret, params, timestamp)
    return {
        "X-BAPI-API-KEY": settings.bybit_api_key,
        "X-BAPI-TIMESTAMP": str(timestamp),
        "X-BAPI-SIGN": signature,
        "X-BAPI-RECV-WINDOW": "5000",
        "Content-Type": "application/json",
    }
