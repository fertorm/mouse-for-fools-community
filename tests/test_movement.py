"""Pruebas del cálculo de movimiento del cursor."""

import pytest

from mouse_for_fools.movement import movement_delta


def test_diagonal_movement_has_same_magnitude_as_straight_movement() -> None:
    """Dos direcciones no deben aumentar artificialmente la velocidad."""
    straight_x, straight_y = movement_delta(frozenset({"right"}), 12.0)
    diagonal_x, diagonal_y = movement_delta(frozenset({"up", "right"}), 12.0)

    straight_magnitude = (straight_x**2 + straight_y**2) ** 0.5
    diagonal_magnitude = (diagonal_x**2 + diagonal_y**2) ** 0.5
    assert diagonal_magnitude == pytest.approx(straight_magnitude)
