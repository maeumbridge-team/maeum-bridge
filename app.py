"""마음다리(MaeumBridge) — 자가검진 연계형 대학생 정신건강 상담 접근성 개선 서비스.

실행:  streamlit run app.py
교육용 프로토타입이며 의학적 진단 도구가 아니다.
"""

from __future__ import annotations

from datetime import date

import streamlit as st

from core.booking import (SlotTakenError, available_slots, book, cancel, load_channels,
                          lookup, rank_channels)
from core.guidance import CRISIS_CONTACTS, DISCLAIMER, SAFETY_MESSAGE, guidance_for
from core.screening import (GAD7_ITEMS, GAD7_STEM, PHQ9_ITEMS, PHQ9_STEM, RESPONSE_OPTIONS,
                            RiskLevel, classify)

st.set_page_config(page_title="마음다리 · 익명 자가검진", page_icon="🌉", layout="centered")

LEVEL_STYLE = {
    RiskLevel.SELF_CARE: ("🟢", st.success),
    RiskLevel.COUNSELING: ("🟡", st.warning),
    RiskLevel.PRIORITY: ("🔴", st.error),
}
MODES = ["대면", "채팅", "화상", "전화"]

ss = st.session_state
ss.setdefault("step", "intro")


def go(step: str) -> None:
    ss.step = step
    st.rerun()


def contacts_block() -> None:
    for c in CRISIS_CONTACTS:
        st.markdown(f"**{c['name']} {c['number']}** · {c['hours']} · {c['note']}")


# ---------------------------------------------------------------------------
# 사이드바: 언제나 보이는 위기 연락처 + 예약 조회
# ---------------------------------------------------------------------------
with st.sidebar:
    st.subheader("지금 많이 힘들다면")
    contacts_block()
    st.divider()
    st.subheader("내 예약 확인·취소")
    q = st.text_input("익명 예약 코드", placeholder="MB-XXXX-XXXX")
    c1, c2 = st.columns(2)
    if c1.button("조회", use_container_width=True) and q:
        r = lookup(q)
        if r:
            ch = load_channels().set_index("channel_id").loc[r["channel_id"]]
            st.info(f"{ch['org']} · {ch['mode']} · {r['slot']:%m/%d %H:%M}")
        else:
            st.warning("예약이 없습니다.")
    if c2.button("취소", use_container_width=True) and q:
        if cancel(q):
            st.success("취소했습니다.")
        else:
            st.warning("예약이 없습니다.")
    st.divider()
    st.caption(DISCLAIMER)

st.title("🌉 마음다리")
st.caption("로그인 없이 3분 · 익명 자가검진에서 상담 예약까지")

# ---------------------------------------------------------------------------
# 1. 안내 및 동의
# ---------------------------------------------------------------------------
if ss.step == "intro":
    st.markdown(
        """
- 우울(PHQ-9) 9문항, 불안(GAD-7) 7문항에 답하면 결과를 바로 알려드려요.
- **이름·학번·연락처를 묻지 않습니다.** 응답은 이 화면에서만 계산하고 저장하지 않아요.
- 예약하면 무작위 익명 코드만 발급됩니다.
        """
    )
    st.info(DISCLAIMER)
    agree = st.checkbox("위 내용을 이해했고, 이 결과가 진단이 아니라는 점에 동의합니다.")
    if st.button("검진 시작", type="primary", disabled=not agree):
        go("screen")

# ---------------------------------------------------------------------------
# 2. 검진
# ---------------------------------------------------------------------------
elif ss.step == "screen":
    with st.form("screen"):
        st.subheader("1. 우울 (PHQ-9)")
        st.caption(PHQ9_STEM)
        phq = [st.radio(f"{i+1}. {t}", range(4), index=None, key=f"phq{i}",
                        format_func=lambda v: RESPONSE_OPTIONS[v], horizontal=True)
               for i, t in enumerate(PHQ9_ITEMS)]
        st.subheader("2. 불안 (GAD-7)")
        st.caption(GAD7_STEM)
        gad = [st.radio(f"{i+1}. {t}", range(4), index=None, key=f"gad{i}",
                        format_func=lambda v: RESPONSE_OPTIONS[v], horizontal=True)
               for i, t in enumerate(GAD7_ITEMS)]
        submitted = st.form_submit_button("결과 보기", type="primary")

    if submitted:
        missing = [f"PHQ-9 {i+1}" for i, v in enumerate(phq) if v is None] + \
                  [f"GAD-7 {i+1}" for i, v in enumerate(gad) if v is None]
        if missing:
            st.error("아직 답하지 않은 문항이 있어요: " + ", ".join(missing))
        else:
            res = classify(phq, gad)
            # 응답 원본은 버리고 결과만 세션에 둔다(서버에 저장하지 않음)
            ss.result = res
            for k in [f"phq{i}" for i in range(9)] + [f"gad{i}" for i in range(7)]:
                ss.pop(k, None)
            go("result")

# ---------------------------------------------------------------------------
# 3. 결과 + 대기 현황 + 예약
# ---------------------------------------------------------------------------
elif ss.step == "result":
    res = ss.result
    g = guidance_for(res)

    if g["show_crisis_banner"]:
        st.error(SAFETY_MESSAGE)

    icon, box = LEVEL_STYLE[res.level]
    box(f"{icon} **{res.level.label}** — {g['headline']}")

    c1, c2 = st.columns(2)
    c1.metric(f"우울 PHQ-9 · {res.phq9_severity}", f"{res.phq9_total} / 27")
    c2.metric(f"불안 GAD-7 · {res.gad7_severity}", f"{res.gad7_total} / 21")
    with st.expander("이렇게 판단한 이유"):
        for r in res.reasons:
            st.markdown(f"- {r}")
        st.caption("기준: PHQ-9·GAD-7 각 10점 이상 → 상담 권고, 15점 이상 또는 PHQ-9 9번 문항 응답 → 우선 연계")

    st.subheader("지금 해 볼 수 있는 것")
    for a in g["actions"]:
        st.markdown(f"- {a}")
    st.caption(f"{g['recheck_days']}일 뒤 다시 검진해 변화를 확인해 보세요.")

    if g["show_contacts"]:
        with st.expander("24시간 상담 연락처", expanded=res.safety_flag):
            contacts_block()

    st.divider()
    st.subheader("상담 대기 현황")
    st.caption("⚠️ 시연용 가상 데이터입니다. 실제 기관의 대기 인원이 아닙니다.")
    pc1, pc2 = st.columns(2)
    pref = pc1.multiselect("선호하는 상담 방식", MODES, default=MODES)
    tol = pc2.select_slider("기다릴 수 있는 기간(일)", options=[3, 7, 14, 30], value=7)

    priority = res.level == RiskLevel.PRIORITY
    table = rank_channels(load_channels(), priority=priority, today=date.today(),
                          preferred_modes=pref or None, max_wait_days=tol)
    show = table.drop(columns=["channel_id", "선호 방식"])
    st.dataframe(show, hide_index=True, use_container_width=True)
    if priority:
        st.caption("3단계는 기관별 긴급 슬롯(우선 트랙)으로 대기를 계산했습니다.")
    if not table["희망 기간 내"].any():
        st.warning("희망 기간 안에 가능한 곳이 없어요. 기다리는 동안 1577-0199(24시간)를 이용할 수 있어요.")

    if g["suggest_booking"] or st.toggle("그래도 상담을 예약하고 싶어요"):
        st.subheader("익명 예약")
        opts = table[table["선호 방식"]] if pref else table
        label = {r["channel_id"]: f"{r['기관']} · {r['방식']} (첫 가능일 {r['첫 상담 가능일']:%m/%d})"
                 for _, r in opts.iterrows()}
        ch = st.selectbox("상담 채널", list(label), format_func=label.get)
        first = opts.loc[opts.channel_id == ch, "첫 상담 가능일"].iloc[0]
        slots = available_slots(ch, first)
        slot = st.selectbox("시간", slots, format_func=lambda s: f"{s:%m/%d(%a) %H:%M}")
        if st.button("이 시간으로 예약", type="primary"):
            try:
                ss.booking = {"code": book(ch, slot, priority), "label": label[ch], "slot": slot}
                go("done")
            except SlotTakenError as e:
                st.error(str(e))

    if st.button("처음부터 다시"):
        ss.clear()
        go("intro")

# ---------------------------------------------------------------------------
# 4. 예약 완료
# ---------------------------------------------------------------------------
elif ss.step == "done":
    b = ss.booking
    st.success("예약되었습니다.")
    st.markdown(f"**{b['label']}**  \n{b['slot']:%Y-%m-%d %H:%M}")
    st.code(b["code"], language=None)
    st.caption("이 코드는 다시 보여드릴 수 없어요. 캡처하거나 메모해 두세요. 조회·취소는 왼쪽 메뉴에서 할 수 있어요.")
    if st.button("처음으로"):
        ss.clear()
        go("intro")
