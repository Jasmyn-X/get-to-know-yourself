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
