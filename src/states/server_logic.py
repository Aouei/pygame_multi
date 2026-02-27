from websockets import ClientConnection
from loguru import logger


from states.server_state import State
from enums import MESSAGES, ROLE, STATE
from entities import Player, Geometry, Live, Bullet


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
            logger.info('new player')
            self.__set_player_class(id, data)
        elif message_type == MESSAGES.WISH_MOVE:
            logger.info('move player')
            self.__try_move(id, data)
        elif message_type == MESSAGES.SHOT:
            logger.info('new bullet')
            self.__new_bullet(id, data)

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

    def __new_bullet(self, id : int, data : dict):
        player = self.STATE.PLAYERS[id]

        role, dx, dy = *[ data[key] for key in ['role', 'dx', 'dy'] ], 
        pos = player.pos
        new_pos = Geometry(pos.x + dx * self.STATE.BULLET_VELOCITY,
                           pos.y + dy * self.STATE.BULLET_VELOCITY,
                           radius = 16)
        
        self.STATE.BULLETS.append(Bullet(new_pos, dx, dy, ROLE(role)))

    def __move_bullets(self):
        for bullet in self.STATE.BULLETS[::]:
            new_pos = Geometry(bullet.pos.x, bullet.pos.y, bullet.pos.radius)
            new_pos.x += bullet.dx * self.STATE.BULLET_VELOCITY
            new_pos.y += bullet.dy * self.STATE.BULLET_VELOCITY

            if not self.STATE.MAP.is_collision(new_pos):
                bullet.pos = new_pos
            else:
                self.STATE.BULLETS.remove(bullet)

    def tick(self):
        self.__move_bullets()


    def serialize(self):
        return { 
                'players' : {            
                                id : player.dump() for id, player in self.STATE.PLAYERS.items() 
                            },
                'bullets' : [ bullet.dump() for bullet in self.STATE.BULLETS ]
               }