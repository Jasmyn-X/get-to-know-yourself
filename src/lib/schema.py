# src/lib/schema.py
import datetime as dt
from typing import Literal, Optional
from pydantic import BaseModel, Field

NoteType = Literal["图文", "视频"]


class Note(BaseModel):
    id: str
    type: NoteType
    title: str
    author: str
    url: str
    collected_at: dt.date
    folder: Optional[str] = None
    body_text: str = ""
    image_urls: list[str] = Field(default_factory=list)
    video_url: Optional[str] = None
    top_comments: list[str] = Field(default_factory=list)
    fetched_at: dt.datetime
    # 阶段4 分类后追加
    categories: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    cluster_id: Optional[int] = None
