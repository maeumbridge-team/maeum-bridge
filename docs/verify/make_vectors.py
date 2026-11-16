"""Python 원본 로직으로 기대값을 만든다 (웹 버전과 비교용)."""
import itertools, json, random, sys
from datetime import date, timedelta
sys.path.insert(0, sys.argv[1])
from core.screening import classify
from core.booking import load_channels, estimate_wait, rank_channels
rng = random.Random(42)
cases = [(list(p), [0]*7) for p in itertools.product(range(4), repeat=9)]
cases += [([rng.randint(0,3) for _ in range(9)], [rng.randint(0,3) for _ in range(7)]) for _ in range(20000)]
cases += [([0]*9, list(g)) for g in itertools.product(range(4), repeat=7)]
out = {"classify": [], "wait": [], "rank": []}
for p, g in cases:
    r = classify(p, g)
    out["classify"].append([p, g, r.phq9_total, r.gad7_total, r.phq9_severity, r.gad7_severity, int(r.level), r.safety_flag, r.reasons])
df = load_channels()
for k in range(60):
    d = date(2026, 11, 1) + timedelta(days=k)
    for pr in (False, True):
        for _, row in df.iterrows():
            w = estimate_wait(row, pr, d)
            out["wait"].append([d.isoformat(), pr, row.channel_id, w.wait_business_days, w.first_date.isoformat(), w.used_urgent_track])
        for pref in (None, ["채팅"], ["대면", "전화"]):
            for tol in (3, 7, 14):
                t = rank_channels(df, pr, d, pref, tol)
                out["rank"].append([d.isoformat(), pr, pref, tol, t["channel_id"].tolist(), t["희망 기간 내"].tolist()])
json.dump(out, open(sys.argv[2], "w"), ensure_ascii=False)
print({k: len(v) for k, v in out.items()})
