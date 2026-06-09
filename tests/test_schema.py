# tests/test_schema.py
import datetime as dt
import pytest
from pydantic import ValidationError
from src.lib.schema import Note


def make_kwargs(**over):
    base = dict(
        id="abc123",
        type="图文",
        title="露营装备清单",
        author="user1",
        url="https://www.xiaohongshu.com/explore/abc123",
        collected_at=dt.date(2025, 8, 12),
        folder="户外",
        body_text="正文",
        image_urls=["https://img/1.jpg"],
        video_url=None,
        top_comments=["好用"],
        fetched_at=dt.datetime(2026, 6, 9, 10, 0, 0),
    )
    base.update(over)
    return base


def test_valid_note_round_trips():
    note = Note(**make_kwargs())
    assert note.id == "abc123"
    assert note.type == "图文"
    assert note.categories == []   # 分类前默认空
    assert note.cluster_id is None


def test_invalid_type_rejected():
    with pytest.raises(ValidationError):
        Note(**make_kwargs(type="音频"))


def test_collected_at_serializes_as_iso_date():
    note = Note(**make_kwargs())
    assert note.model_dump(mode="json")["collected_at"] == "2025-08-12"
