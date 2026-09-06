#!/usr/bin/env python3
"""Re-read the provider catalogues that are public, and record what changed.

No API key needed: these endpoints answer to anybody. It is the cheapest honest thing a list like this
can do daily, and it answers the question every one of these repos gets wrong within a month - is the
model still there?

    python bench/refresh_catalog.py --out data/catalog.json

Writes data/catalog.json and prints a diff against the previous version, so CI can commit it and the
repo carries a dated record of models appearing and disappearing rather than a frozen table.
"""
import argparse, json, re, sys, urllib.request
from pathlib import Path

UA = {"User-Agent": "free-llm-benchmark/1.0 (+https://github.com/i-voryStudio)"}

MAX_IDS = 5000            # a catalogue bigger than this is a provider fault, not news
# Calibrated against all 430 ids OpenRouter served on 2026-09-06, not guessed: the only non-alphanumeric
# characters in use are / - : . and ~, and ~ appears only as a leading character on "latest" aliases
# (~z-ai/glm-latest). Longest id measured: 56 characters. The guard still rejects whitespace, control
# characters, backslashes and path traversal, which is the point of having it.
ID_OK = re.compile(r"^[A-Za-z0-9~][A-Za-z0-9._/:~+-]{0,119}$")

# Only endpoints that answer without authentication belong here.
CATALOGS = [
    {"name": "openrouter", "url": "https://openrouter.ai/api/v1/models",
     "extract": lambda d: [m["id"] for m in d.get("data", [])],
     "free_filter": lambda mid: mid.endswith(":free")},
]


def fetch(url, timeout=60):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as f:
        return json.load(f)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default="data/catalog.json")
    ap.add_argument("--date", required=True, help="YYYY-MM-DD, passed in so the output is reproducible")
    a = ap.parse_args()

    out_path = Path(a.out)
    previous = {}
    if out_path.exists():
        try:
            previous = json.loads(out_path.read_text(encoding="utf-8")).get("providers", {})
        except Exception:
            previous = {}

    providers, problems = {}, []
    for cat in CATALOGS:
        try:
            data = fetch(cat["url"])
            ids = sorted(cat["extract"](data))
            # A 200 that parses is not the same as an answer. A provider mid-deploy, an empty cache or a
            # partial edge response all return {"data": []}, and believing it would commit "everything
            # disappeared" to a public history that exists to be trustworthy. Two guards:
            if not ids:
                raise ValueError("returned 200 with an empty model list, which is a provider fault, not news")
            if len(ids) > MAX_IDS:
                raise ValueError("returned %d models, over the sanity ceiling of %d" % (len(ids), MAX_IDS))
            bad = [m for m in ids if not ID_OK.match(m)]
            if bad:
                raise ValueError("%d model ids have an unexpected shape, first: %r" % (len(bad), bad[0][:60]))
            before = previous.get(cat["name"], {})
            if before.get("total") and len(ids) < before["total"] * 0.5:
                # Halving is possible but far more often means a partial response. Record it, do not act.
                problems.append("%s: model count fell from %d to %d, over 50%%. Recorded as suspect and "
                                "NOT treated as models disappearing." % (cat["name"], before["total"], len(ids)))
                providers[cat["name"]] = dict(before, suspect=True, suspect_on=a.date,
                                              suspect_total=len(ids))
                print("%-12s SUSPECT: %d -> %d models, keeping previous" % (cat["name"], before["total"], len(ids)))
                continue
            free = sorted(m for m in ids if cat["free_filter"](m))
            providers[cat["name"]] = {"total": len(ids), "free": len(free), "free_models": free,
                                      "source": cat["url"], "fetched_on": a.date, "stale": False}
            print("%-12s %d models, %d free (%.1f%%)" % (cat["name"], len(ids), len(free),
                                                         100.0 * len(free) / len(ids) if ids else 0))
        except Exception as e:
            problems.append("%s: %s" % (cat["name"], str(e)[:160]))
            print("%-12s FAILED: %s" % (cat["name"], str(e)[:160]))
            if cat["name"] in previous:
                # Keep the last known good and MARK it stale, so a reader can tell a fresh reading from
                # a frozen one. Blanking it would publish a false disappearance.
                providers[cat["name"]] = dict(previous[cat["name"]], stale=True, stale_since=a.date)

    changes = []
    for name, now in providers.items():
        before = previous.get(name)
        # Only compare two readings we actually trust. A stale or suspect entry is last week's data
        # wearing today's date, and diffing it would invent appearances and disappearances.
        if not before or now.get("stale") or now.get("suspect") or before.get("stale"):
            continue
        gone = sorted(set(before.get("free_models", [])) - set(now.get("free_models", [])))
        new = sorted(set(now.get("free_models", [])) - set(before.get("free_models", [])))
        for m in gone:
            changes.append({"provider": name, "model": m, "change": "disappeared"})
        for m in new:
            changes.append({"provider": name, "model": m, "change": "appeared"})

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps({"checked_on": a.date, "providers": providers,
                                    "changes_since_last_check": changes,
                                    "problems": problems}, indent=1) + "\n",
                        encoding="utf-8", newline="\n")

    if changes:
        print("\n%d changes since the last check:" % len(changes))
        for c in changes:
            print("  %-12s %-8s %s" % (c["provider"], c["change"], c["model"]))
    else:
        print("\nno changes since the last check")
    print("wrote %s" % out_path)
    return 0 if not problems else 0  # a provider being down is news, not a build failure


if __name__ == "__main__":
    sys.exit(main())
