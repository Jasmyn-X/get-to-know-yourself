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
