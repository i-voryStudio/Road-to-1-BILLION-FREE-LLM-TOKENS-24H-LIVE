#!/usr/bin/env python3
"""Calibrate the fourteen-day rule in both directions. No network.

    python bench/test_viability.py

gate_viability.py decides which endpoints are buried, degraded or healthy, and rank.py acts on that
verdict. A rule that decides burials and has never been watched failing is a rumour with an exit code.
Each case plants an uptime history in a temp dir, runs the gate, and checks the verdict it wrote.
"""
import json, subprocess, sys, tempfile
from datetime import date, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
GATE = HERE / "gate_viability.py"


def rows(provider, model, states, end="2026-09-21"):
    """One row per day, ending on `end`, states given oldest first."""
    e = date.fromisoformat(end)
    out = []
    for i, s in enumerate(states):
        d = e - timedelta(days=len(states) - 1 - i)
        out.append({"date": d.isoformat(), "provider": provider, "model": model, "state": s,
                    "http": 200 if s in ("alive", "empty") else 503, "seconds": 1.0, "note": ""})
    return out


def run(history_rows, today="2026-09-21"):
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        hist = tmp / "uptime.jsonl"
        hist.write_text("".join(json.dumps(r) + "\n" for r in history_rows), encoding="utf-8")
        (tmp / "data").mkdir()
        r = subprocess.run([sys.executable, str(GATE), "--today", today, "--history", str(hist),
                            "--out", str(tmp / "GRAVEYARD.md"), "--announced", str(tmp / "none.json")],
                           capture_output=True, text=True, cwd=str(tmp))
        state = json.loads((tmp / "data" / "viability.json").read_text(encoding="utf-8")) if (tmp / "data" / "viability.json").exists() else None
        grave = (tmp / "GRAVEYARD.md").read_text(encoding="utf-8") if (tmp / "GRAVEYARD.md").exists() else ""
        return r.returncode, r.stdout + r.stderr, state, grave


def names(state, bucket):
    return sorted((e["provider"], e["model"]) for e in (state or {}).get(bucket, []))


def main():
    bad = 0

    def case(label, ok, detail=""):
        nonlocal bad
        print("  %-4s %s%s" % ("ok" if ok else "FAIL", label, ("  -> " + detail) if (detail and not ok) else ""))
        if not ok:
            bad += 1

    print("must be BURIED:")
    code, out, st, grave = run(rows("p", "m", ["alive"] + ["down"] * 14))
    case("14 consecutive probed days down", code == 0 and names(st, "buried") == [("p", "m")], out[-200:])
    case("the headstone names the model, the death date and the last answer",
         "`m`" in grave and "2026-09-08" in grave and "2026-09-07" in grave, grave[:300])
    code, out, st, _ = run(rows("p", "m", ["alive"] + ["overloaded"] * 14))
    case("14 days of 503 count as down", names(st, "buried") == [("p", "m")], out[-200:])

    print("\nmust NOT be buried:")
    code, out, st, _ = run(rows("p", "m", ["alive"] + ["down"] * 13))
    case("13 days down is degraded, not buried", names(st, "buried") == [] and names(st, "degraded") == [("p", "m")])
    code, out, st, _ = run(rows("p", "m", ["down"] * 13 + ["alive"]))
    case("an endpoint that answered today is healthy whatever came before", names(st, "healthy") == [("p", "m")])
    code, out, st, _ = run(rows("p", "m", ["alive"] + ["empty"] * 14))
    case("empty 200s are not deaths (the endpoint answered)", names(st, "healthy") == [("p", "m")])
    code, out, st, _ = run(rows("p", "m", ["alive"] + ["rate_limited"] * 14))
    case("429s are not deaths", names(st, "healthy") == [("p", "m")])
    code, out, st, _ = run(rows("p", "m", ["alive"] + ["blocked"] * 14))
    case("blocked (401/403) is skipped entirely: a fact about the caller, not about them",
         names(st, "buried") == [] and names(st, "degraded") == [])
    # A gap in the history is not a day down: 5 down rows spread over 20 days with no rows between.
    gap = rows("p", "m", ["alive"], end="2026-09-01") + rows("p", "m", ["down"], end="2026-09-05") \
        + rows("p", "m", ["down"], end="2026-09-10") + rows("p", "m", ["down"], end="2026-09-21")
    code, out, st, _ = run(gap)
    case("days we did not probe do not count against a provider", names(st, "buried") == [] and st and st["degraded"] == [] and names(st, "flaky") == [("p", "m")])

    print("\nthe file itself:")
    dup = rows("p", "m", ["alive"] * 3)
    dup.append(dict(dup[-1], state="rate_limited"))
    code, out, st, _ = run(dup)
    case("two rows for one endpoint-day are refused with exit 1", code == 1 and "more than once" in out, out[-200:])
    code, out, st, _ = run([])
    case("no history at all is exit 0 and buries nothing", code == 0 and st is None)
    junk = rows("p", "m", ["alive"] * 2) + [{"date": "not-a-date", "provider": "p", "model": "m", "state": "down"}]
    code, out, st, _ = run(junk)
    case("a row with a bad date is skipped, not fatal", code == 0 and names(st, "healthy") == [("p", "m")])

    print("\n%d failures" % bad)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
