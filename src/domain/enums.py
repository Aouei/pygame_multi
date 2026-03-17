from enum import Enum


class ROLE(Enum):
    ARCHER = "archer"
    FARMER = "farmer"
    MAGE = "mage"
    MUSKETEER = "musketeer"


class STATE(Enum):
    UP = "up"
    DOWN = "down"
    LEFT = "left"
    RIGHT = "right"
    IDLE = "idle"


class COLLISIONS(Enum):
    PLAYER = "player"
    BULLET = "bullet"
    SHIP = "ship"
    ENEMY = "enemy"
