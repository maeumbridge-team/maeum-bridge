// 웹 버전(core.js)이 Python 원본과 같은 결과를 내는지 전수 비교
const MB = require("../core.js");
const v = require(process.argv[2]);
let bad = 0, n = 0;
const d = (s) => { const [y, m, dd] = s.split("-").map(Number); return MB.ymd(y, m, dd); };
for (const [p, g, pt, gt, ps, gs, lv, fl, rs] of v.classify) {
  n++; const r = MB.classify(p, g);
  if (r.phq9_total !== pt || r.gad7_total !== gt || r.phq9_severity !== ps || r.gad7_severity !== gs ||
      r.level !== lv || r.safety_flag !== fl || JSON.stringify(r.reasons) !== JSON.stringify(rs)) { if (bad++ < 3) console.log("classify", p, g, r); }
}
for (const [day, pr, id, days, first, urg] of v.wait) {
  n++; const ch = MB.CHANNELS.find((c) => c.channel_id === id); const w = MB.estimateWait(ch, pr, d(day));
  if (w.wait_business_days !== days || MB.iso(w.first_date) !== first || w.used_urgent_track !== urg) { if (bad++ < 3) console.log("wait", day, pr, id, w); }
}
for (const [day, pr, pref, tol, ids, within] of v.rank) {
  n++; const t = MB.rankChannels(pr, d(day), pref, tol);
  if (JSON.stringify(t.map((x) => x.channel_id)) !== JSON.stringify(ids) || JSON.stringify(t.map((x) => x.within)) !== JSON.stringify(within)) { if (bad++ < 3) console.log("rank", day, pr, pref, tol, t.map((x) => x.channel_id), ids); }
}
// 웹 전용: 슬롯은 평일만, 예약된 슬롯 제외, 코드 형식
const s = MB.slotsFor(MB.ymd(2026, 11, 20), 5, new Set(["2026-11-20T10:00"]));
const okSlots = s.every((k) => { const x = new Date(k.slice(0, 10) + "T00:00:00Z").getUTCDay(); return x > 0 && x < 6; }) && !s.includes("2026-11-20T10:00") && s.length === 29;
const okCode = /^MB-[A-HJ-NP-Z2-9]{4}-[A-HJ-NP-Z2-9]{4}$/.test(MB.newCode((k) => Math.floor(Math.random() * k)));
console.log(`비교 ${n.toLocaleString()}건, 불일치 ${bad}건 · 슬롯 규칙 ${okSlots ? "OK" : "FAIL"} · 코드 형식 ${okCode ? "OK" : "FAIL"}`);
process.exit(bad || !okSlots || !okCode ? 1 : 0);
