"""
Feedforward Neural Network for ZTA authentication decisions.
Used for LIME comparison as a non-tree-based model.
"""

import logging
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset

logger = logging.getLogger(__name__)


class AuthNet(nn.Module):
    """Feedforward neural network for authentication decisions."""

    def __init__(self, input_dim: int, hidden_layers: list = None, dropout: float = 0.3):
        super().__init__()

        if hidden_layers is None:
            hidden_layers = [128, 64, 32]

        layers = []
        prev_dim = input_dim
        for h_dim in hidden_layers:
            layers.extend([
                nn.Linear(prev_dim, h_dim),
                nn.BatchNorm1d(h_dim),
                nn.ReLU(),
                nn.Dropout(dropout),
            ])
            prev_dim = h_dim

        layers.append(nn.Linear(prev_dim, 1))
        self.network = nn.Sequential(*layers)

    def forward(self, x):
        return self.network(x)


class NeuralNetClassifier:
    """Sklearn-compatible wrapper for the AuthNet neural network."""

    def __init__(self, input_dim: int = None, hidden_layers: list = None,
                 dropout: float = 0.3, lr: float = 0.001, epochs: int = 50,
                 batch_size: int = 256, patience: int = 10, random_state: int = 42,
                 verbose: bool = False):
        self.input_dim = input_dim
        self.hidden_layers = hidden_layers or [128, 64, 32]
        self.dropout = dropout
        self.lr = lr
        self.epochs = epochs
        self.batch_size = batch_size
        self.patience = patience
        self.random_state = random_state
        self.verbose = verbose
        self.model = None
        self.device = torch.device('cpu')  # ✅ Force CPU — avoids MPS/BatchNorm1d hang on Apple Silicon
        self.classes_ = np.array([0, 1])
        self.training_history = []

    def fit(self, X, y):
        torch.manual_seed(self.random_state)

        if self.input_dim is None:
            self.input_dim = X.shape[1]

        self.model = AuthNet(self.input_dim, self.hidden_layers, self.dropout).to(self.device)

        X_tensor = torch.FloatTensor(np.array(X)).to(self.device)
        y_tensor = torch.FloatTensor(np.array(y)).reshape(-1, 1).to(self.device)

        dataset = TensorDataset(X_tensor, y_tensor)
        loader = DataLoader(
            dataset,
            batch_size=self.batch_size,
            shuffle=True,
            drop_last=True,
            num_workers=0,  # ✅ Prevents multiprocessing hang on macOS
        )

        optimizer = torch.optim.Adam(self.model.parameters(), lr=self.lr, weight_decay=0.0001)
        criterion = nn.BCEWithLogitsLoss()

        best_loss = float('inf')
        patience_counter = 0

        for epoch in range(self.epochs):
            self.model.train()
            epoch_loss = 0.0

            for batch_X, batch_y in loader:
                optimizer.zero_grad()
                predictions = self.model(batch_X)
                loss = criterion(predictions, batch_y)
                loss.backward()
                optimizer.step()
                epoch_loss += loss.item()

            avg_loss = epoch_loss / len(loader)
            self.training_history.append(avg_loss)

            if avg_loss < best_loss:
                best_loss = avg_loss
                patience_counter = 0
            else:
                patience_counter += 1
                if patience_counter >= self.patience:
                    if self.verbose:
                        logger.info(f"Early stopping at epoch {epoch + 1}")
                    break

            # Always log every 5 epochs so you can see progress
            if (epoch + 1) % 5 == 0:
                logger.info(f"Epoch {epoch + 1}/{self.epochs}, Loss: {avg_loss:.4f}")

        return self

    def predict(self, X) -> np.ndarray:
        proba = self.predict_proba(X)
        return (proba[:, 1] >= 0.5).astype(int)

    def predict_proba(self, X) -> np.ndarray:
        self.model.eval()
        with torch.no_grad():
            X_tensor = torch.FloatTensor(np.array(X)).to(self.device)
            logits = self.model(X_tensor).cpu().numpy().flatten()
            proba_positive = 1.0 / (1.0 + np.exp(-logits))

        return np.column_stack([1 - proba_positive, proba_positive])
