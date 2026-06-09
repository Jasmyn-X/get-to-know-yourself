# src/fetch.py
import datetime as dt
import json
from pathlib import Path
from src.lib.timewindow import within_last_years
from src.lib.xhs_client import XhsClient, cli_note_to_model
from src.lib.ratelimit import RateLimiter
from src.lib.store import ProgressStore

STAGE = "fetch"


def select_new_in_window(raw_notes: list[dict], done_ids: set[str],
                         years: int, today: dt.date) -> list[dict]:
    """保留近 N 年且未处理过的笔记。"""
    out = []
    for n in raw_notes:
        if n["note_id"] in done_ids:
            continue
        collected = dt.date.fromisoformat(n.get("collected_time", "")[:10])
        if within_last_years(collected, years=years, today=today):
            out.append(n)
    return out


def run(client: XhsClient, store: ProgressStore, limiter: RateLimiter,
        years: int, out_path: Path, today: dt.date | None = None) -> int:
    """抓取近2年新收藏,逐条取详情,写 raw_notes.json。返回新增条数。"""
    today = today or dt.date.today()
    listing = client.favorites_raw().get("notes", [])
    todo = select_new_in_window(listing, store.done_ids(STAGE), years, today)

    out_path = Path(out_path)
    existing = []
    if out_path.exists():
        existing = json.loads(out_path.read_text(encoding="utf-8"))

    now = dt.datetime.now()
    for raw in todo:
        try:
            detail = client.read_raw(raw["note_id"])  # 详情(正文/图片/视频)
            merged = {**raw, **detail}
            note = cli_note_to_model(merged, fetched_at=now,
                                     folder=raw.get("folder"))
            existing.append(note.model_dump(mode="json"))
            store.mark_done(note.id, STAGE, "ok")
        except Exception as e:  # 单条失败 fail soft,记录后继续
            store.mark_done(raw["note_id"], STAGE, f"failed:{e}")
        limiter.wait()

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(existing, ensure_ascii=False, indent=2),
                        encoding="utf-8")
    return len(todo)
