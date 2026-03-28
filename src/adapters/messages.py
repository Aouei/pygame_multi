import json
from enum import Enum

from websockets import ClientConnection, broadcast


class MESSAGES(Enum):
    HELLO = "hello"
    ROLE = "role"
    WISH_MOVE = "wish_mode"
    PLAYERS_UPDATE = "players_update"
    SHOT = "shot"
    QUIT = "quit"
    ROUND_START = "round_start"
    SHUT_DOWN = "shut_down"


def hello(id: int, socket: ClientConnection):
    message = {"type": MESSAGES.HELLO.value, "id": id}
    return socket.send(json.dumps(message))


def set_role(role, socket: ClientConnection):
    message = {"type": MESSAGES.ROLE.value, "role": role.value}
    return socket.send(json.dumps(message))


def wish_move(dx: int, dy: int, state: str, socket: ClientConnection):
    message = {
        "type": MESSAGES.WISH_MOVE.value,
        "dx": dx,
        "dy": dy,
        "state": state,
    }
    return socket.send(json.dumps(message))


def wish_shot(role, dx: float, dy: float, socket: ClientConnection):
    message = {
        "type": MESSAGES.SHOT.value,
        "dx": dx,
        "dy": dy,
        "role": role.value,
    }
    return socket.send(json.dumps(message))


def update_clients(snapshot, sockets: list[ClientConnection]):
    message = json.dumps({"type": MESSAGES.PLAYERS_UPDATE.value, **snapshot.to_wire()})
    broadcast(sockets, message)


def quit(socket: ClientConnection):
    message = {"type": MESSAGES.QUIT.value}
    return socket.send(json.dumps(message))


def round_start(sockets: list[ClientConnection]):
    message = json.dumps({"type": MESSAGES.ROUND_START.value})
    broadcast(sockets, message)


def shut_down(socket: ClientConnection):
    message = {"type": MESSAGES.SHUT_DOWN.value}
    return socket.send(json.dumps(message))
