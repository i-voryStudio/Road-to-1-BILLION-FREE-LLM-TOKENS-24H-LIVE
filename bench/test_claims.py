#!/usr/bin/env python3
"""Calibrate the claims gate in both directions, on a copy of the real pages. No network.

    python bench/test_claims.py

Each case copies the repo's published pages and data into a temp dir, plants ONE edit a careless or
hostile pull request would make, runs the gate on the copy, and asserts the named check fires. Then the
untouched copy must pass. A gate that has never been watched failing is a green light, not a gate.
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


def first_ranked_row(text):
    m = re.search(r"<!--RANKING-->\n(.*?)\n<!--/RANKING-->", text, re.S)
    rows = [l for l in m.group(1).split("\n") if l.startswith("| 1 |")]
    return rows[0]


def main():
    bad = 0

    def case(label, ok, detail=""):
        nonlocal bad
        print("  %-4s %s%s" % ("ok" if ok else "FAIL", label, ("  -> " + detail[:160]) if (detail and not ok) else ""))
        if not ok:
            bad += 1

    def planted(label, rel, fn, must_mention):
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            copy_repo(tmp)
            edit(tmp, rel, fn)
            checked, problems = G.run(tmp)
            hit = any(must_mention in what for _, what in problems)
            case(label, hit, "; ".join(w for _, w in problems)[:300] or "no problem raised")

    print("edits that MUST be refused:")
    planted("a value typed by hand in the ranking", "README.md",
            lambda t: t.replace(first_ranked_row(t), first_ranked_row(t).replace("**", "**9", 1), 1), "published as")
    planted("the formula edited on one page", "RESULTS.md",
            lambda t: t.replace("log10(1 + daily_tokens / 500)", "log10(1 + requests_per_day)"), "value formula")
    planted("PAID-PLAN in a ranked row", "README.md",
            lambda t: t.replace(first_ranked_row(t), first_ranked_row(t).replace("| MEASURED |", "| PAID-PLAN |", 1), 1), "ranked row carries PAID-PLAN")
    planted("an invented label", "ALL-ENDPOINTS.md",
            lambda t: t.replace("| MEASURED |", "| CONFIRMED |", 1), "is not one of")
    planted("a ? for Answers in a ranked row", "README.md",
            lambda t: t.replace(first_ranked_row(t), re.sub(r"\| [0-9]+ of [0-9]+ in 14 days[^|]*\|", "| ? |", first_ranked_row(t), 1), 1), "prints ? for Answers")
    planted("a Get key door on a lookalike domain", "README.md",
            lambda t: t.replace(first_ranked_row(t), re.sub(r"\]\(https://[^)]+\)", "](https://xkiro.com.evil.example/keys)", first_ranked_row(t), 1), 1), "neither its API domain")
    planted("a provider link in the capacity table pointing elsewhere", "README.md",
            lambda t: t.replace("[cerebras](https://cloud.cerebras.ai)", "[cerebras](https://cerebras-keys.example)", 1), "neither its API domain")
    planted("the headline figure typed by hand", "README.md",
            lambda t: re.sub(r"(\| \*\*Tokens a day this list can defend\*\* \| \*\*)([\d,]+)(\*\*)", r"\g<1>999,999,999\3", t), "defensible figure")
    planted("a provider row deleted from the capacity table", "README.md",
            lambda t: re.sub(r"\n\| \*\*\[kenari\]\([^\n]*", "", t, 1), "missing from the CAPACITY block")
    planted("a count typed into README prose", "README.md",
            lambda t: t.replace("## How to read any row of this list", "We track 12 providers today.\n\n## How to read any row of this list", 1), "count in prose")
    planted("a count typed into SECURITY prose", "SECURITY.md",
            lambda t: t.replace("# Security", "# Security\n\nIt sends requests to ten hosts.", 1), "count in prose")
    planted("a link to a file that does not exist", "README.md",
            lambda t: t.replace("[RESULTS.md](RESULTS.md)", "[RESULTS.md](RESULTS-old.md)", 1), "does not exist")

    print("\nwhat MUST pass:")
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        copy_repo(tmp)
        checked, problems = G.run(tmp)
        case("an untouched copy of the published pages", not problems, "; ".join(w for _, w in problems)[:300])
        edit(tmp, "README.md", lambda t: t.replace("<!--COUNTS-->", "<!--COUNTS-->\nGenerated: 99 providers and 99 endpoints.", 1))
        checked, problems = G.run(tmp)
        case("a count INSIDE a generated block is the generator's business, not the gate's",
             not any("count in prose" in w for _, w in problems))
        edit(tmp, "LIMITS.md", lambda t: t.replace("| DECLARED |", "| DECLARED; per model, largest shown |", 1))
        checked, problems = G.run(tmp)
        case("a label followed by a note is still a label", not any("is not one of" in w for _, w in problems))

    print("\n%d failures" % bad)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
