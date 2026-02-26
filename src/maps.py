import pandas as pd
import random
import pygame
import os

from scipy.spatial import KDTree

import paths


TILE_SIZE = 64
TILES = {
    str(i): pygame.transform.scale(
        pygame.image.load(os.path.join(paths.TILES_DIR, f"tile_{i}_{'shore' if i <= 5 else 'grass'}.png")),
        (TILE_SIZE, TILE_SIZE),
    )
    for i in range(1, 11)
}

class Map:
    SOLID_TILES = {2}
    SPAWN_CODE = 8

    
    def __init__(self, data_path : str) -> None:
        self.__load(data_path)
        self.__set_collision_tiles()
        self.__set_spawn_positions()
        self.__load_map()

    @property
    def width(self):
        return self.data.shape[-1] * TILE_SIZE

    @property
    def height(self):
        return self.data.shape[0] * TILE_SIZE

    def __load(self, data_path : str):
        self.data = pd.read_csv(data_path, header=None).values

    def __set_collision_tiles(self):
        self.solid_positions = []
        for i, row in enumerate(self.data):
            for j, col in enumerate(row):
                if col in self.SOLID_TILES:
                    self.solid_positions.append((j * TILE_SIZE + TILE_SIZE // 2, 
                                                 i * TILE_SIZE + TILE_SIZE // 2))

        self.solid_tree = KDTree(self.solid_positions) if self.solid_positions else None

    def __set_spawn_positions(self):
        self.spawn_tiles = []
        for i, row in enumerate(self.data):
            for j, col in enumerate(row):
                if col == self.SPAWN_CODE:
                    self.spawn_tiles.append((j, i))

    def spawn(self) -> tuple[int, int]:
        j, i = random.choice(self.spawn_tiles)
        x = j * TILE_SIZE + TILE_SIZE // 2  # centro del tile
        y = i * TILE_SIZE + TILE_SIZE // 2  # centro del tile
    
        return x, y

    def is_collision(self, x, y, surface: pygame.mask.Mask):
        # x, y es el centro del jugador
        # La máscara del jugador tiene origen en su esquina top-left: (x - TILE_SIZE//2, y - TILE_SIZE//2)
        # El offset para mask.overlap es: posición top-left del tile - posición top-left del jugador
        player_left = x - TILE_SIZE // 2
        player_top  = y - TILE_SIZE // 2

        for sx, sy in self.solid_positions:
            # sx, sy es el centro del tile sólido → su top-left es (sx - TILE_SIZE//2, sy - TILE_SIZE//2)
            tile_left = sx - TILE_SIZE // 2
            tile_top  = sy - TILE_SIZE // 2

            tile_mask = pygame.mask.Mask((TILE_SIZE, TILE_SIZE), fill=True)
            offset = (tile_left - player_left, tile_top - player_top)
            if surface.overlap(tile_mask, offset):
                return True
                
        return False
    
    def __load_map(self):
        self.prev_map = pygame.Surface((self.data.shape[-1] * TILE_SIZE, self.data.shape[0] * TILE_SIZE))
        for i, row in enumerate(self.data):
            for j, col in enumerate(row):
                self.prev_map.blit(TILES[str(col)], (j * TILE_SIZE, i * TILE_SIZE))
    
    def draw(self, surface, position):
        surface.blit(self.prev_map, position)