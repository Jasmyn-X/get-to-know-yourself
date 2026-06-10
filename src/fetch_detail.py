"""后段第一步:逐条抓笔记正文详情(从页面 __INITIAL_STATE__ 取,绕开签名 API)。
提取 desc/标签/发布时间/IP/图片/视频流URL,存 data/details/{note_id}.json。
SQLite 续传、fail-soft、限速。运行: python -m src.fetch_detail
"""
import json
import random
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

from src.lib.store import ProgressStore

STATE = ".secrets/xhs_storage_state.json"
RAW = Path("data/raw_collect.json")
OUT = Path("data/details")
DB = "data/state.sqlite"
STAGE = "detail"

_JS = r"""
() => {
  const s = window.__INITIAL_STATE__;
  if(!s || !s.note) return null;
  const m = s.note.noteDetailMap || {};
  for (const key of Object.keys(m)){ const nd=m[key];
    if(nd && nd.note && nd.note.noteId){ const n=nd.note;
      let vurl = null;
      try {
        const st = n.video.media.stream;
        for (const codec of ['h264','h265','av1']){
          if(st[codec] && st[codec].length){
            vurl = st[codec][0].masterUrl || (st[codec][0].backupUrls||[])[0]; break; }
        }
      } catch(e){}
      const ii = n.interactInfo || {};
      return {
        note_id: n.noteId, title: n.title || '', desc: n.desc || '',
        time: n.time || null, last_update_time: n.lastUpdateTime || null,
        type: n.type || '', tags: (n.tagList||[]).map(t=>t.name),
        ip_location: n.ipLocation || '',
        image_urls: (n.imageList||[]).map(im => im.urlDefault || im.url || ''),
        video_url: vurl,
        liked_count: ii.likedCount, comment_count: ii.commentCount,
        collected_count: ii.collectedCount
      };
    }
  }
  return null;
}
"""


def run(limit: int | None = None, headless: bool = True,
        min_s: float = 2.5, max_s: float = 6.0) -> dict:
    raw = json.loads(RAW.read_text(encoding="utf-8"))
    OUT.mkdir(parents=True, exist_ok=True)
    store = ProgressStore(DB)
    done = store.done_ids(STAGE)
    todo = [n for n in raw if n["note_id"] not in done]
    if limit:
        todo = todo[:limit]

    ok = fail = 0
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        ctx = browser.new_context(storage_state=STATE)
        page = ctx.new_page()
        for note in todo:
            nid, tok = note["note_id"], note.get("xsec_token", "")
            url = (f"https://www.xiaohongshu.com/explore/{nid}"
                   f"?xsec_token={tok}&xsec_source=pc_user")
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=30000)
                time.sleep(2.0)
                detail = page.evaluate(_JS)
                if detail and detail.get("note_id"):
                    (OUT / f"{nid}.json").write_text(
                        json.dumps(detail, ensure_ascii=False, indent=2), encoding="utf-8")
                    store.mark_done(nid, STAGE, "ok")
                    ok += 1
                else:
                    store.mark_done(nid, STAGE, "failed:no_state")
                    fail += 1
            except Exception as e:
                store.mark_done(nid, STAGE, f"failed:{type(e).__name__}")
                fail += 1
            time.sleep(min_s + random.random() * (max_s - min_s))
        browser.close()
    result = {"ok": ok, "fail": fail, "remaining": len(raw) - len(store.done_ids(STAGE))}
    print(f"detail fetch: ok={ok} fail={fail} remaining={result['remaining']}")
    return result


if __name__ == "__main__":
    run()
