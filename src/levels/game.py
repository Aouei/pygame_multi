import asyncio
import json
import websockets
import pygame
import pygame_gui

from pygame.time import Clock
from loguru import logger

import adapters.messages as messages
from adapters.messages import MESSAGES
from adapters.camera import Camera
from adapters.input_adapter import InputAdapter
from adapters.renderer import GameRenderer
from frameworks.asset_store import AssetStore
from frameworks.inputs import InputHandler
from frameworks.factories import BASE_COLOR
from use_cases.client_session import ClientSession
from use_cases.input_translator import translate_move, translate_shoot
from domain.enums import ROLE
import frameworks.paths as paths


class Game:
    FRAME_RATE = 60

    def __init__(
        self, window: pygame.Surface, inputs: InputHandler, clock: Clock
    ) -> None:
        self._assets = AssetStore.get()
        self._session = ClientSession()
        self._renderer = GameRenderer(self._assets)
        self._input_adapter = InputAdapter(inputs)

        map_r = self._assets.map_render
        self.camera = Camera(
            x=self._session.player.x,
            y=self._session.player.y,
            map_pixel_h=map_r.height,
            map_pixel_w=map_r.width,
            screen_h=window.get_height(),
            screen_w=window.get_width(),
        )
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
        pw = max(180, min(220, int(W * 0.13)))
        M = 10
        ew = pw - 2 * M
        pad = 12

        row_h = 18
        bar_h = 16
        gap = 8
        y0 = M
        y1 = y0 + row_h + 2
        y2 = y1 + bar_h + gap
        y3 = y2 + row_h + gap
        y4 = y3 + row_h + gap
        ph = y4 + row_h + M

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
        player = self._session.player
        live = player.live
        max_live = player.max_live
        ratio = max(0.0, live / max_live) if max_live > 0 else 0.0

        self._lbl_hp.set_text(f"HP: {live}/{max_live}")
        self._lbl_ships.set_text(f"Ships: {len(self._session.received_ships)}")
        self._lbl_enemies.set_text(f"Enemies: {len(self._session.received_enemies)}")
        self._lbl_castles.set_text(f"Castles: {len(self._session.received_castles)}")

        self._hud_manager.update(time_delta)

        surface.blit(self._hud_bg, self._hud_rect.topleft)

        bar = self._hp_bar_rect
        pygame.draw.rect(surface, (0, 0, 0), bar)
        pygame.draw.rect(surface, (220, 60, 60), (bar.x, bar.y, int(bar.w * ratio), bar.h))
        pygame.draw.rect(surface, (200, 200, 200), bar, 1)

        self._hud_manager.draw_ui(surface)

    # ------------------------------------------------------------------

    async def receive_from_server(self, websocket) -> None:
        try:
            async for raw in websocket:
                data = json.loads(raw)
                message_type = MESSAGES(data["type"])

                if message_type == MESSAGES.HELLO:
                    self._session.ID = data["id"]
                elif message_type == MESSAGES.PLAYERS_UPDATE:
                    self._session.update_players(
                        {int(k): v for k, v in data.get("players", {}).items()}
                    )
                    self._session.update_bullets(data.get("bullets", []))
                    self._session.update_ships(data.get("ships", []))
                    self._session.update_enemies(data.get("enemies", []))
                    self._session.update_castles(data.get("castles", {}))
                elif message_type == MESSAGES.QUIT:
                    self.connected = False
        except websockets.exceptions.ConnectionClosed:
            self.connected = False

    def _update_camera(self):
        self.camera.x = self._session.player.x
        self.camera.y = self._session.player.y
        self.camera.move(-self.camera.screen_w // 2, -self.camera.screen_h // 2)

    def _update_music(self):
        in_battle = self._session.in_battle
        if not hasattr(self, "_was_in_battle"):
            self._was_in_battle = False

        if in_battle and not self._was_in_battle:
            pygame.mixer.music.load(paths.BATTLE_MUSIC_PATH)
            pygame.mixer.music.play(loops=-1)
            self._was_in_battle = True
        elif not in_battle and self._was_in_battle:
            pygame.mixer.music.load(paths.BACKGROND_MUSIC_PATH)
            pygame.mixer.music.play(loops=-1)
            self._was_in_battle = False

    async def loop(self, websocket) -> None:
        while self.connected and not self.inputs.quit:
            await self._handle_player_actions(websocket)
            self._update_camera()
            self.window.fill(BASE_COLOR)
            self._renderer.draw(
                self.window, self._session, -self.camera.x, -self.camera.y
            )
            self._update_music()

            time_delta = self.clock.tick(self.FRAME_RATE) / 1000.0
            self._draw_hud(self.window, time_delta)
            pygame.display.flip()
            await asyncio.sleep(0)

    async def _handle_player_actions(self, websocket):
        self.inputs.update()
        intention = self._input_adapter.read()

        dx, dy, state = translate_move(intention, self._session.player.speed)
        if dx != 0 or dy != 0 or state != self._last_sent_state:
            self._last_sent_state = state
            await messages.wish_move(dx, dy, state, websocket)

        shoot_dx, shoot_dy = translate_shoot(
            intention,
            self._session.player.x,
            self._session.player.y,
            self.camera.x,
            self.camera.y,
        )
        if shoot_dx != 0 or shoot_dy != 0:
            await messages.wish_shot(
                self._session.player.role, shoot_dx, shoot_dy, websocket
            )

    async def run(self, role: ROLE, host: str, port: str) -> str:
        self._session.reset()
        pygame.mixer.music.load(paths.BACKGROND_MUSIC_PATH)
        pygame.mixer.music.play(loops=-1)

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
            pygame.mixer.music.stop()

        return "lobby"
