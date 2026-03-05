from dataclasses import dataclass, field
import math

from enums import ROLE, STATE
from inputs import InputHandler


@dataclass
class Counter:
    """Contador de tiempo basado en ticks del servidor."""

    seconds: float
    rate: int = 20  # ticks/segundo — debe coincidir con el tick rate del servidor
    _count: int = field(default=0, init=False, repr=False)

    def tick(self) -> bool:
        """Incrementa un tick. Devuelve True (y se autoreset) al llegar al tiempo máximo."""
        self._count += 1
        if self._count >= self.seconds * self.rate:
            self._count = 0
            return True
        return False

    def reset(self):
        self._count = 0


@dataclass
class Geometry:
    x: int
    y: int
    radius: int

    def __setitem__(self, key, value):
        self.__setattr__(key, value)


@dataclass
class Player:
    role: ROLE
    x: int
    y: int
    live: int = 20
    max_live: int = 20
    radius: int = 25
    speed: int = 5
    state: STATE = STATE.DOWN

    def wish_to_move(self, inputs: InputHandler) -> tuple[int, int, str]:
        dx, dy = 0, 0

        if inputs.con_left:
            dx = -self.speed
            self.state = STATE.LEFT
        if inputs.con_right:
            dx = self.speed
            self.state = STATE.RIGHT
        if inputs.con_up:
            dy = -self.speed
            self.state = STATE.UP
        if inputs.con_down:
            dy = self.speed
            self.state = STATE.DOWN

        if dx == 0 and dy == 0:
            self.state = STATE.IDLE

        return dx, dy, self.state.value

    def wish_to_shoot(
        self, inputs: InputHandler, offset_x: int = 0, offset_y: int = 0
    ) -> tuple[float, float]:
        dx, dy = 0, 0
        if inputs.shot:
            dx, dy = self.__shoot_direction(inputs, offset_x, offset_y)

        return dx, dy

    def __shoot_direction(
        self, inputs: InputHandler, offset_x: float = 0, offset_y: float = 0
    ) -> tuple[float, float]:
        dx, dy = 0, 0

        if inputs._joystick is not None:
            rx, ry = inputs.right_stick
            length = math.hypot(rx, ry)
            if length > inputs.deadzone:
                dx = float(rx / length)
                dy = float(ry / length)
        else:
            player_sx = self.x - offset_x
            player_sy = self.y - offset_y
            mx, my = inputs.mouse_pos
            dx, dy = mx - player_sx, my - player_sy
            length = math.hypot(dx, dy)

            dx = float(dx / length)
            dy = float(dy / length)

        return dx, dy

    def update(self, data: dict):
        for key, value in data.items():
            if key == "state":
                self.state = STATE(value)
            elif key == "role":
                self.role = ROLE(value)
            else:
                self.__setattr__(key, value)

    def dump(self) -> dict:
        return {
            "x": self.x,
            "y": self.y,
            "live": self.live,
            "state": self.state.value,
            "role": self.role.value,
        }


@dataclass
class Bullet:
    x: int
    y: int
    dx: float
    dy: float
    owner: ROLE
    radius: int = 16

    def update(self, data: dict):
        for key, value in data.items():
            if key == "role":
                self.role = ROLE(value)
            else:
                self.__setattr__(key, value)

    def dump(self) -> dict:
        return {
            "x": self.x,
            "y": self.y,
            "dx": self.dx,
            "dy": self.dy,
            "role": self.owner.value,
        }


@dataclass
class Ship:
    x: int
    y: int
    path: list[STATE]
    live: int = 20
    max_live: int = 20
    radius: int = 32
    speed: int = 15
    state: STATE = STATE.DOWN
    target_x: int = 0
    target_y: int = 0

    def update(self, data: dict):
        for key, value in data.items():
            if key == "state":
                self.state = STATE(value)
            else:
                self.__setattr__(key, value)

    def dump(self) -> dict:
        return {"x": self.x, "y": self.y, "state": self.state.value, "live": self.live}


@dataclass
class Enemy:
    x: int
    y: int
    path: list[STATE]
    variant: int
    live: int = 5
    max_live: int = 5
    radius: int = 25
    speed: int = 15
    state: STATE = STATE.LEFT
    target_x: int = 0
    target_y: int = 0

    def update(self, data: dict):
        for key, value in data.items():
            if key == "state":
                if not value in [STATE.DOWN.value, STATE.UP.value]:
                    self.state = STATE(value)
            else:
                self.__setattr__(key, value)

    def dump(self) -> dict:
        return {
            "x": self.x,
            "y": self.y,
            "state": self.state.value,
            "live": self.live,
            "variant": self.variant,
        }
