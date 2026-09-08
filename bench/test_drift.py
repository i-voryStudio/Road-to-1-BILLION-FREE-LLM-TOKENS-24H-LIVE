#!/usr/bin/env python3
"""Calibrate the score-drift gate in both directions. No network.

    python bench/test_drift.py

Every rule in gate_drift.py has a case here that it must refuse and a neighbour it must admit. The fixture
gives every model its own coding_index, the way a feed does: a fixture where every model scored 50.0 would
itself be the flattened file the gate refuses, and a test that only ever passes such a file is not a test.

The fixture is 55 rows because the poison the second review planted was 12 of 55 (21.8%): that shape is
planted here at every size the contract names, and the honest day beside it (2% moved by a point or two)
must pass. The self-defence scenario is planted whole: a poison written over the committed file by hand,
then the honest fetch, which must be applied because the gate remembers what it applied and this is not it.
"""
import copy, json, subprocess, sys, tempfile
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gate_drift as G

ROOT = HERE.parent
TODAY = date(2026, 9, 7)
N = 55                     # the committed file has 55 matched rows; 12 of them is the 21.8% the review poisoned
POISONED = 12


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


def poison(d):
    """The review's plant: 12 of 55 rows raised by 30 + a little, all distinct, all in range."""
    c = copy.deepcopy(d)
    for i, m in enumerate(c["matched"][:POISONED]):
        m["artificial_analysis"]["coding_index"] += 30 + i * 0.13
    return c


def write(path, d):
    Path(path).write_text(json.dumps(d), encoding="utf-8")


def gate(*args):
    return subprocess.run([sys.executable, str(HERE / "gate_drift.py")] + [str(a) for a in args],
                          capture_output=True, text=True, encoding="utf-8")


def last_row(log):
    return json.loads(Path(log).read_text(encoding="utf-8").splitlines()[-1]) if Path(log).exists() else {}


def main():
    bad = 0

    def case(label, ok, detail=""):
        nonlocal bad
        print("  %-4s %s%s" % ("ok" if ok else "FAIL", label, ("  -> " + detail[:300]) if (detail and not ok) else ""))
        if not ok:
            bad += 1

    def refuses(label, d, must_mention, previous=None):
        with tempfile.TemporaryDirectory() as tmp:
            f = Path(tmp) / "s.json"
            write(f, d)
            probs = G.check(f, TODAY, 14, previous)
        case(label, any(must_mention in p for p in probs), "; ".join(probs) or "no problem raised")

    def admits(label, d, stale_after=14, today=TODAY, previous=None):
        with tempfile.TemporaryDirectory() as tmp:
            f = Path(tmp) / "s.json"
            write(f, d)
            probs = G.check(f, today, stale_after, previous)
        case(label, not probs, "; ".join(probs))

    prev = scores(N)

    print("drift that MUST be refused (compare):")
    v, moved = G.compare(prev, poison(prev))
    case("12 of 55 (21.8%) raised by 30 points, distinct and in range: the review's plant",
         v["refused"] and v["moved"] == POISONED and any("21.8%" in r for r in v["reasons"]), "; ".join(v["reasons"]))
    v, moved = G.compare(prev, shifted(prev, 6.0, first=POISONED))
    case("12 of 55 (21.8%) move by 6 points: the share bound alone", v["refused"] and v["moved"] == POISONED
         and not any("any single" in r for r in v["reasons"]), "; ".join(v["reasons"]))
    v, moved = G.compare(prev, shifted(prev, 6.0, first=3))
    case("3 of 55 (5.5%) move by 6 points: just over the 5% share", v["refused"], "; ".join(v["reasons"]))
    v, moved = G.compare(prev, shifted(prev, 16.0, first=1))
    case("one score moves by 16 points: the single-move bound", v["refused"] and any("any single" in r for r in v["reasons"])
         and v["moved"] == 1, "; ".join(v["reasons"]))
    v, moved = G.compare(prev, shifted(prev, 3.0, first=POISONED))
    case("12 of 55 (21.8%) nudged by 3 points: under 5 points each, refused as a mass nudge",
         v["refused"] and any("mass nudge" in r for r in v["reasons"]) and v["moved"] == 0 and v["nudged"] == POISONED,
         "; ".join(v["reasons"]))
    cur = copy.deepcopy(prev); cur["matched"] = cur["matched"][:48]
    v, _ = G.compare(prev, cur)
    case("7 of 55 models vanish (12.7%)", v["refused"] and len(v["vanished"]) == 7)
    cur = copy.deepcopy(prev); cur["matched"] = cur["matched"][:40]
    v, _ = G.compare(prev, cur)
    case("matched count falls from 55 to 40 (27%)", v["refused"])

    print("\ndrift that MUST pass (compare):")
    honest = copy.deepcopy(prev)                              # a real re-run: two models nudged, nothing else
    honest["matched"][0]["artificial_analysis"]["coding_index"] += 2.0
    honest["matched"][7]["artificial_analysis"]["coding_index"] -= 1.5
    v, moved = G.compare(prev, honest)
    case("a legitimate day: 2 of 55 (3.6%) move by 1.5 and 2 points", not v["refused"] and not moved, "; ".join(v["reasons"]))
    v, moved = G.compare(prev, shifted(prev, 8.0, first=1))
    case("1 of 55 (1.8%) moves by 8 points", not v["refused"] and v["moved"] == 1, "; ".join(v["reasons"]))
    v, moved = G.compare(prev, shifted(prev, 5.0, first=2))
    case("2 of 55 move by exactly 5 points: not more than 5, not a move", not v["refused"] and v["moved"] == 0
         and v["nudged"] == 2, "; ".join(v["reasons"]))
    v, moved = G.compare(prev, shifted(prev, 15.0, first=1))
    case("one score moves by exactly 15 points: not more than 15", not v["refused"], "; ".join(v["reasons"]))
    v, moved = G.compare(prev, shifted(prev, 2.0))
    case("every model moves by exactly 2 points: not more than 2, not even a nudge", not v["refused"] and not moved,
         "; ".join(v["reasons"]))
    v, moved = G.compare(prev, shifted(prev, 3.0, first=11))
    case("11 of 55 (20%) nudged by 3 points: exactly the nudge share, not more", not v["refused"] and v["nudged"] == 11,
         "; ".join(v["reasons"]))
    cur = copy.deepcopy(prev); cur["matched"].append(scores(1, coding=99.0)["matched"][0] | {"model": "new", "matched_as": "org/new"})
    v, _ = G.compare(prev, cur)
    case("one model appears", not v["refused"] and v["appeared"] == [["p", "new"]])
    cur = copy.deepcopy(prev); cur["matched"] = cur["matched"][:50]
    v, _ = G.compare(prev, cur)
    case("5 of 55 vanish (9.1%): under the vanish bound", not v["refused"], "; ".join(v["reasons"]))

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
        write(f, scores(3, fetched="2026-09-01"))
        case("stale (30 days) is refused", bool(G.check(f, date(2026, 10, 1), 14)))

    print("\ndrift since the committed file, on --check:")
    refuses("12 of 55 raised by 30 points since the committed file (the review's plant, on the PR side)",
            poison(prev), "since the committed file", previous=prev)
    refuses("12 of 55 nudged by 3 points since the committed file", shifted(prev, 3.0, first=POISONED),
            "mass nudge", previous=prev)
    refuses("one score 16 points away from the committed file", shifted(prev, 16.0, first=1), "any single score",
            previous=prev)
    noted = poison(prev); noted["note"] = "Artificial Analysis republished the coding index on suite v3"
    refuses("the same plant with a note is refused all the same, and told about --force-note", noted, "--force-note",
            previous=prev)
    admits("a legitimate day since the committed file: 2 of 55 by 1.5 and 2 points", honest, previous=prev)
    admits("the committed file against itself", prev, previous=prev)
    with tempfile.TemporaryDirectory() as tmp:
        f, base = Path(tmp) / "s.json", Path(tmp) / "base.json"
        write(f, poison(prev)); write(base, prev)
        r = gate("--check", f, "--today", "2026-09-07", "--previous", base)
        case("the command line: --check --previous refuses the plant, exit 1", r.returncode == 1 and "since the committed file" in r.stdout, r.stdout)
        write(f, honest)
        r = gate("--check", f, "--today", "2026-09-07", "--previous", base)
        case("the command line: --check --previous admits the honest day, and says what it measured against",
             r.returncode == 0 and "CLEAN" in r.stdout and "within the drift bounds since --previous" in r.stdout, r.stdout)
        r = gate("--check", f, "--today", "2026-09-07")
        case("outside a git repo, with no --previous, --check says out loud that drift was not measured",
             r.returncode == 0 and "no previous version" in r.stdout, r.stdout)
        write(base, scores(N, coding=99.0, spread=0.0))
        write(f, prev)
        r = gate("--check", f, "--today", "2026-09-07", "--previous", base)
        case("a --previous that fails the content checks is not measured against, and the check says so",
             r.returncode == 0 and "fails the content checks itself" in r.stdout, r.stdout)
        # the committed file must not be the refused one, and must be the one the gate applied
        write(f, prev); write(Path(tmp) / G.REJECTED_NAME, prev)
        r = gate("--check", f, "--today", "2026-09-07")
        case("the file under --check holds the same scores as scores.rejected.json: refused",
             r.returncode == 1 and "is a file this gate refused" in r.stdout, r.stdout)
        (Path(tmp) / G.REJECTED_NAME).unlink()
        log = Path(tmp) / G.LOG_NAME
        G.record(log, {"date": "2026-09-06", "applied": True, "sha256": G.content_digest(honest)})
        r = gate("--check", f, "--today", "2026-09-07")
        case("the log says the gate last applied another file: the committed one is a hand edit, refused",
             r.returncode == 1 and "not the file this gate last applied" in r.stdout, r.stdout)
        write(f, honest)
        r = gate("--check", f, "--today", "2026-09-07")
        case("the committed file is the one the gate last applied: admitted, and the digest is named",
             r.returncode == 0 and "the file this gate last applied" in r.stdout, r.stdout)
        # whitespace is not content: the same scores reformatted carry the same digest
        Path(f).write_text(json.dumps(honest, indent=2) + "\r\n", encoding="utf-8")
        r = gate("--check", f, "--today", "2026-09-07")
        case("the same scores re-indented with CRLF still carry the last applied digest", r.returncode == 0, r.stdout)

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

    print("\n--apply refuses out loud, applies within bounds, and remembers what it applied:")
    with tempfile.TemporaryDirectory() as tmp:
        p, c, log, rej = Path(tmp) / "prev.json", Path(tmp) / "cur.json", Path(tmp) / "drift.jsonl", Path(tmp) / G.REJECTED_NAME
        write(p, prev); write(c, poison(prev))
        r = gate("--previous", p, "--current", c, "--apply", "--date", "2026-09-08", "--log", log)
        case("the plant against an honest committed file: exit 1, previous untouched, fetched file kept beside it, refusal recorded",
             r.returncode == 1 and G.same_scores(G.load(p), prev) and "REFUSED" in r.stdout and rej.exists()
             and G.same_scores(G.load(rej), poison(prev)) and last_row(log)["refused"] is True
             and any("21.8%" in x for x in last_row(log)["reasons"]), r.stdout)
        write(c, honest)
        r = gate("--previous", p, "--current", c, "--apply", "--date", "2026-09-08", "--log", log)
        row = last_row(log)
        case("a legitimate day: exit 0, previous replaced, applied and its content digest recorded",
             r.returncode == 0 and G.same_scores(G.load(p), honest) and "applied" in r.stdout
             and row.get("applied") is True and row.get("sha256") == G.content_digest(honest), r.stdout)
        case("the drift record is the default log beside the committed file when --log is not given",
             G.LOG_NAME == "scores-drift.jsonl")
        # --force-note: only a file that carries a note can be forced
        write(c, poison(honest))
        r = gate("--previous", p, "--current", c, "--apply", "--force-note", "--date", "2026-09-09", "--log", log)
        case("--force-note on a file with no note: refused, exit 1, previous untouched",
             r.returncode == 1 and "carries no 'note'" in r.stdout and G.same_scores(G.load(p), honest), r.stdout)
        noted = poison(honest); noted["note"] = "suite v3: the coding index was re-run on every model"
        write(c, noted)
        r = gate("--previous", p, "--current", c, "--apply", "--date", "2026-09-09", "--log", log)
        case("the noted file without --force-note: still refused, exit 1, and the record names the note",
             r.returncode == 1 and any("--force-note" in x for x in last_row(log)["reasons"]) and G.same_scores(G.load(p), honest), r.stdout)
        r = gate("--previous", p, "--current", c, "--apply", "--force-note", "--date", "2026-09-09", "--log", log)
        row = last_row(log)
        case("the noted file with --force-note: applied, exit 0, forced and the note recorded with the digest",
             r.returncode == 0 and G.same_scores(G.load(p), noted) and row.get("forced") is True
             and row.get("note") == noted["note"] and row.get("sha256") == G.content_digest(noted), r.stdout)

    print("\nthe previous file can never be the one that was refused:")
    with tempfile.TemporaryDirectory() as tmp:
        p, c, log, rej = Path(tmp) / "prev.json", Path(tmp) / "cur.json", Path(tmp) / "drift.jsonl", Path(tmp) / G.REJECTED_NAME
        write(p, prev); write(c, poison(prev))
        gate("--previous", p, "--current", c, "--apply", "--date", "2026-09-08", "--log", log)
        assert rej.exists(), "the refusal above should have written %s" % rej
        write(p, poison(prev))                                   # the refused file copied over the committed one by hand
        write(c, honest)                                         # and an honest fetch the next day
        r = gate("--previous", p, "--current", c, "--apply", "--date", "2026-09-09", "--log", log)
        case("scores.rejected.json equals the previous file: the gate refuses to run, exit 1, nothing applied",
             r.returncode == 1 and "REFUSING TO RUN" in r.stdout and G.same_scores(G.load(p), poison(prev)), r.stdout)
        Path(p).write_text(json.dumps(poison(prev), indent=1), encoding="utf-8")
        r = gate("--previous", p, "--current", c, "--apply", "--date", "2026-09-09", "--log", log)
        case("the same refused scores re-indented are still the refused file", r.returncode == 1 and "REFUSING TO RUN" in r.stdout, r.stdout)
        rej.unlink()
        r = gate("--previous", p, "--current", c, "--apply", "--date", "2026-09-09", "--log", log)
        case("with scores.rejected.json reviewed and removed, the gate runs again", "REFUSING TO RUN" not in r.stdout, r.stdout)

    print("\nself-defence: a poisoned committed file is not defended against the honest feed:")
    with tempfile.TemporaryDirectory() as tmp:
        p, c, log, rej = Path(tmp) / "prev.json", Path(tmp) / "cur.json", Path(tmp) / "drift.jsonl", Path(tmp) / G.REJECTED_NAME
        # day 1: the gate applies an honest file and remembers it
        write(p, prev); write(c, honest)
        r = gate("--previous", p, "--current", c, "--apply", "--date", "2026-09-08", "--log", log)
        assert r.returncode == 0, r.stdout
        # day 2: someone writes the review's plant over the committed file by hand (distinct, in range: passes --check)
        write(p, poison(honest))
        assert not G.check(p, TODAY, None), "the plant must pass the content checks, or this case tests nothing"
        # day 3: the honest feed, 21.8% away from the poison
        write(c, honest)
        r = gate("--previous", p, "--current", c, "--apply", "--date", "2026-09-09", "--log", log)
        row = last_row(log)
        case("poison applied by hand, honest fetch: the fetch is applied, the previous file is named as not the gate's, exit 0",
             r.returncode == 0 and G.same_scores(G.load(p), honest) and "not the file this gate last applied" in r.stdout
             and row.get("applied") is True and row.get("previous_unattested", {}).get("found") == G.content_digest(poison(honest))
             and row.get("sha256") == G.content_digest(honest) and not rej.exists(), r.stdout)
        # and once the gate has applied the honest file, the same poison arriving as a FETCH is refused
        write(c, poison(honest))
        r = gate("--previous", p, "--current", c, "--apply", "--date", "2026-09-10", "--log", log)
        case("the same poison arriving as a fetch, against the file the gate applied: refused, exit 1",
             r.returncode == 1 and "REFUSED" in r.stdout and G.same_scores(G.load(p), honest), r.stdout)
        rej.unlink()
        # the forged-ledger case: the poison carries the log's digest, so it is defended - and the failure is loud
        write(p, poison(honest))
        G.record(log, {"date": "2026-09-10", "applied": True, "sha256": G.content_digest(poison(honest))})
        write(c, honest)
        r = gate("--previous", p, "--current", c, "--apply", "--date", "2026-09-11", "--log", log)
        case("poison with a forged log row: the honest fetch is refused, exit 1, and the message says how a human recovers",
             r.returncode == 1 and "REFUSED" in r.stdout and rej.exists() and "git history" in r.stdout
             and G.same_scores(G.load(p), poison(honest)), r.stdout)
        # a log that predates the gate's memory: no digest, the bounds apply, and a refusal is still exit 1
        rej.unlink(); log.unlink()
        G.record(log, {"date": "2026-09-01", "applied": True})
        write(p, prev); write(c, poison(prev))
        r = gate("--previous", p, "--current", c, "--apply", "--date", "2026-09-12", "--log", log)
        case("a log without digests: the bounds decide, and a refusal is exit 1 with the file kept beside",
             r.returncode == 1 and rej.exists() and G.same_scores(G.load(p), prev), r.stdout)

    print("\n--apply never keeps a previous file that fails --check, never applies a fresh one that does:")
    with tempfile.TemporaryDirectory() as tmp:
        p, c, log, rej = Path(tmp) / "prev.json", Path(tmp) / "cur.json", Path(tmp) / "drift.jsonl", Path(tmp) / G.REJECTED_NAME
        poisoned = scores(20, coding=99.0, spread=0.0)          # every row hand-set to 99.0
        poisoned["fetched_on"] = "2027-01-01"
        write(p, poisoned); write(c, scores(20))                  # the honest feed, 49 points away
        r = gate("--previous", p, "--current", c, "--apply", "--date", "2026-09-08", "--log", log)
        now = G.load(p)
        row = last_row(log)
        case("poisoned previous + honest fetch: the fetch is applied although it 'drifts', reason and digest recorded",
             r.returncode == 0 and now["fetched_on"] == "2026-09-07"
             and now["matched"][0]["artificial_analysis"]["coding_index"] == 50.0
             and "fails --check" in r.stdout and row.get("applied") is True and row.get("previous_invalid")
             and row.get("sha256") == G.content_digest(scores(20)), r.stdout)
        # honest previous, fresh file with a future date: kept, refused, exit 1, the fresh file kept beside
        write(p, scores(20)); write(c, scores(20, fetched="2027-01-01"))
        r = gate("--previous", p, "--current", c, "--apply", "--date", "2026-09-08", "--log", log)
        row = last_row(log)
        case("honest previous + fresh file dated in the future: kept, exit 1, refusal recorded, fresh file beside",
             r.returncode == 1 and G.load(p)["fetched_on"] == "2026-09-07"
             and "REFUSED" in r.stdout and row["refused"] is True and rej.exists()
             and any("after today" in x for x in row["reasons"]), r.stdout)
        rej.unlink()
        # both unsound: nothing to stand on
        write(p, poisoned); write(c, scores(20, fetched="2027-01-01"))
        r = gate("--previous", p, "--current", c, "--apply", "--date", "2026-09-08", "--log", log)
        case("both files fail --check: exit 1, nothing applied",
             r.returncode == 1 and "NEITHER FILE IS SOUND" in r.stdout
             and G.load(p)["fetched_on"] == "2027-01-01", r.stdout)
        # a previous file that is merely older than 14 days is not 'unsound': drift bounds still apply. A fresh
        # log: the one above already remembers another file, and a previous the gate never applied is not defended.
        stale = scores(20, fetched="2026-08-01")
        write(p, stale); write(c, scores(20, coding=80.0, fetched="2026-09-08"))
        log2 = Path(tmp) / "drift2.jsonl"
        G.record(log2, {"date": "2026-08-01", "applied": True, "sha256": G.content_digest(stale)})
        r = gate("--previous", p, "--current", c, "--apply", "--date", "2026-09-08", "--log", log2)
        case("a stale but sound previous file the gate applied is still defended against a 30-point re-rank, exit 1",
             r.returncode == 1 and "REFUSED" in r.stdout
             and G.load(p)["fetched_on"] == "2026-08-01", r.stdout)

    print("\n--check on the committed file:")
    real = ROOT / "data" / "scores.json"
    if real.exists():
        fetched = date.fromisoformat(G.load(real)["fetched_on"])
        probs = G.check(real, fetched, 14)
        case("the committed data/scores.json passes on its own fetch date", not probs, "; ".join(probs))
        r = gate("--check", real, "--today", fetched.isoformat())
        case("and the command line agrees, exit 0 with CLEAN", r.returncode == 0 and "CLEAN" in r.stdout, r.stdout)
        case("the committed file is not the one in %s" % G.REJECTED_NAME, G.rejected_twin(real) is None)

    print("\n%d failures" % bad)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
