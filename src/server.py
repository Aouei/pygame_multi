import websockets
import asyncio
import random
import json
import math

from websockets import ClientConnection
from loguru import logger

import paths
import messages
from enums import MESSAGES
from entities import Player, Bullet, Ship, Enemy
from map import MapData
from enums import MESSAGES, ROLE, STATE, COLLISIONS
from entities import Player, Geometry, Bullet, Ship, Counter, Enemy
from factories import ENEMY_VARIANTS
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


class Server:
    def __init__(self) -> None:
        self.TICK_RATE = 20
        self.IDS = {0, 1, 2, 3}
        self.CLIENTS: dict[int, ClientConnection] = {}
        self.PLAYERS: dict[int, Player] = {}
        self.BULLETS: list[Bullet] = []
        self.SHIPS: list[Ship] = []
        self.ENEMIES: list[Enemy] = []
        self.MAX_SHIPS: int = 5
        self.MAX_ENEMIES: int = 10
        self.BULLET_VELOCITY = 30
        self.INVULNERABLE_TICKS = 10
        self.MAP: MapData = MapData(paths.MAP_PATH, scale = 4)
        self.spawn_ship_timer = Counter(seconds=30)
        self.spawn_enemy_timer = Counter(seconds=5)
        self.died_players: set = set()
        self.new_round: bool = False
        self.DELTA = {
            STATE.UP: (0, -1),
            STATE.DOWN: (0, 1),
            STATE.LEFT: (-1, 0),
            STATE.RIGHT: (1, 0),
        }

    @property
    def available_ids(self):
        diff = list(self.IDS.difference(self.CLIENTS.keys()))
        return [-1] if not diff else diff
    

    def new_player(self, socket: ClientConnection):
        new_id = self.available_ids[0]
        if new_id >= 0:
            self.CLIENTS[new_id] = socket

        return new_id

    def remove_player(self, id: int):
        if id in self.CLIENTS:
            self.CLIENTS.pop(id)
        if id in self.PLAYERS:
            self.PLAYERS.pop(id)

    def handle_message(self, id: int, data: dict):
        message_type = MESSAGES(data["type"])

        if not id in self.CLIENTS:
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
        x, y = self.MAP.spawn()

        self.PLAYERS[id] = Player(role=ROLE(data["role"]), x=x, y=y)

    def __try_move(self, id: int, data: dict):
        dx, dy, state = data["dx"], data["dy"], data["state"]

        player = self.PLAYERS[id]
        new_x = player.x + dx
        new_y = player.y + dy

        player.state = STATE(state)

        pos = Geometry(new_x, new_y, player.radius)
        collision = check_collision_with_entities(pos, self.SHIPS.copy())
        castle_collision = check_collision_with_entities(pos, self.MAP.castles.values())

        if not collision and not castle_collision and not self.MAP.is_collision(pos, COLLISIONS.PLAYER):
            player.x = new_x
            player.y = new_y

    def __new_bullet(self, id: int, data: dict):
        player = self.PLAYERS[id]

        role, dx, dy = (*[data[key] for key in ["role", "dx", "dy"]],)
        x, y = (
            player.x + dx * self.BULLET_VELOCITY,
            player.y + dy * self.BULLET_VELOCITY,
        )

        self.BULLETS.append(Bullet(x, y, dx, dy, ROLE(role)))

    def __move_bullets(self):
        for bullet in self.BULLETS[::]:
            new_x = int(bullet.x + bullet.dx * self.BULLET_VELOCITY)
            new_y = int(bullet.y + bullet.dy * self.BULLET_VELOCITY)

            pos = Geometry(new_x, new_y, bullet.radius)

            shipcollision = check_collision_with_entities(pos, self.SHIPS.copy())
            if (
                shipcollision
                and isinstance(shipcollision, (LivingEntity))
                and not shipcollision.path
            ):
                shipcollision.live -= bullet.damage
                if shipcollision.live <= 0:
                    self.SHIPS.remove(shipcollision)

                self.BULLETS.remove(bullet)
            else:
                enemy_collision = check_collision_with_entities(
                    pos, self.ENEMIES.copy()
                )
                if enemy_collision and isinstance(enemy_collision, (LivingEntity)):
                    enemy_collision.live -= bullet.damage
                    if enemy_collision.live <= 0:
                        self.ENEMIES.remove(enemy_collision)

                    self.BULLETS.remove(bullet)
                elif check_collision_with_entities(pos, self.MAP.castles.values()):
                    self.BULLETS.remove(bullet)
                elif self.MAP.is_collision(pos, COLLISIONS.BULLET):
                    self.BULLETS.remove(bullet)
                else:
                    bullet.x = new_x
                    bullet.y = new_y

    def __check_round(self):
        if self.SHIPS or self.ENEMIES:
            self.spawn_ship_timer.reset()
            return

        if not self.spawn_ship_timer.tick():
            self.__recover_player_health()
            return

        self.new_round = True

        n = min(
            self.MAX_SHIPS * len(self.PLAYERS),
            len(self.MAP.ship_spawn_tiles),
            len(self.MAP.disembark_tiles),
        )
        spawns = random.sample(self.MAP.ship_spawn_tiles, n)  # list of (col, row)
        targets = random.sample(
            self.MAP.disembark_tiles, n
        )  # list of (world_x, world_y)

        for (scol, srow), (tcol, trow) in zip(spawns, targets):
            path = self.MAP.find_path(scol, srow, tcol, trow, COLLISIONS.SHIP)

            sx, sy = self.MAP.tile_center(scol, srow)
            target_x, target_y = sx, sy
            if path:
                dcol, drow = self.DELTA[path[0]]
                target_x, target_y = self.MAP.tile_center(scol + dcol, srow + drow)

                self.SHIPS.append(
                    Ship(x=sx, y=sy, path=path, target_x=target_x, target_y=target_y)
                )

    def __move(self, enemies: list[Ship] | list[Enemy]):
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
                        dcol, drow = self.DELTA[enemy.path[0]]
                        cur_col, cur_row = self.MAP.pixel_to_tile(enemy.x, enemy.y)
                        enemy.target_x, enemy.target_y = self.MAP.tile_center(cur_col + dcol, cur_row + drow)
                else:
                    enemy.x += int(dx / dist * enemy.speed)
                    enemy.y += int(dy / dist * enemy.speed)

    def __spawn_enemies(self):
        for ship in self.SHIPS:
            if not ship.path and self.spawn_enemy_timer.tick():
                self.spawn_enemy_timer.reset()

                for _ in range(random.randint(1, self.MAX_ENEMIES)):
                    x, y = ship.x, ship.y
                    tcol, trow = random.sample(list(self.MAP.enemy_target_tiles), 1)[0]
                    scol, srow = self.MAP.pixel_to_tile(x, y)
                    path = self.MAP.find_path(scol, srow, tcol, trow, COLLISIONS.ENEMY)

                    target_x, target_y = x, y
                    if path:
                        dcol, drow = self.DELTA[path[0]]
                        target_x, target_y = self.MAP.tile_center(scol + dcol, srow + drow)

                        enemy = Enemy(
                            x,
                            y,
                            path,
                            target_x=target_x,
                            target_y=target_y,
                            variant=random.randint(0, ENEMY_VARIANTS - 1),
                        )
                        self.ENEMIES.append(enemy)

    def __redirect_enemies(self):
        for enemy in self.ENEMIES:
            if not enemy.path:
                x, y = enemy.x, enemy.y
                tcol, trow = random.sample(list(self.MAP.enemy_target_tiles), 1)[0]
                scol, srow = self.MAP.pixel_to_tile(x, y)
                path = self.MAP.find_path(scol, srow, tcol, trow, COLLISIONS.ENEMY)
                enemy.path = path

                if path:
                    dcol, drow = self.DELTA[path[0]]
                    enemy.target_x, enemy.target_y = self.MAP.tile_center(scol + dcol, srow + drow)

    def __check_enemy_hit_with_castle(self):
        for enemy in self.ENEMIES:
            for castle in self.MAP.castles.values():
                if check_intersection_by_radius(enemy, castle) and castle.invulnerable == 0:
                    castle.live -= enemy.damage
                    castle.invulnerable = self.INVULNERABLE_TICKS

        dead = [cid for cid, c in self.MAP.castles.items() if c.live <= 0]
        for cid in dead:
            self.MAP.remove_castle(cid)

    def __check_enemy_hit_with_player(self):

        for enemy in self.ENEMIES:
            for idd, player in self.PLAYERS.copy().items():
                if check_intersection_by_radius(enemy, player) and isinstance(
                    player, LivingEntity
                ) and player.invulnerable == 0:
                    player.live -= enemy.damage
                    player.invulnerable = self.INVULNERABLE_TICKS

                    if player.live <= 0:  # TODO: desconectar personaje
                        self.died_players.add(idd)

    def __tick_invulnerability(self):
        for player in self.PLAYERS.values():
            if player.invulnerable > 0:
                player.invulnerable -= 1
        for castle in self.MAP.castles.values():
            if castle.invulnerable > 0:
                castle.invulnerable -= 1

    def __recover_player_health(self):
        for player in self.PLAYERS.values():
            player.live = player.max_live

    def tick(self):
        self.new_round = False

        if self.CLIENTS:
            self.__tick_invulnerability()
            self.__check_round()
            self.__move(self.SHIPS)
            self.__spawn_enemies()
            self.__redirect_enemies()
            self.__move(self.ENEMIES)
            self.__check_enemy_hit_with_player()
            self.__check_enemy_hit_with_castle()
            self.__move_bullets()

            if self.PLAYERS and not self.MAP.castles:
                self.died_players.update(self.PLAYERS.keys())

        return self.died_players, self.new_round

    def serialize(self):
        return {
            "clients": len(self.CLIENTS),
            "players": {id: player.dump() for id, player in self.PLAYERS.items()},
            "bullets": [bullet.dump() for bullet in self.BULLETS],
            "ships": [ship.dump() for ship in self.SHIPS],
            "enemies": [enemy.dump() for enemy in self.ENEMIES],
            "castles": {id: castle.dump() for id, castle in self.MAP.castles.items()},
        }


    async def handle_client(self, socket):
        ID = self.new_player(socket)
        # TODO: handle ID = -1
        try:
            await messages.hello(ID, socket)
            logger.info(f"Sended Hello to player {ID}")

            async for message in socket:
                data = json.loads(message)
                if MESSAGES.QUIT == self.handle_message(ID, data):
                    await messages.quit(self.CLIENTS[ID])

        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            self.remove_player(ID)


    async def loop(self):
        interval = 1.0 / self.TICK_RATE
        while True:
            await asyncio.sleep(interval)
            if not self.CLIENTS:
                continue

            died_players, new_round = self.tick()

            if new_round:
                messages.round_start(list(self.CLIENTS.values()))

            for idd in died_players.copy():
                if idd in self.CLIENTS:
                    await messages.quit(self.CLIENTS[idd])
                    self.remove_player(idd)
                self.died_players.discard(idd)

            message = self.serialize()
            logger.info(f"Sended UPDATE to players {message}")
            messages.update_clients(message, list(self.CLIENTS.values()))


async def main():
    server = Server()

    logger.info(f"Server running")
    async with websockets.serve(server.handle_client, "0.0.0.0", 25565):
        await server.loop()


asyncio.run(main())