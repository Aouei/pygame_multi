from websockets import ClientConnection


import paths

from _entities import Player
from maps import Map


class State:
    IDS = {0, 1, 2, 3}
    CLIENTS : dict[int, ClientConnection] = {}
    PLAYERS : dict[int, Player] = {}
    MAP : Map = Map(paths.MAP_PATH)

    @property
    def available_ids(self):
        diff = list(self.IDS.difference(self.CLIENTS.keys()))
        return [-1] if not diff else diff