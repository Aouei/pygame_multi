from pathlib import Path
import pygame
import os


import paths

from enums import STATE, ROLE

TILE_SIZE = 64
PLAYER_SIZE = 64
ENEMY_SIZE = 64
SHIP_SIZE = 128
BULLET_SIZE = 32
ENEMY_VARIANTS = 4
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

def load_enemy(size : int = ENEMY_SIZE):
    enemies = []
    for i in range(ENEMY_VARIANTS):
        enemies.append({
        state : load_scale(os.path.join(paths.ENEMY_DIR, f'{i}', f'{state.value}.png'), size) for state in [STATE.LEFT, STATE.RIGHT]
        })

    return enemies