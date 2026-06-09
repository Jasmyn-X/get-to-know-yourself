# src/transcribe.py
from pathlib import Path
from typing import Callable

STAGE = "transcribe"


def select_pending_videos(notes: list[dict], done_ids: set[str]) -> list[dict]:
    return [n for n in notes
            if n.get("type") == "视频" and n.get("video_url")
            and n["id"] not in done_ids]


def transcribe_notes(notes: list[dict], out_dir,
                     transcriber: Callable[[str], str],
                     mark_done: Callable[[str, str], None]) -> int:
    """对每条视频笔记转写为 txt。失败 fail soft。返回成功数。"""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    ok = 0
    for n in notes:
        try:
            text = transcriber(n["video_url"])
            (out_dir / f"{n['id']}.txt").write_text(text, encoding="utf-8")
            mark_done(n["id"], "ok")
            ok += 1
        except Exception as e:
            mark_done(n["id"], f"failed:{e}")
    return ok


def faster_whisper_transcriber(model_size: str = "small", language: str = "zh"):
    """返回一个 transcriber(video_url)->text。下载音频 → faster-whisper。
    真实实现:此处用 faster_whisper.WhisperModel;音频下载复用 hc-tec 思路。
    """
    from faster_whisper import WhisperModel  # 延迟导入,避免测试期加载
    model = WhisperModel(model_size)

    def _transcribe(video_url: str) -> str:
        audio_path = _download_audio(video_url)  # 见 Task 9 smoke 中实现/对接
        segments, _ = model.transcribe(str(audio_path), language=language)
        return "".join(seg.text for seg in segments).strip()

    return _transcribe


def _download_audio(video_url: str):
    """对接 hc-tec media-audio-download 或 yt-dlp 下载音频轨,返回本地路径。
    smoke 阶段确定具体命令后实现。"""
    raise NotImplementedError("在 Task 9 smoke 阶段对接音频下载")
