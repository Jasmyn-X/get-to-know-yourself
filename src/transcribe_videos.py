"""后段第二步:重点方向视频的本地 faster-whisper 逐字稿(0 token)。
只转 AI/技术折腾 + 求职/搞钱 这几类的视频。下载视频→转写→存 txt。
复用 src.transcribe.transcribe_notes 的 fail-soft 循环。SQLite 续传。
运行: python -m src.transcribe_videos
"""
import json
import os
import tempfile
import urllib.request
from pathlib import Path

from faster_whisper import WhisperModel

from src.lib.store import ProgressStore
from src.transcribe import transcribe_notes

RAW = Path("data/raw_collect.json")
CLUSTERS = Path("data/clusters.json")
DETAILS = Path("data/details")
OUT = Path("data/transcripts")
DB = "data/state.sqlite"
STAGE = "transcribe"

# 重点方向对应的簇 id(见 scripts/build_analysis.py 的命名)
TARGET_CLUSTERS = {4, 5, 8, 13, 14, 16, 17}


def target_videos() -> list[dict]:
    raw = json.loads(RAW.read_text(encoding="utf-8"))
    labels = json.loads(CLUSTERS.read_text(encoding="utf-8"))["labels"]
    out = []
    for i, n in enumerate(raw):
        if labels[i] not in TARGET_CLUSTERS:
            continue
        df = DETAILS / f"{n['note_id']}.json"
        if not df.exists():
            continue
        vurl = json.loads(df.read_text(encoding="utf-8")).get("video_url")
        if vurl:
            out.append({"id": n["note_id"], "type": "视频", "video_url": vurl})
    return out


def _make_transcriber(model: WhisperModel):
    def _transcribe(video_url: str) -> str:
        tmp = os.path.join(tempfile.gettempdir(), "xhs_tx.mp4")
        req = urllib.request.Request(video_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=120) as r:
            Path(tmp).write_bytes(r.read())
        try:
            segments, _ = model.transcribe(tmp, language="zh")
            return "".join(s.text for s in segments).strip()
        finally:
            if os.path.exists(tmp):
                os.remove(tmp)
    return _transcribe


def run(limit: int | None = None) -> int:
    store = ProgressStore(DB)
    done = store.done_ids(STAGE)
    pending = [n for n in target_videos() if n["id"] not in done]
    if limit:
        pending = pending[:limit]
    print(f"待转写: {len(pending)} 个(已完成 {len(done)})")
    if not pending:
        return 0

    model = WhisperModel("small", device="cpu", compute_type="int8")
    transcriber = _make_transcriber(model)
    ok = transcribe_notes(
        pending, OUT, transcriber,
        mark_done=lambda nid, status: store.mark_done(nid, STAGE, status),
    )
    print(f"transcribe done this run: ok={ok}/{len(pending)}")
    return ok


if __name__ == "__main__":
    run()
