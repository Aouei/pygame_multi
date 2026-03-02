import pygame, os
from typing import Optional

import paths

from enums import ROLE
from inputs import InputHandler
from UI import TextInput

pygame.font.init()


class Screen:
    FRAME_RATE = 60
    ROLE_TEXT_FONT = pygame.font.Font(None, 64)

    def __init__(self, inputs: InputHandler, window):

        self.inputs = inputs
        self.classes: list[tuple[ROLE, pygame.Surface]] = [
            (
                ROLE.ARCHER,
                pygame.image.load(os.path.join(paths.PLAYER_DIR, r"archer\down.png")),
            ),
            (
                ROLE.MAGE,
                pygame.image.load(os.path.join(paths.PLAYER_DIR, r"mage\down.png")),
            ),
            (
                ROLE.FARMER,
                pygame.image.load(os.path.join(paths.PLAYER_DIR, r"farmer\down.png")),
            ),
            (
                ROLE.MUSKETEER,
                pygame.image.load(
                    os.path.join(paths.PLAYER_DIR, r"musketeer\down.png")
                ),
            ),
        ]

        self.current_class: int = 0
        self.size = 20 * self.classes[0][-1].get_rect().width
        self.selection: ROLE | None = None

        self.host = TextInput(window.get_rect(), -100, 0, 200, 40, "25.33.144.47", None, rel_x = 0.5, rel_y = 0.7, max_chars = 15)
        self.port = TextInput(window.get_rect(), -100, 50, 200, 40, "25565", None, rel_x = 0.5, rel_y = 0.7, max_chars = 15)

    def reset(self):
        self.selection = None
        self.inputs._reset()

    def loop(self, window: pygame.Surface, clock) -> Optional[ROLE]:
        while self.selection is None and not self.inputs.quit:
            window.fill((132, 226, 150))
            self.handle_events()
            self.draw(window)
            pygame.display.update()
            clock.tick(self.FRAME_RATE)

        return self.selection

    def handle_events(self):
        self.inputs.update()

        if self.inputs.quit:
            self.selection = None
            return

        if self.inputs.k_left:
            self.current_class = (self.current_class - 1) % len(self.classes)
        if self.inputs.k_right:
            self.current_class = (self.current_class + 1) % len(self.classes)
        if self.inputs.k_enter:
            self.selection = self.classes[self.current_class][0]

        self.host.update(self.inputs)
        self.port.update(self.inputs)

    def draw(self, surface):
        center = list(surface.get_rect().center)

        image_pos = center.copy()
        image_pos[0] -= self.size // 2
        image_pos[1] -= self.size // 2

        self.draw_role_name(surface, center.copy())
        self.host.draw(surface)
        self.port.draw(surface)

        new_surface = pygame.transform.scale(
            self.classes[self.current_class][-1], (self.size, self.size)
        )
        surface.blit(new_surface, image_pos)

    def draw_role_name(self, surface, text_pos):
        role_name = self.classes[self.current_class][0].value.capitalize()
        text_surface = self.ROLE_TEXT_FONT.render(role_name, False, (255, 255, 255))
        text_pos[0] -= text_surface.get_rect().width // 2
        text_pos[1] -= self.size // 2 + text_surface.get_rect().height

        surface.blit(text_surface, text_pos)