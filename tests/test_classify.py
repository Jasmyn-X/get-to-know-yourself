# tests/test_classify.py
from src.classify import tokenize


def test_tokenize_keeps_meaningful_terms_and_english():
    toks = tokenize("0-1 Vibe Coding 蓝图教程！AI Agent 闭环设计")
    assert "coding" in toks          # 英文保留(小写)
    assert "ai" in toks
    assert "教程" not in toks         # 水词被过滤
    assert any("设计" == t or "闭环" == t for t in toks)


def test_tokenize_strips_punctuation_and_emoji():
    toks = tokenize("‼️超嫩滑的滑蛋牛肉饭💕")
    assert all("‼" not in t and "💕" not in t for t in toks)
    assert "牛肉" in toks or "滑蛋" in toks
