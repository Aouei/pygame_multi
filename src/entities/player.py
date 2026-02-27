import pygame
import os

from enums import PLAYER_CLASS, STATE
from factories import load_player, load_bullet


class Player:
    PLAYER_SIZE = 64
    BULLET_SIZE = 32

    def __init__(self, inputs, folder: str, player_class : PLAYER_CLASS) -> None:
        self.states = load_player(player_class, self.PLAYER_SIZE)
        self.masks = {
            state : pygame.mask.from_surface(surface) for state, surface in self.states.items()
        }

        self.player_class = player_class
        self.current_state = STATE.DOWN
        self.speed = 5
        self.x = 0
        self.y = 0

        self.bullet = Bullet(player_class, self.BULLET_SIZE)

    @property
    def class_type(self):
        return self.player_class.value
        
    @property
    def mask(self):
        return self.masks[self.current_state]

    def wish_to_move(self, inputs) -> tuple[int, int, str]:
        dx, dy = 0, 0

        if inputs.con_left:
            dx = -self.speed
            self.current_state = STATE.LEFT
        if inputs.con_right:
            dx =  self.speed
            self.current_state = STATE.RIGHT
        if inputs.con_up:
            dy = -self.speed
            self.current_state = STATE.UP
        if inputs.con_down:
            dy =  self.speed
            self.current_state = STATE.DOWN

        return dx, dy, self.current_state.value
    
    def move(self, new_x : int, new_y : int, state : str) -> None:
        self.x = new_x
        self.y = new_y
        self.current_state = STATE(state)

    def dump(self) -> dict:
        summary =  {
            'x' : self.x, 
            'y' : self.y, 
            'state' : self.current_state.value,
            'type_class' : self.class_type,
        }

        return summary
    
    def draw(self, surface, dx, dy):
        position = (self.x - self.PLAYER_SIZE // 2 + dx,
                    self.y - self.PLAYER_SIZE // 2 + dy)
        surface.blit(self.states[self.current_state], position)


class Bullet:
    def __init__(self, player_class : PLAYER_CLASS, size : int) -> None:
        self.image = load_bullet(player_class, size)
        self.mask = pygame.mask.from_surface(self.image)
        self.x = 0
        self.y = 0
        self.size = size

    def draw(self, surface, dx, dy):
        position = (self.x - self.size // 2 + dx,
                    self.y - self.size // 2 + dy)
        surface.blit(self.image, position)