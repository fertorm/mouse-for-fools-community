"""Pruebas para la acumulación de movimiento fraccional."""

import importlib

import pytest


def accumulator_type() -> type:
    try:
        module = importlib.import_module("mouse_for_fools.accumulator")
    except ModuleNotFoundError:
        pytest.fail("FractionalAccumulator todavía no está implementado")
    result = getattr(module, "FractionalAccumulator", None)
    assert result is not None
    return result


def test_positive_fractions_eventually_emit_integer_unit() -> None:
    accumulator = accumulator_type()()
    emitted = [accumulator.consume(0.4) for _ in range(3)]
    assert emitted == [0, 0, 1]


def test_negative_fractions_are_symmetric() -> None:
    accumulator = accumulator_type()()
    emitted = [accumulator.consume(-0.4) for _ in range(3)]
    assert emitted == [0, 0, -1]


def test_reset_discards_pending_fraction() -> None:
    accumulator = accumulator_type()()
    accumulator.consume(0.8)
    accumulator.reset()
    assert accumulator.consume(0.3) == 0


def test_decimal_tenths_do_not_lose_integer_to_float_error() -> None:
    accumulator = accumulator_type()()
    emitted = [accumulator.consume(0.1) for _ in range(10)]
    assert emitted == [0, 0, 0, 0, 0, 0, 0, 0, 0, 1]
