"""
app/ensemble/consensus.py
──────────────────────────
Model agreement and multi-timeframe consensus calculations.
"""

from __future__ import annotations

from typing import Optional

from app.core.constants import SignalDirection
from app.core.logging import get_logger
from app.models.base import ModelOutput

logger = get_logger("model")


class ConsensusEngine:
    """
    Calculates:
    1. Model agreement percentage
    2. Weighted ensemble probability
    3. Multi-timeframe consensus
    4. Disagreement threshold — force NO_TRADE if too conflicted
    """

    def __init__(self, min_agreement: float = 0.70) -> None:
        self.min_agreement = min_agreement

    def calculate(
        self,
        outputs: list[ModelOutput],
        weights: dict[str, float],
    ) -> dict:
        """
        Compute weighted ensemble result from individual model outputs.

        Returns:
            {
                "direction": SignalDirection,
                "probability_long": float,
                "probability_short": float,
                "probability_no_trade": float,
                "confidence": float,
                "model_agreement": float,
                "model_count": int,
            }
        """
        if not outputs:
            return self._no_trade_result()

        # ── Weighted probabilities ────────────────────
        total_weight = 0.0
        w_prob_long = 0.0
        w_prob_short = 0.0
        w_prob_no_trade = 0.0

        model_directions: list[str] = []

        for out in outputs:
            w = weights.get(out.model, 1.0 / len(outputs))
            w_prob_long += out.probability_long * w
            w_prob_short += out.probability_short * w
            w_prob_no_trade += out.probability_no_trade * w
            total_weight += w
            model_directions.append(out.prediction.value)

        if total_weight > 0:
            w_prob_long /= total_weight
            w_prob_short /= total_weight
            w_prob_no_trade /= total_weight

        # Normalize
        total_prob = w_prob_long + w_prob_short + w_prob_no_trade
        if total_prob > 0:
            w_prob_long /= total_prob
            w_prob_short /= total_prob
            w_prob_no_trade /= total_prob

        # ── Model agreement ───────────────────────────
        # Agreement = fraction of models voting for the majority direction
        direction_counts: dict[str, int] = {}
        for d in model_directions:
            direction_counts[d] = direction_counts.get(d, 0) + 1

        majority_count = max(direction_counts.values()) if direction_counts else 0
        agreement = majority_count / len(model_directions) if model_directions else 0.0

        # ── Final direction ───────────────────────────
        if agreement < self.min_agreement:
            # Too much disagreement → NO TRADE
            logger.debug(
                "Ensemble: insufficient agreement",
                agreement=round(agreement, 2),
                min_required=self.min_agreement,
            )
            direction = SignalDirection.NO_TRADE
            confidence = w_prob_no_trade
        elif w_prob_long >= w_prob_short and w_prob_long >= w_prob_no_trade:
            direction = SignalDirection.LONG
            confidence = w_prob_long
        elif w_prob_short >= w_prob_long and w_prob_short >= w_prob_no_trade:
            direction = SignalDirection.SHORT
            confidence = w_prob_short
        else:
            direction = SignalDirection.NO_TRADE
            confidence = w_prob_no_trade

        return {
            "direction": direction,
            "probability_long": round(w_prob_long, 4),
            "probability_short": round(w_prob_short, 4),
            "probability_no_trade": round(w_prob_no_trade, 4),
            "confidence": round(confidence, 4),
            "model_agreement": round(agreement, 4),
            "model_count": len(outputs),
            "direction_votes": direction_counts,
        }

    def multi_timeframe_consensus(
        self,
        results: dict[str, dict],  # {timeframe: consensus_result}
        timeframe_weights: Optional[dict[str, float]] = None,
    ) -> dict:
        """
        Combine consensus results across multiple timeframes.

        Higher timeframes get more weight for direction context,
        lower timeframes for entry timing.
        """
        default_tf_weights = {
            "240": 0.35,   # 4H — regime
            "60": 0.30,    # 1H — trend
            "15": 0.25,    # 15M — setup
            "5": 0.10,     # 5M — entry
        }
        tf_weights = timeframe_weights or default_tf_weights

        if not results:
            return self._no_trade_result()

        w_long = 0.0
        w_short = 0.0
        w_no_trade = 0.0
        total_w = 0.0
        alignments: dict[str, str] = {}

        for tf, result in results.items():
            w = tf_weights.get(tf, 0.1)
            w_long += result.get("probability_long", 0.0) * w
            w_short += result.get("probability_short", 0.0) * w
            w_no_trade += result.get("probability_no_trade", 0.0) * w
            total_w += w
            alignments[tf] = result.get("direction", SignalDirection.NO_TRADE)

        if total_w > 0:
            w_long /= total_w
            w_short /= total_w
            w_no_trade /= total_w

        # Check alignment
        directions = list(alignments.values())
        long_aligned = sum(1 for d in directions if d == SignalDirection.LONG)
        short_aligned = sum(1 for d in directions if d == SignalDirection.SHORT)
        alignment_ratio = max(long_aligned, short_aligned) / len(directions) if directions else 0

        # Conflicting timeframes reduce confidence
        if alignment_ratio < 0.6:
            return {
                "direction": SignalDirection.WAIT,
                "probability_long": round(w_long, 4),
                "probability_short": round(w_short, 4),
                "probability_no_trade": round(w_no_trade, 4),
                "confidence": 0.0,
                "mtf_alignment": round(alignment_ratio, 4),
                "alignments": {str(k): str(v) for k, v in alignments.items()},
            }

        if w_long > w_short and w_long > w_no_trade:
            direction = SignalDirection.LONG
            confidence = w_long
        elif w_short > w_long and w_short > w_no_trade:
            direction = SignalDirection.SHORT
            confidence = w_short
        else:
            direction = SignalDirection.NO_TRADE
            confidence = w_no_trade

        return {
            "direction": direction,
            "probability_long": round(w_long, 4),
            "probability_short": round(w_short, 4),
            "probability_no_trade": round(w_no_trade, 4),
            "confidence": round(confidence, 4),
            "mtf_alignment": round(alignment_ratio, 4),
            "alignments": {str(k): str(v) for k, v in alignments.items()},
        }

    @staticmethod
    def _no_trade_result() -> dict:
        return {
            "direction": SignalDirection.NO_TRADE,
            "probability_long": 0.0,
            "probability_short": 0.0,
            "probability_no_trade": 1.0,
            "confidence": 1.0,
            "model_agreement": 0.0,
            "model_count": 0,
        }
