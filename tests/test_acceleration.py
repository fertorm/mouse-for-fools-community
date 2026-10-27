"""Pruebas del perfil de aceleración."""

import importlib

import pytest


@pytest.mark.parametrize(
    ("held_seconds", "expected_speed"),
    [(0.0, 240.0), (0.5, 560.0), (1.5, 1200.0), (4.0, 1200.0)],
)
def test_speed_grows_linearly_until_maximum(held_seconds: float, expected_speed: float) -> None:
    try:
        module = importlib.import_module("mouse_for_fools.acceleration")
    except ModuleNotFoundError:
        pytest.fail("AccelerationProfile todavía no está implementado")
    profile_type = getattr(module, "AccelerationProfile", None)
    assert profile_type is not None
    profile = profile_type(
        initial_speed=240.0,
        acceleration=640.0,
        maximum_speed=1200.0,
    )

    assert profile.speed(held_seconds) == expected_speed
