import math
from math import gcd, lcm
import pygame
import tiledpy.map.render as tiled_render

import frameworks.paths as paths
from domain.entities import Player, Ship, Bullet, Enemy, Castle
from domain.map_data import MapData
from domain.protocols import LivingEntity
from frameworks.factories import MAP_SCALE, HEALTH_BAR_HEIGHT, BASE_COLOR


class MapRender:
    MINI_SIZE = 320
    MINI_RADIUS = MINI_SIZE // 2
    WORLD_RADIUS = 320
    MINI_SCALE = 0.2

    def __init__(self, data: str, scale: int = 1) -> None:
        self.map = MapData(data, scale)
        self._full_surface: pygame.Surface | None = None
        self._layer_surfaces: dict[str, pygame.Surface] = {}
        self._animated_layer_names: set[str] = set()
        self._precomputed_frames: dict[str, list[pygame.Surface]] = {}
        self._layer_tick_ms: dict[str, int] = {}

    @property
    def width(self):
        return self.map.width

    @property
    def height(self):
        return self.map.height

    @property
    def castles(self):
        return self.map.castles

    def __build_mini_base(self):
        if self._full_surface is None:
            self._full_surface = pygame.Surface((self.map.width, self.map.height))
            tiled_render.draw_all_layers(
                self._full_surface, self.map.map, (0, 0), self.map.scale
            )

        scaled_w = int(self.map.width * self.MINI_SCALE)
        scaled_h = int(self.map.height * self.MINI_SCALE)
        self._mini_map_full = pygame.transform.scale(
            self._full_surface, (scaled_w, scaled_h)
        )

        S = self.MINI_SIZE
        R = self.MINI_RADIUS

        self._circle_mask = pygame.Surface((S, S), pygame.SRCALPHA)
        self._circle_mask.fill((0, 0, 0, 0))
        pygame.draw.circle(self._circle_mask, (255, 255, 255, 255), (R, R), R)

        self._mini_surf = pygame.Surface((S, S))
        self._mini_result = pygame.Surface((S, S), pygame.SRCALPHA)

    def _blit_cached(self, surface: pygame.Surface, cached: pygame.Surface, position):
        screen_w, screen_h = surface.get_size()
        offset_x = -position[0]
        offset_y = -position[1]

        src_x = max(0, offset_x)
        src_y = max(0, offset_y)
        src_w = min(screen_w, self.map.width - src_x)
        src_h = min(screen_h, self.map.height - src_y)

        if src_w <= 0 or src_h <= 0:
            return

        dst_x = max(0, position[0])
        dst_y = max(0, position[1])

        surface.blit(cached, (dst_x, dst_y), area=pygame.Rect(src_x, src_y, src_w, src_h))

    def _draw_animated_layer_to(self, surface: pygame.Surface, layer, t_ms: int) -> None:
        scale = self.map.scale
        scaled_tw = int(self.map.map.tile_width * scale)
        scaled_th = int(self.map.map.tile_height * scale)
        surf_w = surface.get_width()
        surf_h = surface.get_height()
        for tile in layer.iter_tiles():
            tile_surf = tile.get_animated_surface(t_ms, scale)
            actual_w = tile_surf.get_width()
            actual_h = tile_surf.get_height()
            px = tile.tx * scaled_tw + int(layer.offset_x * scale)
            py = tile.ty * scaled_th + int(layer.offset_y * scale) + scaled_th - actual_h
            if px + actual_w < 0 or px > surf_w or py + actual_h < 0 or py > surf_h:
                continue
            if layer.opacity < 1.0:
                tile_surf = tile_surf.copy()
                tile_surf.set_alpha(int(layer.opacity * 255))
            surface.blit(tile_surf, (px, py))

    def _precompute_animated_layer(self, layer, name: str) -> None:
        animated_tiles = layer.get_animated_tiles()
        if not animated_tiles:
            return

        all_durations: list[int] = []
        cycle_totals: list[int] = []
        for tile in animated_tiles:
            durations = [f["duration"] for f in tile.meta.animation]
            all_durations.extend(durations)
            cycle_totals.append(sum(durations))

        tick_ms = gcd(*all_durations)
        total_ms = lcm(*cycle_totals)
        n_frames = total_ms // tick_ms

        frames = []
        for i in range(n_frames):
            surf = pygame.Surface((self.map.width, self.map.height), pygame.SRCALPHA)
            self._draw_animated_layer_to(surf, layer, i * tick_ms)
            frames.append(surf)

        self._precomputed_frames[name] = frames
        self._layer_tick_ms[name] = tick_ms

    def draw_layer(self, surface, position, name: str):
        layer = self.map.map.get_layer(name)

        # Lazy detection: first time we see this layer, check for animated tiles
        if name not in self._layer_surfaces and name not in self._animated_layer_names:
            if layer is not None and layer.get_animated_tiles():
                self._animated_layer_names.add(name)

        if name in self._animated_layer_names:
            if name not in self._precomputed_frames:
                if layer is not None:
                    self._precompute_animated_layer(layer, name)
                else:
                    self._precomputed_frames[name] = []
                    self._layer_tick_ms[name] = 1
            frames = self._precomputed_frames[name]
            if frames:
                tick_ms = self._layer_tick_ms[name]
                idx = (pygame.time.get_ticks() // tick_ms) % len(frames)
                self._blit_cached(surface, frames[idx], position)
        else:
            if name not in self._layer_surfaces:
                cached = pygame.Surface((self.map.width, self.map.height), pygame.SRCALPHA)
                if layer is not None:
                    tiled_render.draw_layer(
                        cached, layer,
                        self.map.map.tile_width, self.map.map.tile_height,
                        (0, 0), self.map.scale,
                    )
                self._layer_surfaces[name] = cached
            self._blit_cached(surface, self._layer_surfaces[name], position)

    def draw(self, surface, position):
        if self._full_surface is None:
            self._full_surface = pygame.Surface((self.map.width, self.map.height))
            tiled_render.draw_all_layers(
                self._full_surface, self.map.map, (0, 0), self.map.scale
            )
        self._blit_cached(surface, self._full_surface, position)

    def draw_collision_debug(self, surface: pygame.Surface, position):
        dx, dy = position
        tw = self.map.map.tile_width * self.map.scale
        th = self.map.map.tile_height * self.map.scale

        for (tx, ty), shapes in self.map.collision_shapes.items():
            for shape in shapes:
                r = pygame.Rect(shape.x + dx, shape.y + dy, shape.width, shape.height)
                pygame.draw.rect(surface, (255, 0, 255), r, 1)

        for collision_positions in self.map.solid_positions_by_collision.values():
            for tx, ty in collision_positions:
                if (tx, ty) not in self.map.collision_shapes:
                    r = pygame.Rect(tx * tw + dx, ty * th + dy, tw, th)
                    pygame.draw.rect(surface, (255, 165, 0), r, 1)

    def draw_mini(self, surface: pygame.Surface, dx, dy, points, player_x, player_y):
        if not hasattr(self, "_mini_map_full"):
            self.__build_mini_base()

        S = self.MINI_SIZE
        R = self.MINI_RADIUS
        sc = self.MINI_SCALE

        cx_scaled = int(player_x * sc)
        cy_scaled = int(player_y * sc)
        src_x = cx_scaled - R
        src_y = cy_scaled - R

        self._mini_surf.fill(BASE_COLOR)

        blit_dst_x = max(0, -src_x)
        blit_dst_y = max(0, -src_y)
        clip_x = max(0, src_x)
        clip_y = max(0, src_y)
        clip_w = min(S - blit_dst_x, self._mini_map_full.get_width() - clip_x)
        clip_h = min(S - blit_dst_y, self._mini_map_full.get_height() - clip_y)

        if clip_w > 0 and clip_h > 0:
            self._mini_surf.blit(
                self._mini_map_full,
                (blit_dst_x, blit_dst_y),
                area=pygame.Rect(clip_x, clip_y, clip_w, clip_h),
            )

        EDGE_MARGIN = 8
        for point in points:
            rel_x = (point["x"] - player_x) * sc
            rel_y = (point["y"] - player_y) * sc
            dist_sq = rel_x ** 2 + rel_y ** 2
            inner_r = R - EDGE_MARGIN
            if dist_sq <= inner_r ** 2:
                px = int(R + rel_x)
                py = int(R + rel_y)
                img = point["image"]
                self._mini_surf.blit(img, (px - img.get_width() // 2, py - img.get_height() // 2))
            elif point.get("clamp_to_edge"):
                dist = math.sqrt(dist_sq)
                factor = inner_r / dist
                px = int(R + rel_x * factor)
                py = int(R + rel_y * factor)
                img = point["image"]
                self._mini_surf.blit(img, (px - img.get_width() // 2, py - img.get_height() // 2))

        self._mini_result.fill((0, 0, 0, 0))
        self._mini_result.blit(self._mini_surf, (0, 0))
        self._mini_result.blit(
            self._circle_mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN
        )

        surface.blit(self._mini_result, (dx, dy))
        pygame.draw.circle(surface, (255, 255, 255), (dx + R, dy + R), R, width=2)


class GameRenderer:
    """
    Renderiza el estado del juego (ClientSession) en una superficie pygame.
    Lee sprites del AssetStore inyectado.
    """

    DEBUG = True
    ANIM_FPS = 8

    def __init__(self, assets) -> None:
        self._assets = assets

    def _anim_frame(self, n_frames: int) -> int:
        if n_frames <= 1:
            return 0
        ms = pygame.time.get_ticks()
        return (ms // (1000 // self.ANIM_FPS)) % n_frames

    def draw(self, surface, session, dx: int, dy: int):
        map_r: MapRender = self._assets.map_render
        map_r.draw_layer(surface, (dx, dy), "water")
        map_r.draw_layer(surface, (dx, dy), "cliff")

        for player in session.received_players.copy().values():
            self.draw_player(surface, dx, dy, player)

        for ship in session.received_ships.copy():
            self.draw_ship(surface, dx, dy, ship)

        for enemy in session.received_enemies.copy():
            self.draw_enemy(surface, dx, dy, enemy)

        for bullet in session.received_bullets.copy():
            self.draw_bullet(
                surface,
                bullet.x + dx,
                bullet.y + dy,
                bullet.owner,
                bullet.dx,
                bullet.dy,
            )

        map_r.draw_layer(surface, (dx, dy), "buildings")

        if self.DEBUG:
            map_r.draw_collision_debug(surface, (dx, dy))

        self.draw_castles(surface, dx, dy, session.received_castles)
        self.draw_ui(surface, dx, dy, session, map_r)

    def draw_bullet(self, surface, x: int, y: int, role, dx: float, dy: float):
        angle = math.degrees(math.atan2(-dy, dx)) - 90
        rotated = pygame.transform.rotate(self._assets.bullets[role], angle)
        rect = rotated.get_rect(center=(x, y))
        surface.blit(rotated, rect)

    def draw_player(self, surface, dx, dy, player: Player):
        frames = self._assets.players[player.role][player.state]
        sprite = frames[self._anim_frame(len(frames))]
        surface.blit(
            sprite,
            (
                player.x - sprite.get_width() // 2 + dx,
                player.y - sprite.get_height() // 2 + dy,
            ),
        )
        if self.DEBUG:
            pygame.draw.circle(
                surface, (255, 0, 0), (player.x + dx, player.y + dy), player.radius, 1
            )

    def draw_ship(self, surface, dx, dy, ship: Ship):
        sprite = self._assets.ships[ship.state]
        surface.blit(
            sprite,
            (
                ship.x - sprite.get_width() // 2 + dx,
                ship.y - sprite.get_height() // 2 + dy,
            ),
        )
        if self.DEBUG:
            pygame.draw.circle(
                surface, (255, 0, 0), (ship.x + dx, ship.y + dy), ship.radius, 1
            )

    def draw_enemy(self, surface, dx, dy, enemy):
        sprite = self._assets.enemies[enemy.variant][enemy.state]
        surface.blit(
            sprite,
            (
                enemy.x - sprite.get_width() // 2 + dx,
                enemy.y - sprite.get_height() // 2 + dy,
            ),
        )
        if self.DEBUG:
            pygame.draw.circle(
                surface, (255, 0, 0), (enemy.x + dx, enemy.y + dy), enemy.radius, 1
            )

    def draw_castles(self, surface, dx, dy, castles: dict):
        for castle in castles.values():
            sprite = self._assets.castle
            surface.blit(
                sprite,
                (
                    castle.x - sprite.get_width() // 2 + dx,
                    castle.y - sprite.get_height() // 2 + dy,
                ),
            )
            if self.DEBUG:
                pygame.draw.circle(
                    surface,
                    (255, 0, 0),
                    (castle.x + dx, castle.y + dy),
                    castle.radius,
                    1,
                )

    def _sprite_width(self, entity) -> int:
        if isinstance(entity, Player):
            return self._assets.players[entity.role][entity.state][0].get_width()
        elif isinstance(entity, Ship):
            return self._assets.ships[entity.state].get_width()
        elif isinstance(entity, Enemy):
            return self._assets.enemies[entity.variant][entity.state].get_width()
        elif isinstance(entity, Castle):
            return self._assets.castle.get_width()
        return HEALTH_BAR_HEIGHT

    def draw_ui(self, surface, dx, dy, session, map_r: MapRender):
        for player in session.received_players.copy().values():
            if isinstance(player, LivingEntity):
                w = self._sprite_width(player)
                self.draw_health_bar(
                    surface,
                    player.x - w // 2 + dx,
                    player.y - w // 2 - HEALTH_BAR_HEIGHT + dy,
                    w,
                    HEALTH_BAR_HEIGHT,
                    player,
                )

        for ship in session.received_ships.copy():
            if isinstance(ship, LivingEntity):
                w = self._sprite_width(ship)
                self.draw_health_bar(
                    surface,
                    ship.x - w // 2 + dx,
                    ship.y - w // 2 - HEALTH_BAR_HEIGHT + dy,
                    w,
                    HEALTH_BAR_HEIGHT,
                    ship,
                )

        for enemy in session.received_enemies.copy():
            if isinstance(enemy, LivingEntity):
                w = self._sprite_width(enemy)
                self.draw_health_bar(
                    surface,
                    enemy.x - w // 2 + dx,
                    enemy.y - w // 2 - HEALTH_BAR_HEIGHT + dy,
                    w,
                    HEALTH_BAR_HEIGHT,
                    enemy,
                )

        for castle in session.received_castles.values():
            if isinstance(castle, LivingEntity):
                w = self._sprite_width(castle)
                self.draw_health_bar(
                    surface,
                    castle.x - w // 2 + dx,
                    castle.y - w // 2 - HEALTH_BAR_HEIGHT + dy,
                    w,
                    HEALTH_BAR_HEIGHT,
                    castle,
                )

        self.draw_minimap(surface, session, map_r)

    def draw_health_bar(self, surface, x, y, width, height, entity: LivingEntity):
        base_rect = (x, y, width, height)
        current_rect = (x, y, width * (entity.live / entity.max_live), height)
        pygame.draw.rect(surface, (0, 0, 0), base_rect)
        pygame.draw.rect(surface, (248, 117, 117), current_rect)
        pygame.draw.rect(surface, (255, 255, 255), base_rect, width=2)

    def draw_minimap(self, surface, session, map_r: MapRender):
        minimap_points = []
        players_sprites = self._assets.players

        sc = map_r.MINI_SCALE

        def _mini_img(surf: pygame.Surface) -> pygame.Surface:
            w = max(1, int(surf.get_width() * sc))
            h = max(1, int(surf.get_height() * sc))
            return pygame.transform.scale(surf, (w, h))

        for player in session.received_players.copy().values():
            minimap_points.append(
                {
                    "x": player.x,
                    "y": player.y,
                    "image": _mini_img(players_sprites[player.role][player.state][0]),
                    "clamp_to_edge": True,
                }
            )

        for castle in session.received_castles.values():
            minimap_points.append(
                {
                    "x": castle.x,
                    "y": castle.y,
                    "image": _mini_img(self._assets.castle),
                    "clamp_to_edge": False,
                }
            )

        for ship in session.received_ships:
            minimap_points.append(
                {
                    "x": ship.x,
                    "y": ship.y,
                    "image": _mini_img(self._assets.ships[ship.state]),
                    "clamp_to_edge": True,
                }
            )

        p = session.player
        minimap_points.append(
            {
                "x": p.x,
                "y": p.y,
                "image": _mini_img(players_sprites[p.role][p.state][0]),
                "clamp_to_edge": False,
            }
        )

        map_r.draw_mini(surface, 16, 16, minimap_points, p.x, p.y)
