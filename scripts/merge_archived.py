# scripts/merge_archived.py
"""累积式更新:把"本次采集到的收藏"与"vault 里已有但本次没采到的旧笔记"合并。

每次重采收藏,失效/被删的笔记会从列表消失。为了知识库"只增不删",本脚本:
  - 以 data/raw_collect.json(本次采集)为基准
  - 找出 vault/Clippings 里存在、但本次没采到的 note_id(= 已从收藏移除)
  - 用 vault frontmatter(+ details 封面)重建这些笔记的最小 raw 项,标 _archived=True
  - 把它们追加进 data/raw_collect.json(并集)

之后照常 fetch_detail / recluster / build_kepano_vault 即可。
运行: PYTHONPATH=. python scripts/merge_archived.py
"""
import glob
import json
import re
from pathlib import Path

RAW = Path("data/raw_collect.json")
CLIPPINGS = "vault/Clippings/**/*.md"
DETAILS = Path("data/details")

_ID_RE = re.compile(r"__([0-9a-zA-Z]{12,})\.md$")


def _fm(text: str, key: str):
    m = re.search(rf'^{key}:\s*"?(.*?)"?\s*$', text, re.MULTILINE)
    return m.group(1).strip() if m else ""


def _cover(note_id: str):
    df = DETAILS / f"{note_id}.json"
    if df.exists():
        try:
            imgs = json.loads(df.read_text(encoding="utf-8")).get("image_urls") or []
            if imgs:
                return imgs[0]
        except Exception:
            pass
    return None


def reconstruct(path: Path, note_id: str) -> dict:
    txt = path.read_text(encoding="utf-8")
    typ = _fm(txt, "type")
    liked = _fm(txt, "liked_count")
    cover = _cover(note_id)
    return {
        "note_id": note_id,
        "type": "video" if typ == "视频" else "normal",
        "display_title": _fm(txt, "title") or path.stem.split("__")[0],
        "user": {"nickname": _fm(txt, "author")},
        "interact_info": {"liked_count": liked or "0"},
        "cover": {"url_default": cover} if cover else {},
        "xsec_token": "",          # 失效笔记无 token,URL 不可用属预期
        "_archived": True,         # 标记:已从收藏移除/可能失效
    }


def main():
    raw = json.loads(RAW.read_text(encoding="utf-8"))
    current_ids = {x["note_id"] for x in raw}

    vault_files = {}
    for p in glob.glob(CLIPPINGS, recursive=True):
        m = _ID_RE.search(Path(p).name)
        if m:
            vault_files[m.group(1)] = Path(p)

    archived_ids = [i for i in vault_files if i not in current_ids]
    added = [reconstruct(vault_files[i], i) for i in archived_ids]

    merged = raw + added
    RAW.write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"本次采集: {len(raw)} | vault 旧笔记补回(标 archived): {len(added)} "
          f"| 合并后: {len(merged)}")
    with_cover = sum(1 for a in added if a["cover"])
    print(f"  其中 {with_cover} 条能补回封面(有 details)")


if __name__ == "__main__":
    main()
