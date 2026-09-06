#!/usr/bin/env python3
"""Measure how much the judges agree, and publish it. Standard library only.

    python bench/agreement.py jury.json --out results/2026-09-06/agreement.md

Half of every quality score in this repo comes from a language model judging paragraphs. That is a
conflict of interest we cannot remove, only expose. The strongest way to expose it is to use more than
one judge, from different model families, and then say plainly how often they disagreed.

What is reported, per lens:

  mean gap        - the average distance between judges on the same paragraph, in points out of 10.
                    This is the number to read first. Under 1.5 is close agreement; over 3 means the
                    lens is measuring something the judges do not define the same way.
  correlation     - Pearson r on the paired scores. High r with a large gap means the judges rank
                    paragraphs the same way but on different parts of the scale: one is simply harsher.
                    That is a much milder problem than a low r, and the two are worth telling apart.
  worst cases     - the paragraphs they disagreed on most. These are the most interesting texts in the
                    whole corpus, because they are where "does this read like a person" stops being
                    obvious.

A lens where judges do not agree is not a broken lens. It is a finding, and it belongs in the open.
"""
import argparse, json, sys
from collections import defaultdict
from pathlib import Path


def pearson(xs, ys):
    n = len(xs)
    if n < 2:
        return None
    mx, my = sum(xs) / n, sum(ys) / n
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    dx = sum((x - mx) ** 2 for x in xs) ** 0.5
    dy = sum((y - my) ** 2 for y in ys) ** 0.5
    if dx == 0 or dy == 0:
        return None  # one judge gave the same score to everything: correlation is undefined, not zero
    return num / (dx * dy)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("jury", help="the JSON written by judge.py")
    ap.add_argument("--out", default=None, help="write a Markdown report here as well as printing it")
    a = ap.parse_args()

    jury = json.loads(Path(a.jury).read_text(encoding="utf-8"))
    verdicts = jury.get("verdicts", [])
    if not verdicts:
        print("no verdicts in %s" % a.jury)
        return 2

    judges = sorted({v.get("judge", "unnamed") for v in verdicts})
    if len(judges) < 2:
        print("only one judge (%s) - there is nothing to compare." % judges[0])
        print("Agreement needs at least two judges, ideally from different model families.")
        print("Run: python bench/judge.py <results> --api   with more than one judge in judges.json")
        return 1

    # scores[lens][paragraph][judge] = score
    scores = defaultdict(lambda: defaultdict(dict))
    for v in verdicts:
        scores[v["lens"]][v["id"]][v.get("judge", "unnamed")] = v["score"]

    families = {j.get("name"): j.get("family", "?") for j in jury.get("judges", [])}
    lines = ["# Judge agreement", "",
             "Judges: " + ", ".join("**%s** (%s)" % (j, families.get(j, "family not declared")) for j in judges),
             "",
             "Half of every quality score comes from a model judging text. This page is how far that can",
             "be trusted. The gap is the average distance between judges on the same paragraph, out of 10.",
             "", "| Lens | Paragraphs | Mean gap | Max gap | Correlation | Reading |", "|---|---|---|---|---|---|"]
    print("judges: %s" % ", ".join(judges))
    summary = {}

    for lens in sorted(scores):
        paired = [(pid, d) for pid, d in scores[lens].items() if len(d) >= 2]
        if not paired:
            continue
        a_name, b_name = judges[0], judges[1]
        xs = [d[a_name] for _, d in paired if a_name in d and b_name in d]
        ys = [d[b_name] for _, d in paired if a_name in d and b_name in d]
        gaps = [(abs(d[a_name] - d[b_name]), pid) for pid, d in paired if a_name in d and b_name in d]
        if not gaps:
            continue
        mean_gap = sum(g for g, _ in gaps) / len(gaps)
        max_gap, worst = max(gaps)
        r = pearson(xs, ys)
        reading = ("close agreement" if mean_gap < 1.5 else
                   "usable, but they weight it differently" if mean_gap < 3 else
                   "the judges do not define this lens the same way")
        if r is not None and r > 0.7 and mean_gap >= 1.5:
            reading = "same ranking, different strictness"
        summary[lens] = {"mean_gap": round(mean_gap, 2), "max_gap": max_gap,
                         "correlation": round(r, 2) if r is not None else None, "n": len(gaps)}
        lines.append("| `%s` | %d | **%.2f** | %d | %s | %s |"
                     % (lens, len(gaps), mean_gap, max_gap,
                        "%.2f" % r if r is not None else "undefined", reading))
        print("  %-24s n=%-3d gap %.2f (max %d)  r=%s  %s"
              % (lens, len(gaps), mean_gap, max_gap, "%.2f" % r if r is not None else "n/a", reading))

    lines += ["", "## Where they disagreed most", "",
              "These paragraphs are the most interesting texts in the corpus: they are where the question",
              "stops having an obvious answer. All of them are in `paragraphs-anonymised.md`.", ""]
    worst_all = []
    for lens in sorted(scores):
        for pid, d in scores[lens].items():
            if len(d) >= 2:
                lo, hi = min(d.values()), max(d.values())
                if hi - lo >= 3:
                    worst_all.append((hi - lo, lens, pid, dict(d)))
    worst_all.sort(reverse=True)
    if worst_all:
        lines += ["| Gap | Lens | Paragraph | Scores |", "|---|---|---|---|"]
        for gap, lens, pid, d in worst_all[:12]:
            lines.append("| **%d** | `%s` | %s | %s |"
                         % (gap, lens, pid, ", ".join("%s %s" % kv for kv in sorted(d.items()))))
    else:
        lines.append("No paragraph split the judges by 3 points or more on any lens.")

    lines += ["", "## What this does not tell you", "",
              "Agreement is not correctness. Two judges can agree and both be wrong, and they are more",
              "likely to agree with each other than either is to agree with a native speaker, because",
              "they are both language models. The honest use of this page is as a floor: where the judges",
              "disagree, the score is definitely soft. Where they agree, it might still be.", ""]

    report = "\n".join(lines) + "\n"
    if a.out:
        Path(a.out).parent.mkdir(parents=True, exist_ok=True)
        Path(a.out).write_text(report, encoding="utf-8", newline="\n")
        print("\nwrote %s" % a.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
