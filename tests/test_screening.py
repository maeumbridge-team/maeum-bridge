"""채점·위험도 분류 단위 테스트."""

import itertools
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.screening import (CUTOFFS, InvalidResponseError, RiskLevel, classify,  # noqa: E402
                            score_gad7, score_phq9)


def phq_with_total(total: int, item9: int = 0) -> list[int]:
    """9번 문항을 item9로 고정하고 나머지 8문항으로 total을 채운 응답."""
    rest = total - item9
    assert 0 <= rest <= 24
    out = []
    for _ in range(8):
        v = min(3, rest)
        out.append(v)
        rest -= v
    return out + [item9]


def gad_with_total(total: int) -> list[int]:
    out, rest = [], total
    for _ in range(7):
        v = min(3, rest)
        out.append(v)
        rest -= v
    return out


# --- 채점 ------------------------------------------------------------------

def test_score_min_max():
    assert score_phq9([0] * 9) == 0
    assert score_phq9([3] * 9) == 27
    assert score_gad7([0] * 7) == 0
    assert score_gad7([3] * 7) == 21


@pytest.mark.parametrize("bad", [[0] * 8, [0] * 10, [0] * 8 + [4], [0] * 8 + [-1],
                                 [0] * 8 + [1.5], [0] * 8 + ["1"], [0] * 8 + [True], None])
def test_invalid_phq_rejected(bad):
    with pytest.raises(InvalidResponseError):
        score_phq9(bad)


# --- 절단점 경계 -------------------------------------------------------------

@pytest.mark.parametrize("total,expected", [
    (0, RiskLevel.SELF_CARE), (9, RiskLevel.SELF_CARE),
    (10, RiskLevel.COUNSELING), (14, RiskLevel.COUNSELING),
    (15, RiskLevel.PRIORITY), (24, RiskLevel.PRIORITY),  # 9번=0일 때 최대 24점
])
def test_phq_boundaries(total, expected):
    assert classify(phq_with_total(total), [0] * 7).level == expected


@pytest.mark.parametrize("total,expected", [
    (0, RiskLevel.SELF_CARE), (9, RiskLevel.SELF_CARE),
    (10, RiskLevel.COUNSELING), (14, RiskLevel.COUNSELING),
    (15, RiskLevel.PRIORITY), (21, RiskLevel.PRIORITY),
])
def test_gad_boundaries(total, expected):
    assert classify([0] * 9, gad_with_total(total)).level == expected


def test_higher_scale_wins():
    # 우울은 낮고 불안만 높아도 높은 쪽을 따른다
    r = classify(phq_with_total(3), gad_with_total(16))
    assert r.level == RiskLevel.PRIORITY


# --- 안전 규칙: 9번 문항 ------------------------------------------------------

@pytest.mark.parametrize("item9", [1, 2, 3])
def test_item9_overrides_low_total(item9):
    r = classify(phq_with_total(item9, item9=item9), [0] * 7)
    assert r.phq9_total == item9 < CUTOFFS["phq_moderate"]
    assert r.level == RiskLevel.PRIORITY
    assert r.safety_flag is True


def test_no_flag_when_item9_zero():
    r = classify(phq_with_total(14, item9=0), [0] * 7)
    assert r.safety_flag is False


# --- 전수 검증: 단조성 + 안전 규칙 --------------------------------------------

def test_exhaustive_phq_space_safety_and_level():
    """PHQ-9 응답 전체(4^9 = 262,144가지)에 대해 9번 문항 규칙과 단계 규칙을 확인."""
    gad0 = [0] * 7
    for resp in itertools.product(range(4), repeat=9):
        r = classify(list(resp), gad0)
        t = sum(resp)
        if resp[8] >= 1:
            assert r.level == RiskLevel.PRIORITY and r.safety_flag
        elif t >= 15:
            assert r.level == RiskLevel.PRIORITY
        elif t >= 10:
            assert r.level == RiskLevel.COUNSELING
        else:
            assert r.level == RiskLevel.SELF_CARE


def test_monotonic_in_totals():
    """어느 응답을 올려도 단계가 내려가지 않는다(9번 문항 0 고정, 총점 격자 전수)."""
    prev_row = None
    for p in range(0, 25):
        row = [classify(phq_with_total(p), gad_with_total(g)).level for g in range(22)]
        assert row == sorted(row)
        if prev_row:
            assert all(a <= b for a, b in zip(prev_row, row))
        prev_row = row
