"""Training script for RansomScope LSTM model.

Expects CSV: label, f1, f2, ... (0=benign, 1=ransomware).
Uses class weights for imbalance, validation split, more epochs.
"""

from __future__ import annotations

import argparse
import csv
import logging
from pathlib import Path
from typing import List, Tuple

import torch
from torch import nn
from torch.utils.data import DataLoader, Dataset, random_split

import config
from processing.model import RansomScopeLSTM, build_loss_and_optimizer, ModelManager

logger = logging.getLogger(__name__)


class WindowSequenceDataset(Dataset):
    """Dataset wrapping pre-computed window sequences (already scaled by feature engine)."""

    def __init__(self, rows: List[Tuple[float, list[float]]]) -> None:
        self._rows = rows

    def __len__(self) -> int:
        return len(self._rows)

    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, torch.Tensor]:
        label, features = self._rows[idx]
        seq_len = config.SEQUENCE_LENGTH
        feat_dim = config.FEATURE_DIM
        if len(features) != seq_len * feat_dim:
            raise ValueError(f"Expected {seq_len * feat_dim} features, got {len(features)}")
        x = torch.tensor(features, dtype=torch.float32).view(seq_len, feat_dim)
        y = torch.tensor([label], dtype=torch.float32)
        return x, y


def load_csv(path: Path) -> List[Tuple[float, list[float]]]:
    rows: List[Tuple[float, list[float]]] = []
    with path.open("r", newline="") as f:
        reader = csv.reader(f)
        header = next(reader, None)
        for row in reader:
            if not row:
                continue
            label = float(row[0])
            features = [float(v) for v in row[1:]]
            rows.append((label, features))
    return rows


def train(args: argparse.Namespace) -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    data_path = Path(args.data)
    if not data_path.exists():
        raise SystemExit(f"Data file not found: {data_path}")

    rows = load_csv(data_path)
    full_dataset = WindowSequenceDataset(rows)

    # Train/val split
    val_size = max(1, int(len(full_dataset) * args.val_ratio))
    train_size = len(full_dataset) - val_size
    train_dataset, val_dataset = random_split(
        full_dataset, [train_size, val_size],
        generator=torch.Generator().manual_seed(42),
    )

    train_loader = DataLoader(train_dataset, batch_size=args.batch_size, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=args.batch_size)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = RansomScopeLSTM().to(device)

    criterion = nn.BCEWithLogitsLoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=args.lr)

    # Class weights for imbalance (more benign than ransomware typically)
    pos_count = sum(1 for l, _ in rows if l >= 0.5)
    neg_count = len(rows) - pos_count
    pos_weight = torch.tensor([neg_count / max(1, pos_count)], dtype=torch.float32, device=device)
    criterion_weighted = nn.BCEWithLogitsLoss(pos_weight=pos_weight)

    best_val_loss = float("inf")
    for epoch in range(args.epochs):
        model.train()
        train_loss = 0.0
        for x, y in train_loader:
            x, y = x.to(device), y.to(device)
            optimizer.zero_grad()
            logits = model(x)
            loss = criterion_weighted(logits.view(-1), y.view(-1))
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            train_loss += loss.item() * x.size(0)

        model.eval()
        val_loss = 0.0
        correct = 0
        total = 0
        with torch.no_grad():
            for x, y in val_loader:
                x, y = x.to(device), y.to(device)
                logits = model(x)
                loss = criterion(logits.view(-1), y.view(-1))
                val_loss += loss.item() * x.size(0)
                pred = (torch.sigmoid(logits) >= 0.5).float().view(-1)
                correct += (pred == y.view(-1)).sum().item()
                total += y.size(0)

        avg_train = train_loss / len(train_dataset)
        avg_val = val_loss / len(val_dataset)
        acc = correct / total if total > 0 else 0.0
        logger.info(
            "Epoch %d/%d train_loss=%.4f val_loss=%.4f val_acc=%.2f",
            epoch + 1, args.epochs, avg_train, avg_val, acc,
        )

        if avg_val < best_val_loss:
            best_val_loss = avg_val
            manager = ModelManager(args.model_path, auto_load=False)
            manager.model.load_state_dict(model.state_dict())
            manager.save()

    logger.info("Training complete. Best model saved to %s", args.model_path)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train RansomScope LSTM model")
    parser.add_argument("--data", type=str, required=True, help="Path to CSV training data")
    parser.add_argument("--epochs", type=int, default=15, help="Number of epochs")
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--val-ratio", type=float, default=0.2, help="Validation split ratio")
    parser.add_argument("--model-path", type=str, default="ransomescope_lstm.pt")
    return parser.parse_args()


if __name__ == "__main__":
    train(parse_args())
