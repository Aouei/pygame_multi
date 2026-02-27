from enum import Enum


class ROLE(Enum):
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
    ROLE = 'role'
    WISH_MOVE = 'wish_mode'
    MOVE = 'move'
    PLAYERS_UPDATE = 'players_update'