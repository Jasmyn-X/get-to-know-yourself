# tests/test_to_obsidian.py
import datetime as dt

from src.lib.schema import Note
from src.to_obsidian import build_vault, render, safe_filename


def _note(**ov):
    base = dict(id="abc", type="视频", title="硅谷/程序员:现状", author="远南岛",
                url="https://x/abc", fetched_at=dt.datetime(2026, 6, 9),
                cover_url="http://img/c.webp", liked_count=3952, collect_rank=0)
    base.update(ov)
    return Note(**base)


def test_safe_filename_strips_illegal_chars():
    fn = safe_filename("硅谷/程序员:现状", "abc")
    assert "/" not in fn and ":" not in fn
    assert fn.endswith("__abc.md")


def test_render_has_frontmatter_title_cover():
    md = render(_note())
    assert md.startswith("---")
    assert 'title: "硅谷/程序员:现状"' in md
    assert "type: 视频" in md
    assert "liked_count: 3952" in md
    assert "# 硅谷/程序员:现状" in md
    assert "http://img/c.webp" in md


def test_build_vault_writes_one_file_per_note(tmp_path):
    notes = [_note(id="a", title="第一条"), _note(id="b", title="第二条")]
    n = build_vault(notes, tmp_path)
    assert n == 2
    assert len(list(tmp_path.glob("*.md"))) == 2
