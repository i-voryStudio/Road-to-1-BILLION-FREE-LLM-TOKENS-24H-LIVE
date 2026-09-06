#!/usr/bin/env python3
"""Re-read the provider catalogues that are public, and record what changed.

No API key needed: these endpoints answer to anybody. It is the cheapest honest thing a list like this
can do daily, and it answers the question every one of these repos gets wrong within a month - is the
model still there?

    python bench/refresh_catalog.py --out data/catalog.json

Writes data/catalog.json and prints a diff against the previous version, so CI can commit it and the
repo carries a dated record of models appearing and disappearing rather than a frozen table.
"""
import argparse, json, sys, urllib.request
from pathlib import Path

UA = {"User-Agent": "free-llm-benchmark/1.0 (+https://github.com/i-voryStudio)"}

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
            free = sorted(m for m in ids if cat["free_filter"](m))
            providers[cat["name"]] = {"total": len(ids), "free": len(free), "free_models": free,
                                      "source": cat["url"]}
            print("%-12s %d models, %d free (%.1f%%)" % (cat["name"], len(ids), len(free),
                                                         100.0 * len(free) / len(ids) if ids else 0))
        except Exception as e:
            problems.append("%s: %s" % (cat["name"], str(e)[:120]))
            print("%-12s FAILED: %s" % (cat["name"], str(e)[:120]))
            if cat["name"] in previous:
                providers[cat["name"]] = previous[cat["name"]]  # keep the last known good, do not blank it

    changes = []
    for name, now in providers.items():
        before = previous.get(name)
        if not before:
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
