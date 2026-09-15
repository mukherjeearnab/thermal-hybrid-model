"""PyTorch residual-correction model.

``ResidualMLP`` predicts the residual error of the baseline Modelica
simulation:

    predicted_residual = ResidualMLP(temperature_sim, power, ambient)
    temperature_hybrid  = temperature_sim + predicted_residual
"""

from __future__ import annotations

from typing import Sequence

import torch
from torch import nn


_ACTIVATIONS = {
    "tanh": nn.Tanh,
    "relu": nn.ReLU,
    "gelu": nn.GELU,
}


class ResidualMLP(nn.Module):
    """Small multilayer perceptron predicting a scalar residual.

    Default architecture (matching the project configuration):
        Linear(3, 32) -> Tanh -> Linear(32, 32) -> Tanh -> Linear(32, 1)
    """

    def __init__(
        self,
        input_size: int = 3,
        hidden_sizes: Sequence[int] = (32, 32),
        output_size: int = 1,
        activation: str = "tanh",
    ) -> None:
        super().__init__()
        if activation not in _ACTIVATIONS:
            raise ValueError(
                f"Unsupported activation '{activation}'. "
                f"Available: {list(_ACTIVATIONS)}"
            )
        act_cls = _ACTIVATIONS[activation]

        layers: list[nn.Module] = []
        in_features = input_size
        for hidden in hidden_sizes:
            layers.append(nn.Linear(in_features, hidden))
            layers.append(act_cls())
            in_features = hidden
        layers.append(nn.Linear(in_features, output_size))

        self.net = nn.Sequential(*layers)
        self.input_size = input_size
        self.output_size = output_size

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Predict residuals for a batch of feature vectors.

        Args:
            x: Tensor of shape ``(batch_size, input_size)``.

        Returns:
            Tensor of shape ``(batch_size, output_size)``.
        """
        return self.net(x)
