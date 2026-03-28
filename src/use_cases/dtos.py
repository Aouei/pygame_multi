from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class PlayerDTO:
    x: int
    y: int
    live: int
    state: str
    role: str


@dataclass
class BulletDTO:
    x: int
    y: int
    dx: float
    dy: float
    role: str


@dataclass
class ShipDTO:
    x: int
    y: int
    state: str
    live: int


@dataclass
class EnemyDTO:
    x: int
    y: int
    state: str
    live: int
    variant: int


@dataclass
class CastleDTO:
    x: int
    y: int
    live: int


@dataclass
class GameSnapshot:
    clients: int
    players: dict[int, PlayerDTO] = field(default_factory=dict)
    bullets: list[BulletDTO] = field(default_factory=list)
    ships: list[ShipDTO] = field(default_factory=list)
    enemies: list[EnemyDTO] = field(default_factory=list)
    castles: dict[int, CastleDTO] = field(default_factory=dict)

    @classmethod
    def from_wire(cls, data: dict) -> GameSnapshot:
        return cls(
            clients=data.get("clients", 0),
            players={int(k): PlayerDTO(**v) for k, v in data.get("players", {}).items()},
            bullets=[BulletDTO(**b) for b in data.get("bullets", [])],
            ships=[ShipDTO(**s) for s in data.get("ships", [])],
            enemies=[EnemyDTO(**e) for e in data.get("enemies", [])],
            castles={int(k): CastleDTO(**v) for k, v in data.get("castles", {}).items()},
        )

    def to_wire(self) -> dict:
        return {
            "clients": self.clients,
            "players": {k: vars(v) for k, v in self.players.items()},
            "bullets": [vars(b) for b in self.bullets],
            "ships": [vars(s) for s in self.ships],
            "enemies": [vars(e) for e in self.enemies],
            "castles": {k: vars(v) for k, v in self.castles.items()},
        }
