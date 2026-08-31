"""
app/models/transformer.py
──────────────────────────
PyTorch Transformer with temporal attention for crypto market prediction.
"""

from __future__ import annotations

import math
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


class _PositionalEncoding(nn.Module):
    def __init__(self, d_model: int, max_len: int = 200, dropout: float = 0.1) -> None:
        super().__init__()
        self.dropout = nn.Dropout(dropout)
        pe = torch.zeros(max_len, d_model)
        position = torch.arange(0, max_len, dtype=torch.float).unsqueeze(1)
        div_term = torch.exp(torch.arange(0, d_model, 2).float() * (-math.log(10000.0) / d_model))
        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term)
        pe = pe.unsqueeze(0)
        self.register_buffer("pe", pe)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = x + self.pe[:, :x.size(1), :]
        return self.dropout(x)


class _TransformerNet(nn.Module):
    def __init__(self, input_size: int, d_model: int = 64, nhead: int = 4,
                 num_layers: int = 2, dropout: float = 0.1) -> None:
        super().__init__()
        self.input_proj = nn.Linear(input_size, d_model)
        self.pos_enc = _PositionalEncoding(d_model, dropout=dropout)
        encoder_layer = nn.TransformerEncoderLayer(d_model=d_model, nhead=nhead,
                                                    dim_feedforward=d_model * 4,
                                                    dropout=dropout, batch_first=True)
        self.encoder = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)
        self.fc = nn.Linear(d_model, 3)
        self.softmax = nn.Softmax(dim=1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.input_proj(x)
        x = self.pos_enc(x)
        x = self.encoder(x)
        x = x[:, -1, :]  # Last token
        return self.softmax(self.fc(x))


class TransformerModel(BaseMLModel):
    def __init__(self, version: str = "v1", d_model: int = 64, nhead: int = 4,
                 num_layers: int = 2, lookback: int = LOOKBACK_SEQUENCE,
                 epochs: int = 50, batch_size: int = 64, lr: float = 0.0005) -> None:
        super().__init__(model_name="transformer", version=version)
        self.d_model = d_model
        self.nhead = nhead
        self.num_layers = num_layers
        self.lookback = lookback
        self.epochs = epochs
        self.batch_size = batch_size
        self.lr = lr
        self._net: Optional[_TransformerNet] = None
        self._scaler: Optional[StandardScaler] = None
        self._device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    def _build_sequences(self, X: np.ndarray, y: Optional[np.ndarray] = None):
        X_seq, y_seq = [], []
        for i in range(self.lookback, len(X)):
            X_seq.append(X[i - self.lookback:i])
            if y is not None:
                y_seq.append(y[i])
        X_seq = np.array(X_seq, dtype=np.float32)
        if y is not None:
            return X_seq, np.array(y_seq, dtype=np.int64)
        return X_seq

    def train(self, X: pd.DataFrame, y: pd.Series, **kwargs: Any) -> dict:
        logger.info("Training Transformer", version=self.version, samples=len(X))
        self._feature_names = list(X.columns)
        self._scaler = StandardScaler()
        X_arr = self._scaler.fit_transform(X.values.astype(np.float32))
        X_seq, y_seq = self._build_sequences(X_arr, y.values)
        if len(X_seq) == 0:
            return {}

        # d_model must be divisible by nhead
        input_size = X_seq.shape[2]
        self._net = _TransformerNet(input_size, self.d_model, self.nhead, self.num_layers).to(self._device)

        loader = DataLoader(TensorDataset(torch.from_numpy(X_seq), torch.from_numpy(y_seq)),
                            batch_size=self.batch_size, shuffle=True)
        optimizer = torch.optim.Adam(self._net.parameters(), lr=self.lr)
        scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=self.epochs)
        criterion = nn.CrossEntropyLoss()

        self._net.train()
        for epoch in range(self.epochs):
            for bx, by in loader:
                optimizer.zero_grad()
                loss = criterion(self._net(bx.to(self._device)), by.to(self._device))
                loss.backward()
                nn.utils.clip_grad_norm_(self._net.parameters(), 1.0)
                optimizer.step()
            scheduler.step()

        self._is_trained = True
        return {}

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        if self._net is None:
            raise RuntimeError("Transformer not trained")
        X_arr = X.values.astype(np.float32)
        if self._scaler:
            X_arr = self._scaler.transform(X_arr)
        if len(X_arr) < self.lookback:
            return np.array([[1/3, 1/3, 1/3]])
        tensor = torch.from_numpy(X_arr[-self.lookback:]).unsqueeze(0).to(self._device)
        self._net.eval()
        with torch.no_grad():
            return self._net(tensor).cpu().numpy()

    def save(self, path: Path) -> None:
        path.mkdir(parents=True, exist_ok=True)
        torch.save(self._net.state_dict() if self._net else {}, path / f"transformer_{self.version}.pt")
        with open(path / f"transformer_{self.version}_meta.pkl", "wb") as f:
            pickle.dump({"scaler": self._scaler, "features": self._feature_names,
                         "d_model": self.d_model, "nhead": self.nhead, "num_layers": self.num_layers,
                         "lookback": self.lookback}, f)

    def load(self, path: Path) -> None:
        with open(path / f"transformer_{self.version}_meta.pkl", "rb") as f:
            meta = pickle.load(f)
        self._scaler = meta["scaler"]
        self._feature_names = meta["features"]
        self._net = _TransformerNet(len(self._feature_names), meta["d_model"],
                                     meta["nhead"], meta["num_layers"]).to(self._device)
        state_path = path / f"transformer_{self.version}.pt"
        if state_path.exists():
            self._net.load_state_dict(torch.load(state_path, map_location=self._device))
        self._is_trained = True
