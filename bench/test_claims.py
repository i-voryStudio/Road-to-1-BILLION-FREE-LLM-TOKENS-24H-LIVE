#!/usr/bin/env python3
"""Calibrate the claims gate in both directions, on a copy of the real pages. No network.

    python bench/test_claims.py

Each case copies the repo's published pages and data into a temp dir, plants ONE edit a careless or
hostile pull request would make, runs the gate on the copy, and asserts the named check fires. Then the
untouched copy must pass. A gate that has never been watched failing is a green light, not a gate.

The three holes the second review found each have a planted case here: an invented <!--NOTE--> block
hiding a count, a brand-new BEST.md with a fake score row and a lookalike door, and a hand-typed star
count on SOURCES.md outside the block that declares it.
"""
import json, re, shutil, sys, tempfile
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
    (tmp / rel).write_text(text, encoding="utf-8", newline="\n")


def first_ranked_row(text):
    m = re.search(r"<!--RANKING-->\n(.*?)\n<!--/RANKING-->", text, re.S)
    rows = [l for l in m.group(1).split("\n") if l.startswith("| 1 |")]
    return rows[0]


def a_real_ranked(tmp):
    """(provider, model, value) of the first ranked row in the copy's data, for a row that must pass on its own."""
    r = json.loads((tmp / "data" / "ranking.json").read_text(encoding="utf-8"))["ranked"][0]
    return r["provider"], r["model"], r["value"]


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


def main():
    bad = 0

    def case(label, ok, detail=""):
        nonlocal bad
        print("  %-4s %s%s" % ("ok" if ok else "FAIL", label, ("  -> " + detail[:200]) if (detail and not ok) else ""))
        if not ok:
            bad += 1

    def planted(label, plant, *must_mention):
        """plant(tmp) edits the copy; every phrase in must_mention has to appear among the problems."""
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            copy_repo(tmp)
            plant(tmp)
            checked, problems = G.run(tmp)
            whats = [what for _, what in problems]
            missing = [m for m in must_mention if not any(m in w for w in whats)]
            case(label, not missing, ("not raised: %r; raised: " % missing) + ("; ".join(whats)[:300] or "nothing"))

    def on(rel, fn):
        return lambda tmp: edit(tmp, rel, fn)

    print("edits that MUST be refused:")
    planted("a value typed by hand in the ranking",
            on("README.md", lambda t: t.replace(first_ranked_row(t), first_ranked_row(t).replace("**", "**9", 1), 1)),
            "published as")
    planted("the formula edited on one page",
            on("RESULTS.md", lambda t: t.replace("log10(1 + daily_tokens / 500)", "log10(1 + requests_per_day)")),
            "value formula")
    planted("PAID-PLAN in a ranked row",
            on("README.md", lambda t: t.replace(first_ranked_row(t), first_ranked_row(t).replace("| MEASURED |", "| PAID-PLAN |", 1), 1)),
            "ranked row carries PAID-PLAN")
    planted("an invented label",
            on("ALL-ENDPOINTS.md", lambda t: t.replace("| MEASURED |", "| CONFIRMED |", 1)), "is not one of")
    planted("a ? for Answers in a ranked row",
            on("README.md", lambda t: t.replace(first_ranked_row(t), re.sub(r"\| [0-9]+ of [0-9]+ in 14 days[^|]*\|", "| ? |", first_ranked_row(t), 1), 1)),
            "prints ? for Answers")
    planted("a Get key door on a lookalike domain",
            on("README.md", lambda t: t.replace(first_ranked_row(t), re.sub(r"\]\(https://[^)]+\)", "](https://xkiro.com.evil.example/keys)", first_ranked_row(t), 1), 1)),
            "neither its API domain")
    planted("a provider link in the capacity table pointing elsewhere",
            on("README.md", lambda t: t.replace("[cerebras](https://cloud.cerebras.ai)", "[cerebras](https://cerebras-keys.example)", 1)),
            "neither its API domain")
    planted("the headline figure typed by hand",
            on("README.md", lambda t: re.sub(r"(\| \*\*Tokens a day this list can defend\*\* \| \*\*)([\d,]+)(\*\*)", r"\g<1>999,999,999\3", t)),
            "defensible figure")
    planted("a provider row deleted from the capacity table",
            on("README.md", lambda t: re.sub(r"\n\| \*\*\[kenari\]\([^\n]*", "", t, 1)), "missing from the CAPACITY block")
    planted("a count typed into README prose",
            on("README.md", lambda t: t.replace("## How to read any row of this list", "We track 12 providers today.\n\n## How to read any row of this list", 1)),
            "'12 providers' is a count in prose")
    planted("a count of models typed into README prose",
            on("README.md", lambda t: t.replace("## How to read any row of this list", "We list 250 models.\n\n## How to read any row of this list", 1)),
            "'250 models' is a count in prose")
    planted("a count of keys typed into README prose",
            on("README.md", lambda t: t.replace("## How to read any row of this list", "Each runner holds two keys.\n\n## How to read any row of this list", 1)),
            "'two keys' is a count in prose")
    planted("a count with an adjective between ('12 free providers')",
            on("README.md", lambda t: t.replace("## How to read any row of this list", "We track 12 free providers.\n\n## How to read any row of this list", 1)),
            "'12 free providers' is a count in prose")
    planted("a count wrapped over a line break ('350+' then 'providers')",
            on("README.md", lambda t: t.replace("## How to read any row of this list", "A catalogue of 350+\nproviders informed this list.\n\n## How to read any row of this list", 1)),
            "'350+ providers' is a count in prose")
    planted("a count typed into SECURITY prose",
            on("SECURITY.md", lambda t: t.replace("# Security", "# Security\n\nIt sends requests to ten hosts.", 1)),
            "'ten hosts' is a count in prose")
    planted("a count typed into CONTRIBUTING prose",
            on("CONTRIBUTING.md", lambda t: t.replace("# Contributing\n", "# Contributing\n\nEighteen providers are listed.\n", 1)),
            "'Eighteen providers' is a count in prose")
    planted("a link to a file that does not exist",
            on("README.md", lambda t: t.replace("[RESULTS.md](RESULTS.md)", "[RESULTS.md](RESULTS-old.md)", 1)), "does not exist")
    planted("a broken link in the language-pack README, resolved from its own folder",
            on("bench/languages/README.md", lambda t: t.replace("Copy `ro.json`", "Copy [`ro.json`](ro-missing.json)", 1)),
            "ro-missing.json, which does not exist")
    planted("an invented <!--NOTE--> block with a count inside it",
            on("README.md", lambda t: t.replace("## How to read any row of this list",
                                                "<!--NOTE-->\nWe track 99 providers across 400 endpoints.\n<!--/NOTE-->\n\n## How to read any row of this list", 1)),
            "<!--NOTE--> is not a generated block", "'99 providers' is a count in prose", "'400 endpoints' is a count in prose")
    planted("a marker the generator does write, but on a page it never writes to",
            on("SECURITY.md", lambda t: t.replace("# Security", "# Security\n\n<!--COUNTS-->\nWe scan 12 hosts.\n<!--/COUNTS-->", 1)),
            "<!--COUNTS--> is not a generated block", "'12 hosts' is a count in prose")
    planted("the SOURCES-TABLE block used on README to hide a count",
            on("README.md", lambda t: t.replace("## How to read any row of this list",
                                                "<!--SOURCES-TABLE-->\nWe track 99 providers.\n<!--/SOURCES-TABLE-->\n\n## How to read any row of this list", 1)),
            "<!--SOURCES-TABLE--> is not a generated block", "'99 providers' is a count in prose")

    def best_md(tmp):
        prov, model, value = a_real_ranked(tmp)
        write(tmp, "BEST.md", "# Best\n\n| # | Model | Provider | Value | Get key |\n|---|---|---|---|---|\n"
                              "| 1 | `gpt-5` | evilrouter | **999.9** | [get a key](https://evil.example/keys) |\n"
                              "| 2 | `%s` | %s | **%s** | [Get key](https://%s.com.evil.example/keys) |\n" % (model, prov, value, prov))
    planted("a new BEST.md with a fake score row, an unknown provider and a lookalike door", best_md,
            "model 'gpt-5' is scored here but is not in the data",
            "provider 'evilrouter' appears in a table but is not in bench/providers.json",
            "neither its API domain")
    planted("a new page linking to a file that does not exist",
            lambda tmp: write(tmp, "NOTES.md", "# Notes\n\nSee [the plan](PLAN.md).\n"), "PLAN.md, which does not exist")
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
        checked, problems = G.run(tmp)
        case("an untouched copy of the published pages", not problems, "; ".join("%s: %s" % pw for pw in problems)[:400])
        case("the gate opens every *.md at the root, and the language-pack README",
             set(checked) >= {p.name for p in ROOT.glob("*.md")} and "bench/languages/README.md" in checked, str(checked))
        edit(tmp, "README.md", lambda t: t.replace("<!--COUNTS-->", "<!--COUNTS-->\nGenerated: 99 providers and 99 endpoints.", 1))
        checked, problems = G.run(tmp)
        case("a count INSIDE a generated block is the generator's business, not the gate's",
             not any("'99 providers'" in w or "'99 endpoints'" in w for _, w in problems))
        edit(tmp, "LIMITS.md", lambda t: t.replace("| DECLARED |", "| DECLARED; per model, largest shown |", 1))
        checked, problems = G.run(tmp)
        case("a label followed by a note is still a label", not any("is not one of" in w for _, w in problems))
        edit(tmp, "bench/languages/README.md", lambda t: t.replace("Copy `ro.json`", "Copy [`ro.json`](ro.json)", 1))
        checked, problems = G.run(tmp)
        case("a link in the language-pack README to a file beside it", not any("does not exist" in w for _, w in problems))
        write(tmp, "SOURCES.md", HONEST_SOURCES)
        checked, problems = G.run(tmp)
        case("star counts and 'Six for six' INSIDE the SOURCES-TABLE block",
             not any(pw[0].startswith("SOURCES.md") for pw in problems), "; ".join(w for _, w in problems)[:300])
        edit(tmp, "METHOD.md", lambda t: t.replace("# Method\n", "# Method\n\nThe archived run covered four models.\n", 1))
        checked, problems = G.run(tmp)
        case("a count in METHOD.md's archived-run prose is history and stays",
             not any(pw[0].startswith("METHOD.md") and "count in prose" in pw[1] for pw in problems))

    print("\nthe gate's own lists are read from the code they describe:")
    known = G.known_markers(ROOT)
    on_readme = set(re.findall(r"<!--/?([A-Z0-9_-]+)-->", (ROOT / "README.md").read_text(encoding="utf-8")))
    case("rank.py yields a non-empty marker list", bool(known), str(known))
    case("every <!--X--> in the committed README is a marker rank.py writes", on_readme <= known,
         "on README but not in rank.py: %s" % sorted(on_readme - known))
    rank_src = (ROOT / "bench" / "rank.py").read_text(encoding="utf-8")
    viab_src = (ROOT / "bench" / "gate_viability.py").read_text(encoding="utf-8")
    for name in sorted(G.GENERATED_PAGES):
        case("%s, exempt from the count check, is written whole by a generator" % name,
             '"%s"' % name in rank_src or '"%s"' % name in viab_src)
    case("the SOURCES-TABLE marker is the only hand-typed block, and only on SOURCES.md",
         G.page_markers(ROOT).get("SOURCES.md") == {G.SOURCES_MARKER} and G.SOURCES_MARKER not in known)

    print("\n%d failures" % bad)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
