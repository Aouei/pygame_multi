import pygame

from dataclasses import dataclass
from inputs import InputHandler


@dataclass
class PlaceableUI:
    parent : pygame.Rect
    x : int
    y : int
    w : int
    h : int
    rel_x : float = 0 
    rel_y : float = 0
    
    @property
    def position(self) -> pygame.Rect:
        pos = pygame.Rect(self.x, self.y, self.w, self.h)

        dx = self.parent.x + self.parent.w * self.rel_x
        dy = self.parent.y + self.parent.h * self.rel_y

        return pos.move(dx, dy)


class TextInput(PlaceableUI):
    ACTIVE_COLOR = (255, 255, 255)
    INACTIVE_COLOR = (100, 100, 100)
    MARGIN = 5

    def __init__(
        self,
        parent : pygame.Rect,
        x : int,
        y : int,
        w : int,
        h : int,
        text: str,
        font: str | None,
        active: bool = False,
        rel_y : float = 0,
        rel_x : float = 0,
        max_chars : int = 15,
    ) -> None:
        super().__init__(parent, x, y, w, h, rel_x, rel_y)
        self.font = pygame.font.Font(font, 32)
        self.text = text
        self.active = active
        self.max_chars = max_chars

    @property
    def value(self) -> str:
        return self.text

    def update(self, input: InputHandler):
        if input.click:
            if self.position.collidepoint(input.mouse_pos):
                self.active = True
            else:
                self.active = False

        if self.active:
            if input.delete_char:
                self.text = self.text[:-1]
            elif len(self.text) + 1 <= self.max_chars:
                self.text += input.current_char

    def draw(self, surface: pygame.Surface):
        color = self.ACTIVE_COLOR if self.active else self.INACTIVE_COLOR

        text_pos = self.position.copy()
        text_pos.x += self.MARGIN
        text_pos.y += self.MARGIN

        surface.blit(
            self.font.render(self.text, False, self.ACTIVE_COLOR), text_pos
        )  # change text_color to init
        pygame.draw.rect(surface, color, self.position, width=2)


class TextButton(PlaceableUI):
    COLOR = (80, 80, 80)
    HOVER_COLOR = (120, 120, 120)
    TEXT_COLOR = (255, 255, 255)

    def __init__(
        self,
        parent: pygame.Rect,
        x: int,
        y: int,
        w: int,
        h: int,
        text: str,
        font: str | None,
        rel_y: float = 0,
        rel_x: float = 0,
    ) -> None:
        super().__init__(parent, x, y, w, h, rel_x, rel_y)
        self.font = pygame.font.Font(font, 32)
        self.text = text
        self.clicked = False
        self._hovered = False

    def update(self, input: InputHandler):
        self._hovered = self.position.collidepoint(input.mouse_pos)
        self.clicked = self._hovered and input.click

    def draw(self, surface: pygame.Surface):
        color = self.HOVER_COLOR if self._hovered else self.COLOR
        pygame.draw.rect(surface, color, self.position)
        pygame.draw.rect(surface, self.TEXT_COLOR, self.position, width=2)
        text_surf = self.font.render(self.text, False, self.TEXT_COLOR)
        surface.blit(text_surf, text_surf.get_rect(center=self.position.center))


class TextLabel(PlaceableUI):
    def __init__(
        self,
        parent: pygame.Rect,
        x: int,
        y: int,
        text: str,
        font: str | None,
        size: int,
        color: tuple,
        rel_x: float = 0,
        rel_y: float = 0,
    ) -> None:
        super().__init__(parent, x, y, 0, 0, rel_x, rel_y)
        self.font = pygame.font.Font(font, size)
        self.text = text
        self.color = color

    def draw(self, surface: pygame.Surface):
        surface.blit(self.font.render(self.text, False, self.color), self.position.topleft)
