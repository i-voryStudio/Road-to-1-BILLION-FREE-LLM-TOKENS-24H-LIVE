#!/usr/bin/env python3
"""Build the main ranking: free LLM endpoints, sorted by what you can actually get done with them.

    python bench/rank.py --date 2026-09-07 --out .

Reads the data files, each with its own provenance, and writes EVERY public page that carries a number:
the README blocks between markers, RESULTS.md, ALL-ENDPOINTS.md, LIMITS.md, data/ranking.{json,csv}
and data/capacity.json. One writer, so two tables cannot disagree, and `bench/test_rank.py` runs this
file against a fixture and compares the output byte for byte.

FIVE FILTERS, in the order a reader cares about them:

  1. VALUE = quality x volume          the headline. A brilliant model with 20 requests a day loses to
                                       a decent one with 2,400, and no other list ranks that way.
                                       Endpoints that need no key get a declared bonus.
  2. QUALITY                           from OFFICIAL benchmarks (bench/scores.py), never our own.
  3. VOLUME                            what you get per day, in tokens, labelled by how we know it.
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

THE VALUE FORMULA is one function, `value_of`, and the string printed on every page (`FORMULA`) is
built from the same constants that function uses, so the page cannot describe a formula the code does
not run. In words: coding index, times log10 of the daily token volume in replies of 500 tokens, times
the share of radar probes that came back with text, times 1.25 if no key is needed, times 0.5 while
the endpoint is degraded. log10 because the difference between 20 and 2,400 requests a day matters
enormously, and the difference between 2,400 and 24,000 much less: past a point you stop being the
bottleneck.

EVERY DAILY FIGURE CARRIES THE LABEL ITS EVIDENCE DESERVES, and only three labels may be ranked or
summed:

    MEASURED   we saw the daily figure: a response header, a usage endpoint
    DECLARED   the provider publishes a daily figure IN TOKENS on a page we read
    DERIVED    arithmetic done here on figures the provider publishes: a request cap times 500
               tokens a reply, or a unit price divided into a daily allowance. The arithmetic is
               written into `volume_evidence` on every such row
    PAID-PLAN  the only published daily figure belongs to a paid tier. Not ranked, not summed
    UNKNOWN    nobody publishes one and we have not measured one. Not ranked, not summed
    DRAWN      tokens actually pulled over a 60-minute draw (data/drawn.jsonl), times 24. Used only
               in the daily shelf, only where a provider has none of the first three, and always
               labelled as an extrapolation

A row needs both halves to be ranked: an official score AND a daily figure with one of the first three
labels. Half a fact is not a rank, and a paid plan's number is not a free tier's.
"""
import argparse, csv, json, math, re, sys
from datetime import date as _date, timedelta
from pathlib import Path
from urllib.parse import urlparse

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from states import ANSWERED, NOT_ANSWERED                                   # noqa: E402
from gate_contributions import KNOWN_SIGNUP_HOSTS, host_of, registrable     # noqa: E402

NOAUTH_BONUS = 1.25
DEGRADED_PENALTY = 0.5
# A request budget and a token budget are the same shelf measured in different units, and whichever
# runs out first is your real ceiling. To compare them we need one number for the size of a reply.
# 500 output tokens is roughly a substantial paragraph, and it is DECLARED here rather than buried:
# change it and every DERIVED volume figure moves, which is exactly why it should be visible.
TOKENS_PER_REPLY = 500
TARGET_TOKENS_PER_DAY = 1000000000
TARGET_DATE = "2026-11-07"
UPTIME_WINDOW_DAYS = 14
RANKABLE = ("MEASURED", "DECLARED", "DERIVED")
LABELS = {
    "MEASURED": "we saw it ourselves: a response header, a usage endpoint, a 429 we walked into",
    "DECLARED": "the provider says so on a page we read, with the date we read it. Real, and still "
                "their word",
    "DERIVED": "arithmetic done here on figures the provider publishes, with the arithmetic shown: "
               "a request cap times %d tokens a reply, or a unit price divided into an allowance"
               % TOKENS_PER_REPLY,
    "PAID-PLAN": "the only published number belongs to a paid tier, so it is not free capacity at "
                 "all. Never ranked, never summed",
    "UNKNOWN": "nobody publishes it and we have not measured it. It stays unknown. We do not borrow "
               "a number from another list to fill the hole, and unknown does not mean unlimited",
}
DRAWN_LABEL = ("tokens actually pulled over a 60-minute draw, times 24. An extrapolation, and it is "
               "labelled as one everywhere it appears; used only where a provider has no MEASURED, "
               "DECLARED or DERIVED daily figure")

# THE ONE FORMULA STRING, built from the constants value_of() uses. Printed identically in
# data/ranking.json, RESULTS.md, ALL-ENDPOINTS.md and README.
FORMULA = ("coding_index x log10(1 + daily_tokens / %d) x answered_rate x %s if no key x %s if degraded"
           % (TOKENS_PER_REPLY, NOAUTH_BONUS, DEGRADED_PENALTY))


def value_of(coding, daily_tokens, answered_rate, needs_key, degraded):
    """The only place the value is computed. FORMULA describes exactly this."""
    rate = 1.0 if answered_rate is None else answered_rate    # untested means unpenalised
    v = coding * math.log10(1 + daily_tokens / TOKENS_PER_REPLY) * rate
    if not needs_key:
        v *= NOAUTH_BONUS
    if degraded:
        v *= DEGRADED_PENALTY
    return round(v, 1)


def load(path, what):
    p = Path(path)
    if not p.exists():
        print("missing %s (%s)" % (path, what))
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def read_jsonl(path):
    rows = []
    p = Path(path)
    if not p.exists():
        return rows
    for line in p.read_text(encoding="utf-8").split(chr(10)):
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except ValueError:
            continue
    return rows


def num(v, dash="?"):
    return dash if v is None else "{:,}".format(v)


def cell(v, dash="?"):
    return dash if v is None else v


def money(v):
    return "$%g" % v


# ---------------------------------------------------------------------------------------------------
# VOLUME: the daily figure, labelled by its evidence
# ---------------------------------------------------------------------------------------------------
def volume_of(provider, model, limits):
    """The daily token figure for one endpoint, with the label its evidence deserves.

    Returns a dict: rpd, tpd, daily_tokens, confidence, evidence. The candidates are the token figure
    the provider states (its own confidence) and the request cap times TOKENS_PER_REPLY (DERIVED, with
    the arithmetic written out); the smaller wins because it binds first. A paid-plan figure keeps its
    number so a reader can see it, but is labelled PAID-PLAN and is neither ranked nor summed.
    """
    p = (limits.get("providers") or {}).get(provider)
    if not p:
        return {"rpd": None, "tpd": None, "daily_tokens": None, "confidence": "UNKNOWN",
                "evidence": "Provider not in limits.json."}
    am = p.get("all_models") or {}
    entry = (p.get("models") or {}).get(model) or am
    base = p.get("confidence", "UNKNOWN")
    rpd, tpd = entry.get("rpd"), entry.get("tpd")
    rpd_conf = entry.get("rpd_confidence") or base
    tpd_conf = entry.get("tpd_confidence") or base
    bits = [p.get("caveat", "")]

    if rpd is None and p.get("free_models_combined"):
        tiers = p["free_models_combined"]
        rpd = min((v["rpd"] for v in tiers.values()), default=None)
        best = max((v["rpd"] for v in tiers.values()), default=None)
        if rpd != best:
            bits.append("What a NEW account gets; rises to %s/day under the conditions in LIMITS.md, "
                        "and is shared across all free models." % num(best))

    candidates = []
    if tpd:
        candidates.append((tpd, tpd_conf,
                           "%s tokens/day is the provider's own token figure (%s)." % (num(tpd), tpd_conf)))
    if rpd:
        candidates.append((rpd * TOKENS_PER_REPLY, "DERIVED",
                           "%s requests/day (%s) x %d tokens a reply = %s tokens/day. The request cap is "
                           "the provider's figure; the token figure is arithmetic done here, so it is "
                           "DERIVED, not DECLARED."
                           % (num(rpd), rpd_conf, TOKENS_PER_REPLY, num(rpd * TOKENS_PER_REPLY))))
    if not candidates:
        # A unit price the provider publishes, divided into an allowance the provider publishes.
        # Cloudflare's Neurons: the tracked model's own price where it is on file, else the
        # provider-level figure, which names the model it was computed on.
        neurons = (p.get("free_allocation") or {}).get("neurons_per_day")
        cost = ((p.get("neuron_cost_examples") or {}).get(model) or {}).get("output_per_million")
        d = p.get("derived") or {}
        if neurons and cost:
            per_day = int(neurons / cost * 1000000)
            candidates.append((per_day, "DERIVED",
                               "%s Neurons/day / %s Neurons per 1M output tokens on this model = %s "
                               "output tokens/day. Both figures are the provider's; the division is ours."
                               % (num(neurons), num(cost), num(per_day))))
        elif d.get("output_tokens_per_day") and d.get("confidence") == "DERIVED":
            candidates.append((d["output_tokens_per_day"], "DERIVED",
                               "%s. This model's own unit price is not on file, so the figure is the "
                               "provider-level one and this model's real allowance may be lower."
                               % d.get("how", "derived by the provider's published arithmetic")))

    if candidates:
        daily, conf, how = min(candidates, key=lambda c: c[0])
        bits.append(how)
    else:
        daily, conf = None, "UNKNOWN"

    if entry.get("rpd_is_paid_plan"):
        conf = "PAID-PLAN"
        bits.append("This figure is the provider's %s plan, not its free tier: it is shown and it is not "
                    "ranked or summed." % (p.get("rpd_plan") or "paid"))
    if entry.get("note"):
        bits.append(entry["note"])
    if p.get("binding_limit"):
        bits.append("Binding limit: " + p["binding_limit"])
    if p.get("scope"):
        bits.append("Applies per %s." % p["scope"].upper())
    if p.get("volatile"):
        bits.append("VOLATILE: this figure moved under us at least once.")
    return {"rpd": rpd, "tpd": tpd, "daily_tokens": daily, "confidence": conf,
            "evidence": " ".join(b for b in bits if b).strip()}


def ceiling_of(entry):
    """The provider-level per-minute ceiling, reading BOTH shapes limits.json may carry.

    `all_models` is the one shape every provider has. Where per-model figures exist under `models`
    the largest of them is what a reader can reach, so the max is shown and `per_model` says so.
    """
    am = entry.get("all_models") or {}
    out = {k: am.get(k) for k in ("rpm", "tpm", "tpm_input", "tpm_output")}
    per_model = False
    for v in (entry.get("models") or {}).values():
        for k in out:
            if v.get(k):
                per_model = True
                out[k] = max(out[k] or 0, v[k])
    out["per_model"] = per_model or "per model" in (am.get("note") or "")
    out["confidence"] = entry.get("confidence", "UNKNOWN")
    return out


HTTP_PHRASES = {
    "0": "no response: timeout or connection failure",
    "400": "HTTP 400: the request was rejected as malformed",
    "401": "HTTP 401: a credential is required",
    "402": "HTTP 402: the endpoint stops serving until a top-up",
    "403": "HTTP 403: the endpoint refused the caller",
    "404": "HTTP 404: no such model or path",
    "409": "HTTP 409: the endpoint reported a conflict",
    "413": "HTTP 413: the request was too large",
    "429": "HTTP 429: rate limited",
    "500": "HTTP 500: server error",
    "502": "HTTP 502: bad gateway",
    "503": "HTTP 503: no capacity behind the endpoint",
    "504": "HTTP 504: gateway timeout",
}
SAFE_REASONS = {"rate limit reached", "window ended", "token budget spent", "60 minutes elapsed",
                "token cap reached", "their limit is holding"}


def plain_reason(text):
    """A throughput row's `first_error` or `stopped_because`, reduced to the HTTP code and a fixed
    phrase. The raw string is whatever the script or the provider wrote at the time, and it is not
    republished: a page describes what the endpoint returned, as a code, and nothing about anyone's
    account."""
    if not text:
        return None
    text = str(text)
    m = re.search(r"HTTP\s+(\d+)", text)
    prefix = "five failures in a row: " if "five failures" in text else ""
    if m:
        return prefix + HTTP_PHRASES.get(m.group(1), "HTTP %s" % m.group(1))
    low = text.strip().lower()
    for safe in SAFE_REASONS:
        if safe in low:
            return safe
    return "stopped: see data/throughput.jsonl"


def unlock_text(entry):
    u = (entry or {}).get("unlock") or {}
    if not u.get("costs_usd"):
        return None
    return ("%s top-up unlocks the daily quota" if u.get("one_time") else
            "%s a month unlocks the daily quota") % money(u["costs_usd"])


# ---------------------------------------------------------------------------------------------------
# ANSWERED RATE: from the radar, per endpoint, over a rolling window
# ---------------------------------------------------------------------------------------------------
def answered_from_uptime(path, today):
    """({(provider, model): (yes, total)}, {(provider, model) probed at all}) from the last
    UPTIME_WINDOW_DAYS days of the radar.

    Endpoints with no verdict in the window are absent from the tally, and the ranking leaves those
    unpenalised: we do not punish what we did not test. States that are not a verdict (blocked,
    rate_limited, payment_required) are skipped in the tally but counted as PROBED, so a page can say
    "probed, no verdict yet" rather than "not probed yet" about an endpoint that only ever answered
    429 or 402; bench/states.py says why `empty` counts as not answered here.
    """
    tally, probed = {}, set()
    try:
        end = _date.fromisoformat(today)
    except ValueError:
        return tally, probed
    start = end - timedelta(days=UPTIME_WINDOW_DAYS - 1)
    for r in read_jsonl(path):
        try:
            d = _date.fromisoformat(r["date"])
        except (ValueError, KeyError):
            continue
        if d < start or d > end:
            continue
        state = r.get("state")
        key = (r["provider"], r["model"])
        if state != "no_key":
            probed.add(key)
        if state not in ANSWERED and state not in NOT_ANSWERED:
            continue
        yes, total = tally.get(key, (0, 0))
        tally[key] = (yes + (1 if state in ANSWERED else 0), total + 1)
    return tally, probed


def answers_text(rate, yes_total, was_probed):
    if rate is None:
        return "probed, no verdict yet" if was_probed else "not probed yet"
    yes, total = yes_total
    return "%d of %d in %d days" % (yes, total, UPTIME_WINDOW_DAYS)


# ---------------------------------------------------------------------------------------------------
# THE DOOR: where a reader gets a key
# ---------------------------------------------------------------------------------------------------
def door_of(p):
    """(url, kind) for the Get key column, validated the way gate_contributions validates `signup`:
    the link's registrable domain must equal the API host's or a declared sign-up host. Anything else
    falls back to the API host, so this column can never point at a lookalike."""
    api_host = host_of(p["url"])
    allowed = KNOWN_SIGNUP_HOSTS.get(p["name"], set()) | {registrable(api_host)}
    signup = p.get("signup") or ""
    if signup and urlparse(signup).scheme == "https" and registrable(host_of(signup)) in allowed:
        return signup, "signup"
    return "https://%s/" % api_host, "api_host"


def door_cell(r):
    if r["auth"] == "NO KEY":
        return "no key needed: [%s](%s)" % (host_of(r["get_key"]), r["get_key"])
    return "[get a key](%s)" % r["get_key"]


def provider_link(name, doors):
    url = doors.get(name)
    return "[%s](%s)" % (name, url) if url else name


def privacy_flags(r):
    flags = []
    if r["trains_on_free_tier"] == "yes":
        flags.append("**trains on your prompts**")
    if r.get("human_review") == "yes":
        flags.append("human review")
    if r["region_restriction"] not in ("UNKNOWN", None):
        flags.append("region-restricted")
    return "; ".join(flags) if flags else "terms not read"


def cost_text(r):
    parts = [privacy_flags(r)]
    if r.get("unlock"):
        parts.append(r["unlock"])
    return "; ".join(parts)


# ---------------------------------------------------------------------------------------------------
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
    rel = load(a.reliability, "archived answered rates - run bench/reliability.py first") or {"providers": []}
    if not all([providers, limits, privacy, scores]):
        return 2
    out = Path(a.out)
    (out / "data").mkdir(parents=True, exist_ok=True)
    LP = limits.get("providers") or {}

    # ANSWERED RATE COMES FROM THE RADAR, NOT FROM THE ARCHIVE. data/uptime.jsonl is the only file
    # written every day, so the live claim is computed from it, over a rolling window, per ENDPOINT.
    # The archived run in reliability.json is kept for RESULTS.md section 6 and labelled as archived.
    tally, probed = answered_from_uptime(out / "data" / "uptime.jsonl", a.date)
    answered = {k: yes / total for k, (yes, total) in tally.items()}
    archive = {r["provider"]: r for r in rel.get("providers", [])}
    trap = rel.get("reasoning_trap", {})
    trapped = {(t["provider"], t["model"]) for t in trap.get("observed", []) if not t["had_switch"]}
    switched = {(t["provider"], t["model"]) for t in trap.get("already_switched_off_by_us", [])}

    # THE FOURTEEN-DAY RULE, applied here and not only described: a buried endpoint leaves the
    # ranking and every sum; a degraded one is halved.
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
    doors = {p["name"]: door_of(p)[0] for p in providers["providers"]}

    rows, unranked, buried = [], [], []
    for p in providers["providers"]:
        needs_key = bool(p.get("key_env"))
        priv = (privacy.get("providers") or {}).get(p["name"], {})
        door, door_kind = door_of(p)
        for m in p["models"]:
            key = (p["name"], m["id"])
            sc = by_model.get(key, {})
            aa = sc.get("artificial_analysis", {})
            da = sc.get("design_arena", {})
            coding = aa.get("coding_index")
            vol = volume_of(p["name"], m["id"], limits)
            state, days = viab.get(key, (None, None))
            rate = answered.get(key)
            row = {
                "provider": p["name"], "model": m["id"],
                "auth": "KEY" if needs_key else "NO KEY",
                "get_key": door, "get_key_kind": door_kind,
                "coding_index": coding,
                "intelligence_index": aa.get("intelligence_index"),
                "agentic_index": aa.get("agentic_index"),
                "arena_elo": (da.get("codecategories") or {}).get("elo"),
                "scored_as": sc.get("matched_as"),
                "requests_per_day": vol["rpd"],
                "tokens_per_day": vol["tpd"],
                "daily_tokens": vol["daily_tokens"],
                "volume_confidence": vol["confidence"],
                "volume_evidence": vol["evidence"],
                "trains_on_free_tier": priv.get("trains_on_free_tier", "UNKNOWN"),
                "human_review": priv.get("human_review", "UNKNOWN"),
                "region_restriction": priv.get("region_restriction", "UNKNOWN"),
                "privacy_source": priv.get("source"),
                "unlock": unlock_text(LP.get(p["name"])),
                "answered_rate": rate,
                "radar_probes": list(tally[key]) if key in tally else None,
                "answers": answers_text(rate, tally.get(key), key in probed),
                "answered_rate_archive": (archive.get(p["name"]) or {}).get("answered_rate"),
                "returned_empty_200": key in trapped,
                "thinking_switch": m.get("extra_body") if key in switched else None,
                "viability": state or "healthy",
                "days_down": days,
                "measured_at": a.date,
            }
            row["cost"] = cost_text(row)
            if state == "buried":
                row["value"] = None
                row["why_unranked"] = ("buried: no answer for %s consecutive days - see GRAVEYARD.md" % days)
                row["daily_tokens"] = None
                buried.append(row)
                continue
            if coding is not None and vol["daily_tokens"] and vol["confidence"] in RANKABLE:
                row["value"] = value_of(coding, vol["daily_tokens"], rate, needs_key, state == "degraded")
                row["noauth_bonus_applied"] = not needs_key
                row["reliability_applied"] = 1.0 if rate is None else rate
                if state == "degraded":
                    row["degraded_penalty_applied"] = DEGRADED_PENALTY
                rows.append(row)
            else:
                row["value"] = None
                row["why_unranked"] = ("no official benchmark score published for this model"
                                       if coding is None else
                                       "only a paid-plan figure is published"
                                       if vol["confidence"] == "PAID-PLAN" else
                                       "daily volume unknown - see LIMITS.md")
                unranked.append(row)

    rows.sort(key=lambda r: (-r["value"], r["provider"], r["model"]))
    unranked.sort(key=lambda r: (r["why_unranked"], r["provider"], r["model"]))
    everything = rows + unranked
    n_providers = len({r["provider"] for r in everything + buried})
    n_endpoints = len(everything) + len(buried)
    noauth = [r for r in everything if r["auth"] == "NO KEY"]

    # -----------------------------------------------------------------------------------------------
    # THE DAILY SHELF: one figure per provider, the largest among its rankable rows. A quota belongs to
    # the ACCOUNT, not to each model on it, so a provider contributes once. PAID-PLAN and UNKNOWN never
    # enter it; DRAWN fills in only where nothing else exists.
    # -----------------------------------------------------------------------------------------------
    per_provider = {}
    paid_excluded = {}
    for r in everything:
        v = r.get("daily_tokens")
        if not v:
            continue
        if r["volume_confidence"] in RANKABLE:
            if v > per_provider.get(r["provider"], {"daily_tokens": 0})["daily_tokens"]:
                per_provider[r["provider"]] = {"daily_tokens": v, "confidence": r["volume_confidence"],
                                               "model": r["model"], "evidence": r["volume_evidence"]}
        elif r["volume_confidence"] == "PAID-PLAN":
            paid_excluded[r["provider"]] = max(paid_excluded.get(r["provider"], 0), v)

    # DRAWN: data/drawn.jsonl, written by bench/draw_day.py where it exists. tokens_per_hour_drawn x 24,
    # latest reading per provider, labelled as an extrapolation from a 60-minute draw.
    drawn = {}
    for r in read_jsonl(out / "data" / "drawn.jsonl"):
        if r.get("provider") and r.get("tokens_per_hour_drawn") is not None:
            drawn[r["provider"]] = r
    drawn_who = []
    for name, r in sorted(drawn.items()):
        per_day = int(r["tokens_per_hour_drawn"] * 24)
        # A draw against a ONE-TIME grant is not a day: at the drawn rate the grant runs out in hours and
        # then there is nothing, so the extrapolation is reported with the hours it would last and is NOT
        # added to the daily shelf. Measured 2026-09-07: one provider drew 699,585 tokens an hour against a
        # sign-up grant of 1,000,000 per model; times 24 that would have put 16.8M a day on the bar for a pot
        # that lasts under six hours.
        entry = (limits.get("providers") or {}).get(name) or {}
        ot = entry.get("one_time") or {}
        recurring = any((entry.get("all_models") or {}).get(k) for k in ("rpd", "tpd")) or bool(entry.get("monthly"))             or bool(entry.get("derived")) or any((m or {}).get("rpd") or (m or {}).get("tpd")
                                                  for m in (entry.get("models") or {}).values())
        pot = None
        if ot.get("tokens") and ot.get("confidence") in ("MEASURED", "DECLARED") and not recurring:
            n_models = len(next((pp["models"] for pp in providers["providers"] if pp["name"] == name), []))                 if ot.get("per_model") else 1
            pot = int(ot["tokens"]) * max(1, n_models)
        hours = (pot / r["tokens_per_hour_drawn"]) if (pot and r["tokens_per_hour_drawn"]) else None
        row = {"provider": name, "model": r.get("model"), "date": r.get("date"),
               "tokens_per_hour_drawn": r["tokens_per_hour_drawn"],
               "tokens_per_day_extrapolated": per_day,
               "minutes": r.get("minutes_run", r.get("minutes")),
               "stopped_because": plain_reason(r.get("stopped_because")),
               "counted": pot is None and name not in per_provider,
               "note": (("extrapolated from a 60-minute draw" if name not in per_provider else
                         "not on the shelf: a %s daily figure already exists" % per_provider[name]["confidence"])
                        if pot is None else
                        "not counted: the only free capacity here is a one-time grant of %s tokens, and at the "
                        "drawn rate it lasts about %.0f hours; a grant is not a day" % (num(pot), hours))}
        drawn_who.append(row)
        if name not in per_provider and pot is None:
            per_provider[name] = {"daily_tokens": per_day, "confidence": "DRAWN", "model": r.get("model"),
                                  "evidence": "%s tokens drawn per hour x 24: extrapolated from a "
                                              "60-minute draw on %s" % (num(r["tokens_per_hour_drawn"]),
                                                                         r.get("date"))}

    def shelf(kind):
        who = [n for n, e in per_provider.items() if e["confidence"] == kind]
        return sum(per_provider[n]["daily_tokens"] for n in who), sorted(who)

    measured, measured_who = shelf("MEASURED")
    declared, declared_who = shelf("DECLARED")
    derived, derived_who = shelf("DERIVED")
    drawn_total, drawn_names = shelf("DRAWN")
    defensible = measured + declared + derived + drawn_total
    paid = sum(paid_excluded.values())
    silent = sorted({r["provider"] for r in everything} - set(per_provider))
    pct = 100.0 * defensible / TARGET_TOKENS_PER_DAY
    multiple = round(TARGET_TOKENS_PER_DAY / defensible, 1) if defensible else None
    target_min = TARGET_TOKENS_PER_DAY / 1440.0

    # -----------------------------------------------------------------------------------------------
    # BURSTS: what bench/throughput.py actually received, 30-second windows, LATEST reading per
    # provider. A rate, never a day. Rows from the older script lack `first_error`: missing is null.
    # -----------------------------------------------------------------------------------------------
    latest, all_rows = {}, {}
    for r in read_jsonl(out / "data" / "throughput.jsonl"):
        if r.get("provider"):
            latest[r["provider"]] = r
            all_rows.setdefault(r["provider"], []).append(r)
    burst_min, burst_who, burst_zero, burst_norate = 0, [], [], []
    for name, r in sorted(latest.items()):
        rate = r.get("tokens_per_minute_measured")
        hist = [x.get("tokens_per_minute_measured") for x in all_rows.get(name, [])
                if x.get("tokens_per_minute_measured") is not None]
        entry = {"provider": name, "model": r.get("model"), "tokens_per_minute": rate,
                 "best_seen": max(hist) if hist else rate, "readings": len(hist),
                 "holds_up": (None if len(hist) < 2 or not rate else rate >= 0.5 * max(hist)),
                 "requests_ok": r.get("requests_ok"), "requests_failed": r.get("requests_failed"),
                 "seconds": r.get("seconds"), "first_error": plain_reason(r.get("first_error")),
                 "stopped_because": plain_reason(r.get("stopped_because")), "date": r.get("date")}
        if rate is None:
            burst_norate.append(entry)
        elif rate > 0:
            burst_min += rate
            burst_who.append(entry)
        else:
            burst_zero.append(entry)
    drop = None
    for w in burst_who:
        if w["holds_up"] is False and w["tokens_per_minute"]:
            f = w["best_seen"] / w["tokens_per_minute"]
            drop = max(drop or 0, f)

    # -----------------------------------------------------------------------------------------------
    # CEILINGS: two shelves that never add. Output-only figures may be compared with the output
    # target; combined in+out figures (or ones that do not say) may not, and are not.
    # -----------------------------------------------------------------------------------------------
    out_only, out_who, combined, combined_who, req_min, any_min = 0, [], 0, [], 0, []
    ceilings = {name: ceiling_of(e) for name, e in LP.items()}
    for name, c in sorted(ceilings.items()):
        if not any(c.get(k) for k in ("rpm", "tpm", "tpm_input", "tpm_output")):
            continue
        any_min.append({"provider": name, "requests_per_minute": c["rpm"],
                        "tokens_per_minute_combined": c["tpm"],
                        "tokens_per_minute_input": c["tpm_input"],
                        "tokens_per_minute_output": c["tpm_output"],
                        "per_model_largest_shown": c["per_model"], "confidence": c["confidence"]})
        req_min += c["rpm"] or 0
        if c["tpm_output"]:
            out_only += c["tpm_output"]
            out_who.append(name)
        if c["tpm"]:
            combined += c["tpm"]
            combined_who.append(name)

    # -----------------------------------------------------------------------------------------------
    # GRANTS: once, and monthly. Money stays money.
    # -----------------------------------------------------------------------------------------------
    def grants(field):
        tokens, credits, who = 0, 0.0, []
        for name, entry in sorted(LP.items()):
            g = entry.get(field)
            if not isinstance(g, dict) or g.get("confidence") not in ("MEASURED", "DECLARED"):
                continue
            if g.get("tokens"):
                tokens += g["tokens"]
            if g.get("credits_usd"):
                credits += g["credits_usd"]
            who.append({"provider": name, "tokens": g.get("tokens"), "per_model": bool(g.get("per_model")),
                        "credits_usd": g.get("credits_usd"), "confidence": g["confidence"],
                        "source": g.get("source"), "read_on": g.get("read_on"),
                        "quote": g.get("quote"), "expires": g.get("expires")})
        return tokens, credits, who

    one_time_tokens, one_time_credits, one_time_who = grants("one_time")
    monthly_tokens, monthly_credits, monthly_who = grants("monthly")

    def grant_size(g):
        if g.get("tokens"):
            return num(g["tokens"]) + " tokens" + (" per model" if g.get("per_model") else "")
        if g.get("credits_usd"):
            return money(g["credits_usd"]) + " in credits"
        return "size not published"

    # Today's answers, straight from the radar's own history.
    today_alive = today_total = 0
    for r in read_jsonl(out / "data" / "uptime.jsonl"):
        if r.get("date") != a.date or r.get("state") == "no_key":
            continue
        today_total += 1
        today_alive += 1 if r.get("state") == "alive" else 0

    # Per-provider radar, every provider in providers.json, for the README reliability table.
    radar = {}
    for (prov, _), (yes, total) in tally.items():
        y, t, n = radar.get(prov, (0, 0, 0))
        radar[prov] = (y + yes, t + total, n + 1)

    # =============================================================================================
    # data/ranking.json and data/ranking.csv
    # =============================================================================================
    (out / "data" / "ranking.json").write_text(json.dumps({
        "measured_at": a.date,
        "ranking_formula": FORMULA,
        "tokens_per_reply": TOKENS_PER_REPLY,
        "noauth_bonus": NOAUTH_BONUS,
        "degraded_penalty": DEGRADED_PENALTY,
        "rankable_volume_labels": list(RANKABLE),
        "quality_source": scores.get("source"),
        "quality_fetched_on": scores.get("fetched_on"),
        "filters": ["1 value = quality x volume", "2 quality (official benchmarks)", "3 volume",
                    "4 auth", "5 privacy cost"],
        "ranked": rows, "unranked": unranked, "buried": buried,
    }, indent=1, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")

    cols = ["provider", "model", "value", "auth", "get_key", "coding_index", "intelligence_index",
            "arena_elo", "daily_tokens", "requests_per_day", "volume_confidence", "answered_rate",
            "trains_on_free_tier", "region_restriction", "measured_at"]
    with open(out / "data" / "ranking.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore", lineterminator="\n")
        w.writeheader()
        w.writerows(everything)

    # =============================================================================================
    # RESULTS.md
    # =============================================================================================
    L = ["# Full ranking", "",
         "Generated by `bench/rank.py` on **%s** - do not edit by hand." % a.date,
         "",
         "Quality is **imported** from official benchmarks (%s, fetched %s). We do not run it ourselves. "
         "Everything else - quota, auth, privacy cost - is measured or read from the provider's own terms."
         % (scores.get("source"), scores.get("fetched_on")),
         "",
         "`Value` = `%s`. A brilliant model you may call 20 times a day loses to a decent one you may "
         "call 2,400 times, which is the whole point of ranking this way. `daily_tokens` is the smaller "
         "of the token cap and the request cap times %d, and its label says how we know it: MEASURED, "
         "DECLARED or DERIVED may be ranked; PAID-PLAN and UNKNOWN may not." % (FORMULA, TOKENS_PER_REPLY),
         "", "## 1. By value: quality x volume", "",
         "| # | Model | Provider | Value | Coding | Tokens/day | Volume | Answers | Cost | Get key |",
         "|---|---|---|---|---|---|---|---|---|---|"]
    for i, r in enumerate(rows, 1):
        L.append("| %d | `%s` | %s | **%s** | %s | %s | %s | %s | %s | %s |"
                 % (i, r["model"], r["provider"], r["value"], cell(r["coding_index"]),
                    num(r["daily_tokens"]), r["volume_confidence"], r["answers"], r["cost"],
                    door_cell(r)))

    L += ["", "## 2. By quality alone (official benchmark scores)", "",
          "| Model | Provider | Coding | Intelligence | Agentic | Arena ELO | Scored as |",
          "|---|---|---|---|---|---|---|"]
    for r in sorted([x for x in everything if x["coding_index"] is not None],
                    key=lambda x: (-x["coding_index"], x["provider"], x["model"])):
        L.append("| `%s` | %s | **%s** | %s | %s | %s | `%s` |"
                 % (r["model"], provider_link(r["provider"], doors), r["coding_index"], cell(r["intelligence_index"]),
                    cell(r["agentic_index"]), cell(r["arena_elo"]), r["scored_as"]))

    L += ["", "## 3. By volume: what you get to burn in a day", "",
          "Tokens, not requests: whichever of the two limits binds first, converted at "
          "%d output tokens per reply. A request cap and a token cap are the same shelf in different "
          "units, and the smaller one is your real ceiling. A figure converted from requests is "
          "DERIVED, because the provider published the requests and we chose the tokens per reply." % TOKENS_PER_REPLY, "",
          "| Model | Provider | Tokens/day | Requests/day | Volume | Value | How we know, and the arithmetic |",
          "|---|---|---|---|---|---|---|"]
    for r in sorted([x for x in everything if x["daily_tokens"]],
                    key=lambda x: (-x["daily_tokens"], x["provider"], x["model"])):
        L.append("| `%s` | %s | **%s** | %s | %s | %s | %s |"
                 % (r["model"], provider_link(r["provider"], doors), num(r["daily_tokens"]), num(r["requests_per_day"], "-"),
                    r["volume_confidence"], r["value"] if r["value"] is not None else "not ranked",
                    r["volume_evidence"].replace("|", "/")))

    L += ["", "## 4. Needs no key at all", ""]
    if noauth:
        L += ["| Model | Provider | Coding | Tokens/day | Volume | Where |", "|---|---|---|---|---|---|"]
        for r in noauth:
            L.append("| `%s` | %s | %s | %s | %s | %s |" % (r["model"], r["provider"], cell(r["coding_index"]),
                                                            num(r["daily_tokens"]), r["volume_confidence"],
                                                            door_cell(r)))
    else:
        L.append("**None yet.** Every provider we measure today wants a key.")

    L += ["", "## 5. What the free tier costs you that is not money", "",
          "Training on your prompts, human review, and legal limits on where you may serve users. "
          "`UNKNOWN` means nobody has read that provider's terms yet - and UNKNOWN is the honest "
          "default here, because inventing a `no` would be the most damaging wrong answer this repo "
          "could publish.", "",
          "| Provider | Trains on your prompts | Human review | Region restriction | Source |",
          "|---|---|---|---|---|"]
    for p in providers["providers"]:
        pv = (privacy.get("providers") or {}).get(p["name"], {})
        src = pv.get("source")
        L.append("| %s | %s | %s | %s | %s |"
                 % (provider_link(p["name"], doors), pv.get("trains_on_free_tier", "UNKNOWN"),
                    pv.get("human_review", "UNKNOWN"), pv.get("region_restriction", "UNKNOWN"),
                    "[terms](%s)" % src if src else "not read yet"))

    L += ["", "## 6. Does it actually answer, and does it answer with anything", "",
          "### 6a. The radar, last %d days, per endpoint" % UPTIME_WINDOW_DAYS, "",
          "One probe per endpoint per day from `bench/probe_alive.py`, history in `data/uptime.jsonl`. "
          "Answered means HTTP 200 with text in it; a `200` with no text counts as not answered here "
          "and as alive for the fourteen-day rule, and `bench/states.py` says why both are right. "
          "Endpoints with no row have not been probed yet and are not penalised.", "",
          "| Model | Provider | Answered | Rate |", "|---|---|---|---|"]
    for (prov, model), (yes, total) in sorted(tally.items()):
        L.append("| `%s` | %s | %d of %d | %.0f%% |" % (model, provider_link(prov, doors), yes, total, 100.0 * yes / total))
    if archive:
        run = ", ".join(rel.get("runs_included") or [])
        L += ["", "### 6b. Archived run %s, per provider" % run, "",
              "Every call of the archived benchmark battery, counted by outcome: a small sample from one "
              "afternoon, kept because it is the only measurement of the `200`-with-nothing-in-it trap. "
              "It does not feed the ranking; the radar above does.", "",
              "| Provider | Calls | Answered | Empty 200 | 429 | 503 | Timeout | Reading |",
              "|---|---|---|---|---|---|---|---|"]
        for r in sorted(archive.values(), key=lambda x: (-x["answered_rate"], x["provider"])):
            L.append("| %s | %d | %.0f%% | %d | %d | %d | %d | %s |"
                     % (provider_link(r["provider"], doors), r["calls"], 100 * r["answered_rate"], r["empty_200"],
                        r["rate_limited"], r["overloaded"], r["timeout"], r["note"]))
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
              "Measured in the archived run: **%d empty 200s, %d of them on models where no switch was set.**"
              % (len(obs), sum(1 for t in obs if not t["had_switch"])), "",
              "| Model | Provider | Switch was set | Probe |", "|---|---|---|---|"]
        for t in obs:
            L.append("| `%s` | %s | %s | %s |" % (t["model"], provider_link(t["provider"], doors),
                                                  "yes, and ignored" if t["had_switch"] else "**no**",
                                                  t["probe"]))
        sw = trap.get("already_switched_off_by_us", [])
        if sw:
            L += ["", "We already turn thinking off for **%d** of the models we call. Those switches are "
                      "in [`bench/providers.json`](bench/providers.json) and are the cheapest thing to "
                      "copy out of this repo." % len(sw)]

    if unranked:
        L += ["", "## Not ranked, and why", "",
              "A row needs both halves to be ranked: an official score AND a daily figure labelled "
              "MEASURED, DECLARED or DERIVED. Half a fact is not a rank, and a paid plan's number is "
              "not a free tier's.", "",
              "| Model | Provider | Missing | Get key |", "|---|---|---|---|"]
        for r in unranked:
            L.append("| `%s` | %s | %s | %s |" % (r["model"], r["provider"], r["why_unranked"], door_cell(r)))
    if buried:
        L += ["", "## Buried", "", "| Model | Provider | Why |", "|---|---|---|"]
        for r in buried:
            L.append("| `%s` | %s | %s |" % (r["model"], provider_link(r["provider"], doors), r["why_unranked"]))
    (out / "RESULTS.md").write_text("\n".join(L) + "\n", encoding="utf-8", newline="\n")

    # =============================================================================================
    # data/capacity.json: every headline number as data, so a gate can check the prose against it
    # =============================================================================================
    (out / "data" / "capacity.json").write_text(json.dumps({
        "date": a.date,
        "target_tokens_per_day": TARGET_TOKENS_PER_DAY,
        "target_date": TARGET_DATE,
        "defensible_tokens_per_day": defensible,
        "share_of_target_pct": round(pct, 2),
        "multiple_still_needed": multiple,
        "daily_shelf": {
            "measured": {"tokens_per_day": measured, "providers": measured_who,
                         "how": "response headers or usage endpoints"},
            "declared": {"tokens_per_day": declared, "providers": declared_who,
                         "how": "a daily figure published by the provider in tokens"},
            "derived": {"tokens_per_day": derived, "providers": derived_who,
                        "how": "a published request cap x %d tokens a reply, or a published unit price "
                               "divided into a published allowance; the arithmetic is in each row's "
                               "volume_evidence" % TOKENS_PER_REPLY},
            "drawn": {"tokens_per_day": drawn_total, "providers": drawn_names,
                      "how": "tokens_per_hour_drawn x 24 from data/drawn.jsonl: extrapolated from a "
                             "60-minute draw, used only where nothing above exists"},
        },
        "per_provider": {k: per_provider[k] for k in sorted(per_provider)},
        "paid_plan_tokens_per_day_excluded": paid,
        "paid_plan_per_provider": paid_excluded,
        "providers_tracked": n_providers,
        "endpoints_tracked": n_endpoints,
        "endpoints_ranked": len(rows),
        "providers_with_no_daily_figure": silent,
        "burst": {
            "what": "30-second burst, per provider, latest reading; bench/throughput.py; a rate, never a day",
            "tokens_per_minute_added_up": burst_min,
            "providers_delivered": [w["provider"] for w in burst_who],
            "providers_measured_zero": [w["provider"] for w in burst_zero],
            "providers_no_rate": [w["provider"] for w in burst_norate],
            "largest_drop_between_readings": round(drop, 1) if drop else None,
            "per_provider": burst_who + burst_zero + burst_norate,
        },
        "ceilings_per_minute": {
            "target_output_tokens_per_minute": round(target_min),
            "output_only_tokens_per_minute": out_only,
            "output_only_providers": out_who,
            "output_only_share_of_target_pct": round(100.0 * out_only / target_min, 1),
            "combined_or_unspecified_tokens_per_minute": combined,
            "combined_or_unspecified_providers": combined_who,
            "requests_per_minute": req_min,
            "providers_with_any_per_minute_figure": len(any_min),
            "per_provider": any_min,
            "note": "Output-only and combined in+out ceilings are two shelves and are never added "
                    "together; only the output-only shelf is compared with the output target.",
        },
        "one_time": {"tokens": one_time_tokens, "credits_usd": one_time_credits, "grants": one_time_who,
                     "note": "true exactly once; never added to the daily shelf. A grant recorded "
                             "per_model is per model, not multiplied by the models this list tracks."},
        "monthly": {"tokens": monthly_tokens, "credits_usd": monthly_credits, "grants": monthly_who,
                    "note": "refreshes monthly; money stays money"},
        "drawn": drawn_who,
        "radar_today": {"alive": today_alive, "tested": today_total},
        "note": "defensible_tokens_per_day = MEASURED + DECLARED + DERIVED + DRAWN, largest figure per "
                "provider, and it is the only number the bar and the distance use. PAID-PLAN is shown "
                "and never counted. Bursts and ceilings are per minute and are never multiplied out to "
                "a day. Money is never converted into tokens.",
    }, indent=1, ensure_ascii=False) + chr(10), encoding="utf-8", newline=chr(10))

    # =============================================================================================
    # README blocks, each between markers. Hand-editing a generated block is how a published number
    # drifts from the data; the markers make drift impossible.
    # =============================================================================================
    readme = out / "README.md"

    def put(marker, lines):
        if not readme.exists():
            return
        text = readme.read_text(encoding="utf-8")
        if "<!--%s-->" % marker not in text:
            return
        blk = "<!--%s-->" % marker + chr(10) + chr(10).join(lines) + chr(10) + "<!--/%s-->" % marker
        text = re.sub(r"<!--%s-->.*?<!--/%s-->" % (marker, marker), lambda _: blk, text, flags=re.S)
        readme.write_text(text, encoding="utf-8", newline=chr(10))

    # ROAD: the bar is the daily shelf over the target. A burst is a rate and never becomes a day.
    filled = int(round(min(pct, 100.0) / 100.0 * 40))
    bar = "█" * max(0, min(40, filled)) + "░" * max(0, 40 - filled)
    def shelf_phrase(total, who, what):
        if not who:
            return "nothing " + what
        return "%s %s (%d provider%s)" % (num(total), what, len(who), "" if len(who) == 1 else "s")

    shelf_bits = [shelf_phrase(measured, measured_who, "measured from response headers or usage endpoints"),
                  shelf_phrase(declared, declared_who, "published by a provider as a daily token figure"),
                  shelf_phrase(derived, derived_who, "derived from a published request cap at %d tokens a "
                                                     "reply or from a published unit price" % TOKENS_PER_REPLY)]
    shelf_bits.append("%s extrapolated from a 60-minute draw (%d provider%s)"
                      % (num(drawn_total), len(drawn_names), "" if len(drawn_names) == 1 else "s")
                      if drawn_names else "nothing yet from a sustained draw")
    R = ["`%s`  **~%.1f%%**" % (bar, pct), "",
         "**Roughly %s tokens a day** is what this list can defend on %s: %s. The target is "
         "%s a day by %s, %s times that. Nothing here is a burst multiplied out to a day."
         % (num(defensible), a.date, "; ".join(shelf_bits), num(TARGET_TOKENS_PER_DAY), TARGET_DATE,
            "%.1f" % multiple if multiple else "?"), "",
         "*Bursts are a different thing.* In 30-second bursts, latest reading per provider, "
         "**%d of %d providers handed us %s tokens a minute** added together on %s%s. "
         "A burst is a rate: 100,000 tokens a minute is a fact and 144,000,000 a day is a number "
         "nobody will be allowed to spend, so the bar above is built from the daily shelf and never "
         "from this rate.%s Nothing on this page is guaranteed to you by anyone, us included."
         % (len(burst_who), n_providers, num(burst_min),
            max([w["date"] for w in burst_who if w.get("date")] or [a.date]),
            ("; %d answered and delivered nothing (%s)" % (len(burst_zero), ", ".join(w["provider"] for w in burst_zero))
             if burst_zero else ""),
            (" Free tiers move, throttle without warning and close; one provider here dropped "
             "%d-fold between two readings taken the same day." % round(drop) if drop and drop >= 2 else
             " Free tiers move, throttle without warning and close.")), "",
         "*What they allow.* %s Ceilings published as input-plus-output, or without saying which, add "
         "up to %s a minute across %d providers and cannot be compared with an output target, so they "
         "are not."
         % (("The only output-only ceiling%s published (%s: %s output tokens a minute) %s %.0f%% of the "
             "%s a minute the target works out to."
             % ("s" if len(out_who) > 1 else "", ", ".join(out_who), num(out_only),
                "add up to" if len(out_who) > 1 else "is", 100.0 * out_only / target_min, num(round(target_min))))
            if out_who else "No provider publishes an output-only ceiling.",
            num(combined), len(combined_who))]
    put("ROAD", R)

    H = ["| | |", "|---|---|",
         "| **Tokens a day this list can defend** | **%s** |" % num(defensible),
         "| measured by us from headers or usage endpoints | %s |" % num(measured),
         "| published by the provider in tokens | %s |" % num(declared),
         "| derived from a published request cap at %d tokens each, or a published unit price | %s |"
         % (TOKENS_PER_REPLY, num(derived)),
         "| extrapolated from a 60-minute draw, where nothing above exists | %s |" % num(drawn_total),
         "| The target | %s a day by %s |" % (num(TARGET_TOKENS_PER_DAY), TARGET_DATE),
         "| **Share of it** | **%.1f%%** |" % pct,
         "| Providers with a daily figure on this shelf | %d of %d |" % (len(per_provider), n_providers),
         "| | |",
         "| *Bursts, which are a rate and not a day:* | |",
         "| 30-second burst, per provider, latest reading, added up | %s a minute |" % num(burst_min),
         "| Providers that delivered anything in the burst | **%d of %d** |" % (len(burst_who), n_providers),
         "| measured, delivered nothing | %s |" % (", ".join(w["provider"] for w in burst_zero) or "none"),
         "| Endpoints answering today | **%d of %d tested** |" % (today_alive, today_total),
         "| | |",
         "| *What they ALLOW per minute, two shelves that never add:* | |",
         "| Output-only ceilings, added up | %s (%s) |" % (num(out_only), ", ".join(out_who) or "none"),
         "| Combined in+out ceilings, or unspecified, added up | %s (%d providers) |" % (num(combined), len(combined_who)),
         "| Providers with any per-minute figure on file | %d of %d |" % (len(any_min), n_providers),
         "| | |",
         "| *Shown, and not counted above:* | |",
         "| Published only for a PAID plan | %s a day (%s) |"
         % (num(paid), ", ".join(sorted(paid_excluded)) or "none"),
         "| Once, at sign-up, in tokens | %s |"
         % (", ".join("%s%s (%s)" % (num(g["tokens"]), " per model" if g["per_model"] else "", g["provider"])
                      for g in one_time_who if g["tokens"]) or "none"),
         "| Once, at sign-up, in money | %s |" % (money(one_time_credits) if one_time_credits else "none"),
         "| Monthly, in money | %s |"
         % (", ".join("%s (%s)" % (money(g["credits_usd"]), g["provider"]) for g in monthly_who if g["credits_usd"])
            or "none")]
    put("HEADLINE", H)
    print("headline: %s tokens/day defensible = %.2f%% of the target; burst %s tokens/min from %d providers"
          % (num(defensible), pct, num(burst_min), len(burst_who)))

    # THE FIVE AT THE TOP, and the top 30, with a door on every row.
    head = ("| # | Model | Provider | Value | Coding | Tokens/day | Volume | Answers | Cost | Get key |\n"
            "|---|---|---|---|---|---|---|---|---|---|\n")

    def rank_row(i, r):
        return ("| %d | `%s` | %s | **%s** | %s | %s | %s | %s | %s | %s |"
                % (i, r["model"], r["provider"], r["value"], cell(r["coding_index"]),
                   num(r["daily_tokens"]), r["volume_confidence"],
                   r["answers"] + ("; blank 200 seen in the archived run" if r["returned_empty_200"] else ""),
                   r["cost"], door_cell(r)))

    if rows:
        put("TOP5", head.rstrip("\n").split("\n") + [rank_row(i, r) for i, r in enumerate(rows[:5], 1)])
        put("RANKING", head.rstrip("\n").split("\n") + [rank_row(i, r) for i, r in enumerate(rows[:30], 1)])

    # THE WHOLE LIST, one row per provider, on the shelf each figure belongs to.
    got = {w["provider"]: w for w in burst_who + burst_zero + burst_norate}
    C = ["| Provider | Received /min, 30 s burst | Why 0 | Allow /min | Req/min | Per day | How we know "
         "| Monthly | Once | Key | Card | Phone |",
         "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    rows_by_prov = {}
    for r in everything:
        rows_by_prov.setdefault(r["provider"], []).append(r)

    def sort_key(name):
        g = got.get(name) or {}
        c = ceilings.get(name) or {}
        pp = per_provider.get(name) or {}
        return (-(g.get("tokens_per_minute") or 0), -(c.get("tpm") or c.get("tpm_output") or 0),
                -(pp.get("daily_tokens") or 0), name)

    for name in sorted(rows_by_prov, key=sort_key):
        entry = LP.get(name) or {}
        c = ceilings.get(name) or {}
        pp = per_provider.get(name)
        g = got.get(name)
        star = " (per model, largest)" if c.get("per_model") else ""
        tok_min = ("%s in / %s out" % (num(c["tpm_input"]), num(c["tpm_output"]))
                   if c.get("tpm_input") and c.get("tpm_output")
                   else num(c["tpm_output"]) + " out" if c.get("tpm_output")
                   else num(c["tpm"]) + " in+out" if c.get("tpm") else "-") + (star if c.get("tpm") or c.get("tpm_output") else "")
        req = (num(c["rpm"]) + (star if not (c.get("tpm") or c.get("tpm_output")) else "")) if c.get("rpm") else "-"
        if not g:
            recv, why = "-", "not measured yet"
        elif g["tokens_per_minute"] is None:
            recv, why = "-", "no rate: %s" % (g.get("first_error") or g.get("stopped_because") or "?")
        elif g["tokens_per_minute"] == 0:
            recv, why = "0", g.get("stopped_because") or g.get("first_error") or "?"
        elif g.get("holds_up") is False:
            recv, why = "%s (was %s)" % (num(g["tokens_per_minute"]), num(g["best_seen"])), ""
        else:
            recv, why = num(g["tokens_per_minute"]), ""
        ot = entry.get("one_time") or {}
        mo = entry.get("monthly") or {}
        once = grant_size(ot) if ot.get("confidence") in ("MEASURED", "DECLARED") else "-"
        month = grant_size(mo) if mo.get("confidence") in ("MEASURED", "DECLARED") else "-"
        if pp and pp["confidence"] == "PAID-PLAN":
            pp = None
        needs_key = any(r["auth"] == "KEY" for r in rows_by_prov[name])
        sg = entry.get("signup_requires") or {}
        card = {"no": "no", "yes": "**yes**", "either": "or ID"}.get(sg.get("card"), "?")
        phone = {"no": "no", "yes": "**yes**", "optional": "optional"}.get(sg.get("phone"), "?")
        C.append("| **%s** | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s |"
                 % (provider_link(name, doors), recv, why.replace("|", "/").strip(), tok_min, req,
                    num(pp["daily_tokens"]) if pp else "-",
                    (pp["confidence"] if pp else
                     "PAID-PLAN, not counted" if name in paid_excluded else "UNKNOWN"),
                    month, once, "yes" if needs_key else "**no key**", card, phone))
    put("CAPACITY", C)
    print("capacity table: %d providers" % len(rows_by_prov))

    # RELIABILITY: the radar, every provider, "not probed yet" where there is no row.
    RL = ["| Provider | Answered, last %d days | Endpoints probed | Endpoints tracked |" % UPTIME_WINDOW_DAYS,
          "|---|---|---|---|"]
    order = sorted(rows_by_prov, key=lambda n: (-(radar[n][0] / radar[n][1]) if n in radar else 1, n))
    for name in order:
        if name in radar:
            y, t, n_ep = radar[name]
            RL.append("| %s | %d of %d (%.0f%%) | %d | %d |"
                      % (provider_link(name, doors), y, t, 100.0 * y / t, n_ep, len(rows_by_prov[name])))
        else:
            touched = sum(1 for (pv, _) in probed if pv == name)
            RL.append("| %s | %s | %d | %d |"
                      % (provider_link(name, doors),
                         "probed, no verdict yet: only 429 or 402 in the window" if touched else "not probed yet",
                         touched, len(rows_by_prov[name])))
    put("RELIABILITY", RL)

    # COUNTS: every number the prose used to type by hand.
    probed_eps = len(tally)
    put("COUNTS", [
        "%d providers and %d endpoints are tracked. %d endpoints are ranked; %d are listed with what is "
        "missing. %d endpoints have a radar verdict in the last %d days, %d were probed and only ever "
        "refused (429 or 402), and %d have not been probed yet. "
        "%d endpoint%s need%s no key. %d providers have a daily figure this list can defend; %d "
        "publish none and are counted as nothing: %s."
        % (n_providers, n_endpoints, len(rows), len(unranked) + len(buried), probed_eps,
           UPTIME_WINDOW_DAYS, len(probed) - probed_eps, n_endpoints - len(probed), len(noauth),
           "" if len(noauth) == 1 else "s", "s" if len(noauth) == 1 else "",
           len(per_provider), len(silent), ", ".join(silent) or "none")])

    # EXAMPLE: the best coding score in the list and where every endpoint carrying it actually sits,
    # each with the cause taken from its own row. Written by hand, this sentence once explained a 0.0
    # by a quota when the data said a single empty radar probe.
    top = max((r["coding_index"] for r in everything if r["coding_index"] is not None), default=None)
    if top is not None:
        clauses = []
        for r in [x for x in everything if x["coding_index"] == top]:
            if r in rows:
                pos = rows.index(r) + 1
                if r["answered_rate"] == 0:
                    why = ("its radar probes in the window (%s) came back with no text, so the answered "
                           "rate in the formula is 0" % r["answers"])
                else:
                    why = "%s tokens a day (%s)" % (num(r["daily_tokens"]), r["volume_confidence"])
                clauses.append("at %s it sits at #%d with a value of %s: %s" % (r["provider"], pos, r["value"], why))
            else:
                clauses.append("at %s it is not ranked: %s" % (r["provider"], r["why_unranked"]))
        names = sorted({r["model"] for r in everything if r["coding_index"] == top})
        put("EXAMPLE", ["The best coding score in the whole list, **%s**, belongs to %s, and the score alone "
                        "decides nothing: %s." % (top, ", ".join("`%s`" % n for n in names), "; ".join(clauses))])

    # FORMULA and LABELS: the one formula string and the one legend, so the prose cannot drift from
    # the constants the code runs on.
    put("FORMULA", ["`%s`" % FORMULA])
    put("LABELS", ["| | |", "|---|---|"]
        + ["| **%s** | %s |" % (k, v) for k, v in LABELS.items()]
        + ["| **DRAWN** | %s |" % DRAWN_LABEL])

    # TRAP: the archived run's empty-200 counts, which the README used to type by hand.
    if obs:
        put("TRAP", ["Measured in the archived run of %s: **%d empty 200s, %d of them on models where no switch "
                     "was set.** We already set the switch for %d of the models we call; those switches are in "
                     "[`bench/providers.json`](bench/providers.json) and are the cheapest thing to copy out of "
                     "this repo. The per-model list is in [RESULTS.md](RESULTS.md)."
                     % (", ".join(rel.get("runs_included") or ["an unrecorded date"]), len(obs),
                        sum(1 for x in obs if not x["had_switch"]),
                        len(trap.get("already_switched_off_by_us") or []))])
    else:
        put("TRAP", ["No archived run with empty-200 counts is on file."])

    # KEYLESS: every endpoint that takes no credential, with the day it was called without one.
    K = []
    for p in providers["providers"]:
        if p.get("auth") == "none":
            K.append("- **%s**, [%s](%s): %s (called with no `Authorization` header on %s)."
                     % (p["name"], host_of(p["url"]), doors[p["name"]],
                        ", ".join("`%s`" % m["id"] for m in p["models"]),
                        p.get("auth_measured_on", "an unrecorded date")))
    put("KEYLESS", K or ["None yet. Every provider we measure today wants a key."])

    # =============================================================================================
    # ALL-ENDPOINTS.md: never filters
    # =============================================================================================
    A = ["# Every endpoint we track", "",
         "All %d of them, ranked or not, scored or not, alive or not, across %d providers. The tables in "
         "[RESULTS.md](RESULTS.md) filter and sort; this one never does. %d of the %d have an answered-or-not "
         "verdict from the radar in the last %d days; %d were probed and only ever refused (429 or 402), "
         "which is not a verdict either way; %d have not been probed yet. [GRAVEYARD.md](GRAVEYARD.md) "
         "counts every endpoint the radar has touched."
         % (n_endpoints, n_providers, probed_eps, n_endpoints, UPTIME_WINDOW_DAYS,
            len(probed) - probed_eps, n_endpoints - len(probed)),
         "", "Measured **%s**. `?` means we do not know, and we would rather write that than guess."
         % a.date, "",
         "| Model | Provider | Value | Get key | Coding | Intelligence | Agentic | Arena | Tokens/day | "
         "Req/day | Volume | Answers | Trains on prompts | Note |",
         "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in everything + buried:
        note = []
        if r.get("returned_empty_200"):
            note.append("answers blank unless thinking is off")
        if r.get("thinking_switch"):
            note.append("we send `%s`" % json.dumps(r["thinking_switch"]))
        if r.get("why_unranked"):
            note.append(r["why_unranked"])
        if r.get("unlock"):
            note.append(r["unlock"])
        if r.get("region_restriction") not in (None, "UNKNOWN"):
            note.append(r["region_restriction"])
        ans = (r["answers"] if r["answered_rate"] is None else
               "%d of %d (%.0f%%)" % (r["radar_probes"][0], r["radar_probes"][1], 100 * r["answered_rate"]))
        A.append("| `%s` | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s |"
                 % (r["model"], r["provider"],
                    r["value"] if r["value"] is not None else "not ranked",
                    door_cell(r),
                    cell(r["coding_index"]), cell(r["intelligence_index"]), cell(r["agentic_index"]),
                    cell(r["arena_elo"]), num(r["daily_tokens"]), num(r["requests_per_day"]),
                    r["volume_confidence"], ans, r["trains_on_free_tier"], "; ".join(note) or ""))
    A += ["", "## What the columns mean", "",
          "- **Value** - `%s`. Blank where we lack a score or a rankable daily figure: a row needs "
          "both halves, and half a fact is not a rank." % FORMULA,
          "- **Get key** - the provider's own sign-up page, or its API host where it publishes none; "
          "the link's domain is checked against the API host, so it cannot point at a lookalike.",
          "- **Coding / Intelligence / Agentic / Arena** - imported from official benchmarks, never run "
          "by us. `?` means that model has no published score.",
          "- **Tokens/day** - the smaller of the token cap and the request cap times %d." % TOKENS_PER_REPLY,
          "- **Volume** - how we know that figure:"]
    for k, v in LABELS.items():
        A.append("  - **%s** - %s." % (k, v))
    A.append("  - **DRAWN** - %s." % DRAWN_LABEL)
    A += ["- **Answers** - radar probes in the last %d days that came back with text, `yes of total`. "
          "0%% is a measurement; `not probed yet` is the absence of one." % UPTIME_WINDOW_DAYS,
          "- **Trains on prompts** - from the provider's own terms. `UNKNOWN` means nobody has read "
          "them yet, and that is the honest default.", ""]
    (out / "ALL-ENDPOINTS.md").write_text(chr(10).join(A) + chr(10), encoding="utf-8", newline=chr(10))

    # =============================================================================================
    # LIMITS.md: the whole file, from limits.json, every provider
    # =============================================================================================
    M = ["# Rate limits, and how we know them", "",
         "Generated by `bench/rank.py` from [`bench/limits.json`](bench/limits.json), read on %s. "
         "Correcting a number is a one-line pull request to that file; this page is overwritten on "
         "every run." % limits.get("read_on", a.date), "",
         "Five confidence labels, and the difference matters more than the numbers:", ""]
    for k, v in LABELS.items():
        M.append("- **%s** - %s." % (k, v))
    M += ["- **DRAWN** - %s." % DRAWN_LABEL, "",
          "## Monthly grants, kept apart from the daily numbers", "",
          "A pot that refreshes each month is neither a daily quota nor a one-time bundle. Money stays "
          "money: converting it into tokens needs the provider's published price.", ""]
    if monthly_who:
        M += ["| Provider | Monthly | Refreshes | Their words |", "|---|---|---|---|"]
        for g in monthly_who:
            M.append("| %s | %s | %s | %s |" % (provider_link(g["provider"], doors), grant_size(g),
                                                g.get("expires") or "UNKNOWN",
                                                (g.get("quote") or "").replace("|", "/")))
    else:
        M.append("Nothing recorded yet.")
    M += ["", "## One-time grants, kept apart from the daily numbers", "",
          "A sign-up bundle is not a daily quota. It is real once, and every figure below carries the "
          "provider's own sentence, because a giveaway described in our words is a marketing claim with "
          "our name on it. A grant recorded per model is per model: it is not multiplied by the number "
          "of models this list happens to track.", ""]
    if one_time_who:
        M += ["| Provider | One-time | Expires | Their words |", "|---|---|---|---|"]
        for g in one_time_who:
            M.append("| %s | %s | %s | %s |" % (provider_link(g["provider"], doors), grant_size(g),
                                                g.get("expires") or "UNKNOWN",
                                                (g.get("quote") or "").replace("|", "/")))
    else:
        M.append("Nothing recorded yet.")
    M += ["", "## Per-minute ceilings, two shelves", "",
          "Output-only ceilings can be compared with an output target; combined in+out ceilings, or "
          "ones that do not say, cannot, and the two are never added together. Where a provider "
          "publishes per-model figures the largest is shown.", "",
          "| Provider | Req/min | Tokens/min | Denominated in | How we know |", "|---|---|---|---|---|"]
    for e in any_min:
        if e["tokens_per_minute_input"] and e["tokens_per_minute_output"]:
            tok, denom = ("%s in / %s out" % (num(e["tokens_per_minute_input"]), num(e["tokens_per_minute_output"])),
                          "input and output, separately")
        elif e["tokens_per_minute_output"]:
            tok, denom = num(e["tokens_per_minute_output"]), "output only"
        elif e["tokens_per_minute_combined"]:
            tok, denom = num(e["tokens_per_minute_combined"]), "input+output, or unspecified"
        else:
            tok, denom = "-", "-"
        M.append("| %s | %s | %s | %s | %s%s |"
                 % (provider_link(e["provider"], doors), num(e["requests_per_minute"], "-"), tok, denom,
                    e["confidence"], "; per model, largest shown" if e["per_model_largest_shown"] else ""))
    for name, p in LP.items():
        M += ["", "## %s" % provider_link(name, doors), "",
              "- **Confidence:** %s" % p.get("confidence", "UNKNOWN"),
              "- **Limit applies per:** %s" % str(p.get("scope", "?")).upper() +
              (" - so a second API key does not raise it." if p.get("scope") in ("organization", "project") else "")]
        if p.get("source"):
            M.append("- **Source:** %s (read %s)" % (p["source"], p.get("read_on", "?")))
        if p.get("measured_on"):
            M.append("- **Measured:** %s, %s" % (p["measured_on"], p.get("measured_how", "")))
        if p.get("volatile"):
            M.append("- **VOLATILE** - re-measure before relying on it.")
        if p.get("binding_limit"):
            M.append("- **The limit that actually bites:** %s" % p["binding_limit"])
        if name in per_provider:
            pp = per_provider[name]
            M.append("- **Daily figure this list uses:** %s tokens (%s), on `%s`."
                     % (num(pp["daily_tokens"]), pp["confidence"], pp["model"]))
        elif name in paid_excluded:
            M.append("- **Daily figure:** %s tokens is published only for a paid plan, so it is shown and "
                     "not used." % num(paid_excluded[name]))
        else:
            M.append("- **Daily figure this list uses:** none. UNKNOWN is not unlimited.")
        if p.get("caveat"):
            M += ["", p["caveat"]]
        if p.get("models"):
            M += ["", "| Model | RPM | RPD | TPM | TPD | Daily figure is |", "|---|---|---|---|---|---|"]
            for mid, v in p["models"].items():
                tag = ("PAID-PLAN" if v.get("rpd_is_paid_plan") else
                       v.get("rpd_confidence") or p.get("confidence", "UNKNOWN")) if (v.get("rpd") or v.get("tpd")) else "UNKNOWN"
                M.append("| `%s` | %s | %s | %s | %s | %s |"
                         % (mid, num(v.get("rpm"), "-"), num(v.get("rpd"), "-"), num(v.get("tpm"), "-"),
                            num(v.get("tpd"), "-"), tag))
                if v.get("note"):
                    M.append("| | | | | | %s |" % v["note"].replace("|", "/"))
        am = p.get("all_models") or {}
        keys = [(k, am[k]) for k in ("rpm", "rps", "rph", "rpd", "tpm", "tpm_input", "tpm_output", "tpd",
                                     "concurrent_requests", "neurons_per_day") if am.get(k)]
        if keys:
            M += ["", "All models: " + ", ".join("%s %s" % (k.upper(), num(v)) for k, v in keys)
                  + (" (%s)" % am["note"] if am.get("note") else "")]
        elif am.get("note"):
            M += ["", "All models: %s" % am["note"]]
        if p.get("derived"):
            d = p["derived"]
            M += ["", "Derived: %s output tokens/day - %s (%s)."
                  % (num(d.get("output_tokens_per_day")), d.get("how", ""), d.get("confidence", "DERIVED"))]
        if p.get("free_models_combined"):
            M += ["", "| Lifetime credits purchased | Req/min | Req/day |", "|---|---|---|"]
            for cond, v in p["free_models_combined"].items():
                M.append("| %s | %s | %s |" % (cond.replace("_", " "), v["rpm"], v["rpd"]))
        if p.get("tiers"):
            M += ["", "| Tier | Req/min | Req/day | How you get there |", "|---|---|---|---|"]
            for tier, v in p["tiers"].items():
                M.append("| %s | %s | %s | %s |" % (tier, num(v.get("rpm"), "-"), num(v.get("rpd"), "-"),
                                                     v.get("unlock", "a new account")))
        if p.get("unverified_accounts"):
            u = p["unverified_accounts"]
            M += ["", "Published for unverified accounts: %s requests/day, %s requests/hour - %s (%s)."
                  % (num(u.get("rpd"), "-"), num(u.get("rph"), "-"), u.get("applies_to", ""),
                     u.get("confidence", "DECLARED"))]
        if p.get("unlock"):
            M += ["", "Unlock: %s. Their words: %s" % (unlock_text(p), p["unlock"].get("quote", ""))]
        if p.get("free_allocation"):
            M += ["", "Free allocation: %s" % json.dumps(p["free_allocation"])]
            if p.get("neuron_cost_examples"):
                M += ["", "| Model | Neurons / M input | Neurons / M output |", "|---|---|---|"]
                for mid, v in p["neuron_cost_examples"].items():
                    M.append("| `%s` | %s | %s |" % (mid, num(v["input_per_million"]), num(v["output_per_million"])))
        if p.get("measured_concurrency"):
            M += ["", "**Concurrency, measured %s** - how many calls the model takes in parallel, which no "
                      "rate-limit table tells you:" % p["measured_concurrency"].get("measured_on", "?")]
            for mid, note in p["measured_concurrency"].items():
                if mid != "measured_on":
                    M.append("- `%s`: %s" % (mid, note))
        if p.get("readings"):
            M += ["", "| Read at (UTC) | HTTP | Tokens/min header | Req/min header |", "|---|---|---|---|"]
            for rd in p["readings"]:
                M.append("| %s | %s | %s | %s |" % (rd.get("utc"), rd.get("http"),
                                                    num(rd.get("limit_tokens_minute"), "-"),
                                                    num(rd.get("limit_req_minute"), "-")))
        if p.get("authenticated_tier"):
            t = p["authenticated_tier"]
            M += ["", "Authenticated tier: %s requests/minute, %s - %s." % (num(t.get("rpm"), "?"), t.get("kind"), t.get("why"))]
        if p.get("monthly") and p["monthly"].get("confidence") in ("MEASURED", "DECLARED"):
            M += ["", "Monthly: %s, %s." % (grant_size(p["monthly"]), p["monthly"].get("expires") or "UNKNOWN")]
        if p.get("one_time") and p["one_time"].get("confidence") in ("MEASURED", "DECLARED"):
            M += ["", "One-time: %s, expires %s." % (grant_size(p["one_time"]), p["one_time"].get("expires") or "UNKNOWN")]
        if p.get("quotes"):
            M += ["", "Their words:"] + ["> %s" % q.replace(chr(10), " ") for q in p["quotes"]]
        sg = p.get("signup_requires")
        if sg:
            M += ["", "Sign-up requires: card %s, phone %s%s (read %s)."
                  % (sg.get("card", "?"), sg.get("phone", "?"),
                     (" - " + sg["note"]) if sg.get("note") else "", sg.get("read_on", "?"))]
    (out / "LIMITS.md").write_text(chr(10).join(M) + chr(10), encoding="utf-8", newline=chr(10))

    print("ranked %d endpoints, %d unranked, %d buried" % (len(rows), len(unranked), len(buried)))
    if rows:
        print("  top: %s @ %s  value=%s (coding %s, %s/day %s%s)"
              % (rows[0]["model"], rows[0]["provider"], rows[0]["value"], rows[0]["coding_index"],
                 num(rows[0]["daily_tokens"]), rows[0]["volume_confidence"],
                 ", no key" if rows[0]["auth"] == "NO KEY" else ""))
    print("  no-key endpoints: %d" % len(noauth))
    print("wrote RESULTS.md, ALL-ENDPOINTS.md, LIMITS.md, data/ranking.json, data/ranking.csv, data/capacity.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
