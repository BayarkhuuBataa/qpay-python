from contextlib import contextmanager
from datetime import datetime, timedelta
from unittest.mock import MagicMock
from urllib.parse import urljoin

import pytest

from qpay import InMemoryTokenStore, QPayAuth, QPayException, TokenStore

HOST = "https://merchant.qpay.mn/v2/"
AUTH_HOST = urljoin(HOST, "auth/")
ACCESS_TOKEN = "DUMMY_ACCESS_TOKEN"
NEW_ACCESS_TOKEN = "NEW_DUMMY_ACCESS_TOKEN"
REFRESH_TOKEN = "DUMMY_REFRESH_TOKEN"


def test_token(requests_mock, monkeypatch):
    def token_callback(request, _):
        assert request.headers["authorization"] == "Basic dXNlcm5hbWU6cGFzc3dvcmQ="
        return {
            "token_type": "bearer",
            "refresh_expires_in": 50,
            "refresh_token": REFRESH_TOKEN,
            "access_token": ACCESS_TOKEN,
            "expires_in": 10,
        }

    def refresh_callback(request, _):
        assert request.headers["authorization"] == f"Bearer {REFRESH_TOKEN}"
        return {
            "token_type": "bearer",
            "refresh_expires_in": 50,
            "refresh_token": "NEW_DUMMY_REFRESH_TOKEN",
            "access_token": NEW_ACCESS_TOKEN,
            "expires_in": 10,
        }

    token_url = urljoin(AUTH_HOST, "token")
    refresh_url = urljoin(AUTH_HOST, "refresh")
    requests_mock.post(token_url, json=token_callback)
    requests_mock.post(
        refresh_url,
        [
            {"json": {"message": "Error"}, "status_code": 401},
            {"json": refresh_callback, "status_code": 200},
        ],
    )

    auth = QPayAuth(HOST, "username", "password")
    request = MagicMock(headers={})

    # Нэвтрэх нэр, нууц үгийг ашиглан токен авна
    with monkeypatch.context() as m:
        frozen_time = datetime(2014, 4, 20, 10, 30, 00)
        m.setattr("qpay.auth.QPayAuth._timestamp", lambda _: frozen_time)
        token = auth._get_token()
        assert token.token == ACCESS_TOKEN
        assert token.expires == frozen_time + timedelta(seconds=10)
        assert auth(request).headers["Authorization"] == f"Bearer {ACCESS_TOKEN}"

    # Токен сэргээн авах хүсэлт 401 буцаавал, нэвтрэх нэр нууц үгээр дахин токен авна
    with monkeypatch.context() as m:
        frozen_time = datetime(2014, 4, 20, 10, 30, 40)
        m.setattr("qpay.auth.QPayAuth._timestamp", lambda _: frozen_time)
        token = auth._get_token()
        assert token.token == ACCESS_TOKEN
        assert token.expires == frozen_time + timedelta(seconds=10)
        assert auth(request).headers["Authorization"] == f"Bearer {ACCESS_TOKEN}"

    # Сэргээх токен ашиглан хандалтын токен дахиж авна
    with monkeypatch.context() as m:
        frozen_time = datetime(2014, 4, 20, 10, 31, 00)
        m.setattr("qpay.auth.QPayAuth._timestamp", lambda _: frozen_time)
        token = auth._get_token()
        assert token.token == NEW_ACCESS_TOKEN
        assert token.expires == frozen_time + timedelta(seconds=10)
        assert auth(request).headers["Authorization"] == f"Bearer {NEW_ACCESS_TOKEN}"

    # Сэргээх токены хугацаа дууссан бол нэвтрэх нэр, нууц үгээр шинийг авна
    with monkeypatch.context() as m:
        frozen_time = datetime(2014, 4, 20, 11, 00, 00)
        m.setattr("qpay.auth.QPayAuth._timestamp", lambda _: frozen_time)
        token = auth._get_token()
        assert token.token == ACCESS_TOKEN
        assert token.expires == frozen_time + timedelta(seconds=10)
        assert auth(request).headers["Authorization"] == f"Bearer {ACCESS_TOKEN}"

    assert [i.url for i in requests_mock.request_history] == [
        token_url,
        refresh_url,
        token_url,
        refresh_url,
        token_url,
    ]


def test_timestamp():
    auth = QPayAuth(HOST, "username", "password")
    assert isinstance(auth._timestamp(), datetime)

    now = datetime.now()
    mocked_now = MagicMock(**{"return_value": now})
    auth = QPayAuth(HOST, "username", "password", mocked_now)
    assert auth._timestamp() == now


def test_token_request_raises_exception(requests_mock):
    with pytest.raises(QPayException) as exc:
        json = {"message": "error"}
        auth = QPayAuth(HOST, "username", "password")
        requests_mock.post(urljoin(AUTH_HOST, "token"), json=json, status_code=500)
        auth._get_token()

    assert exc.value.response.json() == json


def _token_response():
    return {
        "token_type": "bearer",
        "refresh_expires_in": 36000,
        "refresh_token": REFRESH_TOKEN,
        "access_token": ACCESS_TOKEN,
        "expires_in": 36000,
    }


def test_token_store_shared_across_instances(requests_mock):
    requests_mock.post(urljoin(AUTH_HOST, "token"), json=_token_response())

    store = InMemoryTokenStore()
    auth1 = QPayAuth(HOST, "username", "password", token_store=store)
    auth2 = QPayAuth(HOST, "username", "password", token_store=store)

    token1 = auth1._get_token()
    token2 = auth2._get_token()

    assert token1.token == token2.token == ACCESS_TOKEN
    assert len(requests_mock.request_history) == 1


class DummyTokenStore(TokenStore):
    def __init__(self):
        self._access_token = None
        self._refresh_token = None

    def get(self):
        return self._access_token, self._refresh_token

    def set(self, access_token, refresh_token):
        self._access_token = access_token
        self._refresh_token = refresh_token

    @contextmanager
    def lock(self):
        yield


def test_custom_token_store_contract(requests_mock):
    requests_mock.post(urljoin(AUTH_HOST, "token"), json=_token_response())

    store = DummyTokenStore()
    auth = QPayAuth(HOST, "username", "password", token_store=store)
    token = auth._get_token()

    assert token.token == ACCESS_TOKEN
    assert store.get()[0].token == ACCESS_TOKEN


def test_fetch_token_uses_timeout(requests_mock, monkeypatch):
    requests_mock.post(urljoin(AUTH_HOST, "token"), json=_token_response())

    auth = QPayAuth(HOST, "username", "password", timeout=5)
    calls = []
    original_post = auth._session.post
    monkeypatch.setattr(
        auth._session,
        "post",
        lambda *a, **kw: (calls.append(kw), original_post(*a, **kw))[1],
    )

    auth._get_token()

    assert calls[0]["timeout"] == 5


def test_auth_configures_retry_adapter():
    auth = QPayAuth(HOST, "username", "password", max_retries=5)
    assert auth._session.adapters["https://"].max_retries.total == 5
