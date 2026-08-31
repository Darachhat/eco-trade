"""
app/regime/detector.py
───────────────────────
Market Regime Detection Engine.

Uses multiple independent signals:
- ADX (trend strength)
- EMA structure (direction)
- Rolling volatility (high/low vol regimes)
- Returns (bull/bear momentum)
- GMM clustering (unsupervised regime discovery)
- HMM (hidden states)

Produces: {"regime": "BULL", "confidence": 0.84}
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

import numpy as np
import pandas as pd
from sklearn.mixture import GaussianMixture

from app.core.constants import MarketRegime
from app.core.logging import get_logger
from app.regime.models import RegimeResult

logger = get_logger("model")


class MarketRegimeDetector:
    """
    Detects the current market regime using multiple signals.
    Does NOT rely on a single indicator.
    """

    def __init__(self) -> None:
        self._gmm: Optional[GaussianMixture] = None
        self._gmm_fitted = False

    def detect(
        self,
        df: pd.DataFrame,
        symbol: str,
        timeframe: str,
    ) -> RegimeResult:
        """
        Detect regime for the most recent candle in the DataFrame.

        df must contain feature columns computed by FeaturePipeline.
        Returns the regime at the latest timestamp.
        """
        if df.empty or len(df) < 50:
            return RegimeResult(
                symbol=symbol,
                timeframe=timeframe,
                timestamp=datetime.utcnow(),
                regime=MarketRegime.UNCERTAIN,
                confidence=0.5,
            )

        latest = df.iloc[-1]
        indicators = self._compute_indicators(df)
        regime, confidence = self._classify_regime(indicators, latest)

        return RegimeResult(
            symbol=symbol,
            timeframe=timeframe,
            timestamp=latest.get("open_time", datetime.utcnow()),
            regime=regime,
            confidence=confidence,
            indicators=indicators,
        )

    def _compute_indicators(self, df: pd.DataFrame) -> dict:
        """Compute all regime-detection signals from the latest row and rolling data."""
        latest = df.iloc[-1]
        indicators: dict = {}

        # 1. ADX — trend strength
        if "adx" in df.columns:
            adx_val = float(latest["adx"])
            indicators["adx"] = adx_val
            indicators["trending"] = adx_val > 25
            indicators["strongly_trending"] = adx_val > 40

        # 2. EMA structure — direction
        ema_bullish = 0
        ema_bearish = 0
        for col in ["ema_9_above_20", "ema_20_above_50", "ema_50_above_200"]:
            if col in df.columns:
                val = float(latest[col])
                ema_bullish += val
                ema_bearish += (1 - val)
        indicators["ema_bullish_count"] = ema_bullish  # 0-3
        indicators["ema_bearish_count"] = ema_bearish  # 0-3

        # 3. Volatility regime
        if "vol_regime" in df.columns:
            indicators["vol_regime"] = float(latest["vol_regime"])
        if "realized_vol_20" in df.columns:
            rv = float(latest["realized_vol_20"]) if not np.isnan(latest["realized_vol_20"]) else 0.0
            indicators["realized_vol"] = rv

        # 4. Returns — recent momentum
        if "returns_20" in df.columns:
            r20 = float(latest["returns_20"]) if not np.isnan(latest["returns_20"]) else 0.0
            indicators["return_20"] = r20
        elif "log_returns_1" in df.columns:
            lr = df["log_returns_1"].tail(20)
            indicators["return_20"] = float(lr.sum())

        # 5. RSI
        if "rsi_14" in df.columns:
            rsi_val = float(latest["rsi_14"])
            indicators["rsi"] = rsi_val
            indicators["rsi_bullish"] = rsi_val > 50
            indicators["rsi_overbought"] = rsi_val > 70
            indicators["rsi_oversold"] = rsi_val < 30

        # 6. MACD
        if "macd_bullish" in df.columns:
            indicators["macd_bullish"] = float(latest["macd_bullish"])

        # 7. GMM-based regime (if we have enough data)
        if len(df) >= 100:
            gmm_regime = self._gmm_regime(df)
            indicators["gmm_regime"] = gmm_regime

        return indicators

    def _gmm_regime(self, df: pd.DataFrame) -> int:
        """
        Use GMM to detect unsupervised regimes.
        Returns 0 (bear/low vol), 1 (range), or 2 (bull/high momentum).
        """
        try:
            features = []
            if "log_returns_1" in df.columns:
                lr = df["log_returns_1"].dropna()
                features.append(lr.rolling(20).mean().dropna())
                features.append(lr.rolling(20).std().dropna())

            if len(features) < 2:
                return 1

            X = pd.concat(features, axis=1).dropna()
            if len(X) < 50:
                return 1

            if not self._gmm_fitted or self._gmm is None:
                self._gmm = GaussianMixture(n_components=3, random_state=42, max_iter=100)
                self._gmm.fit(X.values[-200:])  # Fit on recent 200 points
                self._gmm_fitted = True

            latest_row = X.iloc[-1:].values
            label = int(self._gmm.predict(latest_row)[0])
            return label
        except Exception as e:
            logger.debug("GMM regime detection failed", error=str(e))
            return 1

    def _classify_regime(
        self, indicators: dict, latest_row: pd.Series
    ) -> tuple[MarketRegime, float]:
        """
        Vote-based regime classification combining all signals.
        Returns (regime, confidence).
        """
        votes: dict[str, float] = {
            "STRONG_BULL": 0.0,
            "BULL": 0.0,
            "RANGE": 0.0,
            "BEAR": 0.0,
            "STRONG_BEAR": 0.0,
            "HIGH_VOLATILITY": 0.0,
        }
        total_weight = 0.0

        # ── ADX vote (weight: 3) ──────────────────────────
        adx_weight = 3.0
        if "adx" in indicators:
            adx = indicators["adx"]
            total_weight += adx_weight
            if indicators.get("strongly_trending"):
                if indicators.get("ema_bullish_count", 0) >= 2:
                    votes["STRONG_BULL"] += adx_weight
                elif indicators.get("ema_bearish_count", 0) >= 2:
                    votes["STRONG_BEAR"] += adx_weight
                else:
                    votes["RANGE"] += adx_weight
            elif indicators.get("trending"):
                if indicators.get("ema_bullish_count", 0) >= 2:
                    votes["BULL"] += adx_weight
                elif indicators.get("ema_bearish_count", 0) >= 2:
                    votes["BEAR"] += adx_weight
                else:
                    votes["RANGE"] += adx_weight
            else:
                votes["RANGE"] += adx_weight

        # ── EMA structure vote (weight: 4) ────────────────
        ema_weight = 4.0
        bull_count = indicators.get("ema_bullish_count", 0)
        bear_count = indicators.get("ema_bearish_count", 0)
        total_weight += ema_weight
        if bull_count >= 3:
            votes["STRONG_BULL"] += ema_weight
        elif bull_count >= 2:
            votes["BULL"] += ema_weight
        elif bear_count >= 3:
            votes["STRONG_BEAR"] += ema_weight
        elif bear_count >= 2:
            votes["BEAR"] += ema_weight
        else:
            votes["RANGE"] += ema_weight

        # ── Return vote (weight: 2) ───────────────────────
        ret_weight = 2.0
        ret_20 = indicators.get("return_20", 0.0)
        total_weight += ret_weight
        if ret_20 > 0.05:
            votes["BULL"] += ret_weight
        elif ret_20 > 0.10:
            votes["STRONG_BULL"] += ret_weight
        elif ret_20 < -0.05:
            votes["BEAR"] += ret_weight
        elif ret_20 < -0.10:
            votes["STRONG_BEAR"] += ret_weight
        else:
            votes["RANGE"] += ret_weight

        # ── Volatility vote (weight: 2) ───────────────────
        vol_weight = 2.0
        vol_regime = indicators.get("vol_regime", 1.0)
        total_weight += vol_weight
        if vol_regime >= 2.0:
            votes["HIGH_VOLATILITY"] += vol_weight
        else:
            # Give vote to the dominant direction
            if bull_count >= 2:
                votes["BULL"] += vol_weight * 0.5
            elif bear_count >= 2:
                votes["BEAR"] += vol_weight * 0.5
            else:
                votes["RANGE"] += vol_weight

        # ── RSI vote (weight: 1.5) ────────────────────────
        rsi_weight = 1.5
        if "rsi" in indicators:
            total_weight += rsi_weight
            rsi = indicators["rsi"]
            if rsi > 70 and bull_count >= 2:
                votes["STRONG_BULL"] += rsi_weight
            elif rsi > 55:
                votes["BULL"] += rsi_weight
            elif rsi < 30 and bear_count >= 2:
                votes["STRONG_BEAR"] += rsi_weight
            elif rsi < 45:
                votes["BEAR"] += rsi_weight
            else:
                votes["RANGE"] += rsi_weight

        # ── MACD vote (weight: 1.5) ───────────────────────
        macd_weight = 1.5
        if "macd_bullish" in indicators:
            total_weight += macd_weight
            if indicators["macd_bullish"] > 0.5:
                votes["BULL"] += macd_weight
            else:
                votes["BEAR"] += macd_weight

        # ── Winner ───────────────────────────────────────
        if total_weight == 0:
            return MarketRegime.UNCERTAIN, 0.5

        best_regime = max(votes, key=lambda k: votes[k])
        confidence = votes[best_regime] / total_weight

        # Map to enum
        regime_map = {
            "STRONG_BULL": MarketRegime.STRONG_BULL,
            "BULL": MarketRegime.BULL,
            "RANGE": MarketRegime.RANGE,
            "BEAR": MarketRegime.BEAR,
            "STRONG_BEAR": MarketRegime.STRONG_BEAR,
            "HIGH_VOLATILITY": MarketRegime.HIGH_VOLATILITY,
        }

        # If confidence is too low, return UNCERTAIN
        if confidence < 0.35:
            return MarketRegime.UNCERTAIN, confidence

        return regime_map.get(best_regime, MarketRegime.UNCERTAIN), round(confidence, 4)
