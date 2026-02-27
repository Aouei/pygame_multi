from dataclasses import dataclass


@dataclass
class Entity:
    x : int
    y : int
    hp : int
    radius : int