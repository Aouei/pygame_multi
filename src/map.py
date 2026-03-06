import heapq
import pandas as pd
import numpy as np
import random
import pygame

from scipy.spatial import KDTree

from factories import TILE_SIZE, load_tiles
from entities import Geometry
from enums import COLLISIONS, STATE

from tiledpy import TiledMap
from tiledpy.enums import OFFSET



class MapData:
    COMMON_COLLISIONS = {'tree', 'building', 'cliff'}
    COLLISION_TILES = {
        COLLISIONS.PLAYER: {'deep_water', 9, *COMMON_COLLISIONS},
        COLLISIONS.BULLET: {4, *COMMON_COLLISIONS},
        COLLISIONS.SHIP: {1, 2},
        COLLISIONS.ENEMY: {4, 5, 9, *COMMON_COLLISIONS},
    }
    NO_TILES = {0}
    PLAYER_SPAWN_CODES = {14}
    SHIP_SPAWN_CODES = {'deep_water'}
    SHIP_DISEMBARK_CODES = {2}
    ENEMY_TARGET_CODES = {1, 12}

    COLLISSION_SHAPES_BY_TILE_POS : dict[tuple, list[pygame.Rect]] = {}

    def __init__(self, data: str, scale : int = 1) -> None:
        self.map = TiledMap(data)
        self.scale = scale
        # self.__load(background, foreground)
        self.__set_collision_tiles()
        self.__set_player_spawn_positions()
        # self.__set_ship_spawn_positions()
        # self.__set_blocked_tiles()
        # self.__set_disembark_positions()
        # self.__set_enemy_target_positions()

    @property
    def width(self):
        return self.map.width * self.map.tile_width * self.scale

    @property
    def height(self):
        return self.map.height * self.map.tile_height * self.scale


    def __load(self, background: str, foreground: str | None):
        self.background = pd.read_csv(background, header=None).values
        self.foreground = (
            pd.read_csv(foreground, header=None).values
            if foreground is not None
            else None
        )

    def __set_collision_tiles(self):
        self.solid_tree_by_collision: dict[COLLISIONS, KDTree] = {}
        self.solid_positions_by_collision: dict[COLLISIONS, list] = {}

        all_positions: set[tuple] = set()
        for collision in COLLISIONS:
            positions = []
            self.__set_collision_pos(collision, positions)

            self.solid_tree_by_collision[collision] = (
                KDTree(positions) if positions else None
            )
            self.solid_positions_by_collision[collision] = positions
            all_positions.update(map(tuple, positions))

        self.__create_collision_rectangles(all_positions)

    def __create_collision_rectangles(self, all_positions):
        tw = self.map.tile_width * self.scale
        th = self.map.tile_height * self.scale
    
        for (tx, ty) in all_positions:
            for layer in self.map.visible_layers:
                gid = layer.get_raw_gid(tx, ty)
            
                if gid in [0, None]:
                    continue

                tileset = self.map.get_tileset_for_gid(gid)
                if tileset is None:
                    continue
                
                tile_data = tileset.tile_data.get(tileset.global_to_local(gid))
                if not tile_data or not tile_data.collision_objects:
                    continue

                print(tile_data)
                
                wx = tx * tw
                wy = ty * th

                for col in tile_data.collision_objects:
                    rect = pygame.Rect(
                        wx + col["x"]  * self.scale,
                        wy + col["y"]  * self.scale,
                        col["width"]  * self.scale,
                        col["height"] * self.scale,
                    )
                    self.COLLISSION_SHAPES_BY_TILE_POS.setdefault((tx, ty), []).append(rect)

    def __set_collision_pos(self, collision, positions):
        for collision_id in self.COLLISION_TILES[collision]:
            for layer in self.map.visible_layers:
                positions.extend( layer.get_tile_by_property("Class", collision_id) )

    def __set_player_spawn_positions(self):
        self.player_spawn_tiles = []

        for layer in self.map.visible_layers:
            self.player_spawn_tiles.extend( layer.get_tile_by_property("Class", "spawn") )

    def __set_ship_spawn_positions(self):
        self.ship_spawn_tiles = []
        for i, row in enumerate(self.background):
            for j, col in enumerate(row):
                if col in self.SHIP_SPAWN_CODES:
                    self.ship_spawn_tiles.append((j, i))
                    self.ship_spawn_tiles.append((j, i))

    def __set_blocked_tiles(self):
        self._blocked_by_collision: dict[COLLISIONS, set] = {}
        for collision in COLLISIONS:
            blocked: set[tuple[int, int]] = set()
            self.__collect_blocked(collision, self.background, blocked)
            if self.foreground is not None:
                self.__collect_blocked(collision, self.foreground, blocked)
            self._blocked_by_collision[collision] = blocked

    def __collect_blocked(self, collision: COLLISIONS, data, blocked: set):
        for i, row in enumerate(data):
            for j, col in enumerate(row):
                if col in self.COLLISION_TILES[collision]:
                    blocked.add((j, i))

    def __set_disembark_positions(self):
        """
        Tiles de agua (no bloqueados para ships) adyacentes a tiles de desembarco.
        Son los puntos donde los ships terminan su recorrido.
        """
        blocked = self._blocked_by_collision[COLLISIONS.SHIP]
        rows, cols = self.background.shape
        near_shore: set[tuple[int, int]] = set()

        for i, row in enumerate(self.background):
            for j, tile in enumerate(row):
                if tile in self.SHIP_DISEMBARK_CODES:
                    for di, dj in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                        ni, nj = i + di, j + dj
                        if 0 <= ni < rows and 0 <= nj < cols:
                            if (nj, ni) not in blocked:
                                near_shore.add((nj, ni))

        T = TILE_SIZE
        self.disembark_tiles = [
            (col * T + T // 2, row * T + T // 2) for col, row in near_shore
        ]

    def __set_enemy_target_positions(self):
        """
        Tiles de agua (no bloqueados para ships) adyacentes a tiles de desembarco.
        Son los puntos donde los ships terminan su recorrido.
        """
        blocked = self._blocked_by_collision[COLLISIONS.ENEMY]
        rows, cols = self.background.shape
        near_shore: set[tuple[int, int]] = set()

        for i, row in enumerate(self.background):
            for j, tile in enumerate(row):
                if tile in self.ENEMY_TARGET_CODES:
                    for di, dj in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                        ni, nj = i + di, j + dj
                        if 0 <= ni < rows and 0 <= nj < cols:
                            if (nj, ni) not in blocked:
                                near_shore.add((nj, ni))

        T = TILE_SIZE
        self.enemy_target_tiles = [
            (col * T + T // 2, row * T + T // 2) for col, row in near_shore
        ]

    def find_path(
        self,
        sx: int,
        sy: int,
        tx: int,
        ty: int,
        collision: COLLISIONS = COLLISIONS.PLAYER,
    ) -> list[STATE]:
        """
        A* sobre el grid de tiles de (sx, sy) a (tx, ty) en coordenadas world (píxeles).
        Devuelve una lista de STATE (UP/DOWN/LEFT/RIGHT) que lleva al destino,
        o [] si no hay camino o ya se está en el destino.
        """
        cols = self.background.shape[1]
        rows = self.background.shape[0]
        blocked = self._blocked_by_collision[collision]

        start = (sx // TILE_SIZE, sy // TILE_SIZE)
        goal = (tx // TILE_SIZE, ty // TILE_SIZE)

        if start == goal:
            return []

        _DIRS = [
            (STATE.UP, (0, -1)),
            (STATE.DOWN, (0, 1)),
            (STATE.LEFT, (-1, 0)),
            (STATE.RIGHT, (1, 0)),
        ]

        # heapq: (f, g, tile)  — f=g+h, g=coste acumulado, tile=(col, row)
        open_heap: list[tuple] = []
        heapq.heappush(open_heap, (0, 0, start))
        came_from: dict[tuple, tuple] = {}  # tile → (prev_tile, STATE)
        g_score: dict[tuple, int] = {start: 0}

        while open_heap:
            _, g, current = heapq.heappop(open_heap)

            if current == goal:
                path: list[STATE] = []
                node = current
                while node in came_from:
                    prev, direction = came_from[node]
                    path.append(direction)
                    node = prev
                path.reverse()
                return path

            if g > g_score.get(current, float("inf")):
                continue

            cx, cy = current
            for state, (dx, dy) in _DIRS:
                neighbor = (cx + dx, cy + dy)
                nc, nr = neighbor
                if nc < 0 or nc >= cols or nr < 0 or nr >= rows:
                    continue
                if neighbor in blocked:
                    continue
                new_g = g + 1
                if new_g < g_score.get(neighbor, float("inf")):
                    g_score[neighbor] = new_g
                    h = abs(nc - goal[0]) + abs(nr - goal[1])
                    heapq.heappush(open_heap, (new_g + h, new_g, neighbor))
                    came_from[neighbor] = (current, state)

        return []

    def spawn(self, is_player=True) -> tuple[int | float, int | float]:
        if is_player:
            j, i = random.choice(self.player_spawn_tiles)
        else:
            j, i = random.choice(self.ship_spawn_tiles)

        return self.map.tile_to_world(j, i, self.scale, OFFSET.CENTER)

    def is_collision(self, pos: Geometry, collision: COLLISIONS):
        if self.solid_tree_by_collision[collision] is None:
            return False

        tx_f, ty_f = self.map.world_to_tile(pos.x, pos.y, self.scale, OFFSET.CENTER)
        nearby_indices = self.solid_tree_by_collision[collision].query_ball_point(
            [tx_f, ty_f], 2
        )

        tw = self.map.tile_width * self.scale
        th = self.map.tile_height * self.scale

        for idx in nearby_indices:
            tx, ty = self.solid_positions_by_collision[collision][idx]

            shapes = self.COLLISSION_SHAPES_BY_TILE_POS.get((tx, ty))
            if shapes:
                # custom per-tile collision shapes (world space) vs circle
                for shape in shapes:
                    cx = max(shape.left, min(pos.x, shape.right))
                    cy = max(shape.top,  min(pos.y, shape.bottom))
                    if (pos.x - cx) ** 2 + (pos.y - cy) ** 2 < pos.radius ** 2:
                        return True
            else:
                # full tile AABB vs circle
                cx = max(tx * tw, min(pos.x, (tx + 1) * tw))
                cy = max(ty * th, min(pos.y, (ty + 1) * th))
                if (pos.x - cx) ** 2 + (pos.y - cy) ** 2 < pos.radius ** 2:
                    return True

        return False


class MapRender:
    MINI_SIZE = 320
    MINI_RADIUS = MINI_SIZE // 2
    WORLD_RADIUS = 320
    MINI_SCALE = 0.1

    def __init__(self, data : str, scale : int = 1) -> None:
        self.map = MapData(data, scale)
        self._full_surface: pygame.Surface | None = None
        self._layer_surfaces: dict[str, pygame.Surface] = {}

    @property
    def width(self):
        return self.map.width

    @property
    def height(self):
        return self.map.height

    def __build_mini_base(self):
        """
        Versión del mapa escalada a MINI_SCALE, usada como fuente para recortar
        cada frame la ventana centrada en el jugador.
        """

        # Asegurarse de que _full_surface está construida
        if self._full_surface is None:
            self._full_surface = pygame.Surface((self.map.width, self.map.height))
            self.map.map.draw_all_layers(self._full_surface, (0, 0), scale=self.map.scale)

        scaled_w = int(self.map.width * self.MINI_SCALE)
        scaled_h = int(self.map.height * self.MINI_SCALE)
        self._mini_map_full = pygame.transform.scale(self._full_surface, (scaled_w, scaled_h))

        S = self.MINI_SIZE
        R = self.MINI_RADIUS

        self._circle_mask = pygame.Surface((S, S), pygame.SRCALPHA)
        self._circle_mask.fill((0, 0, 0, 0))

        # Rellenamos el círculo con blanco opaco — lo usaremos como máscara de recorte
        pygame.draw.circle(
            self._circle_mask,
            (255, 255, 255, 255),
            (R, R),
            R,
        )

        # Surfaces reutilizables para draw_mini (misma resolución siempre)
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

    def draw_layer(self, surface, position, name: str):
        if name not in self._layer_surfaces:
            cached = pygame.Surface((self.map.width, self.map.height), pygame.SRCALPHA)
            self.map.map.draw_layer(cached, name, (0, 0), scale=self.map.scale)
            self._layer_surfaces[name] = cached

        self._blit_cached(surface, self._layer_surfaces[name], position)

    def draw(self, surface, position):
        if self._full_surface is None:
            self._full_surface = pygame.Surface((self.map.width, self.map.height))
            self.map.map.draw_all_layers(self._full_surface, (0, 0), scale=self.map.scale)

        self._blit_cached(surface, self._full_surface, position)

    def draw_collision_debug(self, surface: pygame.Surface, position):
        """Dibuja los rects de colisión sobre la pantalla (offset de cámara en position)."""
        dx, dy = position
        tw = self.map.map.tile_width  * self.map.scale
        th = self.map.map.tile_height * self.map.scale

        for (tx, ty), shapes in self.map.COLLISSION_SHAPES_BY_TILE_POS.items():
            for shape in shapes:
                r = pygame.Rect(shape.x + dx, shape.y + dy, shape.width, shape.height)
                pygame.draw.rect(surface, (255, 0, 255), r, 1)

        for collision_positions in self.map.solid_positions_by_collision.values():
            for (tx, ty) in collision_positions:
                if (tx, ty) not in self.map.COLLISSION_SHAPES_BY_TILE_POS:
                    r = pygame.Rect(tx * tw + dx, ty * th + dy, tw, th)
                    pygame.draw.rect(surface, (255, 165, 0), r, 1)

    def draw_mini(self, surface: pygame.Surface, dx, dy, points, player_x, player_y):
        """
        Minimapa circular de MINI_SIZE x MINI_SIZE centrado en (player_x, player_y).
        Solo muestra WORLD_RADIUS px alrededor del jugador.
        Los puntos de otros jugadores se dibujan relativos al centro.

        Parámetros
        ----------
        dx, dy      : posición en pantalla donde se dibuja el minimapa
        points      : lista de {'x', 'y', 'color'} en coordenadas world
        player_x/y  : posición world del jugador local (centro del minimapa)
        """
        if not hasattr(self, '_mini_map_full'):
            self.__build_mini_base()

        S = self.MINI_SIZE
        R = self.MINI_RADIUS
        sc = self.MINI_SCALE

        # --- 1. Recortar la ventana del mapa escalado centrada en el jugador ---
        cx_scaled = int(player_x * sc)
        cy_scaled = int(player_y * sc)

        src_x = cx_scaled - R
        src_y = cy_scaled - R

        self._mini_surf.fill((0, 0, 0))

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

        # --- 2. Dibujar puntos de jugadores ---
        for point in points:
            rel_x = (point["x"] - player_x) * sc
            rel_y = (point["y"] - player_y) * sc
            px = int(R + rel_x)
            py = int(R + rel_y)
            if (px - R) ** 2 + (py - R) ** 2 <= R**2:
                self._mini_surf.blit(point["image"], (px, py))

        # --- 3. Aplicar máscara circular ---
        self._mini_result.fill((0, 0, 0, 0))
        self._mini_result.blit(self._mini_surf, (0, 0))
        self._mini_result.blit(self._circle_mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)

        # --- 4. Borde circular y blit final ---
        surface.blit(self._mini_result, (dx, dy))
        pygame.draw.circle(surface, (255, 255, 255), (dx + R, dy + R), R, width=2)