import pygame
from pygame.time import Clock


_LAYOUT = [
    list("1234567890"),
    list("QWERTYUIOP"),
    list("ASDFGHJKL."),
    list("ZXCVBNM@-_"),
    ["ESPACIO", "BORRAR", "ACEPTAR"],
]

_KEY_W   = 48
_KEY_H   = 44
_GAP     = 6
_PAD     = 20
_TEXT_H  = 50


class VirtualKeyboard:
    FRAME_RATE = 60

    def __init__(self, initial_text: str = "") -> None:
        self.text = initial_text
        self._row = 0
        self._col = 0
        self._cursor_visible = True
        self._cursor_timer = 0

        self._font_key  = pygame.font.Font(None, 26)
        self._font_text = pygame.font.Font(None, 34)

        # pre-calcular tamaño del panel
        max_keys    = max(len(row) for row in _LAYOUT[:-1])
        row_count   = len(_LAYOUT)
        panel_w     = _PAD * 2 + max_keys * _KEY_W + (max_keys - 1) * _GAP
        panel_h     = _PAD * 2 + _TEXT_H + row_count * _KEY_H + (row_count - 1) * _GAP
        self._panel_size = (panel_w, panel_h)

    # ------------------------------------------------------------------

    def run(self, window: pygame.Surface, clock: Clock) -> str | None:
        while True:
            dt = clock.tick(self.FRAME_RATE)
            self._cursor_timer += dt
            if self._cursor_timer >= 500:
                self._cursor_visible = not self._cursor_visible
                self._cursor_timer = 0

            for event in pygame.event.get():
                result = self._handle_event(event)
                if result is not None:
                    return result

            self._draw(window)
            pygame.display.flip()

    # ------------------------------------------------------------------

    def _handle_event(self, event) -> str | None:
        row = _LAYOUT[self._row]

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                return None
            elif event.key == pygame.K_BACKSPACE:
                self.text = self.text[:-1]
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                return self._activate_current()
            elif event.key == pygame.K_UP:
                self._move(-1, 0)
            elif event.key == pygame.K_DOWN:
                self._move(1, 0)
            elif event.key == pygame.K_LEFT:
                self._col = max(0, self._col - 1)
            elif event.key == pygame.K_RIGHT:
                self._col = min(len(row) - 1, self._col + 1)
            elif event.unicode:
                self.text += event.unicode

        elif event.type == pygame.JOYHATMOTION:
            hx, hy = event.value
            if hy == 1:
                self._move(-1, 0)
            elif hy == -1:
                self._move(1, 0)
            if hx == -1:
                self._col = max(0, self._col - 1)
            elif hx == 1:
                row_len = len(_LAYOUT[self._row])
                self._col = min(row_len - 1, self._col + 1)

        elif event.type == pygame.JOYBUTTONDOWN:
            if event.button == 0:
                return self._activate_current()
            elif event.button == 1:
                self.text = self.text[:-1]
            elif event.button == 6:
                return None

        return None  # still active

    def _move(self, drow: int, dcol_hint: int):
        new_row = (self._row + drow) % len(_LAYOUT)
        new_col = min(self._col, len(_LAYOUT[new_row]) - 1)
        self._row = new_row
        self._col = new_col

    def _activate_current(self) -> str | None:
        key = _LAYOUT[self._row][self._col]
        if key == "ACEPTAR":
            return self.text
        elif key == "BORRAR":
            self.text = self.text[:-1]
        elif key == "ESPACIO":
            self.text += " "
        else:
            self.text += key
        return None

    # ------------------------------------------------------------------

    def _draw(self, window: pygame.Surface):
        pw, ph = self._panel_size
        wx, wy = window.get_size()
        ox = (wx - pw) // 2
        oy = (wy - ph) // 2

        panel = pygame.Surface((pw, ph), pygame.SRCALPHA)
        panel.fill((20, 20, 20, 225))
        pygame.draw.rect(panel, (200, 200, 200, 80), panel.get_rect(), 1)

        # texto actual
        display = self.text + ("|" if self._cursor_visible else " ")
        txt_surf = self._font_text.render(display, True, (255, 255, 255))
        text_bg = pygame.Rect(_PAD - 4, _PAD - 4, pw - 2 * (_PAD - 4), _TEXT_H)
        pygame.draw.rect(panel, (40, 40, 40), text_bg, border_radius=4)
        panel.blit(txt_surf, (_PAD, _PAD + (_TEXT_H - txt_surf.get_height()) // 2))

        # teclas
        y0 = _PAD + _TEXT_H + _GAP
        for r, row in enumerate(_LAYOUT):
            y = y0 + r * (_KEY_H + _GAP)
            if r < len(_LAYOUT) - 1:
                # fila normal — centrada
                total_w = len(row) * _KEY_W + (len(row) - 1) * _GAP
                x_start = (pw - total_w) // 2
                for c, key in enumerate(row):
                    x = x_start + c * (_KEY_W + _GAP)
                    focused = (r == self._row and c == self._col)
                    self._draw_key(panel, key, x, y, _KEY_W, _KEY_H, focused)
            else:
                # fila de acción — teclas anchas distribuidas
                action_keys = row
                n = len(action_keys)
                total_w = pw - 2 * _PAD
                key_w = (total_w - (n - 1) * _GAP) // n
                for c, key in enumerate(action_keys):
                    x = _PAD + c * (key_w + _GAP)
                    focused = (r == self._row and c == self._col)
                    self._draw_key(panel, key, x, y, key_w, _KEY_H, focused)

        window.blit(panel, (ox, oy))

    def _draw_key(self, surface, text, x, y, w, h, focused):
        color = (255, 220, 50) if focused else (60, 60, 60)
        txt_color = (0, 0, 0) if focused else (220, 220, 220)
        pygame.draw.rect(surface, color, (x, y, w, h), border_radius=4)
        surf = self._font_key.render(text, True, txt_color)
        surface.blit(surf, (x + (w - surf.get_width()) // 2,
                             y + (h - surf.get_height()) // 2))
