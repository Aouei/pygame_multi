import asyncio
import json
import sys
import pygame
import websockets
from loguru import logger


import messages

from levels import lobby
from enums import ROLE, MESSAGES
from inputs import InputHandler
from states.client_logic import Logic

pygame.init()

# window = pygame.display.set_mode((500, 500))
window = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
WIDTH, HEIGHT = window.get_size()

class Client:
    LOGIC = Logic()
    INPUTS = InputHandler()
    CLOCK = pygame.time.Clock()
    FRAME_RATE = 60

    def __init__(self) -> None:
        self.offset_x = 0
        self.offset_y = 0
    
    async def receive_from_server(self, websocket) -> None:
        async for raw in websocket:
            data = json.loads(raw)

            message_type = MESSAGES(data["type"])
            
            if message_type == MESSAGES.HELLO:
                self.LOGIC.ID = data["id"]
            elif message_type == MESSAGES.PLAYERS_UPDATE:
                self.LOGIC.update_players({int(k): v for k, v in data.get("players", {}).items()})
                self.LOGIC.update_bullets(data.get('bullets', []))

    async def loop(self, websocket) -> None:
        while True:
            self.__center_screen()
            await self.__handle_player_actions(websocket) 

            window.fill((0, 0, 0))
            self.LOGIC.draw(window, -self.offset_x, -self.offset_y)

            pygame.display.flip()
            self.CLOCK.tick(self.FRAME_RATE)
            await asyncio.sleep(0) 

    async def __handle_player_actions(self, websocket):
        self.INPUTS.update()

        if self.INPUTS.quit:
            pygame.quit()
            sys.exit()

        dx, dy, state = self.LOGIC.player.wish_to_move(self.INPUTS)
        if dx != 0 or dy != 0:
            logger.info(f"Sending to server {MESSAGES.WISH_MOVE}")
            await messages.wish_move(dx, dy, state, websocket) 
            
        dx, dy = self.LOGIC.player.wish_to_shoot(self.INPUTS, self.offset_x, self.offset_y)
        print(dx, dy)
        if dx != 0 or dy != 0:
            await messages.wish_shot(self.LOGIC.player.role, dx, dy, websocket)

    def __center_screen(self):

        if self.LOGIC.ID >= 0:
            center_x = self.LOGIC.player.pos.x + self.LOGIC.player.radius
            center_y = self.LOGIC.player.pos.y + self.LOGIC.player.radius
        else:
            center_x = WIDTH // 2
            center_y = HEIGHT // 2

        map_pixel_width = self.LOGIC.STATE.MAP.width
        map_pixel_height = self.LOGIC.STATE.MAP.height
        self.offset_x = center_x - WIDTH // 2
        self.offset_y = center_y - HEIGHT // 2
        self.offset_x = max(0, min(self.offset_x, map_pixel_width - WIDTH))
        self.offset_y = max(0, min(self.offset_y, map_pixel_height - HEIGHT))
    
    async def connect(self, role : ROLE) -> None:
        async with websockets.connect("ws://25.33.144.47:25565") as websocket:
            logger.info(f"Sending to server: {role}")
            await messages.set_role(role, websocket)
            
            await asyncio.gather(
                self.receive_from_server(websocket),
                self.loop(websocket),
            )


if __name__ == '__main__':
    client = Client()

    
    first_screen = lobby.Screen(client.INPUTS)
    role = first_screen.loop(window, client.CLOCK, client.FRAME_RATE)

    asyncio.run(client.connect(role))