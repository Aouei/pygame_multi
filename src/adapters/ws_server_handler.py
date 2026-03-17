import json
import traceback

import websockets
from loguru import logger

import adapters.messages as messages
from adapters.messages import MESSAGES
from use_cases.server_session import ServerSession


async def handle_client(socket, session: ServerSession):
    ID = session.new_player(socket)
    # TODO: handle ID = -1
    try:
        await messages.hello(ID, socket)
        logger.info(f"Sended Hello to player {ID}")

        async for message in socket:
            data = json.loads(message)
            result = session.handle_message(ID, data)
            if result == "quit":
                await messages.quit(session.CLIENTS[ID])
            elif result == "shut_down":
                await messages.quit(session.CLIENTS[ID])
                session.running = False

    except websockets.exceptions.ConnectionClosed:
        pass
    except Exception:
        logger.error(
            f"Unhandled exception for player {ID}: {traceback.format_exc()}"
        )
    finally:
        session.remove_player(ID)
