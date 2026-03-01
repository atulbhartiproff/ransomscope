"""Sequence-based LSTM classifier for ransomware risk scoring."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Iterable, Tuple

import torch
from torch import nn

import config

logger = logging.getLogger(__name__)


class RansomScopeLSTM(nn.Module):
    """LSTM-based binary classifier with 2 layers and dropout."""

    def __init__(
        self,
        feature_dim: int = config.FEATURE_DIM,
        hidden_size: int = config.LSTM_HIDDEN_SIZE,
        num_layers: int = config.LSTM_NUM_LAYERS,
        dropout: float = config.LSTM_DROPOUT,
    ) -> None:
        super().__init__()
        self.lstm = nn.LSTM(
            input_size=feature_dim,
            hidden_size=hidden_size,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0.0,
        )
        self.fc = nn.Linear(hidden_size, 1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Forward pass.

        Args:
            x: Tensor of shape (batch_size, seq_len, feature_dim)

        Returns:
            Logits tensor of shape (batch_size, 1)
        """
        lstm_out, _ = self.lstm(x)
        last_hidden = lstm_out[:, -1, :]
        logits = self.fc(last_hidden)
        return logits


class ModelManager:
    """Utility for loading, saving, and running inference with the model."""

    def __init__(
        self,
        model_path: Path | str = Path("ransomescope_lstm.pt"),
        auto_load: bool = True,
    ) -> None:
        self.model_path = Path(model_path)
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model = RansomScopeLSTM().to(self.device)
        self.model.eval()
        if auto_load and self.model_path.exists():
            self.load()
        elif auto_load:
            logger.warning("Model file not found at %s; using untrained weights.", self.model_path)

    def load(self) -> None:
        state = torch.load(self.model_path, map_location=self.device)
        self.model.load_state_dict(state)
        self.model.to(self.device)
        self.model.eval()
        logger.info("Loaded model from %s", self.model_path)

    def save(self) -> None:
        self.model.cpu()
        torch.save(self.model.state_dict(), self.model_path)
        self.model.to(self.device)
        logger.info("Saved model to %s", self.model_path)

    @torch.no_grad()
    def predict_sequence(self, sequence: Iterable[Iterable[float]]) -> float:
        """Run inference on a single sequence of feature vectors.

        Args:
            sequence: Iterable of vectors of length feature_dim.

        Returns:
            risk_score in [0, 1].
        """
        seq_list = [list(v) for v in sequence]
        if not seq_list:
            raise ValueError("Empty sequence passed to predict_sequence")

        x = torch.tensor(seq_list, dtype=torch.float32, device=self.device).unsqueeze(0)
        logits = self.model(x)
        risk_score = torch.sigmoid(logits).item()
        return float(risk_score)


def build_loss_and_optimizer(
    model: nn.Module,
    lr: float = 1e-3,
) -> Tuple[nn.Module, torch.optim.Optimizer]:
    """Return BCEWithLogits loss and Adam optimizer."""
    criterion = nn.BCEWithLogitsLoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)
    return criterion, optimizer
