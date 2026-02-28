import math
import random
from websockets import ClientConnection
from loguru import logger


from states.server_state import State
from enums import MESSAGES, ROLE, STATE, COLLISIONS
from entities import Player, Geometry, Bullet, Ship, Counter
from factories import TILE_SIZE


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
        self.spawn_timer = Counter(seconds=10)

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
        self.STATE.PLAYERS[id] = Player(role = ROLE(data['role']), x = x, y = y)

    def __try_move(self, id : int, data : dict):
        dx, dy, state = data['dx'], data['dy'], data['state']

        player = self.STATE.PLAYERS[id]
        new_x = player.x + dx
        new_y = player.y + dy

        player.state = STATE(state)
        if not self.STATE.MAP.is_collision(Geometry(new_x, new_y, player.radius), COLLISIONS.PLAYER):
            player.x = new_x
            player.y = new_y

    def __new_bullet(self, id : int, data : dict):
        player = self.STATE.PLAYERS[id]

        role, dx, dy = *[ data[key] for key in ['role', 'dx', 'dy'] ], 
        x, y = player.x + dx * self.STATE.BULLET_VELOCITY, player.y + dy * self.STATE.BULLET_VELOCITY
        
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
            self.spawn_timer.reset()
            return

        if not self.spawn_timer.tick():
            return

        _DELTA    = {STATE.UP:(0,-1), STATE.DOWN:(0,1), STATE.LEFT:(-1,0), STATE.RIGHT:(1,0)}

        n       = min(self.STATE.MAX_SHIPS,
                      len(self.STATE.MAP.ship_spawn_tiles),
                      len(self.STATE.MAP.disembark_tiles))
        spawns  = random.sample(self.STATE.MAP.ship_spawn_tiles, n)   # list of (col, row)
        targets = random.sample(self.STATE.MAP.disembark_tiles,  n)   # list of (world_x, world_y)

        for (scol, srow), (tx, ty) in zip(spawns, targets):
            sx = scol * TILE_SIZE + TILE_SIZE // 2
            sy = srow * TILE_SIZE + TILE_SIZE // 2

            path = self.STATE.MAP.find_path(sx, sy, tx, ty, COLLISIONS.SHIP)

            target_x, target_y = sx, sy
            if path:
                dcol, drow = _DELTA[path[0]]
                target_x   = (scol + dcol) * TILE_SIZE + TILE_SIZE // 2
                target_y   = (srow + drow) * TILE_SIZE + TILE_SIZE // 2

            self.STATE.SHIPS.append(
                Ship(x=sx, y=sy, path=path, target_x=target_x, target_y=target_y)
            )

    def __move_ships(self):
        _DELTA = {STATE.UP:(0,-1), STATE.DOWN:(0,1), STATE.LEFT:(-1,0), STATE.RIGHT:(1,0)}

        for ship in list(self.STATE.SHIPS):
            if ship.path:
                ship.state = ship.path[0]

                dx   = ship.target_x - ship.x
                dy   = ship.target_y - ship.y
                dist = math.hypot(dx, dy)

                if dist <= ship.speed:
                    ship.x = ship.target_x
                    ship.y = ship.target_y
                    ship.path.pop(0)

                    if ship.path:
                        dcol, drow  = _DELTA[ship.path[0]]
                        cur_col     = ship.x // TILE_SIZE
                        cur_row     = ship.y // TILE_SIZE
                        ship.target_x = (cur_col + dcol) * TILE_SIZE + TILE_SIZE // 2
                        ship.target_y = (cur_row + drow) * TILE_SIZE + TILE_SIZE // 2
                else:
                    ship.x += int(dx / dist * ship.speed)
                    ship.y += int(dy / dist * ship.speed)

    def __spawn_enemies(self):
        pass

    def tick(self):
        if self.STATE.CLIENTS:
            self.__check_round()
            self.__move_ships()
            self.__move_bullets()

    def serialize(self):
        return { 
                'players' : {            
                                id : player.dump() for id, player in self.STATE.PLAYERS.items() 
                            },
                'bullets' : [ bullet.dump() for bullet in self.STATE.BULLETS ],
                'ships' : [ ship.dump() for ship in self.STATE.SHIPS ],
               }