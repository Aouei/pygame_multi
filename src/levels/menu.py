import pygame
import pygame_gui

from pygame.time import Clock
from frameworks.inputs import InputHandler
from frameworks.ui_utils import build_controls_surface


class Screen:
    FRAME_RATE = 60

    def __init__(self, window: pygame.Surface, inputs: InputHandler, clock: Clock) -> None:
        self.window = window
        self.inputs = inputs
        self.clock = clock

        self._show_controls = False
        self._controls_surface = build_controls_surface()

        self.manager = pygame_gui.UIManager(window.get_size())
        self._build_ui()

    def _build_ui(self):
        W, H = self.window.get_size()
        btn_w, btn_h, gap = 220, 50, 16
        x = (W - btn_w) // 2
        y = H // 2 - (3 * btn_h + 2 * gap) // 2

        self._btn_play = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(x, y, btn_w, btn_h),
            text="Jugar",
            manager=self.manager,
        )
        self._btn_controls = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(x, y + btn_h + gap, btn_w, btn_h),
            text="Controles",
            manager=self.manager,
        )
        self._btn_quit = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(x, y + 2 * (btn_h + gap), btn_w, btn_h),
            text="Salir",
            manager=self.manager,
        )

    def loop(self) -> str:
        while True:
            time_delta = self.clock.tick(self.FRAME_RATE) / 1000.0
            result = self._handle_events(time_delta)
            if result is not None:
                return result

            self.window.fill((132, 226, 150))
            self.manager.draw_ui(self.window)
            if self._show_controls:
                s = self._controls_surface
                x = (self.window.get_width()  - s.get_width())  // 2
                y = (self.window.get_height() - s.get_height()) // 2
                self.window.blit(s, (x, y))
            pygame.display.flip()

    def _handle_events(self, time_delta: float):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "quit"

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if self._show_controls:
                        self._show_controls = False
                    else:
                        return "quit"
                elif event.key == pygame.K_m:
                    self._show_controls = not self._show_controls

            if event.type == pygame_gui.UI_BUTTON_PRESSED:
                if event.ui_element == self._btn_play:
                    return "play"
                elif event.ui_element == self._btn_controls:
                    self._show_controls = not self._show_controls
                elif event.ui_element == self._btn_quit:
                    return "quit"

            self.manager.process_events(event)

        # toggle desde mando
        if self.inputs.toggle_controls:
            self._show_controls = not self._show_controls

        self.manager.update(time_delta)
        return None
