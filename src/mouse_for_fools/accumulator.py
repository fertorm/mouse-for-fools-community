"""Acumulación de valores fraccionales entre ticks."""

from dataclasses import dataclass

_FLOAT_TOLERANCE = 1e-9


@dataclass
class FractionalAccumulator:
    """Emite unidades enteras conservando el residuo fraccional."""

    _remainder: float = 0.0

    def consume(self, amount: float) -> int:
        """Agrega una magnitud y devuelve su parte entera acumulada."""
        total = self._remainder + amount
        nearest_integer = round(total)
        if abs(total - nearest_integer) < _FLOAT_TOLERANCE:
            total = float(nearest_integer)
        emitted = int(total)
        self._remainder = total - emitted
        return emitted

    def reset(self) -> None:
        """Descarta el residuo pendiente."""
        self._remainder = 0.0
