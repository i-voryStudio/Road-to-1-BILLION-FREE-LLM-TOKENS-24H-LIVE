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
shapes it never looked at. The third opened every *.md at the root and was green on four more: a
bench/README.md with a fake ranking and a lookalike door (never opened); a door written as an HTML
anchor, a reference-style link or a prose link (only `[text](url)` inside a table with a column called
Provider was read); a fake value beside a provider cell that was a link (the score regex wanted plain
text); and a probe-count check announced on the CLEAN line that had not matched a row on any page in
weeks. A gate that reports more than it checks is the one class of error this repo cannot afford. So the
checks below are the whole list, the CLEAN line names them with the number of items each one verified
and drops any that verified nothing, and the page list is every markdown file git knows about in the
tree, not a list typed here.

WHAT IT OPENS. Every *.md that `git ls-files` reports, tracked or new and not ignored (a walk that skips
what .gitignore names when git is absent), minus the generator's golden blocks under
bench/tests/fixture/golden/: those are rank.py's own output on the fixture, compared byte for byte by
test_rank.py, and they describe five invented providers, so they are blocks, not pages. --list-pages
prints exactly what run() opens. Two pages are written by the generator in full (RESULTS.md,
ALL-ENDPOINTS.md, LIMITS.md by rank.py; GRAVEYARD.md by gate_viability.py) and README.md is written
between <!--MARKER--> blocks; everything else is prose somebody typed.

WHAT IT CHECKS, on every page it opens:
  1. SCORE FIGURES. In any table row that names a model and a provider, every figure under a Value,
     Coding, Intelligence, Agentic, Arena, Tokens/day or Req/day column must equal what data/ranking.json
     holds for THAT provider and model (data/models.json for the archived language run). The provider
     cell may be plain, bold or a link; a row for a pair the data does not have is refused; a row with a
     model and no provider is refused unless every bold figure in it belongs to that model somewhere.
  2. ANSWER CELLS. Every "N of M" under an Answers column must be the radar's own count for that
     provider and model (radar_probes in data/ranking.json); every "N of M" in a per-provider table
     (the RELIABILITY block) must be the sum of its endpoints' counts. N may not exceed M.
  3. RANKED ORDER. A table whose first column is # is numbered 1..n and sorted by the bold value,
     descending. A re-ordered table is a claim the data does not make.
  4. LINKS. Every relative link, in any form (inline, reference-style, autolink, HTML anchor), must point
     at a file that exists, resolved from the page's own folder.
  5. LABELS. A Volume / How-we-know cell may only hold a label from rank.py's LABELS (optionally followed
     by a note after , or ;), and a RANKED table may only carry rank.py's RANKABLE labels: PAID-PLAN,
     UNKNOWN and DRAWN are shown and never ranked (DRAWN sits on the daily shelf, one figure per provider,
     which sums rank.py's SUMMABLE; it is never a row's figure). A ranked row may not print ? for
     Answers: 0% is a measurement and prints as one.
  6. DOORS. Every link on the page, in tables and in prose, in every form: in a table with a Provider
     column the provider must be one bench/providers.json knows and every link in the row must sit on
     that provider's registrable domain, its sign-up host, or a sign-up or terms host declared in code;
     everywhere else, a link whose visible text (or the key-talk right before it) names a provider must
     sit on that provider's hosts, and a link that says get a key / sign up, or whose path does, must be
     a declared door of some provider. Host maps and helpers come from gate_contributions.py, so the
     rule the contribution gate applies to providers.json is applied to what is rendered.
  7. PROVENANCE. A ranking-shaped table (# / Model / Value, or Model / Provider / Value) or a door may
     only appear on a page the generator writes: RESULTS.md, ALL-ENDPOINTS.md, LIMITS.md, GRAVEYARD.md,
     or inside a generated block on README.md. Anywhere else it is a page that looks generated and is
     not, and it is refused whatever its numbers say.
  8. FORMULA. The value formula printed on README, RESULTS and ALL-ENDPOINTS must be, byte for byte, the
     one recorded in data/ranking.json, which rank.py builds from the constants it computes with.
  9. HEADLINE. The bold daily figure and the share in the README headline box must equal
     data/capacity.json, and every provider in providers.json must appear in the CAPACITY and RELIABILITY
     blocks: a provider silently dropped from a table is a number that vanished.
 10. MARKERS. A `<!--X-->` block is recognised only if X is a marker rank.py writes (its MARKERS, read
     from the module) on README.md, or the one declared hand-typed block on SOURCES.md. Any other marker
     on any page is refused as an unknown generated block, and nothing inside it is blanked from the
     count check.
 11. COUNTS IN PROSE. A count of providers, endpoints, hosts, models or keys in prose, outside a
     generated block, is refused. Counts are generated or they are wrong within a week. Exempt, and only
     from this check: the generated pages (the whole file is the generated block and CI's regeneration
     step refuses a hand edit), METHOD.md and the dated run folders under results/, whose prose is
     history and history keeps its counts.
 12. SOURCES. Star counts and a hand-counted "N for N" on SOURCES.md are hand-typed numbers that age by
     the day. They are allowed only inside the <!--SOURCES-TABLE--> block, which declares them as a dated
     snapshot; outside it they are refused.

What this deliberately does NOT check: numbers inside quotes from providers, rate limits (limits.json has
its own gate), dates, the figures in the CAPACITY table and the ROAD paragraph other than the headline
(test_shelf.py recomputes those from the raw files), and the archived-run prose on METHOD.md.
"""
import argparse, json, os, re, subprocess, sys
from pathlib import Path, PurePosixPath
from urllib.parse import urlparse

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from gate_contributions import KNOWN_SIGNUP_HOSTS, KNOWN_TERMS_HOSTS, host_of, hosts_of, registrable  # one door rule, one place
import rank as _rank                                               # one label vocabulary, one marker list, one place

LABELS = set(_rank.LABELS)          # rank.py keeps the legend text; the gate needs the names
RANKABLE = set(_rank.RANKABLE)      # a row is ranked on these
SUMMABLE = set(_rank.SUMMABLE)      # the daily shelf sums these; DRAWN is here and not in RANKABLE
MARKERS = set(_rank.MARKERS)        # every block rank.py writes into README.md
LABEL_COLUMNS = ("volume", "how we know", "evidence")
PROVIDER_COLUMNS = ("provider", "vendor", "host", "service")
FORMULA_PAGES = ("README.md", "RESULTS.md", "ALL-ENDPOINTS.md")   # the pages that print the value formula
# Pages rank.py (and gate_viability.py for GRAVEYARD.md) write in full. The whole file is the generated
# block, so the count-in-prose check does not apply; a hand edit to one of these is refused by CI's
# regeneration step (rank.py at the committed date, then git diff --exit-code). test_claims.py asserts each
# of these names is a string literal in the generator that writes it, so this set cannot hold a hand-written page.
GENERATED_PAGES = {"RESULTS.md", "ALL-ENDPOINTS.md", "LIMITS.md", "GRAVEYARD.md"}
# METHOD.md describes the archived Romanian run ("four models", "two judges"). That is history, and history
# does not go stale, so it keeps its counts. So do the dated run folders under ARCHIVE_DIR.
COUNT_EXEMPT_PAGES = {"METHOD.md"} | GENERATED_PAGES
ARCHIVE_DIR = "results"
SOURCES_MARKER = "SOURCES-TABLE"       # the one hand-typed block, allowed on SOURCES.md only
# rank.py's output on the fixture, compared byte for byte by test_rank.py (its GOLD constant; test_claims.py
# asserts the two paths agree). A file there whose stem is a MARKER is a generated block, not a page.
GOLDEN_DIR = "bench/tests/fixture/golden"
# Table column -> the field in data/ranking.json (or data/models.json) it prints.
COLUMN_FIELDS = {"value": "value", "coding": "coding_index", "intelligence": "intelligence_index",
                 "agentic": "agentic_index", "arena": "arena_elo", "arena elo": "arena_elo",
                 "tokens/day": "daily_tokens", "req/day": "requests_per_day", "requests/day": "requests_per_day",
                 "quality": "quality", "quality for agents": "quality_for_agents"}
FACT_FIELDS = ("value", "coding_index", "intelligence_index", "agentic_index", "arena_elo", "daily_tokens",
               "requests_per_day", "radar_probes")

COUNT_WORDS = (r"(?:\d[\d,]*\+?|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|"
               r"fifteen|sixteen|seventeen|eighteen|nineteen|twenty|thirty|forty|fifty)")
COUNT_NOUNS = r"(?:providers?|endpoints?|hosts?|models?|keys?)"
COUNT_RE = re.compile(r"\b%s (?:[a-z-]+ )?%s\b" % (COUNT_WORDS, COUNT_NOUNS), re.I)   # "12 free providers" too
STARS_RE = re.compile(r"\b\d[\d,.]*\s*k?\s+stars?\b", re.I)
N_FOR_N_RE = re.compile(r"\b(one|two|three|four|five|six|seven|eight|nine|ten|\d+) for (one|two|three|four|five|"
                        r"six|seven|eight|nine|ten|\d+)\b", re.I)
MARKER_RE = re.compile(r"<!--([A-Z0-9_-]+)-->.*?<!--/\1-->", re.S)
MARKER_TAG_RE = re.compile(r"<!--(/?)([A-Z0-9_-]+)-->")
# Every way a link is written on GitHub. Images count: a badge's alt text is what a reader sees.
INLINE_LINK_RE = re.compile(r"!?\[([^\]]*)\]\(\s*<?([^\s)>]+)>?(?:\s+(?:\"[^\"]*\"|'[^']*'))?\s*\)")
REF_LINK_RE = re.compile(r"!?\[([^\]]+)\]\[([^\]]*)\]")
REF_DEF_RE = re.compile(r"^\s{0,3}\[([^\]]+)\]:\s*<?(\S+?)>?(?:\s+(?:\"[^\"]*\"|'[^']*'|\([^)]*\)))?\s*$", re.M)
AUTOLINK_RE = re.compile(r"<((?:https?|mailto):[^>\s]+)>")
HTML_A_RE = re.compile(r"<a\b[^>]*?\bhref\s*=\s*(?:\"([^\"]*)\"|'([^']*)'|([^\s>]+))[^>]*>(.*?)</a>", re.I | re.S)
BARE_URL_RE = re.compile(r"(?<![\w\[(<\"'=/])https?://[^\s<>)\]\"'`]+")
MODEL_CELL_RE = re.compile(r"^`([^`]+)`$")
FIGURE_RE = re.compile(r"^\**(-?\d[\d,]*(?:\.\d+)?)\**(?:$|[\s(])")
N_OF_M_RE = re.compile(r"^\**(\d+) of (\d+)\b")
# Key-talk: "get a key", "get your Groq key", "create an API key", "sign up", "API keys". Up to three words
# may sit between the verb and "key", which is where a provider's name goes.
KEYISH_TEXT_RE = re.compile(r"\b(?:(?:get|grab|create|generate|obtain) (?:[\w']+ ){0,3}keys?|api[ -]?keys?|sign[ -]?up|"
                            r"register)\b", re.I)
KEYISH_URL_RE = re.compile(r"api[-_]?keys?|apikey|/keys?(?:/|$)|api[-_]?tokens?|sign[-_]?up|register", re.I)
CONTEXT_CHARS = 100        # how far before a prose link the key-talk that binds it may start


# ------------------------------------------------------------------ data

def load_models(root):
    """facts[(provider, model)] = every field a table may print for that endpoint; by_model[model] = every
    figure any table may state about the model, whichever provider serves it (the fallback for a row that
    names no provider). Both sources of truth."""
    facts, by_model, found, formula = {}, {}, False, None
    rank_json = root / "data" / "ranking.json"
    if rank_json.exists():
        found = True
        d = json.loads(rank_json.read_text(encoding="utf-8"))
        formula = d.get("ranking_formula")
        for m in d.get("ranked", []) + d.get("unranked", []):
            f = facts.setdefault((m.get("provider"), m["model"]), {})
            for field in FACT_FIELDS:
                if field in m:
                    f[field] = m[field]
            s = by_model.setdefault(m["model"], set())
            for field in ("value", "coding_index", "intelligence_index", "agentic_index", "arena_elo"):
                if m.get(field) is not None:
                    s.add(m[field])
    lang = root / "data" / "models.json"
    if lang.exists():
        found = True
        d = json.loads(lang.read_text(encoding="utf-8"))
        for m in d.get("models", []):
            f = facts.setdefault((m.get("provider"), m["model"]), {})
            f["quality"], f["quality_for_agents"] = m["quality"], m["quality_for_agents"]
            s = by_model.setdefault(m["model"], set())
            s.add(m["quality"])
            s.add(m["quality_for_agents"])
    return found, facts, by_model, formula


def provider_hosts(root):
    """provider -> set of registrable domains a link for it may use: its API host, its sign-up host, and
    the sign-up and terms hosts declared in code by the contribution gate."""
    p = root / "bench" / "providers.json"
    out = {}
    if not p.exists():
        return out
    provs = json.loads(p.read_text(encoding="utf-8")).get("providers", [])
    api = hosts_of(provs)
    for prov in provs:
        name = prov.get("name", "")
        allowed = {registrable(api.get(name, ""))}
        if prov.get("signup"):
            allowed.add(registrable(host_of(prov["signup"])))
        allowed |= set(KNOWN_SIGNUP_HOSTS.get(name, set()))
        allowed |= set(KNOWN_TERMS_HOSTS.get(name, set()))
        out[name] = allowed - {""}
    return out


def page_markers(root):
    """page name -> the markers that may appear on it. Anything else is an unknown generated block."""
    return {"README.md": set(MARKERS), "SOURCES.md": {SOURCES_MARKER}}


def ignored_names(root):
    """The plain names .gitignore lists (no wildcard, no inner slash): what the walk skips when git is absent."""
    names = {".git"}
    gi = root / ".gitignore"
    if gi.exists():
        for line in gi.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or any(ch in line for ch in "*?[!") or "/" in line.rstrip("/"):
                continue
            names.add(line.rstrip("/"))
    return names


def tracked_markdown(root):
    """Every *.md git knows about under root, tracked or new and not ignored, in list form: no shell. When
    git is absent, root is not a repository, or git lists nothing (a copy inside an ignored folder), a walk
    that skips what .gitignore names. Relative posix paths, sorted."""
    rels = []
    try:
        r = subprocess.run(["git", "-C", str(root), "ls-files", "-z", "--cached", "--others", "--exclude-standard",
                            "--", "*.md"], capture_output=True, timeout=60)
        if r.returncode == 0:
            rels = [x for x in r.stdout.decode("utf-8", "replace").split("\0") if x]
    except (OSError, subprocess.SubprocessError):
        rels = []
    if not rels:
        skip = ignored_names(root)
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = sorted(d for d in dirnames if d not in skip)
            for f in filenames:
                if f.lower().endswith(".md") and f not in skip:
                    rels.append((Path(dirpath) / f).relative_to(root).as_posix())
    return sorted({rel for rel in rels if (root / rel).is_file()})


def is_golden_block(rel):
    p = PurePosixPath(rel)
    return p.parent.as_posix() == GOLDEN_DIR and p.stem in MARKERS


def count_exempt(rel):
    return rel in COUNT_EXEMPT_PAGES or rel.startswith(ARCHIVE_DIR + "/")


def pages(root):
    """Every markdown file git knows about, minus the generator's golden blocks. Computed, never typed."""
    return [root / rel for rel in tracked_markdown(root) if not is_golden_block(rel)]


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


def column(header, *names):
    for k, h in enumerate(header):
        if h.lower().strip("*") in names:
            return k
    return None


def cell(header, row, *names):
    k = column(header, *names)
    return row[k] if k is not None and k < len(row) else None


def has_column(header, *names):
    return column(header, *names) is not None


def visible(cell_text):
    """What a reader sees of a cell: link text instead of links, no bold, no backticks."""
    s = INLINE_LINK_RE.sub(lambda m: m.group(1), cell_text)
    s = HTML_A_RE.sub(lambda m: re.sub(r"<[^>]+>", "", m.group(4)), s)
    s = REF_LINK_RE.sub(lambda m: m.group(1), s)
    s = AUTOLINK_RE.sub(lambda m: m.group(1), s)
    return re.sub(r"[*`]", "", s).strip()


def figure(cell_text):
    """The number a cell states, bold or plain, with thousands separators; None if it states none."""
    m = FIGURE_RE.match(cell_text.strip())
    return float(m.group(1).replace(",", "")) if m else None


def scrub_code(text):
    """The document with fenced blocks and inline code spans blanked, line count and columns preserved:
    a URL inside code is an example, not a link."""
    out, fenced = [], False
    for line in text.split("\n"):
        if line.lstrip().startswith("```"):
            fenced = not fenced
            out.append("")
            continue
        out.append("" if fenced else re.sub(r"`[^`]*`", lambda m: " " * len(m.group(0)), line))
    return "\n".join(out)


def links_in(text):
    """Every link on the page, in every form GitHub renders: inline, reference-style, autolink, HTML anchor,
    bare URL. Each is {"line", "text", "url", "start", "end"}; text is what a reader sees (the URL itself,
    for a bare one)."""
    text = scrub_code(text)
    defs = {m.group(1).lower(): m.group(2) for m in REF_DEF_RE.finditer(text)}
    out = []
    for n, line in enumerate(text.split("\n"), 1):
        spans = []

        def add(m, shown, url):
            spans.append((m.start(), m.end()))
            out.append({"line": n, "text": shown, "url": url.rstrip(".,;:!?"), "start": m.start(), "end": m.end()})

        def taken(m):
            return any(s <= m.start() < e for s, e in spans)

        for m in INLINE_LINK_RE.finditer(line):
            add(m, m.group(1), m.group(2))
        for m in HTML_A_RE.finditer(line):
            if not taken(m):
                add(m, re.sub(r"<[^>]+>", "", m.group(4)), m.group(1) or m.group(2) or m.group(3) or "")
        for m in AUTOLINK_RE.finditer(line):
            if not taken(m):
                add(m, m.group(1), m.group(1))
        for m in REF_LINK_RE.finditer(line):
            if not taken(m):
                ident = (m.group(2) or m.group(1)).lower()
                if ident in defs:
                    add(m, m.group(1), defs[ident])
        for m in BARE_URL_RE.finditer(line):
            if not taken(m):
                add(m, m.group(0), m.group(0))
    return out


def outside_markers(text, allowed):
    """The document with every KNOWN generated block blanked, line count preserved. An unknown block is
    left in place, so whatever it hides is still read."""
    def blank(m):
        if m.group(1) not in allowed:
            return m.group(0)
        return "\n" * m.group(0).count("\n")
    return MARKER_RE.sub(blank, text)


def generated_lines(text, allowed):
    """The line numbers that sit inside a known generated block."""
    inside = set()
    for m in MARKER_RE.finditer(text):
        if m.group(1) in allowed:
            first = text.count("\n", 0, m.start()) + 1
            inside.update(range(first, first + m.group(0).count("\n") + 1))
    return inside


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


def bump(counts, name, n=1):
    counts[name] = counts.get(name, 0) + n


# ------------------------------------------------------------------ checks

def identity(header, row, hosts):
    """(provider, model) a table row is about, or (None, None). The provider is the cell under a
    Provider-like column, else any cell whose visible text is a provider bench/providers.json knows;
    plain, bold or linked, all the same. The model is the Model cell, backticked or not; without a Model
    column, the first backticked cell counts as the model only when the row also names a provider (a
    `lens` beside a bold correlation on METHOD.md is not a model)."""
    prov = cell(header, row, *PROVIDER_COLUMNS)
    name = visible(prov).lower() if prov else ""
    if name not in hosts:
        name = next((visible(c).lower() for c in row if visible(c).lower() in hosts), "")
    model = cell(header, row, "model")
    if model is None and name:
        model = next((c for c in row if MODEL_CELL_RE.match(c)), None)
    model = visible(model) if model else None
    return (name or None), (model or None)


def check_rows(path, tabs, facts, by_model, hosts, problems, counts):
    """Score figures (1) and answer cells (2), row by row, on the (provider, model) the row names."""
    per_provider = {}
    for (prov, _model), f in facts.items():
        rp = f.get("radar_probes")
        if rp:
            s = per_provider.setdefault(prov, [0, 0])
            s[0], s[1] = s[0] + rp[0], s[1] + rp[1]
    for hline, header, rows in tabs:
        provider_only = has_column(header, *PROVIDER_COLUMNS) and not has_column(header, "model")
        for n, row in rows:
            prov, model = identity(header, row, hosts)
            if provider_only and prov and not model:
                for c in row:
                    m = N_OF_M_RE.match(c)
                    if not m:
                        continue
                    yes, total = int(m.group(1)), int(m.group(2))
                    bump(counts, "answer cells")
                    if yes > total:
                        problems.append((where(path, n), "claims %d of %d for %s, which is more than the whole" % (yes, total, prov)))
                    elif prov not in per_provider or [yes, total] != per_provider[prov]:
                        problems.append((where(path, n), "claims %d of %d answered for %s; the radar's own counts in "
                                         "data/ranking.json add up to %s" % (yes, total, prov,
                                                                            "%d of %d" % tuple(per_provider[prov]) if prov in per_provider else "nothing")))
                continue
            if not model:
                continue
            key = (prov, model)
            if key in facts:
                f = facts[key]
                for k, h in enumerate(header):
                    field = COLUMN_FIELDS.get(h.lower().strip("*"))
                    if field is None or k >= len(row):
                        continue
                    v = figure(row[k])
                    if v is None:
                        continue
                    bump(counts, "score figures")
                    want = f.get(field)
                    if want is None:
                        problems.append((where(path, n), "%s at %s prints %s under %s, but the data has no %s for it. "
                                         "Regenerate with bench/rank.py rather than editing the table by hand."
                                         % (model, prov, row[k], h, field)))
                    elif float(want) != v:
                        problems.append((where(path, n), "%s at %s is published as %s under %s, but the data has %s. "
                                         "Regenerate with bench/rank.py rather than editing the table by hand."
                                         % (model, prov, row[k], h, want)))
                for k, h in enumerate(header):
                    if not h.lower().strip("*").startswith("answer") or k >= len(row):
                        continue
                    m = N_OF_M_RE.match(row[k])
                    if not m:
                        continue
                    yes, total = int(m.group(1)), int(m.group(2))
                    bump(counts, "answer cells")
                    rp = f.get("radar_probes")
                    if yes > total:
                        problems.append((where(path, n), "claims %d out of %d, which is more than the whole" % (yes, total)))
                    elif not rp or [yes, total] != list(rp):
                        problems.append((where(path, n), "claims %d of %d answered for %s at %s; the radar says %s"
                                         % (yes, total, model, prov, "%d of %d" % tuple(rp) if rp else "it was never probed")))
                continue
            bold = [figure(c) for c in row if c.startswith("**")]
            bold = [b for b in bold if b is not None]
            if not bold:
                continue
            bump(counts, "score figures", len(bold))
            if prov:
                problems.append((where(path, n), "%s is scored here at %s, but the data has no such endpoint%s"
                                 % (model, prov, "" if model in by_model else " and no such model")))
            elif model not in by_model:
                problems.append((where(path, n), "model %r is scored here but is not in the data" % model))
            else:
                for b in bold:
                    if b not in by_model[model]:
                        problems.append((where(path, n),
                                         "%s is published as %s, but the data has %s. Regenerate with bench/rank.py "
                                         "rather than editing the table by hand." % (model, b, sorted(by_model[model]))))


def check_order(path, tabs, problems, counts):
    """A ranked table is numbered 1..n and sorted by its bold value, descending."""
    for hline, header, rows in tabs:
        if not header or header[0].strip() != "#" or not rows:
            continue
        bump(counts, "ranked tables in order")
        vcol = column(header, "value")
        last = None
        for i, (n, row) in enumerate(rows, 1):
            if not row or row[0].strip() != str(i):
                problems.append((where(path, n), "ranked row %d is numbered %r. A ranked table is numbered 1..n, in order."
                                 % (i, row[0] if row else "")))
            vcell = row[vcol] if vcol is not None and vcol < len(row) else next((c for c in row if c.startswith("**")), "")
            v = figure(vcell)
            if v is None:
                continue
            if last is not None and v > last:
                problems.append((where(path, n), "ranked row %d carries %s above a row with %s: the table is not sorted "
                                 "by value, descending. A re-ordered table is a claim the data does not make."
                                 % (i, vcell, last)))
            last = v


def check_paths(path, root, links, problems, counts):
    for link in links:
        ref = link["url"]
        if ref.startswith(("http://", "https://", "#", "mailto:")) or not ref:
            continue
        target = (path.parent / ref.split("#")[0]).resolve()
        try:
            target.relative_to(root)
        except ValueError:
            continue        # points outside the tree (GitHub's own ../../security/... URLs): not ours to check
        bump(counts, "links")
        if not target.exists():
            problems.append((where(path, link["line"]), "links to %s, which does not exist. Saying a file is 'in "
                             "this repo' when it is not is the same class of error as an invented number." % ref))


def check_formula(path, text, formula, problems, counts):
    if not formula:
        return
    bump(counts, "the formula")
    if formula not in text:
        problems.append((where(path), "the value formula printed here is not the one in data/ranking.json: %r. "
                         "Every page prints the same string, built from the constants rank.py computes with." % formula))


def check_labels(path, tabs, problems, counts):
    for hline, header, rows in tabs:
        ranked = bool(header) and header[0].strip() == "#"
        for n, row in rows:
            v = cell(header, row, *LABEL_COLUMNS)
            if v is not None and v:
                bump(counts, "labels")
                label = re.split(r"[,;]", v)[0].strip().strip("*")
                if label not in LABELS:
                    problems.append((where(path, n), "label %r is not one of %s" % (v, sorted(LABELS))))
                elif ranked and label not in RANKABLE:
                    problems.append((where(path, n), "a ranked row carries %s. A row is ranked on %s; %s sit on the daily "
                                     "shelf or are shown, never ranked." % (label, ", ".join(sorted(RANKABLE)),
                                                                            ", ".join(sorted(LABELS - RANKABLE)))))
            a = cell(header, row, "answers")
            if ranked and a is not None and a.strip() == "?":
                problems.append((where(path, n), "a ranked row prints ? for Answers. An answered rate of 0 "
                                 "is a measurement and prints as 0 of N; ? is reserved for endpoints never probed."))


def named_in(text, hosts):
    low = text.lower()
    return {name for name in hosts if re.search(r"\b%s\b" % re.escape(name), low)}


def is_door(link):
    """A link that says it hands out keys, by its text or by its path."""
    u = urlparse(link["url"])
    return bool(KEYISH_TEXT_RE.search(link["text"]) or KEYISH_URL_RE.search(u.path or "") or KEYISH_URL_RE.search(u.query or ""))


def check_doors(path, text, tabs, links, hosts, problems, counts):
    """Every link on the page. In a table with a Provider column the row's provider binds every link in the
    row; everywhere else the link's own text, or the key-talk right before it, names the provider it must
    belong to, and a door with no name must at least be some provider's declared door."""
    if not hosts:
        return
    lines = scrub_code(text).split("\n")
    by_line = {}
    for link in links:
        by_line.setdefault(link["line"], []).append(link)
    bound = set()
    for hline, header, rows in tabs:
        if not has_column(header, *PROVIDER_COLUMNS):
            continue
        for n, row in rows:
            prov_cell = cell(header, row, *PROVIDER_COLUMNS) or ""
            name = visible(prov_cell).lower()
            if not name:
                continue
            bound.add(n)
            if name not in hosts:
                problems.append((where(path, n), "provider %r appears in a table but is not in bench/providers.json. "
                                 "A page may only name providers the contribution gate has admitted; a row for a "
                                 "provider nobody vetted is a door nobody checked." % name))
                continue
            for link in by_line.get(n, []):
                u = link["url"]
                if not u.startswith(("http://", "https://")):
                    continue
                bump(counts, "doors")
                if registrable(host_of(u)) not in hosts[name]:
                    problems.append((where(path, n), "the door for %s points at %s, which is neither its API "
                                     "domain nor a declared sign-up or terms host. A link on an undeclared "
                                     "domain is how people get phished." % (name, host_of(u))))
    every_host = set().union(*hosts.values())
    for link in links:
        n, u = link["line"], link["url"]
        if n in bound or not u.startswith(("http://", "https://")):
            continue
        line = lines[n - 1] if n - 1 < len(lines) else ""
        earlier = [l["end"] for l in by_line.get(n, []) if l["end"] <= link["start"]]
        context = line[max(0, link["start"] - CONTEXT_CHARS, max(earlier) if earlier else 0):link["start"]]
        names = named_in(link["text"], hosts)
        door = is_door(link)
        if KEYISH_TEXT_RE.search(context):
            door = True
            names |= named_in(context, hosts)
        if names:
            allowed, owner = set().union(*(hosts[x] for x in names)), ", ".join(sorted(names))
        elif door:
            allowed, owner = every_host, "any provider"
        else:
            continue
        bump(counts, "doors")
        if registrable(host_of(u)) not in allowed:
            problems.append((where(path, n), "the link %r points at %s, which is not a domain declared for %s (API host, "
                             "sign-up host or terms host in bench/providers.json and gate_contributions.py). A link that "
                             "names a provider, or offers a key, on an undeclared domain is how people get phished."
                             % (link["text"][:60], host_of(u), owner)))


def ranking_shaped(header):
    return bool(header) and has_column(header, "model") and (
        header[0].strip() == "#" or (has_column(header, *PROVIDER_COLUMNS) and has_column(header, "value")))


def check_provenance(rel, path, text, tabs, links, allowed, problems, counts):
    """A ranking-shaped table or a door only ever comes out of the generator. Anywhere else it is a page
    that looks generated and is not."""
    generated = rel in GENERATED_PAGES
    inside = generated_lines(text, allowed) if rel == "README.md" else set()
    provider_rows = {n for hline, header, rows in tabs if has_column(header, *PROVIDER_COLUMNS) for n, _ in rows}
    for hline, header, rows in tabs:
        if not ranking_shaped(header):
            continue
        bump(counts, "pages that look generated")
        if not (generated or hline in inside):
            problems.append((where(path, hline), "a ranking-shaped table (%s) on a page the generator does not write. "
                             "Rankings come out of bench/rank.py onto %s, or into a generated block on README.md; a page "
                             "that looks generated and is not is refused whatever its numbers say."
                             % (" / ".join(header[:4]), ", ".join(sorted(GENERATED_PAGES)))))
    for link in links:
        if not link["url"].startswith(("http://", "https://")):
            continue
        if not (is_door(link) or link["line"] in provider_rows):
            continue
        bump(counts, "pages that look generated")
        if not (generated or link["line"] in inside):
            problems.append((where(path, link["line"]), "a door (%r -> %s) on a page the generator does not write. Doors "
                             "come out of bench/rank.py, checked against the provider's own domain; a hand-typed one "
                             "is a page that looks generated and is not." % (link["text"][:40], host_of(link["url"]))))


def check_headline(readme, root, hosts, problems, counts):
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
        bump(counts, "the headline box")
        if "**%s**" % want not in block:
            problems.append((readme.name, "the headline box does not carry data/capacity.json's defensible figure %s in bold" % want))
        pct = d.get("share_of_target_pct")
        if pct is not None:
            bump(counts, "the headline box")
            if ("**%.1f%%**" % pct) not in block and ("**%.0f%%**" % pct) not in block:
                problems.append((readme.name, "the headline share is not %.1f%% from data/capacity.json" % pct))
    for marker in ("CAPACITY", "RELIABILITY"):
        m = re.search(r"<!--%s-->(.*?)<!--/%s-->" % (marker, marker), text, re.S)
        if not m:
            problems.append((readme.name, "no %s block" % marker))
            continue
        for name in hosts:
            bump(counts, "the headline box")
            if not re.search(r"\b%s\b" % re.escape(name), m.group(1)):
                problems.append((readme.name, "provider %r is missing from the %s block: a provider dropped from a "
                                 "table is a number that vanished" % (name, marker)))


def check_markers(path, text, allowed, problems, counts):
    """Every <!--X--> tag on the page must be a marker the generator writes here, or the declared
    hand-typed block. An invented one is refused, not blanked: the generator would never rewrite it, so a
    number inside it would outlive every regeneration."""
    for n, line in enumerate(text.split("\n"), 1):
        for closing, name in MARKER_TAG_RE.findall(line):
            bump(counts, "generated-block markers")
            if name not in allowed:
                problems.append((where(path, n), "<!--%s%s--> is not a generated block on this page (the generator writes "
                                 "%s here). An unknown marker survives regeneration untouched, so it is refused as an "
                                 "unknown generated block and nothing inside it is exempt from the checks below."
                                 % (closing, name, ", ".join(sorted(allowed)) or "nothing")))


def check_count_prose(path, text, allowed, problems, counts):
    text = outside_markers(text, allowed)
    for n, para in paragraphs(text):
        bump(counts, "prose paragraphs read for counts")
        for m in COUNT_RE.finditer(para):
            problems.append((where(path, n), "%r is a count in prose outside a generated block. Counts are "
                             "generated between markers, or they go stale." % m.group(0)))


def check_sources(path, text, problems, counts):
    """Star counts and a hand-counted 'N for N' are allowed only inside the <!--SOURCES-TABLE--> block."""
    text = outside_markers(text, {SOURCES_MARKER})
    for hline, header, rows in tables(text):
        bump(counts, "hand-typed numbers on SOURCES.md")
        if has_column(header, "stars"):
            problems.append((where(path, hline), "a table with a Stars column sits outside the <!--%s--> block. Star "
                             "counts are hand-typed and age by the day; they are shown only inside the block that "
                             "declares them as a dated snapshot." % SOURCES_MARKER))
    for n, para in paragraphs(text):
        bump(counts, "hand-typed numbers on SOURCES.md")
        for m in STARS_RE.finditer(para):
            problems.append((where(path, n), "%r is a hand-typed star count outside the <!--%s--> block." % (m.group(0), SOURCES_MARKER)))
        for m in N_FOR_N_RE.finditer(para):
            problems.append((where(path, n), "%r is a hand-counted score outside the <!--%s--> block. It was true "
                             "on the day it was typed and nothing re-counts it." % (m.group(0), SOURCES_MARKER)))


# ------------------------------------------------------------------ main

# The CLEAN line prints these, in this order, with the number of items each verified; a check that
# verified nothing on the tree is named on its own line as not exercised, never as a check that ran.
CHECKS = ("score figures", "answer cells", "ranked tables in order", "links", "labels", "doors",
          "pages that look generated", "the formula", "the headline box", "generated-block markers",
          "prose paragraphs read for counts", "hand-typed numbers on SOURCES.md")


def run(root):
    global _ROOT
    _ROOT = root
    problems, checked, counts = [], [], {}
    found, facts, by_model, formula = load_models(root)
    if not found:
        return None, ["no data/ranking.json and no data/models.json - run bench/rank.py first"], counts
    hosts = provider_hosts(root)
    markers = page_markers(root)
    for p in pages(root):
        rel = p.relative_to(root).as_posix()      # "README.md" and "bench/languages/README.md" are different pages
        allowed = markers.get(rel, set())
        checked.append(rel)
        text = p.read_text(encoding="utf-8")
        tabs = list(tables(text))
        links = links_in(text)
        check_rows(p, tabs, facts, by_model, hosts, problems, counts)
        check_order(p, tabs, problems, counts)
        check_paths(p, root, links, problems, counts)
        check_labels(p, tabs, problems, counts)
        check_doors(p, text, tabs, links, hosts, problems, counts)
        check_provenance(rel, p, text, tabs, links, allowed, problems, counts)
        check_markers(p, text, allowed, problems, counts)
        if rel in FORMULA_PAGES:
            check_formula(p, text, formula, problems, counts)
        if rel == "README.md":
            check_headline(p, root, hosts, problems, counts)
        if not count_exempt(rel):
            check_count_prose(p, text, allowed, problems, counts)
        if rel == "SOURCES.md":
            check_sources(p, text, problems, counts)
    return checked, problems, counts


def summary(counts):
    ran = ["%s %d" % (name, counts[name]) for name in CHECKS if counts.get(name)]
    idle = [name for name in CHECKS if not counts.get(name)]
    return ", ".join(ran), idle


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
        checked, problems, counts = run(root)
    except (OSError, ValueError, KeyError) as e:
        print("gate could not run: %s: %s" % (type(e).__name__, e))
        return 2
    if checked is None:
        print(problems[0])
        return 2
    ran, idle = summary(counts)
    print("checked %d documents (%s)" % (len(checked), ", ".join(checked)))
    if idle:
        print("not exercised on this tree, so not counted as a check: %s" % ", ".join(idle))
    if not problems:
        print("CLEAN - every checked claim is in the data. Verified: %s." % ran)
        return 0
    print("\n%d UNSUPPORTED CLAIMS:\n" % len(problems))
    for where_, what in problems:
        print("  %s\n      %s" % (where_, what))
    return 1


if __name__ == "__main__":
    sys.exit(main())
