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
