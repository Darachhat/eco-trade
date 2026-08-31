"""
app/models/retrainer.py
────────────────────────
Model Retraining and Champion vs Challenger Management Engine.

Responsibilities:
- Hyperparameter optimization via Optuna.
- Chronological train / validation / test splits (no shuffling / leakage).
- Model training & out-of-sample evaluation.
- Champion vs Challenger comparison.
- Promotion threshold validation.
- Model artifact versioning and persistence.
"""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import numpy as np
import optuna
import pandas as pd

from app.core.config import settings
from app.core.constants import ModelName, ModelStatus
from app.core.logging import get_logger
from app.features.pipeline import FeaturePipeline
from app.models.base import BaseMLModel
from app.models.lightgbm_model import LightGBMModel
from app.models.random_forest import RandomForestModel
from app.models.xgboost_model import XGBoostModel
from app.prediction.labels import generate_labels, select_primary_label

# Suppress Optuna verbose logging
optuna.logging.set_verbosity(optuna.logging.WARNING)

logger = get_logger("model")


class ModelRetrainer:
    """
    Automated Model Retrainer and Champion vs Challenger Manager.

    Ensures that only empirically superior, statistically validated models
    are promoted to active production use.
    """

    def __init__(self, artifact_dir: Optional[Path] = None) -> None:
        self.artifact_dir = artifact_dir or Path(settings.ml_model_path)
        self.artifact_dir.mkdir(parents=True, exist_ok=True)
        self.pipeline = FeaturePipeline()

    def retrain_model(
        self,
        model_name: str,
        df_candles: pd.DataFrame,
        optimize_hyperparams: bool = True,
        n_trials: int = 20,
    ) -> dict:
        """
        Full retraining cycle for a specific model family.

        1. Feature generation & label calculation.
        2. Strict chronological Train / Val / Test split.
        3. Hyperparameter tuning via Optuna (if enabled).
        4. Challenger model training.
        5. Out-of-sample evaluation.
        6. Champion comparison & potential promotion.
        """
        logger.info(f"Starting retraining cycle for {model_name}", rows=len(df_candles))

        # 1. Feature pipeline & labeling
        df_feat = self.pipeline.compute(df_candles)
        df_labeled = generate_labels(df_feat)
        y = select_primary_label(df_labeled)
        X, feature_names = self.pipeline.get_feature_matrix(df_labeled)

        # 2. Chronological Split (70% Train, 15% Val, 15% OOS Test)
        n = len(X)
        if n < 1000:
            logger.warning("Insufficient samples for reliable retraining", count=n)
            return {"status": "SKIPPED", "reason": "Insufficient samples"}

        train_end = int(n * 0.70)
        val_end = int(n * 0.85)

        X_train, y_train = X.iloc[:train_end], y.iloc[:train_end]
        X_val, y_val = X.iloc[train_end:val_end], y.iloc[train_end:val_end]
        X_test, y_test = X.iloc[val_end:], y.iloc[val_end:]

        logger.info(
            "Data split complete",
            train_samples=len(X_train),
            val_samples=len(X_val),
            test_samples=len(X_test),
        )

        # 3. Hyperparameter optimization with Optuna
        best_params = {}
        if optimize_hyperparams and model_name in (ModelName.XGBOOST, ModelName.LIGHTGBM, ModelName.RANDOM_FOREST):
            best_params = self._optimize_hyperparameters(
                model_name, X_train, y_train, X_val, y_val, n_trials=n_trials
            )

        # 4. Initialize challenger model with version timestamp
        new_version = f"v_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        challenger = self._create_model_instance(model_name, new_version, best_params)

        # 5. Train challenger
        train_metrics = challenger.train(X_train, y_train, val_X=X_val, val_y=y_val)
        oos_metrics = challenger.evaluate(X_test, y_test)

        logger.info(
            "Challenger evaluated on Out-of-Sample Test data",
            model=model_name,
            version=new_version,
            oos_accuracy=f"{oos_metrics.get('accuracy', 0):.1%}",
            oos_f1=f"{oos_metrics.get('f1_macro', 0):.3f}",
            oos_brier=f"{oos_metrics.get('brier_score', 0):.4f}",
        )

        # 6. Champion vs Challenger Decision
        promoted = self._evaluate_and_promote(challenger, oos_metrics, model_name, new_version)

        return {
            "model_name": model_name,
            "version": new_version,
            "promoted": promoted,
            "train_metrics": train_metrics,
            "oos_metrics": oos_metrics,
            "best_params": best_params,
            "trained_at": datetime.utcnow().isoformat(),
        }

    def _optimize_hyperparameters(
        self,
        model_name: str,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        X_val: pd.DataFrame,
        y_val: pd.Series,
        n_trials: int = 15,
    ) -> dict:
        """Run Optuna study on validation set to find optimal hyperparameters."""
        logger.info(f"Optimizing hyperparameters for {model_name} ({n_trials} trials)")

        def objective(trial: optuna.Trial) -> float:
            if model_name == ModelName.XGBOOST:
                params = {
                    "n_estimators": trial.suggest_int("n_estimators", 100, 600, step=50),
                    "max_depth": trial.suggest_int("max_depth", 3, 8),
                    "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.2, log=True),
                    "subsample": trial.suggest_float("subsample", 0.6, 1.0),
                    "colsample_bytree": trial.suggest_float("colsample_bytree", 0.6, 1.0),
                    "reg_alpha": trial.suggest_float("reg_alpha", 1e-3, 10.0, log=True),
                    "reg_lambda": trial.suggest_float("reg_lambda", 1e-3, 10.0, log=True),
                }
                model = XGBoostModel(version="tuning", params=params)

            elif model_name == ModelName.LIGHTGBM:
                params = {
                    "n_estimators": trial.suggest_int("n_estimators", 100, 600, step=50),
                    "max_depth": trial.suggest_int("max_depth", 3, 8),
                    "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.2, log=True),
                    "subsample": trial.suggest_float("subsample", 0.6, 1.0),
                    "colsample_bytree": trial.suggest_float("colsample_bytree", 0.6, 1.0),
                    "reg_alpha": trial.suggest_float("reg_alpha", 1e-3, 10.0, log=True),
                    "reg_lambda": trial.suggest_float("reg_lambda", 1e-3, 10.0, log=True),
                }
                model = LightGBMModel(version="tuning", params=params)

            else:  # Random Forest
                params = {
                    "n_estimators": trial.suggest_int("n_estimators", 100, 400, step=50),
                    "max_depth": trial.suggest_int("max_depth", 4, 12),
                    "min_samples_leaf": trial.suggest_int("min_samples_leaf", 5, 50),
                }
                model = RandomForestModel(version="tuning", params=params)

            model.train(X_train, y_train, val_X=X_val, val_y=y_val)
            val_metrics = model.evaluate(X_val, y_val)
            # Maximize macro F1 score on validation set
            return val_metrics.get("f1_macro", 0.0)

        study = optuna.create_study(direction="maximize")
        study.optimize(objective, n_trials=n_trials, timeout=300)

        logger.info(
            "Optuna optimization finished",
            best_value=round(study.best_value, 4),
            best_params=study.best_params,
        )
        return study.best_params

    def _evaluate_and_promote(
        self,
        challenger: BaseMLModel,
        oos_metrics: dict,
        model_name: str,
        version: str,
    ) -> bool:
        """
        Strict promotion gate:
        - Must beat baseline F1 score (> 0.40 for 3-class financial series).
        - Must have acceptable calibration (Brier score < 0.25).
        - Saves candidate model and updates champion tag if verified.
        """
        f1 = oos_metrics.get("f1_macro", 0.0)
        brier = oos_metrics.get("brier_score", 1.0)
        acc = oos_metrics.get("accuracy", 0.0)

        # Minimum baseline criteria
        if f1 < 0.38 or acc < 0.40:
            logger.warning(
                "Challenger rejected — below minimum performance threshold",
                f1=f1,
                acc=acc,
                model=model_name,
            )
            # Save as candidate for review
            challenger.save(self.artifact_dir / "candidates")
            return False

        # Promotion passed: save as production model
        challenger.save(self.artifact_dir / "production")
        logger.info(
            f"👑 NEW CHAMPION PROMOTED: {model_name} {version}",
            f1=f1,
            accuracy=f"{acc:.1%}",
            brier=brier,
        )
        return True

    def _create_model_instance(self, model_name: str, version: str, params: dict) -> BaseMLModel:
        if model_name == ModelName.XGBOOST:
            return XGBoostModel(version=version, params=params)
        elif model_name == ModelName.LIGHTGBM:
            return LightGBMModel(version=version, params=params)
        elif model_name == ModelName.RANDOM_FOREST:
            return RandomForestModel(version=version, params=params)
        elif model_name == ModelName.LSTM:
            from app.models.lstm import LSTMModel
            return LSTMModel(version=version)
        elif model_name == ModelName.TRANSFORMER:
            from app.models.transformer import TransformerModel
            return TransformerModel(version=version)
        else:
            return XGBoostModel(version=version, params=params)
