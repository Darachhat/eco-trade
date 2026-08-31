"""
app/models/lstm.py
───────────────────
PyTorch LSTM model for sequential candle prediction.
Input: last N candles as feature vectors.
Output: [prob_no_trade, prob_long, prob_short]
"""

from __future__ import annotations

import pickle
from pathlib import Path
from typing import Any, Optional

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from sklearn.preprocessing import StandardScaler
from torch.utils.data import DataLoader, TensorDataset

from app.core.constants import LOOKBACK_SEQUENCE
from app.core.logging import get_logger
from app.models.base import BaseMLModel

logger = get_logger("model")


class _LSTMNet(nn.Module):
    def __init__(self, input_size: int, hidden_size: int = 128, num_layers: int = 2, dropout: float = 0.2) -> None:
        super().__init__()
        self.lstm = nn.LSTM(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0.0,
        )
        self.dropout = nn.Dropout(dropout)
        self.fc = nn.Linear(hidden_size, 3)
        self.softmax = nn.Softmax(dim=1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        out, _ = self.lstm(x)
        out = self.dropout(out[:, -1, :])
        return self.softmax(self.fc(out))


class LSTMModel(BaseMLModel):
    def __init__(
        self,
        version: str = "v1",
        hidden_size: int = 128,
        num_layers: int = 2,
        lookback: int = LOOKBACK_SEQUENCE,
        epochs: int = 50,
        batch_size: int = 64,
        lr: float = 0.001,
    ) -> None:
        super().__init__(model_name="lstm", version=version)
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        self.lookback = lookback
        self.epochs = epochs
        self.batch_size = batch_size
        self.lr = lr
        self._net: Optional[_LSTMNet] = None
        self._scaler: Optional[StandardScaler] = None
        self._device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    def _build_sequences(self, X: np.ndarray, y: Optional[np.ndarray] = None):
        """Build (X_seq, y_seq) from a flat feature array."""
        n = len(X)
        X_seq, y_seq = [], []
        for i in range(self.lookback, n):
            X_seq.append(X[i - self.lookback:i])
            if y is not None:
                y_seq.append(y[i])
        X_seq = np.array(X_seq, dtype=np.float32)
        if y is not None:
            return X_seq, np.array(y_seq, dtype=np.int64)
        return X_seq

    def train(self, X: pd.DataFrame, y: pd.Series, **kwargs: Any) -> dict:
        logger.info("Training LSTM", version=self.version, samples=len(X))
        self._feature_names = list(X.columns)
        self._scaler = StandardScaler()
        X_arr = self._scaler.fit_transform(X.values.astype(np.float32))
        y_arr = y.values

        X_seq, y_seq = self._build_sequences(X_arr, y_arr)
        if len(X_seq) == 0:
            logger.warning("LSTM: not enough samples for sequence building")
            return {}

        input_size = X_seq.shape[2]
        self._net = _LSTMNet(input_size, self.hidden_size, self.num_layers).to(self._device)

        dataset = TensorDataset(
            torch.from_numpy(X_seq),
            torch.from_numpy(y_seq),
        )
        loader = DataLoader(dataset, batch_size=self.batch_size, shuffle=True)
        optimizer = torch.optim.Adam(self._net.parameters(), lr=self.lr)
        criterion = nn.CrossEntropyLoss()

        self._net.train()
        for epoch in range(self.epochs):
            epoch_loss = 0.0
            for batch_X, batch_y in loader:
                batch_X = batch_X.to(self._device)
                batch_y = batch_y.to(self._device)
                optimizer.zero_grad()
                out = self._net(batch_X)
                loss = criterion(out, batch_y)
                loss.backward()
                nn.utils.clip_grad_norm_(self._net.parameters(), 1.0)
                optimizer.step()
                epoch_loss += loss.item()
            if epoch % 10 == 0:
                logger.debug("LSTM epoch", epoch=epoch, loss=epoch_loss / len(loader))

        self._is_trained = True
        return {}

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        if self._net is None:
            raise RuntimeError("Model not trained")
        X_arr = X.values.astype(np.float32)
        if self._scaler:
            X_arr = self._scaler.transform(X_arr)

        if len(X_arr) < self.lookback:
            # Not enough history — return equal probabilities
            return np.array([[1/3, 1/3, 1/3]])

        seq = X_arr[-self.lookback:]
        tensor = torch.from_numpy(seq).unsqueeze(0).to(self._device)
        self._net.eval()
        with torch.no_grad():
            proba = self._net(tensor).cpu().numpy()
        return proba

    def save(self, path: Path) -> None:
        path.mkdir(parents=True, exist_ok=True)
        torch.save(self._net.state_dict() if self._net else {}, path / f"lstm_{self.version}.pt")
        with open(path / f"lstm_{self.version}_meta.pkl", "wb") as f:
            pickle.dump({
                "scaler": self._scaler,
                "features": self._feature_names,
                "hidden_size": self.hidden_size,
                "num_layers": self.num_layers,
                "lookback": self.lookback,
            }, f)

    def load(self, path: Path) -> None:
        meta_path = path / f"lstm_{self.version}_meta.pkl"
        if not meta_path.exists():
            raise FileNotFoundError(f"LSTM meta not found: {meta_path}")
        with open(meta_path, "rb") as f:
            meta = pickle.load(f)
        self._scaler = meta["scaler"]
        self._feature_names = meta["features"]
        self.hidden_size = meta["hidden_size"]
        self.num_layers = meta["num_layers"]
        self.lookback = meta["lookback"]
        self._net = _LSTMNet(len(self._feature_names), self.hidden_size, self.num_layers).to(self._device)
        state_path = path / f"lstm_{self.version}.pt"
        if state_path.exists():
            self._net.load_state_dict(torch.load(state_path, map_location=self._device))
        self._is_trained = True
