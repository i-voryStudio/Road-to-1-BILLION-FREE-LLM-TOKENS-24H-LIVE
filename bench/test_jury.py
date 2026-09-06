#!/usr/bin/env python3
"""Tests for the jury maths. No network, no keys, no API calls.

    python bench/test_jury.py

Agreement between judges is half the credibility of every quality score in this repo, so the number
that reports it has to be right in both directions: perfect agreement must read as perfect, a split
jury must read as split, and the difference between "they disagree" and "one is simply harsher" must
not be flattened, because those two call for different responses.

The anonymisation is tested too. It is the only thing making the jury blind, and a shuffle that is not
reproducible would mean nobody can check the key against the paragraphs.
"""
import json, subprocess, sys, tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import agreement
import judge as J


def jury_file(rows, judges=("a", "b")):
    return {"judges": [{"name": j, "family": "family-" + j} for j in judges],
            "lenses": sorted({r[1] for r in rows}),
            "verdicts": [{"id": pid, "lens": lens, "judge": jd, "score": sc, "reason": "because"}
                         for pid, lens, jd, sc in rows],
            "key": {pid: "prov | model-" + pid for pid, _, _, _ in rows}}


def run_agreement(data):
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "jury.json"
        p.write_text(json.dumps(data), encoding="utf-8")
        out = Path(tmp) / "agreement.md"
        r = subprocess.run([sys.executable, str(HERE / "agreement.py"), str(p), "--out", str(out)],
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
        return r.returncode, (r.stdout or "") + (r.stderr or ""), (out.read_text(encoding="utf-8") if out.exists() else "")


def main():
    failures = []
    nonlocal_checks = [0]

    def check(name, ok, detail=""):
        nonlocal_checks[0] += 1
        print("%s %s" % ("ok  " if ok else "FAIL", name))
        if not ok:
            failures.append((name, detail))

    # --- perfect agreement: gap 0
    rows = [(("P%02d" % i), "sounds_human", j, s)
            for i, s in enumerate([2, 5, 8, 9, 1], 1) for j, s in (("a", s), ("b", s))]
    code, out, md = run_agreement(jury_file(rows))
    check("perfect agreement reads as gap 0.00", "0.00" in md and "close agreement" in md, md[:300])

    # --- total disagreement: judges inverted
    rows = []
    for i, s in enumerate([0, 2, 5, 8, 10], 1):
        rows.append(("P%02d" % i, "sounds_human", "a", s))
        rows.append(("P%02d" % i, "sounds_human", "b", 10 - s))
    code, out, md = run_agreement(jury_file(rows))
    check("inverted judges read as a large gap",
          "do not define this lens the same way" in md, md[:300])
    check("inverted judges give negative correlation", "-1.00" in md or "-0.9" in md, md[:400])

    # --- same ranking, one judge harsher by a constant: must NOT read as disagreement about ranking
    rows = []
    for i, s in enumerate([1, 3, 5, 7, 9], 1):
        rows.append(("P%02d" % i, "sounds_human", "a", s))
        rows.append(("P%02d" % i, "sounds_human", "b", min(10, s + 3)))
    code, out, md = run_agreement(jury_file(rows))
    check("a consistently harsher judge is reported as strictness, not disagreement",
          "different strictness" in md, md[:400])

    # --- one judge only: nothing to compare, and it must say so rather than invent a number
    rows = [("P01", "sounds_human", "a", 5), ("P02", "sounds_human", "a", 7)]
    code, out, md = run_agreement(jury_file(rows, judges=("a",)))
    check("a single judge is refused, not averaged with itself",
          code == 1 and "nothing to compare" in out, out[:200])

    # --- a flat judge: correlation is undefined, and must not be printed as 0
    rows = []
    for i, s in enumerate([1, 4, 7, 9, 10], 1):
        rows.append(("P%02d" % i, "sounds_human", "a", s))
        rows.append(("P%02d" % i, "sounds_human", "b", 5))
    code, out, md = run_agreement(jury_file(rows))
    check("a judge who scores everything the same gives undefined correlation, not zero",
          "undefined" in md, md[:400])

    # --- the big disagreements must be listed, since they are the point of the page
    rows = []
    for i in range(1, 6):
        rows.append(("P%02d" % i, "sounds_human", "a", 9))
        rows.append(("P%02d" % i, "sounds_human", "b", 9 if i != 3 else 1))
    code, out, md = run_agreement(jury_file(rows))
    check("the paragraph they split on is named", "P03" in md.split("disagreed most")[-1], md[-500:])

    # --- anonymisation: reproducible, complete, and it really does hide the model
    paragraphs = [{"provider": "p%d" % i, "model": "m%d" % i, "text": "text %d" % i} for i in range(12)]
    k1, a1 = J.anonymise(list(paragraphs))
    k2, a2 = J.anonymise(list(paragraphs))
    check("the blind shuffle is reproducible", [x["id"] for x in a1] == [x["id"] for x in a2])
    check("every paragraph survives the shuffle", len(a1) == len(paragraphs) == len(k1))
    check("the anonymised text carries no model name",
          not any("m%d" % i in x["text"] for i in range(12) for x in a1 if x["text"] != "text %d" % i))
    check("the shuffle actually shuffles", [x["id"] for x in a1] != sorted(k1, key=lambda p: k1[p]))

    print("\n%d checks, %d failures" % (nonlocal_checks[0], len(failures)))
    for name, detail in failures:
        print("  %s\n      %s" % (name, detail.replace("\n", "\n      ")[:300]))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
