"""Base storage package."""

from infrastructure.storage.base.repository import StrategyBasedRepository
from infrastructure.storage.base.strategy import (
    BaseStorageStrategy,
    StorageStrategy,
)
from infrastructure.storage.base.unit_of_work import (
    BaseUnitOfWork,
    StrategyUnitOfWork,
)

__all__: list[str] = [
    "BaseStorageStrategy",
    "BaseUnitOfWork",
    "StorageStrategy",
    "StrategyBasedRepository",
    "StrategyUnitOfWork",
]
