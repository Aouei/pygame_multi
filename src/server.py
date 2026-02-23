import asyncio
import json
import random
import websockets
import numpy as np

# Constants
WIDTH, HEIGHT = 800, 600
PLAYER_SIZE = 32

# Store player data
players = {}
next_player_id = 1
clients = set()

async def handle_client(websocket):
    global next_player_id
    player_id = next_player_id
    next_player_id += 1
    clients.add(websocket)
    
    try:
        async for message in websocket:
            data = json.loads(message)
            if data['type'] == 'start':
                players[player_id] = {
                    'x_lim' : data['x'],
                    'y_lim' : data['y'],
                    "x": random.randint(PLAYER_SIZE, data['x'] - PLAYER_SIZE),
                    "y": random.randint(PLAYER_SIZE, data['y'] - PLAYER_SIZE),
                }
            elif data["type"] == "move" and player_id in players:
                new_x = np.clip(players[player_id]["x"] + data['dx'], 0, players[player_id]['x_lim'])
                new_y = np.clip(players[player_id]["y"] + data['dy'], 0, players[player_id]['y_lim'])
                players[player_id]["x"] = int(new_x)
                players[player_id]["y"] = int(new_y)
            # Broadcast updates to all clients
            update = json.dumps({"type": "update", "players": players})
            await asyncio.gather(*(client.send(update) for client in clients))
    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        del players[player_id]
        clients.remove(websocket)

async def main():
    async with websockets.serve(handle_client, "localhost", 8765):
        await asyncio.Future()  # Keep server running

asyncio.run(main())