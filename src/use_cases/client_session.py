from domain.entities import Player, Bullet, Ship, Enemy, Castle
from domain.enums import ROLE


class ClientSession:
    """
    Estado local del cliente: recibe snapshots del servidor y mantiene
    la proyección de entidades para su posterior renderizado.
    Sin imports de pygame, asyncio ni websockets.
    """

    def __init__(self) -> None:
        self.received_players: dict[int, Player] = {}
        self.received_bullets: list[Bullet] = []
        self.received_ships: list[Ship] = []
        self.received_enemies: list[Enemy] = []
        self.received_castles: dict[int, Castle] = {}
        self._current_player: Player = Player(ROLE.MAGE, 0, 0)
        self._ID: int = -1
        self._in_battle: bool = False

    def reset(self):
        self.received_players.clear()
        self.received_bullets.clear()
        self.received_ships.clear()
        self.received_enemies.clear()
        self.received_castles.clear()
        self._ID = -1
        self._in_battle = False

    @property
    def player(self) -> Player:
        return self._current_player

    @property
    def ID(self) -> int:
        return self._ID

    @ID.setter
    def ID(self, value: int) -> None:
        self._ID = value

    @property
    def in_battle(self) -> bool:
        return bool(self.received_ships or self.received_enemies)

    def apply_snapshot(self, snap) -> None:
        self.received_players.clear()
        for idd, dto in snap.players.items():
            p = Player(ROLE.MAGE, 0, 0)
            p.update(vars(dto))
            self.received_players[idd] = p
        if self._ID in snap.players:
            self.player.update(vars(snap.players[self._ID]))

        self.received_bullets.clear()
        for dto in snap.bullets:
            b = Bullet(0, 0, 0, 0, ROLE.MAGE)
            b.update(vars(dto))
            self.received_bullets.append(b)

        self.received_ships.clear()
        for dto in snap.ships:
            s = Ship(0, 0, [])
            s.update(vars(dto))
            self.received_ships.append(s)

        self.received_enemies.clear()
        for dto in snap.enemies:
            e = Enemy(0, 0, [], 0)
            e.update(vars(dto))
            self.received_enemies.append(e)

        server_ids = set(snap.castles.keys())
        for cid in list(self.received_castles.keys()):
            if cid not in server_ids:
                del self.received_castles[cid]
        for cid, dto in snap.castles.items():
            if cid not in self.received_castles:
                self.received_castles[cid] = Castle(dto.x, dto.y)
            self.received_castles[cid].update(vars(dto))
