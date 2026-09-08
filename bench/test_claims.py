#!/usr/bin/env python3
"""Calibrate the claims gate in both directions, on a copy of the real pages. No network.

    python bench/test_claims.py

Each case copies the repo's published pages and data into a temp dir, plants ONE edit a careless or
hostile pull request would make, runs the gate on the copy, and asserts the named check fires. Then the
untouched copy must pass. A gate that has never been watched failing is a green light, not a gate.

Every planted edit finds its target BY STRUCTURE: the first ranked row whatever its label, the cell under
a named column, the first row that carries a probe count. The previous version replaced literal strings
("| MEASURED |", "N of M in 14 days") in row #1, so a legitimate re-ordering of the ranking that put a
DERIVED row first crashed this file on its own assert while every gate stayed green: a red light by
accident, and a gate that never checked order. Order is a check now, and the fixtures no longer care
which row is first.

The holes each review found have a planted case here: an invented <!--NOTE--> block hiding a count; a
brand-new BEST.md with a fake score row and a lookalike door; a hand-typed star count on SOURCES.md; a
bench/README.md with a fake ranking (never opened before); doors written as HTML anchors, reference-style
links, autolinks, bare URLs and prose links; a fake value beside a provider cell that is a link; a ranked
DRAWN row; a re-ordered ranked table; an Answers cell that disagrees with the radar.
"""
import json, re, shutil, subprocess, sys, tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
import gate_claims as G


def copy_repo(tmp):
    """The whole tree minus git: the link check needs every file a page points at."""
    shutil.copytree(ROOT, tmp, dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns(".git", "__pycache__", ".venv", "venv", "scratch"))


def edit(tmp, rel, fn):
    p = tmp / rel
    t = p.read_text(encoding="utf-8")
    t2 = fn(t)
    assert t2 != t, "the planted edit changed nothing in %s" % rel
    p.write_text(t2, encoding="utf-8", newline="\n")


def write(tmp, rel, text):
    (tmp / rel).parent.mkdir(parents=True, exist_ok=True)
    (tmp / rel).write_text(text, encoding="utf-8", newline="\n")


def rebuilt(cells):
    return "| " + " | ".join(cells) + " |"


def block(t, marker):
    """(span, header, [(raw line, cells)]) of the first table inside <!--marker-->, found by structure."""
    m = re.search(r"<!--%s-->\n(.*?)\n<!--/%s-->" % (marker, marker), t, re.S)
    hline, header, rows = next(G.tables(m.group(1)))
    lines = m.group(1).split("\n")
    return m.span(1), header, [(lines[n - 1], cells) for n, cells in rows]


def in_block(t, marker, fn):
    """Apply fn to the text of the block only, so a row that also appears in TOP5 is edited where intended."""
    (a, b), _, _ = block(t, marker)
    return t[:a] + fn(t[a:b]) + t[b:]


def col(header, name):
    """Index of the column whose header starts with `name`, case-insensitive."""
    for k, h in enumerate(header):
        if h.lower().strip("*").startswith(name.lower()):
            return k
    raise AssertionError("no column %r in %s" % (name, header))


def ranked_edit(t, column, fn, pick=None, marker="RANKING"):
    """Rewrite ONE cell, under `column`, of the first ranked row (or the first row `pick` accepts). Whatever
    the row's label, whatever its position."""
    _, header, rows = block(t, marker)
    k = col(header, column)
    for line, cells in rows:
        if pick is None or pick(cells):
            new = list(cells)
            new[k] = fn(cells[k])
            return in_block(t, marker, lambda b: b.replace(line, rebuilt(new), 1))
    raise AssertionError("no ranked row to edit under %r" % column)


def ranked_swap(t, marker="RANKING"):
    """Exchange the first two adjacent ranked rows whose values differ, keeping the numbers: a re-ordering."""
    _, header, rows = block(t, marker)
    v = col(header, "value")
    for (l1, c1), (l2, c2) in zip(rows, rows[1:]):
        if G.figure(c1[v]) != G.figure(c2[v]):
            n1, n2 = list(c2), list(c1)
            n1[0], n2[0] = c1[0], c2[0]
            return in_block(t, marker, lambda b: b.replace(l1, "\0A", 1).replace(l2, "\0B", 1)
                            .replace("\0A", rebuilt(n1)).replace("\0B", rebuilt(n2)))
    raise AssertionError("every ranked value is the same; nothing to re-order")


def first_ranked(tmp):
    """(provider, model, value) of the first ranked row, from the copy's data, for a row that must pass on its own."""
    r = json.loads((tmp / "data" / "ranking.json").read_text(encoding="utf-8"))["ranked"][0]
    return r["provider"], r["model"], r["value"]


def endpoints(tmp):
    d = json.loads((tmp / "data" / "ranking.json").read_text(encoding="utf-8"))
    return {(r["provider"], r["model"]) for r in d["ranked"] + d["unranked"]}


def door_url(cells, header):
    return re.search(r"\((https?://[^)]+)\)", cells[col(header, "get key")]).group(1)


N_OF_M = re.compile(r"^(\d+) of (\d+)")


def bump_answers(c):
    return N_OF_M.sub(lambda m: "%s of %d" % (m.group(1), int(m.group(2)) + 1), c, 1)


HONEST_SOURCES = """# Sources

Everything here has a source.

<!--SOURCES-TABLE-->
| Repo | Stars | What it does better than us |
|---|---|---|
| [someone/some-list](https://github.com/someone/some-list) | 24.5k | verifies rows live |

Six for six. A directory with 2,700 stars still lists a dead endpoint.
<!--/SOURCES-TABLE-->

Read on the dates recorded in [`bench/limits.json`](bench/limits.json).
"""

FAKE_RANKING = ("| # | Model | Provider | Value | Get key |\n|---|---|---|---|---|\n"
                "| 1 | `gpt-5` | evilrouter | **999.9** | [get a key](https://evil.example/keys) |\n"
                "| 2 | `%s` | %s | **%s** | [Get key](https://%s.com.evil.example/keys) |\n")
ANCHOR = "## How to read any row of this list"        # README prose, outside every generated block


def main():
    bad = 0

    def case(label, ok, detail=""):
        nonlocal bad
        print("  %-4s %s%s" % ("ok" if ok else "FAIL", label, ("  -> " + detail[:300]) if (detail and not ok) else ""))
        if not ok:
            bad += 1

    def planted(label, plant, *must_mention):
        """plant(tmp) edits the copy; every phrase in must_mention has to appear among the problems."""
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            copy_repo(tmp)
            plant(tmp)
            checked, problems, counts = G.run(tmp)
            whats = [what for _, what in problems]
            missing = [m for m in must_mention if not any(m in w for w in whats)]
            case(label, not missing, ("not raised: %r; raised: " % missing) + ("; ".join(whats)[:300] or "nothing"))

    def on(rel, fn):
        return lambda tmp: edit(tmp, rel, fn)

    def readme_prose(text):
        return on("README.md", lambda t: t.replace(ANCHOR, text + "\n\n" + ANCHOR, 1))

    print("edits that MUST be refused:")
    planted("a value typed by hand in the ranking",
            on("README.md", lambda t: ranked_edit(t, "value", lambda c: c.replace("**", "**9", 1))), "is published as **9")
    planted("the formula edited on one page",
            on("RESULTS.md", lambda t: t.replace("log10(1 + daily_tokens / 500)", "log10(1 + requests_per_day)")),
            "value formula")
    planted("PAID-PLAN in a ranked row",
            on("README.md", lambda t: ranked_edit(t, "volume", lambda c: "PAID-PLAN")), "ranked row carries PAID-PLAN")
    planted("DRAWN in a ranked row: a shelf label, never a row's",
            on("README.md", lambda t: ranked_edit(t, "volume", lambda c: "DRAWN")), "ranked row carries DRAWN")
    planted("an invented label",
            on("ALL-ENDPOINTS.md", lambda t: t.replace("| MEASURED |", "| CONFIRMED |", 1)), "is not one of")
    planted("a ? for Answers in a ranked row",
            on("README.md", lambda t: ranked_edit(t, "answers", lambda c: "?")), "prints ? for Answers")
    planted("an Answers cell that disagrees with the radar",
            on("README.md", lambda t: ranked_edit(t, "answers", bump_answers, pick=lambda cells: any(N_OF_M.match(c) for c in cells))),
            "the radar says")
    planted("a per-provider Answered cell that disagrees with the radar",
            on("README.md", lambda t: ranked_edit(t, "answered", bump_answers, pick=lambda cells: any(N_OF_M.match(c) for c in cells),
                                                  marker="RELIABILITY")),
            "the radar's own counts")
    planted("the ranked table re-ordered, numbers kept",
            on("README.md", ranked_swap), "not sorted by value")
    planted("a ranked row misnumbered",
            on("README.md", lambda t: ranked_edit(t, "#", lambda c: str(int(c) + 1), pick=lambda cells: cells[0] == "2")),
            "is numbered")
    planted("a Get key door on a lookalike domain",
            on("README.md", lambda t: ranked_edit(t, "get key", lambda c: re.sub(r"\]\(https://[^)]+\)", "](https://xkiro.com.evil.example/keys)", c, 1))),
            "neither its API domain")
    planted("a provider link in the capacity table pointing elsewhere",
            on("README.md", lambda t: t.replace("[cerebras](https://cloud.cerebras.ai)", "[cerebras](https://cerebras-keys.example)", 1)),
            "neither its API domain")

    def linked_cell_fake_value(tmp):
        def fn(t):
            _, header, rows = block(t, "RANKING")
            line, cells = rows[0]
            new = list(cells)
            new[col(header, "provider")] = "[%s](%s)" % (cells[col(header, "provider")], door_url(cells, header))
            new[col(header, "value")] = "**999.9**"
            return in_block(t, "RANKING", lambda b: b.replace(line, rebuilt(new), 1))
        edit(tmp, "README.md", fn)
    planted("a fake value beside a provider cell that is a link (the cell is still matched as that provider)",
            linked_cell_fake_value, "is published as **999.9**")

    def borrowed_provider(tmp):
        prov, model, value = first_ranked(tmp)
        others = sorted(p for p, m in endpoints(tmp) if m == model and p != prov)
        other = others[0] if others else sorted(p for p, _ in endpoints(tmp) if p != prov)[0]
        edit(tmp, "README.md", lambda t: ranked_edit(t, "provider", lambda c: other))
        return bool(others)
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        copy_repo(tmp)
        shared = borrowed_provider(tmp)
        checked, problems, _ = G.run(tmp)
        whats = [w for _, w in problems]
        want = "is published as" if shared else "no such endpoint"
        case("the first row's value under another provider's name%s" % (" that serves the same model" if shared else ""),
             any(want in w for w in whats), "; ".join(whats)[:300])

    planted("the headline figure typed by hand",
            on("README.md", lambda t: re.sub(r"(\| \*\*Tokens a day this list can defend\*\* \| \*\*)([\d,]+)(\*\*)", r"\g<1>999,999,999\3", t)),
            "defensible figure")
    planted("a provider row deleted from the capacity table",
            on("README.md", lambda t: re.sub(r"\n\| \*\*\[kenari\]\([^\n]*", "", t, 1)), "missing from the CAPACITY block")
    planted("a count typed into README prose", readme_prose("We track 12 providers today."), "'12 providers' is a count in prose")
    planted("a count of models typed into README prose", readme_prose("We list 250 models."), "'250 models' is a count in prose")
    planted("a count of keys typed into README prose", readme_prose("Each runner holds two keys."), "'two keys' is a count in prose")
    planted("a count with an adjective between ('12 free providers')", readme_prose("We track 12 free providers."),
            "'12 free providers' is a count in prose")
    planted("a count wrapped over a line break ('350+' then 'providers')",
            readme_prose("A catalogue of 350+\nproviders informed this list."), "'350+ providers' is a count in prose")
    planted("a count typed into SECURITY prose",
            on("SECURITY.md", lambda t: t.replace("# Security", "# Security\n\nIt sends requests to ten hosts.", 1)),
            "'ten hosts' is a count in prose")
    planted("a count typed into CONTRIBUTING prose",
            on("CONTRIBUTING.md", lambda t: t.replace("# Contributing\n", "# Contributing\n\nEighteen providers are listed.\n", 1)),
            "'Eighteen providers' is a count in prose")
    planted("a link to a file that does not exist",
            on("README.md", lambda t: t.replace("[RESULTS.md](RESULTS.md)", "[RESULTS.md](RESULTS-old.md)", 1)), "does not exist")
    planted("a reference-style link to a file that does not exist",
            readme_prose("See [the plan][plan].\n\n[plan]: PLAN.md"), "PLAN.md, which does not exist")
    planted("an HTML anchor to a file that does not exist",
            readme_prose('See <a href="PLAN.md">the plan</a>.'), "PLAN.md, which does not exist")
    planted("a broken link in the language-pack README, resolved from its own folder",
            on("bench/languages/README.md", lambda t: t.replace("Copy `ro.json`", "Copy [`ro.json`](ro-missing.json)", 1)),
            "ro-missing.json, which does not exist")
    planted("an invented <!--NOTE--> block with a count inside it",
            readme_prose("<!--NOTE-->\nWe track 99 providers across 400 endpoints.\n<!--/NOTE-->"),
            "<!--NOTE--> is not a generated block", "'99 providers' is a count in prose", "'400 endpoints' is a count in prose")
    planted("a marker the generator does write, but on a page it never writes to",
            on("SECURITY.md", lambda t: t.replace("# Security", "# Security\n\n<!--COUNTS-->\nWe scan 12 hosts.\n<!--/COUNTS-->", 1)),
            "<!--COUNTS--> is not a generated block", "'12 hosts' is a count in prose")
    planted("the SOURCES-TABLE block used on README to hide a count",
            readme_prose("<!--SOURCES-TABLE-->\nWe track 99 providers.\n<!--/SOURCES-TABLE-->"),
            "<!--SOURCES-TABLE--> is not a generated block", "'99 providers' is a count in prose")

    def fake_page(rel):
        def plant(tmp):
            prov, model, value = first_ranked(tmp)
            write(tmp, rel, "# Best\n\n" + FAKE_RANKING % (model, prov, value, prov))
        return plant
    planted("a new BEST.md with a fake score row, an unknown provider and a lookalike door", fake_page("BEST.md"),
            "model 'gpt-5' is scored here but is not in the data",
            "provider 'evilrouter' appears in a table but is not in bench/providers.json",
            "neither its API domain", "looks generated and is not")
    planted("a bench/README.md with a fake ranking and a lookalike door: a page outside the root", fake_page("bench/README.md"),
            "model 'gpt-5' is scored here but is not in the data", "neither its API domain", "looks generated and is not")
    planted("a page planted among the generator's golden blocks", fake_page("bench/tests/fixture/golden/BEST.md"),
            "looks generated and is not")
    planted("a page planted in a dated results folder", fake_page("results/2026-09-06/BEST.md"), "looks generated and is not")
    planted("a shared key offered in the pull request template",
            on(".github/pull_request_template.md", lambda t: t + "\nGrab a shared one [here](https://evil.example/keys).\n"),
            "a door", "not a domain declared for any provider")
    planted("a new page linking to a file that does not exist",
            lambda tmp: write(tmp, "NOTES.md", "# Notes\n\nSee [the plan](PLAN.md).\n"), "PLAN.md, which does not exist")

    def vendor_table(tmp):
        prov, model, value = first_ranked(tmp)
        edit(tmp, "README.md", lambda t: t.replace(ANCHOR, "| # | Model | Vendor | Value | Key |\n|---|---|---|---|---|\n"
                                                    "| 1 | `%s` | %s | **%s** | [get a key](https://evil.example/keys) |\n\n%s"
                                                    % (model, prov, value, ANCHOR), 1))
    planted("a Vendor table on README outside every block, real row, door on evil.example", vendor_table,
            "looks generated and is not", "neither its API domain")
    planted("a door written as an HTML anchor in README prose",
            readme_prose('Keys: <a href="https://evil.example/keys">get a key</a>.'),
            "a door", "not a domain declared for any provider")
    planted("a door written as a reference-style link in README prose",
            readme_prose("You can [get key][k] here.\n\n[k]: https://evil.example/keys"),
            "a door", "not a domain declared for any provider")
    planted("a door written as an autolink, named only by its path",
            readme_prose("Keys: <https://evil.example/keys>."), "a door", "not a domain declared for any provider")
    planted("a prose link whose text names a provider and points elsewhere (CONTRIBUTING)",
            on("CONTRIBUTING.md", lambda t: t.replace("# Contributing\n", "# Contributing\n\nSee [Groq's rate limits](https://groq-limits.example/).\n", 1)),
            "not a domain declared for groq")
    planted("key-talk before a bland link text binds it to the provider named ('Get your Groq key at the console')",
            on("CONTRIBUTING.md", lambda t: t.replace("# Contributing\n", "# Contributing\n\nGet your Groq key at [the console](https://groq-console.example/).\n", 1)),
            "not a domain declared for groq")
    planted("a bare lookalike URL in SECURITY prose",
            on("SECURITY.md", lambda t: t.replace("# Security", "# Security\n\nKeys: https://console.groq.com.evil.example/keys", 1)),
            "not a domain declared for groq")
    planted("a Stars table on SOURCES.md outside the SOURCES-TABLE block",
            lambda tmp: write(tmp, "SOURCES.md", HONEST_SOURCES.replace("<!--/SOURCES-TABLE-->\n", "<!--/SOURCES-TABLE-->\n\n"
                              "| Repo | Stars | What it does better than us |\n|---|---|---|\n| [x/y](https://github.com/x/y) | 9k | nothing |\n")),
            "a table with a Stars column sits outside the <!--SOURCES-TABLE--> block")
    planted("'Six for six' on SOURCES.md outside the block",
            lambda tmp: write(tmp, "SOURCES.md", HONEST_SOURCES + "\nSix for six.\n"), "'Six for six' is a hand-counted score outside")
    planted("a star count in SOURCES prose outside the block",
            lambda tmp: write(tmp, "SOURCES.md", HONEST_SOURCES + "\nA directory with 2,700 stars still lists it.\n"),
            "'2,700 stars' is a hand-typed star count outside")

    print("\nwhat MUST pass:")
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        copy_repo(tmp)
        checked, problems, counts = G.run(tmp)
        case("an untouched copy of the published pages", not problems, "; ".join("%s: %s" % pw for pw in problems)[:400])
        tracked = subprocess.run(["git", "-C", str(ROOT), "ls-files", "--", "*.md"], capture_output=True, text=True).stdout.split()
        expected = {rel for rel in tracked if not G.is_golden_block(rel)}
        case("the gate opens every markdown file git tracks, minus the generator's golden blocks, in a copy without git",
             set(checked) == expected, "opened but not tracked: %s; tracked but not opened: %s"
             % (sorted(set(checked) - expected), sorted(expected - set(checked))))
        listed = {p.relative_to(ROOT).as_posix() for p in G.pages(ROOT)}
        case("--list-pages on the repo prints exactly what run() opens", listed == set(checked),
             "listed only: %s; opened only: %s" % (sorted(listed - set(checked)), sorted(set(checked) - listed)))
        case("every page at the root, and the language-pack README, is on the list",
             set(checked) >= {p.name for p in ROOT.glob("*.md")} and "bench/languages/README.md" in checked, str(checked))
        ran, idle = G.summary(counts)
        case("every check on the CLEAN line verified at least one item on this tree, and says how many",
             not idle and all(re.search(r"\b%s \d+" % re.escape(name), ran) for name in G.CHECKS), "idle: %s; line: %s" % (idle, ran))
        case("the score check read hundreds of figures, not a handful of rows", counts.get("score figures", 0) > 100, str(counts))
        case("the answer check read the probe counts on the pages", counts.get("answer cells", 0) > 20, str(counts))
        case("the door check read the links in prose as well as in tables", counts.get("doors", 0) > 200, str(counts))
        edit(tmp, "README.md", lambda t: t.replace("<!--COUNTS-->", "<!--COUNTS-->\nGenerated: 99 providers and 99 endpoints.", 1))
        checked, problems, _ = G.run(tmp)
        case("a count INSIDE a generated block is the generator's business, not the gate's",
             not any("'99 providers'" in w or "'99 endpoints'" in w for _, w in problems))
        edit(tmp, "LIMITS.md", lambda t: t.replace("| DECLARED |", "| DECLARED; per model, largest shown |", 1))
        checked, problems, _ = G.run(tmp)
        case("a label followed by a note is still a label", not any("is not one of" in w for _, w in problems))
        edit(tmp, "bench/languages/README.md", lambda t: t.replace("Copy `ro.json`", "Copy [`ro.json`](ro.json)", 1))
        checked, problems, _ = G.run(tmp)
        case("a link in the language-pack README to a file beside it", not any("does not exist" in w for _, w in problems))
        write(tmp, "SOURCES.md", HONEST_SOURCES)
        checked, problems, _ = G.run(tmp)
        case("star counts and 'Six for six' INSIDE the SOURCES-TABLE block",
             not any(pw[0].startswith("SOURCES.md") for pw in problems), "; ".join(w for _, w in problems)[:300])
        edit(tmp, "METHOD.md", lambda t: t.replace("# Method\n", "# Method\n\nThe archived run covered four models.\n", 1))
        checked, problems, _ = G.run(tmp)
        case("a count in METHOD.md's archived-run prose is history and stays",
             not any(pw[0].startswith("METHOD.md") and "count in prose" in pw[1] for pw in problems))
        write(tmp, "results/2026-09-06/notes.md", "# Notes on the run\n\nWe probed 40 endpoints and 9 providers that day.\n")
        checked, problems, _ = G.run(tmp)
        case("a count in a dated results folder is history and stays, and the page is still opened",
             "results/2026-09-06/notes.md" in checked and not any(pw[0].startswith("results/") for pw in problems),
             "; ".join("%s: %s" % pw for pw in problems)[:300])
        case("the golden CAPACITY block, with its five invented providers, is not a page", not any("golden" in c for c in checked), str(checked))

    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        copy_repo(tmp)

        def linked_cell(t):
            _, header, rows = block(t, "RANKING")
            line, cells = rows[0]
            new = list(cells)
            new[col(header, "provider")] = "[%s](%s)" % (cells[col(header, "provider")], door_url(cells, header))
            return in_block(t, "RANKING", lambda b: b.replace(line, rebuilt(new), 1))
        edit(tmp, "README.md", linked_cell)
        edit(tmp, "SOURCES.md", lambda t: t + "\nSee [Groq's rate limits][g] and [OpenRouter](https://openrouter.ai/docs).\n\n"
                                              "[g]: https://console.groq.com/docs/rate-limits\n")
        edit(tmp, "CONTRIBUTING.md", lambda t: t + '\nThe list is on <a href="https://github.com/x/y">GitHub</a>; Cerebras documents '
                                                   'its tiers at https://inference-docs.cerebras.ai/support/pricing.\n')
        checked, problems, _ = G.run(tmp)
        case("a provider cell that is a link to the provider's own door, value untouched",
             not any("published as" in w or "neither its API domain" in w for _, w in problems), "; ".join(w for _, w in problems)[:300])
        case("prose links that name a provider on its own hosts, in reference and inline form, and a bare URL",
             not any("declared for" in w for _, w in problems), "; ".join(w for _, w in problems)[:300])
        case("an HTML anchor that names no provider and offers no key is not a door",
             not any(pw[0].startswith("CONTRIBUTING.md") for pw in problems), "; ".join(w for _, w in problems)[:300])

    print("\nthe gate's own lists are read from the code they describe:")
    import rank
    on_readme = set(re.findall(r"<!--/?([A-Z0-9_-]+)-->", (ROOT / "README.md").read_text(encoding="utf-8")))
    case("rank.py yields a non-empty marker list", bool(G.MARKERS), str(G.MARKERS))
    case("every <!--X--> in the committed README is a marker rank.py writes", on_readme <= G.MARKERS,
         "on README but not in rank.py: %s" % sorted(on_readme - G.MARKERS))
    case("the label vocabulary is rank.py's, not a copy", G.LABELS == set(rank.LABELS) and G.RANKABLE == set(rank.RANKABLE)
         and G.SUMMABLE == set(rank.SUMMABLE))
    case("DRAWN is summable and not rankable, in rank.py and therefore here", "DRAWN" in G.SUMMABLE and "DRAWN" not in G.RANKABLE)
    rank_src = (ROOT / "bench" / "rank.py").read_text(encoding="utf-8")
    viab_src = (ROOT / "bench" / "gate_viability.py").read_text(encoding="utf-8")
    for name in sorted(G.GENERATED_PAGES):
        case("%s, exempt from the count check, is written whole by a generator" % name,
             '"%s"' % name in rank_src or '"%s"' % name in viab_src)
    case("the SOURCES-TABLE marker is the only hand-typed block, and only on SOURCES.md",
         G.page_markers(ROOT).get("SOURCES.md") == {G.SOURCES_MARKER} and G.SOURCES_MARKER not in G.MARKERS)
    test_rank_src = (ROOT / "bench" / "test_rank.py").read_text(encoding="utf-8")
    case("the golden folder the gate skips is the one test_rank.py compares byte for byte",
         'FIX = HERE / "tests" / "fixture"' in test_rank_src and 'GOLD = FIX / "golden"' in test_rank_src
         and G.GOLDEN_DIR == "bench/tests/fixture/golden")
    golden = sorted(p.stem for p in (ROOT / G.GOLDEN_DIR).glob("*.md")) if (ROOT / G.GOLDEN_DIR).exists() else []
    case("every golden block skipped is a marker rank.py writes and a block test_rank.py compares: %s" % golden,
         bool(golden) and all(s in G.MARKERS and '"%s"' % s in test_rank_src for s in golden))

    print("\n%d failures" % bad)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
