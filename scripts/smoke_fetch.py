# scripts/smoke_fetch.py
"""手动小批量真实抓取冒烟(默认看本页收藏)。先 `xhs login` 登录。
用途: 校正 xhs_client 适配字段、确认登录态与限速可用。"""
import datetime as dt
from pathlib import Path
from src.lib.config import load_config
from src.lib.xhs_client import XhsClient
from src.lib.ratelimit import RateLimiter
from src.lib.store import ProgressStore
from src.auth import ensure_authenticated
from src import fetch

if __name__ == "__main__":
    cfg = load_config()
    client = XhsClient()
    user = ensure_authenticated(client)
    print(f"已登录: {user.get('nickname')}")

    # 仅看前若干条原始输出,人工核对字段名
    listing = client.favorites_raw().get("notes", [])
    print(f"收藏总数(本页): {len(listing)}")
    if listing:
        print("首条原始字段:", listing[0])

    store = ProgressStore(Path(cfg.paths.data_dir) / "state.sqlite")
    limiter = RateLimiter(cfg.fetch.min_interval_s, cfg.fetch.max_interval_s)
    n = fetch.run(client, store, limiter, years=cfg.time_window_years,
                  out_path=Path(cfg.paths.data_dir) / "raw_notes_smoke.json")
    print(f"新增抓取: {n} 条 → data/raw_notes_smoke.json")
