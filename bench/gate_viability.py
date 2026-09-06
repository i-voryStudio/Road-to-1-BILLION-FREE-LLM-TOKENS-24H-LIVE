#!/usr/bin/env python3
"""Apply the fourteen-day rule: what is healthy, what is degraded, and what gets buried.

    python bench/gate_viability.py --today 2026-09-06

Free endpoints die. Not in years - in months, and often without an announcement. The catalogue we
cross-check against lost six providers between March and August 2026, and the only reason anyone knows
is that somebody went back and looked. A list that never removes anything is a list of things that
used to work.

So there is a rule, and it is applied by code rather than by whoever remembers:

    0 days down          healthy
    1-3 days down        flaky      - marked in the tables, still ranked
    4-13 days down       DEGRADED   - pushed down the ranking
    14+ days down        BURIED     - out of the main ranking, into GRAVEYARD.md with the date it
                                      died and the last day it answered

Buried is not deleted. A provider that comes back returns to the ranking with its history intact,
because "this died in September and came back in November" is worth more to a reader than either
half alone.

TWO THINGS THIS DELIBERATELY DOES NOT DO:

**A day with no measurement is not a day down.** If we never had a key, or the radar did not run,
that is our gap, not their outage. Only days we actually probed count against a provider.

**`empty` does not count as down either.** A reasoning model that returns 200 with nothing in it is
a real problem, and it is reported - but the endpoint answered. Conflating the two would blame a
provider for a switch we failed to set.
"""
import argparse, json, sys
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
FLAKY_FROM, DEGRADED_FROM, BURY_AT = 1, 4, 14
UP_STATES = {"alive", "empty", "rate_limited"}   # answered, even if not usefully
DOWN_STATES = {"down", "overloaded"}


def read_history(path):
    rows = []
    if not path.exists():
        return rows
    for line in path.read_text(encoding="utf-8").split("\n"):
        line = line.strip()
        if line:
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--today", required=True)
    ap.add_argument("--history", default="data/uptime.jsonl")
    ap.add_argument("--out", default="GRAVEYARD.md")
    a = ap.parse_args()

    try:
        today = datetime.strptime(a.today, "%Y-%m-%d").date()
    except ValueError:
        print("--today must be YYYY-MM-DD")
        return 2

    rows = read_history(Path(a.history))
    if not rows:
        print("no uptime history yet at %s" % a.history)
        print("Run bench/probe_alive.py daily. Until there is history, nothing can be buried and")
        print("nothing can be trusted to be alive either - which is the honest state, not a failure.")
        return 0

    # date -> state, per endpoint. Days we did not probe simply do not exist here.
    seen = defaultdict(dict)
    for r in rows:
        if r.get("state") == "no_key":
            continue
        try:
            d = datetime.strptime(r["date"], "%Y-%m-%d").date()
        except (ValueError, KeyError):
            continue
        seen[(r["provider"], r["model"])][d] = r["state"]

    healthy, flaky, degraded, buried = [], [], [], []
    for (prov, model), days in sorted(seen.items()):
        dates = sorted(days)
        last_up = max((d for d in dates if days[d] in UP_STATES), default=None)
        # Consecutive probed days at the end that were down.
        down_run, cursor = 0, dates[-1]
        for d in reversed(dates):
            if days[d] in DOWN_STATES:
                down_run += 1
                cursor = d
            else:
                break
        entry = {"provider": prov, "model": model, "days_down": down_run,
                 "last_alive": last_up.isoformat() if last_up else None,
                 "probed_days": len(dates), "first_probe": dates[0].isoformat(),
                 "down_since": cursor.isoformat() if down_run else None}
        if down_run >= BURY_AT:
            buried.append(entry)
        elif down_run >= DEGRADED_FROM:
            degraded.append(entry)
        elif down_run >= FLAKY_FROM:
            flaky.append(entry)
        else:
            healthy.append(entry)

    state = {"checked_on": a.today, "rule": {"flaky_from_days": FLAKY_FROM,
                                             "degraded_from_days": DEGRADED_FROM,
                                             "buried_at_days": BURY_AT},
             "healthy": healthy, "flaky": flaky, "degraded": degraded, "buried": buried}
    Path("data/viability.json").parent.mkdir(parents=True, exist_ok=True)
    Path("data/viability.json").write_text(json.dumps(state, indent=1) + "\n",
                                           encoding="utf-8", newline="\n")

    span = (today - min(d for days in seen.values() for d in days)).days + 1
    L = ["# Graveyard", "",
         "Endpoints removed from the main ranking after **%d consecutive days** with no answer, and the "
         "date each one died. Buried is not deleted: if one comes back it returns to the ranking with "
         "its history intact." % BURY_AT, "",
         "Free endpoints die in months, not years, and usually without an announcement. A list that "
         "never removes anything is a list of things that used to work.", "",
         "History so far: **%d day(s)** of measurements, %d endpoints tracked."
         % (span, len(seen)), ""]
    if buried:
        L += ["| Model | Provider | Died | Last answered | Days down |", "|---|---|---|---|---|"]
        for e in buried:
            L.append("| `%s` | %s | %s | %s | **%d** |"
                     % (e["model"], e["provider"], e["down_since"], e["last_alive"] or "never in our history",
                        e["days_down"]))
    else:
        L.append("**Nothing buried yet.** Either everything is answering, or there is not yet %d days of "
                 "history to bury anything with. The counts below say which." % BURY_AT)
    if degraded:
        L += ["", "## Degraded: 4 to %d days down, still listed but pushed down" % (BURY_AT - 1), "",
              "| Model | Provider | Down since | Days |", "|---|---|---|---|"]
        for e in degraded:
            L.append("| `%s` | %s | %s | %d |" % (e["model"], e["provider"], e["down_since"], e["days_down"]))
    if flaky:
        L += ["", "## Flaky: missed the last %d day(s)" % FLAKY_FROM, ""]
        for e in flaky:
            L.append("- `%s` at %s, down %d day(s) since %s"
                     % (e["model"], e["provider"], e["days_down"], e["down_since"]))
    L += ["", "---", "",
          "A day we did not measure is not a day down: if the radar did not run, or we hold no key, "
          "that is our gap and it does not count against a provider. An `empty` 200 does not count "
          "as down either - the endpoint answered, even if a reasoning switch was missing.", ""]
    Path(a.out).write_text("\n".join(L) + "\n", encoding="utf-8", newline="\n")

    print("history: %d day(s), %d endpoints" % (span, len(seen)))
    print("  healthy %d | flaky %d | degraded %d | buried %d"
          % (len(healthy), len(flaky), len(degraded), len(buried)))
    for e in buried:
        print("  BURIED  %-12s %s (down since %s)" % (e["provider"], e["model"], e["down_since"]))
    print("wrote %s and data/viability.json" % a.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
