"""대기 추정·익명 예약 테스트. 실제 DB 대신 임시 파일을 쓴다."""

import re
import sys
from datetime import date, datetime
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.booking import (SlotTakenError, add_business_days, available_slots, book,  # noqa: E402
                          cancel, estimate_wait, load_channels, lookup, rank_channels)

MON = date(2026, 11, 16)  # 월요일
FRI = date(2026, 11, 20)


def test_business_days_skip_weekend():
    assert add_business_days(FRI, 1) == date(2026, 11, 23)
    assert add_business_days(MON, 5) == date(2026, 11, 23)
    assert add_business_days(date(2026, 11, 21), 0) == date(2026, 11, 23)  # 토 → 월


def _row(**kw):
    base = dict(channel_id="x", org="o", mode="대면", counselors=2, sessions_per_counselor_per_day=5,
                waiting_now=0, urgent_slots_per_day=2, urgent_waiting=0, location="l")
    base.update(kw)
    return pd.Series(base)


def test_wait_formula_regular():
    # 처리량 2*5-2 = 8/일, 앞 대기 16명 → 내 순번 17 → ceil(17/8)=3 영업일
    w = estimate_wait(_row(waiting_now=16), priority=False, today=MON)
    assert w.wait_business_days == 3
    assert w.first_date == date(2026, 11, 19)


def test_priority_uses_urgent_track_and_is_not_slower():
    r = _row(waiting_now=40, urgent_waiting=1)
    normal = estimate_wait(r, priority=False, today=MON)
    urgent = estimate_wait(r, priority=True, today=MON)
    assert urgent.used_urgent_track
    assert urgent.wait_business_days <= normal.wait_business_days


def test_priority_without_urgent_slots_falls_back():
    w = estimate_wait(_row(urgent_slots_per_day=0, waiting_now=3), priority=True, today=MON)
    assert not w.used_urgent_track


def test_sample_data_priority_never_slower():
    df = load_channels()
    for _, r in df.iterrows():
        assert (estimate_wait(r, True, MON).wait_business_days
                <= estimate_wait(r, False, MON).wait_business_days)


def test_rank_puts_preferred_first_and_sorted():
    t = rank_channels(load_channels(), priority=False, today=MON, preferred_modes=["채팅"], max_wait_days=7)
    assert t.iloc[0]["방식"] == "채팅"
    rest = t[~t["선호 방식"]]["예상 대기(영업일)"].tolist()
    assert rest == sorted(rest)
    assert "희망 기간 내" in t.columns


def test_bad_csv_rejected(tmp_path):
    p = tmp_path / "c.csv"
    p.write_text("channel_id,org\nx,y\n", encoding="utf-8")
    with pytest.raises(ValueError):
        load_channels(p)


# --- 예약 -------------------------------------------------------------------

def test_book_lookup_cancel_roundtrip(tmp_path):
    db = tmp_path / "b.db"
    slot = available_slots("campus_chat", MON, db_path=db)[0]
    code = book("campus_chat", slot, priority=True, db_path=db)
    assert re.fullmatch(r"MB-[A-Z2-9]{4}-[A-Z2-9]{4}", code)
    got = lookup(code.lower(), db_path=db)
    assert got["slot"] == slot and got["priority"] is True
    assert slot not in available_slots("campus_chat", MON, db_path=db)
    assert cancel(code, db_path=db)
    assert lookup(code, db_path=db) is None
    assert slot in available_slots("campus_chat", MON, db_path=db)


def test_double_booking_blocked(tmp_path):
    db = tmp_path / "b.db"
    slot = datetime(2026, 11, 16, 10)
    book("campus_f2f", slot, False, db_path=db)
    with pytest.raises(SlotTakenError):
        book("campus_f2f", slot, False, db_path=db)


def test_no_personal_columns_in_db(tmp_path):
    import sqlite3
    db = tmp_path / "b.db"
    book("campus_f2f", datetime(2026, 11, 16, 10), False, db_path=db)
    cols = {r[1] for r in sqlite3.connect(db).execute("PRAGMA table_info(bookings)")}
    assert cols == {"code", "channel_id", "slot", "priority", "created_at"}


def test_slots_are_weekdays_only(tmp_path):
    for s in available_slots("campus_f2f", FRI, db_path=tmp_path / "b.db", n_days=5):
        assert s.weekday() < 5
