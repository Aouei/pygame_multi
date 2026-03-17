class Camera:
    def __init__(
        self,
        x: int,
        y: int,
        map_pixel_w: int,
        map_pixel_h: int,
        screen_w: int,
        screen_h: int,
    ) -> None:
        self.x = x
        self.y = y
        self.map_w = map_pixel_w
        self.map_h = map_pixel_h
        self.screen_w = screen_w
        self.screen_h = screen_h

    def move(self, dx: int, dy: int) -> None:
        self.x = max(0, min(self.x + dx, self.map_w - self.screen_w))
        self.y = max(0, min(self.y + dy, self.map_h - self.screen_h))

    @property
    def offset(self) -> tuple[int, int]:
        return self.x, self.y
