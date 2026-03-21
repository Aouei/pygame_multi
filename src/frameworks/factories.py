import os
import pygame

import frameworks.paths as paths
from domain.enums import STATE, ROLE

HEALTH_BAR_HEIGHT = 16
ENEMY_VARIANTS = 4

MAP_SCALE = 4
BULLET_SCALE = 2
SHIP_SCALE = 6
CASTLE_SCALE = 4
PLAYER_SCALE = 4

BASE_COLOR = (66, 172, 175)


def load_scale(path: str, factor: float) -> pygame.Surface:
    return pygame.transform.scale_by(pygame.image.load(path), factor)


def load_player(role: ROLE, scale: float) -> dict[STATE, list[pygame.Surface]]:
    result = {}
    for state in STATE:
        sheet = pygame.image.load(
            os.path.join(paths.PLAYER_DIR, role.value, f"{state.value}.png")
        )
        frame_w = sheet.get_height()
        n_frames = sheet.get_width() // frame_w
        result[state] = [
            pygame.transform.scale_by(
                sheet.subsurface((i * frame_w, 0, frame_w, frame_w)), scale
            )
            for i in range(n_frames)
        ]
    return result


def load_bullet(scale: float) -> dict[ROLE, pygame.Surface]:
    return {
        role: load_scale(os.path.join(paths.BULLET_DIR, f"{role.value}.png"), scale)
        for role in ROLE
    }


_MOVE_STATES = [STATE.UP, STATE.DOWN, STATE.LEFT, STATE.RIGHT]


def load_ship(scale: float) -> dict[STATE, pygame.Surface]:
    return {
        state: load_scale(os.path.join(paths.SHIP_DIR, f"{state.value}.png"), scale)
        for state in _MOVE_STATES
    }


def load_enemy(scale: float) -> list[dict[STATE, pygame.Surface]]:
    enemies = []
    for i in range(ENEMY_VARIANTS):
        enemies.append(
            {
                state: load_scale(
                    os.path.join(paths.ENEMY_DIR, f"{i}", f"{state.value}.png"), scale
                )
                for state in [STATE.LEFT, STATE.RIGHT]
            }
        )
    return enemies


def load_castle(scale: float) -> pygame.Surface:
    return load_scale(paths.CASTLE_PATH, scale)
