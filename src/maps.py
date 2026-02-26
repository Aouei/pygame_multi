import pandas as pd
import random
import pygame


from scipy.spatial import KDTree

import factories


class Map:
    SOLID_TILES = {2}
    NO_TILES = {0}
    SPAWN_CODE = 7
    MINMAP_SCALE = 0.1
    TILE_SIZE = 64
    TILES = factories.load_tiles(TILE_SIZE)
    
    def __init__(self, data_path : str) -> None:
        self.__load(data_path)
        self.__set_collision_tiles()
        self.__set_spawn_positions()
        self.__load_map()
        self.__load_minimap()

    @property
    def width(self):
        return self.data.shape[-1] * self.TILE_SIZE

    @property
    def height(self):
        return self.data.shape[0] * self.TILE_SIZE

    def __load(self, data_path : str):
        self.data = pd.read_csv(data_path, header=None).values

    def __set_collision_tiles(self):
        self.solid_positions = []
        for i, row in enumerate(self.data):
            for j, col in enumerate(row):
                if col in self.SOLID_TILES:
                    self.solid_positions.append((j * self.TILE_SIZE + self.TILE_SIZE // 2, 
                                                 i * self.TILE_SIZE + self.TILE_SIZE // 2))

        self.solid_tree = KDTree(self.solid_positions) if self.solid_positions else None

    def __set_spawn_positions(self):
        self.spawn_tiles = []
        for i, row in enumerate(self.data):
            for j, col in enumerate(row):
                if col == self.SPAWN_CODE:
                    self.spawn_tiles.append((j, i))

    def spawn(self) -> tuple[int, int]:
        j, i = random.choice(self.spawn_tiles)
        x = j * self.TILE_SIZE + self.TILE_SIZE // 2  # centro del tile
        y = i * self.TILE_SIZE + self.TILE_SIZE // 2  # centro del tile
        return x, y

    def is_collision(self, x, y, mask: pygame.mask.Mask):
        if self.solid_tree is None:
            return False

        player_size = mask.get_size()[0]
        search_radius = self.TILE_SIZE + player_size // 2
        nearby_indices = self.solid_tree.query_ball_point([x, y], search_radius)

        player_left = x - player_size // 2
        player_top  = y - player_size // 2

        for idx in nearby_indices:
            sx, sy = self.solid_positions[idx]
            tile_left = sx - self.TILE_SIZE // 2
            tile_top  = sy - self.TILE_SIZE // 2
            tile_mask = pygame.mask.Mask((self.TILE_SIZE, self.TILE_SIZE), fill=True)
            offset = (tile_left - player_left, tile_top - player_top)
            if mask.overlap(tile_mask, offset):
                return True

        return False
    
    def __load_map(self):
        self.prev_map = pygame.Surface((self.data.shape[-1] * self.TILE_SIZE, self.data.shape[0] * self.TILE_SIZE))
        for i, row in enumerate(self.data):
            for j, col in enumerate(row):
                if col not in self.NO_TILES:
                    self.prev_map.blit(self.TILES[col], (j * self.TILE_SIZE, i * self.TILE_SIZE))

    def __load_minimap(self):
        # Pre-renderizamos el minimap una sola vez en init, sin puntos de jugadores
        mini_w = int(self.width  * self.MINMAP_SCALE)
        mini_h = int(self.height * self.MINMAP_SCALE)
        scaled = pygame.transform.scale(self.prev_map, (mini_w, mini_h))
        pygame.draw.rect(scaled, (255, 255, 255), scaled.get_rect(), width=2)
        self.mini_map = scaled
        self.mini_scale = self.MINMAP_SCALE

    def draw(self, surface, position):
        # Solo transferimos los píxeles visibles en pantalla usando el parámetro area
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

    def draw_mini(self, surface: pygame.Surface, dx, dy, points):
        # Bliteamos el minimap pre-renderizado y dibujamos los puntos encima directamente en pantalla
        surface.blit(self.mini_map, (dx, dy))
        mini_rect = self.mini_map.get_rect().move(dx, dy)
        for point in points:
            px = int(dx + point['x'] * self.mini_scale)
            py = int(dy + point['y'] * self.mini_scale)
            if mini_rect.collidepoint(px, py):
                pygame.draw.circle(surface, point['color'], (px, py), radius=3)
        pygame.draw.rect(surface, (255, 255, 255), mini_rect, width=2)