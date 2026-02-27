from dataclasses import dataclass

from enums import ROLE, STATE


@dataclass
class Geometry:
    x : int
    y : int
    radius : int

@dataclass
class Live:
    hp : int

@dataclass
class Player():
    role : ROLE
    pos : Geometry
    live : Live
    radius : int = 32
    speed : int = 5
    state : STATE = STATE.DOWN

    def dump(self) -> dict:
        summary =  {
            'x' : self.pos.x, 
            'y' : self.pos.y, 
            'state' : self.state.value,
            'role' : self.role.value,
        }
        return summary