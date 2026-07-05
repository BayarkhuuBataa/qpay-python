import logging
from datetime import datetime, timedelta
from typing import Callable, Optional
from urllib.parse import urljoin

import requests

from ._http import build_session
from .exceptions import QPayException
from .token_store import AccessToken, InMemoryTokenStore, RefreshToken, TokenStore

logger = logging.getLogger(__name__)


class QPayAuth(requests.auth.AuthBase):
    def __init__(
        self,
        host: str,
        username: str,
        password: str,
        now: Optional[Callable[[], datetime]] = None,
        token_store: Optional[TokenStore] = None,
        timeout: float = 10,
        max_retries: int = 3,
    ):
        self._token_store = token_store or InMemoryTokenStore()
        self._session = build_session(max_retries)
        self._host = urljoin(host, "auth/")
        self._username = username
        self._password = password
        self._now = now
        self._timeout = timeout

    def _timestamp(self):
        if self._now:
            return self._now()
        else:
            return datetime.now()

    def _fetch_token(
        self, refresh_token: Optional[RefreshToken] = None
    ) -> tuple[AccessToken, RefreshToken]:
        try:
            now = self._timestamp()
            r = (
                self._session.post(
                    urljoin(self._host, "refresh"),
                    headers={"Authorization": f"Bearer {refresh_token.token}"},
                    timeout=self._timeout,
                )
                if refresh_token and refresh_token.expires > now
                else self._session.post(
                    urljoin(self._host, "token"),
                    auth=(self._username, self._password),
                    timeout=self._timeout,
                )
            )
            r.raise_for_status()
            token = r.json()
            access_token = AccessToken(
                token=token["access_token"],
                expires=now + timedelta(seconds=token["expires_in"]),
            )
            refresh_token = RefreshToken(
                token=token["refresh_token"],
                expires=now + timedelta(seconds=token["refresh_expires_in"]),
            )
            return (access_token, refresh_token)
        except requests.HTTPError as exc:
            logger.exception(exc)
            if refresh_token and exc.response.status_code == 401:
                return self._fetch_token()
            raise QPayException(
                exc.response.json(), request=exc.request, response=exc.response
            ) from exc

    def _get_token(self) -> AccessToken:
        with self._token_store.lock():
            access_token, refresh_token = self._token_store.get()
            now = self._timestamp()

            if access_token and access_token.expires > now:
                return access_token

            access_token, refresh_token = self._fetch_token(refresh_token)
            self._token_store.set(access_token, refresh_token)
            return access_token

    def __call__(self, r):
        token = self._get_token()
        r.headers["Authorization"] = f"Bearer {token.token}"
        return r
