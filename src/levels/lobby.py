import pygame, os, sys
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
from UI import TextButton, TextInput, TextLabel

pygame.font.init()


class Screen:
    FRAME_RATE = 60
    ROLE_TEXT_FONT = pygame.font.Font(None, 64)
    PANEL_COLOR = (30, 30, 30)
    PANEL_BORDER = (80, 80, 80)

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

        self._build_ui()

    def _build_ui(self):
        win_rect = self.window.get_rect()
        panel_w, panel_h = 350, 300
        panel_x = win_rect.centerx - panel_w * 2
        panel_y = win_rect.centerx - panel_h * 1.7
        self._panel_rect = pygame.Rect(panel_x, panel_y, panel_w, panel_h)

        p = self._panel_rect
        self.host = TextInput(p, -100, 20, 200, 40, "25.33.144.47", None, max_chars=15, rel_x = 0.5)
        self.port = TextInput(p, -100, 70, 200, 40, "25565", None, max_chars=5, rel_x = 0.5)
        self.btn_host = TextButton(p, 0, 120, 130, 40, "host", None, rel_x = 0.1)
        self.btn_connect = TextButton(p, -65, 120, 130, 40, "connect", None, rel_x = 0.7)
        self.btn_disconnect = TextButton(p, 0, 170, 130, 40, "disconnect", None, rel_x = 0.1)
        self.btn_play = TextButton(p, -65, 170, 130, 40, "play", None, rel_x = 0.7)
        self.lbl_status = TextLabel(p, 0, 225, "disconnected", None, 24, (255, 255, 255), rel_x = 0.1)
        self.lbl_players = TextLabel(p, -65, 225, "0/4", None, 24, (255, 255, 255), rel_x = 0.7)

    # ------------------------------------------------------------------
    # Server subprocess
    # ------------------------------------------------------------------

    def _launch_server(self):
        if self._server_proc and self._server_proc.poll() is None:
            self._server_proc.terminate()
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
            self.window.fill((132, 226, 150))
            self.handle_events()
            self.draw(self.window)
            pygame.display.update()
            self.clock.tick(self.FRAME_RATE)

        self._disconnect_ws()
        if self.selection is None:
            if self._server_proc and self._server_proc.poll() is None:
                self._server_proc.terminate()
        return self.selection

    def handle_events(self):
        self.inputs.update()

        if self.inputs.quit:
            self.selection = None
            return

        if self.inputs.k_left:
            self.current_class = (self.current_class - 1) % len(self.classes)
        if self.inputs.k_right:
            self.current_class = (self.current_class + 1) % len(self.classes)
        if self.inputs.k_enter:
            self.selection = self.classes[self.current_class][0]

        self.host.update(self.inputs)
        self.port.update(self.inputs)
        self.btn_host.update(self.inputs)
        self.btn_connect.update(self.inputs)
        self.btn_disconnect.update(self.inputs)
        self.btn_play.update(self.inputs)

        if self.btn_host.clicked:
            self._launch_server()
            threading.Timer(0.5, self._connect_ws).start()
        if self.btn_connect.clicked:
            self._connect_ws()
        if self.btn_disconnect.clicked:
            self._disconnect()
        if self.btn_play.clicked and self._connected:
            self.selection = self.classes[self.current_class][0]

        if self._connected:
            self.lbl_status.text = "connected"
            self.lbl_status.color = (0, 200, 0)
        else:
            self.lbl_status.text = "disconnected"
            self.lbl_status.color = (255, 255, 255)
        self.lbl_players.text = f"{self._player_count}/4"

    def draw(self, surface):
        center = list(surface.get_rect().center)

        image_pos = center.copy()
        image_pos[0] -= self.size // 2
        image_pos[1] -= self.size // 2

        self.draw_role_name(surface, center.copy())

        pygame.draw.rect(surface, self.PANEL_COLOR, self._panel_rect)
        pygame.draw.rect(surface, self.PANEL_BORDER, self._panel_rect, width=2)

        self.host.draw(surface)
        self.port.draw(surface)
        self.btn_host.draw(surface)
        self.btn_connect.draw(surface)
        self.btn_disconnect.draw(surface)
        self.btn_play.draw(surface)
        self.lbl_status.draw(surface)
        self.lbl_players.draw(surface)

        new_surface = pygame.transform.scale(
            self.classes[self.current_class][-1], (self.size, self.size)
        )
        surface.blit(new_surface, image_pos)

    def draw_role_name(self, surface, text_pos):
        role_name = self.classes[self.current_class][0].value.capitalize()
        text_surface = self.ROLE_TEXT_FONT.render(role_name, False, (255, 255, 255))
        text_pos[0] -= text_surface.get_rect().width // 2
        text_pos[1] -= self.size // 2 + text_surface.get_rect().height

        surface.blit(text_surface, text_pos)
