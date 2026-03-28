import os
import pygame
import pygame_gui
import asyncio
import json
import threading
from typing import Optional

import websockets

import frameworks.paths as paths
from domain.enums import ROLE
from adapters.messages import MESSAGES
from frameworks.inputs import InputHandler
from use_cases.lobby_service import LobbyService
from pygame.time import Clock


pygame.font.init()


class _EntryWrapper:
    """Exposes .value so main.py can do LOBBY.host.value / LOBBY.port.value."""

    def __init__(self, entry: pygame_gui.elements.UITextEntryLine):
        self._entry = entry

    @property
    def value(self) -> str:
        return self._entry.get_text()


class Screen:
    FRAME_RATE = 60

    def __init__(self, window: pygame.Surface, inputs: InputHandler, clock: Clock):
        self.inputs = inputs
        self.classes: list[tuple[ROLE, pygame.Surface]] = [
            (
                ROLE.ARCHER,
                pygame.image.load(
                    os.path.join(paths.PLAYER_DIR, r"archer\idle.png")
                ),
            ),
            (
                ROLE.MAGE,
                pygame.image.load(
                    os.path.join(paths.PLAYER_DIR, r"mage\idle.png")
                ),
            ),
            (
                ROLE.FARMER,
                pygame.image.load(
                    os.path.join(paths.PLAYER_DIR, r"farmer\idle.png")
                ),
            ),
            (
                ROLE.MUSKETEER,
                pygame.image.load(
                    os.path.join(
                        paths.PLAYER_DIR, r"musketeer\idle.png"
                    )
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
        self._focused = 0
        import asyncio
        from frameworks.ws_runner import run as _ws_run
        self._lobby_service = LobbyService(runner=lambda srv: asyncio.run(_ws_run(srv)))
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

        panel_w = max(230, min(300, int(W * 0.20)))
        panel_h = 235
        char_size = min(self.size, int(H * 0.52))
        gap = max(30, int(W * 0.04))

        total_w = panel_w + gap + char_size
        left_x = (W - total_w) // 2
        center_y = H // 2

        panel_rect = pygame.Rect(left_x, center_y - panel_h // 2, panel_w, panel_h)
        self._panel = pygame_gui.elements.UIPanel(
            relative_rect=panel_rect,
            manager=self.manager,
        )

        self._char_x = left_x + panel_w + gap
        self._char_y = center_y - char_size // 2
        self._char_size = char_size

        M = 12
        ew = panel_w - 2 * M
        btn_w = (ew - 20) // 3

        pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(M, 8, ew, 22),
            text="IP",
            manager=self.manager,
            container=self._panel,
        )
        self._ip_entry = pygame_gui.elements.UITextEntryLine(
            relative_rect=pygame.Rect(M, 32, ew, 34),
            manager=self.manager,
            container=self._panel,
            initial_text="25.33.144.47",
        )

        pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(M, 74, ew, 22),
            text="Port",
            manager=self.manager,
            container=self._panel,
        )
        self._port_entry = pygame_gui.elements.UITextEntryLine(
            relative_rect=pygame.Rect(M, 98, ew, 34),
            manager=self.manager,
            container=self._panel,
            initial_text="25565",
        )
        self._port_entry.set_allowed_characters(list("0123456789"))

        self._btn_host = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(M, 145, btn_w, 36),
            text="Host",
            manager=self.manager,
            container=self._panel,
        )
        self._btn_connect = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(M + btn_w + 10, 145, btn_w, 36),
            text="Connect",
            manager=self.manager,
            container=self._panel,
        )
        self._btn_disconnect = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(M + btn_w + 10, 145, btn_w, 36),
            text="Disconnect",
            manager=self.manager,
            container=self._panel,
        )
        self._btn_disconnect.hide()

        self._btn_play = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(M + 2 * (btn_w + 10), 145, btn_w, 36),
            text="Play",
            manager=self.manager,
            container=self._panel,
        )
        self._btn_play.disable()

        self._lbl_players = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(M + ew // 2, 195, ew // 2, 26),
            text="0/4",
            manager=self.manager,
            container=self._panel,
        )

        self._status_font = pygame.font.Font(None, 26)
        self._role_font = pygame.font.Font(None, 52)

        self.host = _EntryWrapper(self._ip_entry)
        self.port = _EntryWrapper(self._port_entry)

    # ------------------------------------------------------------------
    # Gamepad focus navigation
    # ------------------------------------------------------------------

    @property
    def _nav_items(self):
        if self._connected:
            items = [self._btn_disconnect]
            if self._btn_play.is_enabled:
                items.append(self._btn_play)
        else:
            items = [self._ip_entry, self._port_entry, self._btn_host, self._btn_connect]
        return items

    def _draw_focus_highlight(self, surface: pygame.Surface):
        nav = self._nav_items
        if nav:
            idx = min(self._focused, len(nav) - 1)
            rect = nav[idx].get_abs_rect()
            pygame.draw.rect(surface, (255, 220, 50), rect, 3)

    # ------------------------------------------------------------------
    # WebSocket connection probe
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
            RENDER = "wss://oh-no-ships.onrender.com"
            connection = (
                RENDER
                if self.host.value == "render"
                else f"ws://{self.host.value}:{self.port.value}"
            )
            async with websockets.connect(connection) as ws:
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
        self._lobby_service.stop_hosting()

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
            self._lobby_service.stop_hosting()
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

            elif event.type == pygame.JOYHATMOTION:
                hx, hy = event.value
                if hx == -1:
                    self.current_class = (self.current_class - 1) % len(self.classes)
                elif hx == 1:
                    self.current_class = (self.current_class + 1) % len(self.classes)
                nav = self._nav_items
                if nav:
                    if hy == 1:
                        self._focused = (self._focused - 1) % len(nav)
                    elif hy == -1:
                        self._focused = (self._focused + 1) % len(nav)
                    self._focused = min(self._focused, len(nav) - 1)

            elif event.type == pygame.JOYBUTTONDOWN:
                if event.button == 0:
                    nav = self._nav_items
                    if nav:
                        item = nav[min(self._focused, len(nav) - 1)]
                        if isinstance(item, pygame_gui.elements.UITextEntryLine):
                            from frameworks.virtual_keyboard import VirtualKeyboard
                            result = VirtualKeyboard(item.get_text()).run(self.window, self.clock)
                            if result is not None:
                                item.set_text(result)
                        elif item == self._btn_host:
                            self._lobby_service.start_hosting()
                            threading.Timer(0.5, self._connect_ws).start()
                        elif item == self._btn_connect:
                            self._connect_ws()
                        elif item == self._btn_disconnect:
                            self._disconnect()
                        elif item == self._btn_play and self._connected:
                            self.selection = self.classes[self.current_class][0]
                elif event.button == 6:
                    self.inputs.quit = True
                    return

            if event.type == pygame_gui.UI_BUTTON_PRESSED:
                if event.ui_element == self._btn_host:
                    self._lobby_service.start_hosting()
                    threading.Timer(0.5, self._connect_ws).start()
                elif event.ui_element == self._btn_connect:
                    self._connect_ws()
                elif event.ui_element == self._btn_disconnect:
                    self._disconnect()
                elif event.ui_element == self._btn_play and self._connected:
                    self.selection = self.classes[self.current_class][0]

            self.manager.process_events(event)

        self.manager.update(time_delta)

        if self._connected:
            self._btn_connect.hide()
            self._btn_disconnect.show()
            self._btn_play.enable()
        else:
            self._btn_connect.show()
            self._btn_disconnect.hide()
            self._btn_play.disable()

        self._lbl_players.set_text(f"{self._player_count}/4")

    def _draw(self):
        surface = self.window
        scaled = pygame.transform.scale(
            self.classes[self.current_class][-1],
            (self._char_size, self._char_size),
        )
        surface.blit(scaled, (self._char_x, self._char_y))
        self.manager.draw_ui(surface)
        self._draw_focus_highlight(surface)
        self._draw_status(surface)
        self._draw_role_label(surface)

    def _draw_status(self, surface):
        panel_rect = self._panel.get_abs_rect()
        if self._connected:
            color = (0, 210, 80)
            text = "Connected"
        else:
            color = (180, 180, 180)
            text = "Disconnected"
        surf = self._status_font.render(text, True, color)
        x = panel_rect.left + 12
        y = panel_rect.top + 195 + (26 - surf.get_height()) // 2
        surface.blit(surf, (x, y))

    def _draw_role_label(self, surface):
        role_name = self.classes[self.current_class][0].value.capitalize()
        surf = self._role_font.render(role_name, True, (255, 255, 255))
        cx = self._char_x + self._char_size // 2
        y = self._char_y + self._char_size + 10
        surface.blit(surf, (cx - surf.get_width() // 2, y))
