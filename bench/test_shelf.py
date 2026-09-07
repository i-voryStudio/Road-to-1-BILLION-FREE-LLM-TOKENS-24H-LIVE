#!/usr/bin/env python3
"""The headline number, recomputed from the raw files without bench/rank.py in the loop.

    python bench/test_shelf.py

bench/test_rank.py proves the generator on a fixture, and bench/gate_claims.py proves the pages agree with
data/capacity.json. Neither proves that data/capacity.json agrees with the files it was made from: a
multiplier slipped into rank.py would move the headline, regenerate every page to match, and leave both of
them green. This test closes that gap. It reads bench/limits.json, data/drawn.jsonl, data/capacity.json,
data/ranking.json and README.md, and checks, with its own arithmetic:

  1. the defensible figure is the sum of the four shelves, and each shelf is the sum of its providers;
  2. every provider's figure exists in the raw files under the label it carries: a MEASURED or DECLARED
     figure is a tpd the provider block holds; a DERIVED figure is a request cap x TOKENS_PER_REPLY or
     the derived block's own output_tokens_per_day or a Neuron division the block makes possible; a
     DRAWN figure is tokens_per_hour_drawn x 24 from a row that stated a rate, for a provider with no
     figure of the other three kinds and with free capacity that is not only a one-time grant;
  3. nothing PAID-PLAN or UNKNOWN is on the shelf, and no provider is on two shelves;
  4. the share, the multiple and the README's headline print exactly these numbers;
  5. capacity.json and ranking.json carry the same date.

Zero network. Exit 0 when every check holds, 1 otherwise.
"""
import json
import re
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
TOKENS_PER_REPLY = 500          # the constant rank.py derives with; restated here on purpose, so a change
TARGET = 1_000_000_000          # in one place fails the test until the other is changed too
SUMMABLE = ("MEASURED", "DECLARED", "DERIVED", "DRAWN")

failures = []


def check(cond, what):
    print(("  ok   " if cond else "  FAIL ") + what)
    if not cond:
        failures.append(what)


def load(rel):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def ints_under(obj, key):
    """Every integer stored under `key` anywhere inside obj (dicts and lists, any depth)."""
    out = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == key and isinstance(v, int) and not isinstance(v, bool):
                out.append(v)
            out.extend(ints_under(v, key))
    elif isinstance(obj, list):
        for v in obj:
            out.extend(ints_under(v, key))
    return out


def figures_for(block):
    """What the raw block can justify, by label, with the arithmetic done here."""
    tpd = set(ints_under(block, "tpd"))
    derived = {rpd * TOKENS_PER_REPLY for rpd in ints_under(block, "rpd")}
    d = block.get("derived") or {}
    if isinstance(d.get("output_tokens_per_day"), int):
        derived.add(d["output_tokens_per_day"])
    neurons = (block.get("free_allocation") or {}).get("neurons_per_day")
    for ex in (block.get("neuron_cost_examples") or {}).values():
        price = (ex or {}).get("output_per_million")
        if isinstance(neurons, int) and isinstance(price, int) and price > 0:
            derived.add(int(neurons / price * 1_000_000))
    return {"MEASURED": tpd, "DECLARED": tpd, "DERIVED": derived}


def main():
    cap = load("data/capacity.json")
    limits = load("bench/limits.json")["providers"]
    ranking = load("data/ranking.json")
    drawn = [json.loads(l) for l in (ROOT / "data" / "drawn.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    print("=== the four shelves ===")
    shelf = cap["daily_shelf"]
    defensible = cap["defensible_tokens_per_day"]
    check(tuple(cap["summable_labels"]) == SUMMABLE, "capacity.json names exactly the four summable labels")
    check(sum(shelf[k.lower()]["tokens_per_day"] for k in SUMMABLE) == defensible,
          "defensible = measured + declared + derived + drawn (%s)" % "{:,}".format(defensible))
    per = cap["per_provider"]
    on_shelf = {}
    for label in SUMMABLE:
        s = shelf[label.lower()]
        total = sum(per[p]["daily_tokens"] for p in s["providers"] if p in per)
        check(total == s["tokens_per_day"], "%s shelf %s is the sum of its %d providers" % (label, "{:,}".format(s["tokens_per_day"]), len(s["providers"])))
        for p in s["providers"]:
            check(p in per and per[p]["confidence"] == label, "%s carries the %s label in per_provider" % (p, label))
            check(p not in on_shelf, "%s is on one shelf only" % p)
            on_shelf[p] = label

    print("=== every figure is in the raw files ===")
    drawn_rate = {}
    for r in drawn:
        if r.get("tokens_per_hour_drawn") is not None:
            drawn_rate.setdefault(r["provider"], set()).add(int(r["tokens_per_hour_drawn"]) * 24)
    for p, label in sorted(on_shelf.items()):
        figure = per[p]["daily_tokens"]
        block = limits.get(p) or {}
        justified = figures_for(block)
        if label == "DRAWN":
            others = justified["MEASURED"] | justified["DERIVED"]
            check(not others, "%s: DRAWN only where no tpd, request cap or derived figure exists (found %s)" % (p, sorted(others)))
            grant_only = bool((block.get("one_time") or {}).get("tokens")) and not others
            check(not grant_only or figure == 0, "%s: a one-time grant is not a day, so its draw is not counted" % p)
            check(figure in drawn_rate.get(p, set()),
                  "%s: %s = tokens_per_hour_drawn x 24 of a drawn.jsonl row that stated a rate" % (p, "{:,}".format(figure)))
        else:
            check(figure in justified[label],
                  "%s: %s %s is a figure bench/limits.json can justify under that label (%s)"
                  % (p, label, "{:,}".format(figure), sorted(justified[label]) or "nothing"))
    for p, row in per.items():
        if row["confidence"] in SUMMABLE:
            check(p in on_shelf, "%s carries a summable label and is on a shelf" % p)
        else:
            check(p not in on_shelf, "%s (%s) is not on a shelf" % (p, row["confidence"]))
    for p in cap.get("paid_plan_per_provider", {}) if isinstance(cap.get("paid_plan_per_provider"), dict) else cap.get("paid_plan_per_provider", []):
        check(p not in on_shelf, "%s is PAID-PLAN and not on a shelf" % p)
    for p in cap.get("providers_with_no_daily_figure", []):
        check(p not in on_shelf, "%s has no daily figure and is not on a shelf" % p)
    tracked = set(limits)
    check(set(on_shelf) | set(cap.get("providers_with_no_daily_figure", [])) <= tracked,
          "every provider counted or listed as having no figure is in bench/limits.json")
    for r in drawn:
        rate = r.get("tokens_per_hour_drawn")
        if rate is not None and r["provider"] not in on_shelf:
            block = limits.get(r["provider"]) or {}
            j = figures_for(block)
            reason = "a figure of another kind" if (j["MEASURED"] | j["DERIVED"]) else (
                "a one-time grant" if (block.get("one_time") or {}).get("tokens") else "")
            check(bool(reason), "%s drew %s an hour and is not counted: %s" % (r["provider"], "{:,}".format(rate), reason or "NO REASON FOUND"))

    print("=== the numbers on the page ===")
    share = round(defensible / TARGET * 100, 2)
    check(abs(cap["share_of_target_pct"] - share) < 0.006, "share_of_target_pct %s = defensible / target" % cap["share_of_target_pct"])
    mult = round(TARGET / defensible, 1) if defensible else None
    check(cap.get("multiple_still_needed") == mult, "multiple_still_needed %s = target / defensible" % cap.get("multiple_still_needed"))
    m = re.search(r"\| \*\*Tokens a day this list can defend\*\* \| \*\*([\d,]+)\*\* \|", readme)
    check(bool(m) and int(m.group(1).replace(",", "")) == defensible, "README headline box prints the defensible figure")
    m = re.search(r"\*\*Roughly ([\d,]+) quality tokens a day\*\*", readme)
    check(bool(m) and int(m.group(1).replace(",", "")) == defensible, "README road paragraph prints the defensible figure")
    m = re.search(r"\| \*\*Share of it\*\* \| \*\*([\d.]+)%\*\* \|", readme)
    check(bool(m) and abs(float(m.group(1)) - share) < 0.06, "README share matches defensible / target")
    check(cap["target_tokens_per_day"] == TARGET, "the target is %s" % "{:,}".format(TARGET))
    check(cap["date"] == ranking.get("measured_at"), "capacity.json and ranking.json carry the same date (%s)" % cap["date"])

    print()
    if failures:
        print("%d FAILURES:" % len(failures))
        for f in failures:
            print("  FAIL", f)
        return 1
    print("every headline figure recomputes from the raw files")
    return 0


if __name__ == "__main__":
    sys.exit(main())
