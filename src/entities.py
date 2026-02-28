from dataclasses import dataclass
import math

from enums import ROLE, STATE
from inputs import InputHandler


@dataclass
class Geometry:
    x : int
    y : int
    radius : int

    def __setitem__(self, key, value):
        self.__setattr__(key, value)

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

    def wish_to_move(self, inputs : InputHandler) -> tuple[int, int, str]:
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

    def wish_to_shoot(self, inputs : InputHandler, offset_x : int = 0, offset_y : int = 0) -> tuple[float, float]:
        dx, dy = 0, 0
        if inputs.shot:
            dx, dy = self.__shoot_direction(inputs, offset_x, offset_y)
        
        return dx, dy

    def __shoot_direction(self, inputs : InputHandler, offset_x : float = 0, offset_y : float = 0) -> tuple[float, float]:
        dx, dy = 0, 0

        if inputs._joystick is not None:
            rx, ry = inputs.right_stick
            length = math.hypot(rx, ry)
            if length > inputs.deadzone:
                dx = float(rx / length)
                dy = float(ry / length)
        else:
            player_sx = self.pos.x - offset_x
            player_sy = self.pos.y - offset_y
            mx, my = inputs.mouse_pos
            dx, dy = mx - player_sx, my - player_sy
            length = math.hypot(dx, dy)

            dx = float(dx / length)
            dy = float(dy / length)
        
        return dx, dy
    
    def update(self, data : dict):
        for key, value in data.items():
            if key == 'state':
                self.state = STATE(value)
            elif key == 'role':
                self.role = ROLE(value)
            elif key in ['x', 'y', 'radius']:
                self.pos[key] = value
            elif key == 'live':
                self.live = Live(int(value))
    
    def dump(self) -> dict:
        return {
            'x' : self.pos.x, 
            'y' : self.pos.y, 
            'radius' : self.pos.radius,
            'state' : self.state.value,
            'role' : self.role.value,
            'live' : self.live.hp
        }
    

@dataclass
class Bullet:
    pos : Geometry
    dx : float
    dy : float
    owner : ROLE

    def dump(self) -> dict:
        return {
            'x' : self.pos.x, 
            'y' : self.pos.y, 
            'dx' : self.dx, 
            'dy' : self.dy, 
            'role' : self.owner.value,
        }