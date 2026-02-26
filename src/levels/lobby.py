import pygame, sys, os

from enums import PLAYER_CLASS
from inputs import InputHandler


class Screen():
    def __init__(self, inputs : InputHandler, folder : str):
        self.inputs = inputs
        self.classes = [
            (PLAYER_CLASS.ARCHER, 
                pygame.image.load( os.path.join(folder, r"archer\down.png"))),
            (PLAYER_CLASS.MAGE, 
                pygame.image.load(os.path.join(folder, r"mage\down.png"))),
            (PLAYER_CLASS.FARMER, 
                pygame.image.load(os.path.join(folder, r"farmer\down.png"))),
            (PLAYER_CLASS.MUSKETEER, 
                pygame.image.load(os.path.join(folder, r"musketeer\down.png"))),
        ]

        self.current_class : int = 0
        self.size = 20 * self.classes[0][-1].get_rect().width
        self.selection : PLAYER_CLASS | None = None

    def loop(self, window: pygame.Surface, clock, frames) -> PLAYER_CLASS:
        while self.selection is None:
            window.fill((0, 0, 0))
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