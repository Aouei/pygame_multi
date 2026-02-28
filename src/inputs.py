import pygame


class InputHandler:
    def __init__(self) -> None:
        pygame.joystick.init()
        self.deadzone = 0.1
        self._reset()
        self._joystick = None
        self._try_init_joystick()
        self._prev_hat = 0
        self._prev_trigger = False

    def _try_init_joystick(self):
        if pygame.joystick.get_count() > 0:
            self._joystick = pygame.joystick.Joystick(0)
            self._joystick.init()

    def _reset(self):
        self.quit            = False
        self.k_left          = False   # pulso puntual (menús)
        self.k_right         = False   # pulso puntual (menús)
        self.k_enter         = False   # pulso puntual
        self.con_left        = False   # estado continuo (movimiento)
        self.con_right       = False
        self.con_up          = False
        self.con_down        = False
        self.shot            = False
        self.shot_direction  = (0, 0)
        self.right_stick  = (0.0, 0.0)

    def update(self):
        self._reset()

        # Consumir eventos de pygame (necesario siempre para que pygame no se congele)
        events = pygame.event.get()

        if self._joystick is not None:
            self._handle_joystick(events)
        else:
            self._handle_keyboard(events)

    def _handle_keyboard(self, events):
        for event in events:
            if event.type == pygame.QUIT:
                self.quit = True
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.quit = True
                elif event.key == pygame.K_RETURN:
                    self.k_enter = True
                elif event.key == pygame.K_LEFT:
                    self.k_left = True
                elif event.key == pygame.K_RIGHT:
                    self.k_right = True
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    self.shot = True
            elif event.type == pygame.JOYDEVICEADDED:
                self._try_init_joystick()

        self.mouse_pos = pygame.mouse.get_pos()

        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT]:  self.con_left  = True
        if keys[pygame.K_RIGHT]: self.con_right = True
        if keys[pygame.K_UP]:    self.con_up    = True
        if keys[pygame.K_DOWN]:  self.con_down  = True

    def _handle_joystick(self, events):
        for event in events:
            if event.type == pygame.QUIT:
                self.quit = True
            elif event.type == pygame.JOYBUTTONDOWN:
                if event.button == 0:
                    self.k_enter = True
                elif event.button == 6:
                    self.quit = True
            elif event.type == pygame.JOYDEVICEREMOVED:
                self._joystick = None
                return

        if self._joystick is None:
            return

        j = self._joystick

        # Ejes analógicos → movimiento continuo
        ax = j.get_axis(0) if j.get_numaxes() > 0 else 0.0
        ay = j.get_axis(1) if j.get_numaxes() > 1 else 0.0

        rx = j.get_axis(2) if j.get_numaxes() > 2 else 0.0
        ry = j.get_axis(3) if j.get_numaxes() > 3 else 0.0
        
        trigger = j.get_axis(5) > -0.5 if j.get_numaxes() > 5 else False
        self.shot = trigger and not self._prev_trigger
        self._prev_trigger = trigger

        self.right_stick = (rx, ry)

        if ax < -self.deadzone: self.con_left  = True
        if ax >  self.deadzone: self.con_right = True
        if ay < -self.deadzone: self.con_up    = True
        if ay >  self.deadzone: self.con_down  = True

        # Cruceta → estado continuo + pulso para menús
        if j.get_numhats() > 0:
            hx, hy = j.get_hat(0)
            if hx == -1 and self._prev_hat != -1:
                self.con_left  = True
                self.k_left    = True
            elif hx ==  1 and self._prev_hat != 1:
                self.con_right = True
                self.k_right   = True
            else:
                self._prev_hat = 0
            if hy ==  1: self.con_up   = True
            if hy == -1: self.con_down = True

            self._prev_hat = hx

