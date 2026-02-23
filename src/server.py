import asyncio
import json
import random
import websockets

# Constants
WIDTH, HEIGHT = 800, 600
PLAYER_SIZE = 64

# Store player data
players = {}
next_player_id = 1
clients = set()

async def handle_client(websocket):
    print('new')
    global next_player_id
    player_id = next_player_id
    next_player_id += 1
    players[player_id] = {"x": random.randint(PLAYER_SIZE, WIDTH - PLAYER_SIZE),
                          "y": random.randint(PLAYER_SIZE, HEIGHT - PLAYER_SIZE),
                          "score": 0}
    clients.add(websocket)
    print(players)
    try:
        # Enviar estado inicial al cliente recién conectado
        initial_update = json.dumps({"type": "update", "players": players})
        await websocket.send(initial_update)

        async for message in websocket:
            data = json.loads(message)
            if data["type"] == "move":
                players[player_id]["x"] += data["dx"]
                players[player_id]["y"] += data["dy"]
            
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