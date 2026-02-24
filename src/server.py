
import os
import pandas as pd
import asyncio
import json
import random
import websockets
import numpy as np
from scipy.spatial import KDTree
from loguru import logger

# Constants
PLAYER_SIZE = 32
TILE_SIZE = 32
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
            # Centro del tile
            solid_positions.append((j * PLAYER_SIZE + PLAYER_SIZE // 2, i * PLAYER_SIZE + PLAYER_SIZE // 2))

if solid_positions:
    solid_tree = KDTree(solid_positions)
else:
    solid_tree = None

def is_collision(x, y, radius=PLAYER_SIZE//2):
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

# State
players = {}
next_player_id = 1
clients = {}  # websocket -> player_id


async def handle_client(websocket):
    global next_player_id
    player_id = next_player_id
    next_player_id += 1
    clients[websocket] = player_id

    try:
        # Inform client of its assigned ID
        msg = json.dumps({"type": "hello", "id": player_id})
        logger.info(f"Enviando mensaje a cliente {player_id}: {msg}")
        await websocket.send(msg)

        async for message in websocket:
            data = json.loads(message)

            if data["type"] == "start":
                # Buscar tiles con valor 6
                spawn_tiles = []
                for i, row in enumerate(map_data):
                    for j, col in enumerate(row):
                        if col == SPAWN_CODE:
                            spawn_tiles.append((j, i))
                if spawn_tiles:
                    j, i = random.choice(spawn_tiles)
                    x = j * TILE_SIZE
                    y = i * TILE_SIZE
                else:
                    # Fallback: centro del mapa
                    x = data["x"] // 2
                    y = data["y"] // 2
                players[player_id] = {
                    "x_lim": data["x"],
                    "y_lim": data["y"],
                    "x": x,
                    "y": y,
                }

            elif data["type"] == "move" and player_id in players:
                p = players[player_id]
                new_x = int(np.clip(p["x"] + data["dx"], 0, p["x_lim"] - PLAYER_SIZE))
                new_y = int(np.clip(p["y"] + data["dy"], 0, p["y_lim"] - PLAYER_SIZE))
                # Chequear colisión antes de mover
                if not is_collision(new_x + PLAYER_SIZE // 2, new_y + PLAYER_SIZE // 2):
                    p["x"] = new_x
                    p["y"] = new_y
                # Si hay colisión, no se mueve

    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        players.pop(player_id, None)
        clients.pop(websocket, None)


async def broadcast_loop():
    """Sends world state to all clients at a fixed 20 Hz tick rate.
    Decoupling broadcast from input handling prevents clients with high
    input rates from flooding slower clients with updates."""
    interval = 1.0 / TICK_RATE
    while True:
        await asyncio.sleep(interval)
        if not clients:
            continue

        update = json.dumps({"type": "update", "players": players})
        dead = []
        for ws in list(clients):
            try:
                logger.info(f"Enviando actualización a cliente {clients[ws]}: {update}")
                await ws.send(update)
            except websockets.exceptions.ConnectionClosed:
                dead.append(ws)
        for ws in dead:
            pid = clients.pop(ws, None)
            if pid is not None:
                players.pop(pid, None)


async def main():
    logger.info(f"Server running")

    async with websockets.serve(handle_client, "0.0.0.0", 25565):
        await broadcast_loop()


asyncio.run(main())
