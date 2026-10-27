"""Cálculo puro de desplazamiento del cursor."""

from math import hypot

from mouse_for_fools.state import Direction

_HORIZONTAL = {"left": -1.0, "right": 1.0}
_VERTICAL = {"up": -1.0, "down": 1.0}


def movement_delta(directions: frozenset[Direction], step: float) -> tuple[float, float]:
    """Calcula un vector normalizado para las direcciones retenidas."""
    horizontal = sum(_HORIZONTAL.get(direction, 0.0) for direction in directions)
    vertical = sum(_VERTICAL.get(direction, 0.0) for direction in directions)
    magnitude = hypot(horizontal, vertical)
    if magnitude == 0:
        return 0.0, 0.0
    return horizontal * step / magnitude, vertical * step / magnitude
