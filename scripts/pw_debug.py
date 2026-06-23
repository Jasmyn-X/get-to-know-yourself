"""诊断:看收藏页到底发了哪些 API、有哪些 tab、是否被风控。
运行: python scripts/pw_debug.py   (默认无头;传 --headed 用有头)
产物: data/debug_screenshot.png, data/debug_api_urls.txt
"""
import os
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

STATE = Path(".secrets/xhs_storage_state.json")
# 你的小红书 user_id。设环境变量 XHS_USER_ID,勿硬编码。
USER_ID = os.environ.get("XHS_USER_ID", "")


def main(headed: bool) -> int:
    if not USER_ID:
        raise SystemExit("请先设置环境变量 XHS_USER_ID(你的小红书 user_id)")
    api_urls: list[str] = []
    collect_hits: list[str] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=not headed)
        ctx = browser.new_context(storage_state=str(STATE))
        page = ctx.new_page()

        def on_response(resp):
            u = resp.url
            if "xiaohongshu.com/api" in u or "edith" in u:
                api_urls.append(f"{resp.status} {u}")
            if "collect" in u:
                collect_hits.append(f"{resp.status} {u}")

        page.on("response", on_response)

        page.goto(f"https://www.xiaohongshu.com/user/profile/{USER_ID}",
                  wait_until="domcontentloaded")
        time.sleep(4)
        print("PAGE TITLE:", page.title())
        print("PAGE URL:", page.url)

        # dump 所有“收藏”叶子元素的 tag/class/outerHTML,定位真正的 tab
        cands = page.evaluate(
            """() => {
                const out=[];
                document.querySelectorAll('*').forEach(e=>{
                    if(e.childElementCount===0 && (e.textContent||'').trim()==='收藏'){
                        out.push({tag:e.tagName, cls:String(e.className), html:(e.outerHTML||'').slice(0,160)});
                    }
                });
                return out;
            }"""
        )
        print(f"收藏 leaf candidates: {len(cands)}")
        for i, c in enumerate(cands):
            print(f"  [{i}] <{c['tag']} class={c['cls']!r}> {c['html']}")

        # 逐个候选尝试点击,看哪个能触发 note/collect/page
        clicked = False
        loc = page.get_by_text("收藏", exact=True)
        n = loc.count()
        print(f"locator count for exact '收藏': {n}")
        for i in range(n):
            try:
                with page.expect_response(lambda r: "note/collect/page" in r.url, timeout=6000):
                    loc.nth(i).click(timeout=3000)
                clicked = True
                print(f">>> note/collect/page FIRED by clicking exact-收藏 nth({i})")
                break
            except Exception as e:
                print(f"  nth({i}) no collect/page: {str(e)[:90]}")
        time.sleep(4)

        for _ in range(5):
            page.mouse.wheel(0, 4000)
            time.sleep(1.5)

        Path("data").mkdir(parents=True, exist_ok=True)
        page.screenshot(path="data/debug_screenshot.png", full_page=True)
        Path("data/debug_api_urls.txt").write_text(
            "CLICKED: %s\n\nCOLLECT HITS:\n%s\n\nALL API:\n%s" % (
                clicked, "\n".join(collect_hits), "\n".join(api_urls)),
            encoding="utf-8")
        print(f"collect hits: {len(collect_hits)} | total api calls: {len(api_urls)}")
        print("first 15 api urls:")
        for u in api_urls[:15]:
            print("  ", u)
        browser.close()
    return 0


if __name__ == "__main__":
    main(headed="--headed" in sys.argv)
