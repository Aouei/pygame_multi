import websockets
import asyncio
import pygame
import json

from loguru import logger

import messages
from enums import MESSAGES
from server_state.logic import Logic


pygame.init()

class Server:
    TICK_RATE = 20
    LOGIC = Logic()


    async def handle_client(self, socket):
        ID = self.LOGIC.new_player(socket)
        # TODO: handle ID = -1
        try:
            await messages.hello(ID, socket)
            logger.info(f"Sended Hello to player {ID}")

            async for message in socket:
                data = json.loads(message)
                self.LOGIC.handle_message(ID, data)

        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            self.LOGIC.remove_player(ID)

    # En server.py
    async def loop(self):
        interval = 1.0 / self.TICK_RATE
        while True:
            await asyncio.sleep(interval)
            if not self.LOGIC.CLIENTS:
                continue

            message = json.dumps({
                'type': MESSAGES.PLAYERS_UPDATE.value,
                'players': self.LOGIC.get_players()
            })

            logger.info(f"Sended UPDATE to players {message}")
            websockets.broadcast(self.LOGIC.CLIENTS.values(), message)

async def main():
    server = Server()

    logger.info(f"Server running")
    async with websockets.serve(server.handle_client, "0.0.0.0", 25565):
        await server.loop()


asyncio.run(main())
