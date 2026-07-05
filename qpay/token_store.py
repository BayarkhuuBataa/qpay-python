import threading
from abc import ABC, abstractmethod
from contextlib import AbstractContextManager, contextmanager
from datetime import datetime
from typing import Iterator, Optional

from pydantic import BaseModel


class AccessToken(BaseModel):
    token: str
    expires: datetime


class RefreshToken(BaseModel):
    token: str
    expires: datetime


class TokenStore(ABC):
    @abstractmethod
    def get(self) -> tuple[Optional[AccessToken], Optional[RefreshToken]]: ...

    @abstractmethod
    def set(self, access_token: AccessToken, refresh_token: RefreshToken) -> None: ...

    @abstractmethod
    def lock(self) -> AbstractContextManager[None]: ...


class InMemoryTokenStore(TokenStore):
    def __init__(self):
        self._access_token: Optional[AccessToken] = None
        self._refresh_token: Optional[RefreshToken] = None
        self._lock = threading.Lock()

    def get(self) -> tuple[Optional[AccessToken], Optional[RefreshToken]]:
        return self._access_token, self._refresh_token

    def set(self, access_token: AccessToken, refresh_token: RefreshToken) -> None:
        self._access_token = access_token
        self._refresh_token = refresh_token

    @contextmanager
    def lock(self) -> Iterator[None]:
        with self._lock:
            yield
