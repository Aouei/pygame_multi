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

    def update_players(self, players: dict) -> None:
        self.received_players.clear()
        for idd, player in players.items():
            self.received_players[idd] = Player(ROLE.MAGE, 0, 0)
            self.received_players[idd].update(player)
        self.player.update(players.get(self.ID, {}))

    def update_bullets(self, bullets: list) -> None:
        self.received_bullets.clear()
        for bullet in bullets:
            self.received_bullets.append(Bullet(0, 0, 0, 0, ROLE.MAGE))
            self.received_bullets[-1].update(bullet)

    def update_ships(self, ships: list) -> None:
        self.received_ships.clear()
        for ship in ships:
            self.received_ships.append(Ship(0, 0, []))
            self.received_ships[-1].update(ship)

    def update_enemies(self, enemies: list) -> None:
        self.received_enemies.clear()
        for enemy in enemies:
            self.received_enemies.append(Enemy(0, 0, [], 0))
            self.received_enemies[-1].update(enemy)

    def update_castles(self, castles: dict) -> None:
        server_ids = {int(k) for k in castles}
        for cid in list(self.received_castles.keys()):
            if cid not in server_ids:
                del self.received_castles[cid]
        for id_str, data in castles.items():
            cid = int(id_str)
            if cid not in self.received_castles:
                self.received_castles[cid] = Castle(data["x"], data["y"])
            self.received_castles[cid].update(data)
