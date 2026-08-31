"""
app/regime/models.py
─────────────────────
Pydantic types for market regime detection.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.core.constants import MarketRegime


class RegimeResult(BaseModel):
    """Output of the Market Regime Engine."""
    symbol: str
    timeframe: str
    timestamp: datetime
    regime: MarketRegime
    confidence: float = Field(ge=0.0, le=1.0)
    indicators: Optional[dict] = None

    @property
    def is_trending(self) -> bool:
        return self.regime in (
            MarketRegime.STRONG_BULL,
            MarketRegime.BULL,
            MarketRegime.BEAR,
            MarketRegime.STRONG_BEAR,
        )

    @property
    def is_bullish(self) -> bool:
        return self.regime in (MarketRegime.STRONG_BULL, MarketRegime.BULL)

    @property
    def is_bearish(self) -> bool:
        return self.regime in (MarketRegime.STRONG_BEAR, MarketRegime.BEAR)

    @property
    def is_uncertain(self) -> bool:
        return self.regime in (MarketRegime.UNCERTAIN, MarketRegime.RANGE)

    def allows_long(self) -> bool:
        """Can we consider LONG signals in this regime?"""
        return self.regime not in (
            MarketRegime.STRONG_BEAR,
            MarketRegime.BEAR,
            MarketRegime.HIGH_VOLATILITY,
        )

    def allows_short(self) -> bool:
        """Can we consider SHORT signals in this regime?"""
        return self.regime not in (
            MarketRegime.STRONG_BULL,
            MarketRegime.BULL,
            MarketRegime.HIGH_VOLATILITY,
        )
