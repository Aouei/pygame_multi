import math
import random
from websockets import ClientConnection
from loguru import logger


from states.server_state import State
from enums import MESSAGES, ROLE, STATE, COLLISIONS
from entities import Player, Geometry, Bullet, Ship, Counter, Enemy
from factories import TILE_SIZE, ENEMY_VARIANTS
from protocols import LivingEntity


def check_intersection_by_radius(obj1, obj2):
    """
    Comprueba si dos objetos intersectan basándose en sus posiciones y radios.
    Se asume que cada objeto tiene los atributos 'x', 'y' y 'radius'.
    """
    dx = obj1.x - obj2.x
    dy = obj1.y - obj2.y
    distance = math.hypot(dx, dy)
    return distance <= (obj1.radius + obj2.radius)


def check_collision_with_entities(obj, entities):
    for entity in entities:
        if check_intersection_by_radius(obj, entity):
            return entity

    return False


class Logic:
    STATE: State = State()

    def __init__(self) -> None:
        self.spawn_ship_timer = Counter(seconds=30)
        self.spawn_enemy_timer = Counter(seconds=15)
        self.died_players: set = set()
        self.new_round: bool = False

    @property
    def CLIENTS(self):
        return self.STATE.CLIENTS

    def new_player(self, socket: ClientConnection):
        new_id = self.STATE.available_ids[0]
        if new_id >= 0:
            self.STATE.CLIENTS[new_id] = socket

        return new_id

    def remove_player(self, id: int):
        if id in self.STATE.CLIENTS:
            self.STATE.CLIENTS.pop(id)
        if id in self.STATE.PLAYERS:
            self.STATE.PLAYERS.pop(id)

    def handle_message(self, id: int, data: dict):
        message_type = MESSAGES(data["type"])

        if not id in self.STATE.CLIENTS:
            return MESSAGES.QUIT

        if message_type == MESSAGES.ROLE:
            logger.info("new player")
            self.__set_player_class(id, data)
        elif message_type == MESSAGES.WISH_MOVE:
            logger.info("move player")
            self.__try_move(id, data)
        elif message_type == MESSAGES.SHOT:
            logger.info("new bullet")
            self.__new_bullet(id, data)

    def __set_player_class(self, id: int, data: dict):
        x, y = self.STATE.MAP.spawn()

        self.STATE.PLAYERS[id] = Player(role=ROLE(data["role"]), x=x, y=y)

    def __try_move(self, id: int, data: dict):
        dx, dy, state = data["dx"], data["dy"], data["state"]

        player = self.STATE.PLAYERS[id]
        new_x = player.x + dx
        new_y = player.y + dy

        player.state = STATE(state)

        pos = Geometry(new_x, new_y, player.radius)
        collision = check_collision_with_entities(pos, self.STATE.SHIPS.copy())

        if not collision and not self.STATE.MAP.is_collision(pos, COLLISIONS.PLAYER):
            player.x = new_x
            player.y = new_y

    def __new_bullet(self, id: int, data: dict):
        player = self.STATE.PLAYERS[id]

        role, dx, dy = (*[data[key] for key in ["role", "dx", "dy"]],)
        x, y = (
            player.x + dx * self.STATE.BULLET_VELOCITY,
            player.y + dy * self.STATE.BULLET_VELOCITY,
        )

        self.STATE.BULLETS.append(Bullet(x, y, dx, dy, ROLE(role)))

    def __move_bullets(self):
        for bullet in self.STATE.BULLETS[::]:
            new_x = int(bullet.x + bullet.dx * self.STATE.BULLET_VELOCITY)
            new_y = int(bullet.y + bullet.dy * self.STATE.BULLET_VELOCITY)

            pos = Geometry(new_x, new_y, bullet.radius)

            shipcollision = check_collision_with_entities(pos, self.STATE.SHIPS.copy())
            if (
                shipcollision
                and isinstance(shipcollision, (LivingEntity))
                and not shipcollision.path
            ):
                shipcollision.live -= 1
                if shipcollision.live <= 0:
                    self.STATE.SHIPS.remove(shipcollision)

                self.STATE.BULLETS.remove(bullet)
            else:
                enemy_collision = check_collision_with_entities(
                    pos, self.STATE.ENEMIES.copy()
                )
                if enemy_collision and isinstance(enemy_collision, (LivingEntity)):
                    enemy_collision.live -= 1
                    if enemy_collision.live <= 0:
                        self.STATE.ENEMIES.remove(enemy_collision)

                    self.STATE.BULLETS.remove(bullet)
                elif self.STATE.MAP.is_collision(pos, COLLISIONS.BULLET):
                    self.STATE.BULLETS.remove(bullet)
                else:
                    bullet.x = new_x
                    bullet.y = new_y

    def __check_round(self):
        if self.STATE.SHIPS or self.STATE.ENEMIES:
            self.spawn_ship_timer.reset()
            return

        if not self.spawn_ship_timer.tick():
            return

        self.new_round = True
        _DELTA = {
            STATE.UP: (0, -1),
            STATE.DOWN: (0, 1),
            STATE.LEFT: (-1, 0),
            STATE.RIGHT: (1, 0),
        }

        n = min(
            self.STATE.MAX_SHIPS * len(self.STATE.PLAYERS),
            len(self.STATE.MAP.ship_spawn_tiles),
            len(self.STATE.MAP.disembark_tiles),
        )
        spawns = random.sample(self.STATE.MAP.ship_spawn_tiles, n)  # list of (col, row)
        targets = random.sample(
            self.STATE.MAP.disembark_tiles, n
        )  # list of (world_x, world_y)

        for (scol, srow), (tx, ty) in zip(spawns, targets):
            sx = scol * TILE_SIZE + TILE_SIZE // 2
            sy = srow * TILE_SIZE + TILE_SIZE // 2

            path = self.STATE.MAP.find_path(sx, sy, tx, ty, COLLISIONS.SHIP)

            target_x, target_y = sx, sy
            if path:
                dcol, drow = _DELTA[path[0]]
                target_x = (scol + dcol) * TILE_SIZE + TILE_SIZE // 2
                target_y = (srow + drow) * TILE_SIZE + TILE_SIZE // 2

            self.STATE.SHIPS.append(
                Ship(x=sx, y=sy, path=path, target_x=target_x, target_y=target_y)
            )

    def __move(self, enemies: list[Ship] | list[Enemy]):
        _DELTA = {
            STATE.UP: (0, -1),
            STATE.DOWN: (0, 1),
            STATE.LEFT: (-1, 0),
            STATE.RIGHT: (1, 0),
        }

        for enemy in list(enemies):
            if enemy.path:
                enemy.state = enemy.path[0]

                dx = enemy.target_x - enemy.x
                dy = enemy.target_y - enemy.y
                dist = math.hypot(dx, dy)

                if dist <= enemy.speed:
                    enemy.x = enemy.target_x
                    enemy.y = enemy.target_y
                    enemy.path.pop(0)

                    if enemy.path:
                        dcol, drow = _DELTA[enemy.path[0]]
                        cur_col = enemy.x // TILE_SIZE
                        cur_row = enemy.y // TILE_SIZE
                        enemy.target_x = (cur_col + dcol) * TILE_SIZE + TILE_SIZE // 2
                        enemy.target_y = (cur_row + drow) * TILE_SIZE + TILE_SIZE // 2
                else:
                    enemy.x += int(dx / dist * enemy.speed)
                    enemy.y += int(dy / dist * enemy.speed)

    def __spawn_enemies(self):
        _DELTA = {
            STATE.UP: (0, -1),
            STATE.DOWN: (0, 1),
            STATE.LEFT: (-1, 0),
            STATE.RIGHT: (1, 0),
        }

        for ship in self.STATE.SHIPS:
            if not ship.path and self.spawn_enemy_timer.tick():
                self.spawn_enemy_timer.reset()

                for _ in range(random.randint(1, self.STATE.MAX_ENEMIES)):
                    x, y = ship.x, ship.y
                    final_tx, final_ty = random.sample(
                        self.STATE.MAP.enemy_target_tiles, 1
                    )[0]
                    path = self.STATE.MAP.find_path(
                        x, y, final_tx, final_ty, COLLISIONS.ENEMY
                    )

                    target_x, target_y = x, y
                    if path:
                        dcol, drow = _DELTA[path[0]]
                        scol, srow = x // TILE_SIZE, y // TILE_SIZE
                        target_x = (scol + dcol) * TILE_SIZE + TILE_SIZE // 2
                        target_y = (srow + drow) * TILE_SIZE + TILE_SIZE // 2

                    enemy = Enemy(
                        x,
                        y,
                        path,
                        target_x=target_x,
                        target_y=target_y,
                        variant=random.randint(0, ENEMY_VARIANTS - 1),
                    )
                    self.STATE.ENEMIES.append(enemy)

    def __redirect_enemies(self):
        _DELTA = {
            STATE.UP: (0, -1),
            STATE.DOWN: (0, 1),
            STATE.LEFT: (-1, 0),
            STATE.RIGHT: (1, 0),
        }

        for enemy in self.STATE.ENEMIES:
            if not enemy.path:
                x, y = enemy.x, enemy.y
                final_tx, final_ty = random.sample(
                    self.STATE.MAP.enemy_target_tiles, 1
                )[0]
                path = self.STATE.MAP.find_path(
                    x, y, final_tx, final_ty, COLLISIONS.ENEMY
                )
                enemy.path = path

                if path:
                    dcol, drow = _DELTA[path[0]]
                    scol, srow = x // TILE_SIZE, y // TILE_SIZE
                    enemy.target_x = (scol + dcol) * TILE_SIZE + TILE_SIZE // 2
                    enemy.target_y = (srow + drow) * TILE_SIZE + TILE_SIZE // 2

    def __check_enemy_hit_with_player(self):

        for enemy in self.STATE.ENEMIES:
            for idd, player in self.STATE.PLAYERS.copy().items():
                if check_intersection_by_radius(enemy, player) and isinstance(
                    player, LivingEntity
                ):
                    player.live -= 1

                    if player.live <= 0:  # TODO: desconectar personaje
                        self.died_players.add(idd)

    def tick(self):
        self.new_round = False

        if self.STATE.CLIENTS:
        #     self.__check_round()
            # self.__move(self.STATE.SHIPS)
        #     self.__spawn_enemies()
        #     self.__redirect_enemies()
        #     self.__move(self.STATE.ENEMIES)
        #     self.__check_enemy_hit_with_player()
            self.__move_bullets()

        return self.died_players, self.new_round

    def serialize(self):
        return {
            "clients": len(self.STATE.CLIENTS),
            "players": {id: player.dump() for id, player in self.STATE.PLAYERS.items()},
            "bullets": [bullet.dump() for bullet in self.STATE.BULLETS],
            "ships": [ship.dump() for ship in self.STATE.SHIPS],
            "enemies": [enemy.dump() for enemy in self.STATE.ENEMIES],
        }
