"""Valores visuales compartidos del diseño aprobado."""

BACKGROUND = "#F7F7F5"
TEXT = "#202428"
SECONDARY = "#525B60"
ACCENT = "#006873"
WHITE = "#FFFFFF"
FOCUS = "#005FCC"
DIVIDER = "#D5D9D7"
FONT = "Segoe UI"
BODY_SIZE = 16
SPACE = 8
MARGIN = 24
RADIUS = 6
WINDOW_WIDTH = 620
WINDOW_HEIGHT = 660
STACK_WIDTH = 540
MIN_WIDTH = 340
MIN_HEIGHT = 400
KEY_SIZE = 58


def stylesheet() -> str:
    """Devuelve estilos de widgets, incluidos foco y estados deshabilitados."""
    return f"""
        QWidget {{ background: {BACKGROUND}; color: {TEXT};
            font-family: "{FONT}"; font-size: {BODY_SIZE}px; }}
        QLabel {{ background: transparent; }}
        QLabel#status {{ font-size: 24px; font-weight: 600; }}
        QLabel#heading {{ font-size: 21px; font-weight: 600; }}
        QLabel#secondary {{ color: {SECONDARY}; }}
        QLabel#key {{ color: {ACCENT}; background: {WHITE};
            border: 1px solid {SECONDARY}; border-radius: {RADIUS}px;
            font-size: 26px; font-weight: 600; padding: {SPACE}px; }}
        QLabel#shortcut {{ color: {ACCENT}; font-weight: 600; }}
        QPushButton {{ border: 2px solid {SECONDARY}; border-radius: {RADIUS}px;
            padding: {SPACE}px; min-height: 28px; color: {ACCENT}; }}
        QPushButton#primary {{ background: {ACCENT}; color: {WHITE};
            border: 2px solid {ACCENT}; font-size: 21px; font-weight: 600;
            padding: 12px; }}
        QPushButton:focus {{ border: 2px solid {FOCUS}; }}
        QPushButton#primary:focus {{ border: 2px solid {TEXT}; }}
        QPushButton:disabled {{ background: {DIVIDER}; color: {SECONDARY};
            border-color: {SECONDARY}; }}
        QScrollArea {{ border: none; }}
        QMenu {{ background: {BACKGROUND}; }}
        QMenu::item:selected {{ background: {ACCENT}; color: {WHITE}; }}
    """
