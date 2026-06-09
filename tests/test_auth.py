# tests/test_auth.py
import pytest
from src.auth import ensure_authenticated, NotAuthenticated


class FakeClient:
    def __init__(self, data):
        self._data = data

    def status_raw(self):
        return self._data


def test_authenticated_passes():
    client = FakeClient({"authenticated": True, "user": {"nickname": "u"}})
    assert ensure_authenticated(client)["nickname"] == "u"


def test_not_authenticated_raises():
    client = FakeClient({"authenticated": False})
    with pytest.raises(NotAuthenticated):
        ensure_authenticated(client)
