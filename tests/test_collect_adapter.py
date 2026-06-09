# tests/test_collect_adapter.py
import datetime as dt

from src.lib.collect_adapter import collect_item_to_note

SAMPLE = {
    "type": "video",
    "cover": {"url_default": "http://img/d.webp", "url_pre": "http://img/p.webp"},
    "user": {"nickname": "远南岛", "user_id": "u1"},
    "interact_info": {"liked": True, "liked_count": "3952"},
    "xsec_token": "TK",
    "note_id": "abc",
    "display_title": "硅谷程序员应聘现状",
}


def test_maps_core_fields():
    n = collect_item_to_note(SAMPLE, rank=0, fetched_at=dt.datetime(2026, 6, 9))
    assert n.id == "abc"
    assert n.type == "视频"
    assert n.title == "硅谷程序员应聘现状"
    assert n.author == "远南岛"
    assert n.liked_count == 3952
    assert n.collect_rank == 0
    assert n.cover_url == "http://img/d.webp"
    assert "abc" in n.url and "TK" in n.url


def test_image_note_and_missing_liked():
    item = {**SAMPLE, "type": "normal", "interact_info": {"liked_count": None}}
    n = collect_item_to_note(item, rank=5, fetched_at=dt.datetime(2026, 6, 9))
    assert n.type == "图文"
    assert n.liked_count is None
    assert n.collect_rank == 5
