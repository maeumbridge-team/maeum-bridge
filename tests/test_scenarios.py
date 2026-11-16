"""보고서 6장 위험도별 시나리오 3종 회귀 테스트."""

import json
import sys
from datetime import date
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.booking import load_channels, rank_channels  # noqa: E402
from core.guidance import guidance_for  # noqa: E402
from core.screening import RiskLevel, classify  # noqa: E402

SCENARIOS = json.loads((ROOT / "validation" / "scenarios.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("s", SCENARIOS, ids=[s["id"] for s in SCENARIOS])
def test_scenario(s):
    r = classify(s["phq9"], s["gad7"])
    g = guidance_for(r)
    assert int(r.level) == s["expected_level"]
    assert r.safety_flag == s["expected_flag"]
    assert g["show_crisis_banner"] == s["expected_flag"]
    if r.level >= RiskLevel.COUNSELING:
        assert g["suggest_booking"] and g["show_contacts"]
    t = rank_channels(load_channels(), r.level == RiskLevel.PRIORITY, date(2026, 11, 16),
                      s["preferred_modes"], 7)
    assert t.iloc[0]["방식"] in s["preferred_modes"]
