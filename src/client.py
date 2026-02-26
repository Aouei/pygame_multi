import asyncio
import json
import os
import sys
import pygame
import websockets
import pandas as pd
import numpy as np
from loguru import logger


import messages

from levels import game, lobby
from enums import PLAYER_CLASS, MESSAGES, STATE
from entities.player import Player
from inputs import InputHandler
from states import ClientState


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
FRAME_RATE   = 60
PLAYER_SPEED = 5
PLAYER_SIZE  = 64
TILE_SIZE    = 64
BACKGROUND_COLOR = (127, 64, 0)

# ---------------------------------------------------------------------------
# Paths (relative to this file so the project is portable)
# ---------------------------------------------------------------------------
if getattr(sys, "frozen", False):
    BASE_DIR = sys._MEIPASS
else:
    BASE_DIR = os.path.join(os.path.dirname(__file__), "..")
ASSETS_DIR  = os.path.join(BASE_DIR, "assets")
PLAYER_DIR  = os.path.join(ASSETS_DIR, "player")
TILES_DIR   = os.path.join(ASSETS_DIR, "tiles")
MAP_PATH    = os.path.join(ASSETS_DIR, "map", "map.csv")

PLAYER = {
    'up' : pygame.transform.scale(pygame.image.load(os.path.join(PLAYER_DIR, 'mage', "up.png")), (PLAYER_SIZE, PLAYER_SIZE)),
    'down' : pygame.transform.scale(pygame.image.load(os.path.join(PLAYER_DIR, 'mage', "down.png")), (PLAYER_SIZE, PLAYER_SIZE)),
    'right' : pygame.transform.scale(pygame.image.load(os.path.join(PLAYER_DIR, 'mage', "right.png")), (PLAYER_SIZE, PLAYER_SIZE)),
    'left' : pygame.transform.scale(pygame.image.load(os.path.join(PLAYER_DIR, 'mage', "left.png")), (PLAYER_SIZE, PLAYER_SIZE)),
}
CURRENT_STATE = 'down'

# ---------------------------------------------------------------------------
# Pygame setup
# ---------------------------------------------------------------------------
pygame.init()

window = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
WIDTH, HEIGHT = window.get_size()

class Client:
    INPUTS = InputHandler()
    CLOCK = pygame.time.Clock()
    FRAME_RATE = 60
    server_positions = {}
    render_positions =  {}


    def __init__(self):
        self.state = ClientState()
        self.ID = -1
        self.server_positions = {}
        self.render_positions = {}

    async def update(self, websocket) -> None:
        async for raw in websocket:
            data = json.loads(raw)

            message_type = MESSAGES(data["type"])
            
            if message_type == MESSAGES.HELLO:
                self.ID = data["id"]
            elif message_type == MESSAGES.PLAYERS_UPDATE:
                print(data)

                self.server_positions.clear()
                self.server_positions.update(data.get("players", {}))

                # Initialise render position for newly connected players
                for pid, pos in self.server_positions.items():
                    if pid not in self.render_positions:
                        self.render_positions[pid] = pos

                # Remove players that have disconnected
                for pid in list(self.render_positions):
                    if pid not in self.server_positions:
                        del self.render_positions[pid]


    async def loop(self, websocket) -> None:
        while True:
            self.INPUTS.update()

            if self.INPUTS.quit:
                pygame.quit()
                sys.exit()

            dx, dy, state = self.player.wish_to_move(self.INPUTS)
            if dx != 0 or dy != 0:
                logger.info(f"Sending to server {MESSAGES.WISH_MOVE}")
                await messages.wish_move(dx, dy, state, websocket) 

            for pid, srv in self.server_positions.items():
                rnd = self.render_positions.get(pid)
                if rnd is None:
                    self.render_positions[pid] = srv
                    continue

                rnd["x"] = srv["x"]
                rnd["y"] = srv["y"]
                rnd["state"] = srv["state"]

            window.fill(BACKGROUND_COLOR)

            my_id = str(self.ID)
            if self.ID >= 0 and my_id in self.render_positions:
                player_pos = self.render_positions[my_id]
                center_x = int(player_pos["x"] + PLAYER_SIZE // 2)
                center_y = int(player_pos["y"] + PLAYER_SIZE // 2)
            else:
                center_x = WIDTH // 2
                center_y = HEIGHT // 2


            map_pixel_width = self.state.MAP.width
            map_pixel_height = self.state.MAP.height
            offset_x = center_x - WIDTH // 2
            offset_y = center_y - HEIGHT // 2
            offset_x = max(0, min(offset_x, map_pixel_width - WIDTH))
            offset_y = max(0, min(offset_y, map_pixel_height - HEIGHT))

            self.state.MAP.draw(window, (-offset_x, -offset_y))

            minmap_points = []
            for pid, pos in self.render_positions.items():
                self.state.draw(window, -offset_x, -offset_y, pos)
                minmap_points.append({'x' : pos['x'], 'y' : pos['y'], 'color' : self.state.COLORS[int(pid)]} )
            else:
                self.state.MAP.draw_mini(window, 16, 16, minmap_points)

            pygame.display.flip()
            self.CLOCK.tick(self.FRAME_RATE)
            await asyncio.sleep(0)  # Cede el control al event loop para que `update` reciba mensajes del servidor
    
    async def connect(self, player_class : PLAYER_CLASS) -> None:
        self.player = Player(None, PLAYER_DIR, player_class)

        async with websockets.connect("ws://25.33.144.47:25565") as websocket:
            logger.info(f"Sending to server: {MESSAGES.PLAYER_CLASS}")
            await messages.player_class(self.player.class_type, websocket)
            
            await asyncio.gather(
                self.update(websocket),
                self.loop(websocket),
            )

if __name__ == '__main__':
    client = Client()

    first_screen = lobby.Screen(client.INPUTS, PLAYER_DIR)
    selection = first_screen.loop(window, client.CLOCK, client.FRAME_RATE)

    asyncio.run(client.connect(selection))