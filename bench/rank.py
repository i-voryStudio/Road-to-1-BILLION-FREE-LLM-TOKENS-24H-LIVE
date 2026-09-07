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


UPTIME_WINDOW_DAYS = 14
# What counts as the endpoint having answered us. `blocked` is deliberately absent from BOTH sets: it
# means they refused the caller, which is a fact about the caller's IP, not about the endpoint's health.
ANSWERED = {"alive"}
NOT_ANSWERED = {"down", "overloaded", "empty"}


def answered_from_uptime(path, today):
    """{(provider, model): rate}, {(provider, model): note}, from the last %d days of the radar.

    Endpoints with no reading in the window are absent from the result, and rank.py leaves those
    unpenalised - we do not punish what we did not test. A rate built on two days says two days.
    """ % UPTIME_WINDOW_DAYS
    from datetime import date as _date, timedelta
    rates, notes = {}, {}
    if not Path(path).exists():
        return rates, notes
    try:
        end = _date.fromisoformat(today)
    except ValueError:
        return rates, notes
    start = end - timedelta(days=UPTIME_WINDOW_DAYS - 1)
    tally = {}
    for line in Path(path).read_text(encoding="utf-8").split(chr(10)):
        line = line.strip()
        if not line:
            continue
        try:
            r = json.loads(line)
            d = _date.fromisoformat(r["date"])
        except (ValueError, KeyError):
            continue
        if d < start or d > end:
            continue
        state = r.get("state")
        if state not in ANSWERED and state not in NOT_ANSWERED:
            continue                      # no_key, rate_limited, payment_required, blocked: not a verdict
        key = (r["provider"], r["model"])
        yes, total = tally.get(key, (0, 0))
        tally[key] = (yes + (1 if state in ANSWERED else 0), total + 1)
    for key, (yes, total) in tally.items():
        rates[key] = yes / total
        notes[key] = ("answered %d of %d radar probes in the last %d days"
                      % (yes, total, UPTIME_WINDOW_DAYS))
    return rates, notes


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
    # ANSWERED RATE COMES FROM THE RADAR, NOT FROM THE ARCHIVE.
    #
    # It used to come from reliability.py, which reads every results/*/raw.json ever written, unweighted
    # by date. That made "answers 88% of the time", printed in the present tense on the front page, a
    # souvenir of whichever afternoon the battery last ran - and for a provider admitted today it would
    # be a single ten-second sample, frozen forever. data/uptime.jsonl is the only file written every
    # day, so the live claim is computed from it, over a rolling 14-day window, per ENDPOINT.
    out = Path(a.out)
    answered, rel_note = answered_from_uptime(out / "data" / "uptime.jsonl", a.date)
    archive = {r["provider"]: r["answered_rate"] for r in rel.get("providers", [])}
    trap = rel.get("reasoning_trap", {})
    trapped = {(t["provider"], t["model"]) for t in trap.get("observed", []) if not t["had_switch"]}
    switched = {(t["provider"], t["model"]) for t in trap.get("already_switched_off_by_us", [])}
    # THE FOURTEEN-DAY RULE, APPLIED HERE AND NOT ONLY DESCRIBED.
    #
    # gate_viability.py has been writing data/viability.json since the radar was born, and until now
    # NOTHING read it. The rule that gives this repo the word LIVE in its name - 14 consecutive days
    # without an answer and an endpoint is buried - decided the contents of GRAVEYARD.md and nothing
    # else: a buried endpoint kept its row, its value and its share of the headline total. A document
    # generator, not a rule. Now the ranking honours it.
    viab = {}
    vpath = out / "data" / "viability.json"
    if vpath.exists():
        try:
            v = json.loads(vpath.read_text(encoding="utf-8"))
            for state in ("degraded", "buried"):
                for e in v.get(state) or []:
                    viab[(e["provider"], e["model"])] = (state, e.get("days_down"))
        except ValueError:
            print("data/viability.json is not readable - refusing to rank as if every endpoint were healthy")
            return 2

    by_model = {(r["provider"], r["model"]): r for r in scores.get("matched", [])}

    rows, unranked, buried = [], [], []
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
                "answered_rate": answered.get((p["name"], m["id"])),
                "reliability_note": rel_note.get((p["name"], m["id"])),
                "answered_rate_archive": archive.get(p["name"]),
                "returned_empty_200": (p["name"], m["id"]) in trapped,
                "thinking_switch": m.get("extra_body") if (p["name"], m["id"]) in switched else None,
                "measured_at": a.date,
            }
            state, days = viab.get((p["name"], m["id"]), (None, None))
            row["viability"] = state or "healthy"
            row["days_down"] = days
            if state == "buried":
                # Out of the ranking and out of the headline sum entirely. Capacity you cannot reach
                # for fourteen days is not capacity, and leaving it in the total would inflate the one
                # number this repo is judged on with endpoints that stopped answering a fortnight ago.
                row["value"] = None
                row["why_unranked"] = ("buried: no answer for %s consecutive days - see GRAVEYARD.md"
                                       % days)
                row["daily_tokens"] = None
                buried.append(row)
                continue

            # Rankable only with BOTH halves. Half a fact is not a rank.
            if coding is not None and volume:
                bonus = NOAUTH_BONUS if not needs_key else 1.0
                reliability = answered.get((p["name"], m["id"]), 1.0)   # untested means unpenalised
                degraded_penalty = 0.5 if state == "degraded" else 1.0
                row["value"] = round(coding * math.log10(1 + volume / TOKENS_PER_REPLY) * bonus
                                     * reliability * degraded_penalty, 1)
                if state == "degraded":
                    row["degraded_penalty_applied"] = degraded_penalty
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
        "ranked": rows, "unranked": unranked, "buried": buried,
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
          "| Model | Provider | Tokens/day | Requests/day | Evidence | Value |",
          "|---|---|---|---|---|---|"]
    for r in sorted([x for x in rows if x["daily_tokens"]], key=lambda x: -x["daily_tokens"]):
        L.append("| `%s` | %s | **%s** | %s | %s | %s |"
                 % (r["model"], r["provider"], num(r["daily_tokens"]), num(r["requests_per_day"]),
                    r["volume_confidence"], r["value"]))

    noauth = [r for r in rows + unranked if r["auth"] == "NO KEY"]
    L += ["", "## 4. Needs no key at all", ""]
    if noauth:
        L += ["| Model | Provider | Coding | Tokens/day |", "|---|---|---|---|"]
        for r in noauth:
            L.append("| `%s` | %s | %s | %s |" % (r["model"], r["provider"], cell(r["coding_index"]),
                                                  cell(r["requests_per_day"])))
    else:
        L.append("**None yet.** Every provider we measure today wants a key. Endpoints that need none "
                 "exist, and an endpoint that needs no account at all is worth more than its raw score.")

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
        if v and v > per_provider.get(r["provider"], (0, ""))[0]:
            per_provider[r["provider"]] = (v, r.get("volume_confidence") or "UNKNOWN")

    # And now the part that was wrong for two days: these are NOT one number. Summing them and calling
    # the result "confirmed" is exactly what this repo accuses every other list of doing, three lines
    # under a README sentence that reads "Nothing here is copied". They are three separate facts:
    #
    #   MEASURED   we saw it: a response header, a usage endpoint, a 429 we walked into
    #   DECLARED   the provider says so on a page we read. Real, sourced, and still their claim
    #   PAID-PLAN  the only published figure belongs to a PAID tier. It is not free-tier capacity at all
    #
    # The headline number, and the distance to the target, use MEASURED alone.
    def total(kind):
        return sum(v for v, c in per_provider.values() if c == kind)

    measured, declared, paid = total("MEASURED"), total("DECLARED"), total("PAID-PLAN")

    # THE SECOND KIND OF FREE. A daily quota and a sign-up bundle are both real and they are not the
    # same shelf: one is there every morning, the other is there once. Adding them gives a number that
    # stops being true after 24 hours, which is why the two are counted separately and only ever meet
    # in a line that says "first 24 hours" out loud.
    #
    # A bundle handed over in MONEY is not converted into tokens. Doing that needs the provider's own
    # per-token price, and a made-up conversion is exactly the sort of confident wrong number this
    # list exists to avoid. Five dollars of credits stays five dollars of credits.
    # A THIRD SHELF: providers whose ceiling is published PER MINUTE and who publish no daily figure
    # at all. That is most of the good ones - Hetzner, OVHcloud, NVIDIA, Mistral - and counting them as
    # zero, which is what a daily-only total does, understates the list badly. They are summed on
    # their own terms, per minute, and never multiplied out to a day: 100,000 output tokens a minute
    # is a fact, and 144,000,000 a day is arithmetic nobody will ever be allowed to spend.
    # THE OFFICIAL METRIC OF THIS LIST IS PER MINUTE, and the reason is that it is the only one the
    # market actually publishes. A provider tells you 100,000 output tokens a minute; almost none tell
    # you a daily figure, and the ones that do are the small ones. A daily total therefore counts the
    # biggest providers as zero, which is how a list ends up reporting six million while sitting on
    # capacity three orders of magnitude larger.
    #
    # Per minute is also the only one that can be CHECKED: it arrives in a response header on a call
    # you make yourself. A daily figure is almost always somebody's marketing page.
    #
    # Nothing here is ever multiplied out to a day. 100,000 output tokens a minute is a fact;
    # 144,000,000 a day is a number nobody will be allowed to spend.
    # WHAT WE ACTUALLY GOT, as opposed to what they allow. bench/throughput.py sends real requests in
    # parallel for a short window and counts the output tokens that came back; this reads the latest
    # reading per provider. It is a floor - the window is capped and the token budget is small on
    # purpose, because the test spends somebody's free quota to find out.
    measured_min, measured_who = 0, []
    tpath = out / "data" / "throughput.jsonl"
    if tpath.exists():
        latest = {}
        for line in tpath.read_text(encoding="utf-8").split(chr(10)):
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except ValueError:
                continue
            if r.get("provider"):
                latest[r["provider"]] = r
        for name, r in sorted(latest.items()):
            rate = r.get("tokens_per_minute_measured")
            if rate is None:
                continue
            measured_min += rate
            measured_who.append({"provider": name, "tokens_per_minute": rate,
                                 "requests_ok": r.get("requests_ok"),
                                 "seconds": r.get("seconds"),
                                 "stopped_because": r.get("stopped_because"),
                                 "date": r.get("date")})

    tok_per_min, out_per_min, req_per_min, per_minute_who = 0, 0, 0, []
    for name, entry in sorted((limits.get("providers") or {}).items()):
        am = entry.get("all_models") or {}
        combined = am.get("tpm")
        split_in, split_out = am.get("tpm_input"), am.get("tpm_output")
        # A provider publishes EITHER one combined tokens-per-minute figure - their word, "includes
        # input and output tokens" - OR a split pair. They are added on their own terms and never
        # mixed: adding somebody's output-only ceiling to somebody else's combined one produces a
        # number that means nothing.
        total = combined if combined else ((split_in or 0) + (split_out or 0)) or None
        r = am.get("rpm")
        if not (total or r):
            continue
        tok_per_min += total or 0
        out_per_min += split_out or 0
        req_per_min += r or 0
        per_minute_who.append({"provider": name, "tokens_per_minute": total,
                               "output_tokens_per_minute": split_out,
                               "requests_per_minute": r, "confidence": entry.get("confidence")})

    per_minute_out = tok_per_min

    one_time_tokens, one_time_credits, one_time_who = 0, 0.0, []
    for name, entry in sorted((limits.get("providers") or {}).items()):
        ot = entry.get("one_time")
        if not isinstance(ot, dict) or ot.get("confidence") not in ("MEASURED", "DECLARED"):
            continue
        if ot.get("tokens"):
            one_time_tokens += ot["tokens"]
        if ot.get("credits_usd"):
            one_time_credits += ot["credits_usd"]
        one_time_who.append({"provider": name, "tokens": ot.get("tokens"),
                             "credits_usd": ot.get("credits_usd"),
                             "confidence": ot["confidence"], "source": ot.get("source"),
                             "quote": ot.get("quote"), "expires": ot.get("expires")})
    first_24h = measured + one_time_tokens
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

    # The first line of the repo is the target and how far along it is, drawn as a bar. It is
    # generated, so it can never say something the data does not.
    if readme.exists() and "<!--ROAD-->" in readme.read_text(encoding="utf-8"):
        # The bar measures what is CONFIRMED, not what is allowed. Published per-minute ceilings add
        # up to many times the target rate, and drawing that as a full bar would be the same trick
        # every other list plays: quoting the biggest number on the page as if it were delivery.
        # A ceiling is headroom. It goes beside the bar, not inside it.
        TARGET = 1000000000
        target_min = TARGET / 1440.0
        ceiling_min = 0
        for name, entry in ((limits.get("providers") or {}).items()):
            am = entry.get("all_models") or {}
            ceiling_min += am.get("tpm") or ((am.get("tpm_input") or 0) + (am.get("tpm_output") or 0))
        pct = 100.0 * measured_min / target_min if target_min else 0
        filled = int(round(min(pct, 100.0) / 100.0 * 40))
        bar = "█" * max(0, min(40, filled)) + "░" * max(0, 40 - filled)
        R = ["`%s`  **%.0f%%**" % (bar, pct), "",
             "**%s tokens a minute**, and this is what %d providers actually handed us on %s, not what "
             "they advertise: real requests, in parallel, counted from the response. One billion a day "
             "is %s a minute."
             % (num(measured_min), len(measured_who), a.date, num(int(target_min))), "",
             "*It is a floor. The test stops after 25,000 tokens or half a minute, whichever comes "
             "first, because it is spending somebody's free quota to find out. The ceilings these "
             "providers publish add up to %s a minute - %s times the target rate - and turning that "
             "headroom into delivered tokens is the whole job.*"
             % (num(ceiling_min), "%.0f" % (ceiling_min / target_min) if target_min else "?")]
        text = readme.read_text(encoding="utf-8")
        blk = "<!--ROAD-->" + chr(10) + chr(10).join(R) + chr(10) + "<!--/ROAD-->"
        text = re.sub(r"<!--ROAD-->.*?<!--/ROAD-->", lambda _: blk, text, flags=re.S)
        readme.write_text(text, encoding="utf-8", newline=chr(10))

    if readme.exists() and "<!--HEADLINE-->" in readme.read_text(encoding="utf-8"):
        TARGET = 1000000000
        gap = TARGET / measured if measured else 0
        # 1,000,000,000 tokens a day is the written target. Expressed in the unit this list
        # actually measures in, that is 1e9 / 1440 minutes.
        TARGET_PER_MIN = TARGET / 1440.0
        pct_meas = 100.0 * measured_min / TARGET_PER_MIN if TARGET_PER_MIN else 0
        H = ["| | |", "|---|---|",
             "| **Tokens per minute we actually received** | **%s** |" % num(measured_min),
             "| The rate 1,000,000,000 a day would need | %s |" % num(int(TARGET_PER_MIN)),
             "| **Share of it, measured** | **%.0f%%** |" % pct_meas,
             "| Providers that delivered anything | **%d of %d** |" % (len(measured_who), n_providers),
             "| Endpoints answering today | **%d of %d tested** |" % (today_alive, today_total),
             "| | |",
             "| *What they ALLOW, which is a different thing:* | |",
             "| Published per-minute ceilings, added up | %s |" % num(tok_per_min),
             "| Providers publishing a ceiling at all | %d of %d |" % (len(per_minute_who), n_providers),
             "| | |",
             "| *In daily terms:* | |",
             "| Tokens per day, where a provider publishes one | %s |" % num(measured),
             "| Once, at sign-up, across every account | %s |" % num(one_time_tokens),
             "| One-time credits, in money | %s |"
             % ("$%g" % one_time_credits if one_time_credits else "0"),
             "| Published only for a PAID plan | %s |" % num(paid)]
        text = readme.read_text(encoding="utf-8")
        block = "<!--HEADLINE-->" + chr(10) + chr(10).join(H) + chr(10) + "<!--/HEADLINE-->"
        text = re.sub(r"<!--HEADLINE-->.*?<!--/HEADLINE-->", lambda _: block, text, flags=re.S)
        readme.write_text(text, encoding="utf-8", newline=chr(10))
        print("headline: MEASURED %s tokens/min from %d providers = %.0f%% of the target rate; "
              "ceilings %s" % (num(measured_min), len(measured_who), pct_meas, num(tok_per_min)))

    # The same three numbers as data, so a gate can check the prose against them instead of trusting it.
    (out / "data" / "capacity.json").write_text(json.dumps({
        "date": a.date,
        "first_24h_tokens": first_24h,
        "recurring_measured_tokens_per_day": measured,
        "official_metric": "tokens per minute, measured",
        "measured_tokens_per_minute": measured_min,
        "measured_per_provider": measured_who,
        "output_tokens_per_minute": out_per_min,
        "published_ceilings_tokens_per_minute": tok_per_min,
        "requests_per_minute": req_per_min,
        "target_output_tokens_per_minute": round(1000000000 / 1440.0),
        "per_minute_providers": per_minute_who,
        "one_time_tokens": one_time_tokens,
        "one_time_credits_usd": one_time_credits,
        "one_time_grants": one_time_who,
        "measured_tokens_per_day": measured,
        "declared_tokens_per_day": declared,
        "paid_plan_tokens_per_day_excluded": paid,
        "per_provider": {k: {"daily_tokens": v, "confidence": c} for k, (v, c) in sorted(per_provider.items())},
        "providers_tracked": n_providers,
        "providers_with_no_published_quota": silent,
        "target_tokens_per_day": 1000000000,
        "target_date": "2026-11-07",
        "multiple_still_needed": round(1000000000 / measured, 1) if measured else None,
        "note": "first_24h_tokens is recurring PLUS one-time, and it is true exactly once. "
                "recurring_measured_tokens_per_day is what is there every morning, and it is the "
                "figure the target distance uses. One-time grants in money are NOT converted into "
                "tokens: that needs the provider's own price, and inventing the conversion is the "
                "kind of confident wrong number this list exists to avoid. "
                "MEASURED is the only figure the headline and the target distance use. DECLARED is the "
                "provider's own claim, sourced and dated, and is never added to it. PAID-PLAN is a "
                "number published for a paid tier and is excluded from both - reprinting one as free "
                "capacity is the mistake this repo names in its own README.",
    }, indent=1, ensure_ascii=False) + chr(10), encoding="utf-8", newline=chr(10))

    # The one-time grants, generated into LIMITS.md so the two kinds of free cannot drift apart in
    # prose while they are separated in code.
    lim_md = out / "LIMITS.md"
    if lim_md.exists() and "<!--ONE-TIME-->" in lim_md.read_text(encoding="utf-8"):
        O = ["| Provider | One-time | Expires | Their words |", "|---|---|---|---|"]
        for g in one_time_who:
            size = (num(g["tokens"]) + " tokens" if g.get("tokens")
                    else "$%g in credits" % g["credits_usd"] if g.get("credits_usd")
                    else "size not published")
            O.append("| %s | %s | %s | %s |"
                     % (g["provider"], size, g.get("expires") or "UNKNOWN",
                        (g.get("quote") or "").replace("|", "/")))
        if not one_time_who:
            O = ["Nothing recorded yet."]
        text = lim_md.read_text(encoding="utf-8")
        blk = "<!--ONE-TIME-->" + chr(10) + chr(10).join(O) + chr(10) + "<!--/ONE-TIME-->"
        text = re.sub(r"<!--ONE-TIME-->.*?<!--/ONE-TIME-->", lambda _: blk, text, flags=re.S)
        lim_md.write_text(text, encoding="utf-8", newline=chr(10))

    # THE WHOLE LIST, ONE ROW PER PROVIDER, generated. What each one actually gives you, on the
    # shelf it belongs to: recurring per day, published per minute, granted once. Three columns
    # instead of one total, because a provider with 100,000 output tokens a minute and a provider
    # with 250,000 a day are both real and are not comparable by adding them.
    if readme.exists() and "<!--CAPACITY-->" in readme.read_text(encoding="utf-8"):
        rows_by_prov = {}
        for r in rows + unranked:
            rows_by_prov.setdefault(r["provider"], []).append(r)
        got = {m["provider"]: m for m in measured_who}
        C = ["| Provider | We received /min | They allow /min | Req/min | Per day | Once | Key | Card | Phone |",
             "|---|---|---|---|---|---|---|---|---|"]
        def sort_key(name):
            entry = (limits.get("providers") or {}).get(name) or {}
            am = entry.get("all_models") or {}
            g = got.get(name)
            v = per_provider.get(name)
            return (-(g["tokens_per_minute"] if g else 0),
                    -(am.get("tpm") or am.get("tpm_output") or 0),
                    -(v[0] if v else 0), name)
        for name in sorted(rows_by_prov, key=sort_key):
            entry = (limits.get("providers") or {}).get(name) or {}
            am = entry.get("all_models") or {}
            daily = per_provider.get(name)
            ot = entry.get("one_time") or {}
            tok_min = (num(am["tpm"]) if am.get("tpm")
                       else "%s in / %s out" % (num(am["tpm_input"]), num(am["tpm_output"]))
                       if am.get("tpm_input") and am.get("tpm_output")
                       else num(am["tpm_output"]) + " out" if am.get("tpm_output") else "-")
            req_min = num(am["rpm"]) if am.get("rpm") else "-"
            once = (num(ot["tokens"]) if ot.get("tokens")
                    else "$%g" % ot["credits_usd"] if ot.get("credits_usd")
                    else "yes, size not published" if ot.get("confidence") in ("MEASURED", "DECLARED")
                    else "-")
            needs_key = any(r["auth"] == "KEY" for r in rows_by_prov[name])
            g = got.get(name)
            recv = num(g["tokens_per_minute"]) if g else "-"
            sg = entry.get("signup_requires") or {}
            card = {"no": "no", "yes": "**yes**", "either": "or ID"}.get(sg.get("card"), "?")
            phone = {"no": "no", "yes": "**yes**", "optional": "optional"}.get(sg.get("phone"), "?")
            C.append("| **%s** | %s | %s | %s | %s | %s | %s | %s | %s |"
                     % (name, recv, tok_min, req_min,
                        num(daily[0]) if daily else "-",
                        once,
                        "yes" if needs_key else "**no key**", card, phone))
        text = readme.read_text(encoding="utf-8")
        blk = "<!--CAPACITY-->" + chr(10) + chr(10).join(C) + chr(10) + "<!--/CAPACITY-->"
        text = re.sub(r"<!--CAPACITY-->.*?<!--/CAPACITY-->", lambda _: blk, text, flags=re.S)
        readme.write_text(text, encoding="utf-8", newline=chr(10))
        print("capacity table: %d providers" % len(rows_by_prov))

    # The five at the top, generated too. Hand-typed, this table drifted from the ranking the first
    # time the formula changed, and gate_claims.py caught four wrong numbers on the front page.
    if readme.exists() and "<!--TOP5-->" in readme.read_text(encoding="utf-8") and rows:
        T = ["| # | Model | Provider | Value | Coding | Tokens/day |", "|---|---|---|---|---|---|"]
        for i, r5 in enumerate(rows[:5], 1):
            T.append("| %d | `%s` | %s | **%s** | %s | %s |"
                     % (i, r5["model"], r5["provider"], r5["value"], r5["coding_index"],
                        num(r5["daily_tokens"])))
        text = readme.read_text(encoding="utf-8")
        block = "<!--TOP5-->" + chr(10) + chr(10).join(T) + chr(10) + "<!--/TOP5-->"
        text = re.sub(r"<!--TOP5-->.*?<!--/TOP5-->", lambda _: block, text, flags=re.S)
        readme.write_text(text, encoding="utf-8", newline=chr(10))

    # The README table is GENERATED between markers. Hand-editing it is how a published number
    # drifts away from the data, which gate_claims.py then catches. Better to make drift impossible.
    if readme.exists() and rows:
        text = readme.read_text(encoding="utf-8")
        if "<!--RANKING-->" in text and "<!--/RANKING-->" in text:
            head = ("| # | Model | Provider | Value | Auth | Coding | Tokens/day | Note |\n"
                    "|---|---|---|---|---|---|---|---|\n")
            body = ""
            for i, r in enumerate(rows[:30], 1):
                note = ("**trains on your prompts**" if r["trains_on_free_tier"] == "yes"
                        else "**answers blank unless you turn thinking off**" if r["returned_empty_200"]
                        else "answered %s" % r["reliability_note"].split("answered ")[-1]
                        if r.get("reliability_note") else r["volume_confidence"])
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
