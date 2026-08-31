"""
app/strategy/signal_engine.py
──────────────────────────────
Signal Engine — applies all conditions to produce LONG/SHORT/NO_TRADE/WAIT.
Computes Signal Quality Score (Section 55).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

import pandas as pd

from app.core.config import settings
from app.core.constants import MarketRegime, SignalDirection
from app.core.logging import get_logger
from app.regime.models import RegimeResult
from app.strategy.entry import (
    EntryZone,
    StopLoss,
    TakeProfit,
    calculate_entry_zone,
    calculate_stop_loss,
    calculate_take_profits,
)

logger = get_logger("trading")


@dataclass
class SignalQualityScore:
    model_agreement: float = 0.0
    probability: float = 0.0
    mtf_alignment: float = 0.0
    risk_reward: float = 0.0
    regime_score: float = 0.0
    liquidity: float = 0.0

    @property
    def total(self) -> float:
        return (
            self.model_agreement * 20
            + self.probability * 20
            + self.mtf_alignment * 20
            + self.risk_reward * 10
            + self.regime_score * 10
            + self.liquidity * 10
        )

    def to_dict(self) -> dict:
        return {
            "model_agreement": round(self.model_agreement * 20, 1),
            "probability": round(self.probability * 20, 1),
            "mtf_alignment": round(self.mtf_alignment * 20, 1),
            "risk_reward": round(self.risk_reward * 10, 1),
            "regime_score": round(self.regime_score * 10, 1),
            "liquidity": round(self.liquidity * 10, 1),
            "total": round(self.total, 1),
        }


@dataclass
class TradeSignal:
    """Complete trade signal output."""
    symbol: str
    timeframe: str
    direction: SignalDirection
    generated_at: datetime

    entry_zone: Optional[EntryZone] = None
    stop_loss: Optional[StopLoss] = None
    take_profit: Optional[TakeProfit] = None

    confidence: float = 0.0
    model_agreement: float = 0.0
    regime: Optional[str] = None

    probability_long: float = 0.0
    probability_short: float = 0.0
    probability_no_trade: float = 1.0

    model_predictions: dict = field(default_factory=dict)
    ensemble_weights: dict = field(default_factory=dict)
    mtf_consensus: dict = field(default_factory=dict)
    quality_score: Optional[SignalQualityScore] = None
    explanation: dict = field(default_factory=dict)

    # Reason for NO_TRADE
    no_trade_reason: Optional[str] = None


class SignalEngine:
    """
    Final signal generation after all checks pass.

    Conditions for a LONG signal:
    1. Ensemble probability >= MIN_CONFIDENCE
    2. Model agreement >= MIN_MODEL_AGREEMENT
    3. Higher timeframe trend supports direction
    4. Market regime is suitable
    5. Risk/Reward >= MIN_RISK_REWARD
    6. Spread acceptable
    7. No abnormal volatility
    8. No risk limit violation
    """

    def __init__(self) -> None:
        self._min_confidence = settings.min_confidence
        self._min_agreement = settings.min_model_agreement
        self._min_rr = settings.min_risk_reward
        self._min_quality = settings.min_signal_quality_score

    def generate(
        self,
        ensemble_result: dict,
        df: pd.DataFrame,
        symbol: str,
        timeframe: str,
        regime: Optional[RegimeResult] = None,
        mtf_results: Optional[dict] = None,
        current_price: Optional[float] = None,
        spread: float = 0.0,
        risk_ok: bool = True,
    ) -> TradeSignal:
        """
        Apply all conditions and generate a TradeSignal.

        Returns a LONG/SHORT signal if all conditions pass,
        otherwise returns NO_TRADE with reason.
        """
        direction = ensemble_result.get("direction", SignalDirection.NO_TRADE)
        confidence = ensemble_result.get("confidence", 0.0)
        agreement = ensemble_result.get("model_agreement", 0.0)
        prob_long = ensemble_result.get("probability_long", 0.0)
        prob_short = ensemble_result.get("probability_short", 0.0)
        prob_no_trade = ensemble_result.get("probability_no_trade", 1.0)
        model_table = ensemble_result.get("model_table", "")

        price = current_price or (float(df["close"].iloc[-1]) if not df.empty else 0.0)
        ts = datetime.utcnow()

        # ── Gate 1: Direction must be LONG or SHORT ─────────────────────
        if direction not in (SignalDirection.LONG, SignalDirection.SHORT):
            return self._no_trade(symbol, timeframe, ts, "Ensemble direction = NO_TRADE or WAIT")

        # ── Gate 2: Confidence threshold ────────────────────────────────
        if confidence < self._min_confidence:
            return self._no_trade(
                symbol, timeframe, ts,
                f"Confidence {confidence:.1%} < {self._min_confidence:.1%}"
            )

        # ── Gate 3: Model agreement threshold ───────────────────────────
        if agreement < self._min_agreement:
            return self._no_trade(
                symbol, timeframe, ts,
                f"Agreement {agreement:.1%} < {self._min_agreement:.1%}"
            )

        # ── Gate 4: Market regime ────────────────────────────────────────
        if regime:
            if direction == SignalDirection.LONG and not regime.allows_long():
                return self._no_trade(
                    symbol, timeframe, ts,
                    f"Regime {regime.regime} does not support LONG"
                )
            if direction == SignalDirection.SHORT and not regime.allows_short():
                return self._no_trade(
                    symbol, timeframe, ts,
                    f"Regime {regime.regime} does not support SHORT"
                )

        # ── Gate 5: Risk limits ──────────────────────────────────────────
        if not risk_ok:
            return self._no_trade(symbol, timeframe, ts, "Risk limit violation")

        # ── Calculate entry, SL, TP ─────────────────────────────────────
        entry_zone = calculate_entry_zone(df, direction, price)
        sl = calculate_stop_loss(df, direction, entry_zone.center)
        tp = calculate_take_profits(df, direction, entry_zone.center, sl.distance)

        # ── Gate 6: R:R check ────────────────────────────────────────────
        if tp.risk_reward_tp1 < self._min_rr:
            return self._no_trade(
                symbol, timeframe, ts,
                f"R:R {tp.risk_reward_tp1:.1f} < {self._min_rr:.1f}"
            )

        # ── Gate 7: Spread ───────────────────────────────────────────────
        max_spread_pct = 0.001  # 0.1% of price
        if price > 0 and spread / price > max_spread_pct:
            return self._no_trade(symbol, timeframe, ts, f"Spread too wide: {spread/price:.3%}")

        # ── Quality Score ────────────────────────────────────────────────
        quality = self._compute_quality(
            agreement=agreement,
            confidence=confidence,
            mtf_results=mtf_results,
            rr=tp.risk_reward_tp1,
            regime=regime,
        )

        if quality.total < self._min_quality:
            return self._no_trade(
                symbol, timeframe, ts,
                f"Signal quality score {quality.total:.0f} < {self._min_quality}"
            )

        # ── Build explanation ─────────────────────────────────────────────
        explanation = self._build_explanation(df, direction, regime)

        signal = TradeSignal(
            symbol=symbol,
            timeframe=timeframe,
            direction=direction,
            generated_at=ts,
            entry_zone=entry_zone,
            stop_loss=sl,
            take_profit=tp,
            confidence=confidence,
            model_agreement=agreement,
            regime=regime.regime.value if regime else None,
            probability_long=prob_long,
            probability_short=prob_short,
            probability_no_trade=prob_no_trade,
            model_predictions={
                o.model: {
                    "direction": o.prediction.value,
                    "confidence": o.confidence,
                    "prob_long": o.probability_long,
                    "prob_short": o.probability_short,
                }
                for o in ensemble_result.get("model_outputs", [])
            },
            ensemble_weights=ensemble_result.get("weights", {}),
            mtf_consensus=mtf_results or {},
            quality_score=quality,
            explanation=explanation,
        )

        logger.info(
            "Signal generated",
            symbol=symbol,
            timeframe=timeframe,
            direction=direction.value,
            confidence=confidence,
            agreement=agreement,
            quality=quality.total,
            rr=tp.risk_reward_tp1,
        )

        return signal

    def _compute_quality(
        self,
        agreement: float,
        confidence: float,
        mtf_results: Optional[dict],
        rr: float,
        regime: Optional[RegimeResult],
    ) -> SignalQualityScore:
        """Compute signal quality score (out of 80 max total)."""
        q = SignalQualityScore()
        q.model_agreement = min(agreement / 1.0, 1.0)
        q.probability = min(confidence / 1.0, 1.0)

        if mtf_results:
            alignment = max(
                sum(1 for r in mtf_results.values() if r.get("direction") == "LONG") / max(len(mtf_results), 1),
                sum(1 for r in mtf_results.values() if r.get("direction") == "SHORT") / max(len(mtf_results), 1),
            )
            q.mtf_alignment = alignment
        else:
            q.mtf_alignment = 0.5

        q.risk_reward = min((rr - 1.0) / 4.0, 1.0)  # 1R=0, 5R=1.0

        if regime:
            regime_scores = {
                "STRONG_BULL": 0.9, "BULL": 0.8, "RANGE": 0.5,
                "BEAR": 0.8, "STRONG_BEAR": 0.9,
                "HIGH_VOLATILITY": 0.2, "UNCERTAIN": 0.3,
            }
            q.regime_score = regime_scores.get(str(regime.regime), 0.5) * regime.confidence
        else:
            q.regime_score = 0.5

        q.liquidity = 0.8  # Default — would be computed from OB data

        return q

    def _build_explanation(
        self,
        df: pd.DataFrame,
        direction: SignalDirection,
        regime: Optional[RegimeResult],
    ) -> dict:
        """Build human-readable explanation for the signal."""
        positives = []
        negatives = []

        if df.empty:
            return {"positives": positives, "negatives": negatives}

        latest = df.iloc[-1]

        if direction == SignalDirection.LONG:
            if float(latest.get("ema_50_above_200", 0)) > 0.5:
                positives.append("Strong higher-timeframe trend (EMA 50 > 200)")
            if float(latest.get("rsi_14", 50)) > 50:
                positives.append(f"Positive RSI momentum ({latest.get('rsi_14', 50):.0f})")
            if float(latest.get("macd_bullish", 0)) > 0.5:
                positives.append("Bullish MACD")
            if float(latest.get("above_vwap", 0)) > 0.5:
                positives.append("Price above VWAP")
            if float(latest.get("adx", 20)) > 25:
                positives.append(f"Strong trend (ADX {latest.get('adx', 20):.0f})")
            if float(latest.get("vol_regime", 1)) >= 2:
                negatives.append("High volatility environment")
        else:
            if float(latest.get("ema_50_above_200", 0)) < 0.5:
                positives.append("Bearish EMA structure")
            if float(latest.get("rsi_14", 50)) < 50:
                positives.append(f"Bearish RSI ({latest.get('rsi_14', 50):.0f})")
            if float(latest.get("macd_bullish", 0)) < 0.5:
                positives.append("Bearish MACD")
            if float(latest.get("above_vwap", 0)) < 0.5:
                positives.append("Price below VWAP")

        if regime:
            positives.append(f"Market regime: {regime.regime.value} ({regime.confidence:.0%} confidence)")

        return {"positives": positives, "negatives": negatives}

    @staticmethod
    def _no_trade(
        symbol: str, timeframe: str, ts: datetime, reason: str
    ) -> TradeSignal:
        logger.debug("NO_TRADE signal", symbol=symbol, timeframe=timeframe, reason=reason)
        return TradeSignal(
            symbol=symbol,
            timeframe=timeframe,
            direction=SignalDirection.NO_TRADE,
            generated_at=ts,
            no_trade_reason=reason,
        )
