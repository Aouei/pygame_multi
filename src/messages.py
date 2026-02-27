import json

from websockets import ClientConnection
from enums import MESSAGES


def hello(id : int, socket : ClientConnection):
    message = {
        'type' : MESSAGES.HELLO.value,
        'id' : id
    }

    return socket.send(json.dumps(message))

def player_class(role : str, socket : ClientConnection):
    message = {
        'type' : MESSAGES.PLAYER_CLASS.value,
        'role' : role
    }

    return socket.send(json.dumps(message))

def wish_move(dx : int, dy : int, state : str, socket : ClientConnection):
    message = {
        'type' : MESSAGES.WISH_MOVE.value,
        'dx' : dx,
        'dy' : dy,
        'state' : state,
    }

    return socket.send(json.dumps(message))