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


class MESSAGES(Enum):
    HELLO = "hello"
    ROLE = "role"
    WISH_MOVE = "wish_mode"
    PLAYERS_UPDATE = "players_update"
    SHOT = "shot"
    QUIT = "quit"
    ROUND_START = "round_start"
    SHUT_DOWN = "shut_down"


class COLLISIONS(Enum):
    PLAYER = "player"
    BULLET = "bullet"
    SHIP = "ship"
    ENEMY = "enemy"
