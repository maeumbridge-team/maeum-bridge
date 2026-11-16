"""대기 현황 추정과 익명 예약.

데이터 주의: data/channels.csv 는 **가상(합성) 데이터**다. 실제 기관의 대기 인원이
아니며, 기관명도 '(예시)'로 표시했다. 실제 운영하려면 상담센터 예약 시스템과
연동해야 한다.

개인정보 원칙
- 예약 시 이름·학번·연락처를 받지 않는다. 무작위 익명 코드만 발급한다.
- 검진 응답 원본은 저장하지 않는다. 예약에는 '우선 연계 여부(참/거짓)'만 남긴다.
"""

from __future__ import annotations

import math
import secrets
import sqlite3
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
CHANNELS_CSV = ROOT / "data" / "channels.csv"
DEFAULT_DB = ROOT / "data" / "bookings.db"

SLOT_HOURS = [10, 11, 13, 14, 15, 16]
CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # 헷갈리는 0/O, 1/I 제외


# ---------------------------------------------------------------------------
# 영업일 계산
# ---------------------------------------------------------------------------

def add_business_days(start: date, n: int) -> date:
    """start 다음 영업일부터 n번째 영업일(주말 제외). n=0이면 start가 평일일 때 start."""
    d = start
    if n == 0:
        while d.weekday() >= 5:
            d += timedelta(days=1)
        return d
    added = 0
    while added < n:
        d += timedelta(days=1)
        if d.weekday() < 5:
            added += 1
    return d


# ---------------------------------------------------------------------------
# 대기 추정
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class WaitEstimate:
    channel_id: str
    org: str
    mode: str
    location: str
    waiting_ahead: int
    wait_business_days: int
    first_date: date
    used_urgent_track: bool


def load_channels(path: Path = CHANNELS_CSV) -> pd.DataFrame:
    df = pd.read_csv(path)
    required = {"channel_id", "org", "mode", "counselors", "sessions_per_counselor_per_day",
                "waiting_now", "urgent_slots_per_day", "urgent_waiting", "location"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"channels.csv에 필요한 열이 없습니다: {missing}")
    if (df["counselors"] <= 0).any() or (df["sessions_per_counselor_per_day"] <= 0).any():
        raise ValueError("상담사 수와 하루 회기 수는 1 이상이어야 합니다.")
    return df


def estimate_wait(row: pd.Series, priority: bool, today: date) -> WaitEstimate:
    """대기열 모델(선입선출, 하루 처리량 고정)로 첫 상담 가능일을 추정한다.

    일반 트랙: 하루 처리량 = 상담사×회기 − 긴급 슬롯
               대기 영업일 = ceil((앞 대기 인원 + 1) / 하루 처리량)
    우선 트랙(3단계): 긴급 슬롯이 있으면 긴급 대기열을 사용
               대기 영업일 = ceil((긴급 대기 + 1) / 긴급 슬롯)
    """
    total_cap = int(row.counselors * row.sessions_per_counselor_per_day)
    urgent_cap = int(row.urgent_slots_per_day)
    regular_cap = max(total_cap - urgent_cap, 1)

    if priority and urgent_cap > 0:
        ahead = int(row.urgent_waiting)
        days = math.ceil((ahead + 1) / urgent_cap)
        used_urgent = True
    else:
        ahead = int(row.waiting_now)
        days = math.ceil((ahead + 1) / regular_cap)
        used_urgent = False

    # 오늘 신청하면 가장 빨라도 다음 영업일부터 상담(접수 처리 시간 가정)
    first = add_business_days(today, days)
    return WaitEstimate(row.channel_id, row.org, row["mode"], row.location,
                        ahead, days, first, used_urgent)


def rank_channels(df: pd.DataFrame, priority: bool, today: date,
                  preferred_modes: list[str] | None = None,
                  max_wait_days: int | None = None) -> pd.DataFrame:
    """선호 방식 → 대기일 순으로 정렬한 표를 돌려준다."""
    rows = []
    for _, r in df.iterrows():
        w = estimate_wait(r, priority, today)
        rows.append({
            "channel_id": w.channel_id,
            "기관": w.org,
            "방식": w.mode,
            "위치": w.location,
            "앞 대기(명)": w.waiting_ahead,
            "예상 대기(영업일)": w.wait_business_days,
            "첫 상담 가능일": w.first_date,
            "우선 트랙": w.used_urgent_track,
            "선호 방식": (preferred_modes is None) or (w.mode in preferred_modes),
        })
    out = pd.DataFrame(rows)
    if max_wait_days is not None:
        out["희망 기간 내"] = [(d - today).days <= max_wait_days for d in out["첫 상담 가능일"]]
    return out.sort_values(["선호 방식", "예상 대기(영업일)"], ascending=[False, True]).reset_index(drop=True)


# ---------------------------------------------------------------------------
# 익명 예약 (SQLite)
# ---------------------------------------------------------------------------

def _connect(db_path: Path) -> sqlite3.Connection:
    con = sqlite3.connect(db_path)
    con.execute(
        """CREATE TABLE IF NOT EXISTS bookings (
               code TEXT PRIMARY KEY,
               channel_id TEXT NOT NULL,
               slot TEXT NOT NULL,
               priority INTEGER NOT NULL,
               created_at TEXT NOT NULL,
               UNIQUE(channel_id, slot)
           )"""
    )
    return con


def new_code() -> str:
    body = "".join(secrets.choice(CODE_ALPHABET) for _ in range(8))
    return f"MB-{body[:4]}-{body[4:]}"


def available_slots(channel_id: str, first_date: date, db_path: Path = DEFAULT_DB,
                    n_days: int = 5) -> list[datetime]:
    """first_date부터 n_days 영업일 동안 비어 있는 슬롯."""
    with _connect(db_path) as con:
        taken = {r[0] for r in con.execute(
            "SELECT slot FROM bookings WHERE channel_id = ?", (channel_id,))}
    slots = []
    base = add_business_days(first_date, 0)  # 주말이면 다음 월요일로
    for i in range(n_days):
        d = add_business_days(base, i)
        for h in SLOT_HOURS:
            s = datetime.combine(d, time(h, 0))
            if s.isoformat() not in taken:
                slots.append(s)
    return slots


class SlotTakenError(RuntimeError):
    pass


def book(channel_id: str, slot: datetime, priority: bool,
         db_path: Path = DEFAULT_DB) -> str:
    code = new_code()
    try:
        with _connect(db_path) as con:
            con.execute(
                "INSERT INTO bookings(code, channel_id, slot, priority, created_at) VALUES (?,?,?,?,?)",
                (code, channel_id, slot.isoformat(), int(priority), datetime.now().isoformat(timespec="seconds")),
            )
    except sqlite3.IntegrityError as e:
        raise SlotTakenError("방금 다른 사람이 예약한 시간입니다. 다른 시간을 골라 주세요.") from e
    return code


def lookup(code: str, db_path: Path = DEFAULT_DB) -> dict | None:
    with _connect(db_path) as con:
        r = con.execute("SELECT code, channel_id, slot, priority FROM bookings WHERE code = ?",
                        (code.strip().upper(),)).fetchone()
    if r is None:
        return None
    return {"code": r[0], "channel_id": r[1], "slot": datetime.fromisoformat(r[2]), "priority": bool(r[3])}


def cancel(code: str, db_path: Path = DEFAULT_DB) -> bool:
    with _connect(db_path) as con:
        cur = con.execute("DELETE FROM bookings WHERE code = ?", (code.strip().upper(),))
        return cur.rowcount > 0
