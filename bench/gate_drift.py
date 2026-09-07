#!/usr/bin/env python3
"""Refuse to let a third-party score feed silently re-rank this list.

    python bench/gate_drift.py --previous data/scores.json --current /tmp/scores-new.json --date 2026-09-08 --apply
    python bench/gate_drift.py --check data/scores.json --today 2026-09-08

Half of every Value on the front page is a quality score we import from a public feed, and until now the
daily job fetched that feed and committed whatever came back. A provider changing what it republishes, a
partial response, or a renamed model would have moved the ranking with no measurement of ours and no
review. Two things stop that:

  --apply   compares a fresh fetch against the committed file. If the fetch is within bounds it replaces
            the committed file; if not, the committed file is KEPT, the diff is written to
            data/scores-drift.jsonl so the refusal is public, and the exit code is still 0 so the rest
            of the daily job runs on yesterday's scores. Bounds: at most 20% of previously matched models
            may move their coding_index by more than 5 points, at most 10% may vanish, and the matched
            count may not fall by more than 25%. Every model that moved is printed either way.
  --check   is the pull-request side: the committed file must be readable, every matched row must carry
            the three indexes as numbers, and fetched_on may not be older than --stale-after days (default
            14). A stale file means the daily job stopped running, which is a fact the front page would
            otherwise hide behind a fresh-looking date on the ranking.

Exit 0 clean (or drift refused but recorded), 1 a check failed, 2 the gate could not run.
"""
import argparse, json, shutil, sys
from datetime import date, datetime
from pathlib import Path

MAX_MOVED_SHARE = 0.20
MAX_MOVE_POINTS = 5.0
MAX_VANISHED_SHARE = 0.10
MAX_SHRINK_SHARE = 0.25
FIELDS = ("intelligence_index", "coding_index", "agentic_index")


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def index(scores):
    return {(m["provider"], m["model"]): m for m in scores.get("matched", [])}


def compare(prev, cur):
    """Return (verdict dict, list of moved rows). Pure, so a test can pin it."""
    a, b = index(prev), index(cur)
    vanished = sorted(k for k in a if k not in b)
    appeared = sorted(k for k in b if k not in a)
    moved = []
    for k in a:
        if k not in b:
            continue
        pa = (a[k].get("artificial_analysis") or {}).get("coding_index")
        pb = (b[k].get("artificial_analysis") or {}).get("coding_index")
        if isinstance(pa, (int, float)) and isinstance(pb, (int, float)) and abs(pa - pb) > MAX_MOVE_POINTS:
            moved.append({"provider": k[0], "model": k[1], "coding_index_before": pa, "coding_index_after": pb})
    n = max(1, len(a))
    reasons = []
    if len(moved) / n > MAX_MOVED_SHARE:
        reasons.append("%d of %d matched models moved their coding index by more than %g points"
                       % (len(moved), n, MAX_MOVE_POINTS))
    if len(vanished) / n > MAX_VANISHED_SHARE:
        reasons.append("%d of %d matched models vanished from the feed" % (len(vanished), n))
    if len(b) < len(a) * (1 - MAX_SHRINK_SHARE):
        reasons.append("matched count fell from %d to %d" % (len(a), len(b)))
    return {"previous_matched": len(a), "current_matched": len(b), "moved": len(moved),
            "vanished": [list(k) for k in vanished], "appeared": [list(k) for k in appeared],
            "refused": bool(reasons), "reasons": reasons}, moved


def check(path, today, stale_after):
    problems = []
    d = load(path)
    try:
        fetched = date.fromisoformat(d.get("fetched_on", ""))
    except ValueError:
        problems.append("fetched_on is not a date: %r" % d.get("fetched_on"))
        fetched = None
    if fetched and (today - fetched).days > stale_after:
        problems.append("scores were fetched on %s, %d days ago; the daily job has not refreshed them"
                        % (fetched, (today - fetched).days))
    for m in d.get("matched", []):
        aa = m.get("artificial_analysis") or {}
        for f in FIELDS:
            v = aa.get(f)
            if v is not None and not isinstance(v, (int, float)):
                problems.append("%s/%s: %s is %r, not a number" % (m.get("provider"), m.get("model"), f, v))
        if not m.get("matched_as"):
            problems.append("%s/%s has a score but no matched_as" % (m.get("provider"), m.get("model")))
    if not d.get("matched"):
        problems.append("no matched models at all")
    return problems


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--previous")
    ap.add_argument("--current")
    ap.add_argument("--apply", action="store_true", help="replace --previous with --current when within bounds")
    ap.add_argument("--date", help="YYYY-MM-DD for the drift record")
    ap.add_argument("--log", default="data/scores-drift.jsonl")
    ap.add_argument("--check", metavar="SCORES", help="validate a committed scores file")
    ap.add_argument("--today", help="YYYY-MM-DD, for --check")
    ap.add_argument("--stale-after", type=int, default=14)
    a = ap.parse_args()

    try:
        if a.check:
            today = date.fromisoformat(a.today) if a.today else date.today()
            problems = check(a.check, today, a.stale_after)
            if problems:
                print("%d PROBLEMS with %s:" % (len(problems), a.check))
                for p in problems:
                    print("  " + p)
                return 1
            print("CLEAN - %s is readable, numeric and fetched within %d days." % (a.check, a.stale_after))
            return 0

        if not (a.previous and a.current):
            print("need --previous and --current, or --check")
            return 2
        prev, cur = load(a.previous), load(a.current)
        verdict, moved = compare(prev, cur)
        for m in moved:
            print("  moved  %-12s %-44s %s -> %s" % (m["provider"], m["model"][:44],
                                                    m["coding_index_before"], m["coding_index_after"]))
        print("previous %d matched, current %d matched, %d moved, %d vanished, %d appeared"
              % (verdict["previous_matched"], verdict["current_matched"], verdict["moved"],
                 len(verdict["vanished"]), len(verdict["appeared"])))
        if a.apply:
            row = dict(verdict, date=a.date, moved_rows=moved)
            log = Path(a.log)
            log.parent.mkdir(parents=True, exist_ok=True)
            with open(log, "a", encoding="utf-8", newline="\n") as f:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
            if verdict["refused"]:
                print("\nDRIFT REFUSED - keeping %s unchanged:" % a.previous)
                for r in verdict["reasons"]:
                    print("  " + r)
                print("recorded in %s. The ranking runs on the previous scores until a human looks." % a.log)
                return 0
            shutil.copyfile(a.current, a.previous)
            print("applied: %s now holds the fresh scores (recorded in %s)" % (a.previous, a.log))
            return 0
        if verdict["refused"]:
            print("\nWOULD REFUSE:")
            for r in verdict["reasons"]:
                print("  " + r)
            return 1
        print("within bounds")
        return 0
    except (OSError, ValueError, KeyError) as e:
        print("gate could not run: %s: %s" % (type(e).__name__, e))
        return 2


if __name__ == "__main__":
    sys.exit(main())
