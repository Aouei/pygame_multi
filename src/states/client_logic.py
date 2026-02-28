import math
import pygame
from enums import ROLE, STATE
from states.client_state import State


PLAYER_SIZE = 64
TILE_SIZE = 64
SPAWN_CODE = 8

class Logic:
    STATE = State()

    def reset(self):
        self.STATE.players_positions.clear()
        self.STATE.bullets_positions.clear()
        self.STATE.ID = -1

    @property
    def player(self):
        return self.STATE.player

    @property
    def ID(self):
        return self.STATE.ID
    
    @ID.setter
    def ID(self, value):
        self.STATE.ID = value

    def update_players(self, players : dict):
        self.STATE.players_positions = players

        self.player.update(self.STATE.players_positions.get(self.ID, {}))

    def update_bullets(self, bullets : dict):
        self.STATE.bullets_positions = bullets

    def draw(self, surface, dx, dy):
        self.STATE.MAP.draw(surface, (dx, dy))
        for player in self.STATE.players_positions.copy().values():
            self.draw_player(surface, dx, dy, player)

        for bullet in self.STATE.bullets_positions.copy():
            print(bullet)
            x, y, role, vx, vy = bullet['x'], bullet['y'], bullet['role'], bullet['dx'], bullet['dy']
            self.draw_bullet(surface, x + dx, y + dy, role, vx, vy)

        minmap_points = []
        for data in self.STATE.players_positions.copy().values():
            minmap_points.append({'x' : data['x'], 'y' : data['y'], 'image' : self.STATE.PLAYERS[ROLE(data['role'])][STATE.DOWN]} )

        self.STATE.MAP.draw_mini(surface, 16, 16, minmap_points, self.player.pos.x, self.player.pos.y)

    def draw_bullet(self, surface, x: int, y: int, role: str, vx: float, vy: float):
        angle = math.degrees(math.atan2(-vy, vx)) - 90
        rotated = pygame.transform.rotate(self.STATE.BULLETS[ROLE(role)], angle)
        rect = rotated.get_rect(center=(x, y))
        surface.blit(rotated, rect)

    def draw_player(self, surface, dx, dy, data : dict):
        x = data['x']
        y = data['y']
        state = STATE(data['state'])
        role = ROLE(data['role'])

        surface.blit(self.STATE.PLAYERS[role][state], 
                     (x - PLAYER_SIZE // 2 + dx, y - PLAYER_SIZE // 2 + dy))