#!/usr/bin/env python3
"""Refuse to let a third-party score feed, or a hand edit dressed as one, silently re-rank this list.

    python bench/gate_drift.py --previous data/scores.json --current /tmp/scores-new.json --date 2026-09-08 --apply
    python bench/gate_drift.py --check data/scores.json --today 2026-09-08

Half of every Value on the front page is a quality score we import from a public feed, and until now the
daily job fetched that feed and committed whatever came back. A provider changing what it republishes, a
partial response, or a renamed model would have moved the ranking with no measurement of ours and no
review. The first version of this gate checked shape and freshness only, so a scores.json with every
coding_index set to 99.0 and a fetched_on next year passed --check, passed every other gate, regenerated a
front page ranked on invented numbers, and then the daily --apply DEFENDED the poisoned file against the
honest feed, because the honest feed "drifted" too far from it. Two things stop that now:

  --check   is the pull-request side, and it reads the content, not only the shape. The committed file
            must be readable; fetched_on must be a date, not in the future, and not older than
            --stale-after days (default 14: a stale file means the daily job stopped running, which is a
            fact the front page would otherwise hide behind a fresh-looking date on the ranking); every
            matched row must carry its indexes as numbers inside [0, 100], every arena ELO inside
            [0, 5000], and a matched_as that has the shape of a model id (the same ID_OK the catalogue
            refresher applies); and no single coding_index may be shared by more than 10 percent of the
            matched rows across distinct models. The same model served by six providers shares one score
            and that is a feed; six different models at the same decimal is a hand edit.
  --apply   compares a fresh fetch against the committed file, and FIRST runs the content checks above on
            both. A previous file that fails them is never kept: the fresh one replaces it and the reason
            is printed and recorded, because a poisoned committed file is exactly what the drift bounds
            would otherwise protect. A fresh file that fails them is never applied. When both are sound,
            the fetch is applied if it is within bounds; if not, the committed file is KEPT, the diff is
            written to data/scores-drift.jsonl so the refusal is public, and the exit code is still 0 so
            the rest of the daily job runs on yesterday's scores. Bounds: at most 20% of previously
            matched models may move their coding_index by more than 5 points, at most 10% may vanish, and
            the matched count may not fall by more than 25%. Every model that moved is printed either way.

Exit 0 clean (or drift refused but recorded), 1 a check failed (or, under --apply, neither file is
sound, so there is nothing to stand on), 2 the gate could not run.
"""
import argparse, json, shutil, sys
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from refresh_catalog import ID_OK  # one shape for a model id, one place

MAX_MOVED_SHARE = 0.20
MAX_MOVE_POINTS = 5.0
MAX_VANISHED_SHARE = 0.10
MAX_SHRINK_SHARE = 0.25
MAX_FLAT_SHARE = 0.10          # share of matched rows, on distinct models, that may share one coding_index
INDEX_RANGE = (0.0, 100.0)
ELO_RANGE = (0.0, 5000.0)
WIN_RATE_RANGE = (0.0, 100.0)
FIELDS = ("intelligence_index", "coding_index", "agentic_index")


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def index(scores):
    return {(m["provider"], m["model"]): m for m in scores.get("matched", [])}


def base_id(matched_as):
    """qwen/qwen3.8-27b:free and qwen/qwen3.8-27b are one model; the feed scores the model, not the variant."""
    return (matched_as or "").split(":")[0]


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


def _number(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def check(path, today, stale_after=14):
    """Every problem with a scores file. stale_after=None skips the staleness rule (for --apply, where
    the committed file is by definition older than the fetch and its age is not what is in question)."""
    problems = []
    d = load(path)
    try:
        fetched = date.fromisoformat(d.get("fetched_on", ""))
    except (TypeError, ValueError):
        problems.append("fetched_on is not a date: %r" % d.get("fetched_on"))
        fetched = None
    if fetched and fetched > today:
        problems.append("fetched_on is %s, which is after today (%s). A fetch cannot happen in the future; a date "
                        "there is a hand edit" % (fetched, today))
    if fetched and stale_after is not None and (today - fetched).days > stale_after:
        problems.append("scores were fetched on %s, %d days ago; the daily job has not refreshed them"
                        % (fetched, (today - fetched).days))
    matched = d.get("matched") or []
    flat = {}
    for m in matched:
        who = "%s/%s" % (m.get("provider"), m.get("model"))
        aa = m.get("artificial_analysis") or {}
        for f in FIELDS:
            v = aa.get(f)
            if v is None:
                continue
            if not _number(v):
                problems.append("%s: %s is %r, not a number" % (who, f, v))
            elif not INDEX_RANGE[0] <= v <= INDEX_RANGE[1]:
                problems.append("%s: %s is %s, outside [%g, %g]. The feed publishes an index on that scale; anything "
                                "else was typed" % (who, f, v, INDEX_RANGE[0], INDEX_RANGE[1]))
        for cat, row in (m.get("design_arena") or {}).items():
            row = row or {}
            elo, wr = row.get("elo"), row.get("win_rate")
            if elo is not None and (not _number(elo) or not ELO_RANGE[0] <= elo <= ELO_RANGE[1]):
                problems.append("%s: %s elo is %r, outside [%g, %g]" % (who, cat, elo, ELO_RANGE[0], ELO_RANGE[1]))
            if wr is not None and (not _number(wr) or not WIN_RATE_RANGE[0] <= wr <= WIN_RATE_RANGE[1]):
                problems.append("%s: %s win_rate is %r, outside [%g, %g]" % (who, cat, wr, WIN_RATE_RANGE[0], WIN_RATE_RANGE[1]))
        ma = m.get("matched_as")
        if not ma:
            problems.append("%s has a score but no matched_as" % who)
        elif not isinstance(ma, str) or not ID_OK.match(ma):
            problems.append("%s: matched_as %r does not have the shape of a model id" % (who, ma))
        ci = aa.get("coding_index")
        if _number(ci):
            flat.setdefault(ci, set()).add(base_id(ma if isinstance(ma, str) else who))
    for value, models in sorted(flat.items(), key=lambda kv: -len(kv[1])):
        if len(models) >= 2 and len(models) / max(1, len(matched)) > MAX_FLAT_SHARE:
            problems.append("%d distinct models out of %d matched rows share the identical coding_index %s. One model on "
                            "several providers shares a score; several models at one decimal is a hand edit, not a feed"
                            % (len(models), len(matched), value))
            break
    if not matched:
        problems.append("no matched models at all")
    return problems


def record(log_path, row):
    log = Path(log_path)
    log.parent.mkdir(parents=True, exist_ok=True)
    with open(log, "a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--previous")
    ap.add_argument("--current")
    ap.add_argument("--apply", action="store_true", help="replace --previous with --current when within bounds")
    ap.add_argument("--date", help="YYYY-MM-DD for the drift record; also 'today' for the content checks")
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
            print("CLEAN - %s is readable, every index and ELO is a number in range, every matched_as is a model id, "
                  "no score is flattened across models, and it was fetched within %d days." % (a.check, a.stale_after))
            return 0

        if not (a.previous and a.current):
            print("need --previous and --current, or --check")
            return 2
        today = date.fromisoformat(a.date) if a.date else date.today()
        prev_problems = check(a.previous, today, None)
        cur_problems = check(a.current, today, None)
        for label, probs in (("previous", prev_problems), ("current", cur_problems)):
            if probs:
                print("%s file %s fails the content checks:" % (label, a.previous if label == "previous" else a.current))
                for p in probs:
                    print("  " + p)
        if cur_problems and prev_problems:
            print("\nNEITHER FILE IS SOUND. Nothing here can be published; a human has to look.")
            return 1
        if cur_problems:
            # The fetch is broken or was tampered with in flight. Keep the committed file, say so in public.
            if a.apply:
                record(a.log, {"date": a.date, "refused": True, "applied": False,
                               "reasons": ["the fresh file fails --check"] + cur_problems})
                print("\nFRESH FILE REFUSED - keeping %s unchanged; recorded in %s." % (a.previous, a.log))
                return 0
            print("\nWOULD REFUSE: the fresh file fails --check")
            return 1
        if prev_problems:
            # The committed file is what is wrong. The drift bounds must not defend it: replace it, and say why.
            print("\nthe committed file fails --check, so the drift bounds do not apply to it: a poisoned file must "
                  "not be defended against an honest fetch.")
            if a.apply:
                record(a.log, {"date": a.date, "refused": False, "applied": True,
                               "previous_invalid": prev_problems})
                shutil.copyfile(a.current, a.previous)
                print("applied: %s now holds the fresh scores, replacing a file that failed --check (recorded in %s)"
                      % (a.previous, a.log))
                return 0
            print("would apply the fresh file over it")
            return 0

        prev, cur = load(a.previous), load(a.current)
        verdict, moved = compare(prev, cur)
        for m in moved:
            print("  moved  %-12s %-44s %s -> %s" % (m["provider"], m["model"][:44],
                                                    m["coding_index_before"], m["coding_index_after"]))
        print("previous %d matched, current %d matched, %d moved, %d vanished, %d appeared"
              % (verdict["previous_matched"], verdict["current_matched"], verdict["moved"],
                 len(verdict["vanished"]), len(verdict["appeared"])))
        if a.apply:
            record(a.log, dict(verdict, date=a.date, moved_rows=moved, applied=not verdict["refused"]))
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
