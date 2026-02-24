
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
SOLID_TILES = {1}

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
    """Chequea si la posición (x, y) colisiona con un tile sólido usando KDTree."""
    if not solid_tree:
        return False
    # Buscar tiles sólidos cercanos
    idxs = solid_tree.query_ball_point([x, y], r=radius)
    return len(idxs) > 0

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
                players[player_id] = {
                    "x_lim": data["x"],
                    "y_lim": data["y"],
                    "x": random.randint(PLAYER_SIZE, data["x"] - PLAYER_SIZE),
                    "y": random.randint(PLAYER_SIZE, data["y"] - PLAYER_SIZE),
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
