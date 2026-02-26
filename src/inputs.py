import pygame, sys


class InputHandler:
    def __init__(self) -> None:
        pygame.joystick.init()

        if pygame.joystick.get_count() > 0:
            self.joystick = pygame.joystick.Joystick(0)
            self.joystick.init()
        else:
            self.joystick = None

        self.deadzone = 0.1
        self._reset()
        self._prev_hat = (0, 0)

    def _reset(self):
        self.quit = False
        self.k_left = False
        self.k_right = False
        self.k_enter = False
        self.con_left = False
        self.con_right = False
        self.con_up = False
        self.con_down = False

    def update(self):
        self._reset()
        self.handle_keyboard()
        self.handle_joystick()

    def handle_joystick(self):
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

            ax = self.joystick.get_axis(0)
            ay = self.joystick.get_axis(1)
            if abs(ax) > self.deadzone:
                if ax < 0:
                    self.con_left = True
                else:
                    self.con_right = True
            if abs(ay) > self.deadzone:
                if ay < 0:
                    self.con_up = True
                else:
                    self.con_down = True

    def handle_keyboard(self):
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
        if keys[pygame.K_UP]:
            self.con_up = True
        if keys[pygame.K_DOWN]:
            self.con_down = True