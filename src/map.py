import pandas as pd
import numpy as np
import random
import pygame

from scipy.spatial import KDTree

import factories
from entities import Geometry
from enums import COLLISIONS


class MapData:
    COMMON_COLLISIONS = {15, 18, 25, 27, 28, 32, 42, 44, 45, 50, 69}
    TILE_SIZE = 64
    COLLISION_TILES = {
        COLLISIONS.PLAYER : {2, 3, 9, *COMMON_COLLISIONS},
        COLLISIONS.BULLET : {4, *COMMON_COLLISIONS},
        COLLISIONS.SHIP : {3},
    }
    NO_TILES = {0}
    SPAWN_CODES = {14}

    def __init__(self, background: str, foreground : str | None = None) -> None:
        self.__load(background, foreground)
        self.__set_collision_tiles()
        self.__set_spawn_positions()

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
                    
    def __set_spawn_positions(self):
        self.spawn_tiles = []
        for i, row in enumerate(self.background):
            for j, col in enumerate(row):
                if col in self.SPAWN_CODES:
                    self.spawn_tiles.append((j, i))
                    
    def spawn(self) -> tuple[int, int]:
        j, i = random.choice(self.spawn_tiles)
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
                image = point['image']
                new_size = image.get_rect().width // 2
                mini_surf.blit(pygame.transform.scale(image, (new_size, new_size)), (px - new_size, py - new_size))

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