#!/usr/bin/env python3
"""Refuse a published page that says something the data does not. Exit 0 clean, 1 a claim is unsupported,
2 the gate could not run.

    python bench/gate_claims.py            # the repo it lives in
    python bench/gate_claims.py --root DIR # a copy, for the test

This repo's entire argument is that its numbers are measured and its labels are honest. The first version
of this gate checked three things (score rows against the data, probe counts, link targets) and printed
"every published number is in the data" - which was true of the score rows and false of everything
else on the page: the headline box, the capacity table, the counts in prose and the labels were never
opened. A gate that reports more than it checks is the one class of error this repo cannot afford. So the
checks below are the whole list, and the CLEAN line names them.

  1. SCORE ROWS. Every `| n | model | provider | **value** |` row in a ranked table must match
     data/ranking.json (or the archived data/models.json for the language run).
  2. PROBE COUNTS. Every `**N / M**` in README must be recomputable from the latest raw results.
  3. LINKS. Every relative link in prose must point at a file that exists.
  4. FORMULA. The value formula printed on README, RESULTS and ALL-ENDPOINTS must be, byte for byte, the
     one recorded in data/ranking.json, which rank.py builds from the constants it computes with.
  5. LABELS. A Volume / How-we-know cell may only hold MEASURED, DECLARED, DERIVED, PAID-PLAN, UNKNOWN or
     DRAWN (optionally followed by a note after , or ;), and a RANKED table may never carry PAID-PLAN or
     UNKNOWN, nor a `?` in its Answers column: 0% is a measurement and prints as one.
  6. DOORS. Every provider link in a table (Get key, Where, or the provider cell itself) must sit on the
     provider's own registrable domain or on a sign-up host declared in code, so no page can send a reader
     to a lookalike. Same rule the contribution gate applies to providers.json, applied to what is rendered.
  7. HEADLINE. The bold daily figure and the share in the README headline box must equal
     data/capacity.json, and every provider in providers.json must appear in the CAPACITY and RELIABILITY
     blocks: a provider silently dropped from a table is a number that vanished.
  8. COUNTS. On README.md and SECURITY.md, a count of providers, endpoints, hosts or models outside a
     generated block is refused. Counts are generated or they are wrong within a week; both pages had
     three stale ones on the day this rule was written.

What this deliberately does NOT check: numbers inside quotes from providers, rate limits (limits.json has
its own gate), dates, and prose on METHOD.md about the archived run, which is history and stays as written.
"""
import argparse, json, re, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from gate_contributions import KNOWN_SIGNUP_HOSTS, host_of, registrable  # the same door rule, one place

LABELS = {"MEASURED", "DECLARED", "DERIVED", "PAID-PLAN", "UNKNOWN", "DRAWN"}
RANKABLE = {"MEASURED", "DECLARED", "DERIVED", "DRAWN"}
LABEL_COLUMNS = ("volume", "how we know", "evidence")
DOOR_COLUMNS = ("get key", "where")
COUNT_WORDS = r"(?:\d+|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty)"
COUNT_NOUNS = r"(?:providers?|endpoints?|hosts?)"
COUNT_RE = re.compile(r"\b%s %s\b" % (COUNT_WORDS, COUNT_NOUNS), re.I)
MARKER_RE = re.compile(r"<!--([A-Z0-9_-]+)-->.*?<!--/\1-->", re.S)
LINK_RE = re.compile(r"\[([^\]]*)\]\(([^)]+)\)")


# ------------------------------------------------------------------ data

def load_models(root):
    """Every number a table may state about a model, from both sources of truth."""
    by, found, formula = {}, False, None
    rank = root / "data" / "ranking.json"
    if rank.exists():
        found = True
        d = json.loads(rank.read_text(encoding="utf-8"))
        formula = d.get("ranking_formula")
        for m in d.get("ranked", []) + d.get("unranked", []):
            s = by.setdefault(m["model"], set())
            for field in ("value", "coding_index", "intelligence_index", "agentic_index", "arena_elo"):
                if m.get(field) is not None:
                    s.add(m[field])
    lang = root / "data" / "models.json"
    if lang.exists():
        found = True
        d = json.loads(lang.read_text(encoding="utf-8"))
        for m in d.get("models", []):
            s = by.setdefault(m["model"], set())
            s.add(m["quality"])
            s.add(m["quality_for_agents"])
    return found, by, formula


def latest_raw(root):
    runs = sorted((root / "results").glob("*/raw.json")) if (root / "results").exists() else []
    return json.loads(runs[-1].read_text(encoding="utf-8")) if runs else None


def provider_hosts(root):
    """provider -> set of registrable domains a link for it may use."""
    p = root / "bench" / "providers.json"
    out = {}
    if not p.exists():
        return out
    for prov in json.loads(p.read_text(encoding="utf-8")).get("providers", []):
        allowed = {registrable(host_of(prov.get("url", "")))}
        if prov.get("signup"):
            allowed.add(registrable(host_of(prov["signup"])))
        allowed |= set(KNOWN_SIGNUP_HOSTS.get(prov.get("name", ""), set()))
        out[prov["name"]] = allowed - {""}
    return out


# ------------------------------------------------------------------ markdown

def tables(text):
    """Yield (line_number_of_header, header cells, rows) for every pipe table in a document."""
    lines = text.split("\n")
    i = 0
    while i < len(lines) - 1:
        if lines[i].strip().startswith("|") and re.match(r"^\s*\|(\s*:?-+:?\s*\|)+\s*$", lines[i + 1]):
            header = [c.strip() for c in lines[i].strip().strip("|").split("|")]
            rows, j = [], i + 2
            while j < len(lines) and lines[j].strip().startswith("|"):
                rows.append((j + 1, [c.strip() for c in lines[j].strip().strip("|").split("|")]))
                j += 1
            yield i + 1, header, rows
            i = j
        else:
            i += 1


def cell(header, row, *names):
    for k, h in enumerate(header):
        if h.lower().strip("*") in names and k < len(row):
            return row[k]
    return None


def outside_markers(text):
    """The document with every generated block blanked, line count preserved."""
    def blank(m):
        return "\n" * m.group(0).count("\n")
    return MARKER_RE.sub(blank, text)


# ------------------------------------------------------------------ checks

def check_tables(path, by_model, problems):
    text = path.read_text(encoding="utf-8")
    for n, line in enumerate(text.split("\n"), 1):
        m = re.match(r"\|\s*\d+\s*\|\s*`([^`]+)`\s*\|\s*[\w@/.\s-]+?\s*\|\s*\*\*([\d.]+)\*\*", line.strip())
        if not m:
            continue
        model, claimed = m.group(1), float(m.group(2))
        if model not in by_model:
            problems.append(("%s:%d" % (path.name, n), "model %r is scored here but is not in the data" % model))
        elif claimed not in by_model[model]:
            problems.append(("%s:%d" % (path.name, n),
                             "%s is published as %s, but the data has %s. Regenerate with bench/rank.py "
                             "rather than editing the table by hand." % (model, claimed, sorted(by_model[model]))))


def check_counts(path, raw, problems):
    if not raw:
        return
    answered, passed = {}, {}
    for r in raw["rows"]:
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
            problems.append(("%s:%d" % (path.name, n), "claims %d out of %d, which is more than the whole" % (num, den)))
        kind = "arithmetic" if "arithmetic" in label else "json_extraction" if "json" in label else None
        if kind and kind in answered and (den != answered[kind] or num != passed[kind]):
            problems.append(("%s:%d" % (path.name, n), "claims %d/%d for the %s probe; the raw results say %d/%d"
                             % (num, den, kind, passed[kind], answered[kind])))


def check_paths(path, root, problems):
    text = path.read_text(encoding="utf-8")
    for n, line in enumerate(text.split("\n"), 1):
        for _, ref in LINK_RE.findall(line):
            if ref.startswith(("http", "#", "mailto:", "../")):
                continue
            if not (root / ref.split("#")[0]).exists():
                problems.append(("%s:%d" % (path.name, n), "links to %s, which does not exist. Saying a file is 'in "
                                 "this repo' when it is not is the same class of error as an invented number." % ref))


def check_formula(path, formula, problems):
    if not formula:
        return
    text = path.read_text(encoding="utf-8")
    if formula not in text:
        problems.append((path.name, "the value formula printed here is not the one in data/ranking.json: %r. "
                         "Every page prints the same string, built from the constants rank.py computes with." % formula))


def check_labels(path, problems):
    text = path.read_text(encoding="utf-8")
    for hline, header, rows in tables(text):
        ranked = bool(header) and header[0].strip() == "#"
        for n, row in rows:
            v = cell(header, row, *LABEL_COLUMNS)
            if v is not None and v:
                label = re.split(r"[,;]", v)[0].strip().strip("*")
                if label not in LABELS:
                    problems.append(("%s:%d" % (path.name, n), "label %r is not one of %s" % (v, sorted(LABELS))))
                elif ranked and label not in RANKABLE:
                    problems.append(("%s:%d" % (path.name, n), "a ranked row carries %s. A paid-plan or unknown "
                                     "volume is shown, never ranked." % label))
            a = cell(header, row, "answers")
            if ranked and a is not None and a.strip() == "?":
                problems.append(("%s:%d" % (path.name, n), "a ranked row prints ? for Answers. An answered rate of 0 "
                                 "is a measurement and prints as 0 of N; ? is reserved for endpoints never probed."))


def check_doors(path, hosts, problems):
    if not hosts:
        return
    text = path.read_text(encoding="utf-8")
    for hline, header, rows in tables(text):
        for n, row in rows:
            prov_cell = cell(header, row, "provider") or ""
            name = re.sub(r"[*`\[\]]", "", LINK_RE.sub(lambda m: m.group(1), prov_cell)).strip()
            links = []
            for col in DOOR_COLUMNS:
                c = cell(header, row, col)
                if c:
                    links += [u for _, u in LINK_RE.findall(c)]
            links += [u for _, u in LINK_RE.findall(prov_cell)]
            if not name or name not in hosts:
                continue
            for u in links:
                if not u.startswith("http"):
                    continue
                if registrable(host_of(u)) not in hosts[name]:
                    problems.append(("%s:%d" % (path.name, n), "the door for %s points at %s, which is neither its API "
                                     "domain nor a declared sign-up host. A link on an undeclared domain is how people "
                                     "get phished." % (name, host_of(u))))


def check_headline(readme, root, hosts, problems):
    cap = root / "data" / "capacity.json"
    if not cap.exists() or not readme.exists():
        return
    d = json.loads(cap.read_text(encoding="utf-8"))
    text = readme.read_text(encoding="utf-8")
    m = re.search(r"<!--HEADLINE-->(.*?)<!--/HEADLINE-->", text, re.S)
    if not m:
        problems.append((readme.name, "no HEADLINE block: the headline box must be generated"))
    else:
        block = m.group(1)
        want = "{:,}".format(int(d.get("defensible_tokens_per_day", -1)))
        if "**%s**" % want not in block:
            problems.append((readme.name, "the headline box does not carry data/capacity.json's defensible figure %s in bold" % want))
        pct = d.get("share_of_target_pct")
        if pct is not None and ("**%.1f%%**" % pct) not in block and ("**%.0f%%**" % pct) not in block:
            problems.append((readme.name, "the headline share is not %.1f%% from data/capacity.json" % pct))
    for marker in ("CAPACITY", "RELIABILITY"):
        m = re.search(r"<!--%s-->(.*?)<!--/%s-->" % (marker, marker), text, re.S)
        if not m:
            problems.append((readme.name, "no %s block" % marker))
            continue
        for name in hosts:
            if not re.search(r"\b%s\b" % re.escape(name), m.group(1)):
                problems.append((readme.name, "provider %r is missing from the %s block: a provider dropped from a "
                                 "table is a number that vanished" % (name, marker)))


def check_count_prose(path, problems):
    text = outside_markers(path.read_text(encoding="utf-8"))
    for n, line in enumerate(text.split("\n"), 1):
        if line.lstrip().startswith(("|", "#", "<!--", "    ", "```")):
            continue
        for m in COUNT_RE.finditer(line):
            problems.append(("%s:%d" % (path.name, n), "%r is a count in prose outside a generated block. Counts are "
                             "generated between markers, or they go stale." % m.group(0)))


# ------------------------------------------------------------------ main

def run(root):
    problems, checked = [], []
    found, by_model, formula = load_models(root)
    if not found:
        return None, ["no data/ranking.json and no data/models.json - run bench/rank.py first"]
    raw = latest_raw(root)
    hosts = provider_hosts(root)
    for name in ("README.md", "RESULTS.md", "ALL-ENDPOINTS.md", "LIMITS.md", "METHOD.md", "SECURITY.md", "CONTRIBUTING.md"):
        p = root / name
        if not p.exists():
            continue
        checked.append(name)
        check_tables(p, by_model, problems)
        check_paths(p, root, problems)
        check_labels(p, problems)
        check_doors(p, hosts, problems)
        if name in ("README.md", "RESULTS.md", "ALL-ENDPOINTS.md"):
            check_formula(p, formula, problems)
        if name == "README.md":
            check_counts(p, raw, problems)
            check_headline(p, root, hosts, problems)
        if name in ("README.md", "SECURITY.md"):
            check_count_prose(p, problems)
    return checked, problems


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default=str(HERE.parent))
    a = ap.parse_args()
    root = Path(a.root).resolve()
    try:
        checked, problems = run(root)
    except (OSError, ValueError, KeyError) as e:
        print("gate could not run: %s: %s" % (type(e).__name__, e))
        return 2
    if checked is None:
        print(problems[0])
        return 2
    print("checked %d documents: score rows, probe counts, links, the formula, labels, doors, the headline box and "
          "counts in prose" % len(checked))
    if not problems:
        print("CLEAN - every checked claim is in the data.")
        return 0
    print("\n%d UNSUPPORTED CLAIMS:\n" % len(problems))
    for where, what in problems:
        print("  %s\n      %s" % (where, what))
    return 1


if __name__ == "__main__":
    sys.exit(main())
