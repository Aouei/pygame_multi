from enum import Enum, auto


class PLAYER_CLASS(Enum):
    ARCHER = 'archer'
    FARMER = 'farmer'
    MAGE = 'mage'
    MUSKETEER = 'musketeer'


class STATE(Enum):
    UP = 'up'
    DOWN = 'down'
    LEFT = 'left'
    RIGHT = 'right'
    