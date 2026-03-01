import math
import pygame
from enums import ROLE, STATE
from states.client_state import State
from factories import PLAYER_SIZE, SHIP_SIZE, HEALTH_BAR_HEIGHT
from protocols import LivingEntity
from entities import Player, Ship, Bullet

class Logic:
    STATE = State()
    DEBUG = True

    def reset(self):
        self.STATE.received_players.clear()
        self.STATE.received_bullets.clear()
        self.STATE.received_ships.clear()
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
        self.STATE.received_players.clear()

        for idd, player in players.items():
            self.STATE.received_players[idd] = Player(ROLE.MAGE, 0, 0)
            self.STATE.received_players[idd].update(player)
            
        self.player.update(players.get(self.ID, {}))

    def update_bullets(self, bullets : list):
        self.STATE.received_bullets.clear()

        for bullet in bullets:
            self.STATE.received_bullets.append(Bullet(0, 0, 0, 0, ROLE.MAGE))
            self.STATE.received_bullets[-1].update(bullet)

    def update_ships(self, ships : list):
        self.STATE.received_ships.clear()

        for ship in ships:
            self.STATE.received_ships.append(Ship(0, 0, []))
            self.STATE.received_ships[-1].update(ship)

    def draw(self, surface, dx, dy):
        self.STATE.MAP.draw_layer(surface, (dx, dy), self.STATE.MAP.background)

        for player in self.STATE.received_players.copy().values():
            self.draw_player(surface, dx, dy, player)

            if isinstance(player, LivingEntity):
                self.draw_health_bar(surface, 
                                     player.x - PLAYER_SIZE // 2 + dx, 
                                     player.y - PLAYER_SIZE // 2 - HEALTH_BAR_HEIGHT + dy, 
                                     PLAYER_SIZE,
                                     HEALTH_BAR_HEIGHT,
                                     player)

        for ship in self.STATE.received_ships.copy():
            self.draw_ship(surface, dx, dy, ship)

            if isinstance(ship, LivingEntity):
                self.draw_health_bar(surface, 
                                     ship.x - SHIP_SIZE // 2 + dx, 
                                     ship.y - SHIP_SIZE // 2 - HEALTH_BAR_HEIGHT + dy, 
                                     SHIP_SIZE, HEALTH_BAR_HEIGHT,
                                     ship)

        for bullet in self.STATE.received_bullets.copy():
            self.draw_bullet(surface, bullet.x + dx, bullet.y + dy, bullet.role, bullet.dx, bullet.dy)

        self.STATE.MAP.draw_layer(surface, (dx, dy), self.STATE.MAP.foreground)

        self.draw_minimap(surface)

    def draw_minimap(self, surface):
        minmap_points = []
        for player in self.STATE.received_players.copy().values():
            minmap_points.append({'x' : player.x, 'y' : player.y, 'image' : 
                                  pygame.transform.scale(self.STATE.PLAYERS[player.role][player.state], (16, 16))}, ) 
        for ship in self.STATE.received_ships.copy():
            minmap_points.append({'x' : ship.x, 'y' : ship.y, 'image' : 
                                  pygame.transform.scale(self.STATE.SHIPS[ship.state], (32, 32))} )
        
        minmap_points.append({'x' : self.player.x, 'y' : self.player.y, 'image' : 
                                  pygame.transform.scale(self.STATE.PLAYERS[self.player.role][self.player.state], (16, 16))}, )

        self.STATE.MAP.draw_mini(surface, 16, 16, minmap_points, self.player.x, self.player.y)

    def draw_bullet(self, surface, x: int, y: int, role: ROLE, dx: float, dy: float):
        angle = math.degrees(math.atan2(-dy, dx)) - 90
        rotated = pygame.transform.rotate(self.STATE.BULLETS[role], angle)
        rect = rotated.get_rect(center=(x, y))
        surface.blit(rotated, rect)

    def draw_player(self, surface, dx, dy, player : Player):
        surface.blit(self.STATE.PLAYERS[player.role][player.state],
                     (player.x - PLAYER_SIZE // 2 + dx, player.y - PLAYER_SIZE // 2 + dy))

        if self.DEBUG:
            pygame.draw.circle(surface, (255, 0, 0), (player.x + dx, player.y + dy), player.radius, 1)

    def draw_ship(self, surface, dx, dy, ship : Ship):
        surface.blit(self.STATE.SHIPS[ship.state],
                     (ship.x - SHIP_SIZE // 2 + dx, ship.y - SHIP_SIZE // 2 + dy))
    
        if self.DEBUG:
            pygame.draw.circle(surface, (255, 0, 0), (ship.x + dx, ship.y + dy), ship.radius, 1)
        
    def draw_health_bar(self, surface, x, y, width, height, entity : LivingEntity):
        base_rect = (x, y,  width, height)
        current_rect = (x, y, width * (entity.live / entity.max_live), height)

        pygame.draw.rect(surface, (0, 0, 0), base_rect)
        pygame.draw.rect(surface, (248, 117, 117), current_rect)
        pygame.draw.rect(surface, (255, 255, 255), base_rect, width = 2)