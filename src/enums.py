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
    
class MESSAGES(Enum):
    HELLO = 'hello'
    PLAYER_CLASS = 'player_class'
    WISH_MOVE = 'wish_mode'
    MOVE = 'move'
    PLAYERS_UPDATE = 'players_update'