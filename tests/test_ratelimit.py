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
