from frameworks.inputs import InputHandler
from use_cases.input_translator import PlayerIntention


class InputAdapter:
    """Traduce el estado de InputHandler a un PlayerIntention inmutable."""

    def __init__(self, handler: InputHandler) -> None:
        self._handler = handler

    def read(self) -> PlayerIntention:
        h = self._handler
        return PlayerIntention(
            move_left=h.con_left,
            move_right=h.con_right,
            move_up=h.con_up,
            move_down=h.con_down,
            shoot=h.shot,
            mouse_pos=h.mouse_pos,
            right_stick_x=h.right_stick[0],
            right_stick_y=h.right_stick[1],
            use_stick=h._joystick is not None,
            deadzone=h.deadzone,
        )
