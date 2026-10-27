"""Perfil puro de aceleración del cursor."""

from dataclasses import dataclass


@dataclass(frozen=True)
class AccelerationProfile:
    """Calcula velocidad lineal limitada por un máximo."""

    initial_speed: float
    acceleration: float
    maximum_speed: float

    def speed(self, held_seconds: float) -> float:
        """Devuelve píxeles por segundo para el tiempo retenido."""
        accelerated_speed = self.initial_speed + self.acceleration * held_seconds
        return min(accelerated_speed, self.maximum_speed)
