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
# A request budget and a token budget are the same shelf measured in different units, and whichever
# runs out first is your real ceiling. To compare them we need one number for the size of a reply.
# 500 output tokens is roughly a substantial paragraph, and it is DECLARED here rather than buried:
# change it and every volume figure moves, which is exactly why it should be visible.
TOKENS_PER_REPLY = 500


def load(path, what):
    p = Path(path)
    if not p.exists():
        print("missing %s (%s)" % (path, what))
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def daily_tokens(rpd, tpd):
    """The volume you can actually draw in a day, in tokens, from whichever limit binds first.

    A provider offering 2,400 requests but 1,000,000 tokens gives you the smaller of the two once a
    request is worth TOKENS_PER_REPLY. Ranking on requests alone hid the largest free allowance in this
    whole list: xkiro publishes 5M tokens a day and no request cap at all, so it did not appear.
    """
    from_requests = rpd * TOKENS_PER_REPLY if rpd else None
    candidates = [x for x in (tpd, from_requests) if x]
    return min(candidates) if candidates else None


def volume_of(provider, model, limits):
    """(requests_per_day, tokens_per_day, confidence, evidence). UNKNOWN stays UNKNOWN."""
    p = (limits.get("providers") or {}).get(provider)
    if not p:
        return None, None, "UNKNOWN", "Provider not in limits.json."
    entry = (p.get("models") or {}).get(model) or p.get("all_models") or {}
    rpd, tpd = entry.get("rpd"), entry.get("tpd")
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
    if rpd is None and tpd is None:
        conf = "UNKNOWN"
    if entry.get("note"):
        bits.append(entry["note"])
    if p.get("binding_limit"):
        bits.append("Binding limit: " + p["binding_limit"])
    if p.get("scope"):
        bits.append("Applies per %s." % p["scope"].upper())
    if p.get("volatile"):
        bits.append("VOLATILE: this figure moved under us at least once.")
    return rpd, tpd, conf, " ".join(b for b in bits if b).strip()


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
            rpd, tpd, conf, evidence = volume_of(p["name"], m["id"], limits)
            volume = daily_tokens(rpd, tpd)

            row = {
                "provider": p["name"], "model": m["id"],
                "auth": "KEY" if needs_key else "NO KEY",
                "coding_index": coding,
                "intelligence_index": aa.get("intelligence_index"),
                "agentic_index": aa.get("agentic_index"),
                "arena_elo": (da.get("codecategories") or {}).get("elo"),
                "scored_as": sc.get("matched_as"),
                "requests_per_day": rpd,
                "tokens_per_day": tpd,
                "daily_tokens": volume,
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
            if coding is not None and volume:
                bonus = NOAUTH_BONUS if not needs_key else 1.0
                reliability = answered.get(p["name"], 1.0)   # untested means unpenalised
                row["value"] = round(coding * math.log10(1 + volume / TOKENS_PER_REPLY) * bonus * reliability, 1)
                row["noauth_bonus_applied"] = bonus != 1.0
                row["reliability_applied"] = reliability
                rows.append(row)
            else:
                row["value"] = None
                row["why_unranked"] = ("no official benchmark score published for this model"
                                       if coding is None else
                                       "daily volume unknown - see LIMITS.md")
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

    def num(v, dash="?"):
        return dash if v is None else "{:,}".format(v)

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
         "| # | Model | Provider | Value | Auth | Coding | Tokens/day | Evidence | Privacy |",
         "|---|---|---|---|---|---|---|---|---|"]
    for i, r in enumerate(rows, 1):
        L.append("| %d | `%s` | %s | **%s** | %s | %s | %s | %s | %s |"
                 % (i, r["model"], r["provider"], r["value"],
                    "**no key**" if r["auth"] == "NO KEY" else "key",
                    cell(r["coding_index"]), num(r["daily_tokens"]),
                    r["volume_confidence"], privacy_flag(r)))

    L += ["", "## 2. By quality alone (official benchmark scores)", "",
          "| Model | Provider | Coding | Intelligence | Agentic | Arena ELO | Scored as |",
          "|---|---|---|---|---|---|---|"]
    for r in sorted([x for x in rows + unranked if x["coding_index"] is not None],
                    key=lambda x: -x["coding_index"]):
        L.append("| `%s` | %s | **%s** | %s | %s | %s | `%s` |"
                 % (r["model"], r["provider"], r["coding_index"], cell(r["intelligence_index"]),
                    cell(r["agentic_index"]), cell(r["arena_elo"]), r["scored_as"]))

    L += ["", "## 3. By volume: what you get to burn in a day", "",
          "Tokens, not requests: whichever of the two limits binds first, converted at "
          "%d output tokens per reply. A request cap and a token cap are the same shelf in different "
          "units, and the smaller one is your real ceiling." % TOKENS_PER_REPLY, "",
          "| Model | Provider | Tokens/day | Req/day | Evidence | Value |",
          "|---|---|---|---|---|---|"]
    for r in sorted([x for x in rows if x["daily_tokens"]], key=lambda x: -x["daily_tokens"]):
        L.append("| `%s` | %s | **%s** | %s | %s | %s |"
                 % (r["model"], r["provider"], num(r["daily_tokens"]), num(r["requests_per_day"]),
                    r["volume_confidence"], r["value"]))

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

    # ---- the headline box, also generated. It carries the number this repo lives or dies by, so it
    # is the last place that should be typed by hand: the first version of it was, and it went stale
    # the same afternoon the ranking moved.
    #
    # A quota belongs to the ACCOUNT, not to each model on it, so a provider contributes the LARGEST
    # daily figure among its models exactly once. Summing per model would let a provider with six
    # models on one 200k allowance report 1.2M, which is how these lists end up advertising capacity
    # nobody has.
    readme = out / "README.md"
    per_provider = {}
    for r in rows + unranked:
        v = r.get("daily_tokens")
        if v:
            per_provider[r["provider"]] = max(per_provider.get(r["provider"], 0), v)
    confirmed = sum(per_provider.values())
    n_providers = len({r["provider"] for r in rows + unranked})
    silent = n_providers - len(per_provider)

    # Today's answers, straight from the radar's own history.
    today_alive = today_total = 0
    up = out / "data" / "uptime.jsonl"
    if up.exists():
        for line in up.read_text(encoding="utf-8").split(chr(10)):
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except ValueError:
                continue
            if row.get("date") != a.date or row.get("state") == "no_key":
                continue
            today_total += 1
            today_alive += 1 if row.get("state") == "alive" else 0

    if readme.exists() and "<!--HEADLINE-->" in readme.read_text(encoding="utf-8"):
        TARGET = 1000000000
        gap = TARGET / confirmed if confirmed else 0
        H = ["| | |", "|---|---|",
             "| **Tokens per 24h**, confirmed | **%s** |" % num(confirmed),
             "| Endpoints answering today | **%d of %d tested** |" % (today_alive, today_total),
             "| Providers whose quota nobody publishes | **%d of %d** |" % (silent, n_providers),
             "| Distance to 1,000,000,000 tokens/day | **%.0fx** |" % gap]
        text = readme.read_text(encoding="utf-8")
        block = "<!--HEADLINE-->" + chr(10) + chr(10).join(H) + chr(10) + "<!--/HEADLINE-->"
        text = re.sub(r"<!--HEADLINE-->.*?<!--/HEADLINE-->", lambda _: block, text, flags=re.S)
        readme.write_text(text, encoding="utf-8", newline=chr(10))
        print("headline: %s tokens/24h confirmed, %d of %d answering, %.0fx to the target"
              % (num(confirmed), today_alive, today_total, gap))

    # The README table is GENERATED between markers. Hand-editing it is how a published number
    # drifts away from the data, which gate_claims.py then catches. Better to make drift impossible.
    if readme.exists() and rows:
        text = readme.read_text(encoding="utf-8")
        if "<!--RANKING-->" in text and "<!--/RANKING-->" in text:
            head = ("| # | Model | Provider | Value | Auth | Coding | Req/day | Note |\n"
                    "|---|---|---|---|---|---|---|---|\n")
            body = ""
            for i, r in enumerate(rows[:30], 1):
                note = ("**trains on your prompts**" if r["trains_on_free_tier"] == "yes"
                        else "**answers blank unless you turn thinking off**" if r["returned_empty_200"]
                        else "answers %.0f%% of the time" % (100 * r["answered_rate"])
                        if r.get("answered_rate") else r["volume_confidence"])
                body += "| %d | `%s` | %s | **%s** | %s | %s | %s | %s |\n" % (
                    i, r["model"], r["provider"], r["value"],
                    "**no key**" if r["auth"] == "NO KEY" else "key",
                    r["coding_index"], num(r["daily_tokens"]), note)
            block = "<!--RANKING-->" + chr(10) + head + body + "<!--/RANKING-->"
            text = re.sub(r"<!--RANKING-->.*?<!--/RANKING-->", lambda _: block, text, flags=re.S)
            readme.write_text(text, encoding="utf-8", newline=chr(10))
            print("regenerated the README table between its markers")
    # One file with EVERY endpoint, ranked or not, scored or not. The main tables filter; this one
    # never does, so there is always a place where nothing has been left out.
    A = ["# Every endpoint we track", "",
         "All %d of them, ranked or not, scored or not, alive or not. The tables in "
         "[RESULTS.md](RESULTS.md) filter and sort; this one never does." % (len(rows) + len(unranked)),
         "", "Measured **%s**. `?` means we do not know, and we would rather write that than guess."
         % a.date, "",
         "| Model | Provider | Value | Auth | Coding | Intelligence | Agentic | Arena | Tokens/day | "
         "Req/day | Evidence | Answers | Trains on prompts | Note |",
         "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows + unranked:
        note = []
        if r.get("returned_empty_200"):
            note.append("answers blank unless thinking is off")
        if r.get("thinking_switch"):
            note.append("we send `%s`" % json.dumps(r["thinking_switch"]))
        if r.get("why_unranked"):
            note.append(r["why_unranked"])
        if r.get("region_restriction") not in (None, "UNKNOWN"):
            note.append(r["region_restriction"])
        A.append("| `%s` | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s |"
                 % (r["model"], r["provider"],
                    r["value"] if r["value"] is not None else "not ranked",
                    "no key" if r["auth"] == "NO KEY" else "key",
                    cell(r["coding_index"]), cell(r["intelligence_index"]), cell(r["agentic_index"]),
                    cell(r["arena_elo"]), num(r["daily_tokens"]), num(r["requests_per_day"]),
                    r["volume_confidence"],
                    "%.0f%%" % (100 * r["answered_rate"]) if r.get("answered_rate") else "?",
                    r["trains_on_free_tier"],
                    "; ".join(note) or ""))
    A += ["", "## What the columns mean", "",
          "- **Value** — `coding_index x log10(1 + requests/day)`, times %s if no key is needed, times "
          "how often the provider actually answered us. Blank where we lack a score or a quota: a row "
          "needs both halves, and half a fact is not a rank." % NOAUTH_BONUS,
          "- **Coding / Intelligence / Agentic / Arena** — imported from official benchmarks, never run "
          "by us. `?` means that model has no published score.",
          "- **Evidence** — how we know the quota: MEASURED by us, DECLARED by the provider, PAID-PLAN "
          "when the only published figure belongs to a paid tier, UNKNOWN when nobody publishes it.",
          "- **Answers** — share of the probe's calls that came back with something in them.",
          "- **Trains on prompts** — from the provider's own terms. `UNKNOWN` means nobody has read "
          "them yet, and that is the honest default.", ""]
    (out / "ALL-ENDPOINTS.md").write_text(chr(10).join(A) + chr(10), encoding="utf-8",
                                          newline=chr(10))
    print("ranked %d endpoints, %d unranked" % (len(rows), len(unranked)))
    if rows:
        print("  top: %s @ %s  value=%s (coding %s, %s/day%s)"
              % (rows[0]["model"], rows[0]["provider"], rows[0]["value"], rows[0]["coding_index"],
                 num(rows[0]["daily_tokens"]),
                 ", no key" if rows[0]["auth"] == "NO KEY" else ""))
    print("  no-key endpoints: %d" % len(noauth))
    print("wrote RESULTS.md, ALL-ENDPOINTS.md, data/ranking.json, data/ranking.csv")
    return 0


if __name__ == "__main__":
    sys.exit(main())
