"""Reserva un único servicio por sesión Windows mediante un mutex nombrado."""

import ctypes
from ctypes import wintypes

MUTEX_NAME = r"Local\Nexum.MouseForFools.Service"
ERROR_ALREADY_EXISTS = 183


class SessionLease:
    """Conserva un handle de exclusión hasta que termina el servicio."""

    def __init__(self, name: str = MUTEX_NAME) -> None:
        self._name = name
        self._handle: int | None = None
        self._kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        self._kernel.CreateMutexW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR]
        self._kernel.CreateMutexW.restype = wintypes.HANDLE
        self._kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        self._kernel.CloseHandle.restype = wintypes.BOOL

    def acquire(self) -> bool:
        """Devuelve False si otra instancia ya conserva la reserva."""
        if self._handle is not None:
            return True
        handle = self._kernel.CreateMutexW(None, False, self._name)
        error = ctypes.get_last_error()
        if not handle:
            raise OSError("No se pudo reservar la instancia")
        if error == ERROR_ALREADY_EXISTS:
            self._kernel.CloseHandle(handle)
            return False
        self._handle = handle
        return True

    def release(self) -> None:
        """Libera la reserva; permite repetir la operación."""
        if self._handle is not None:
            if not self._kernel.CloseHandle(self._handle):
                raise OSError("No se pudo liberar la reserva")
            self._handle = None
