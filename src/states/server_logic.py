from websockets import ClientConnection

from states.server_state import State
from enums import MESSAGES, ROLE, STATE
from _entities import Player, Geometry, Live


class Logic:
    STATE : State =  State()

    @property
    def CLIENTS(self):
        return self.STATE.CLIENTS
    
    def new_player(self, socket : ClientConnection):
        new_id = self.STATE.available_ids[0]
        if new_id >= 0:
            self.STATE.CLIENTS[new_id] = socket

        return new_id
    
    def remove_player(self, id : int):
        self.STATE.CLIENTS.pop(id)
        self.STATE.PLAYERS.pop(id)

    def handle_message(self, id : int, data : dict):
        message_type = MESSAGES(data['type'])

        if message_type == MESSAGES.ROLE:
            self.__set_player_class(id, data)
        elif message_type == MESSAGES.WISH_MOVE:
            self.__try_move(id, data)

    def __set_player_class(self, id : int, data : dict):
        x, y = self.STATE.MAP.spawn()
        self.STATE.PLAYERS[id] = Player(role = ROLE(data['role']),
                                        pos = Geometry(x = x, y = y, radius = 32),
                                        live = Live(5))

    def __try_move(self, id : int, data : dict):
        dx, dy, state = data['dx'], data['dy'], data['state']

        player = self.STATE.PLAYERS[id]
        new_pos = Geometry(player.pos.x, player.pos.y, player.pos.radius)
        new_pos.x += dx
        new_pos.y += dy

        player.state = STATE(state)
        if not self.STATE.MAP.is_collision(new_pos):
            player.pos = new_pos

    def get_players(self):
        return { id : player.dump() for id, player in self.STATE.PLAYERS.items() }