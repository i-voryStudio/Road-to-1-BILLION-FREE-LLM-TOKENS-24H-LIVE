#!/usr/bin/env python3
"""Build the main ranking: free LLM endpoints, sorted by what you can actually get done with them.

    python bench/rank.py --date 2026-09-06 --out .

Reads four data files, each with its own provenance, and writes README tables, RESULTS.md and
data/ranking.{json,csv}. Everything published comes from here, so two tables cannot disagree.

FIVE FILTERS, in the order a reader cares about them:

  1. VALUE = quality x volume          the headline. A brilliant model with 20 requests a day loses to
                                       a decent one with 2,400, and no other list ranks that way.
                                       Endpoints that need no key get a declared bonus.
  2. QUALITY                           from OFFICIAL benchmarks (bench/scores.py), never our own.
  3. VOLUME                            what you get per day, measured or declared, UNKNOWN if unknown.
  4. AUTH                              no key / free key. Zero friction is worth something real.
  5. PRIVACY COST                      what the free tier costs you in things that are not money:
                                       training on your prompts, human review, region restrictions.

WHY QUALITY IS IMPORTED AND EVERYTHING ELSE IS MEASURED

Running our own quality benchmark does not scale: free providers appear weekly and each would have to
be put through a full battery before it could be listed. Worse, a benchmark run by whoever publishes
the ranking is exactly what a careful reader should distrust. So:

    imported   what the MODEL can do        <- Artificial Analysis, Design Arena
    measured   what the PROVIDER gives you  <- quota, uptime, latency, auth, privacy

A new provider costs nothing to rate. Serve `qwen3.8-27b` and you inherit its published scores today.

THE VALUE FORMULA, stated so it can be argued with:

    value = coding_index x log10(1 + requests_per_day) x auth_bonus x answered_rate

log10 because the difference between 20 and 2,400 requests a day matters enormously, and the
difference between 2,400 and 24,000 much less: past a point you stop being the bottleneck.
auth_bonus is 1.25 for an endpoint needing no key at all. answered_rate is how often that provider
actually returned something when probed - a paper quota you cannot draw on is not a quota.
All three are choices, all three are visible here, and a row with UNKNOWN volume is NOT ranked: it
goes in its own table rather than being guessed at.
"""
import argparse, csv, json, math, re, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
NOAUTH_BONUS = 1.25


def load(path, what):
    p = Path(path)
    if not p.exists():
        print("missing %s (%s)" % (path, what))
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def volume_of(provider, model, limits):
    """(requests_per_day, confidence, evidence). UNKNOWN stays UNKNOWN."""
    p = (limits.get("providers") or {}).get(provider)
    if not p:
        return None, "UNKNOWN", "Provider not in limits.json."
    entry = (p.get("models") or {}).get(model) or p.get("all_models") or {}
    rpd = entry.get("rpd")
    conf = entry.get("rpd_confidence") or p.get("confidence", "UNKNOWN")
    bits = [p.get("caveat", "")]
    if rpd is None and p.get("free_models_combined"):
        tiers = p["free_models_combined"]
        rpd = min((v["rpd"] for v in tiers.values()), default=None)
        best = max((v["rpd"] for v in tiers.values()), default=None)
        if rpd != best:
            bits.append("What a NEW account gets; rises to %s/day under the conditions in LIMITS.md, "
                        "and is shared across all free models." % best)
    if entry.get("rpd_is_paid_plan"):
        conf = "PAID-PLAN"
        bits.append("This figure is the provider's %s plan, not its free tier."
                    % (p.get("rpd_plan") or "paid"))
    if rpd is None:
        conf = "UNKNOWN"
    if entry.get("note"):
        bits.append(entry["note"])
    if p.get("binding_limit"):
        bits.append("Binding limit: " + p["binding_limit"])
    if p.get("scope"):
        bits.append("Applies per %s." % p["scope"].upper())
    if p.get("volatile"):
        bits.append("VOLATILE: this figure moved under us at least once.")
    return rpd, conf, " ".join(b for b in bits if b).strip()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--date", required=True)
    ap.add_argument("--out", default=".")
    ap.add_argument("--providers", default=str(HERE / "providers.json"))
    ap.add_argument("--limits", default=str(HERE / "limits.json"))
    ap.add_argument("--privacy", default=str(HERE / "privacy.json"))
    ap.add_argument("--scores", default="data/scores.json")
    ap.add_argument("--reliability", default="data/reliability.json")
    a = ap.parse_args()

    providers = load(a.providers, "endpoints")
    limits = load(a.limits, "quotas")
    privacy = load(a.privacy, "privacy cost")
    scores = load(a.scores, "official benchmark scores - run bench/scores.py first")
    rel = load(a.reliability, "answered rates - run bench/reliability.py first") or {"providers": []}
    if not all([providers, limits, privacy, scores]):
        return 2
    # A published quota is not availability. A provider that refuses a third of your calls is worth a
    # third less than its paper number, and ranking on advertised figures alone rewards whoever
    # advertises hardest. Missing measurement means no penalty - we do not punish what we did not test.
    answered = {r["provider"]: r["answered_rate"] for r in rel.get("providers", [])}
    rel_note = {r["provider"]: r["note"] for r in rel.get("providers", [])}
    trap = rel.get("reasoning_trap", {})
    trapped = {(t["provider"], t["model"]) for t in trap.get("observed", []) if not t["had_switch"]}
    switched = {(t["provider"], t["model"]) for t in trap.get("already_switched_off_by_us", [])}
    out = Path(a.out)

    by_model = {(r["provider"], r["model"]): r for r in scores.get("matched", [])}

    rows, unranked = [], []
    for p in providers["providers"]:
        needs_key = bool(p.get("key_env"))
        priv = (privacy.get("providers") or {}).get(p["name"], {})
        for m in p["models"]:
            sc = by_model.get((p["name"], m["id"]), {})
            aa = sc.get("artificial_analysis", {})
            da = sc.get("design_arena", {})
            coding = aa.get("coding_index")
            rpd, conf, evidence = volume_of(p["name"], m["id"], limits)

            row = {
                "provider": p["name"], "model": m["id"],
                "auth": "KEY" if needs_key else "NO KEY",
                "coding_index": coding,
                "intelligence_index": aa.get("intelligence_index"),
                "agentic_index": aa.get("agentic_index"),
                "arena_elo": (da.get("codecategories") or {}).get("elo"),
                "scored_as": sc.get("matched_as"),
                "requests_per_day": rpd,
                "volume_confidence": conf,
                "volume_evidence": evidence,
                "trains_on_free_tier": priv.get("trains_on_free_tier", "UNKNOWN"),
                "human_review": priv.get("human_review", "UNKNOWN"),
                "region_restriction": priv.get("region_restriction", "UNKNOWN"),
                "privacy_source": priv.get("source"),
                "answered_rate": answered.get(p["name"]),
                "reliability_note": rel_note.get(p["name"]),
                "returned_empty_200": (p["name"], m["id"]) in trapped,
                "thinking_switch": m.get("extra_body") if (p["name"], m["id"]) in switched else None,
                "measured_at": a.date,
            }
            # Rankable only with BOTH halves. Half a fact is not a rank.
            if coding is not None and rpd:
                bonus = NOAUTH_BONUS if not needs_key else 1.0
                reliability = answered.get(p["name"], 1.0)   # untested means unpenalised
                row["value"] = round(coding * math.log10(1 + rpd) * bonus * reliability, 1)
                row["noauth_bonus_applied"] = bonus != 1.0
                row["reliability_applied"] = reliability
                rows.append(row)
            else:
                row["value"] = None
                row["why_unranked"] = ("no official benchmark score published for this model"
                                       if coding is None else
                                       "daily quota unknown - see LIMITS.md")
                unranked.append(row)

    rows.sort(key=lambda r: -r["value"])
    unranked.sort(key=lambda r: (r["why_unranked"], r["provider"]))

    (out / "data").mkdir(parents=True, exist_ok=True)
    (out / "data" / "ranking.json").write_text(json.dumps({
        "measured_at": a.date,
        "ranking_formula": "coding_index * log10(1 + requests_per_day) * %s if no key is needed" % NOAUTH_BONUS,
        "quality_source": scores.get("source"),
        "quality_fetched_on": scores.get("fetched_on"),
        "filters": ["1 value = quality x volume", "2 quality (official benchmarks)", "3 volume",
                    "4 auth", "5 privacy cost"],
        "ranked": rows, "unranked": unranked,
    }, indent=1, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")

    cols = ["provider", "model", "value", "auth", "coding_index", "intelligence_index", "arena_elo",
            "requests_per_day", "volume_confidence", "trains_on_free_tier", "region_restriction",
            "measured_at"]
    with open(out / "data" / "ranking.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows + unranked)

    def cell(v, dash="?"):
        return dash if v is None else v

    def privacy_flag(r):
        if r["trains_on_free_tier"] == "yes":
            return "**trains on your prompts**"
        if r["region_restriction"] not in ("UNKNOWN", None):
            return "region-restricted"
        return "unknown"

    L = ["# Full ranking", "",
         "Generated by `bench/rank.py` on **%s** - do not edit by hand." % a.date,
         "",
         "Quality is **imported** from official benchmarks (%s, fetched %s). We do not run it ourselves. "
         "Everything else - quota, auth, privacy cost - is measured or read from the provider's own terms."
         % (scores.get("source"), scores.get("fetched_on")),
         "",
         "`Value` = `coding_index x log10(1 + requests/day)`, times %s when the endpoint needs no key. "
         "A brilliant model you may call 20 times a day loses to a decent one you may call 2,400 times, "
         "which is the whole point of ranking this way." % NOAUTH_BONUS,
         "", "## 1. By value: quality x volume", "",
         "| # | Model | Provider | Value | Auth | Coding | Req/day | Evidence | Privacy |",
         "|---|---|---|---|---|---|---|---|---|"]
    for i, r in enumerate(rows, 1):
        L.append("| %d | `%s` | %s | **%s** | %s | %s | %s | %s | %s |"
                 % (i, r["model"], r["provider"], r["value"],
                    "**no key**" if r["auth"] == "NO KEY" else "key",
                    cell(r["coding_index"]), "{:,}".format(r["requests_per_day"]),
                    r["volume_confidence"], privacy_flag(r)))

    L += ["", "## 2. By quality alone (official benchmark scores)", "",
          "| Model | Provider | Coding | Intelligence | Agentic | Arena ELO | Scored as |",
          "|---|---|---|---|---|---|---|"]
    for r in sorted([x for x in rows + unranked if x["coding_index"] is not None],
                    key=lambda x: -x["coding_index"]):
        L.append("| `%s` | %s | **%s** | %s | %s | %s | `%s` |"
                 % (r["model"], r["provider"], r["coding_index"], cell(r["intelligence_index"]),
                    cell(r["agentic_index"]), cell(r["arena_elo"]), r["scored_as"]))

    L += ["", "## 3. By volume: what you get to burn", "",
          "| Model | Provider | Req/day | Evidence | Value |", "|---|---|---|---|---|"]
    for r in sorted([x for x in rows if x["requests_per_day"]], key=lambda x: -x["requests_per_day"]):
        L.append("| `%s` | %s | **{:,}** | %s | %s |".format(r["requests_per_day"])
                 % (r["model"], r["provider"], r["volume_confidence"], r["value"]))

    noauth = [r for r in rows + unranked if r["auth"] == "NO KEY"]
    L += ["", "## 4. Needs no key at all", ""]
    if noauth:
        L += ["| Model | Provider | Coding | Req/day |", "|---|---|---|---|"]
        for r in noauth:
            L.append("| `%s` | %s | %s | %s |" % (r["model"], r["provider"], cell(r["coding_index"]),
                                                  cell(r["requests_per_day"])))
    else:
        L.append("**None yet.** Every provider we measure today wants a key. Endpoints that need none "
                 "exist and are the most useful thing this list could add - see IMPROVEMENTS.md.")

    L += ["", "## 5. What the free tier costs you that is not money", "",
          "Training on your prompts, human review, and legal limits on where you may serve users. "
          "`UNKNOWN` means nobody has read that provider's terms yet - and UNKNOWN is the honest "
          "default here, because inventing a `no` would be the most damaging wrong answer this repo "
          "could publish.", "",
          "| Provider | Trains on your prompts | Human review | Region restriction | Source |",
          "|---|---|---|---|---|"]
    for name, pv in (privacy.get("providers") or {}).items():
        src = pv.get("source")
        L.append("| %s | %s | %s | %s | %s |"
                 % (name, pv.get("trains_on_free_tier", "UNKNOWN"), pv.get("human_review", "UNKNOWN"),
                    pv.get("region_restriction", "UNKNOWN"),
                    "[terms](%s)" % src if src else "not read yet"))

    L += ["", "## 6. Does it actually answer, and does it answer with anything", "",
          "A published quota is not availability, and a `200` is not an answer. Both are measured across "
          "every call in every published run - one sample, the calling accounts, not an uptime guarantee.", "",
          "| Provider | Answered | Empty 200 | 429 | 503 | Timeout | Reading |",
          "|---|---|---|---|---|---|---|"]
    for r in rel.get("providers", []):
        L.append("| %s | **%.0f%%** | %d | %d | %d | %d | %s |"
                 % (r["provider"], 100 * r["answered_rate"], r["empty_200"], r["rate_limited"],
                    r["overloaded"], r["timeout"], r["note"]))
    obs = trap.get("observed", [])
    if obs:
        L += ["", "### The reasoning trap", "",
              "A model that reasons can spend its entire token budget thinking and return an **empty "
              "message with HTTP 200**. The status code says success. There is no text in it. This is the "
              "single most expensive surprise on a free tier, because nothing looks wrong.", "",
              "Each provider family takes a different switch, and some take none:", "", "```"]
        for k, v in (trap.get("switches") or {}).items():
            L.append("%-44s %s" % (k, v))
        L += ["```", "",
              "Measured in our runs: **%d empty 200s, %d of them on models where no switch was set.**"
              % (len(obs), sum(1 for t in obs if not t["had_switch"])), "",
              "| Model | Provider | Switch was set | Probe |", "|---|---|---|---|"]
        for t in obs:
            L.append("| `%s` | %s | %s | %s |" % (t["model"], t["provider"],
                                                  "yes, and ignored" if t["had_switch"] else "**no**",
                                                  t["probe"]))
        sw = trap.get("already_switched_off_by_us", [])
        if sw:
            L += ["", "We already turn thinking off for **%d** of the models we call. Those switches are "
                      "in [`bench/providers.json`](bench/providers.json) and are the cheapest thing to "
                      "copy out of this repo." % len(sw)]

    if unranked:
        L += ["", "## Not ranked, and why", "",
              "A row needs both halves to be ranked: an official score AND a known quota. Half a fact "
              "is not a rank.", "",
              "| Model | Provider | Missing |", "|---|---|---|"]
        for r in unranked:
            L.append("| `%s` | %s | %s |" % (r["model"], r["provider"], r["why_unranked"]))

    (out / "RESULTS.md").write_text("\n".join(L) + "\n", encoding="utf-8", newline="\n")

    # The README table is GENERATED between markers. Hand-editing it is how a published number
    # drifts away from the data, which gate_claims.py then catches. Better to make drift impossible.
    readme = out / "README.md"
    if readme.exists() and rows:
        text = readme.read_text(encoding="utf-8")
        if "<!--RANKING-->" in text and "<!--/RANKING-->" in text:
            head = ("| # | Model | Provider | Value | Auth | Coding | Req/day | Note |\n"
                    "|---|---|---|---|---|---|---|---|\n")
            body = ""
            for i, r in enumerate(rows[:10], 1):
                note = ("**trains on your prompts**" if r["trains_on_free_tier"] == "yes"
                        else "returns empty 200s" if r["returned_empty_200"]
                        else "%.0f%% answered" % (100 * r["answered_rate"]) if r.get("answered_rate")
                        else r["volume_confidence"])
                body += "| %d | `%s` | %s | **%s** | %s | %s | %s | %s |\n" % (
                    i, r["model"], r["provider"], r["value"],
                    "**no key**" if r["auth"] == "NO KEY" else "key",
                    r["coding_index"], "{:,}".format(r["requests_per_day"]), note)
            block = "<!--RANKING-->" + chr(10) + head + body + "<!--/RANKING-->"
            text = re.sub(r"<!--RANKING-->.*?<!--/RANKING-->", lambda _: block, text, flags=re.S)
            readme.write_text(text, encoding="utf-8", newline=chr(10))
            print("regenerated the README table between its markers")
    print("ranked %d endpoints, %d unranked" % (len(rows), len(unranked)))
    if rows:
        print("  top: %s @ %s  value=%s (coding %s, %s/day%s)"
              % (rows[0]["model"], rows[0]["provider"], rows[0]["value"], rows[0]["coding_index"],
                 "{:,}".format(rows[0]["requests_per_day"]),
                 ", no key" if rows[0]["auth"] == "NO KEY" else ""))
    print("  no-key endpoints: %d" % len(noauth))
    print("wrote RESULTS.md, data/ranking.json, data/ranking.csv")
    return 0


if __name__ == "__main__":
    sys.exit(main())
