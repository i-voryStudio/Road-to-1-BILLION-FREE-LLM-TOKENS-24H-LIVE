#!/usr/bin/env python3
"""Refuse a published number that does not exist in the data. Exit 0 clean, 1 a claim is unsupported.

    python bench/gate_claims.py

This repo's entire argument is that its numbers are measured. That argument dies the first time someone
checks one and it is not there. It nearly did on day one: the README said a model returned "995 words"
when the real maximum in `raw.json` was 381, and claimed two catalogue readings were "in this repo" when
they were not. Both were written from memory while the data sat one directory away.

So prose does not get to state a score. Three checks:

  1. Every `model -> quality` pair in a RESULTS.md or README.md table must match `data/models.json`.
  2. Every `N / M` claim in the README summary table must be recomputable from the raw results.
  3. Every file path referenced in prose must exist.

What this deliberately does NOT check: numbers inside quotes from providers, rate limits (those live in
limits.json with their own provenance), and dates. Widening it further would produce false positives,
and a gate people learn to ignore is worse than no gate.
"""
import io, json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def load_models():
    """Every number a table may state about a model, from BOTH sources of truth.

    data/ranking.json is the main ranking (value, coding_index, quota). data/models.json is the archived
    Romanian language run, still published and still linked, so its scores must stay checkable too. A
    table may quote either; it may invent neither.
    """
    by, found = {}, False
    rank = ROOT / "data" / "ranking.json"
    if rank.exists():
        found = True
        d = json.loads(rank.read_text(encoding="utf-8"))
        for m in d.get("ranked", []) + d.get("unranked", []):
            s = by.setdefault(m["model"], set())
            for field in ("value", "coding_index", "intelligence_index", "agentic_index", "arena_elo"):
                if m.get(field) is not None:
                    s.add(m[field])
    lang = ROOT / "data" / "models.json"
    if lang.exists():
        found = True
        d = json.loads(lang.read_text(encoding="utf-8"))
        for m in d.get("models", []):
            s = by.setdefault(m["model"], set())
            s.add(m["quality"])
            s.add(m["quality_for_agents"])
    return (True if found else None), by


def latest_raw():
    runs = sorted((ROOT / "results").glob("*/raw.json")) if (ROOT / "results").exists() else []
    return json.loads(runs[-1].read_text(encoding="utf-8")) if runs else None


def check_tables(path, by_model, problems):
    """Any table row shaped `| n | `model` | provider | **score** |` must agree with the data."""
    text = path.read_text(encoding="utf-8")
    for n, line in enumerate(text.split("\n"), 1):
        m = re.match(r"\|\s*\d+\s*\|\s*`([^`]+)`\s*\|\s*[\w@/.\s-]+?\s*\|\s*\*\*([\d.]+)\*\*", line.strip())
        if not m:
            continue
        model, claimed = m.group(1), float(m.group(2))
        if model not in by_model:
            problems.append(("%s:%d" % (path.name, n),
                             "model %r is scored here but is not in data/models.json" % model))
        elif claimed not in by_model[model]:
            problems.append(("%s:%d" % (path.name, n),
                             "%s is published as %s, but data/models.json has %s. Regenerate with "
                             "bench/rank.py rather than editing the table by hand."
                             % (model, claimed, sorted(by_model[model]))))


def check_counts(path, raw, problems):
    """`| something | **29 / 30** |` in the README summary must be recomputable from raw results."""
    if not raw:
        return
    rows = raw["rows"]
    answered = {}
    passed = {}
    for r in rows:
        if r["http"] != 200:
            continue
        k = r["kind"]
        answered[k] = answered.get(k, 0) + 1
        passed[k] = passed.get(k, 0) + (1 if r["passed"] else 0)

    text = path.read_text(encoding="utf-8")
    for n, line in enumerate(text.split("\n"), 1):
        m = re.match(r"\|\s*([^|]+?)\s*\|\s*\*\*(\d+)\s*/\s*(\d+)\*\*\s*\|", line.strip())
        if not m:
            continue
        label, num, den = m.group(1).lower(), int(m.group(2)), int(m.group(3))
        if num > den:
            problems.append(("%s:%d" % (path.name, n),
                             "claims %d out of %d, which is more than the whole" % (num, den)))
        # Only the totals we can tie to a probe kind are checked; the rest are left alone on purpose.
        kind = ("arithmetic" if "arithmetic" in label else
                "json_extraction" if "json" in label else None)
        if kind and kind in answered:
            if den != answered[kind] or num != passed[kind]:
                problems.append(("%s:%d" % (path.name, n),
                                 "claims %d/%d for the %s probe; the raw results say %d/%d"
                                 % (num, den, kind, passed[kind], answered[kind])))


def check_paths(path, problems):
    text = path.read_text(encoding="utf-8")
    for n, line in enumerate(text.split("\n"), 1):
        for ref in re.findall(r"\]\(([^)]+)\)", line):
            if ref.startswith(("http", "#", "mailto:", "../")):
                continue
            target = ROOT / ref.split("#")[0]
            if not target.exists():
                problems.append(("%s:%d" % (path.name, n),
                                 "links to %s, which does not exist. Saying a file is 'in this repo' "
                                 "when it is not is the same class of error as an invented number."
                                 % ref))


def main():
    data, by_model = load_models()
    if data is None:
        print("no data/ranking.json and no data/models.json - run bench/rank.py first")
        return 2
    raw = latest_raw()
    problems = []
    checked = []
    for name in ("README.md", "RESULTS.md", "METHOD.md", "IMPROVEMENTS.md", "SECURITY.md",
                 "CONTRIBUTING.md", "LIMITS.md"):
        p = ROOT / name
        if not p.exists():
            continue
        checked.append(name)
        check_tables(p, by_model, problems)
        check_paths(p, problems)
        if name == "README.md":
            check_counts(p, raw, problems)

    print("checked %d documents against %d scored models%s"
          % (len(checked), len(by_model), " and the latest raw results" if raw else " (no raw results found)"))
    if not problems:
        print("CLEAN - every published number is in the data.")
        return 0
    print("\n%d UNSUPPORTED CLAIMS:\n" % len(problems))
    for where, what in problems:
        print("  %s\n      %s" % (where, what))
    return 1


if __name__ == "__main__":
    sys.exit(main())
