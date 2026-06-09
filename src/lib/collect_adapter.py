# src/lib/collect_adapter.py
"""把浏览器拦截到的 note/collect/page 列表项适配为 Note。
列表是轻量版:有标题/封面/作者/点赞,无正文/收藏时间(那些需逐条拉详情)。
"""
import datetime as dt

from src.lib.schema import Note


def _liked(item: dict) -> int | None:
    raw = (item.get("interact_info") or {}).get("liked_count")
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def _cover(item: dict) -> str | None:
    cover = item.get("cover") or {}
    return cover.get("url_default") or cover.get("url_pre") or None


def collect_item_to_note(item: dict, rank: int, fetched_at: dt.datetime) -> Note:
    note_id = item["note_id"]
    xsec = item.get("xsec_token", "")
    url = (f"https://www.xiaohongshu.com/explore/{note_id}"
           f"?xsec_token={xsec}&xsec_source=pc_user")
    cover = _cover(item)
    return Note(
        id=note_id,
        type="视频" if item.get("type") == "video" else "图文",
        title=item.get("display_title", ""),
        author=(item.get("user") or {}).get("nickname", ""),
        url=url,
        collect_rank=rank,
        cover_url=cover,
        liked_count=_liked(item),
        image_urls=[cover] if cover else [],
        fetched_at=fetched_at,
    )
