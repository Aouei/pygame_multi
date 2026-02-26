import pygame
import os
from enums import PLAYER_CLASS, STATE


class Player:
    PLAYER_SIZE = 64

    def __init__(self, inputs, folder: str, player_class : PLAYER_CLASS) -> None:
        self.states = {
            state : pygame.image.load(os.path.join(folder, player_class.value, f'{state.value}.png')) for state in [STATE.LEFT, 
                                                                                                                    STATE.RIGHT, 
                                                                                                                    STATE.UP, 
                                                                                                                    STATE.DOWN]
        }

        self.masks = {
            state : pygame.mask.from_surface(surface) for state, surface in self.states.items()
        }

        self.player_class = player_class
        self.current_state = STATE.DOWN
        self.speed = 5
        self.x = 0
        self.y = 0

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
        # x, y es el centro → top-left para blit es (x - PLAYER_SIZE//2, y - PLAYER_SIZE//2)
        position = (self.x - self.PLAYER_SIZE // 2 + dx,
                    self.y - self.PLAYER_SIZE // 2 + dy,
                    self.PLAYER_SIZE, self.PLAYER_SIZE)
        image = pygame.transform.scale(self.states[self.current_state],
                                       (self.PLAYER_SIZE, self.PLAYER_SIZE))
        surface.blit(image, position)