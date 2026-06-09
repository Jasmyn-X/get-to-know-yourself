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
