import math
import pygame

import paths
from enums import ROLE
from factories import PLAYER_SIZE, SHIP_SIZE, HEALTH_BAR_HEIGHT, ENEMY_SIZE, CASTLE_SIZE
from factories import load_bullet, load_player, load_ship, load_enemy, load_castle
from protocols import LivingEntity
from entities import Player, Ship, Bullet, Enemy
from map import MapRender


class Logic:
    MAP = MapRender(paths.MAP_PATH, scale=4)
    PLAYERS = {role: load_player(role, PLAYER_SIZE) for role in ROLE}
    BULLETS = load_bullet()
    SHIPS = load_ship()
    ENEMIES = load_enemy()
    CASTLE = load_castle()

    _COLORS = {
        0: (0, 0, 0),
        1: (0, 0, 255),
        2: (0, 255, 0),
        3: (255, 0, 0),
    }

    DEBUG = False
    _in_battle = False
    ANIM_FPS = 8  # frames per second for sprite animation

    def __init__(self) -> None:
        self.received_players: dict[int, Player] = {}
        self.received_bullets: list[Bullet] = []
        self.received_ships: list[Ship] = []
        self.received_enemies: list[Enemy] = []
        self._current_player: Player = Player(ROLE.MAGE, 0, 0)
        self._ID = -1

    def reset(self):
        self.received_players.clear()
        self.received_bullets.clear()
        self.received_ships.clear()
        self.ID = -1

    @property
    def player(self):
        return self._current_player

    @property
    def ID(self):
        return self._ID

    @property
    def castles(self) -> dict:
        return self.MAP.castles

    @property
    def map_width(self):
        return self.MAP.width

    @property
    def map_height(self):
        return self.MAP.height

    @ID.setter
    def ID(self, value):
        self._ID = value

    def update_players(self, players: dict):
        self.received_players.clear()

        for idd, player in players.items():
            self.received_players[idd] = Player(ROLE.MAGE, 0, 0)
            self.received_players[idd].update(player)

        self.player.update(players.get(self.ID, {}))

    def update_bullets(self, bullets: list):
        self.received_bullets.clear()

        for bullet in bullets:
            self.received_bullets.append(Bullet(0, 0, 0, 0, ROLE.MAGE))
            self.received_bullets[-1].update(bullet)

    def update_ships(self, ships: list):
        self.received_ships.clear()

        for ship in ships:
            self.received_ships.append(Ship(0, 0, []))
            self.received_ships[-1].update(ship)

    def update_enemies(self, enemies: list):
        self.received_enemies.clear()

        for enemy in enemies:
            self.received_enemies.append(Enemy(0, 0, [], 0))
            self.received_enemies[-1].update(enemy)

    def update_castles(self, castles: dict):
        server_ids = {int(k) for k in castles}
        for cid in list(self.MAP.castles.keys()):
            if cid not in server_ids:
                self.MAP.remove_castle(cid)

        for id_str, data in castles.items():
            self.MAP.update_castle(int(id_str), data)

    def draw(self, surface, dx, dy):
        self.MAP.draw_layer(surface, (dx, dy), "water")
        self.MAP.draw_layer(surface, (dx, dy), "cliff")

        for player in self.received_players.copy().values():
            self.draw_player(surface, dx, dy, player)

        for ship in self.received_ships.copy():
            self.draw_ship(surface, dx, dy, ship)

        for enemy in self.received_enemies.copy():
            self.draw_enenmy(surface, dx, dy, enemy)

        for bullet in self.received_bullets.copy():
            self.draw_bullet(
                surface, bullet.x + dx, bullet.y + dy, bullet.role, bullet.dx, bullet.dy
            )

        self.MAP.draw_layer(surface, (dx, dy), "buildings")

        if self.DEBUG:
            self.MAP.draw_collision_debug(surface, (dx, dy))

        self.draw_castles(surface, dx, dy)
        self.draw_ui(surface, dx, dy)
        self._update_music()

    def start_music(self):
        pygame.mixer.music.load(paths.BACKGROND_MUSIC_PATH)
        pygame.mixer.music.play(loops=-1)
        self._in_battle = False

    def stop_music(self):
        pygame.mixer.music.stop()

    def _update_music(self):
        round_active = bool(self.received_ships or self.received_enemies)

        if round_active and not self._in_battle:
            pygame.mixer.music.load(paths.BATTLE_MUSIC_PATH)
            pygame.mixer.music.play(loops=-1)
            self._in_battle = True
        elif not round_active and self._in_battle:
            pygame.mixer.music.load(paths.BACKGROND_MUSIC_PATH)
            pygame.mixer.music.play(loops=-1)
            self._in_battle = False

    def draw_minimap(self, surface):
        minmap_points = []
        for player in self.received_players.copy().values():
            minmap_points.append(
                {
                    "x": player.x,
                    "y": player.y,
                    "image": pygame.transform.scale(
                        self.PLAYERS[player.role][player.state][0], (16, 16)
                    ),
                },
            )

        for castle in self.MAP.castles.values():
            minmap_points.append(
                {
                    "x": castle.x,
                    "y": castle.y,
                    "image": pygame.transform.scale(self.CASTLE, (16, 16)),
                },
            )

        minmap_points.append(
            {
                "x": self.player.x,
                "y": self.player.y,
                "image": pygame.transform.scale(
                    self.PLAYERS[self.player.role][self.player.state][0], (16, 16)
                ),
            },
        )

        self.MAP.draw_mini(surface, 16, 16, minmap_points, self.player.x, self.player.y)

    def _anim_frame(self, n_frames: int) -> int:
        if n_frames <= 1:
            return 0
        ms = pygame.time.get_ticks()
        return (ms // (1000 // self.ANIM_FPS)) % n_frames

    def draw_bullet(self, surface, x: int, y: int, role: ROLE, dx: float, dy: float):
        angle = math.degrees(math.atan2(-dy, dx)) - 90
        rotated = pygame.transform.rotate(self.BULLETS[role], angle)
        rect = rotated.get_rect(center=(x, y))
        surface.blit(rotated, rect)

    def draw_player(self, surface, dx, dy, player: Player):
        frames = self.PLAYERS[player.role][player.state]
        sprite = frames[self._anim_frame(len(frames))]
        surface.blit(
            sprite,
            (player.x - PLAYER_SIZE // 2 + dx, player.y - PLAYER_SIZE // 2 + dy),
        )

        if self.DEBUG:
            pygame.draw.circle(
                surface, (255, 0, 0), (player.x + dx, player.y + dy), player.radius, 1
            )

    def draw_ship(self, surface, dx, dy, ship: Ship):
        surface.blit(
            self.SHIPS[ship.state],
            (ship.x - SHIP_SIZE // 2 + dx, ship.y - SHIP_SIZE // 2 + dy),
        )

        if self.DEBUG:
            pygame.draw.circle(
                surface, (255, 0, 0), (ship.x + dx, ship.y + dy), ship.radius, 1
            )

    def draw_enenmy(self, surface, dx, dy, enemy: Enemy):
        surface.blit(
            self.ENEMIES[enemy.variant][enemy.state],
            (enemy.x - ENEMY_SIZE // 2 + dx, enemy.y - ENEMY_SIZE // 2 + dy),
        )

        if self.DEBUG:
            pygame.draw.circle(
                surface, (255, 0, 0), (enemy.x + dx, enemy.y + dy), enemy.radius, 1
            )

    def draw_castles(self, surface, dx, dy):
        for castle in self.castles.values():
            surface.blit(
                self.CASTLE,
                (castle.x - CASTLE_SIZE // 2 + dx, castle.y - CASTLE_SIZE // 2 + dy),
            )

            if self.DEBUG:
                pygame.draw.circle(
                    surface,
                    (255, 0, 0),
                    (castle.x + dx, castle.y + dy),
                    castle.radius,
                    1,
                )

    def draw_ui(self, surface, dx, dy):
        for player in self.received_players.copy().values():
            if isinstance(player, LivingEntity):
                self.draw_health_bar(
                    surface,
                    player.x - PLAYER_SIZE // 2 + dx,
                    player.y - PLAYER_SIZE // 2 - HEALTH_BAR_HEIGHT + dy,
                    PLAYER_SIZE,
                    HEALTH_BAR_HEIGHT,
                    player,
                )

        for ship in self.received_ships.copy():
            if isinstance(ship, LivingEntity):
                self.draw_health_bar(
                    surface,
                    ship.x - SHIP_SIZE // 2 + dx,
                    ship.y - SHIP_SIZE // 2 - HEALTH_BAR_HEIGHT + dy,
                    SHIP_SIZE,
                    HEALTH_BAR_HEIGHT,
                    ship,
                )

        for enemy in self.received_enemies.copy():
            if isinstance(enemy, LivingEntity):
                self.draw_health_bar(
                    surface,
                    enemy.x - ENEMY_SIZE // 2 + dx,
                    enemy.y - ENEMY_SIZE // 2 - HEALTH_BAR_HEIGHT + dy,
                    ENEMY_SIZE,
                    HEALTH_BAR_HEIGHT,
                    enemy,
                )

        for castle in self.castles.values():
            if isinstance(castle, LivingEntity):
                self.draw_health_bar(
                    surface,
                    castle.x - CASTLE_SIZE // 2 + dx,
                    castle.y - CASTLE_SIZE // 2 - HEALTH_BAR_HEIGHT + dy,
                    CASTLE_SIZE,
                    HEALTH_BAR_HEIGHT,
                    castle,
                )

        self.draw_minimap(surface)

    def draw_health_bar(self, surface, x, y, width, height, entity: LivingEntity):
        base_rect = (x, y, width, height)
        current_rect = (x, y, width * (entity.live / entity.max_live), height)

        pygame.draw.rect(surface, (0, 0, 0), base_rect)
        pygame.draw.rect(surface, (248, 117, 117), current_rect)
        pygame.draw.rect(surface, (255, 255, 255), base_rect, width=2)
