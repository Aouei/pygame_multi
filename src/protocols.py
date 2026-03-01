from typing import Protocol, runtime_checkable


@runtime_checkable
class LivingEntity(Protocol):
    live : int
    max_live : int