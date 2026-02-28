from pathlib import Path
import pygame
import os


import paths

from enums import STATE, ROLE

def load_scale(path : str, size : int):
    return pygame.transform.scale(pygame.image.load(path), (size, size))

def load_tiles(size : int = 64):
    return { int(filename.stem.split('_')[-1]) : load_scale(str(filename), size) for filename in Path(paths.TILES_DIR).glob('*') }

def load_player(role : ROLE, size : int = 64):
    return {
        state : load_scale(os.path.join(paths.PLAYER_DIR, role.value, f'{state.value}.png'), size) for state in STATE
    }

def load_bullet(size : int = 32):
    return {
        role : load_scale(os.path.join(paths.BULLET_DIR, f'{role.value}.png'), size) for role in ROLE
    }