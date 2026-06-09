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
