# server.py
# Aquí irá el código del servidor (API)

import asyncio
import websockets
import json
from loguru import logger

PORT = 8765
TICK_RATE = 1/30  # 30 FPS

clients = {}
players = {}
bullets = []

class Bullet:
    def __init__(self, x, y, angle, owner):
        self.x = x
        self.y = y
        self.angle = angle
        self.speed = 10
        self.owner = owner
    def update(self):
        import math
        rad = math.radians(self.angle + 90)
        self.x += math.cos(rad) * self.speed
        self.y -= math.sin(rad) * self.speed

async def handler(websocket):
    player_id = str(id(websocket))
    clients[player_id] = websocket
    players[player_id] = {'x': 400, 'y': 300, 'angle': 0}
    logger.info(f"Jugador conectado: {player_id}")
    try:
        async for msg in websocket:
            data = json.loads(msg)
            if data['type'] == 'move':
                players[player_id]['x'] = data['x']
                players[player_id]['y'] = data['y']
                players[player_id]['angle'] = data['angle']
            elif data['type'] == 'shoot':
                bullets.append(Bullet(data['x'], data['y'], data['angle'], player_id))
                logger.info(f"Bala creada por {player_id}: x={data['x']}, y={data['y']}, angle={data['angle']}")
    except Exception as e:
        logger.error(f"Error en handler de {player_id}: {e}")
    finally:
        logger.info(f"Jugador desconectado: {player_id}")
        del clients[player_id]
        del players[player_id]

async def game_loop():
    while True:
        for bullet in bullets[:]:
            bullet.update()
            if (bullet.x < 0 or bullet.x > 800 or bullet.y < 0 or bullet.y > 600):
                bullets.remove(bullet)
        state = {
            'players': players,
            'bullets': [
                {'x': b.x, 'y': b.y, 'angle': b.angle, 'owner': b.owner} for b in bullets
            ]
        }
        msg = json.dumps(state)
        for ws in clients.copy().values():
            try:
                await ws.send(msg)
            except Exception as e:
                logger.error(f"Error enviando estado a cliente: {e}")
        await asyncio.sleep(TICK_RATE)

async def main():
    logger.info(f"Servidor WebSocket en ws://0.0.0.0:{PORT}")
    async with websockets.serve(handler, "0.0.0.0", PORT):
        await game_loop()

if __name__ == "__main__":
    logger.add("server.log", rotation="10 MB")
    asyncio.run(main())

