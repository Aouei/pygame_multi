import math
from dataclasses import dataclass

from domain.enums import STATE


@dataclass
class PlayerIntention:
    move_left: bool
    move_right: bool
    move_up: bool
    move_down: bool
    shoot: bool
    mouse_pos: tuple[int, int]
    right_stick_x: float
    right_stick_y: float
    use_stick: bool
    deadzone: float


def translate_move(intention: PlayerIntention, speed: int) -> tuple[int, int, str]:
    """Pure function: intención de movimiento → (dx, dy, state_value)."""
    dx, dy = 0, 0
    state = STATE.IDLE

    if intention.move_left:
        dx = -speed
        state = STATE.LEFT
    if intention.move_right:
        dx = speed
        state = STATE.RIGHT
    if intention.move_up:
        dy = -speed
        state = STATE.UP
    if intention.move_down:
        dy = speed
        state = STATE.DOWN

    return dx, dy, state.value


def translate_shoot(
    intention: PlayerIntention,
    player_x: int,
    player_y: int,
    offset_x: float = 0,
    offset_y: float = 0,
) -> tuple[float, float]:
    """Pure function: intención + posición → vector de disparo (dx, dy) normalizado."""
    if not intention.shoot:
        return 0.0, 0.0

    if intention.use_stick:
        rx, ry = intention.right_stick_x, intention.right_stick_y
        length = math.hypot(rx, ry)
        if length > intention.deadzone:
            return float(rx / length), float(ry / length)
        return 0.0, 0.0

    player_sx = player_x - offset_x
    player_sy = player_y - offset_y
    mx, my = intention.mouse_pos
    dx, dy = mx - player_sx, my - player_sy
    length = math.hypot(dx, dy)
    if length == 0:
        return 0.0, 0.0

    return float(dx / length), float(dy / length)
