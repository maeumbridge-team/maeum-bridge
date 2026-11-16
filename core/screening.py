"""PHQ-9 / GAD-7 채점과 3단계 위험도 분류.

출처
- PHQ-9: Kroenke K, Spitzer RL, Williams JBW. J Gen Intern Med. 2001;16(9):606-613.
- GAD-7: Spitzer RL, Kroenke K, Williams JBW, Löwe B. Arch Intern Med. 2006;166(10):1092-1097.
- 이용 조건: Pfizer 교육 연구비로 개발되었으며 "No permission required to reproduce,
  translate, display or distribute" (www.phqscreeners.com).
- 한국어 문항은 공식 한국어판을 참고해 옮겼다. 제출 전 phqscreeners.com의
  공식 한국어판 PDF와 문구를 한 번 더 대조할 것.

주의: 이 모듈의 결과는 선별(screening) 결과이며 진단이 아니다.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum

# ---------------------------------------------------------------------------
# 문항
# ---------------------------------------------------------------------------

PHQ9_STEM = "지난 2주 동안, 다음과 같은 문제들로 인해 얼마나 자주 방해를 받았습니까?"
GAD7_STEM = "지난 2주 동안, 다음과 같은 문제들로 인해 얼마나 자주 방해를 받았습니까?"

PHQ9_ITEMS: list[str] = [
    "일 또는 여가 활동을 하는 데 흥미나 즐거움을 느끼지 못함",
    "기분이 가라앉거나, 우울하거나, 희망이 없음",
    "잠이 들거나 계속 잠을 자는 것이 어려움, 또는 잠을 너무 많이 잠",
    "피곤하다고 느끼거나 기운이 거의 없음",
    "입맛이 없거나 과식을 함",
    "자신을 부정적으로 봄 — 혹은 자신이 실패자라고 느끼거나 자신 또는 가족을 실망시킴",
    "신문을 읽거나 텔레비전 보는 것과 같은 일에 집중하는 것이 어려움",
    "다른 사람들이 알아챌 정도로 너무 느리게 움직이거나 말을 함, "
    "또는 반대로 평상시보다 많이 움직여서 너무 안절부절못하거나 들떠 있음",
    "자신이 죽는 것이 더 낫다고 생각하거나, 어떤 식으로든 자신을 해칠 것이라고 생각함",
]

GAD7_ITEMS: list[str] = [
    "초조하거나 불안하거나 조마조마하게 느낀다",
    "걱정하는 것을 멈추거나 조절할 수가 없다",
    "여러 가지 것들에 대해 걱정을 너무 많이 한다",
    "편하게 있기가 어렵다",
    "너무 안절부절못해서 가만히 있기가 힘들다",
    "쉽게 짜증이 나거나 쉽게 성을 낸다",
    "마치 끔찍한 일이 생길 것처럼 두렵게 느껴진다",
]

RESPONSE_OPTIONS: list[str] = [
    "전혀 방해받지 않았다",   # 0
    "며칠 동안 방해받았다",   # 1
    "7일 이상 방해받았다",    # 2
    "거의 매일 방해받았다",   # 3
]

SUICIDE_ITEM_INDEX = 8  # PHQ-9의 9번 문항(0부터 셈)

# ---------------------------------------------------------------------------
# 절단점(cut-off) — 근거를 함께 둔다
# ---------------------------------------------------------------------------
# PHQ-9 중증도: 0-4 최소, 5-9 경도, 10-14 중등도, 15-19 중등도-중증, 20-27 중증
#   (Kroenke 2001). 10점은 주요우울장애 선별에 가장 널리 쓰이는 절단점이며,
#   한국어판 타당화 연구에서도 10점 내외가 제시되었다.
# GAD-7 중증도: 0-4 최소, 5-9 경도, 10-14 중등도, 15-21 중증 (Spitzer 2006).
CUTOFFS = {
    "phq_moderate": 10,   # 이 점수 이상 → 2단계(상담 권고)
    "phq_high": 15,       # 이 점수 이상 → 3단계(우선 연계)
    "gad_moderate": 10,
    "gad_high": 15,
}

PHQ9_SEVERITY = [(0, 4, "최소"), (5, 9, "경도"), (10, 14, "중등도"),
                 (15, 19, "중등도-중증"), (20, 27, "중증")]
GAD7_SEVERITY = [(0, 4, "최소"), (5, 9, "경도"), (10, 14, "중등도"), (15, 21, "중증")]


class RiskLevel(IntEnum):
    """서비스 안내 단계. 숫자가 클수록 더 빠른 연계가 필요하다."""
    SELF_CARE = 1      # 1단계: 자가관리 + 2주 후 재검진
    COUNSELING = 2     # 2단계: 상담 권고
    PRIORITY = 3       # 3단계: 우선 연계 (전문가 상담 빠르게)

    @property
    def label(self) -> str:
        return {1: "1단계 · 자가관리", 2: "2단계 · 상담 권고", 3: "3단계 · 우선 연계"}[self.value]


@dataclass(frozen=True)
class ScreeningResult:
    phq9_total: int
    gad7_total: int
    phq9_severity: str
    gad7_severity: str
    level: RiskLevel
    safety_flag: bool                 # PHQ-9 9번 문항 ≥1
    reasons: list[str] = field(default_factory=list)


class InvalidResponseError(ValueError):
    pass


# ---------------------------------------------------------------------------
# 채점
# ---------------------------------------------------------------------------

def _validate(responses: list[int], n_items: int, name: str) -> None:
    if responses is None or len(responses) != n_items:
        raise InvalidResponseError(f"{name}은(는) {n_items}개 문항에 모두 응답해야 합니다.")
    for i, r in enumerate(responses, start=1):
        if isinstance(r, bool) or not isinstance(r, int) or r not in (0, 1, 2, 3):
            raise InvalidResponseError(f"{name} {i}번 응답은 0~3 사이 정수여야 합니다: {r!r}")


def score_phq9(responses: list[int]) -> int:
    _validate(responses, 9, "PHQ-9")
    return sum(responses)


def score_gad7(responses: list[int]) -> int:
    _validate(responses, 7, "GAD-7")
    return sum(responses)


def severity(total: int, table: list[tuple[int, int, str]]) -> str:
    for lo, hi, name in table:
        if lo <= total <= hi:
            return name
    raise InvalidResponseError(f"점수 범위를 벗어났습니다: {total}")


def classify(phq9: list[int], gad7: list[int]) -> ScreeningResult:
    """응답을 받아 3단계 위험도를 결정한다.

    규칙(우선순위 순서):
      1) PHQ-9 9번 문항(자해·죽음에 대한 생각)이 1점 이상이면 총점과 무관하게
         3단계 + 안전 플래그. 총점이 낮아도 놓치면 안 되는 신호이기 때문.
      2) PHQ-9 ≥15 또는 GAD-7 ≥15 → 3단계
      3) PHQ-9 ≥10 또는 GAD-7 ≥10 → 2단계
      4) 그 외 → 1단계
    두 척도 중 더 높은 쪽을 따른다(보수적 선택).
    """
    phq_total = score_phq9(phq9)
    gad_total = score_gad7(gad7)
    c = CUTOFFS
    reasons: list[str] = []

    safety_flag = phq9[SUICIDE_ITEM_INDEX] >= 1
    if safety_flag:
        reasons.append("PHQ-9 9번 문항(자해·죽음에 대한 생각)에 응답함 → 총점과 관계없이 우선 안내")

    if phq_total >= c["phq_high"]:
        reasons.append(f"PHQ-9 {phq_total}점 (≥{c['phq_high']})")
    if gad_total >= c["gad_high"]:
        reasons.append(f"GAD-7 {gad_total}점 (≥{c['gad_high']})")

    if safety_flag or phq_total >= c["phq_high"] or gad_total >= c["gad_high"]:
        level = RiskLevel.PRIORITY
    elif phq_total >= c["phq_moderate"] or gad_total >= c["gad_moderate"]:
        level = RiskLevel.COUNSELING
        if phq_total >= c["phq_moderate"]:
            reasons.append(f"PHQ-9 {phq_total}점 (≥{c['phq_moderate']})")
        if gad_total >= c["gad_moderate"]:
            reasons.append(f"GAD-7 {gad_total}점 (≥{c['gad_moderate']})")
    else:
        level = RiskLevel.SELF_CARE
        reasons.append(f"PHQ-9 {phq_total}점, GAD-7 {gad_total}점 (모두 <10)")

    return ScreeningResult(
        phq9_total=phq_total,
        gad7_total=gad_total,
        phq9_severity=severity(phq_total, PHQ9_SEVERITY),
        gad7_severity=severity(gad_total, GAD7_SEVERITY),
        level=level,
        safety_flag=safety_flag,
        reasons=reasons,
    )
