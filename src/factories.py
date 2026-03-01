from pathlib import Path
import pygame
import os


import paths

from enums import STATE, ROLE

TILE_SIZE = 64
PLAYER_SIZE = 64
BULLET_SIZE = 32
SHIP_SIZE = 128
HEALTH_BAR_HEIGHT = 16

def load_scale(path : str, size : int):
    return pygame.transform.scale(pygame.image.load(path), (size, size))

def load_tiles(size : int = TILE_SIZE):
    return { int(filename.stem.split('_')[-1]) : load_scale(str(filename), size) for filename in Path(paths.TILES_DIR).glob('*') }

def load_player(role : ROLE, size : int = PLAYER_SIZE):
    return {
        state : load_scale(os.path.join(paths.PLAYER_DIR, role.value, f'{state.value}.png'), size) for state in STATE
    }

def load_bullet(size : int = BULLET_SIZE):
    return {
        role : load_scale(os.path.join(paths.BULLET_DIR, f'{role.value}.png'), size) for role in ROLE
    }

def load_ship(size : int = SHIP_SIZE):
    return {
        state : load_scale(os.path.join(paths.SHIP_DIR, f'{state.value}.png'), size) for state in STATE
    }