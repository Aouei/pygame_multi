
import os
import pandas as pd
import asyncio
import json
import websockets
import numpy as np
from scipy.spatial import KDTree
from loguru import logger
from game_state import GameState

# Constants
PLAYER_SIZE = 64
TILE_SIZE = 64
TICK_RATE = 20  # Server broadcasts at 20 Hz regardless of client input rate


# Map loading (same as client)
import sys
if getattr(sys, "frozen", False):
    BASE_DIR = sys._MEIPASS
else:
    BASE_DIR = os.path.join(os.path.dirname(__file__), "..")
ASSETS_DIR  = os.path.join(BASE_DIR, "assets")
TILES_DIR   = os.path.join(ASSETS_DIR, "tiles")
MAP_PATH    = os.path.join(ASSETS_DIR, "map", "map.csv")
SPRITE_PATH = os.path.join(ASSETS_DIR, "nave.png")
map_data = pd.read_csv(MAP_PATH, header=None).values

# Tiles sólidos (ejemplo: 5 es sólido, puedes ajustar según el diseño)
SOLID_TILES = {2}
SPAWN_CODE = 8

# Preprocesar posiciones sólidas para KDTree
solid_positions = []
for i, row in enumerate(map_data):
    for j, col in enumerate(row):
        if col in SOLID_TILES:
            solid_positions.append((j * TILE_SIZE + TILE_SIZE // 2, i * TILE_SIZE + TILE_SIZE // 2))

solid_tree = KDTree(solid_positions) if solid_positions else None

def is_collision(x, y):
    """Chequea si el rectángulo (x, y, PLAYER_SIZE, PLAYER_SIZE) colisiona con un tile sólido."""
    for sx, sy in solid_positions:
        # Tile rect
        tile_rect = (sx, sy, TILE_SIZE, TILE_SIZE)
        # Player rect
        player_rect = (x, y, PLAYER_SIZE, PLAYER_SIZE)
        # Check intersection
        if (
            player_rect[0] < tile_rect[0] + tile_rect[2] and
            player_rect[0] + player_rect[2] > tile_rect[0] and
            player_rect[1] < tile_rect[1] + tile_rect[3] and
            player_rect[1] + player_rect[3] > tile_rect[1]
        ):
            return True
    return False


# State managed by GameState
game_state = GameState(map_data, solid_positions, is_collision)


async def handle_client(websocket):
    player_id = game_state.add_client(websocket)
    try:
        # Inform client of its assigned ID
        msg = json.dumps({"type": "hello", "id": player_id})
        logger.info(f"Enviando mensaje a cliente {player_id}: {msg}")
        await websocket.send(msg)

        async for message in websocket:
            data = json.loads(message)

            if data["type"] == "start":
                game_state.handle_start(player_id, data)
            elif data["type"] == "move":
                game_state.handle_move(player_id, data)

    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        game_state.remove_client(websocket)


async def broadcast_loop():
    """Sends world state to all clients at a fixed 20 Hz tick rate."""
    interval = 1.0 / TICK_RATE
    while True:
        await asyncio.sleep(interval)
        if not game_state.clients:
            continue

        update = json.dumps({"type": "update", "players": game_state.get_players()})
        dead = []
        for ws in list(game_state.clients):
            try:
                logger.info(f"Enviando actualización a cliente {game_state.clients[ws]}: {update}")
                await ws.send(update)
            except websockets.exceptions.ConnectionClosed:
                dead.append(ws)
        for ws in dead:
            game_state.remove_client(ws)


async def main():
    logger.info(f"Server running")

    async with websockets.serve(handle_client, "0.0.0.0", 25565):
        await broadcast_loop()


asyncio.run(main())
