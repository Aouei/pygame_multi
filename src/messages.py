import json

from websockets import ClientConnection
from enums import MESSAGES
from states import ServerState


def hello(id : int, socket : ClientConnection):
    message = {
        'type' : MESSAGES.HELLO.value,
        'id' : id
    }

    return socket.send(json.dumps(message))

def player_class(type : str, socket : ClientConnection):
    message = {
        'type' : MESSAGES.PLAYER_CLASS.value,
        'class' : type
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


def players_state(state : ServerState, socket):
    message = {
        'type' : MESSAGES.PLAYERS_UPDATE.value,
        'players' : state.get_players()
    }
    return socket.send(json.dumps(message))