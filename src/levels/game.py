import asyncio
import json
import websockets
import pygame
import pygame_gui

from pygame.time import Clock
from loguru import logger


import messages
from enums import ROLE, MESSAGES
from client import Logic
from inputs import InputHandler
from factories import BASE_COLOR



class Camera:    
    def __init__(self, x, y, map_pixel_w: int, map_pixel_h: int,
        screen_w: int, screen_h: int) -> None:
        self.x = x
        self.y = y
        self.map_w = map_pixel_w
        self.map_h = map_pixel_h
        self.screen_w = screen_w
        self.screen_h = screen_h
        
    def move(self, dx: int, dy: int) -> None:
        self.x = max(0, min(self.x + dx, self.map_w - self.screen_w))
        self.y = max(0, min(self.y + dy, self.map_h - self.screen_h))
        
    @property
    def offset(self) -> tuple[int, int]:
        return self.x, self.y



class Game:
    FRAME_RATE = 60

    def __init__(
        self, window: pygame.Surface, inputs: InputHandler, clock: Clock
    ) -> None:
        self.LOGIC = Logic()
        self.camera = Camera(x = self.LOGIC.player.x, y = self.LOGIC.player.y,
                             map_pixel_h = self.LOGIC.map_height, map_pixel_w = self.LOGIC.map_width,
                             screen_h = window.get_height(), screen_w = window.get_width())
        self.inputs = inputs
        self.clock = clock
        self.window = window
        self.connected = True
        self._last_sent_state: str | None = None

        self._hud_manager = pygame_gui.UIManager(window.get_size())
        self._build_hud()

    # ------------------------------------------------------------------
    # HUD
    # ------------------------------------------------------------------

    def _build_hud(self):
        W, H = self.window.get_size()
        pw = max(180, min(220, int(W * 0.13)))  # panel width, responsive
        M = 10
        ew = pw - 2 * M
        pad = 12  # screen edge margin

        # Row heights and y positions (relative to panel top)
        row_h = 18
        bar_h = 16
        gap = 8
        y0 = M                             # HP label
        y1 = y0 + row_h + 2               # HP bar
        y2 = y1 + bar_h + gap             # Ships label
        y3 = y2 + row_h + gap             # Enemies label
        y4 = y3 + row_h + gap             # Castles label
        ph = y4 + row_h + M               # panel height

        self._hud_rect = pygame.Rect(W - pw - pad, H - ph - pad, pw, ph)
        self._hud_bg = pygame.Surface((pw, ph), pygame.SRCALPHA)
        self._hud_bg.fill((70, 70, 70, 170))

        rx = self._hud_rect.x + M
        ry = self._hud_rect.y

        self._lbl_hp = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(rx, ry + y0, ew, row_h),
            text="HP: 20/20",
            manager=self._hud_manager,
        )
        # HP bar drawn manually; store its screen rect
        self._hp_bar_rect = pygame.Rect(rx, ry + y1, ew, bar_h)

        self._lbl_ships = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(rx, ry + y2, ew, row_h),
            text="Ships: 0",
            manager=self._hud_manager,
        )
        self._lbl_enemies = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(rx, ry + y3, ew, row_h),
            text="Enemies: 0",
            manager=self._hud_manager,
        )
        self._lbl_castles = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(rx, ry + y4, ew, row_h),
            text="Castles: 0",
            manager=self._hud_manager,
        )

    def _draw_hud(self, surface: pygame.Surface, time_delta: float):
        player = self.LOGIC.player
        live = player.live
        max_live = player.max_live
        ratio = max(0.0, live / max_live) if max_live > 0 else 0.0

        # Update label text
        self._lbl_hp.set_text(f"HP: {live}/{max_live}")
        self._lbl_ships.set_text(f"Ships: {len(self.LOGIC.received_ships)}")
        self._lbl_enemies.set_text(f"Enemies: {len(self.LOGIC.received_enemies)}")
        self._lbl_castles.set_text(f"Castles: {len(self.LOGIC.castles)}")

        self._hud_manager.update(time_delta)

        # Semi-transparent grey panel
        surface.blit(self._hud_bg, self._hud_rect.topleft)

        # Health bar (manual draw so it respects the transparent background)
        bar = self._hp_bar_rect
        pygame.draw.rect(surface, (0, 0, 0), bar)
        pygame.draw.rect(surface, (220, 60, 60), (bar.x, bar.y, int(bar.w * ratio), bar.h))
        pygame.draw.rect(surface, (200, 200, 200), bar, 1)

        # pygame_gui labels on top
        self._hud_manager.draw_ui(surface)

    # ------------------------------------------------------------------

    async def receive_from_server(self, websocket) -> None:
        try:
            async for raw in websocket:
                data = json.loads(raw)

                message_type = MESSAGES(data["type"])

                if message_type == MESSAGES.HELLO:
                    self.LOGIC.ID = data["id"]
                elif message_type == MESSAGES.PLAYERS_UPDATE:
                    self.LOGIC.update_players(
                        {int(k): v for k, v in data.get("players", {}).items()}
                    )
                    self.LOGIC.update_bullets(data.get("bullets", []))
                    self.LOGIC.update_ships(data.get("ships", []))
                    self.LOGIC.update_enemies(data.get("enemies", []))
                    self.LOGIC.update_castles(data.get("castles", {}))
                elif message_type == MESSAGES.QUIT:
                    self.connected = False
        except websockets.exceptions.ConnectionClosed:
            self.connected = False

    def update_camera(self):
        self.camera.x = self.LOGIC.player.x
        self.camera.y = self.LOGIC.player.y
        self.camera.move(-self.camera.screen_w // 2, 
                         - self.camera.screen_h // 2)

    async def loop(self, websocket) -> None:
        while self.connected and not self.inputs.quit:
            await self.__handle_player_actions(websocket)

            print(self.LOGIC.player)

            self.update_camera()
            self.window.fill(BASE_COLOR)
            self.LOGIC.draw(self.window, -self.camera.x, -self.camera.y)

            time_delta = self.clock.tick(self.FRAME_RATE) / 1000.0
            self._draw_hud(self.window, time_delta)
            pygame.display.flip()
            await asyncio.sleep(0)

    async def __handle_player_actions(self, websocket):
        self.inputs.update()

        dx, dy, state = self.LOGIC.player.wish_to_move(self.inputs)
        if dx != 0 or dy != 0 or state != self._last_sent_state:
            self._last_sent_state = state
            await messages.wish_move(dx, dy, state, websocket)

        dx, dy = self.LOGIC.player.wish_to_shoot(
            self.inputs, self.camera.x, self.camera.y
        )
        if dx != 0 or dy != 0:
            await messages.wish_shot(self.LOGIC.player.role, dx, dy, websocket)


    async def run(self, role: ROLE, host: str, port: str) -> str:
        self.LOGIC.reset()
        self.LOGIC.start_music()

        RENDER = "wss://oh-no-ships.onrender.com"
        connection = RENDER if host == "render" else f"ws://{host}:{port}"

        try:
            async with websockets.connect(connection) as websocket:
                self.connected = True

                logger.info(f"Sending to server: {role}")
                await messages.set_role(role, websocket)

                recv_task = asyncio.create_task(self.receive_from_server(websocket))
                await self.loop(websocket)
                recv_task.cancel()
        except (OSError, websockets.exceptions.WebSocketException) as e:
            logger.warning(f"WebSocket connection error: {e}")
        finally:
            self.LOGIC.stop_music()

        return "lobby"
