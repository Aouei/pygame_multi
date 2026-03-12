import pygame
import pygame_gui
import os
import sys
from typing import Optional
import asyncio
import json
import subprocess
import threading

import paths
import websockets

from pygame.time import Clock
from enums import ROLE, MESSAGES
from inputs import InputHandler

pygame.font.init()


class _EntryWrapper:
    """Exposes .value so client.py can do LOBBY.host.value / LOBBY.port.value."""

    def __init__(self, entry: pygame_gui.elements.UITextEntryLine):
        self._entry = entry

    @property
    def value(self) -> str:
        return self._entry.get_text()


class Screen:
    FRAME_RATE = 60
    ROLE_TEXT_FONT = pygame.font.Font(None, 64)

    def __init__(self, window: pygame.Surface, inputs: InputHandler, clock: Clock):
        self.inputs = inputs
        self.classes: list[tuple[ROLE, pygame.Surface]] = [
            (
                ROLE.ARCHER,
                pygame.image.load(os.path.join(paths.PLAYER_DIR, r"archer\idle.png")),
            ),
            (
                ROLE.MAGE,
                pygame.image.load(os.path.join(paths.PLAYER_DIR, r"mage\idle.png")),
            ),
            (
                ROLE.FARMER,
                pygame.image.load(os.path.join(paths.PLAYER_DIR, r"farmer\idle.png")),
            ),
            (
                ROLE.MUSKETEER,
                pygame.image.load(
                    os.path.join(paths.PLAYER_DIR, r"musketeer\idle.png")
                ),
            ),
        ]

        self.current_class: int = 0
        self.size = 20 * self.classes[0][-1].get_rect().width
        self.selection: ROLE | None = None
        self.clock = clock
        self.window = window

        self._connected = False
        self._player_count = 0
        self._server_proc: subprocess.Popen | None = None
        self._ws_thread: threading.Thread | None = None
        self._ws_loop_ref: asyncio.AbstractEventLoop | None = None
        self._ws_ref = None

        self.manager = pygame_gui.UIManager(window.get_size())
        self._build_ui()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self):
        W, H = self.window.get_size()

        # Panel size: responsive fraction of screen, clamped
        panel_w = max(300, min(420, int(W * 0.28)))
        panel_h = 285

        # Center the panel on screen
        panel_rect = pygame.Rect(0, 0, panel_w, panel_h)
        panel_rect.center = (W // 2, H // 2)

        self._panel = pygame_gui.elements.UIPanel(
            relative_rect=panel_rect,
            manager=self.manager,
        )

        M = 15                      # inner margin
        ew = panel_w - 2 * M        # usable element width inside panel
        btn_w = (ew - 20) // 3      # 3 buttons with 10px gaps between them

        pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(M, 8, ew, 24),
            text="IP",
            manager=self.manager,
            container=self._panel,
        )
        self._ip_entry = pygame_gui.elements.UITextEntryLine(
            relative_rect=pygame.Rect(M, 35, ew, 36),
            manager=self.manager,
            container=self._panel,
            initial_text="25.33.144.47",
        )
        self._ip_entry.set_allowed_characters(list("0123456789."))

        pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(M, 80, ew, 24),
            text="Port",
            manager=self.manager,
            container=self._panel,
        )
        self._port_entry = pygame_gui.elements.UITextEntryLine(
            relative_rect=pygame.Rect(M, 107, ew, 36),
            manager=self.manager,
            container=self._panel,
            initial_text="25565",
        )
        self._port_entry.set_allowed_characters(list("0123456789"))

        # Three buttons in one row
        self._btn_host = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(M, 158, btn_w, 38),
            text="Host",
            manager=self.manager,
            container=self._panel,
        )
        # Connect and Disconnect share the same slot; only one visible at a time
        self._btn_connect = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(M + btn_w + 10, 158, btn_w, 38),
            text="Connect",
            manager=self.manager,
            container=self._panel,
        )
        self._btn_disconnect = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(M + btn_w + 10, 158, btn_w, 38),
            text="Disconnect",
            manager=self.manager,
            container=self._panel,
        )
        self._btn_disconnect.hide()

        self._btn_play = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(M + 2 * (btn_w + 10), 158, btn_w, 38),
            text="Play",
            manager=self.manager,
            container=self._panel,
        )
        self._btn_play.disable()

        # Status row
        status_w = ew * 2 // 3
        self._lbl_status = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(M, 212, status_w, 28),
            text="Disconnected",
            manager=self.manager,
            container=self._panel,
        )
        self._lbl_players = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(M + status_w + 5, 212, ew - status_w - 5, 28),
            text="0/4",
            manager=self.manager,
            container=self._panel,
        )

        # Wrappers so client.py can read .host.value / .port.value
        self.host = _EntryWrapper(self._ip_entry)
        self.port = _EntryWrapper(self._port_entry)

    # ------------------------------------------------------------------
    # Server subprocess
    # ------------------------------------------------------------------

    def _launch_server(self):
        if self._server_proc and self._server_proc.poll() is None:
            self._server_proc.terminate()
        if getattr(sys, "frozen", False):
            server_exe = os.path.join(os.path.dirname(sys.executable), "server.exe")
            self._server_proc = subprocess.Popen(
                [server_exe],
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
        else:
            server_path = os.path.normpath(
                os.path.join(os.path.dirname(__file__), "..", "server.py")
            )
            self._server_proc = subprocess.Popen([sys.executable, server_path])

    # ------------------------------------------------------------------
    # WebSocket connection (daemon thread)
    # ------------------------------------------------------------------

    def _connect_ws(self):
        if self._ws_thread and self._ws_thread.is_alive():
            return
        self._ws_thread = threading.Thread(target=self._ws_worker, daemon=True)
        self._ws_thread.start()

    def _ws_worker(self):
        loop = asyncio.new_event_loop()
        self._ws_loop_ref = loop
        try:
            loop.run_until_complete(self._ws_coro())
        finally:
            loop.close()
            self._ws_loop_ref = None
            self._connected = False

    async def _ws_coro(self):
        try:
            async with websockets.connect(
                f"ws://{self.host.value}:{self.port.value}"
            ) as ws:
                self._ws_ref = ws
                self._connected = True
                async for raw in ws:
                    data = json.loads(raw)
                    if data.get("type") == MESSAGES.PLAYERS_UPDATE.value:
                        self._player_count = data.get("clients", 0)
        except Exception:
            pass
        finally:
            self._ws_ref = None
            self._connected = False

    def _disconnect_ws(self):
        ws = self._ws_ref
        loop = self._ws_loop_ref
        if ws is not None and loop is not None and loop.is_running():
            asyncio.run_coroutine_threadsafe(ws.close(), loop)
        if self._ws_thread:
            self._ws_thread.join(timeout=2.0)
        self._connected = False
        self._player_count = 0

    def _disconnect(self):
        self._disconnect_ws()
        if self._server_proc and self._server_proc.poll() is None:
            self._server_proc.terminate()

    # ------------------------------------------------------------------
    # Lobby loop
    # ------------------------------------------------------------------

    def reset(self):
        self.selection = None
        self.inputs._reset()

    def loop(self) -> Optional[ROLE]:
        while self.selection is None and not self.inputs.quit:
            time_delta = self.clock.tick(self.FRAME_RATE) / 1000.0
            self.window.fill((132, 226, 150))
            self._handle_events(time_delta)
            self._draw()
            pygame.display.update()

        self._disconnect_ws()
        if self.selection is None:
            if self._server_proc and self._server_proc.poll() is None:
                self._server_proc.terminate()
        return self.selection

    def _handle_events(self, time_delta: float):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.inputs.quit = True
                return

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.inputs.quit = True
                    return
                elif event.key == pygame.K_LEFT:
                    self.current_class = (self.current_class - 1) % len(self.classes)
                elif event.key == pygame.K_RIGHT:
                    self.current_class = (self.current_class + 1) % len(self.classes)
                elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    if self._connected:
                        self.selection = self.classes[self.current_class][0]

            if event.type == pygame_gui.UI_BUTTON_PRESSED:
                if event.ui_element == self._btn_host:
                    self._launch_server()
                    threading.Timer(0.5, self._connect_ws).start()
                elif event.ui_element == self._btn_connect:
                    self._connect_ws()
                elif event.ui_element == self._btn_disconnect:
                    self._disconnect()
                elif event.ui_element == self._btn_play and self._connected:
                    self.selection = self.classes[self.current_class][0]

            self.manager.process_events(event)

        self.manager.update(time_delta)

        # Sync button/label state with connection status
        if self._connected:
            self._btn_connect.hide()
            self._btn_disconnect.show()
            self._btn_play.enable()
            self._lbl_status.set_text("Connected")
        else:
            self._btn_connect.show()
            self._btn_disconnect.hide()
            self._btn_play.disable()
            self._lbl_status.set_text("Disconnected")

        self._lbl_players.set_text(f"{self._player_count}/4")

    def _draw(self):
        surface = self.window
        W, _ = surface.get_size()
        panel_rect = self._panel.get_abs_rect()

        # Available vertical space above the panel
        space_above = panel_rect.top
        char_size = min(self.size, int(space_above * 0.72))

        char_x = W // 2 - char_size // 2
        char_y = panel_rect.top - char_size - 8

        self._draw_role_name(surface, W // 2, char_y - 6)

        scaled = pygame.transform.scale(
            self.classes[self.current_class][-1], (char_size, char_size)
        )
        surface.blit(scaled, (char_x, char_y))

        self.manager.draw_ui(surface)

    def _draw_role_name(self, surface, cx, bottom_y):
        role_name = self.classes[self.current_class][0].value.capitalize()
        text_surface = self.ROLE_TEXT_FONT.render(role_name, False, (255, 255, 255))
        x = cx - text_surface.get_rect().width // 2
        y = bottom_y - text_surface.get_rect().height
        surface.blit(text_surface, (x, y))
