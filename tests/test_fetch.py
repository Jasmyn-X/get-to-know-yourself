# tests/test_fetch.py
import datetime as dt
from src.fetch import select_new_in_window

TODAY = dt.date(2026, 6, 9)


def _raw(note_id, collected):
    return {"note_id": note_id, "type": "normal", "title": "t",
            "user": {"nickname": "u"}, "url": "https://x/" + note_id,
            "collected_time": collected, "desc": "", "images": [], "video": None}


def test_filters_out_old_notes():
    raw = [_raw("a", "2025-08-12"), _raw("b", "2020-01-01")]
    kept = select_new_in_window(raw, done_ids=set(), years=2, today=TODAY)
    assert [n["note_id"] for n in kept] == ["a"]


def test_skips_already_done_ids():
    raw = [_raw("a", "2025-08-12"), _raw("b", "2025-09-01")]
    kept = select_new_in_window(raw, done_ids={"a"}, years=2, today=TODAY)
    assert [n["note_id"] for n in kept] == ["b"]
