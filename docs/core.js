/* 마음다리 핵심 로직 (Python core/screening.py · guidance.py · booking.py 와 동일한 규칙)
 * 브라우저와 Node 양쪽에서 실행된다. Node에서는 Python 결과와 전수 비교 검증에 쓴다.
 * 교육용 프로토타입이며 의학적 진단 도구가 아니다. */
(function (root) {
  "use strict";

  const PHQ9_ITEMS = [
    "일 또는 여가 활동을 하는 데 흥미나 즐거움을 느끼지 못함",
    "기분이 가라앉거나, 우울하거나, 희망이 없음",
    "잠이 들거나 계속 잠을 자는 것이 어려움, 또는 잠을 너무 많이 잠",
    "피곤하다고 느끼거나 기운이 거의 없음",
    "입맛이 없거나 과식을 함",
    "자신을 부정적으로 봄 — 혹은 자신이 실패자라고 느끼거나 자신 또는 가족을 실망시킴",
    "신문을 읽거나 텔레비전 보는 것과 같은 일에 집중하는 것이 어려움",
    "다른 사람들이 알아챌 정도로 너무 느리게 움직이거나 말을 함, 또는 반대로 평상시보다 많이 움직여서 너무 안절부절못하거나 들떠 있음",
    "자신이 죽는 것이 더 낫다고 생각하거나, 어떤 식으로든 자신을 해칠 것이라고 생각함",
  ];
  const GAD7_ITEMS = [
    "초조하거나 불안하거나 조마조마하게 느낀다",
    "걱정하는 것을 멈추거나 조절할 수가 없다",
    "여러 가지 것들에 대해 걱정을 너무 많이 한다",
    "편하게 있기가 어렵다",
    "너무 안절부절못해서 가만히 있기가 힘들다",
    "쉽게 짜증이 나거나 쉽게 성을 낸다",
    "마치 끔찍한 일이 생길 것처럼 두렵게 느껴진다",
  ];
  const STEM = "지난 2주 동안, 다음과 같은 문제들로 인해 얼마나 자주 방해를 받았습니까?";
  const RESPONSE_OPTIONS = ["전혀 방해받지 않았다", "며칠 동안 방해받았다", "7일 이상 방해받았다", "거의 매일 방해받았다"];
  const SUICIDE_ITEM_INDEX = 8;
  const CUTOFFS = { phq_moderate: 10, phq_high: 15, gad_moderate: 10, gad_high: 15 };
  const PHQ9_SEVERITY = [[0, 4, "최소"], [5, 9, "경도"], [10, 14, "중등도"], [15, 19, "중등도-중증"], [20, 27, "중증"]];
  const GAD7_SEVERITY = [[0, 4, "최소"], [5, 9, "경도"], [10, 14, "중등도"], [15, 21, "중증"]];
  const LEVEL_LABEL = { 1: "1단계 · 자가관리", 2: "2단계 · 상담 권고", 3: "3단계 · 우선 연계" };

  function validate(r, n, name) {
    if (!Array.isArray(r) || r.length !== n) throw new Error(`${name}은(는) ${n}개 문항에 모두 응답해야 합니다.`);
    r.forEach((v, i) => {
      if (![0, 1, 2, 3].includes(v)) throw new Error(`${name} ${i + 1}번 응답은 0~3 사이 정수여야 합니다.`);
    });
  }
  const sum = (a) => a.reduce((x, y) => x + y, 0);
  function severity(total, table) {
    for (const [lo, hi, name] of table) if (lo <= total && total <= hi) return name;
    throw new Error("점수 범위를 벗어났습니다: " + total);
  }

  function classify(phq9, gad7) {
    validate(phq9, 9, "PHQ-9");
    validate(gad7, 7, "GAD-7");
    const p = sum(phq9), g = sum(gad7), c = CUTOFFS, reasons = [];
    const safety = phq9[SUICIDE_ITEM_INDEX] >= 1;
    if (safety) reasons.push("PHQ-9 9번 문항(자해·죽음에 대한 생각)에 응답함 → 총점과 관계없이 우선 안내");
    if (p >= c.phq_high) reasons.push(`PHQ-9 ${p}점 (≥${c.phq_high})`);
    if (g >= c.gad_high) reasons.push(`GAD-7 ${g}점 (≥${c.gad_high})`);
    let level;
    if (safety || p >= c.phq_high || g >= c.gad_high) level = 3;
    else if (p >= c.phq_moderate || g >= c.gad_moderate) {
      level = 2;
      if (p >= c.phq_moderate) reasons.push(`PHQ-9 ${p}점 (≥${c.phq_moderate})`);
      if (g >= c.gad_moderate) reasons.push(`GAD-7 ${g}점 (≥${c.gad_moderate})`);
    } else {
      level = 1;
      reasons.push(`PHQ-9 ${p}점, GAD-7 ${g}점 (모두 <10)`);
    }
    return {
      phq9_total: p, gad7_total: g,
      phq9_severity: severity(p, PHQ9_SEVERITY), gad7_severity: severity(g, GAD7_SEVERITY),
      level, label: LEVEL_LABEL[level], safety_flag: safety, reasons,
    };
  }

  const CRISIS_CONTACTS = [
    { name: "자살예방상담전화", number: "109", tel: "109", note: "24시간 · 국번 없이 109" },
    { name: "정신건강위기상담전화", number: "1577-0199", tel: "15770199", note: "24시간 · 지역 정신건강복지센터 연결" },
    { name: "청소년전화", number: "1388", tel: "1388", note: "24시간 · 만 24세 이하" },
    { name: "응급 상황", number: "119 / 112", tel: "119", note: "지금 당장 위험할 때" },
  ];
  const GUIDANCE = {
    1: { headline: "지금은 스스로 돌보며 지켜봐도 괜찮은 상태로 보여요.",
         actions: ["수면 시간을 일정하게 유지하고, 하루 20~30분 가볍게 걸어 보세요.", "힘든 일을 믿을 만한 사람 한 명에게 이야기해 보세요.", "2주 뒤 다시 검진해 변화를 확인해 보세요.", "상담이 필요하다고 느끼면 점수와 상관없이 언제든 예약할 수 있어요."],
         recheck_days: 14, suggest_booking: false },
    2: { headline: "전문 상담사와 이야기해 보는 것을 권해요.",
         actions: ["교내 상담센터나 지역 기관 상담을 1~2주 안에 받아 보세요.", "대면이 부담되면 채팅·화상 상담부터 시작해도 괜찮아요.", "증상이 2주 이상 계속되거나 심해지면 정신건강의학과 진료도 고려하세요."],
         recheck_days: 14, suggest_booking: true },
    3: { headline: "가능한 한 빨리 전문가와 연결되는 것이 좋겠어요.",
         actions: ["가장 빨리 가능한 상담 일정을 아래에서 확인하세요.", "기다리는 동안 힘들어지면 109 또는 1577-0199로 바로 전화하세요(24시간).", "정신건강의학과 진료를 받아 보는 것을 권해요."],
         recheck_days: 7, suggest_booking: true },
  };
  const DISCLAIMER = "이 결과는 PHQ-9·GAD-7 자가 선별 점수에 따른 안내이며 의학적 진단이 아닙니다. 교육용 프로토타입으로, 실제 진단·치료를 대신하지 않습니다.";
  function guidanceFor(res) {
    const g = Object.assign({}, GUIDANCE[res.level]);
    g.show_crisis_banner = res.safety_flag;
    g.show_contacts = res.level >= 2 || res.safety_flag;
    return g;
  }

  /* ---- 대기 추정 (가상 데이터) ---- */
  const CHANNELS = [
    { channel_id: "campus_f2f", org: "교내 학생상담센터(예시)", mode: "대면", counselors: 4, sessions_per_counselor_per_day: 5, waiting_now: 150, urgent_slots_per_day: 2, urgent_waiting: 1, location: "학생회관 3층" },
    { channel_id: "campus_chat", org: "교내 학생상담센터(예시)", mode: "채팅", counselors: 2, sessions_per_counselor_per_day: 6, waiting_now: 9, urgent_slots_per_day: 1, urgent_waiting: 0, location: "앱 내 채팅" },
    { channel_id: "campus_video", org: "교내 학생상담센터(예시)", mode: "화상", counselors: 2, sessions_per_counselor_per_day: 5, waiting_now: 14, urgent_slots_per_day: 1, urgent_waiting: 0, location: "앱 내 화상" },
    { channel_id: "community_f2f", org: "지역 정신건강복지센터(예시)", mode: "대면", counselors: 3, sessions_per_counselor_per_day: 4, waiting_now: 20, urgent_slots_per_day: 2, urgent_waiting: 0, location: "구청 별관 2층" },
    { channel_id: "community_phone", org: "지역 정신건강복지센터(예시)", mode: "전화", counselors: 2, sessions_per_counselor_per_day: 8, waiting_now: 6, urgent_slots_per_day: 2, urgent_waiting: 0, location: "전화 연결" },
  ];
  const MODES = ["대면", "채팅", "화상", "전화"];

  // 날짜는 시간대 문제를 피하려고 UTC 자정 기준 Date로만 다룬다.
  const ymd = (y, m, d) => new Date(Date.UTC(y, m - 1, d));
  const iso = (dt) => dt.toISOString().slice(0, 10);
  const isWeekend = (dt) => { const w = dt.getUTCDay(); return w === 0 || w === 6; };
  const addDays = (dt, n) => new Date(dt.getTime() + n * 86400000);
  function addBusinessDays(start, n) {
    let d = start;
    if (n === 0) { while (isWeekend(d)) d = addDays(d, 1); return d; }
    let added = 0;
    while (added < n) { d = addDays(d, 1); if (!isWeekend(d)) added++; }
    return d;
  }
  function estimateWait(ch, priority, today) {
    const total = ch.counselors * ch.sessions_per_counselor_per_day;
    const urgent = ch.urgent_slots_per_day;
    const regular = Math.max(total - urgent, 1);
    let ahead, days, usedUrgent;
    if (priority && urgent > 0) { ahead = ch.urgent_waiting; days = Math.ceil((ahead + 1) / urgent); usedUrgent = true; }
    else { ahead = ch.waiting_now; days = Math.ceil((ahead + 1) / regular); usedUrgent = false; }
    return { channel_id: ch.channel_id, org: ch.org, mode: ch.mode, location: ch.location,
             waiting_ahead: ahead, wait_business_days: days, first_date: addBusinessDays(today, days), used_urgent_track: usedUrgent };
  }
  function rankChannels(priority, today, preferred, maxWaitDays) {
    const rows = CHANNELS.map((c) => {
      const w = estimateWait(c, priority, today);
      w.preferred = !preferred || preferred.length === 0 || preferred.includes(w.mode);
      w.within = maxWaitDays == null ? true : Math.round((w.first_date - today) / 86400000) <= maxWaitDays;
      return w;
    });
    // 선호 방식 먼저, 그다음 대기일 오름차순 (안정 정렬)
    return rows.map((r, i) => [r, i]).sort((a, b) =>
      (b[0].preferred - a[0].preferred) || (a[0].wait_business_days - b[0].wait_business_days) || (a[1] - b[1])
    ).map((x) => x[0]);
  }
  const SLOT_HOURS = [10, 11, 13, 14, 15, 16];
  function slotsFor(firstDate, nDays, taken) {
    const out = [], base = addBusinessDays(firstDate, 0);
    for (let i = 0; i < nDays; i++) {
      const d = addBusinessDays(base, i);
      for (const h of SLOT_HOURS) {
        const key = `${iso(d)}T${String(h).padStart(2, "0")}:00`;
        if (!taken.has(key)) out.push(key);
      }
    }
    return out;
  }
  const CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789";
  function newCode(rand) {
    let s = "";
    for (let i = 0; i < 8; i++) s += CODE_ALPHABET[rand(CODE_ALPHABET.length)];
    return `MB-${s.slice(0, 4)}-${s.slice(4)}`;
  }

  const api = { PHQ9_ITEMS, GAD7_ITEMS, STEM, RESPONSE_OPTIONS, CUTOFFS, classify, guidanceFor, CRISIS_CONTACTS,
    DISCLAIMER, CHANNELS, MODES, ymd, iso, addBusinessDays, estimateWait, rankChannels, slotsFor, newCode };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.MB = api;
})(typeof window !== "undefined" ? window : globalThis);
