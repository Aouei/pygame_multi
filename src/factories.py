import pygame
import os


import paths

from enums import STATE, ROLE


def load_scale(path : str, size : int):
    return pygame.transform.scale(pygame.image.load(path), (size, size))

def load_tiles(size : int = 64):
    tiles = {
        1 : load_scale(os.path.join(paths.TILES_DIR, "tile_1_shore.png"), size),
        2 : load_scale(os.path.join(paths.TILES_DIR, "tile_2_shore.png"), size),
        3 : load_scale(os.path.join(paths.TILES_DIR, "tile_3_shore.png"), size),
        4 : load_scale(os.path.join(paths.TILES_DIR, "tile_4_shore.png"), size),
        5 : load_scale(os.path.join(paths.TILES_DIR, "tile_5_shore.png"), size),
        6 : load_scale(os.path.join(paths.TILES_DIR, "tile_6_grass.png"), size),
        7 : load_scale(os.path.join(paths.TILES_DIR, "tile_7_grass.png"), size),
        8 : load_scale(os.path.join(paths.TILES_DIR, "tile_8_grass.png"), size),
        9 : load_scale(os.path.join(paths.TILES_DIR, "tile_9_grass.png"), size),
        10 : load_scale(os.path.join(paths.TILES_DIR, "tile_10_grass.png"), size),
    }
    
    return tiles


def load_player(role : ROLE, size : int = 64):
    return {
        state : load_scale(os.path.join(paths.PLAYER_DIR, role.value, f'{state.value}.png'), size) for state in STATE
    }

def load_bullet(size : int = 32):
    return {
        role : load_scale(os.path.join(paths.BULLET_DIR, f'{role.value}.png'), size) for role in ROLE
    }