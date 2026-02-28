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


class Game:
    LOGIC = Logic()
    FRAME_RATE = 60

    def __init__(self, window : pygame.Surface, inputs : InputHandler, clock : Clock) -> None:
        self.offset_x = 0
        self.offset_y = 0
        self.inputs = inputs
        self.clock = clock
        self.window = window
        self.WIDTH, self.HEIGHT = window.get_rect().width, window.get_rect().height
    
    async def receive_from_server(self, websocket) -> None:
        async for raw in websocket:
            data = json.loads(raw)

            message_type = MESSAGES(data["type"])
            
            if message_type == MESSAGES.HELLO:
                self.LOGIC.ID = data["id"]
            elif message_type == MESSAGES.PLAYERS_UPDATE:
                self.LOGIC.update_players({int(k): v for k, v in data.get("players", {}).items()})
                self.LOGIC.update_bullets(data.get('bullets', []))
                self.LOGIC.update_ships(data.get('ships', []))

    async def loop(self, websocket) -> None:
        while True and not self.inputs.quit:
            self.__center_screen()
            await self.__handle_player_actions(websocket)

            self.window.fill((0, 0, 0))
            self.LOGIC.draw(self.window, -self.offset_x, -self.offset_y)

            pygame.display.flip()
            self.clock.tick(self.FRAME_RATE)
            await asyncio.sleep(0) 

    async def __handle_player_actions(self, websocket):
        self.inputs.update()

        dx, dy, state = self.LOGIC.player.wish_to_move(self.inputs)
        if dx != 0 or dy != 0:
            logger.info(f"Sending to server {MESSAGES.WISH_MOVE}")
            await messages.wish_move(dx, dy, state, websocket) 
            
        dx, dy = self.LOGIC.player.wish_to_shoot(self.inputs, self.offset_x, self.offset_y)
        if dx != 0 or dy != 0:
            await messages.wish_shot(self.LOGIC.player.role, dx, dy, websocket)

    def __center_screen(self):

        if self.LOGIC.ID >= 0:
            center_x = self.LOGIC.player.x + self.LOGIC.player.radius
            center_y = self.LOGIC.player.y + self.LOGIC.player.radius
        else:
            center_x = self.WIDTH // 2
            center_y = self.HEIGHT // 2

        map_pixel_width = self.LOGIC.STATE.MAP.width
        map_pixel_height = self.LOGIC.STATE.MAP.height
        self.offset_x = center_x - self.WIDTH // 2
        self.offset_y = center_y - self.HEIGHT // 2
        self.offset_x = max(0, min(self.offset_x, map_pixel_width - self.WIDTH))
        self.offset_y = max(0, min(self.offset_y, map_pixel_height - self.HEIGHT))
    
    async def run(self, role : ROLE) -> str:
        self.LOGIC.reset()                         # ← también falta esto

        async with websockets.connect("ws://25.33.144.47:25565") as websocket:
            logger.info(f"Sending to server: {role}")
            await messages.set_role(role, websocket)
            
            recv_task = asyncio.create_task(self.receive_from_server(websocket))
            await self.loop(websocket)
            recv_task.cancel()

        return 'lobby'