import pygame

from inputs import InputHandler


class TextInput:
    ACTIVE_COLOR = (255, 255, 255)
    INACTIVE_COLOR = (100, 100, 100)

    def __init__(self, text : str, font : pygame.font.Font, position : pygame.Rect, active : bool = False) -> None:
        self.font = font
        self.text = text
        self.active = active
        self.position = position

    def update(self, input : InputHandler):
        if input.shot:
            if self.position.collidepoint(input.mouse_pos):
                self.active = True
            else:
                self.active = False
        
        if self.active:
            if input.delete_char:
                self.text = self.text[:-1]
            else:
                self.text += input.current_char

    def draw(self, surface : pygame.Surface):
        color = self.ACTIVE_COLOR if self.active else self.INACTIVE_COLOR

        surface.blit(self.font.render(self.text, False, self.ACTIVE_COLOR), self.position) # change text_color to init
        pygame.draw.rect(surface, color, self.position, width = 2)