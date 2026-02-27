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
        return {
            'x' : self.pos.x, 
            'y' : self.pos.y, 
            'state' : self.state.value,
            'role' : self.role.value,
        }

    def wish_to_move(self, inputs) -> tuple[int, int, str]:
        dx, dy = 0, 0

        if inputs.con_left:
            dx = -self.speed
            self.state = STATE.LEFT
        if inputs.con_right:
            dx =  self.speed
            self.state = STATE.RIGHT
        if inputs.con_up:
            dy = -self.speed
            self.state = STATE.UP
        if inputs.con_down:
            dy =  self.speed
            self.state = STATE.DOWN

        return dx, dy, self.state.value