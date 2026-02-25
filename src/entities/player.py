import pygame
import os
from enums import PLAYER_CLASS, STATE


class Player:
    def __init__(self, folder: str, player_class : PLAYER_CLASS) -> None:
        self.states = {
            state : pygame.image.load(os.path.join(folder, player_class.value, f'{state.value}.png')) for state in [STATE.LEFT, 
                                                                                                                    STATE.RIGHT, 
                                                                                                                    STATE.UP, 
                                                                                                                    STATE.DOWN]
        }

        self.current_state = STATE.DOWN
        self.x = 0
        self.y = 0

    def handle_move(self, joystick):
        pass