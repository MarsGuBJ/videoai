"""_fill_daily_trend 纯函数单元测试：趋势日期补齐。"""

from datetime import date

from app.services.deployment_events import _fill_daily_trend


def test_fill_daily_trend_pads_missing_days():
    rows = [(date(2026, 1, 1), 3), (date(2026, 1, 3), 2)]

    trend = _fill_daily_trend(rows, date(2026, 1, 1), date(2026, 1, 4))

    assert [(item.date, item.count) for item in trend] == [
        ("2026-01-01", 3),
        ("2026-01-02", 0),
        ("2026-01-03", 2),
        ("2026-01-04", 0),
    ]


def test_fill_daily_trend_accepts_string_keys():
    rows = [("2026-01-02", 5)]

    trend = _fill_daily_trend(rows, date(2026, 1, 1), date(2026, 1, 2))

    assert [(item.date, item.count) for item in trend] == [("2026-01-01", 0), ("2026-01-02", 5)]


def test_fill_daily_trend_crosses_month_boundary():
    trend = _fill_daily_trend([], date(2026, 1, 30), date(2026, 2, 2))

    assert [item.date for item in trend] == ["2026-01-30", "2026-01-31", "2026-02-01", "2026-02-02"]
    assert all(item.count == 0 for item in trend)


def test_fill_daily_trend_single_day():
    trend = _fill_daily_trend([(date(2026, 3, 1), 7)], date(2026, 3, 1), date(2026, 3, 1))

    assert [(item.date, item.count) for item in trend] == [("2026-03-01", 7)]
