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
