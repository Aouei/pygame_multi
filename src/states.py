from websockets import ClientConnection

import paths
from maps import Map
from enums import PLAYER_CLASS, STATE, MESSAGES
from entities.player import Player
from factories import load_bullet


PLAYER_SIZE = 64
TILE_SIZE = 64
SPAWN_CODE = 8

PLAYERS = {
    PLAYER_CLASS.MAGE, Player(PLAYER_CLASS.MAGE)
}

class ClientState:
    MAP = Map(paths.MAP_PATH)
    PLAYERS = {
        type_class : Player(type_class) for type_class in PLAYER_CLASS
    }
    BULLETS = load_bullet()

    COLORS = {
        0 : (0, 0, 0),
        1 : (0, 0, 255),
        2 : (0, 255, 0),
        3 : (255, 0, 0),
    }
    
    def __init__(self) -> None:
        pass

    def draw_player(self, surface, dx, dy, data : dict):
        x, y, state, type_class = list(data.values())
        type_class = PLAYER_CLASS(type_class)

        player = self.PLAYERS[type_class]
        player.move(x, y, state)
        player.draw(surface, dx, dy)