import asyncio
import os

import websockets
from loguru import logger
from http import HTTPStatus

import adapters.messages as messages
from adapters.ws_server_handler import handle_client
from use_cases.server_session import ServerSession


async def health_check(connection, request):
    if request.headers.get("Upgrade", "").lower() != "websocket":
        return connection.respond(HTTPStatus.OK, "OK\n")


async def _game_loop(session: ServerSession):
    interval = 1.0 / session.TICK_RATE
    while session.running:
        await asyncio.sleep(interval)
        if not session.CLIENTS:
            session.reset()
            continue

        died_players = session.tick()

        for idd in list(died_players):
            if idd in session.CLIENTS:
                try:
                    await messages.quit(session.CLIENTS[idd])
                except websockets.exceptions.ConnectionClosed:
                    pass
                session.remove_player(idd)
            session.died_players.discard(idd)

        snapshot = session.serialize()
        logger.info(f"Sended UPDATE to players {snapshot}")
        messages.update_clients(snapshot, list(session.CLIENTS.values()))


async def run(session: ServerSession):
    port = int(os.environ.get("PORT", 25565))
    logger.info(f"Server running on port {port}")
    async with websockets.serve(
        lambda socket: handle_client(socket, session),
        "0.0.0.0",
        port,
        process_request=health_check,
    ):
        await _game_loop(session)


async def main():
    await run(ServerSession())


if __name__ == "__main__":
    asyncio.run(main())
