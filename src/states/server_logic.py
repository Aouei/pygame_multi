import math
import random
from websockets import ClientConnection
from loguru import logger


from states.server_state import State
from enums import MESSAGES, ROLE, STATE, COLLISIONS
from entities import Player, Geometry, Live, Bullet, Ship


def check_intersection_by_radius(obj1, obj2):
    """
    Comprueba si dos objetos intersectan basándose en sus posiciones y radios.
    Se asume que cada objeto tiene los atributos 'x', 'y' y 'radius'.
    """
    dx = obj1.x - obj2.x
    dy = obj1.y - obj2.y
    distance = math.hypot(dx, dy)
    return distance <= (obj1.radius + obj2.radius)

class Logic:    
    STATE : State =  State()

    def __init__(self) -> None:
        self.colddown = 0
        self.colddown_max = 20
        self.colddown_step = 0.1

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
                                        pos = Geometry(x = x, y = y, radius = 25),
                                        live = Live(5))

    def __try_move(self, id : int, data : dict):
        dx, dy, state = data['dx'], data['dy'], data['state']

        player = self.STATE.PLAYERS[id]
        new_pos = Geometry(player.pos.x, player.pos.y, player.pos.radius)
        new_pos.x += dx
        new_pos.y += dy

        player.state = STATE(state)
        if not self.STATE.MAP.is_collision(new_pos, COLLISIONS.PLAYER):
            player.pos = new_pos

    def __new_bullet(self, id : int, data : dict):
        player = self.STATE.PLAYERS[id]

        role, dx, dy = *[ data[key] for key in ['role', 'dx', 'dy'] ], 
        pos = player.pos
        x, y = pos.x + dx * self.STATE.BULLET_VELOCITY, pos.y + dy * self.STATE.BULLET_VELOCITY
        
        self.STATE.BULLETS.append(Bullet(x, y, dx, dy, ROLE(role)))

    def __move_bullets(self):
        for bullet in self.STATE.BULLETS[::]:
            new_x = bullet.x + bullet.dx * self.STATE.BULLET_VELOCITY
            new_y = bullet.y + bullet.dy * self.STATE.BULLET_VELOCITY

            for ship in self.STATE.SHIPS.copy():
                if check_intersection_by_radius(bullet, ship) and not ship.path:
                    ship.live -= 1
                    if ship.live <= 0:
                        self.STATE.SHIPS.remove(ship) 
                    self.STATE.BULLETS.remove(bullet)
                    break
            else:
                if self.STATE.MAP.is_collision(Geometry(new_x, new_y, bullet.radius), COLLISIONS.BULLET):
                    self.STATE.BULLETS.remove(bullet)
                else:
                    bullet.x = new_x
                    bullet.y = new_y

    def __check_round(self):
        if self.STATE.SHIPS:
            return

        if self.colddown < self.colddown_max:
            self.colddown += self.colddown_step
            return

        self.colddown = 0
        map_data  = self.STATE.MAP
        TILE      = map_data.TILE_SIZE
        _DELTA    = {STATE.UP:(0,-1), STATE.DOWN:(0,1), STATE.LEFT:(-1,0), STATE.RIGHT:(1,0)}

        n       = min(self.STATE.MAX_SHIPS,
                      len(map_data.ship_spawn_tiles),
                      len(map_data.disembark_tiles))
        spawns  = random.sample(map_data.ship_spawn_tiles, n)   # list of (col, row)
        targets = random.sample(map_data.disembark_tiles,  n)   # list of (world_x, world_y)

        for (scol, srow), (tx, ty) in zip(spawns, targets):
            sx = scol * TILE + TILE // 2
            sy = srow * TILE + TILE // 2

            path = map_data.find_path(sx, sy, tx, ty, COLLISIONS.SHIP)

            target_x, target_y = sx, sy
            if path:
                dcol, drow = _DELTA[path[0]]
                target_x   = (scol + dcol) * TILE + TILE // 2
                target_y   = (srow + drow) * TILE + TILE // 2

            self.STATE.SHIPS.append(
                Ship(x=sx, y=sy, path=path, target_x=target_x, target_y=target_y)
            )

    def __move_ships(self):
        TILE   = self.STATE.MAP.TILE_SIZE
        _DELTA = {STATE.UP:(0,-1), STATE.DOWN:(0,1), STATE.LEFT:(-1,0), STATE.RIGHT:(1,0)}

        for ship in list(self.STATE.SHIPS):
            if ship.path:
                ship.state = ship.path[0]

                dx   = ship.target_x - ship.x
                dy   = ship.target_y - ship.y
                dist = math.hypot(dx, dy)

                if dist <= ship.speed:
                    # Llega al waypoint: snap y avanza en el path
                    ship.x = ship.target_x
                    ship.y = ship.target_y
                    ship.path.pop(0)

                    if ship.path:
                        dcol, drow  = _DELTA[ship.path[0]]
                        cur_col     = ship.x // TILE
                        cur_row     = ship.y // TILE
                        ship.target_x = (cur_col + dcol) * TILE + TILE // 2
                        ship.target_y = (cur_row + drow) * TILE + TILE // 2
                else:
                    ship.x += int(dx / dist * ship.speed)
                    ship.y += int(dy / dist * ship.speed)

    def tick(self):
        self.__check_round()
        self.__move_bullets()
        self.__move_ships()


    def serialize(self):
        return { 
                'players' : {            
                                id : player.dump() for id, player in self.STATE.PLAYERS.items() 
                            },
                'bullets' : [ bullet.dump() for bullet in self.STATE.BULLETS ],
                'ships' : [ ship.dump() for ship in self.STATE.SHIPS ],
               }