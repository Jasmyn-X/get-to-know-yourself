# tests/test_xhs_client.py
import datetime as dt
import pytest
from src.lib.xhs_client import parse_envelope, cli_note_to_model, XhsClient, XhsError


def test_parse_envelope_ok():
    raw = '{"ok": true, "schema_version": "1", "data": {"notes": []}}'
    assert parse_envelope(raw) == {"notes": []}


def test_parse_envelope_error_raises():
    raw = '{"ok": false, "error": {"code": "not_authenticated", "message": "need login"}}'
    with pytest.raises(XhsError) as e:
        parse_envelope(raw)
    assert e.value.code == "not_authenticated"


def test_cli_note_to_model_maps_fields():
    cli = {
        "note_id": "abc123",
        "type": "normal",
        "title": "露营",
        "user": {"nickname": "user1"},
        "url": "https://www.xiaohongshu.com/explore/abc123",
        "collected_time": "2025-08-12",
        "desc": "正文",
        "images": ["https://img/1.jpg"],
        "video": None,
    }
    note = cli_note_to_model(cli, fetched_at=dt.datetime(2026, 6, 9))
    assert note.id == "abc123"
    assert note.type == "图文"
    assert note.author == "user1"
    assert note.video_url is None


def test_cli_note_to_model_detects_video():
    cli = {
        "note_id": "v1", "type": "video", "title": "t", "user": {"nickname": "u"},
        "url": "https://x/v1", "collected_time": "2025-01-01",
        "desc": "", "images": [], "video": "https://v/1.mp4",
    }
    note = cli_note_to_model(cli, fetched_at=dt.datetime(2026, 6, 9))
    assert note.type == "视频"
    assert note.video_url == "https://v/1.mp4"


def test_favorites_uses_injected_runner():
    calls = []

    def fake_runner(args):
        calls.append(args)
        return '{"ok": true, "data": {"notes": [{"note_id": "a"}]}}'

    client = XhsClient(runner=fake_runner)
    data = client.favorites_raw()
    assert data == {"notes": [{"note_id": "a"}]}
    assert calls == [["xhs", "favorites", "--json"]]
