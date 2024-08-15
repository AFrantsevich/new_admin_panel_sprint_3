from datetime import datetime
import redis
import abc
from typing import Any, Dict


class BaseStorage(abc.ABC):
    """Абстрактное хранилище состояния.

    Позволяет сохранять и получать состояние.
    Способ хранения состояния может варьироваться в зависимости
    от итоговой реализации. Например, можно хранить информацию
    в базе данных или в распределённом файловом хранилище.
    """

    @abc.abstractmethod
    def save_state(self, state: Dict[str, Any]) -> None:
        """Сохранить состояние в хранилище."""

    @abc.abstractmethod
    def retrieve_state(self, key: str) -> Dict[str, Any]:
        """Получить состояние из хранилища."""


class RedisStorage(BaseStorage):
    """Реализация хранилища, использующего Redis."""

    def __init__(self, redis: redis.Redis) -> None:
        self._redis = redis

    def save_state(self, state: Dict[str, Any]) -> None:
        """Сохранить состояние в хранилище."""
        self._redis.mset(state)

    def retrieve_state(self, key: str) -> Dict[str, Any]:
        """Получить состояние из хранилища."""
        return self._redis.get(key)  # pyright: ignore[]


class State:
    """Класс для работы с состояниями."""

    def __init__(self, storage: BaseStorage) -> None:
        self.storage = storage

    @staticmethod
    def time_hook(value: datetime):
        return value.isoformat()

    def set_state(self, key: str, value: Any) -> None:
        """Установить состояние для определённого ключа."""
        if isinstance(value, datetime):
            value = self.time_hook(value)
        self.storage.save_state({key: value})

    def get_state(self, key: str) -> Any:
        """Получить состояние по определённому ключу."""
        return self.storage.retrieve_state(key)
