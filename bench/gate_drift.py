#!/usr/bin/env python3
"""Refuse to let a third-party score feed, or a hand edit dressed as one, silently re-rank this list.

    python bench/gate_drift.py --previous data/scores.json --current /tmp/scores-new.json --date 2026-09-08 --apply
    python bench/gate_drift.py --check data/scores.json --today 2026-09-08
    python bench/gate_drift.py --check data/scores.json --today 2026-09-08 --previous /tmp/scores-base.json

Half of every Value on the front page is a quality score we import from a public feed, and until now the
daily job fetched that feed and committed whatever came back. A provider changing what it republishes, a
partial response, or a renamed model would have moved the ranking with no measurement of ours and no
review. The first version of this gate checked shape and freshness only, so a scores.json with every
coding_index set to 99.0 and a fetched_on next year passed --check, passed every other gate, regenerated a
front page ranked on invented numbers, and then the daily --apply DEFENDED the poisoned file against the
honest feed, because the honest feed "drifted" too far from it. The second version read the content and
caught that file; it did not catch the next one: twelve of fifty-five scores raised by thirty points each,
all distinct, all in range, passed --check because the bound was "at most 20% may move", re-ranked the
list, and the next honest fetch was refused for drifting 21.8% from the poison, exit 0, poison kept. Three
things stop that now: the bounds are tighter, a refusal is loud, and the gate remembers what it applied.

THE BOUNDS, the same for --check and --apply. Against the previous file, a fetch is refused when:
  - more than 5% of the previously matched models moved their coding_index by more than 5 points;
  - any single coding_index moved by more than 15 points;
  - more than 20% moved by more than 2 points: a mass nudge that no single row would flag, and that is
    enough to swap the top two rows of the ranking;
  - more than 10% of the matched models vanished, or the matched count fell by more than 25%.
A fetch that carries a "note" field (a string explaining a benchmark version change) is refused all the
same; the note is what a human needs to apply it anyway, with --apply --force-note, and the forced apply
is recorded with the note. There is no way to force a file that carries no note.

  --check   is the pull-request side. The committed file must be readable; fetched_on must be a date, not
            in the future, and not older than --stale-after days (default 14: a stale file means the
            daily job stopped running); every matched row must carry its indexes as numbers inside
            [0, 100], every arena ELO inside [0, 5000], and a matched_as that has the shape of a model id
            (the same ID_OK the catalogue refresher applies); no single coding_index may be shared by
            more than 10 percent of the matched rows across distinct models. Then the drift bounds above
            run "since the committed file": against --previous when given (CI passes the base branch's
            copy), otherwise against `git show HEAD:<file>` when the working copy differs from it (a
            local edit not yet committed); a file that is committed and unchanged has nothing to be
            compared with and the CLEAN line says so. Two more rules protect the committed file itself:
            if data/scores.rejected.json exists beside it and holds the same scores, the committed file
            IS a file this gate refused, and the check fails; and when data/scores-drift.jsonl records a
            file this gate applied, the committed file must be that file (same content digest), because
            scores enter this repo through --apply, never by hand.
  --apply   compares a fresh fetch against the committed file. In order:
            1. If data/scores.rejected.json exists beside the committed file and holds the same scores,
               the gate refuses to run at all (exit 1): someone copied a refused file over the committed
               one, and the previous file can never be the one that was refused.
            2. The content checks run on both files. A fresh file that fails them is refused. A previous
               file that fails them is never kept: the fresh one replaces it and the reason is recorded,
               because a poisoned committed file is exactly what the drift bounds would otherwise protect.
            3. The gate remembers what it applies: every applied file's content digest (sha256 over the
               canonical JSON, so line endings do not matter) is written to data/scores-drift.jsonl. When
               the log holds one and the previous file's digest is not it, the previous file did not
               arrive through this gate: a hand edit, honest or not, and the bounds do not defend it. The
               fresh file is applied when it passes the content checks, and both digests are recorded.
            4. Otherwise the bounds above decide. Within bounds: applied, recorded with its digest. Out of
               bounds: the fetched file is written to data/scores.rejected.json beside the committed one,
               the refusal is recorded, and the exit code is 1, so the daily job FAILS VISIBLY instead of
               returning 0 and keeping the previous file in silence. (In CI the failed job is the public
               signal; the record and the rejected file live in the runner's workspace for a human to
               fetch.) Every model that moved is printed either way.

HOW A POISONED COMMITTED FILE IS RECOVERED FROM, exactly, and the gate prints which path applied:
  a. It fails the content checks (flat scores, out of range, a date in the future): the next honest fetch
     replaces it (step 2). Nothing to do.
  b. It passes them but its digest is not the one this gate last applied: it was committed by hand, the
     bounds do not defend it, the next honest fetch replaces it (step 3). Nothing to do.
  c. It passes them AND carries the last applied digest (it arrived through the gate under a note, or the
     log row was forged in the same commit): the honest fetch is refused, written to
     data/scores.rejected.json, exit 1, and the daily job keeps failing until a human acts. The human
     restores the last honest version from history (`git log -- data/scores.json`, `git checkout <sha> --
     data/scores.json`), or applies the fetch with --force-note after writing the note into it. What the
     human must never do is copy scores.rejected.json over the committed file: step 1 refuses to run on
     such a file until scores.rejected.json is reviewed and removed.
A --check that passes and an --apply that exits 0 are the only two green lights; nothing else is.

Exit 0 clean (or applied), 1 a check failed, drift refused, or nothing here can be published, 2 the gate
could not run.
"""
import argparse, hashlib, json, shutil, subprocess, sys
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from refresh_catalog import ID_OK  # one shape for a model id, one place

MAX_MOVED_SHARE = 0.05          # share of previously matched models that may move by more than MOVE_POINTS
MOVE_POINTS = 5.0               # a coding_index that moved by more than this counts as moved
MAX_SINGLE_MOVE_POINTS = 15.0   # no single score may move by more than this, whatever the share
MAX_NUDGED_SHARE = 0.20         # share that may move by more than NUDGE_POINTS: a mass nudge no row would flag
NUDGE_POINTS = 2.0
MAX_VANISHED_SHARE = 0.10
MAX_SHRINK_SHARE = 0.25
MAX_FLAT_SHARE = 0.10           # share of matched rows, on distinct models, that may share one coding_index
INDEX_RANGE = (0.0, 100.0)
ELO_RANGE = (0.0, 5000.0)
WIN_RATE_RANGE = (0.0, 100.0)
FIELDS = ("intelligence_index", "coding_index", "agentic_index")
REJECTED_NAME = "scores.rejected.json"   # written beside the committed file on refusal
LOG_NAME = "scores-drift.jsonl"          # the gate's memory of what it applied, beside the committed file


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def index(scores):
    return {(m["provider"], m["model"]): m for m in scores.get("matched", [])}


def base_id(matched_as):
    """qwen/qwen3.8-27b:free and qwen/qwen3.8-27b are one model; the feed scores the model, not the variant."""
    return (matched_as or "").split(":")[0]


def content_digest(scores):
    """sha256 over the canonical JSON: the same scores in a different whitespace or line ending are the
    same file. This is what the gate remembers about a file it applied."""
    canon = json.dumps(scores, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canon.encode("utf-8")).hexdigest()


def same_scores(a, b):
    return content_digest(a) == content_digest(b)


def note_of(scores):
    """The benchmark-version note a fetched file may carry, or None. Only a non-empty string counts."""
    n = scores.get("note")
    return n.strip() if isinstance(n, str) and n.strip() else None


def compare(prev, cur):
    """Return (verdict dict, list of moved rows). Pure, so a test can pin it. A row is in the list when
    its coding_index moved by more than NUDGE_POINTS; each carries the size of the move."""
    a, b = index(prev), index(cur)
    vanished = sorted(k for k in a if k not in b)
    appeared = sorted(k for k in b if k not in a)
    moved = []
    for k in a:
        if k not in b:
            continue
        pa = (a[k].get("artificial_analysis") or {}).get("coding_index")
        pb = (b[k].get("artificial_analysis") or {}).get("coding_index")
        if isinstance(pa, (int, float)) and isinstance(pb, (int, float)) and abs(pa - pb) > NUDGE_POINTS:
            moved.append({"provider": k[0], "model": k[1], "coding_index_before": pa, "coding_index_after": pb,
                          "points": round(abs(pa - pb), 2)})
    n = max(1, len(a))
    big = [m for m in moved if m["points"] > MOVE_POINTS]
    largest = max((m["points"] for m in moved), default=0.0)
    reasons = []
    if len(big) / n > MAX_MOVED_SHARE:
        reasons.append("%d of %d matched models moved their coding index by more than %g points (%.1f%%, the bound "
                       "is %g%%)" % (len(big), n, MOVE_POINTS, 100.0 * len(big) / n, 100 * MAX_MOVED_SHARE))
    if largest > MAX_SINGLE_MOVE_POINTS:
        worst = max(moved, key=lambda m: m["points"])
        reasons.append("%s/%s moved by %g points, more than any single score may move (%g)"
                       % (worst["provider"], worst["model"], worst["points"], MAX_SINGLE_MOVE_POINTS))
    if len(moved) / n > MAX_NUDGED_SHARE:
        reasons.append("%d of %d matched models moved by more than %g points (%.1f%%, the bound is %g%%): a mass "
                       "nudge that no single row would flag"
                       % (len(moved), n, NUDGE_POINTS, 100.0 * len(moved) / n, 100 * MAX_NUDGED_SHARE))
    if len(vanished) / n > MAX_VANISHED_SHARE:
        reasons.append("%d of %d matched models vanished from the feed" % (len(vanished), n))
    if len(b) < len(a) * (1 - MAX_SHRINK_SHARE):
        reasons.append("matched count fell from %d to %d" % (len(a), len(b)))
    return {"previous_matched": len(a), "current_matched": len(b), "moved": len(big), "nudged": len(moved),
            "largest_move": largest, "vanished": [list(k) for k in vanished], "appeared": [list(k) for k in appeared],
            "refused": bool(reasons), "reasons": reasons}, moved


def _number(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def check(path, today, stale_after=14, previous=None):
    """Every problem with a scores file. stale_after=None skips the staleness rule (for --apply, where
    the committed file is by definition older than the fetch and its age is not what is in question).
    previous, a path or a loaded dict, switches on the drift bounds "since the committed file"."""
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
    if previous is not None:
        prev = previous if isinstance(previous, dict) else load(previous)
        verdict, _ = compare(prev, d)
        for r in verdict["reasons"]:
            problems.append("since the committed file: %s" % r)
        if verdict["refused"] and note_of(d):
            problems.append("the file carries a note (%r); the drift above is refused all the same, and a human "
                            "may apply it with --apply --force-note" % note_of(d))
    return problems


def committed_version(path):
    """The committed text of `path` when the working copy differs from it, else None. `git show HEAD:...`,
    run in the file's own folder so a --root copy or a foreign cwd does not matter. No git, not a repo,
    or an identical file all mean "nothing to compare with", and the caller says so out loud."""
    p = Path(path).resolve()
    try:
        top = subprocess.run(["git", "-C", str(p.parent), "rev-parse", "--show-toplevel"],
                             capture_output=True, text=True, timeout=30)
        if top.returncode != 0:
            return None
        rel = p.relative_to(Path(top.stdout.strip()).resolve()).as_posix()
        shown = subprocess.run(["git", "-C", str(p.parent), "show", "HEAD:%s" % rel],
                               capture_output=True, timeout=30)
        if shown.returncode != 0:
            return None
        committed = json.loads(shown.stdout.decode("utf-8"))
    except (OSError, ValueError, subprocess.SubprocessError):
        return None
    return None if same_scores(committed, load(p)) else committed


def record(log_path, row):
    log = Path(log_path)
    log.parent.mkdir(parents=True, exist_ok=True)
    with open(log, "a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def last_applied_digest(log_path):
    """The content digest of the last file this gate applied, from the log, or None when the log has
    never recorded one (a fresh repo, or a log written before the gate remembered what it applied)."""
    log = Path(log_path)
    if not log.exists():
        return None
    found = None
    for line in log.read_text(encoding="utf-8").splitlines():
        try:
            row = json.loads(line)
        except ValueError:
            continue
        if row.get("applied") is True and isinstance(row.get("sha256"), str):
            found = row["sha256"]
    return found


def rejected_twin(path):
    """The refused-file record beside `path`, if the committed file IS that refused file."""
    rej = Path(path).parent / REJECTED_NAME
    if not rej.exists():
        return None
    try:
        return rej if same_scores(load(rej), load(path)) else None
    except (OSError, ValueError):
        return None


def refuse(current, previous, log, date_, row, reasons):
    """Write the fetched file beside the committed one, record why, say it, exit 1."""
    rej = Path(previous).parent / REJECTED_NAME
    shutil.copyfile(current, rej)
    record(log, dict(row, date=date_, refused=True, applied=False, reasons=reasons, rejected_file=str(rej)))
    print("\nREFUSED - keeping %s unchanged; the fetched file is in %s and the refusal is recorded in %s:"
          % (previous, rej, log))
    for r in reasons:
        print("  " + r)
    print("Exit 1 on purpose: the daily job fails where everyone can see it. A human looks, then either restores "
          "the last honest file from git history or applies this one with --apply --force-note after writing a "
          "note into it. Never copy %s over %s." % (rej.name, Path(previous).name))
    return 1


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--previous", help="the committed file (with --current and --apply), or the base copy for --check")
    ap.add_argument("--current")
    ap.add_argument("--apply", action="store_true", help="replace --previous with --current when within bounds")
    ap.add_argument("--force-note", action="store_true",
                    help="with --apply: apply an out-of-bounds fetch that carries a 'note' field, and record the note")
    ap.add_argument("--date", help="YYYY-MM-DD for the drift record; also 'today' for the content checks")
    ap.add_argument("--log", help="the gate's record (default: %s beside the committed file)" % LOG_NAME)
    ap.add_argument("--check", metavar="SCORES", help="validate a committed scores file")
    ap.add_argument("--today", help="YYYY-MM-DD, for --check")
    ap.add_argument("--stale-after", type=int, default=14)
    a = ap.parse_args()

    try:
        if a.check:
            today = date.fromisoformat(a.today) if a.today else date.today()
            log = a.log or str(Path(a.check).parent / LOG_NAME)
            problems = []
            twin = rejected_twin(a.check)
            if twin:
                problems.append("%s holds the same scores as %s: the committed file is a file this gate refused. "
                                "Restore the last honest version from git history; never copy the refused file over "
                                "the committed one" % (a.check, twin))
            prev, since = None, None
            if a.previous:
                prev, since = load(a.previous), "--previous %s" % a.previous
                base_problems = check(a.previous, today, None)
                if base_problems:
                    print("NOTE: %s fails the content checks itself, so the drift bounds are not run against it:"
                          % a.previous)
                    for p in base_problems:
                        print("  " + p)
                    prev, since = None, None
            else:
                prev = committed_version(a.check)
                since = "the committed version, git show HEAD:%s" % Path(a.check).name if prev else None
            problems += check(a.check, today, a.stale_after, prev)
            applied = last_applied_digest(log)
            if applied and applied != content_digest(load(a.check)):
                problems.append("%s is not the file this gate last applied (its content digest is %s..., the log %s "
                                "says %s...). Scores enter this repo through --apply, which records what it applied; a "
                                "committed file the gate never saw is a hand edit, whatever its numbers say"
                                % (a.check, content_digest(load(a.check))[:12], log, applied[:12]))
            if problems:
                print("%d PROBLEMS with %s:" % (len(problems), a.check))
                for p in problems:
                    print("  " + p)
                return 1
            print("CLEAN - %s is readable, every index and ELO is a number in range, every matched_as is a model id, "
                  "no score is flattened across models, it was fetched within %d days, it is not the file in %s, %s"
                  % (a.check, a.stale_after, REJECTED_NAME,
                     ("and it is within the drift bounds since %s." % since) if since else
                     "and it is committed unchanged, so there is no previous version to measure drift against "
                     "(CI passes the base branch's copy as --previous)."))
            if applied:
                print("It is the file this gate last applied (content digest %s...)." % applied[:12])
            return 0

        if not (a.previous and a.current):
            print("need --previous and --current, or --check")
            return 2
        if a.force_note and not a.apply:
            print("--force-note only means something with --apply")
            return 2
        today = date.fromisoformat(a.date) if a.date else date.today()
        log = a.log or str(Path(a.previous).parent / LOG_NAME)

        # 1. The previous file can never be the one that was refused.
        twin = rejected_twin(a.previous)
        if twin:
            print("REFUSING TO RUN: %s holds the same scores as %s, the file this gate refused. Someone copied the "
                  "refused file over the committed one. Restore the last honest version from git history, review "
                  "and remove %s, then run again." % (a.previous, twin, twin.name))
            return 1

        # 2. Content checks on both files.
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
            # The fetch is broken or was tampered with in flight. Keep the committed file, fail out loud.
            if a.apply:
                return refuse(a.current, a.previous, log, a.date, {}, ["the fresh file fails --check"] + cur_problems)
            print("\nWOULD REFUSE: the fresh file fails --check")
            return 1
        prev, cur = load(a.previous), load(a.current)
        cur_digest = content_digest(cur)
        if prev_problems:
            # The committed file is what is wrong. The drift bounds must not defend it: replace it, and say why.
            print("\nthe committed file fails --check, so the drift bounds do not apply to it: a poisoned file must "
                  "not be defended against an honest fetch.")
            if a.apply:
                record(log, {"date": a.date, "refused": False, "applied": True, "sha256": cur_digest,
                             "previous_invalid": prev_problems})
                shutil.copyfile(a.current, a.previous)
                print("applied: %s now holds the fresh scores, replacing a file that failed --check (recorded in %s)"
                      % (a.previous, log))
                return 0
            print("would apply the fresh file over it")
            return 0

        # 3. The bounds defend only what this gate applied.
        applied, prev_digest = last_applied_digest(log), content_digest(prev)
        if applied and applied != prev_digest:
            print("\nthe committed file is not the file this gate last applied (content digest %s..., the log says "
                  "%s...): it was written by hand, and the drift bounds do not defend a hand edit against the feed."
                  % (prev_digest[:12], applied[:12]))
            if a.apply:
                record(log, {"date": a.date, "refused": False, "applied": True, "sha256": cur_digest,
                             "previous_unattested": {"found": prev_digest, "last_applied": applied}})
                shutil.copyfile(a.current, a.previous)
                print("applied: %s now holds the fresh scores, replacing a file that did not arrive through this gate "
                      "(both digests recorded in %s)" % (a.previous, log))
                return 0
            print("would apply the fresh file over it")
            return 0

        # 4. The bounds.
        verdict, moved = compare(prev, cur)
        for m in moved:
            print("  moved  %-12s %-44s %s -> %s (%g)" % (m["provider"], m["model"][:44],
                                                         m["coding_index_before"], m["coding_index_after"], m["points"]))
        print("previous %d matched, current %d matched, %d moved by more than %g, %d by more than %g, largest %g, "
              "%d vanished, %d appeared"
              % (verdict["previous_matched"], verdict["current_matched"], verdict["moved"], MOVE_POINTS,
                 verdict["nudged"], NUDGE_POINTS, verdict["largest_move"], len(verdict["vanished"]),
                 len(verdict["appeared"])))
        note = note_of(cur)
        if a.apply:
            if verdict["refused"] and a.force_note:
                if not note:
                    print("\n--force-note refused: the fetched file carries no 'note' field. A forced apply needs the "
                          "benchmark version change written into the file it applies, so the record explains itself.")
                    return 1
                record(log, dict(verdict, date=a.date, moved_rows=moved, applied=True, forced=True, note=note,
                                 sha256=cur_digest))
                shutil.copyfile(a.current, a.previous)
                print("\nAPPLIED UNDER --force-note: %s now holds the fresh scores despite the drift above; the note "
                      "(%r) and every moved row are recorded in %s" % (a.previous, note, log))
                return 0
            if verdict["refused"]:
                reasons = list(verdict["reasons"])
                if note:
                    reasons.append("the fetched file carries a note (%r): a human may apply it with --apply --force-note"
                                   % note)
                return refuse(a.current, a.previous, log, a.date, dict(verdict, moved_rows=moved), reasons)
            record(log, dict(verdict, date=a.date, moved_rows=moved, applied=True, sha256=cur_digest))
            shutil.copyfile(a.current, a.previous)
            print("applied: %s now holds the fresh scores (recorded in %s with its content digest)" % (a.previous, log))
            return 0
        if verdict["refused"]:
            print("\nWOULD REFUSE:")
            for r in verdict["reasons"]:
                print("  " + r)
            if note:
                print("  the fetched file carries a note (%r): a human may apply it with --apply --force-note" % note)
            return 1
        print("within bounds")
        return 0
    except (OSError, ValueError, KeyError) as e:
        print("gate could not run: %s: %s" % (type(e).__name__, e))
        return 2


if __name__ == "__main__":
    sys.exit(main())
