import json

from websockets import ClientConnection, broadcast
from enums import MESSAGES, ROLE


def hello(id : int, socket : ClientConnection):
    message = {
        'type' : MESSAGES.HELLO.value,
        'id' : id
    }

    return socket.send(json.dumps(message))

def set_role(role : ROLE, socket : ClientConnection):
    message = {
        'type' : MESSAGES.ROLE.value,
        'role' : role.value
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

def wish_shot(role : ROLE, dx : int, dy : int, socket : ClientConnection):
    message = {
        'type' : MESSAGES.SHOT.value,
        'dx' : dx,
        'dy' : dy,
        'role' : role.value,
    }

    return socket.send(json.dumps(message))

def update_clients(data : dict, sockets : list[ClientConnection]):
    message = json.dumps({
        'type': MESSAGES.PLAYERS_UPDATE.value,
        **data
    })

    broadcast(sockets, message)