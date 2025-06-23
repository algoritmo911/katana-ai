from abc import ABC, abstractmethod

from typing import Optional

class InterfaceBase(ABC):
    @abstractmethod
    async def receive(self, payload: Optional[dict] = None) -> dict:
        """Получить запрос от пользователя, вернуть контекст."""
    @abstractmethod
    async def send(self, response: dict) -> None:
        """Отправить ответ пользователю."""
