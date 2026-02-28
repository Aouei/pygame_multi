import heapq
import pandas as pd
import numpy as np
import random
import pygame

from scipy.spatial import KDTree

import factories
from entities import Geometry
from enums import COLLISIONS, STATE


class MapData:
    COMMON_COLLISIONS = {15, 18, 25, 27, 28, 32, 42, 44, 45, 50, 69}
    TILE_SIZE = 64
    COLLISION_TILES = {
        COLLISIONS.PLAYER : {4, 9, *COMMON_COLLISIONS},
        COLLISIONS.BULLET : {4, *COMMON_COLLISIONS},
        COLLISIONS.SHIP : {1, 2},
    }
    NO_TILES = {0}
    PLAYER_SPAWN_CODES = {14}
    SHIP_SPAWN_CODES = {5}
    SHIP_DISEMBARK_CODES = {2}

    def __init__(self, background: str, foreground : str | None = None) -> None:
        self.__load(background, foreground)
        self.__set_collision_tiles()
        self.__set_player_spawn_positions()
        self.__set_ship_spawn_positions()
        self.__set_blocked_tiles()
        self.__set_disembark_positions()

    @property
    def width(self):
        return self.background.shape[-1] * self.TILE_SIZE

    @property
    def height(self):
        return self.background.shape[0] * self.TILE_SIZE


    def __load(self, background: str, foreground : str | None):
        self.background = pd.read_csv(background, header=None).values
        self.foreground = pd.read_csv(foreground, header=None).values if foreground is not None else None

    def __set_collision_tiles(self):
        self.solid_tree_by_collision : dict[COLLISIONS, KDTree] = {}
        self.solid_positions_by_collision : dict[COLLISIONS, list] = {}

        for collision in COLLISIONS:
            positions = []
            self.__set_collision_pos(collision, self.background, positions)
            if self.foreground is not None:
                self.__set_collision_pos(collision, self.foreground, positions)

            self.solid_tree_by_collision[collision] = KDTree(positions) if positions else None
            self.solid_positions_by_collision[collision] = positions

    def __set_collision_pos(self, collision, data, positions):
        for i, row in enumerate(data):
            for j, col in enumerate(row):
                if col in self.COLLISION_TILES[collision]:
                    positions.append((
                            j * self.TILE_SIZE + self.TILE_SIZE // 2,
                            i * self.TILE_SIZE + self.TILE_SIZE // 2,
                        ))
                    
    def __set_player_spawn_positions(self):
        self.player_spawn_tiles = []
        for i, row in enumerate(self.background):
            for j, col in enumerate(row):
                if col in self.PLAYER_SPAWN_CODES:
                    self.player_spawn_tiles.append((j, i))
                    self.player_spawn_tiles.append((j, i))
                    
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

        T = self.TILE_SIZE
        self.disembark_tiles = [
            (col * T + T // 2, row * T + T // 2)
            for col, row in near_shore
        ]

    def find_path(self, sx: int, sy: int, tx: int, ty: int,
                  collision: COLLISIONS = COLLISIONS.PLAYER) -> list[STATE]:
        """
        A* sobre el grid de tiles de (sx, sy) a (tx, ty) en coordenadas world (píxeles).
        Devuelve una lista de STATE (UP/DOWN/LEFT/RIGHT) que lleva al destino,
        o [] si no hay camino o ya se está en el destino.
        """
        cols = self.background.shape[1]
        rows = self.background.shape[0]
        blocked = self._blocked_by_collision[collision]

        start = (sx // self.TILE_SIZE, sy // self.TILE_SIZE)
        goal  = (tx // self.TILE_SIZE, ty // self.TILE_SIZE)

        if start == goal:
            return []

        _DIRS = [
            (STATE.UP,    ( 0, -1)),
            (STATE.DOWN,  ( 0,  1)),
            (STATE.LEFT,  (-1,  0)),
            (STATE.RIGHT, ( 1,  0)),
        ]

        # heapq: (f, g, tile)  — f=g+h, g=coste acumulado, tile=(col, row)
        open_heap: list[tuple] = []
        heapq.heappush(open_heap, (0, 0, start))
        came_from: dict[tuple, tuple] = {}   # tile → (prev_tile, STATE)
        g_score:   dict[tuple, int]   = {start: 0}

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

            if g > g_score.get(current, float('inf')):
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
                if new_g < g_score.get(neighbor, float('inf')):
                    g_score[neighbor] = new_g
                    h = abs(nc - goal[0]) + abs(nr - goal[1])
                    heapq.heappush(open_heap, (new_g + h, new_g, neighbor))
                    came_from[neighbor] = (current, state)

        return []

    def spawn(self, is_player = True) -> tuple[int, int]:
        if is_player:
            j, i = random.choice(self.player_spawn_tiles)
        else:
            j, i = random.choice(self.ship_spawn_tiles)

        return (j * self.TILE_SIZE + self.TILE_SIZE // 2, i * self.TILE_SIZE + self.TILE_SIZE // 2)

    def is_collision(self, pos : Geometry, collision : COLLISIONS):
        if self.solid_tree_by_collision[collision] is None:
            return False
            
        x, y = pos.x, pos.y
        search_radius = self.TILE_SIZE + pos.radius // 2
        nearby_indices = self.solid_tree_by_collision[collision].query_ball_point([x, y], search_radius)

        for idx in nearby_indices:
            sx, sy = self.solid_positions_by_collision[collision][idx]
            dx, dy = pos.x - sx, pos.y - sy
            
            if dx * dx + dy * dy <= (pos.radius + pos.radius) ** 2:
                return True
            
        return False


class MapRender:
    MINI_SIZE    = 320
    MINI_RADIUS  = MINI_SIZE // 2
    WORLD_RADIUS = 320
    MINI_SCALE   = 0.1

    def __init__(self, background: str, foreground : str | None = None) -> None:
        self.map = MapData(background, foreground)
        self.TILES = factories.load_tiles(self.map.TILE_SIZE)

        self.background = self.__load_map(self.map.background)
        self.foreground = self.__load_map(self.map.foreground, True) if self.map.foreground is not None else None
        self.__build_mini_base()

    @property
    def width(self):
        return self.map.width

    @property
    def height(self):
        return self.map.height

    def __load_map(self, data, alpha = False):
        if alpha:
            surface = pygame.Surface(
                (data.shape[-1] * self.map.TILE_SIZE,
                data.shape[0]  * self.map.TILE_SIZE),
                pygame.SRCALPHA
            )
        else:
            surface = pygame.Surface(
                (data.shape[-1] * self.map.TILE_SIZE,
                data.shape[0]  * self.map.TILE_SIZE),
            )

        for i, row in enumerate(data):
            for j, col in enumerate(row):
                if col not in self.map.NO_TILES:
                    surface.blit(self.TILES[col], (j * self.map.TILE_SIZE, i * self.map.TILE_SIZE))

        return surface

    def __build_mini_base(self):
        """
        Versión del mapa escalada a MINI_SCALE, usada como fuente para recortar
        cada frame la ventana centrada en el jugador.
        """
        
        scaled_w = int(self.map.width  * self.MINI_SCALE)
        scaled_h = int(self.map.height * self.MINI_SCALE)
        self.mini_map_full = pygame.transform.scale(self.background, (scaled_w, scaled_h))
        if self.foreground:
            self.mini_map_full.blit(pygame.transform.scale(self.foreground, (scaled_w, scaled_h)), (0, 0))

        self._circle_mask = pygame.Surface((self.MINI_SIZE, self.MINI_SIZE), pygame.SRCALPHA)
        self._circle_mask.fill((0, 0, 0, 0))

        # Rellenamos el círculo con blanco opaco — lo usaremos como máscara de recorte
        pygame.draw.circle(self._circle_mask, (255, 255, 255, 255),
                           (self.MINI_RADIUS, self.MINI_RADIUS), self.MINI_RADIUS)

    def draw_layer(self, surface, position, layer):
        """Dibuja solo la región visible del mapa usando area=Rect."""
        screen_w, screen_h = surface.get_size()
        offset_x = -position[0]
        offset_y = -position[1]

        src_x = max(0, offset_x)
        src_y = max(0, offset_y)
        src_w = min(screen_w, self.map.width  - src_x)
        src_h = min(screen_h, self.map.height - src_y)

        if src_w <= 0 or src_h <= 0:
            return

        dst_x = max(0, position[0])
        dst_y = max(0, position[1])

        surface.blit(layer, (dst_x, dst_y), area=pygame.Rect(src_x, src_y, src_w, src_h))
        
    def draw(self, surface, position):
        self.draw_layer(surface, position, self.background)
        if self.foreground is not None:
            self.draw_layer(surface, position, self.foreground)


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
        S = self.MINI_SIZE
        R = self.MINI_RADIUS
        sc = self.MINI_SCALE

        # --- 1. Recortar la ventana del mapa escalado centrada en el jugador ---
        # Centro del jugador en coordenadas del mapa escalado
        cx_scaled = int(player_x * sc)
        cy_scaled = int(player_y * sc)

        # Región de MINI_SIZE x MINI_SIZE centrada en el jugador (en el mapa escalado)
        src_x = cx_scaled - R
        src_y = cy_scaled - R

        # Surface temporal donde compondremos el minimapa
        mini_surf = pygame.Surface((S, S))

        # Offset para manejar bordes del mapa
        blit_dst_x = max(0, -src_x)
        blit_dst_y = max(0, -src_y)
        clip_x     = max(0, src_x)
        clip_y     = max(0, src_y)
        clip_w     = min(S - blit_dst_x, self.mini_map_full.get_width()  - clip_x)
        clip_h     = min(S - blit_dst_y, self.mini_map_full.get_height() - clip_y)

        if clip_w > 0 and clip_h > 0:
            mini_surf.blit(self.mini_map_full, (blit_dst_x, blit_dst_y),
                           area=pygame.Rect(clip_x, clip_y, clip_w, clip_h))

        # --- 2. Dibujar puntos de jugadores ---
        for point in points:
            # Posición relativa al jugador local → centro del minimapa
            rel_x = (point['x'] - player_x) * sc
            rel_y = (point['y'] - player_y) * sc
            px = int(R + rel_x)
            py = int(R + rel_y)
            # Solo si cae dentro del círculo
            if (px - R) ** 2 + (py - R) ** 2 <= R ** 2:
                mini_surf.blit(point['image'], (px, py))

        # --- 3. Aplicar máscara circular ---
        # Creamos una surface SRCALPHA y bliteamos el contenido solo donde la máscara es blanca
        result = pygame.Surface((S, S), pygame.SRCALPHA)
        result.blit(mini_surf, (0, 0))
        # Multiplicamos alpha con la máscara: fuera del círculo → transparente
        result.blit(self._circle_mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)

        # --- 4. Borde circular y blit final ---
        surface.blit(result, (dx, dy))
        pygame.draw.circle(surface, (255, 255, 255),
                           (dx + R, dy + R), R, width=2)