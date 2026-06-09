# src/to_obsidian.py
"""把 Note 渲染成 Obsidian 笔记(YAML frontmatter + 正文)并落盘。
分类阶段之前先平铺到 vault/notes/;分类后可按 categories 分文件夹。
"""
import re
from pathlib import Path

from src.lib.schema import Note

_ILLEGAL = re.compile(r'[\\/:*?"<>|\n\r\t]+')


def safe_filename(title: str, note_id: str, maxlen: int = 60) -> str:
    base = _ILLEGAL.sub("_", (title or "").strip()) or "untitled"
    base = base[:maxlen].rstrip()
    return f"{base}__{note_id}.md"


def render(note: Note) -> str:
    safe_title = (note.title or "").replace('"', "'")
    fm = ["---", f'title: "{safe_title}"', f'author: "{note.author}"',
          f"xhs_url: {note.url}", f"type: {note.type}"]
    if note.liked_count is not None:
        fm.append(f"liked_count: {note.liked_count}")
    if note.collect_rank is not None:
        fm.append(f"collect_rank: {note.collect_rank}")
    if note.categories:
        fm.append("categories: [" + ", ".join(note.categories) + "]")
    if note.tags:
        fm.append("tags: [" + ", ".join(note.tags) + "]")
    fm.append("---")

    body = [f"# {note.title}", ""]
    if note.cover_url:
        body.append(f"![cover]({note.cover_url})")
        body.append("")
    if note.body_text:
        body.append(note.body_text)
        body.append("")
    body.append(f"[在小红书打开]({note.url})")
    return "\n".join(fm) + "\n\n" + "\n".join(body) + "\n"


def build_vault(notes, out_dir) -> int:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    count = 0
    for note in notes:
        fn = safe_filename(note.title, note.id)
        (out / fn).write_text(render(note), encoding="utf-8")
        count += 1
    return count
