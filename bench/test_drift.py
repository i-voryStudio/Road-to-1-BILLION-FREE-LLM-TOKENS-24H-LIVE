#!/usr/bin/env python3
"""Calibrate the score-drift gate in both directions. No network.

    python bench/test_drift.py

Every rule in gate_drift.py has a case here that it must refuse and a neighbour it must admit. The fixture
gives every model its own coding_index, the way a feed does: a fixture where every model scored 50.0 would
itself be the flattened file the gate refuses, and a test that only ever passes such a file is not a test.
"""
import copy, json, subprocess, sys, tempfile
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gate_drift as G

ROOT = HERE.parent
TODAY = date(2026, 9, 7)


def scores(n, coding=50.0, fetched="2026-09-07", spread=0.5):
    """n matched rows, distinct models, coding_index = coding + i * spread so no two models share a score."""
    return {"fetched_on": fetched, "source": "x", "matched": [
        {"provider": "p", "model": "m%d" % i, "matched_as": "org/m%d" % i,
         "artificial_analysis": {"intelligence_index": 40.0, "coding_index": coding + i * spread, "agentic_index": 30.0},
         "design_arena": {"website": {"elo": 1200 + i, "win_rate": 50.0, "rank": i + 1}}}
        for i in range(n)], "unmatched": []}


def shifted(d, by, first=None):
    """A deep copy where the first `first` models (all, if None) move their coding_index by `by`."""
    c = copy.deepcopy(d)
    for m in c["matched"][:first]:
        m["artificial_analysis"]["coding_index"] += by
    return c


def gate(*args):
    return subprocess.run([sys.executable, str(HERE / "gate_drift.py")] + [str(a) for a in args],
                          capture_output=True, text=True)


def main():
    bad = 0

    def case(label, ok, detail=""):
        nonlocal bad
        print("  %-4s %s%s" % ("ok" if ok else "FAIL", label, ("  -> " + detail[:200]) if (detail and not ok) else ""))
        if not ok:
            bad += 1

    def refuses(label, d, must_mention):
        with tempfile.TemporaryDirectory() as tmp:
            f = Path(tmp) / "s.json"
            f.write_text(json.dumps(d), encoding="utf-8")
            probs = G.check(f, TODAY, 14)
        case(label, any(must_mention in p for p in probs), "; ".join(probs) or "no problem raised")

    def admits(label, d, stale_after=14, today=TODAY):
        with tempfile.TemporaryDirectory() as tmp:
            f = Path(tmp) / "s.json"
            f.write_text(json.dumps(d), encoding="utf-8")
            probs = G.check(f, today, stale_after)
        case(label, not probs, "; ".join(probs))

    print("drift that MUST be refused (compare):")
    prev = scores(20)
    v, moved = G.compare(prev, shifted(prev, 20.0, first=5))
    case("5 of 20 models jump by 20 points (25% moved)", v["refused"] and len(moved) == 5)
    cur = copy.deepcopy(prev); cur["matched"] = cur["matched"][:17]
    v, _ = G.compare(prev, cur)
    case("3 of 20 models vanish (15%)", v["refused"] and len(v["vanished"]) == 3)
    cur = copy.deepcopy(prev); cur["matched"] = cur["matched"][:14]
    v, _ = G.compare(prev, cur)
    case("matched count falls from 20 to 14 (30%)", v["refused"])

    print("\ndrift that MUST pass (compare):")
    v, moved = G.compare(prev, shifted(prev, 8.0, first=3))
    case("3 of 20 move by 8 points (15%)", not v["refused"] and len(moved) == 3)
    v, moved = G.compare(prev, shifted(prev, 3.0))
    case("every model moves by 3 points (under the threshold)", not v["refused"] and not moved)
    cur = copy.deepcopy(prev); cur["matched"].append(scores(1, coding=77.0)["matched"][0] | {"model": "new", "matched_as": "org/new"})
    v, _ = G.compare(prev, cur)
    case("one model appears", not v["refused"] and v["appeared"] == [["p", "new"]])

    print("\ncontent that --check MUST refuse:")
    refuses("fetched_on in the future", scores(3, fetched="2026-09-08"), "after today")
    d = scores(3); d["matched"][0]["artificial_analysis"]["coding_index"] = 101.0
    refuses("a coding_index above 100", d, "outside [0, 100]")
    d = scores(3); d["matched"][1]["artificial_analysis"]["intelligence_index"] = -1
    refuses("an intelligence_index below 0", d, "outside [0, 100]")
    d = scores(3); d["matched"][2]["artificial_analysis"]["agentic_index"] = 100.5
    refuses("an agentic_index just over 100", d, "outside [0, 100]")
    d = scores(3); d["matched"][0]["design_arena"]["website"]["elo"] = 6000
    refuses("an ELO above 5000", d, "elo is 6000")
    d = scores(3); d["matched"][0]["design_arena"]["website"]["elo"] = -5
    refuses("an ELO below 0", d, "elo is -5")
    d = scores(3); d["matched"][0]["design_arena"]["website"]["win_rate"] = 140
    refuses("a win rate above 100", d, "win_rate is 140")
    d = scores(3); d["matched"][0]["matched_as"] = "not a model id!!"
    refuses("a matched_as with spaces and punctuation", d, "shape of a model id")
    d = scores(3); d["matched"][0]["matched_as"] = "/leading-slash"
    refuses("a matched_as starting with a slash", d, "shape of a model id")
    d = scores(3); d["matched"][0]["matched_as"] = ""
    refuses("an empty matched_as", d, "no matched_as")
    d = scores(20)
    for m in d["matched"][:3]:
        m["artificial_analysis"]["coding_index"] = 61.0
    refuses("3 distinct models of 20 (15%) at one identical coding_index", d, "share the identical coding_index 61.0")
    d = scores(55, spread=0.0, coding=99.0)
    refuses("every row hand-set to 99.0 (the poisoned file the skeptic planted)", d, "share the identical coding_index 99.0")
    d = scores(3); d["matched"][0]["artificial_analysis"]["coding_index"] = "high"
    refuses("a score that is a string", d, "not a number")
    d = scores(3); d["matched"][0]["artificial_analysis"]["coding_index"] = True
    refuses("a score that is a boolean", d, "not a number")
    refuses("an empty matched list", {"fetched_on": "2026-09-07", "matched": []}, "no matched models")
    refuses("fetched_on that is not a date", scores(3, fetched="yesterday"), "not a date")
    with tempfile.TemporaryDirectory() as tmp:
        f = Path(tmp) / "s.json"
        f.write_text(json.dumps(scores(3, fetched="2026-09-01")), encoding="utf-8")
        case("stale (30 days) is refused", bool(G.check(f, date(2026, 10, 1), 14)))

    print("\ncontent that --check MUST admit:")
    admits("distinct scores, fetched today", scores(20))
    admits("fetched six days ago", scores(3, fetched="2026-09-01"))
    d = scores(20)
    for m in d["matched"][:2]:
        m["artificial_analysis"]["coding_index"] = 61.0
    admits("2 distinct models of 20 (exactly 10%) at one coding_index", d)
    d = scores(20)
    for m in d["matched"][:6]:
        m["matched_as"] = "org/same-model"
        m["artificial_analysis"]["coding_index"] = 61.0
    admits("one model served by 6 providers shares one score: that is a feed", d)
    d = scores(20)
    for k, m in enumerate(d["matched"][:6]):
        m["matched_as"] = "org/same-model" + (":free", ":nitro", ":batch", "", ":free", ":batch")[k]
        m["artificial_analysis"]["coding_index"] = 61.0
    admits("variants of one model (:free, :batch) share one score", d)
    d = scores(3); d["matched"][0]["artificial_analysis"]["coding_index"] = None
    admits("a null index is unscored, not out of range", d)
    d = scores(3); d["matched"][0]["design_arena"] = {}
    admits("no arena block at all", d)
    d = scores(3); d["matched"][0]["artificial_analysis"]["coding_index"] = 0.0
    admits("an index of exactly 0", d)
    d = scores(3); d["matched"][0]["artificial_analysis"]["coding_index"] = 100.0
    admits("an index of exactly 100", d)

    print("\n--apply keeps the previous file when refused, replaces it when not:")
    with tempfile.TemporaryDirectory() as tmp:
        p, c, log = Path(tmp) / "prev.json", Path(tmp) / "cur.json", Path(tmp) / "drift.jsonl"
        p.write_text(json.dumps(scores(20)), encoding="utf-8")
        c.write_text(json.dumps(scores(20, coding=80.0)), encoding="utf-8")
        r = gate("--previous", p, "--current", c, "--apply", "--date", "2026-09-08", "--log", log)
        kept = json.loads(p.read_text(encoding="utf-8"))["matched"][0]["artificial_analysis"]["coding_index"] == 50.0
        case("refused drift: exit 0, previous file untouched, refusal recorded",
             r.returncode == 0 and kept and "DRIFT REFUSED" in r.stdout and log.exists()
             and json.loads(log.read_text(encoding="utf-8").splitlines()[-1])["refused"] is True, r.stdout)
        c.write_text(json.dumps(scores(20, coding=52.0)), encoding="utf-8")
        r = gate("--previous", p, "--current", c, "--apply", "--date", "2026-09-08", "--log", log)
        applied = json.loads(p.read_text(encoding="utf-8"))["matched"][0]["artificial_analysis"]["coding_index"] == 52.0
        case("small drift: exit 0, previous file replaced, applied recorded",
             r.returncode == 0 and applied and "applied" in r.stdout, r.stdout)

    print("\n--apply never keeps a previous file that fails --check:")
    with tempfile.TemporaryDirectory() as tmp:
        p, c, log = Path(tmp) / "prev.json", Path(tmp) / "cur.json", Path(tmp) / "drift.jsonl"
        poisoned = scores(20, coding=99.0, spread=0.0)          # every row hand-set to 99.0
        poisoned["fetched_on"] = "2027-01-01"
        p.write_text(json.dumps(poisoned), encoding="utf-8")
        c.write_text(json.dumps(scores(20)), encoding="utf-8")   # the honest feed, 49 points away
        r = gate("--previous", p, "--current", c, "--apply", "--date", "2026-09-08", "--log", log)
        now = json.loads(p.read_text(encoding="utf-8"))
        row = json.loads(log.read_text(encoding="utf-8").splitlines()[-1]) if log.exists() else {}
        case("poisoned previous + honest fetch: the fetch is applied although it 'drifts', reason recorded",
             r.returncode == 0 and now["fetched_on"] == "2026-09-07"
             and now["matched"][0]["artificial_analysis"]["coding_index"] == 50.0
             and "fails --check" in r.stdout and row.get("applied") is True and row.get("previous_invalid"), r.stdout)
        # honest previous, fresh file with a future date: kept, refused, exit 0 so the daily job runs on
        p.write_text(json.dumps(scores(20)), encoding="utf-8")
        c.write_text(json.dumps(scores(20, fetched="2027-01-01")), encoding="utf-8")
        r = gate("--previous", p, "--current", c, "--apply", "--date", "2026-09-08", "--log", log)
        row = json.loads(log.read_text(encoding="utf-8").splitlines()[-1])
        case("honest previous + fresh file dated in the future: kept, exit 0, refusal recorded",
             r.returncode == 0 and json.loads(p.read_text(encoding="utf-8"))["fetched_on"] == "2026-09-07"
             and "FRESH FILE REFUSED" in r.stdout and row["refused"] is True
             and any("after today" in x for x in row["reasons"]), r.stdout)
        # both unsound: nothing to stand on
        p.write_text(json.dumps(poisoned), encoding="utf-8")
        c.write_text(json.dumps(scores(20, fetched="2027-01-01")), encoding="utf-8")
        r = gate("--previous", p, "--current", c, "--apply", "--date", "2026-09-08", "--log", log)
        case("both files fail --check: exit 1, nothing applied",
             r.returncode == 1 and "NEITHER FILE IS SOUND" in r.stdout
             and json.loads(p.read_text(encoding="utf-8"))["fetched_on"] == "2027-01-01", r.stdout)
        # a previous file that is merely older than 14 days is not 'unsound': drift bounds still apply
        p.write_text(json.dumps(scores(20, fetched="2026-08-01")), encoding="utf-8")
        c.write_text(json.dumps(scores(20, coding=80.0, fetched="2026-09-08")), encoding="utf-8")
        r = gate("--previous", p, "--current", c, "--apply", "--date", "2026-09-08", "--log", log)
        case("a stale but sound previous file is still defended against a 30-point re-rank",
             r.returncode == 0 and "DRIFT REFUSED" in r.stdout
             and json.loads(p.read_text(encoding="utf-8"))["fetched_on"] == "2026-08-01", r.stdout)

    print("\n--check on the committed file:")
    real = ROOT / "data" / "scores.json"
    if real.exists():
        fetched = date.fromisoformat(json.loads(real.read_text(encoding="utf-8"))["fetched_on"])
        probs = G.check(real, fetched, 14)
        case("the committed data/scores.json passes on its own fetch date", not probs, "; ".join(probs))
        r = gate("--check", real, "--today", fetched.isoformat())
        case("and the command line agrees, exit 0 with CLEAN", r.returncode == 0 and "CLEAN" in r.stdout, r.stdout)

    print("\n%d failures" % bad)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
