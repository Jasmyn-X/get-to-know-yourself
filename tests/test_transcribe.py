# tests/test_transcribe.py
from src.transcribe import select_pending_videos, transcribe_notes


def _note(nid, type_, video=None):
    return {"id": nid, "type": type_, "video_url": video}


def test_select_only_videos_not_done():
    notes = [_note("a", "图文"), _note("b", "视频", "u"), _note("c", "视频", "u")]
    pending = select_pending_videos(notes, done_ids={"c"})
    assert [n["id"] for n in pending] == ["b"]


def test_transcribe_notes_writes_txt_and_marks_done(tmp_path):
    notes = [_note("b", "视频", "http://v/b.mp4")]
    done = []
    out = transcribe_notes(
        notes,
        out_dir=tmp_path,
        transcriber=lambda url: "这是逐字稿",
        mark_done=lambda nid, status: done.append((nid, status)),
    )
    assert (tmp_path / "b.txt").read_text(encoding="utf-8") == "这是逐字稿"
    assert done == [("b", "ok")]
    assert out == 1


def test_transcribe_failure_is_soft(tmp_path):
    notes = [_note("b", "视频", "http://v/b.mp4")]
    done = []

    def boom(url):
        raise RuntimeError("download failed")

    out = transcribe_notes(notes, out_dir=tmp_path, transcriber=boom,
                           mark_done=lambda nid, status: done.append((nid, status)))
    assert out == 0
    assert done[0][0] == "b" and done[0][1].startswith("failed")
    assert not (tmp_path / "b.txt").exists()
