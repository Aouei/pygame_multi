import asyncio
import json
import sys
import pygame
import websockets
from loguru import logger
import math


import messages

from levels import game, lobby
from enums import ROLE, MESSAGES, STATE
from inputs import InputHandler
from states.client_state import ClientState
from entities import Player, Geometry, Live

pygame.init()

# window = pygame.display.set_mode((500, 500))
window = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
WIDTH, HEIGHT = window.get_size()

class Client:
    INPUTS = InputHandler()
    CLOCK = pygame.time.Clock()
    FRAME_RATE = 60
    server_positions = {}
    players_positions =  {}


    def __init__(self):
        self.state = ClientState()
        self.ID = -1
        self.server_positions = {}

        self.players_positions = {}
        self.bullets_positions = {}

    async def update(self, websocket) -> None:
        async for raw in websocket:
            data = json.loads(raw)

            message_type = MESSAGES(data["type"])
            
            if message_type == MESSAGES.HELLO:
                self.ID = data["id"]
            elif message_type == MESSAGES.PLAYERS_UPDATE:
                self.server_positions.clear()
                self.bullets_positions.clear()

                players = {int(k): v for k, v in data.get("players", {}).items()}
                self.server_positions.update(players)
                self.bullets_positions = data.get('bullets', [])

                # Initialise render position for newly connected players
                for pid, pos in self.server_positions.items():
                    if pid not in self.players_positions:
                        self.players_positions[pid] = pos
                else:
                    if self.ID in self.server_positions:
                        x, y, state = self.server_positions[self.ID]['x'], \
                                      self.server_positions[self.ID]['y'], \
                                      self.server_positions[self.ID]['state']
                        self.player.pos.x = x
                        self.player.pos.y = y
                        self.player.state = STATE(state)

                # Remove players that have disconnected
                for pid in list(self.players_positions):
                    if pid not in self.server_positions:
                        del self.players_positions[pid]

    def _shoot_direction(self, dx, dy):
        if self.INPUTS._joystick is not None:
            rx, ry = self.INPUTS.right_stick
            length = math.hypot(rx, ry)
            if length > self.INPUTS.deadzone:
                return rx / length, ry / length
            
            return 0, 0
        else:
            # posición del jugador en pantalla
            player_sx = self.player.pos.x - dx
            player_sy = self.player.pos.y - dy
            mx, my = self.INPUTS.mouse_pos
            dx, dy = mx - player_sx, my - player_sy
            length = math.hypot(dx, dy)
            return (dx / length, dy / length) if length > 0 else (0, 0)


    async def loop(self, websocket) -> None:
        while True:
            offset_x, offset_y = self.__center_screen()

            self.INPUTS.update()

            if self.INPUTS.quit:
                pygame.quit()
                sys.exit()

            dx, dy, state = self.player.wish_to_move(self.INPUTS)
            if dx != 0 or dy != 0:
                logger.info(f"Sending to server {MESSAGES.WISH_MOVE}")
                await messages.wish_move(dx, dy, state, websocket) 

            if self.INPUTS.shot:
                dx, dy = self._shoot_direction(offset_x, offset_y)
                if dx != 0 or dy != 0:
                    await messages.wish_shot(self.player.role, dx, dy, websocket) 


            for pid, srv in self.server_positions.items():
                rnd = self.players_positions.get(pid)
                if rnd is None:
                    self.players_positions[pid] = srv
                    continue

                rnd["x"] = srv["x"]
                rnd["y"] = srv["y"]
                rnd["state"] = srv["state"]

            window.fill((0, 0, 0))
            self.state.MAP.draw(window, (-offset_x, -offset_y))

            for bullet in self.bullets_positions:
                print('---', bullet)
                self.state.draw_bullet(window, 
                                       bullet['x'] -offset_x, 
                                       bullet['y'] -offset_y, 
                                       bullet['role'],
                                       bullet['dx'], 
                                       bullet['dy'],)

            minmap_points = []
            for pid, pos in self.players_positions.items():
                self.state.draw_player(window, -offset_x, -offset_y, pos)
                minmap_points.append({'x' : pos['x'], 'y' : pos['y'], 'color' : self.state.COLORS[int(pid)]} )
            else:
                self.state.MAP.draw_mini(window, 16, 16, minmap_points, self.player.pos.x, self.player.pos.y)

            pygame.display.flip()
            self.CLOCK.tick(self.FRAME_RATE)
            await asyncio.sleep(0) 

    def __center_screen(self):
        if self.ID >= 0:
            center_x = self.player.pos.x + self.player.radius
            center_y = self.player.pos.y + self.player.radius
        else:
            center_x = WIDTH // 2
            center_y = HEIGHT // 2


        map_pixel_width = self.state.MAP.width
        map_pixel_height = self.state.MAP.height
        offset_x = center_x - WIDTH // 2
        offset_y = center_y - HEIGHT // 2
        offset_x = max(0, min(offset_x, map_pixel_width - WIDTH))
        offset_y = max(0, min(offset_y, map_pixel_height - HEIGHT))
        return offset_x,offset_y # Cede el control al event loop para que `update` reciba mensajes del servidor
    
    async def connect(self, role : ROLE) -> None:
        self.player = Player(role, Geometry(0, 0, 32), Live(5))

        async with websockets.connect("ws://25.33.144.47:25565") as websocket:
            logger.info(f"Sending to server: {role}")
            await messages.set_role(role, websocket)
            
            await asyncio.gather(
                self.update(websocket),
                self.loop(websocket),
            )

if __name__ == '__main__':
    client = Client()

    
    first_screen = lobby.Screen(client.INPUTS)
    role = first_screen.loop(window, client.CLOCK, client.FRAME_RATE)

    asyncio.run(client.connect(role))