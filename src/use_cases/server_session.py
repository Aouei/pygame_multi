import random
import math

from domain.entities import Player, Bullet, Ship, Enemy, Counter, Geometry
from domain.enums import ROLE, STATE, COLLISIONS
from domain.protocols import LivingEntity
from domain.rules import check_intersection_by_radius, check_collision_with_entities


class ServerSession:
    """
    Lógica de juego autoritativa del servidor.
    Sin imports de pygame, asyncio ni websockets.
    """

    def __init__(self) -> None:
        self.TICK_RATE = 20
        self.IDS = {0, 1, 2, 3}
        self.MAX_SHIPS: int = 5
        self.MAX_ENEMIES: int = 5
        self.BULLET_VELOCITY = 30
        self.INVULNERABLE_TICKS = 10
        self.DELTA = {
            STATE.UP: (0, -1),
            STATE.DOWN: (0, 1),
            STATE.LEFT: (-1, 0),
            STATE.RIGHT: (1, 0),
        }
        self.spawn_ship_timer = Counter(seconds=30)
        self.spawn_enemy_timer = Counter(seconds=5)

        self.CLIENTS: dict[int, object] = {}
        self.running = True

        self.reset()

    def reset(self):
        import frameworks.paths as paths
        from frameworks.factories import MAP_SCALE
        from domain.map_data import MapData

        self.PLAYERS: dict[int, Player] = {}
        self.BULLETS: list[Bullet] = []
        self.SHIPS: list[Ship] = []
        self.ENEMIES: list[Enemy] = []
        self.MAP: MapData = MapData(paths.MAP_PATH, scale=MAP_SCALE)
        self.died_players: set = set()

    @property
    def available_ids(self):
        diff = list(self.IDS.difference(self.CLIENTS.keys()))
        return [-1] if not diff else diff

    def new_player(self, socket: object):
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
        msg_type = data["type"]

        if id not in self.CLIENTS:
            return "quit"

        if msg_type == "role":
            self.__set_player_class(id, data)
        elif msg_type == "wish_mode":
            self.__try_move(id, data)
        elif msg_type == "shot":
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

        if (
            not collision
            and not castle_collision
            and not self.MAP.is_collision(pos, COLLISIONS.PLAYER)
        ):
            player.x = new_x
            player.y = new_y

    def __new_bullet(self, id: int, data: dict):
        player = self.PLAYERS[id]
        role, dx, dy = data["role"], data["dx"], data["dy"]
        x = player.x + dx * self.BULLET_VELOCITY
        y = player.y + dy * self.BULLET_VELOCITY
        self.BULLETS.append(Bullet(x, y, dx, dy, ROLE(role)))

    def __move_bullets(self):
        for bullet in self.BULLETS[::]:
            new_x = int(bullet.x + bullet.dx * self.BULLET_VELOCITY)
            new_y = int(bullet.y + bullet.dy * self.BULLET_VELOCITY)

            pos = Geometry(new_x, new_y, bullet.radius)

            shipcollision = check_collision_with_entities(pos, self.SHIPS.copy())
            if (
                shipcollision
                and isinstance(shipcollision, LivingEntity)
                and not shipcollision.path
            ):
                shipcollision.live -= bullet.damage
                if shipcollision.live <= 0:
                    self.SHIPS.remove(shipcollision)
                self.BULLETS.remove(bullet)
            else:
                enemy_collision = check_collision_with_entities(pos, self.ENEMIES.copy())
                if enemy_collision and isinstance(enemy_collision, LivingEntity):
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

        n = min(
            self.MAX_SHIPS * len(self.PLAYERS),
            len(self.MAP.ship_spawn_tiles),
            len(self.MAP.disembark_tiles),
        )
        spawns = random.sample(self.MAP.ship_spawn_tiles, n)
        targets = random.sample(self.MAP.disembark_tiles, n)

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

    def __move(self, enemies):
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
                        enemy.target_x, enemy.target_y = self.MAP.tile_center(
                            cur_col + dcol, cur_row + drow
                        )
                else:
                    enemy.x += int(dx / dist * enemy.speed)
                    enemy.y += int(dy / dist * enemy.speed)

    def __spawn_enemies(self):
        from frameworks.factories import ENEMY_VARIANTS
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
                        target_x, target_y = self.MAP.tile_center(
                            scol + dcol, srow + drow
                        )
                        enemy = Enemy(
                            x, y, path,
                            target_x=target_x, target_y=target_y,
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
                    enemy.target_x, enemy.target_y = self.MAP.tile_center(
                        scol + dcol, srow + drow
                    )

    def __check_enemy_hit_with_castle(self):
        for enemy in self.ENEMIES:
            for castle in self.MAP.castles.values():
                if (
                    check_intersection_by_radius(enemy, castle)
                    and castle.invulnerable == 0
                ):
                    castle.live -= enemy.damage
                    castle.invulnerable = self.INVULNERABLE_TICKS

        dead = [cid for cid, c in self.MAP.castles.items() if c.live <= 0]
        for cid in dead:
            self.MAP.remove_castle(cid)

    def __check_enemy_hit_with_player(self):
        for enemy in self.ENEMIES:
            for idd, player in self.PLAYERS.copy().items():
                if (
                    check_intersection_by_radius(enemy, player)
                    and isinstance(player, LivingEntity)
                    and player.invulnerable == 0
                ):
                    player.live -= enemy.damage
                    player.invulnerable = self.INVULNERABLE_TICKS
                    if player.live <= 0:
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

        return self.died_players

    def serialize(self) -> dict:
        return {
            "clients": len(self.CLIENTS),
            "players": {id: player.dump() for id, player in self.PLAYERS.items()},
            "bullets": [bullet.dump() for bullet in self.BULLETS],
            "ships": [ship.dump() for ship in self.SHIPS],
            "enemies": [enemy.dump() for enemy in self.ENEMIES],
            "castles": {id: castle.dump() for id, castle in self.MAP.castles.items()},
        }
