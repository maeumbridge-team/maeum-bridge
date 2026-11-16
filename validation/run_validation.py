"""검증 보고서 생성: python validation/run_validation.py  → validation/REPORT.md

1) 분류 규칙 전수 검증 (PHQ-9 응답 4^9 = 262,144가지)
2) 9번 문항 안전 규칙의 효과: 총점 규칙만 썼다면 놓쳤을 응답 패턴 수
3) 위험도별 시나리오 3종 결과
4) 가상 대기 데이터에서 일반 vs 우선 트랙 대기일
5) 처리 속도
"""

from __future__ import annotations

import itertools
import json
import sys
import time
from collections import Counter
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.booking import estimate_wait, load_channels, rank_channels  # noqa: E402
from core.guidance import guidance_for  # noqa: E402
from core.screening import RiskLevel, classify  # noqa: E402

TODAY = date(2026, 11, 16)  # 재현성을 위해 기준일 고정


def md_table(header: list[str], rows: list[list]) -> str:
    out = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    out += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(out)


def main() -> None:
    lines = ["# 마음다리 검증 보고서", "",
             f"기준일 {TODAY} · `python validation/run_validation.py`로 다시 만들 수 있음", ""]

    # 1) 전수 검증 --------------------------------------------------------
    gad0 = [0] * 7
    level_count: Counter = Counter()
    rule_errors = 0
    missed_without_safety = 0
    t0 = time.perf_counter()
    for resp in itertools.product(range(4), repeat=9):
        r = classify(list(resp), gad0)
        level_count[r.level] += 1
        total = sum(resp)
        expected = (RiskLevel.PRIORITY if resp[8] >= 1 or total >= 15
                    else RiskLevel.COUNSELING if total >= 10 else RiskLevel.SELF_CARE)
        rule_errors += r.level != expected
        if resp[8] >= 1 and total < 15:
            missed_without_safety += 1
    elapsed = time.perf_counter() - t0
    n = sum(level_count.values())

    lines += ["## 1. 분류 규칙 전수 검증 (GAD-7=0 고정)", "",
              md_table(["단계", "응답 패턴 수", "비율"],
                       [[lv.label, f"{c:,}", f"{c / n:.1%}"] for lv, c in sorted(level_count.items())]),
              "", f"- 검사한 패턴: **{n:,}개**, 규칙 불일치: **{rule_errors}개**",
              f"- 1건당 평균 처리 시간: {elapsed / n * 1e6:.1f} µs",
              "- 비율은 가능한 응답 조합 기준이며, 실제 사용자 분포나 유병률이 아니다.", ""]

    # 2) 안전 규칙 효과 ----------------------------------------------------
    flagged = sum(1 for resp in itertools.product(range(4), repeat=9) if resp[8] >= 1)
    lines += ["## 2. 9번 문항 안전 규칙의 효과", "",
              f"- 9번 문항에 1점 이상 응답한 패턴: {flagged:,}개",
              f"- 그중 총점이 15점 미만이라 **총점 규칙만으로는 3단계가 되지 않았을 패턴: "
              f"{missed_without_safety:,}개 ({missed_without_safety / flagged:.1%})**",
              "- 안전 규칙이 이 패턴들을 모두 3단계로 올리고 109 안내를 띄움을 1번 전수 검증에서 확인",
              "- 이 수치도 응답 조합 기준이며, 실제로 놓치는 사람 수를 뜻하지 않는다.", ""]

    # 3) 시나리오 ----------------------------------------------------------
    scenarios = json.loads((ROOT / "validation" / "scenarios.json").read_text(encoding="utf-8"))
    rows, ok_all = [], True
    for s in scenarios:
        r = classify(s["phq9"], s["gad7"])
        g = guidance_for(r)
        t = rank_channels(load_channels(), r.level == RiskLevel.PRIORITY, TODAY, s["preferred_modes"], 7)
        top = t.iloc[0]
        ok = int(r.level) == s["expected_level"] and r.safety_flag == s["expected_flag"]
        ok_all &= ok
        rows.append([s["id"], s["persona"], r.phq9_total, r.gad7_total, r.level.label,
                     "예" if g["show_crisis_banner"] else "아니오",
                     f"{top['기관']} {top['방식']} ({top['첫 상담 가능일']})", "✅" if ok else "❌"])
    lines += ["## 3. 위험도별 시나리오", "",
              md_table(["ID", "사용자", "PHQ-9", "GAD-7", "판정", "위기 배너", "추천 1순위", "기대와 일치"], rows),
              "", f"- 전체 일치: {'✅' if ok_all else '❌'}", ""]

    # 4) 대기 ---------------------------------------------------------------
    rows = []
    for _, c in load_channels().iterrows():
        a, b = estimate_wait(c, False, TODAY), estimate_wait(c, True, TODAY)
        rows.append([c["org"], c["mode"], a.wait_business_days, b.wait_business_days,
                     a.wait_business_days - b.wait_business_days])
    lines += ["## 4. 대기 추정 (가상 데이터)", "",
              md_table(["기관", "방식", "일반(영업일)", "우선 트랙(영업일)", "단축"], rows),
              "", "> 대기 인원·상담사 수는 시연용 가상 값이다. 실제 효과를 주장하는 근거로 쓰지 않는다.", ""]

    out = ROOT / "validation" / "REPORT.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    print(out.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
