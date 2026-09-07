#!/usr/bin/env python3
"""Calibrate the score-drift gate in both directions. No network.

    python bench/test_drift.py
"""
import copy, json, subprocess, sys, tempfile
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gate_drift as G

ROOT = HERE.parent


def scores(n, coding=50.0, fetched="2026-09-07"):
    return {"fetched_on": fetched, "source": "x", "matched": [
        {"provider": "p", "model": "m%d" % i, "matched_as": "m%d" % i,
         "artificial_analysis": {"intelligence_index": 40.0, "coding_index": coding, "agentic_index": 30.0}}
        for i in range(n)], "unmatched": []}


def main():
    bad = 0

    def case(label, ok):
        nonlocal bad
        print("  %-4s %s" % ("ok" if ok else "FAIL", label))
        if not ok:
            bad += 1

    print("drift that MUST be refused:")
    prev = scores(20)
    cur = copy.deepcopy(prev)
    for m in cur["matched"][:5]:
        m["artificial_analysis"]["coding_index"] = 70.0
    v, moved = G.compare(prev, cur)
    case("5 of 20 models jump by 20 points (25% moved)", v["refused"] and len(moved) == 5)
    cur = copy.deepcopy(prev); cur["matched"] = cur["matched"][:17]
    v, _ = G.compare(prev, cur)
    case("3 of 20 models vanish (15%)", v["refused"] and len(v["vanished"]) == 3)
    cur = copy.deepcopy(prev); cur["matched"] = cur["matched"][:14]
    v, _ = G.compare(prev, cur)
    case("matched count falls from 20 to 14 (30%)", v["refused"])

    print("\ndrift that MUST pass:")
    cur = copy.deepcopy(prev)
    for m in cur["matched"][:3]:
        m["artificial_analysis"]["coding_index"] = 58.0
    v, moved = G.compare(prev, cur)
    case("3 of 20 move by 8 points (15%)", not v["refused"] and len(moved) == 3)
    cur = copy.deepcopy(prev)
    for m in cur["matched"]:
        m["artificial_analysis"]["coding_index"] = 53.0
    v, moved = G.compare(prev, cur)
    case("every model moves by 3 points (under the threshold)", not v["refused"] and not moved)
    cur = copy.deepcopy(prev); cur["matched"].append(scores(1)["matched"][0] | {"model": "new"})
    v, _ = G.compare(prev, cur)
    case("one model appears", not v["refused"] and v["appeared"] == [["p", "new"]])

    print("\n--apply keeps the previous file when refused, replaces it when not:")
    with tempfile.TemporaryDirectory() as tmp:
        p, c, log = Path(tmp) / "prev.json", Path(tmp) / "cur.json", Path(tmp) / "drift.jsonl"
        p.write_text(json.dumps(scores(20)), encoding="utf-8")
        bad_cur = scores(20, coding=90.0)
        c.write_text(json.dumps(bad_cur), encoding="utf-8")
        r = subprocess.run([sys.executable, str(HERE / "gate_drift.py"), "--previous", str(p), "--current", str(c),
                            "--apply", "--date", "2026-09-08", "--log", str(log)], capture_output=True, text=True)
        kept = json.loads(p.read_text(encoding="utf-8"))["matched"][0]["artificial_analysis"]["coding_index"] == 50.0
        case("refused drift: exit 0, previous file untouched, refusal recorded",
             r.returncode == 0 and kept and "DRIFT REFUSED" in r.stdout and log.exists()
             and json.loads(log.read_text(encoding="utf-8").splitlines()[-1])["refused"] is True)
        c.write_text(json.dumps(scores(20, coding=52.0)), encoding="utf-8")
        r = subprocess.run([sys.executable, str(HERE / "gate_drift.py"), "--previous", str(p), "--current", str(c),
                            "--apply", "--date", "2026-09-08", "--log", str(log)], capture_output=True, text=True)
        applied = json.loads(p.read_text(encoding="utf-8"))["matched"][0]["artificial_analysis"]["coding_index"] == 52.0
        case("small drift: exit 0, previous file replaced, applied recorded",
             r.returncode == 0 and applied and "applied" in r.stdout)

    print("\n--check on committed files:")
    with tempfile.TemporaryDirectory() as tmp:
        f = Path(tmp) / "s.json"
        f.write_text(json.dumps(scores(3, fetched="2026-09-01")), encoding="utf-8")
        case("fresh enough (6 days)", not G.check(f, date(2026, 9, 7), 14))
        case("stale (30 days) is refused", bool(G.check(f, date(2026, 10, 1), 14)))
        d = scores(3); d["matched"][0]["artificial_analysis"]["coding_index"] = "high"
        f.write_text(json.dumps(d), encoding="utf-8")
        case("a score that is a string is refused", bool(G.check(f, date(2026, 9, 7), 14)))
        f.write_text(json.dumps({"fetched_on": "2026-09-07", "matched": []}), encoding="utf-8")
        case("an empty matched list is refused", bool(G.check(f, date(2026, 9, 7), 14)))
    real = ROOT / "data" / "scores.json"
    if real.exists():
        probs = G.check(real, date.fromisoformat(json.loads(real.read_text(encoding="utf-8"))["fetched_on"]), 14)
        case("the committed data/scores.json passes on its own fetch date", not probs)

    print("\n%d failures" % bad)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
