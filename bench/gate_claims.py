#!/usr/bin/env python3
"""Refuse a published page that says something the data does not. Exit 0 clean, 1 a claim is unsupported,
2 the gate could not run.

    python bench/gate_claims.py               # the repo it lives in
    python bench/gate_claims.py --root DIR    # a copy, for the test
    python bench/gate_claims.py --list-pages  # the pages it opens, one per line, for CI to compare with ls

This repo's entire argument is that its numbers are measured and its labels are honest. The first version
of this gate checked three things (score rows against the data, probe counts, link targets) and printed
"every published number is in the data" - which was true of the score rows and false of everything
else on the page. The second version checked eight things on seven named pages and was green on three
shapes it never looked at: a count of "models" (the docstring promised it, the regex did not), an
invented <!--X--> marker (any block was blanked from the count check, and the generator only rewrites
markers it knows, so an invented one survived regeneration with a hand-typed number inside), and any
page outside the seven (a new BEST.md with a fake score row and a lookalike door was never opened). A
gate that reports more than it checks is the one class of error this repo cannot afford. So the checks
below are the whole list, the CLEAN line names them, and the page list is every *.md at the root plus
the language-pack README, not a list typed here.

  1. SCORE ROWS. Every `| n | model | provider | **value** |` row in a ranked table must match
     data/ranking.json (or the archived data/models.json for the language run).
  2. PROBE COUNTS. Every `| arithmetic or json probe | **N / M** |` row must be recomputable from the
     latest raw results.
  3. LINKS. Every relative link must point at a file that exists, resolved from the page's own folder.
  4. FORMULA. The value formula printed on README, RESULTS and ALL-ENDPOINTS must be, byte for byte, the
     one recorded in data/ranking.json, which rank.py builds from the constants it computes with. The
     other pages do not print it, so the check does not apply to them.
  5. LABELS. A Volume / How-we-know cell may only hold MEASURED, DECLARED, DERIVED, PAID-PLAN, UNKNOWN or
     DRAWN (optionally followed by a note after , or ;), and a RANKED table may never carry PAID-PLAN or
     UNKNOWN, nor a `?` in its Answers column: 0% is a measurement and prints as one.
  6. DOORS. In any table with a Provider column, on any page, the provider must be one bench/providers.json
     knows, and every link in the row must sit on the provider's own registrable domain or on a sign-up or
     terms host declared in code, so no page can send a reader to a lookalike. Same rule the contribution
     gate applies to providers.json, applied to what is rendered.
  7. HEADLINE. The bold daily figure and the share in the README headline box must equal
     data/capacity.json, and every provider in providers.json must appear in the CAPACITY and RELIABILITY
     blocks: a provider silently dropped from a table is a number that vanished.
  8. COUNTS. A count of providers, endpoints, hosts, models or keys in prose, outside a generated block,
     is refused. Counts are generated or they are wrong within a week. Two pages are exempt, and only for
     this check: METHOD.md, whose prose describes the archived language run and is history that stays as
     written; and the pages the generator writes whole (GENERATED_PAGES), where the entire file is the
     generated block and CI's regeneration step, not this one, is what refuses a hand edit.
  9. MARKERS. A `<!--X-->` block is recognised only if X is a marker the generator writes on that page
     (read from rank.py itself, so the two cannot drift) or the one declared hand-typed block on
     SOURCES.md. Any other marker is refused as an unknown generated block, and nothing inside it is
     blanked from the count check.
 10. SOURCES. Star counts and a hand-counted "N for N" on SOURCES.md are hand-typed numbers that age by
     the day. They are allowed only inside the <!--SOURCES-TABLE--> block, which declares them as a dated
     snapshot; outside it they are refused.

What this deliberately does NOT check: numbers inside quotes from providers, rate limits (limits.json has
its own gate), dates, and the archived-run prose on METHOD.md.
"""
import argparse, json, re, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from gate_contributions import KNOWN_SIGNUP_HOSTS, KNOWN_TERMS_HOSTS, host_of, registrable  # one door rule, one place

LABELS = {"MEASURED", "DECLARED", "DERIVED", "PAID-PLAN", "UNKNOWN", "DRAWN"}
RANKABLE = {"MEASURED", "DECLARED", "DERIVED", "DRAWN"}
LABEL_COLUMNS = ("volume", "how we know", "evidence")
FORMULA_PAGES = ("README.md", "RESULTS.md", "ALL-ENDPOINTS.md")   # the pages that print the value formula
# Pages rank.py (and gate_viability.py for GRAVEYARD.md) write in full. The whole file is the generated
# block, so the count-in-prose check does not apply; a hand edit to one of these is refused by CI's
# regeneration step (rank.py at the committed date, then git diff --exit-code). test_claims.py asserts each
# of these names is a string literal in the generator that writes it, so this set cannot hold a hand-written page.
GENERATED_PAGES = {"RESULTS.md", "ALL-ENDPOINTS.md", "LIMITS.md", "GRAVEYARD.md"}
# METHOD.md describes the archived Romanian run ("four models", "two judges"). That is history, and history
# does not go stale, so it keeps its counts. Every other page at the root is checked.
COUNT_EXEMPT_PAGES = {"METHOD.md"} | GENERATED_PAGES
SOURCES_MARKER = "SOURCES-TABLE"       # the one hand-typed block, allowed on SOURCES.md only
EXTRA_PAGES = ("bench/languages/README.md",)

COUNT_WORDS = (r"(?:\d[\d,]*\+?|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|"
               r"fifteen|sixteen|seventeen|eighteen|nineteen|twenty|thirty|forty|fifty)")
COUNT_NOUNS = r"(?:providers?|endpoints?|hosts?|models?|keys?)"
COUNT_RE = re.compile(r"\b%s (?:[a-z-]+ )?%s\b" % (COUNT_WORDS, COUNT_NOUNS), re.I)   # "12 free providers" too
STARS_RE = re.compile(r"\b\d[\d,.]*\s*k?\s+stars?\b", re.I)
N_FOR_N_RE = re.compile(r"\b(one|two|three|four|five|six|seven|eight|nine|ten|\d+) for (one|two|three|four|five|"
                        r"six|seven|eight|nine|ten|\d+)\b", re.I)
MARKER_RE = re.compile(r"<!--([A-Z0-9_-]+)-->.*?<!--/\1-->", re.S)
MARKER_TAG_RE = re.compile(r"<!--(/?)([A-Z0-9_-]+)-->")
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
    """provider -> set of registrable domains a link for it may use: its API host, its sign-up host, and
    the sign-up and terms hosts declared in code by the contribution gate."""
    p = root / "bench" / "providers.json"
    out = {}
    if not p.exists():
        return out
    for prov in json.loads(p.read_text(encoding="utf-8")).get("providers", []):
        allowed = {registrable(host_of(prov.get("url", "")))}
        if prov.get("signup"):
            allowed.add(registrable(host_of(prov["signup"])))
        allowed |= set(KNOWN_SIGNUP_HOSTS.get(prov.get("name", ""), set()))
        allowed |= set(KNOWN_TERMS_HOSTS.get(prov.get("name", ""), set()))
        out[prov["name"]] = allowed - {""}
    return out


def known_markers(root):
    """The marker names the generator writes into README.md, read from rank.py itself.

    rank.py rewrites a block only if it knows the marker, so a marker it does not know is a block nobody
    regenerates: exactly where a hand-typed number would hide. If rank.py ever exposes the list as
    MARKERS, that wins; until then the put("NAME", ...) calls in its source are the list. An empty result
    makes every README marker unknown and the gate loud, which is the right direction to fail in.
    """
    try:
        import rank  # noqa: F401  (the copy under test shares HERE's sys.path; the source below is root's)
        if hasattr(rank, "MARKERS"):
            return set(rank.MARKERS)
    except Exception:
        pass
    src = root / "bench" / "rank.py"
    if not src.exists():
        return set()
    return set(re.findall(r'put\("([A-Z0-9_-]+)"', src.read_text(encoding="utf-8")))


def page_markers(root):
    """page name -> the markers that may appear on it. Anything else is an unknown generated block."""
    return {"README.md": known_markers(root), "SOURCES.md": {SOURCES_MARKER}}


def pages(root):
    """Every *.md at the root, plus the language-pack README. Computed, never typed."""
    out = sorted(p for p in root.glob("*.md") if p.is_file())
    for rel in EXTRA_PAGES:
        p = root / rel
        if p.exists():
            out.append(p)
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


def has_column(header, *names):
    return any(h.lower().strip("*") in names for h in header)


def outside_markers(text, allowed):
    """The document with every KNOWN generated block blanked, line count preserved. An unknown block is
    left in place, so whatever it hides is still read."""
    def blank(m):
        if m.group(1) not in allowed:
            return m.group(0)
        return "\n" * m.group(0).count("\n")
    return MARKER_RE.sub(blank, text)


_ROOT = None      # set by run(); where() prints paths relative to it, so two files called README.md stay apart


def where(path, n=None):
    rel = path.relative_to(_ROOT).as_posix() if _ROOT else path.name
    return rel if n is None else "%s:%d" % (rel, n)


def paragraphs(text):
    """Yield (first line number, paragraph joined on one line) for prose only. Tables, headings, comments,
    indented and fenced code are skipped and end a paragraph. Joining is what lets a count wrapped over a
    line break ("350+" at the end of one line, "providers" at the start of the next) still be read."""
    buf, start, fenced = [], None, False
    for n, line in enumerate(text.split("\n"), 1):
        s = line.lstrip()
        if s.startswith("```"):
            fenced = not fenced
        skip = fenced or not s or s.startswith(("|", "#", "<!--", "    ", "```"))
        if skip:
            if buf:
                yield start, " ".join(buf)
            buf, start = [], None
            continue
        if start is None:
            start = n
        buf.append(s)
    if buf:
        yield start, " ".join(buf)


# ------------------------------------------------------------------ checks

def check_tables(path, by_model, problems):
    text = path.read_text(encoding="utf-8")
    for n, line in enumerate(text.split("\n"), 1):
        m = re.match(r"\|\s*\d+\s*\|\s*`([^`]+)`\s*\|\s*[\w@/.\s-]+?\s*\|\s*\*\*([\d.]+)\*\*", line.strip())
        if not m:
            continue
        model, claimed = m.group(1), float(m.group(2))
        if model not in by_model:
            problems.append((where(path, n), "model %r is scored here but is not in the data" % model))
        elif claimed not in by_model[model]:
            problems.append((where(path, n),
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
            problems.append((where(path, n), "claims %d out of %d, which is more than the whole" % (num, den)))
        kind = "arithmetic" if "arithmetic" in label else "json_extraction" if "json" in label else None
        if kind and kind in answered and (den != answered[kind] or num != passed[kind]):
            problems.append((where(path, n), "claims %d/%d for the %s probe; the raw results say %d/%d"
                             % (num, den, kind, passed[kind], answered[kind])))


def check_paths(path, root, problems):
    text = path.read_text(encoding="utf-8")
    for n, line in enumerate(text.split("\n"), 1):
        for _, ref in LINK_RE.findall(line):
            if ref.startswith(("http", "#", "mailto:")):
                continue
            target = (path.parent / ref.split("#")[0]).resolve()
            try:
                target.relative_to(root)
            except ValueError:
                continue        # points outside the tree (GitHub's own ../../security/... URLs): not ours to check
            if not target.exists():
                problems.append((where(path, n), "links to %s, which does not exist. Saying a file is 'in "
                                 "this repo' when it is not is the same class of error as an invented number." % ref))


def check_formula(path, formula, problems):
    if not formula:
        return
    text = path.read_text(encoding="utf-8")
    if formula not in text:
        problems.append((where(path), "the value formula printed here is not the one in data/ranking.json: %r. "
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
                    problems.append((where(path, n), "label %r is not one of %s" % (v, sorted(LABELS))))
                elif ranked and label not in RANKABLE:
                    problems.append((where(path, n), "a ranked row carries %s. A paid-plan or unknown "
                                     "volume is shown, never ranked." % label))
            a = cell(header, row, "answers")
            if ranked and a is not None and a.strip() == "?":
                problems.append((where(path, n), "a ranked row prints ? for Answers. An answered rate of 0 "
                                 "is a measurement and prints as 0 of N; ? is reserved for endpoints never probed."))


def check_doors(path, hosts, problems):
    """Every table with a Provider column, every link in the row, every page."""
    if not hosts:
        return
    text = path.read_text(encoding="utf-8")
    for hline, header, rows in tables(text):
        if not has_column(header, "provider"):
            continue
        for n, row in rows:
            prov_cell = cell(header, row, "provider") or ""
            name = re.sub(r"[*`\[\]]", "", LINK_RE.sub(lambda m: m.group(1), prov_cell)).strip()
            if not name:
                continue
            if name not in hosts:
                problems.append((where(path, n), "provider %r appears in a table but is not in bench/providers.json. "
                                 "A page may only name providers the contribution gate has admitted; a row for a "
                                 "provider nobody vetted is a door nobody checked." % name))
                continue
            for c in row:
                for _, u in LINK_RE.findall(c):
                    if not u.startswith("http"):
                        continue
                    if registrable(host_of(u)) not in hosts[name]:
                        problems.append((where(path, n), "the door for %s points at %s, which is neither its API "
                                         "domain nor a declared sign-up or terms host. A link on an undeclared "
                                         "domain is how people get phished." % (name, host_of(u))))


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


def check_markers(path, allowed, problems):
    """Every <!--X--> tag on the page must be a marker the generator writes here, or the declared
    hand-typed block. An invented one is refused, not blanked: the generator would never rewrite it, so a
    number inside it would outlive every regeneration."""
    text = path.read_text(encoding="utf-8")
    for n, line in enumerate(text.split("\n"), 1):
        for closing, name in MARKER_TAG_RE.findall(line):
            if name not in allowed:
                problems.append((where(path, n), "<!--%s%s--> is not a generated block on this page (the generator writes "
                                 "%s here). An unknown marker survives regeneration untouched, so it is refused as an "
                                 "unknown generated block and nothing inside it is exempt from the checks below."
                                 % (closing, name, ", ".join(sorted(allowed)) or "nothing")))


def check_count_prose(path, allowed, problems):
    text = outside_markers(path.read_text(encoding="utf-8"), allowed)
    for n, para in paragraphs(text):
        for m in COUNT_RE.finditer(para):
            problems.append((where(path, n), "%r is a count in prose outside a generated block. Counts are "
                             "generated between markers, or they go stale." % m.group(0)))


def check_sources(path, problems):
    """Star counts and a hand-counted 'N for N' are allowed only inside the <!--SOURCES-TABLE--> block."""
    text = outside_markers(path.read_text(encoding="utf-8"), {SOURCES_MARKER})
    for hline, header, rows in tables(text):
        if has_column(header, "stars"):
            problems.append((where(path, hline), "a table with a Stars column sits outside the <!--%s--> block. Star "
                             "counts are hand-typed and age by the day; they are shown only inside the block that "
                             "declares them as a dated snapshot." % SOURCES_MARKER))
    for n, para in paragraphs(text):
        for m in STARS_RE.finditer(para):
            problems.append((where(path, n), "%r is a hand-typed star count outside the <!--%s--> block." % (m.group(0), SOURCES_MARKER)))
        for m in N_FOR_N_RE.finditer(para):
            problems.append((where(path, n), "%r is a hand-counted score outside the <!--%s--> block. It was true "
                             "on the day it was typed and nothing re-counts it." % (m.group(0), SOURCES_MARKER)))


# ------------------------------------------------------------------ main

def run(root):
    global _ROOT
    _ROOT = root
    problems, checked = [], []
    found, by_model, formula = load_models(root)
    if not found:
        return None, ["no data/ranking.json and no data/models.json - run bench/rank.py first"]
    raw = latest_raw(root)
    hosts = provider_hosts(root)
    markers = page_markers(root)
    for p in pages(root):
        rel = p.relative_to(root).as_posix()      # "README.md" and "bench/languages/README.md" are different pages
        allowed = markers.get(rel, set())
        checked.append(rel)
        check_tables(p, by_model, problems)
        check_counts(p, raw, problems)
        check_paths(p, root, problems)
        check_labels(p, problems)
        check_doors(p, hosts, problems)
        check_markers(p, allowed, problems)
        if rel in FORMULA_PAGES:
            check_formula(p, formula, problems)
        if rel == "README.md":
            check_headline(p, root, hosts, problems)
        if rel not in COUNT_EXEMPT_PAGES:
            check_count_prose(p, allowed, problems)
        if rel == "SOURCES.md":
            check_sources(p, problems)
    return checked, problems


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default=str(HERE.parent))
    ap.add_argument("--list-pages", action="store_true", help="print the pages this gate opens and exit")
    a = ap.parse_args()
    root = Path(a.root).resolve()
    if a.list_pages:
        for p in pages(root):
            print(p.relative_to(root).as_posix())
        return 0
    try:
        checked, problems = run(root)
    except (OSError, ValueError, KeyError) as e:
        print("gate could not run: %s: %s" % (type(e).__name__, e))
        return 2
    if checked is None:
        print(problems[0])
        return 2
    print("checked %d documents (%s): score rows, probe counts, links, the formula, labels, doors, the headline "
          "box, counts in prose, generated-block markers and the hand-typed numbers on SOURCES.md"
          % (len(checked), ", ".join(checked)))
    if not problems:
        print("CLEAN - every checked claim is in the data.")
        return 0
    print("\n%d UNSUPPORTED CLAIMS:\n" % len(problems))
    for where_, what in problems:
        print("  %s\n      %s" % (where_, what))
    return 1


if __name__ == "__main__":
    sys.exit(main())
