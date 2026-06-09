# src/lib/xhs_client.py
import json
import subprocess
import datetime as dt
from typing import Callable
from src.lib.schema import Note

_VIDEO_TYPES = {"video", "视频"}


class XhsError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


def parse_envelope(raw: str) -> dict:
    """解析 cli 的 ok/data/error 信封,error 抛 XhsError。"""
    obj = json.loads(raw)
    if not obj.get("ok", False):
        err = obj.get("error", {}) or {}
        raise XhsError(err.get("code", "unknown"), err.get("message", ""))
    return obj.get("data", {})


def _parse_date(value: str) -> dt.date:
    return dt.date.fromisoformat(value[:10])


def cli_note_to_model(cli: dict, fetched_at: dt.datetime,
                      folder: str | None = None,
                      top_comments: list[str] | None = None) -> Note:
    """把 cli 返回的笔记 dict 适配为 Note。字段名按 cli 实际输出调整。"""
    is_video = cli.get("type") in _VIDEO_TYPES or bool(cli.get("video"))
    return Note(
        id=cli["note_id"],
        type="视频" if is_video else "图文",
        title=cli.get("title", ""),
        author=(cli.get("user") or {}).get("nickname", ""),
        url=cli.get("url", ""),
        collected_at=_parse_date(cli.get("collected_time", fetched_at.date().isoformat())),
        folder=folder,
        body_text=cli.get("desc", ""),
        image_urls=cli.get("images", []) or [],
        video_url=cli.get("video"),
        top_comments=top_comments or [],
        fetched_at=fetched_at,
    )


def _default_runner(args: list[str]) -> str:
    return subprocess.run(args, capture_output=True, text=True, check=True).stdout


class XhsClient:
    """xiaohongshu-cli 薄封装。runner 可注入以便测试。"""

    def __init__(self, runner: Callable[[list[str]], str] = _default_runner):
        self._run = runner

    def status_raw(self) -> dict:
        return parse_envelope(self._run(["xhs", "status", "--json"]))

    def favorites_raw(self) -> dict:
        return parse_envelope(self._run(["xhs", "favorites", "--json"]))

    def read_raw(self, note_id: str) -> dict:
        return parse_envelope(self._run(["xhs", "read", note_id, "--json"]))
