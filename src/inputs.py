import pygame, sys


class InputHandler:
    def __init__(self, joystick=None) -> None:
        self.joystick = joystick
        self._reset()
        self._prev_hat = (0, 0)

    def _reset(self):
        self.quit = False
        self.k_left = False
        self.k_right = False
        self.k_enter = False
        self.con_left = False
        self.con_right = False

    def update(self):
        self._reset()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.quit = True
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_LEFT:
                    self.k_left = True
                elif event.key == pygame.K_RIGHT:
                    self.k_right = True
                elif event.key == pygame.K_RETURN:
                    self.k_enter = True
                elif event.key == pygame.K_ESCAPE:
                    self.quit = True

        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT]:
            self.con_left = True
        if keys[pygame.K_RIGHT]:
            self.con_right = True

        # Joystick support
        if self.joystick is not None: # meter con_left y con_right
            hat = self.joystick.get_hat(0) if self.joystick.get_numhats() > 0 else (0, 0)
            # Detectar solo transición de cruceta
            if hat[0] == -1 and self._prev_hat[0] != -1:
                self.k_left = True
            if hat[0] == 1 and self._prev_hat[0] != 1:
                self.k_right = True
            self._prev_hat = hat

            # Botón X (usualmente botón 0 en la mayoría de mandos)
            if self.joystick.get_numbuttons() > 0:
                if self.joystick.get_button(0):
                    self.k_enter = True

            # Start (botón 7), Select (botón 6)
            start = self.joystick.get_button(7) if self.joystick.get_numbuttons() > 7 else False
            select = self.joystick.get_button(6) if self.joystick.get_numbuttons() > 6 else False
            if start and select:
                self.quit = True