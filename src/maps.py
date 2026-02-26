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
        # x, y es el centro del jugador
        # Solo comprobamos tiles cercanos usando el KDTree
        if self.solid_tree is None:
            return False

        player_size = mask.get_size()[0]  # tamaño real de la máscara del jugador
        search_radius = self.TILE_SIZE + player_size // 2

        nearby_indices = self.solid_tree.query_ball_point([x, y], search_radius)

        player_left = x - player_size // 2
        player_top  = y - player_size // 2

        for idx in nearby_indices:
            sx, sy = self.solid_positions[idx]
            # sx, sy es el centro del tile → top-left es (sx - self.TILE_SIZE//2, sy - self.TILE_SIZE//2)
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
                if not col in self.NO_TILES:
                    self.prev_map.blit(self.TILES[col], (j * self.TILE_SIZE, i * self.TILE_SIZE))
    
    def draw(self, surface, position):
        surface.blit(self.prev_map, position)

    def draw_mini(self, surface : pygame.Surface, dx, dy, points):
        temp = self.prev_map.copy()
    
        for point in points:
            pygame.draw.circle(temp, point['color'], (point['x'], point['y']), radius = 32)
    
        temp = pygame.transform.scale(temp, (self.width * self.MINMAP_SCALE, self.height * self.MINMAP_SCALE))
        pygame.draw.rect(temp, (255, 255, 255), temp.get_rect(), width = 5)

        surface.blit(temp, (dx, dy))