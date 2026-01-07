import numpy as np
from dataclasses import dataclass
from typing import Optional


@dataclass
class LatentState:
    energy: float
    tension: float
    complexity: float
    brightness: float
    density: float

    @classmethod
    def random(cls, seed: Optional[int] = None) -> "LatentState":
        if seed is not None:
            np.random.seed(seed)
        return cls(
            energy=np.random.random(),
            tension=np.random.random(),
            complexity=np.random.random(),
            brightness=np.random.random(),
            density=np.random.random(),
        )

    @classmethod
    def from_params(
        cls,
        energy: float = 0.5,
        tension: float = 0.5,
        complexity: float = 0.5,
        brightness: float = 0.5,
        density: float = 0.5,
    ) -> "LatentState":
        return cls(
            energy=np.clip(energy, 0, 1),
            tension=np.clip(tension, 0, 1),
            complexity=np.clip(complexity, 0, 1),
            brightness=np.clip(brightness, 0, 1),
            density=np.clip(density, 0, 1),
        )

    def evolve(self, drift: float = 0.1, volatility: float = 0.2) -> "LatentState":
        noise = np.random.randn(5) * volatility
        drift_vector = np.random.randn(5) * drift

        values = np.array(
            [self.energy, self.tension, self.complexity, self.brightness, self.density]
        )
        new_values = values + drift_vector + noise
        new_values = np.clip(new_values, 0, 1)

        return LatentState(*new_values)

    def interpolate(self, other: "LatentState", alpha: float) -> "LatentState":
        alpha = np.clip(alpha, 0, 1)
        return LatentState(
            energy=self.energy * (1 - alpha) + other.energy * alpha,
            tension=self.tension * (1 - alpha) + other.tension * alpha,
            complexity=self.complexity * (1 - alpha) + other.complexity * alpha,
            brightness=self.brightness * (1 - alpha) + other.brightness * alpha,
            density=self.density * (1 - alpha) + other.density * alpha,
        )


class LatentStateGenerator:
    def __init__(
        self,
        initial_state: Optional[LatentState] = None,
        drift: float = 0.05,
        volatility: float = 0.15,
    ):
        self.current_state = initial_state or LatentState.random()
        self.drift = drift
        self.volatility = volatility
        self.history = [self.current_state]

    def next_state(self) -> LatentState:
        self.current_state = self.current_state.evolve(self.drift, self.volatility)
        self.history.append(self.current_state)
        return self.current_state

    def generate_sequence(self, length: int) -> list[LatentState]:
        states = []
        for _ in range(length):
            states.append(self.next_state())
        return states

    def reset(self, state: Optional[LatentState] = None):
        self.current_state = state or LatentState.random()
        self.history = [self.current_state]
