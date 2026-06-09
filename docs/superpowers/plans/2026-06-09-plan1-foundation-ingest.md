# Plan 1 — Foundation + Ingest 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 搭好项目骨架与底层库,用 xiaohongshu-cli 把近2年收藏抓成 `data/raw_notes.json`,并对视频笔记本地生成逐字稿。

**Architecture:** 分阶段 Python 脚本 + 中间 JSON/SQLite 衔接。底层库(schema/时间窗/限速/SQLite/cli 封装)纯逻辑、可单测;I/O 重的抓取与转写写成薄封装,网络部分靠手动 smoke 脚本验证(spec 第10节)。核心抓取 fail loud,enrich(转写)fail soft。

**Tech Stack:** Python 3.11, pytest, pydantic v2, xiaohongshu-cli(pip), faster-whisper, SQLite(stdlib), PyYAML。

**Spec:** `docs/superpowers/specs/2026-06-09-xhs-collection-knowledge-base-design.md`

---

## 文件结构

- `pyproject.toml` — 依赖与 pytest 配置
- `config.example.yaml` / `config.yaml` — 运行参数(config.yaml gitignore)
- `src/lib/config.py` — 读取 config.yaml → `Config` 对象
- `src/lib/schema.py` — `Note` pydantic 模型 + 校验
- `src/lib/timewindow.py` — 近2年过滤
- `src/lib/ratelimit.py` — 随机间隔限速器(可注入 rng/sleep)
- `src/lib/store.py` — SQLite 进度存储(已处理/状态)
- `src/lib/xhs_client.py` — xiaohongshu-cli subprocess 封装 + 信封解析 + cli dict→Note 适配
- `src/fetch.py` — 阶段1 编排(去重 + 窗口过滤 + 组装)
- `src/transcribe.py` — 阶段2 视频转写(faster-whisper,fail soft)
- `src/auth.py` — 阶段0 `xhs status` 校验
- `scripts/smoke_fetch.py` — 手动小批量(5条)真实抓取冒烟
- `tests/` — 单元测试

---

## Task 0: 项目骨架

**Files:**
- Create: `pyproject.toml`
- Create: `src/__init__.py`, `src/lib/__init__.py`, `tests/__init__.py`
- Create: `config.example.yaml`

- [ ] **Step 1: 创建 pyproject.toml**

```toml
[project]
name = "get-to-know-yourself"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "pydantic>=2.6",
    "pyyaml>=6.0",
    "xiaohongshu-cli",
    "faster-whisper>=1.0",
]

[project.optional-dependencies]
dev = ["pytest>=8.0"]

[tool.pytest.ini_options]
pythonpath = ["."]
testpaths = ["tests"]
```

- [ ] **Step 2: 创建空包文件**

创建 `src/__init__.py`、`src/lib/__init__.py`、`tests/__init__.py`(均为空文件)。

- [ ] **Step 3: 创建 config.example.yaml**

```yaml
# 抓取
time_window_years: 2          # 仅保留近 N 年收藏
fetch:
  min_interval_s: 3.0         # 请求间最小间隔
  max_interval_s: 8.0         # 请求间最大间隔
  max_notes: null             # null=全部;调试可设小值
# 转写
transcribe:
  enabled: true
  model_size: small           # faster-whisper 模型
  language: zh
# 路径
paths:
  data_dir: data
  vault_dir: vault
```

- [ ] **Step 4: 创建 config.yaml(从示例复制)**

```bash
cp config.example.yaml config.yaml
```

- [ ] **Step 5: 安装依赖并确认 pytest 可运行**

Run: `pip install -e ".[dev]" && pytest -q`
Expected: `no tests ran`(无错误,collection 成功)

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml src/__init__.py src/lib/__init__.py tests/__init__.py config.example.yaml
git commit -m "chore: project scaffold for foundation+ingest"
```

---

## Task 1: Note 数据模型

**Files:**
- Create: `src/lib/schema.py`
- Test: `tests/test_schema.py`

- [ ] **Step 1: 写失败测试**

```python
# tests/test_schema.py
import datetime as dt
import pytest
from pydantic import ValidationError
from src.lib.schema import Note


def make_kwargs(**over):
    base = dict(
        id="abc123",
        type="图文",
        title="露营装备清单",
        author="user1",
        url="https://www.xiaohongshu.com/explore/abc123",
        collected_at=dt.date(2025, 8, 12),
        folder="户外",
        body_text="正文",
        image_urls=["https://img/1.jpg"],
        video_url=None,
        top_comments=["好用"],
        fetched_at=dt.datetime(2026, 6, 9, 10, 0, 0),
    )
    base.update(over)
    return base


def test_valid_note_round_trips():
    note = Note(**make_kwargs())
    assert note.id == "abc123"
    assert note.type == "图文"
    assert note.categories == []   # 分类前默认空
    assert note.cluster_id is None


def test_invalid_type_rejected():
    with pytest.raises(ValidationError):
        Note(**make_kwargs(type="音频"))


def test_collected_at_serializes_as_iso_date():
    note = Note(**make_kwargs())
    assert note.model_dump(mode="json")["collected_at"] == "2025-08-12"
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/test_schema.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.lib.schema'`

- [ ] **Step 3: 实现 schema**

```python
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
```

- [ ] **Step 4: 运行测试确认通过**

Run: `pytest tests/test_schema.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add src/lib/schema.py tests/test_schema.py
git commit -m "feat: add Note schema with validation"
```

---

## Task 2: 近2年时间窗过滤

**Files:**
- Create: `src/lib/timewindow.py`
- Test: `tests/test_timewindow.py`

- [ ] **Step 1: 写失败测试**

```python
# tests/test_timewindow.py
import datetime as dt
from src.lib.timewindow import within_last_years

TODAY = dt.date(2026, 6, 9)


def test_recent_date_included():
    assert within_last_years(dt.date(2025, 8, 12), years=2, today=TODAY) is True


def test_exactly_on_boundary_included():
    assert within_last_years(dt.date(2024, 6, 9), years=2, today=TODAY) is True


def test_older_date_excluded():
    assert within_last_years(dt.date(2024, 6, 8), years=2, today=TODAY) is False
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/test_timewindow.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: 实现**

```python
# src/lib/timewindow.py
import datetime as dt


def within_last_years(d: dt.date, years: int, today: dt.date | None = None) -> bool:
    """d 是否落在 [today - years, today] 内(含边界)。"""
    today = today or dt.date.today()
    try:
        cutoff = today.replace(year=today.year - years)
    except ValueError:  # 2/29 等边界
        cutoff = today.replace(year=today.year - years, day=28)
    return d >= cutoff
```

- [ ] **Step 4: 运行测试确认通过**

Run: `pytest tests/test_timewindow.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add src/lib/timewindow.py tests/test_timewindow.py
git commit -m "feat: add near-2y time window filter"
```

---

## Task 3: 限速器

**Files:**
- Create: `src/lib/ratelimit.py`
- Test: `tests/test_ratelimit.py`

- [ ] **Step 1: 写失败测试**

```python
# tests/test_ratelimit.py
from src.lib.ratelimit import RateLimiter


def test_wait_sleeps_within_configured_range():
    slept = []
    # rng 返回 0.5 → uniform(3,8) 应得 3 + 0.5*(8-3) = 5.5
    rl = RateLimiter(min_s=3.0, max_s=8.0, rng=lambda: 0.5, sleep=slept.append)
    rl.wait()
    assert slept == [5.5]


def test_wait_respects_bounds_at_extremes():
    slept = []
    rl = RateLimiter(min_s=3.0, max_s=8.0, rng=lambda: 0.0, sleep=slept.append)
    rl.wait()
    assert slept == [3.0]
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/test_ratelimit.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: 实现**

```python
# src/lib/ratelimit.py
import random
import time
from typing import Callable


class RateLimiter:
    """请求间随机间隔限速。rng/sleep 可注入以便测试。"""

    def __init__(
        self,
        min_s: float,
        max_s: float,
        rng: Callable[[], float] = random.random,
        sleep: Callable[[float], None] = time.sleep,
    ):
        if min_s > max_s:
            raise ValueError("min_s 不能大于 max_s")
        self.min_s = min_s
        self.max_s = max_s
        self._rng = rng
        self._sleep = sleep

    def wait(self) -> None:
        delay = self.min_s + self._rng() * (self.max_s - self.min_s)
        self._sleep(delay)
```

- [ ] **Step 4: 运行测试确认通过**

Run: `pytest tests/test_ratelimit.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add src/lib/ratelimit.py tests/test_ratelimit.py
git commit -m "feat: add injectable rate limiter"
```

---

## Task 4: SQLite 进度存储

**Files:**
- Create: `src/lib/store.py`
- Test: `tests/test_store.py`

- [ ] **Step 1: 写失败测试**

```python
# tests/test_store.py
from src.lib.store import ProgressStore


def test_unseen_id_is_not_done(tmp_path):
    store = ProgressStore(tmp_path / "state.sqlite")
    assert store.is_done("abc", stage="fetch") is False


def test_mark_done_then_is_done(tmp_path):
    store = ProgressStore(tmp_path / "state.sqlite")
    store.mark_done("abc", stage="fetch", status="ok")
    assert store.is_done("abc", stage="fetch") is True
    # 不同阶段相互独立
    assert store.is_done("abc", stage="transcribe") is False


def test_done_ids_lists_only_matching_stage(tmp_path):
    store = ProgressStore(tmp_path / "state.sqlite")
    store.mark_done("a", stage="fetch", status="ok")
    store.mark_done("b", stage="fetch", status="failed")
    store.mark_done("c", stage="transcribe", status="ok")
    assert store.done_ids("fetch") == {"a", "b"}


def test_persists_across_instances(tmp_path):
    db = tmp_path / "state.sqlite"
    ProgressStore(db).mark_done("a", stage="fetch", status="ok")
    assert ProgressStore(db).is_done("a", stage="fetch") is True
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/test_store.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: 实现**

```python
# src/lib/store.py
import sqlite3
import datetime as dt
from pathlib import Path


class ProgressStore:
    """记录每条笔记在各阶段的处理状态,支持增量/续传。"""

    def __init__(self, db_path):
        self.path = Path(db_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.path))
        self._conn.execute(
            """CREATE TABLE IF NOT EXISTS progress (
                   id TEXT NOT NULL,
                   stage TEXT NOT NULL,
                   status TEXT NOT NULL,
                   updated_at TEXT NOT NULL,
                   PRIMARY KEY (id, stage)
               )"""
        )
        self._conn.commit()

    def mark_done(self, id: str, stage: str, status: str) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO progress (id, stage, status, updated_at) VALUES (?,?,?,?)",
            (id, stage, status, dt.datetime.now().isoformat()),
        )
        self._conn.commit()

    def is_done(self, id: str, stage: str) -> bool:
        cur = self._conn.execute(
            "SELECT 1 FROM progress WHERE id=? AND stage=?", (id, stage)
        )
        return cur.fetchone() is not None

    def done_ids(self, stage: str) -> set[str]:
        cur = self._conn.execute("SELECT id FROM progress WHERE stage=?", (stage,))
        return {row[0] for row in cur.fetchall()}
```

- [ ] **Step 4: 运行测试确认通过**

Run: `pytest tests/test_store.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add src/lib/store.py tests/test_store.py
git commit -m "feat: add SQLite progress store for incremental runs"
```

---

## Task 5: xiaohongshu-cli 封装与适配

**Files:**
- Create: `src/lib/xhs_client.py`
- Test: `tests/test_xhs_client.py`

说明: CLI 真实输出走 subprocess,这里把"跑命令"与"解析+适配"解耦。测试只覆盖纯解析/适配逻辑(注入假 runner),不碰网络。

- [ ] **Step 1: 写失败测试**

```python
# tests/test_xhs_client.py
import datetime as dt
import pytest
from src.lib.xhs_client import parse_envelope, cli_note_to_model, XhsClient, XhsError


def test_parse_envelope_ok():
    raw = '{"ok": true, "schema_version": "1", "data": {"notes": []}}'
    assert parse_envelope(raw) == {"notes": []}


def test_parse_envelope_error_raises():
    raw = '{"ok": false, "error": {"code": "not_authenticated", "message": "need login"}}'
    with pytest.raises(XhsError) as e:
        parse_envelope(raw)
    assert e.value.code == "not_authenticated"


def test_cli_note_to_model_maps_fields():
    cli = {
        "note_id": "abc123",
        "type": "normal",
        "title": "露营",
        "user": {"nickname": "user1"},
        "url": "https://www.xiaohongshu.com/explore/abc123",
        "collected_time": "2025-08-12",
        "desc": "正文",
        "images": ["https://img/1.jpg"],
        "video": None,
    }
    note = cli_note_to_model(cli, fetched_at=dt.datetime(2026, 6, 9))
    assert note.id == "abc123"
    assert note.type == "图文"
    assert note.author == "user1"
    assert note.video_url is None


def test_cli_note_to_model_detects_video():
    cli = {
        "note_id": "v1", "type": "video", "title": "t", "user": {"nickname": "u"},
        "url": "https://x/v1", "collected_time": "2025-01-01",
        "desc": "", "images": [], "video": "https://v/1.mp4",
    }
    note = cli_note_to_model(cli, fetched_at=dt.datetime(2026, 6, 9))
    assert note.type == "视频"
    assert note.video_url == "https://v/1.mp4"


def test_favorites_uses_injected_runner():
    calls = []

    def fake_runner(args):
        calls.append(args)
        return '{"ok": true, "data": {"notes": [{"note_id": "a"}]}}'

    client = XhsClient(runner=fake_runner)
    data = client.favorites_raw()
    assert data == {"notes": [{"note_id": "a"}]}
    assert calls == [["xhs", "favorites", "--json"]]
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/test_xhs_client.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: 实现**

```python
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
```

> 注意: cli 实际字段名(`note_id`/`collected_time`/`user.nickname` 等)需在执行 Task 9 smoke 后按真实输出校正;适配集中在 `cli_note_to_model` 一处,改动面小。

- [ ] **Step 4: 运行测试确认通过**

Run: `pytest tests/test_xhs_client.py -v`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
git add src/lib/xhs_client.py tests/test_xhs_client.py
git commit -m "feat: add xiaohongshu-cli wrapper with envelope parsing and Note adapter"
```

---

## Task 6: 阶段1 fetch 编排

**Files:**
- Create: `src/fetch.py`
- Test: `tests/test_fetch.py`

- [ ] **Step 1: 写失败测试**

```python
# tests/test_fetch.py
import datetime as dt
from src.fetch import select_new_in_window

TODAY = dt.date(2026, 6, 9)


def _raw(note_id, collected):
    return {"note_id": note_id, "type": "normal", "title": "t",
            "user": {"nickname": "u"}, "url": "https://x/" + note_id,
            "collected_time": collected, "desc": "", "images": [], "video": None}


def test_filters_out_old_notes():
    raw = [_raw("a", "2025-08-12"), _raw("b", "2020-01-01")]
    kept = select_new_in_window(raw, done_ids=set(), years=2, today=TODAY)
    assert [n["note_id"] for n in kept] == ["a"]


def test_skips_already_done_ids():
    raw = [_raw("a", "2025-08-12"), _raw("b", "2025-09-01")]
    kept = select_new_in_window(raw, done_ids={"a"}, years=2, today=TODAY)
    assert [n["note_id"] for n in kept] == ["b"]
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/test_fetch.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: 实现**

```python
# src/fetch.py
import datetime as dt
import json
from pathlib import Path
from src.lib.timewindow import within_last_years
from src.lib.xhs_client import XhsClient, cli_note_to_model
from src.lib.ratelimit import RateLimiter
from src.lib.store import ProgressStore

STAGE = "fetch"


def select_new_in_window(raw_notes: list[dict], done_ids: set[str],
                         years: int, today: dt.date) -> list[dict]:
    """保留近 N 年且未处理过的笔记。"""
    out = []
    for n in raw_notes:
        if n["note_id"] in done_ids:
            continue
        collected = dt.date.fromisoformat(n.get("collected_time", "")[:10])
        if within_last_years(collected, years=years, today=today):
            out.append(n)
    return out


def run(client: XhsClient, store: ProgressStore, limiter: RateLimiter,
        years: int, out_path: Path, today: dt.date | None = None) -> int:
    """抓取近2年新收藏,逐条取详情,写 raw_notes.json。返回新增条数。"""
    today = today or dt.date.today()
    listing = client.favorites_raw().get("notes", [])
    todo = select_new_in_window(listing, store.done_ids(STAGE), years, today)

    out_path = Path(out_path)
    existing = []
    if out_path.exists():
        existing = json.loads(out_path.read_text(encoding="utf-8"))

    now = dt.datetime.now()
    for raw in todo:
        try:
            detail = client.read_raw(raw["note_id"])  # 详情(正文/图片/视频)
            merged = {**raw, **detail}
            note = cli_note_to_model(merged, fetched_at=now,
                                     folder=raw.get("folder"))
            existing.append(note.model_dump(mode="json"))
            store.mark_done(note.id, STAGE, "ok")
        except Exception as e:  # 单条失败 fail soft,记录后继续
            store.mark_done(raw["note_id"], STAGE, f"failed:{e}")
        limiter.wait()

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(existing, ensure_ascii=False, indent=2),
                        encoding="utf-8")
    return len(todo)
```

- [ ] **Step 4: 运行测试确认通过**

Run: `pytest tests/test_fetch.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add src/fetch.py tests/test_fetch.py
git commit -m "feat: add stage1 fetch orchestration with window+dedup"
```

---

## Task 7: 阶段0 auth 校验

**Files:**
- Create: `src/auth.py`
- Test: `tests/test_auth.py`

- [ ] **Step 1: 写失败测试**

```python
# tests/test_auth.py
import pytest
from src.auth import ensure_authenticated, NotAuthenticated


class FakeClient:
    def __init__(self, data):
        self._data = data

    def status_raw(self):
        return self._data


def test_authenticated_passes():
    client = FakeClient({"authenticated": True, "user": {"nickname": "u"}})
    assert ensure_authenticated(client)["nickname"] == "u"


def test_not_authenticated_raises():
    client = FakeClient({"authenticated": False})
    with pytest.raises(NotAuthenticated):
        ensure_authenticated(client)
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/test_auth.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: 实现**

```python
# src/auth.py
class NotAuthenticated(Exception):
    pass


def ensure_authenticated(client) -> dict:
    """校验登录态;未登录则 fail loud 提示重登。返回 user dict。"""
    data = client.status_raw()
    if not data.get("authenticated"):
        raise NotAuthenticated("未登录,请运行 `xhs login`(或 `xhs login --qrcode`)后重试")
    return data.get("user", {})
```

- [ ] **Step 4: 运行测试确认通过**

Run: `pytest tests/test_auth.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add src/auth.py tests/test_auth.py
git commit -m "feat: add stage0 auth check (fail loud on not authenticated)"
```

---

## Task 8: 阶段2 transcribe(视频逐字稿,fail soft)

**Files:**
- Create: `src/transcribe.py`
- Test: `tests/test_transcribe.py`

说明: faster-whisper 真实转写不进单测(依赖模型/音频)。单测只覆盖"选出视频且未转写"的纯逻辑;转写函数注入 fake。

- [ ] **Step 1: 写失败测试**

```python
# tests/test_transcribe.py
from src.transcribe import select_pending_videos, transcribe_notes


def _note(nid, type_, video=None):
    return {"id": nid, "type": type_, "video_url": video}


def test_select_only_videos_not_done():
    notes = [_note("a", "图文"), _note("b", "视频", "u"), _note("c", "视频", "u")]
    pending = select_pending_videos(notes, done_ids={"c"})
    assert [n["id"] for n in pending] == ["b"]


def test_transcribe_notes_writes_txt_and_marks_done(tmp_path):
    notes = [_note("b", "视频", "http://v/b.mp4")]
    done = []
    out = transcribe_notes(
        notes,
        out_dir=tmp_path,
        transcriber=lambda url: "这是逐字稿",
        mark_done=lambda nid, status: done.append((nid, status)),
    )
    assert (tmp_path / "b.txt").read_text(encoding="utf-8") == "这是逐字稿"
    assert done == [("b", "ok")]
    assert out == 1


def test_transcribe_failure_is_soft(tmp_path):
    notes = [_note("b", "视频", "http://v/b.mp4")]
    done = []

    def boom(url):
        raise RuntimeError("download failed")

    out = transcribe_notes(notes, out_dir=tmp_path, transcriber=boom,
                           mark_done=lambda nid, status: done.append((nid, status)))
    assert out == 0
    assert done[0][0] == "b" and done[0][1].startswith("failed")
    assert not (tmp_path / "b.txt").exists()
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/test_transcribe.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: 实现**

```python
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
```

- [ ] **Step 4: 运行测试确认通过**

Run: `pytest tests/test_transcribe.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add src/transcribe.py tests/test_transcribe.py
git commit -m "feat: add stage2 transcribe with fail-soft logic"
```

---

## Task 9: 手动 smoke 脚本 + 字段校正

**Files:**
- Create: `scripts/smoke_fetch.py`
- Create: `src/lib/config.py`
- Test: `tests/test_config.py`

- [ ] **Step 1: 写 config 失败测试**

```python
# tests/test_config.py
from src.lib.config import load_config


def test_load_config_reads_values(tmp_path):
    p = tmp_path / "config.yaml"
    p.write_text(
        "time_window_years: 2\n"
        "fetch:\n  min_interval_s: 3.0\n  max_interval_s: 8.0\n  max_notes: null\n"
        "transcribe:\n  enabled: true\n  model_size: small\n  language: zh\n"
        "paths:\n  data_dir: data\n  vault_dir: vault\n",
        encoding="utf-8",
    )
    cfg = load_config(p)
    assert cfg.time_window_years == 2
    assert cfg.fetch.min_interval_s == 3.0
    assert cfg.paths.data_dir == "data"
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/test_config.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: 实现 config**

```python
# src/lib/config.py
from pathlib import Path
import yaml
from pydantic import BaseModel


class FetchCfg(BaseModel):
    min_interval_s: float = 3.0
    max_interval_s: float = 8.0
    max_notes: int | None = None


class TranscribeCfg(BaseModel):
    enabled: bool = True
    model_size: str = "small"
    language: str = "zh"


class PathsCfg(BaseModel):
    data_dir: str = "data"
    vault_dir: str = "vault"


class Config(BaseModel):
    time_window_years: int = 2
    fetch: FetchCfg = FetchCfg()
    transcribe: TranscribeCfg = TranscribeCfg()
    paths: PathsCfg = PathsCfg()


def load_config(path="config.yaml") -> Config:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    return Config(**data)
```

- [ ] **Step 4: 运行测试确认通过**

Run: `pytest tests/test_config.py -v`
Expected: PASS (1 passed)

- [ ] **Step 5: 写 smoke 脚本**

```python
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
```

- [ ] **Step 6: 运行 smoke 并按真实输出校正适配**

Run: `xhs login` 然后 `python scripts/smoke_fetch.py`
Expected: 打印登录用户名与首条原始字段。
**若字段名与 Task 5 `cli_note_to_model` 假设不一致**,据"首条原始字段"输出修正 `cli_note_to_model` 与 `select_new_in_window` 里用到的键名,并补/改对应单测后重跑 `pytest -q`。

- [ ] **Step 7: 运行全部测试**

Run: `pytest -q`
Expected: 全绿。

- [ ] **Step 8: Commit**

```bash
git add scripts/smoke_fetch.py src/lib/config.py tests/test_config.py
git commit -m "feat: add config loader and manual fetch smoke script"
```

---

## 验证 Plan 1 完成

- [ ] `pytest -q` 全绿,纯逻辑覆盖率达标(schema/timewindow/ratelimit/store/xhs_client/fetch/auth/transcribe/config)
- [ ] `python scripts/smoke_fetch.py` 能登录并抓到样本,`cli_note_to_model` 字段已按真实输出校正
- [ ] `data/raw_notes.json`(或 smoke 文件)结构符合 `Note` schema
- [ ] 视频笔记可经 `transcribe_notes` 生成 txt(音频下载在 smoke 阶段对接)
- [ ] `.gitignore` 已覆盖 `data/`、`config.yaml`

完成后进入 **Plan 2 — Knowledge base + Classify**。
