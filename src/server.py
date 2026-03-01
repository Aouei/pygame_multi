import websockets
import asyncio
import pygame
import json

from loguru import logger

import messages
from enums import MESSAGES
from states.server_logic import Logic


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
                if MESSAGES.QUIT == self.LOGIC.handle_message(ID, data):
                    await messages.quit(self.LOGIC.CLIENTS[ID])

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

            died_players, new_round = self.LOGIC.tick()

            if new_round:
                messages.round_start(list(self.LOGIC.CLIENTS.values()))

            for idd in died_players.copy():
                if idd in self.LOGIC.CLIENTS:
                    await messages.quit(self.LOGIC.CLIENTS[idd])
                    self.LOGIC.remove_player(idd)
                self.LOGIC.died_players.discard(idd)

            message = self.LOGIC.serialize()
            logger.info(f"Sended UPDATE to players {message}")
            messages.update_clients(message, list(self.LOGIC.CLIENTS.values()))

async def main():
    server = Server()

    logger.info(f"Server running")
    async with websockets.serve(server.handle_client, "0.0.0.0", 25565):
        await server.loop()


asyncio.run(main())
