import websockets
import asyncio
import pygame
import json

from loguru import logger

import messages
from enums import MESSAGES
from states import ServerState

pygame.init()

class Server:
    TICK_RATE = 20

    def __init__(self) -> None:
        self.state = ServerState()

    async def handle_client(self, socket):
        ID = self.state.new_player(socket)
        
        try:
            await messages.hello(ID, socket)
            logger.info(f"Sended Hello to player {ID}")

            async for message in socket:
                data = json.loads(message)
                self.state.handle_message(ID, data)

        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            self.state.remove_player(ID)

    # En server.py
    async def loop(self):
        interval = 1.0 / self.TICK_RATE
        while True:
            await asyncio.sleep(interval)
            if not self.state.clients:
                continue

            message = json.dumps({
                'type': MESSAGES.PLAYERS_UPDATE.value,
                'players': self.state.get_players()
            })
            websockets.broadcast(self.state.clients.values(), message)

async def main():
    server = Server()

    logger.info(f"Server running")
    async with websockets.serve(server.handle_client, "0.0.0.0", 25565):
        await server.loop()


asyncio.run(main())
