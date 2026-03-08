import paths
from map import MapRender
from enums import ROLE
from factories import load_bullet, load_player, load_ship, load_enemy, load_castle
from entities import Player, Ship, Bullet, Enemy, Castle


PLAYER_SIZE = 64
TILE_SIZE = 64
SPAWN_CODE = 8


class State:
    _MAP = MapRender(paths.MAP_PATH, scale = 4)
    _PLAYERS = {role: load_player(role, PLAYER_SIZE) for role in ROLE}
    _BULLETS = load_bullet()
    _SHIPS = load_ship()
    _ENEMIES = load_enemy()
    _CASTLE = load_castle()

    _COLORS = {
        0: (0, 0, 0),
        1: (0, 0, 255),
        2: (0, 255, 0),
        3: (255, 0, 0),
    }

    def __init__(self) -> None:
        self.received_players: dict[int, Player] = {}
        self.received_bullets: list[Bullet] = []
        self.received_ships: list[Ship] = []
        self.received_enemies: list[Enemy] = []
        self._current_player: Player = Player(ROLE.MAGE, 0, 0)
        self._ID = -1

    @property
    def castles(self) -> dict:
        return self._MAP.map.castles

    @property
    def castle_image(self):
        return self._CASTLE
    
    @property
    def MAP(self):
        return self._MAP

    @property
    def PLAYERS(self):
        return self._PLAYERS

    @property
    def BULLETS(self):
        return self._BULLETS

    @property
    def SHIPS(self):
        return self._SHIPS

    @property
    def ENEMIES(self):
        return self._ENEMIES

    @property
    def COLORS(self):
        return self._COLORS

    @property
    def player(self):
        return self._current_player

    @player.setter
    def player(self, value):
        self._current_player = value

    @property
    def ID(self):
        return self._ID

    @ID.setter
    def ID(self, value):
        self._ID = value
