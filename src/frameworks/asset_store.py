import frameworks.paths as paths
from frameworks.factories import (
    MAP_SCALE, BULLET_SCALE, PLAYER_SCALE, CASTLE_SCALE, SHIP_SCALE,
    load_player, load_bullet, load_ship, load_enemy, load_castle,
)
from adapters.renderer import MapRender
from domain.enums import ROLE


class AssetStore:
    """
    Singleton que carga y almacena todos los sprites y el mapa de render.
    Se inicializa una sola vez tras pygame.display.set_mode().
    """

    _instance: "AssetStore | None" = None

    def __init__(self) -> None:
        self.players = {role: load_player(role, PLAYER_SCALE) for role in ROLE}
        self.bullets = load_bullet(BULLET_SCALE)
        self.ships = load_ship(SHIP_SCALE)
        self.enemies = load_enemy(PLAYER_SCALE)
        self.castle = load_castle(CASTLE_SCALE)
        self.map_render = MapRender(paths.MAP_PATH, scale=MAP_SCALE)

    @classmethod
    def get(cls) -> "AssetStore":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        cls._instance = None
