import random
from websockets import ClientConnection

import paths
from maps import Map
from typing import Mapping
from enums import PLAYER_CLASS, STATE, MESSAGES
from entities.player import Player

PLAYER_SIZE = 64
TILE_SIZE = 64
SPAWN_CODE = 8

PLAYERS = {
    PLAYER_CLASS.MAGE, Player(None, paths.PLAYER_DIR, PLAYER_CLASS.MAGE)
}

class ServerState:
    PLAYER_SIZE = 64
    TILE_SIZE = 64
    IDs = {0, 1, 2, 3}
    MAP = Map(paths.MAP_PATH)

    def __init__(self) -> None:
        self.players : dict[int, Player] = {}
        self.clients : dict[int, ClientConnection ] = {}

    @property
    def available_ids(self):
        return list(self.IDs.difference(self.clients.keys()))

    def new_player(self, socket : ClientConnection):
        new_id = self.available_ids[0] if self.available_ids else -1

        if new_id is not None:
            self.clients[new_id] = socket

        return new_id
    
    def remove_player(self, id : int):
        self.clients.pop(id)
        self.players.pop(id)

    def handle_message(self, id : int, data : dict):
        message_type = MESSAGES(data['type'])

        if message_type == MESSAGES.PLAYER_CLASS:
            self.__set_player_class(id, data)
        elif message_type == MESSAGES.WISH_MOVE:
            self.__try_move(id, data)

    def __set_player_class(self, id : int, data : dict):
        type = PLAYER_CLASS(data['class'])
        self.players[id] = Player(None, paths.PLAYER_DIR, type)
        self.players[id].move(*self.MAP.spawn(), STATE.DOWN.value)

    def __try_move(self, id : int, data : dict):
        dx, dy, state = data['dx'], data['dy'], data['state']
        player = self.players[id]
        x, y, = player.x, player.y

        if not self.MAP.is_collision(x + dx, y + dy, player.mask):
            player.move(x + dx, y + dy, state)

    def get_players(self):
        return { id : player.dump() for id, player in self.players.items() }

class ClientState:
    MAP = Map(paths.MAP_PATH)
    PLAYERS = {
        type_class : Player(None, paths.PLAYER_DIR, type_class) for type_class in [PLAYER_CLASS.ARCHER, 
                                                                                   PLAYER_CLASS.FARMER, 
                                                                                   PLAYER_CLASS.MAGE, 
                                                                                   PLAYER_CLASS.MUSKETEER]
    }

    COLORS = {
        0 : (0, 0, 0),
        1 : (0, 0, 255),
        2 : (0, 255, 0),
        3 : (255, 0, 0),
    }
    
    def __init__(self) -> None:
        pass

    def draw(self, surface, dx, dy, data : dict):
        x, y, state, type_class = list(data.values())
        type_class = PLAYER_CLASS(type_class)

        player = self.PLAYERS[type_class]
        player.move(x, y, state)
        player.draw(surface, dx, dy)