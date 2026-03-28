import threading
from typing import Callable, Optional


class LobbyService:
    """
    Gestiona el ciclo de vida del servidor en-proceso.
    Sin imports de pygame, asyncio ni websockets.
    """

    def __init__(self, runner: Callable) -> None:
        self._runner = runner
        self._server_obj = None
        self._server_thread: Optional[threading.Thread] = None

    def start_hosting(self) -> None:
        self.stop_hosting()
        from use_cases.server_session import ServerSession

        self._server_obj = ServerSession()
        srv = self._server_obj
        self._server_thread = threading.Thread(
            target=lambda: self._runner(srv),
            daemon=True,
        )
        self._server_thread.start()

    def stop_hosting(self) -> None:
        if self._server_obj is not None:
            self._server_obj.running = False
        if self._server_thread is not None:
            self._server_thread.join(timeout=2.0)
        self._server_obj = None
        self._server_thread = None

    @property
    def server_obj(self):
        return self._server_obj
