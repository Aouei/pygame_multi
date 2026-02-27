import math
import pygame
import paths
from maps import Map
from enums import ROLE, STATE
from factories import load_bullet, load_player


PLAYER_SIZE = 64
TILE_SIZE = 64
SPAWN_CODE = 8

class ClientState:
    MAP = Map(paths.MAP_PATH)
    PLAYERS = { role : load_player(role, PLAYER_SIZE) for role in ROLE }
    BULLETS = load_bullet()

    COLORS = {
        0 : (0, 0, 0),
        1 : (0, 0, 255),
        2 : (0, 255, 0),
        3 : (255, 0, 0),
    }

    def draw_bullet(self, surface, x: int, y: int, role: str, vx: float, vy: float):
        angle = math.degrees(math.atan2(-vy, vx)) - 90
        rotated = pygame.transform.rotate(self.BULLETS[ROLE(role)], angle)
        rect = rotated.get_rect(center=(x, y))
        surface.blit(rotated, rect)

    def draw_player(self, surface, dx, dy, data : dict):
        x, y, state, role = list(data.values())
        role = ROLE(role)
        surface.blit(self.PLAYERS[ROLE(role)][STATE(state)], 
                     (x - PLAYER_SIZE // 2 + dx, y - PLAYER_SIZE // 2 + dy))