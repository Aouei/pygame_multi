import pygame, sys, os

import paths

from enums import ROLE
from inputs import InputHandler


class Screen():
    def __init__(self, inputs : InputHandler):
        self.inputs = inputs
        self.classes = [
            (ROLE.ARCHER, 
                pygame.image.load(os.path.join(paths.PLAYER_DIR, r"archer\down.png"))),
            (ROLE.MAGE, 
                pygame.image.load(os.path.join(paths.PLAYER_DIR, r"mage\down.png"))),
            (ROLE.FARMER, 
                pygame.image.load(os.path.join(paths.PLAYER_DIR, r"farmer\down.png"))),
            (ROLE.MUSKETEER, 
                pygame.image.load(os.path.join(paths.PLAYER_DIR, r"musketeer\down.png"))),
        ]

        self.current_class : int = 0
        self.size = 20 * self.classes[0][-1].get_rect().width
        self.selection : ROLE | None = None

    def loop(self, window: pygame.Surface, clock, frames) -> ROLE:
        while self.selection is None:
            window.fill((132, 226, 150)) 
            self.handle_events()
            self.draw(window)
            pygame.display.update()
            clock.tick(frames)

        return self.selection

    def handle_events(self):
        self.inputs.update()
        
        if self.inputs.quit:
            pygame.quit()
            sys.exit()

        if self.inputs.k_left:
            self.current_class = (self.current_class - 1) % len(self.classes)
        if self.inputs.k_right:
            self.current_class = (self.current_class + 1) % len(self.classes)
        if self.inputs.k_enter:
            self.selection = self.classes[self.current_class][0]

    def draw(self, surface):
        pos = list(surface.get_rect().center)
        pos[0] -= self.size // 2
        pos[1] -= self.size // 2

        new_surface = pygame.transform.scale(self.classes[self.current_class][-1], (self.size, self.size))

        surface.blit(new_surface, pos)