"""Estado de interacción independiente del backend de Windows."""

from dataclasses import dataclass, field
from typing import Literal

Direction = Literal["up", "down", "left", "right"]
ScrollDirection = Literal["up", "down"]


@dataclass
class MouseModeState:
    """Representa si Mouse Mode está activo."""

    active: bool = False
    _directions: set[Direction] = field(default_factory=set, init=False, repr=False)
    _scroll_directions: set[ScrollDirection] = field(
        default_factory=set, init=False, repr=False
    )
    _drag_active: bool = field(default=False, init=False, repr=False)

    @property
    def directions(self) -> frozenset[Direction]:
        """Devuelve una instantánea de las direcciones retenidas."""
        return frozenset(self._directions)

    @property
    def scroll_directions(self) -> frozenset[ScrollDirection]:
        """Devuelve una instantánea de las direcciones de scroll retenidas."""
        return frozenset(self._scroll_directions)

    @property
    def drag_active(self) -> bool:
        """Indica si existe un arrastre activo."""
        return self._drag_active

    def enable(self) -> None:
        """Activa Mouse Mode."""
        self.active = True

    def disable(self) -> None:
        """Desactiva Mouse Mode y elimina interacciones residuales."""
        self.active = False
        self._directions.clear()
        self._scroll_directions.clear()
        self._drag_active = False

    def hold_direction(self, direction: Direction) -> None:
        """Registra una dirección mientras el modo está activo."""
        if self.active:
            self._directions.add(direction)

    def release_direction(self, direction: Direction) -> None:
        """Elimina una dirección sin afectar las demás."""
        self._directions.discard(direction)

    def hold_scroll(self, direction: ScrollDirection) -> None:
        """Registra una dirección de scroll mientras el modo está activo."""
        if self.active:
            self._scroll_directions.add(direction)

    def release_scroll(self, direction: ScrollDirection) -> None:
        """Elimina una dirección de scroll retenida."""
        self._scroll_directions.discard(direction)

    def start_drag(self) -> None:
        """Inicia el arrastre mientras el modo está activo."""
        if self.active:
            self._drag_active = True

    def stop_drag(self) -> None:
        """Detiene el arrastre activo."""
        self._drag_active = False
