import math
import pygame
from enums import ROLE, STATE
from states.client_state import State
from factories import PLAYER_SIZE, SHIP_SIZE

class Logic:
    STATE = State()
    DEBUG = True

    def reset(self):
        self.STATE.players_positions.clear()
        self.STATE.bullets_positions.clear()
        self.STATE.ships_positions.clear()
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

    def update_bullets(self, bullets : list):
        self.STATE.bullets_positions = bullets

    def update_ships(self, ships : list):
        self.STATE.ships_positions = ships

    def draw(self, surface, dx, dy):
        self.STATE.MAP.draw_layer(surface, (dx, dy), self.STATE.MAP.background)

        for player in self.STATE.players_positions.copy().values():
            self.draw_player(surface, dx, dy, player)

        for ship in self.STATE.ships_positions.copy():
            self.draw_ship(surface, dx, dy, ship)

        for bullet in self.STATE.bullets_positions.copy():
            x, y, role, vx, vy = bullet['x'], bullet['y'], bullet['role'], bullet['dx'], bullet['dy']
            self.draw_bullet(surface, x + dx, y + dy, role, vx, vy)

        self.STATE.MAP.draw_layer(surface, (dx, dy), self.STATE.MAP.foreground)

        self.draw_minimap(surface)

    def draw_minimap(self, surface):
        minmap_points = []
        for data in self.STATE.players_positions.copy().values():
            minmap_points.append({'x' : data['x'], 'y' : data['y'], 'image' : 
                                  pygame.transform.scale(self.STATE.PLAYERS[ROLE(data['role'])][STATE(data['state'])], (16, 16))}, ) 
        for data in self.STATE.ships_positions.copy():
            minmap_points.append({'x' : data['x'], 'y' : data['y'], 'image' : 
                                  pygame.transform.scale(self.STATE.SHIPS[STATE(data['state'])], (32, 32))} )
        
        minmap_points.append({'x' : self.player.x, 'y' : self.player.y, 'image' : 
                                  pygame.transform.scale(self.STATE.PLAYERS[self.player.role][self.player.state], (16, 16))}, )

        self.STATE.MAP.draw_mini(surface, 16, 16, minmap_points, self.player.x, self.player.y)

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

        if self.DEBUG:
            pygame.draw.circle(surface, (255, 0, 0), (x + dx, y + dy), data['radius'], 1)

    def draw_ship(self, surface, dx, dy, data : dict):
        x = data['x']
        y = data['y']
        state = STATE(data['state'])

        surface.blit(self.STATE.SHIPS[state],
                     (x - SHIP_SIZE // 2 + dx, y - SHIP_SIZE // 2 + dy))