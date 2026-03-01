from websockets import ClientConnection


import paths

from entities import Player, Bullet, Ship, Enemy
from map import MapData


class State:
    IDS = {0, 1, 2, 3}
    CLIENTS : dict[int, ClientConnection] = {}
    PLAYERS : dict[int, Player] = {}
    BULLETS : list[Bullet] = []
    SHIPS : list[Ship] = []
    ENEMIES : list[Enemy] = []
    MAX_SHIPS : int = 5
    MAP : MapData = MapData(paths.MAP_L1_PATH, paths.MAP_L2_PATH)

    BULLET_VELOCITY = 30

    @property
    def available_ids(self):
        diff = list(self.IDS.difference(self.CLIENTS.keys()))
        return [-1] if not diff else diff