import pandas as pd
import random
import pygame

from scipy.spatial import KDTree

import factories
from entities import Geometry


class Map:
    SOLID_TILES = {2, 3}
    NO_TILES = {0}
    SPAWN_CODE = 7
    TILE_SIZE = 64

    # Minimap: tamaño fijo y radio de visión en world pixels
    MINI_SIZE    = 320          # diámetro del minimapa en pantalla (px)
    MINI_RADIUS  = MINI_SIZE // 2
    WORLD_RADIUS = 320          # radio visible en coordenadas world (px)
    # Escala: MINI_RADIUS px en pantalla = WORLD_RADIUS px en world
    MINI_SCALE   = 0.1
    # MINI_SCALE   = MINI_RADIUS / WORLD_RADIUS

    TILES = factories.load_tiles(TILE_SIZE)

    def __init__(self, data_path: str) -> None:
        self.__load(data_path)
        self.__set_collision_tiles()
        self.__set_spawn_positions()
        self.__load_map()
        self.__build_mini_base()

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------
    @property
    def width(self):
        return self.data.shape[-1] * self.TILE_SIZE

    @property
    def height(self):
        return self.data.shape[0] * self.TILE_SIZE

    # ------------------------------------------------------------------
    # Init helpers
    # ------------------------------------------------------------------
    def __load(self, data_path: str):
        self.data = pd.read_csv(data_path, header=None).values

    def __set_collision_tiles(self):
        self.solid_positions = []
        for i, row in enumerate(self.data):
            for j, col in enumerate(row):
                if col in self.SOLID_TILES:
                    self.solid_positions.append((
                        j * self.TILE_SIZE + self.TILE_SIZE // 2,
                        i * self.TILE_SIZE + self.TILE_SIZE // 2,
                    ))
        self.solid_tree = KDTree(self.solid_positions) if self.solid_positions else None

    def __set_spawn_positions(self):
        self.spawn_tiles = []
        for i, row in enumerate(self.data):
            for j, col in enumerate(row):
                if col == self.SPAWN_CODE:
                    self.spawn_tiles.append((j, i))

    def __load_map(self):
        self.prev_map = pygame.Surface(
            (self.data.shape[-1] * self.TILE_SIZE,
             self.data.shape[0]  * self.TILE_SIZE)
        )
        for i, row in enumerate(self.data):
            for j, col in enumerate(row):
                if col not in self.NO_TILES:
                    self.prev_map.blit(self.TILES[col],
                                       (j * self.TILE_SIZE, i * self.TILE_SIZE))

    def __build_mini_base(self):
        """
        Versión del mapa escalada a MINI_SCALE, usada como fuente para recortar
        cada frame la ventana centrada en el jugador.
        """
        scaled_w = int(self.width  * self.MINI_SCALE)
        scaled_h = int(self.height * self.MINI_SCALE)
        self.mini_map_full = pygame.transform.scale(self.prev_map, (scaled_w, scaled_h))

        # Máscara circular reutilizable: surface negra con círculo transparente
        self._circle_mask = pygame.Surface((self.MINI_SIZE, self.MINI_SIZE), pygame.SRCALPHA)
        self._circle_mask.fill((0, 0, 0, 0))
        # Rellenamos el círculo con blanco opaco — lo usaremos como máscara de recorte
        pygame.draw.circle(self._circle_mask, (255, 255, 255, 255),
                           (self.MINI_RADIUS, self.MINI_RADIUS), self.MINI_RADIUS)

    # ------------------------------------------------------------------
    # Spawn / Collision
    # ------------------------------------------------------------------
    def spawn(self) -> tuple[int, int]:
        j, i = random.choice(self.spawn_tiles)
        return (j * self.TILE_SIZE + self.TILE_SIZE // 2,
                i * self.TILE_SIZE + self.TILE_SIZE // 2)

    def is_collision(self, pos : Geometry):
        if self.solid_tree is None:
            return False

            
        x, y = pos.x, pos.y
        search_radius = self.TILE_SIZE + pos.radius // 2
        nearby_indices = self.solid_tree.query_ball_point([x, y], search_radius)

        for idx in nearby_indices:
            sx, sy = self.solid_positions[idx]
            dx, dy = pos.x - sx, pos.y - sy
            
            if dx * dx + dy * dy <= (pos.radius + pos.radius) ** 2:
                return True
            
        return False

    # ------------------------------------------------------------------
    # Draw
    # ------------------------------------------------------------------
    def draw(self, surface, position):
        """Dibuja solo la región visible del mapa usando area=Rect."""
        screen_w, screen_h = surface.get_size()
        offset_x = -position[0]
        offset_y = -position[1]

        src_x = max(0, offset_x)
        src_y = max(0, offset_y)
        src_w = min(screen_w, self.width  - src_x)
        src_h = min(screen_h, self.height - src_y)

        if src_w <= 0 or src_h <= 0:
            return

        dst_x = max(0, position[0])
        dst_y = max(0, position[1])

        surface.blit(self.prev_map, (dst_x, dst_y),
                     area=pygame.Rect(src_x, src_y, src_w, src_h))

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
                pygame.draw.circle(mini_surf, point['color'], (px, py), radius=8)

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