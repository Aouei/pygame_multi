from typing import Protocol

from use_cases.input_translator import PlayerIntention


class IInputSource(Protocol):
    def read(self) -> PlayerIntention: ...


class IAssetProvider(Protocol):
    players: dict
    bullets: dict
    ships: dict
    enemies: list
    castle: object


class IServerProcess(Protocol):
    running: bool
