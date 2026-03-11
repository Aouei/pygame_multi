import asyncio
import json
import websockets
import pygame

from pygame.time import Clock
from loguru import logger


import messages
from enums import ROLE, MESSAGES
from states.client_logic import Logic
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

    async def receive_from_server(self, websocket) -> None:
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

            pygame.display.flip()
            self.clock.tick(self.FRAME_RATE)
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
        if host == "render":
            connection = RENDER
        else:
            connection = f"ws://{host}:{port}"

        async with websockets.connect(connection) as websocket:
            self.connected = True

            logger.info(f"Sending to server: {role}")
            await messages.set_role(role, websocket)

            recv_task = asyncio.create_task(self.receive_from_server(websocket))
            await self.loop(websocket)
            recv_task.cancel()

        self.LOGIC.stop_music()
        return "lobby"
