"""위험도 단계별 맞춤 안내와 위기 연락처.

연락처 출처(2026-11 확인)
- 자살예방상담전화 109: 보건복지부, 2024.1.1.부터 기존 1393 등을 통합한 24시간 번호.
- 정신건강위기상담전화 1577-0199: 지역 정신건강복지센터 연결, 24시간.
- 청소년전화 1388, 긴급 119(구급)·112(경찰).
번호는 바뀔 수 있으므로 발표 전에 다시 확인할 것.
"""

from __future__ import annotations

from .screening import RiskLevel, ScreeningResult

CRISIS_CONTACTS = [
    {"name": "자살예방상담전화", "number": "109", "hours": "24시간", "note": "국번 없이 109"},
    {"name": "정신건강위기상담전화", "number": "1577-0199", "hours": "24시간", "note": "지역 정신건강복지센터 연결"},
    {"name": "청소년전화", "number": "1388", "hours": "24시간", "note": "만 24세 이하"},
    {"name": "응급 상황", "number": "119 / 112", "hours": "24시간", "note": "지금 당장 위험할 때"},
]

GUIDANCE: dict[RiskLevel, dict] = {
    RiskLevel.SELF_CARE: {
        "headline": "지금은 스스로 돌보며 지켜봐도 괜찮은 상태로 보여요.",
        "actions": [
            "수면 시간을 일정하게 유지하고, 하루 20~30분 가볍게 걸어 보세요.",
            "힘든 일을 믿을 만한 사람 한 명에게 이야기해 보세요.",
            "2주 뒤 다시 검진해 변화를 확인해 보세요.",
            "상담이 필요하다고 느끼면 점수와 상관없이 언제든 예약할 수 있어요.",
        ],
        "recheck_days": 14,
        "suggest_booking": False,
    },
    RiskLevel.COUNSELING: {
        "headline": "전문 상담사와 이야기해 보는 것을 권해요.",
        "actions": [
            "교내 상담센터나 지역 기관 상담을 1~2주 안에 받아 보세요.",
            "대면이 부담되면 채팅·화상 상담부터 시작해도 괜찮아요.",
            "증상이 2주 이상 계속되거나 심해지면 정신건강의학과 진료도 고려하세요.",
        ],
        "recheck_days": 14,
        "suggest_booking": True,
    },
    RiskLevel.PRIORITY: {
        "headline": "가능한 한 빨리 전문가와 연결되는 것이 좋겠어요.",
        "actions": [
            "가장 빨리 가능한 상담 일정을 아래에서 확인하세요.",
            "기다리는 동안 힘들어지면 109 또는 1577-0199로 바로 전화하세요(24시간).",
            "정신건강의학과 진료를 받아 보는 것을 권해요.",
        ],
        "recheck_days": 7,
        "suggest_booking": True,
    },
}

SAFETY_MESSAGE = (
    "죽음이나 자해에 대한 생각이 든다고 답해 주셨어요. 말해 주어서 고마워요. "
    "혼자 견디지 않아도 됩니다. 지금 바로 **109(자살예방상담전화, 24시간)** 에 "
    "전화하거나, 당장 위험하다면 **119** 에 연락하세요."
)

DISCLAIMER = (
    "이 결과는 PHQ-9·GAD-7 자가 선별 점수에 따른 안내이며 의학적 진단이 아닙니다. "
    "교육용 프로토타입으로, 실제 진단·치료를 대신하지 않습니다."
)


def guidance_for(result: ScreeningResult) -> dict:
    g = dict(GUIDANCE[result.level])
    g["show_crisis_banner"] = result.safety_flag
    g["show_contacts"] = result.level >= RiskLevel.COUNSELING or result.safety_flag
    return g
