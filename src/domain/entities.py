from dataclasses import dataclass, field

from domain.enums import ROLE, STATE


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
    radius: int = 20
    speed: int = 5
    state: STATE = STATE.DOWN
    invulnerable: int = 0

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
    damage: int = 2
    radius: int = 16

    def update(self, data: dict):
        for key, value in data.items():
            if key == "role":
                self.owner = ROLE(value)
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
    speed: int = 5
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
    damage: int = 4
    state: STATE = STATE.LEFT
    target_x: int = 0
    target_y: int = 0

    def update(self, data: dict):
        for key, value in data.items():
            if key == "state":
                if value not in [STATE.DOWN.value, STATE.UP.value]:
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


@dataclass
class Castle:
    x: int
    y: int
    live: int = 50
    max_live: int = 50
    radius: int = 64
    invulnerable: int = 0

    def dump(self) -> dict:
        return {"x": self.x, "y": self.y, "live": self.live}

    def update(self, data: dict):
        for key, value in data.items():
            self.__setattr__(key, value)
