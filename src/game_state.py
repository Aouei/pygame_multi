import random
import numpy as np

PLAYER_SIZE = 64
TILE_SIZE = 64
SPAWN_CODE = 8

class GameState:
    def __init__(self, map_data, solid_positions, is_collision_func):
        self.players = {}
        self.next_player_id = 1
        self.clients = {}  # websocket -> player_id
        self.map_data = map_data
        self.solid_positions = solid_positions
        self.is_collision = is_collision_func

    def add_client(self, websocket):
        player_id = self.next_player_id
        self.next_player_id += 1
        self.clients[websocket] = player_id
        return player_id

    def remove_client(self, websocket):
        player_id = self.clients.pop(websocket, None)
        if player_id is not None:
            self.players.pop(player_id, None)

    def handle_start(self, player_id, data):
        spawn_tiles = []
        for i, row in enumerate(self.map_data):
            for j, col in enumerate(row):
                if col == SPAWN_CODE:
                    spawn_tiles.append((j, i))
        if spawn_tiles:
            j, i = random.choice(spawn_tiles)
            x = j * TILE_SIZE
            y = i * TILE_SIZE
        else:
            x = data["x"] // 2
            y = data["y"] // 2
        self.players[player_id] = {
            "x_lim": data["x"],
            "y_lim": data["y"],
            "x": x,
            "y": y,
            'state': 'up'
        }

    def handle_move(self, player_id, data):
        if player_id not in self.players:
            return
        p = self.players[player_id]
        new_x = int(p["x"] + data["dx"])
        new_y = int(p["y"] + data["dy"])
        if not self.is_collision(new_x + PLAYER_SIZE // 2, new_y + PLAYER_SIZE // 2, data['state']):
            p["x"] = new_x
            p["y"] = new_y
        else:
            p["x"] = int(p["x"] - data["dx"])
            p["y"] = int(p["y"] - data["dy"])

        p['state'] = data['state']

    def get_players(self):
        return self.players

    def get_player_id(self, websocket):
        return self.clients.get(websocket)
