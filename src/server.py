import asyncio
import json
import random
import websockets
import numpy as np

from loguru import logger

# Constants
PLAYER_SIZE = 32
TICK_RATE = 20  # Server broadcasts at 20 Hz regardless of client input rate

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
                p["x"] = int(np.clip(p["x"] + data["dx"], 0, p["x_lim"] - PLAYER_SIZE))
                p["y"] = int(np.clip(p["y"] + data["dy"], 0, p["y_lim"] - PLAYER_SIZE))
                # Input is processed immediately but broadcast happens in tick loop

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
    async with websockets.serve(handle_client, "0.0.0.0", 25565):
        await broadcast_loop()


asyncio.run(main())
