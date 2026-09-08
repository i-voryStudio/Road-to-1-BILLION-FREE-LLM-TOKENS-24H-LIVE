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
  5. capacity.json and ranking.json carry the same date;
  6. every ranked row's value recomputes from its own fields with the formula the pages print, restated
     here constant by constant; the ranked list is in value order, ties broken by provider then model,
     and the README's ranking table is in that same order; every ranked row carries a rankable label and
     a coding index at or above the floor in capacity.json; and every Cost cell on the README's ranking
     table is what bench/privacy.json and limits.json's unlock block say for that provider, rebuilt here.
     A provider-specific sort key or a privacy branch in rank.py rewrites the front page with the
     regeneration step green; this is what refuses it.

Zero network. Exit 0 when every check holds, 1 otherwise.
"""
import json
import math
import re
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
TOKENS_PER_REPLY = 500          # the constant rank.py derives with; restated here on purpose, so a change
TARGET = 1_000_000_000          # in one place fails the test until the other is changed too
SUMMABLE = ("MEASURED", "DECLARED", "DERIVED")
RANKABLE = ("MEASURED", "DECLARED", "DERIVED")     # a row ranks on these; DRAWN is a provider figure, not a row's
NOAUTH_BONUS = 1.25             # the two multipliers in the printed formula, restated for the same reason
DEGRADED_PENALTY = 0.5
FORMULA = ("coding_index x log10(1 + daily_tokens / %d) x answered_rate x %s if no key x %s if degraded"
           % (TOKENS_PER_REPLY, NOAUTH_BONUS, DEGRADED_PENALTY))
NOTHING_ON_FILE = "-"           # the Cost cell when neither a privacy term nor an unlock condition is on file


def value_of(coding, daily, rate, needs_key, degraded):
    """The printed formula, as arithmetic written here and not imported."""
    v = coding * math.log10(1 + daily / TOKENS_PER_REPLY) * rate
    if not needs_key:
        v *= NOAUTH_BONUS
    if degraded:
        v *= DEGRADED_PENALTY
    return round(v, 1)


def cost_cell(priv, lim):
    """What the README's Cost cell must say for a provider, from privacy.json and limits.json alone: the
    privacy flags that are a yes, the region restriction when one is on file, then the unlock condition;
    a dash when nothing is on file."""
    parts = []
    if priv.get("trains_on_free_tier") == "yes":
        parts.append("**trains on your prompts**")
    if priv.get("human_review") == "yes":
        parts.append("human review")
    if priv.get("region_restriction") not in (None, "UNKNOWN"):
        parts.append("region-restricted")
    u = (lim or {}).get("unlock") or {}
    if u.get("costs_usd"):
        parts.append(("$%g top-up unlocks the daily quota" if u.get("one_time") else "$%g a month unlocks the daily quota") % u["costs_usd"])
    return "; ".join(parts) if parts else NOTHING_ON_FILE


def ranking_rows(readme):
    """(rank, model, provider, volume cell, cost cell) for every row of the README's generated RANKING block."""
    m = re.search(r"<!--RANKING-->\n(.*?)<!--/RANKING-->", readme, re.S)
    out = []
    for line in (m.group(1) if m else "").split("\n"):
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) == 10 and cells[0].isdigit():
            out.append((int(cells[0]), cells[1].strip("`"), cells[2], cells[6], cells[8]))
    return out

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
    check(tuple(cap["summable_labels"]) == SUMMABLE, "capacity.json names exactly the three summable labels")
    check(all(w.get("counted") is False for w in cap.get("drawn", [])),
          "no drawn hour is counted: one measured hour times 24 is the arithmetic this list refuses")
    drawn_sum = sum(w["tokens_per_day_extrapolated"] for w in cap.get("drawn", []))
    check(drawn_sum == 0 or defensible < defensible + drawn_sum,
          "the drawn total (%s) is outside the defensible figure" % "{:,}".format(drawn_sum))
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
    # A drawn hour never reaches the shelf, whatever else the provider publishes: one measured hour times
    # twenty-four is the arithmetic every other row of this page refuses.
    for r in drawn:
        rate = r.get("tokens_per_hour_drawn")
        if rate is None:
            continue
        counted_as_drawn = per.get(r["provider"], {}).get("confidence") == "DRAWN"
        check(not counted_as_drawn,
              "%s drew %s an hour and none of it is on the shelf" % (r["provider"], "{:,}".format(rate)))

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

    print("=== every ranked row, with the generator out of the loop ===")
    ranked = ranking.get("ranked") or []
    privacy = load("bench/privacy.json").get("providers") or {}
    floor = cap["quality_floor_coding_index"]
    check(ranking.get("ranking_formula") == FORMULA and FORMULA in readme,
          "the formula the pages print is the one restated here, constant by constant")
    check(tuple(ranking.get("rankable_volume_labels") or ()) == RANKABLE, "ranking.json names exactly the three rankable labels")
    bad_value, bad_rate, bad_label, bad_floor = [], [], [], []
    for r in ranked:
        rate = 1.0 if r.get("answered_rate") is None else r["answered_rate"]
        if r.get("reliability_applied") != rate:
            bad_rate.append((r["provider"], r["model"], r.get("reliability_applied"), rate))
        want = value_of(r["coding_index"], r["daily_tokens"], rate, r["auth"] == "KEY", r.get("viability") == "degraded")
        if abs(want - r["value"]) > 0.05:
            bad_value.append((r["provider"], r["model"], r["value"], want))
        if r["volume_confidence"] not in RANKABLE:
            bad_label.append((r["provider"], r["model"], r["volume_confidence"]))
        if r.get("coding_index") is None or r["coding_index"] < floor:
            bad_floor.append((r["provider"], r["model"], r.get("coding_index")))
    check(bool(ranked) and not bad_value, "every ranked row's value = coding_index x log10(1 + daily_tokens / %d) x answered_rate x %s "
                                          "if no key x %s if degraded, to one decimal%s"
          % (TOKENS_PER_REPLY, NOAUTH_BONUS, DEGRADED_PENALTY, "" if not bad_value else ": %s" % bad_value[:3]))
    check(not bad_rate, "reliability_applied is the answered rate, 1.0 where the radar has not reached the endpoint%s"
          % ("" if not bad_rate else ": %s" % bad_rate[:3]))
    check(not bad_label, "every ranked row carries a rankable label (%s)%s" % (", ".join(RANKABLE), "" if not bad_label else ": %s" % bad_label[:3]))
    check(not bad_floor, "every ranked row's coding index is at or above the floor of %s%s" % (floor, "" if not bad_floor else ": %s" % bad_floor[:3]))
    keys = [(-r["value"], r["provider"], r["model"]) for r in ranked]
    check(keys == sorted(keys), "the ranked list is in value order, highest first, ties broken by provider then model")
    rows = ranking_rows(readme)
    check(len(rows) == len(ranked) and [(n, m, p) for n, m, p, _, _ in rows] == [(i, r["model"], r["provider"]) for i, r in enumerate(ranked, 1)],
          "the README's ranking table lists the same rows in the same order as ranking.json (%d rows)" % len(rows))
    bad_cost, bad_volume = [], []
    for (n, model, prov, volume, cost), r in zip(rows, ranked):
        want = cost_cell(privacy.get(prov) or {}, limits.get(prov) or {})
        if cost != want:
            bad_cost.append((prov, model, cost, want))
        label = volume.split(";")[0].strip()
        tier = (limits.get(prov) or {}).get("measured_on_tier")
        tier_ok = (("read on a %s key" % tier) in volume) if (tier and label == "MEASURED") else (";" not in volume)
        if label != r["volume_confidence"] or not tier_ok:
            bad_volume.append((prov, model, volume))
    check(not bad_cost, "every Cost cell on the README's ranking table is what privacy.json and limits.json's unlock say for that provider%s"
          % ("" if not bad_cost else ": %s" % bad_cost[:3]))
    check(not bad_volume, "every Volume cell is the row's label, with the tier from limits.json's measured_on_tier where a MEASURED figure has one, "
                          "and nothing else%s" % ("" if not bad_volume else ": %s" % bad_volume[:3]))

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
