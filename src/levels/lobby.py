import pygame


from enums import PLAYER_CLASS
from utils import exit_game

class Screen():
    def __init__(self, size : int):
        self.classes = [
            (PLAYER_CLASS.ARCHER, 
                pygame.image.load(r"C:\Users\sergi\Documents\repos\pygame_multi\assets\player\archer\down.png")),
            (PLAYER_CLASS.MAGE, 
                pygame.image.load(r"C:\Users\sergi\Documents\repos\pygame_multi\assets\player\mage\down.png")),
            (PLAYER_CLASS.FARMER, 
                pygame.image.load(r"C:\Users\sergi\Documents\repos\pygame_multi\assets\player\farmer\down.png")),
            (PLAYER_CLASS.MUSKETEER, 
                pygame.image.load(r"C:\Users\sergi\Documents\repos\pygame_multi\assets\player\musketeer\down.png")),
        ]

        self.current_class : int = 0
        self.size = size * self.classes[0][-1].get_rect().width
        self.selection : PLAYER_CLASS | None = None

    def loop(self, window: pygame.Surface, clock, frames) -> PLAYER_CLASS:
        while self.selection is None:
            exit_game()
            window.fill((0, 0, 0))
            self.handle_input()

            self.draw(window)
            pygame.display.update()
            clock.tick(frames)

        return self.selection

    def handle_input(self):
        for event in pygame.event.get():
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_LEFT:
                    self.current_class = (self.current_class - 1) % len(self.classes)
                elif event.key == pygame.K_RIGHT:
                    self.current_class = (self.current_class + 1) % len(self.classes)
                elif event.key == pygame.K_RETURN:
                    self.selection = self.classes[self.current_class][0]

    def draw(self, surface):
        pos = list(surface.get_rect().center)
        pos[0] -= self.size // 2
        pos[1] -= self.size // 2

        new_surface = pygame.transform.scale(self.classes[self.current_class][-1], (self.size, self.size))

        surface.blit(new_surface, pos)