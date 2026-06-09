"""方案2 第二步:浏览器内抓取收藏(绕开逆向 API 的签名问题)。
用 pw_login.py 保存的登录态打开收藏页,拦截网页自身发出的
`note/collect/page` 响应(由页面 JS 正确签名,必过),自动滚动加载全部,
落到 data/raw_collect.json。

运行(需先 pw_login):
    python -m src.fetch_browser
"""
import json
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

STATE = Path(".secrets/xhs_storage_state.json")
OUT = Path("data/raw_collect.json")
USER_ID = "REDACTED_USER_ID"  # owner;后续可由 whoami 动态获取

_COLLECT_MARKER = "note/collect/page"
_MAX_SCROLLS = 200
_STABLE_LIMIT = 6


def _extract_items(payload: dict) -> list[dict]:
    """从 collect/page 响应里取笔记列表。字段名做容错。"""
    data = payload.get("data") or {}
    for key in ("notes", "note_list", "items", "collect_notes"):
        if isinstance(data.get(key), list):
            return data[key]
    return []


def _note_id(item: dict) -> str | None:
    return item.get("note_id") or item.get("id") or (item.get("note_card") or {}).get("note_id")


def run(headless: bool = True, out_path: Path = OUT) -> int:
    if not STATE.exists():
        raise SystemExit("未找到登录态,请先运行: python scripts/pw_login.py")

    collected: list[dict] = []
    seen: set[str] = set()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        ctx = browser.new_context(storage_state=str(STATE))
        page = ctx.new_page()

        def on_response(resp):
            if _COLLECT_MARKER not in resp.url:
                return
            try:
                payload = resp.json()
            except Exception:
                return
            for it in _extract_items(payload):
                nid = _note_id(it)
                if nid and nid not in seen:
                    seen.add(nid)
                    collected.append(it)

        page.on("response", on_response)

        page.goto(f"https://www.xiaohongshu.com/user/profile/{USER_ID}",
                  wait_until="domcontentloaded")
        time.sleep(3)

        # 切到“收藏”tab(触发 collect/page 请求)
        for sel in ("收藏", "收藏 "):
            try:
                page.get_by_text(sel, exact=True).first.click(timeout=4000)
                break
            except Exception:
                continue
        time.sleep(3)

        # 自动滚动直到不再有新增
        last = -1
        stable = 0
        for _ in range(_MAX_SCROLLS):
            page.mouse.wheel(0, 4000)
            time.sleep(1.5)
            if len(collected) == last:
                stable += 1
                if stable >= _STABLE_LIMIT:
                    break
            else:
                stable = 0
                last = len(collected)

        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(collected, ensure_ascii=False, indent=2),
                            encoding="utf-8")
        print(f"共抓到 {len(collected)} 条收藏 -> {out_path}")
        if collected:
            print("首条原始结构(前 1500 字符,用于校正适配器):")
            print(json.dumps(collected[0], ensure_ascii=False, indent=2)[:1500])
        browser.close()
        return len(collected)


if __name__ == "__main__":
    run()
