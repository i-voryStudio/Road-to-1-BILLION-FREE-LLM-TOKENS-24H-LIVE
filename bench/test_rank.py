#!/usr/bin/env python3
"""The page generator, tested two ways. Exit 0 clean, 1 not.

    python bench/test_rank.py             # check
    python bench/test_rank.py --record    # rewrite the golden blocks from the current output (review the diff!)

`bench/rank.py` writes every number on every public page. Until this file existed it had no test, so a
label could change meaning - DECLARED printed on a figure nobody declared, a paid plan's number ranked at
#3, a 0% answered rate printed as "?" - and nothing but a reader would notice. Then it had a fixture, and
the fixture was not enough either: a provider-specific multiplier planted in rank.py changed the real
headline five-fold while the fixture, the claims gate and the regeneration check all stayed green, because
the fixture has no such provider and the regeneration check compares the generator with itself. So now:

  PART ONE, THE FIXTURE (bench/tests/fixture/): five invented providers walk every label path: MEASURED,
  DECLARED, DERIVED from a request cap, DERIVED from the model's own unit price, a model whose unit price
  is not on file (UNKNOWN, unranked, with the reason), PAID-PLAN, DRAWN; a keyless provider whose door is
  its documentation page; a degraded endpoint; a 0%-answered endpoint; a 0-rate burst row; a no-rate burst
  row; a burst row from the older script with no `first_error`; a buried endpoint; a sign-up link on a
  lookalike domain that must fall back to the API host. data/ranking.json fields are asserted one by one,
  one row's value is recomputed by hand from the numbers in the published formula string, the ROAD,
  BARS, HEADLINE and CAPACITY blocks are compared BYTE FOR BYTE with golden files, and rank.py is run twice with
  every output identical, because a generator that is not idempotent makes the daily job commit noise.

  PART TWO, THE ORACLE, on the COMMITTED data and pages of this repo, not on the fixture: every ranked
  row's value recomputes from its own fields with the published formula; every per-provider daily figure
  in data/capacity.json equals a reference recomputation from bench/limits.json written HERE, not a call
  into rank.py; the defensible sum is the sum of the per-provider figures whose label may be summed; no
  PAID-PLAN or UNKNOWN row is ranked; no ranked row sits under the quality floor; the DRAWN shelf holds
  no one-time-grant provider and no unscored model. A multiplier for one provider anywhere in rank.py
  fails this part, whatever the fixture says, because the numbers on the page are recomputed from the
  data by code that is not rank.py.

No network, no keys, standard library only.
"""
import json, math, re, shutil, subprocess, sys, tempfile
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")   # the golden blocks carry the bar glyphs

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
FIX = HERE / "tests" / "fixture"
GOLD = FIX / "golden"
RANK = HERE / "rank.py"
sys.path.insert(0, str(HERE))
import rank   # noqa: E402  the constants under test; the pages are produced by running rank.py as a process
import draw_day   # noqa: E402  the meter's own constants, so the page's "most it can register" is pinned to them

README_TEMPLATE = "# fixture README\n\n" + "".join("<!--%s-->\n<!--/%s-->\n\n" % (m, m) for m in rank.MARKERS)

OUTPUTS = ["README.md", "RESULTS.md", "ALL-ENDPOINTS.md", "LIMITS.md",
           "data/ranking.json", "data/ranking.csv", "data/capacity.json"]
EVIDENCE = ("MEASURED", "DECLARED")
# The sentence every DRAWN figure travels with, for the fixture's epsilon draw: 120 requests over 60 minutes at a
# planned 2 a minute is a realised 2.0, and the figure is a floor for the hour measured, not for a day.
DRAWN_CAVEAT = ("drawn at a planned pace of 2 requests a minute and a realised 2.0 (120 launched over 60 minutes, at most "
                "%d in flight) x %d tokens a call: a floor for the hour measured, times 24, not their ceiling"
                % (draw_day.MAX_IN_FLIGHT, draw_day.MAX_TOKENS_PER_CALL))
TIER_NOTE = "read on a free trial key; may be that tier's allowance, not a standing free tier"


def meter_max_per_hour():
    """What bench/draw_day.py can state at most, from its own constants: the pace cap times the tokens a call,
    or the token cap spread over the shortest capped run that may state a rate, whichever is smaller."""
    return min(draw_day.MAX_PACE_RPM * draw_day.MAX_TOKENS_PER_CALL * 60,
               draw_day.TOKEN_CAP // draw_day.CAP_STOP_MIN_MINUTES * 60)


def comparable(entry):
    """The per-minute figure one provider's limits.json block may set against the output target: the output side
    of a published split, else the bare tpm; the largest per-model figure counts, as the page shows the largest."""
    am = entry.get("all_models") or {}
    tops = {k: am.get(k) or 0 for k in ("tpm", "tpm_input", "tpm_output")}
    for m in (entry.get("models") or {}).values():
        for k in tops:
            tops[k] = max(tops[k], (m or {}).get(k) or 0)
    return tops["tpm_output"] if (tops["tpm_input"] or tops["tpm_output"]) else tops["tpm"]


def run_rank(out):
    (out / "data").mkdir(parents=True, exist_ok=True)
    for name in ("uptime.jsonl", "throughput.jsonl", "drawn.jsonl", "viability.json"):
        shutil.copy(FIX / name, out / "data" / name)
    if not (out / "README.md").exists():
        (out / "README.md").write_text(README_TEMPLATE, encoding="utf-8", newline="\n")
    r = subprocess.run([sys.executable, str(RANK), "--date", "2026-09-07", "--out", str(out),
                        "--providers", str(FIX / "providers.json"), "--limits", str(FIX / "limits.json"),
                        "--privacy", str(FIX / "privacy.json"), "--scores", str(FIX / "scores.json"),
                        "--reliability", str(FIX / "reliability.json")],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def block(text, marker):
    m = re.search(r"<!--%s-->\n(.*?)<!--/%s-->" % (marker, marker), text, flags=re.S)
    return m.group(1) if m else None


def read_jsonl(path):
    rows = []
    if path.exists():
        for line in path.read_text(encoding="utf-8").split("\n"):
            if line.strip():
                rows.append(json.loads(line))
    return rows


def parse_formula(formula):
    """(tokens per reply, no-key bonus, degraded penalty) from the printed formula string, or None."""
    m = re.match(r"coding_index x log10\(1 \+ daily_tokens / (\d+)\) x answered_rate x ([\d.]+) if no key x ([\d.]+) if degraded$",
                 formula or "")
    return (int(m.group(1)), float(m.group(2)), float(m.group(3))) if m else None


def formula_value(coding, daily, rate, needs_key, degraded, consts):
    per_reply, bonus, penalty = consts
    v = coding * math.log10(1 + daily / per_reply) * rate
    if not needs_key:
        v *= bonus
    if degraded:
        v *= penalty
    return round(v, 1)


# ---------------------------------------------------------------------------------------------------
# THE REFERENCE, written here and not imported: what limits.json says one endpoint gets in a day.
# ---------------------------------------------------------------------------------------------------
def ref_volume(lim, name, model, per_reply):
    """(daily tokens or None, label) for one endpoint, from bench/limits.json alone.

    The token figure the provider states and the request cap times per_reply are candidates only when
    their own confidence is MEASURED or DECLARED; the smaller binds. Failing both, a unit price divided
    into an allowance counts only for THIS model's price, or for a provider-level figure when the provider
    publishes one price for every model. A paid-plan figure keeps its number under the PAID-PLAN label."""
    p = (lim.get("providers") or {}).get(name) or {}
    am = p.get("all_models") or {}
    e = (p.get("models") or {}).get(model) or am
    base = p.get("confidence", "UNKNOWN")
    rpd, tpd = e.get("rpd"), e.get("tpd")
    rconf, tconf = e.get("rpd_confidence") or base, e.get("tpd_confidence") or base
    if rpd is None and p.get("free_models_combined"):
        rpd = min(v["rpd"] for v in p["free_models_combined"].values())
    cands = []
    if tpd and tconf in EVIDENCE:
        cands.append((tpd, tconf))
    if rpd and rconf in EVIDENCE:
        cands.append((rpd * per_reply, "DERIVED"))
    if not cands:
        neurons = (p.get("free_allocation") or {}).get("neurons_per_day")
        cost = ((p.get("neuron_cost_examples") or {}).get(model) or {}).get("output_per_million")
        d = p.get("derived") or {}
        if neurons and cost:
            cands.append((int(neurons / cost * 1000000), "DERIVED"))
        elif d.get("output_tokens_per_day") and d.get("confidence") == "DERIVED" and d.get("one_price_for_all_models") is True:
            cands.append((d["output_tokens_per_day"], "DERIVED"))
    if not cands:
        return None, "UNKNOWN"
    daily, conf = min(cands, key=lambda c: c[0])
    if e.get("rpd_is_paid_plan"):
        conf = "PAID-PLAN"
    return daily, conf


def one_time_only(entry):
    """True when the only free capacity a provider records is a one-time grant: no recurring figure at all."""
    ot = entry.get("one_time") or {}
    am = entry.get("all_models") or {}
    recurring = (any(am.get(k) for k in ("rpd", "tpd")) or bool(entry.get("monthly")) or bool(entry.get("derived"))
                 or any((m or {}).get("rpd") or (m or {}).get("tpd") for m in (entry.get("models") or {}).values()))
    return bool(ot.get("tokens")) and ot.get("confidence") in EVIDENCE and not recurring


def ref_shelf(providers, lim, scores, drawn_rows, buried, floor, per_reply, rankable):
    """{provider: (daily, label)}: the largest rankable figure among the provider's models that clear the
    floor and are not buried; where there is none, the latest draw x 24 for a scored model, unless the
    provider's only free capacity is a one-time grant."""
    coding = {(r["provider"], r["model"]): (r.get("artificial_analysis") or {}).get("coding_index")
              for r in scores.get("matched", [])}
    shelf = {}
    for p in providers["providers"]:
        best = None
        for m in p["models"]:
            key = (p["name"], m["id"])
            c = coding.get(key)
            if key in buried or c is None or c < floor:
                continue
            daily, conf = ref_volume(lim, p["name"], m["id"], per_reply)
            if daily and conf in rankable and (best is None or daily > best[0]):
                best = (daily, conf)
        if best:
            shelf[p["name"]] = best
    latest = {}
    for r in drawn_rows:
        if r.get("provider") and r.get("tokens_per_hour_drawn") is not None:
            latest[r["provider"]] = r
    for name, r in latest.items():
        c = coding.get((name, r.get("model")))
        if name in shelf or c is None or c < floor or one_time_only((lim.get("providers") or {}).get(name) or {}):
            continue
        shelf[name] = (int(r["tokens_per_hour_drawn"] * 24), "DRAWN")
    return shelf


def main():
    record = "--record" in sys.argv
    failures = []

    def check(cond, what):
        print("%s %s" % ("ok  " if cond else "FAIL", what))
        if not cond:
            failures.append(what)

    # =============================================================================================
    # PART ONE: the fixture
    # =============================================================================================
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp)
        code, log = run_rank(out)
        check(code == 0, "rank.py exits 0 on the fixture" + ("" if code == 0 else ": " + log[-600:]))
        if code != 0:
            return 1
        first = {f: (out / f).read_bytes() for f in OUTPUTS}
        for f, b in first.items():
            check(b"\r\n" not in b, "%s has no CRLF" % f)

        rk = json.loads(first["data/ranking.json"].decode("utf-8"))
        cap = json.loads(first["data/capacity.json"].decode("utf-8"))
        ranked = {r["model"]: r for r in rk["ranked"]}
        unranked = {r["model"]: r for r in rk["unranked"]}
        buried = {r["model"]: r for r in rk["buried"]}

        # ---- ranking.json, field by field
        print("\n=== ranking.json ===")
        check([r["model"] for r in rk["ranked"]] == ["alpha-large", "delta-7b", "beta-coder", "gamma-chat:free"],
              "ranked order: %s" % [r["model"] for r in rk["ranked"]])
        check(ranked["alpha-large"]["volume_confidence"] == "MEASURED" and ranked["alpha-large"]["daily_tokens"] == 1000000,
              "alpha: the token cap (MEASURED, 1,000,000) binds before 4,000 requests x 500")
        check(ranked["beta-coder"]["volume_confidence"] == "DECLARED" and ranked["beta-coder"]["daily_tokens"] == 300000,
              "beta: a daily figure published in tokens is DECLARED")
        check(ranked["gamma-chat:free"]["volume_confidence"] == "DERIVED" and ranked["gamma-chat:free"]["daily_tokens"] == 50000,
              "gamma: 100 requests x 500 is DERIVED, never DECLARED")
        check("100 requests/day (DECLARED) x 500 tokens a reply = 50,000 tokens/day" in ranked["gamma-chat:free"]["volume_evidence"],
              "gamma: the arithmetic is written into volume_evidence")
        check(ranked["delta-7b"]["volume_confidence"] == "DERIVED" and ranked["delta-7b"]["daily_tokens"] == 200000
              and "on this model" in ranked["delta-7b"]["volume_evidence"],
              "delta-7b: derived from the model's own unit price")
        check(unranked["delta-70b"]["volume_confidence"] == "UNKNOWN" and unranked["delta-70b"]["daily_tokens"] is None
              and unranked["delta-70b"]["why_unranked"] == "daily volume unknown: this model's unit price is not on file - see LIMITS.md"
              and unranked["delta-70b"]["volume_unknown_reason"] == "this model's unit price is not on file",
              "delta-70b: no price of its own and the provider prices per model, so UNKNOWN, unranked, with the reason")
        check(unranked["epsilon-pro"]["why_unranked"] == "only a paid-plan figure is published"
              and unranked["epsilon-pro"]["volume_confidence"] == "PAID-PLAN"
              and unranked["epsilon-pro"]["daily_tokens"] == 100000,
              "epsilon-pro: PAID-PLAN is shown and not ranked")
        check(unranked["alpha-mini"]["why_unranked"].startswith("no official benchmark score"),
              "alpha-mini: no score, not ranked")
        check(unranked["beta-small"]["why_unranked"].startswith("below the quality floor: coding index 30.0"),
              "beta-small: scored under the floor, listed and never ranked")
        check(cap["per_provider"]["beta"]["daily_tokens"] == 300000 and cap["per_provider"]["beta"]["model"] == "beta-coder",
              "beta: the account's daily figure stays on the shelf through the model that clears the floor")
        check(cap["quality_floor_coding_index"] == rank.QUALITY_FLOOR == rk["quality_floor_coding_index"],
              "the floor is written into capacity.json and ranking.json")
        check("epsilon-lite" in buried and buried["epsilon-lite"]["value"] is None
              and buried["epsilon-lite"]["daily_tokens"] is None,
              "epsilon-lite: buried, out of the ranking and out of every sum")
        check(ranked["delta-7b"]["auth"] == "NO KEY" and ranked["delta-7b"]["noauth_bonus_applied"] is True,
              "delta: keyless, bonus applied")
        check(ranked["beta-coder"].get("degraded_penalty_applied") == 0.5 and ranked["beta-coder"]["viability"] == "degraded",
              "beta: degraded penalty applied")
        check(ranked["gamma-chat:free"]["answered_rate"] == 0.0 and ranked["gamma-chat:free"]["value"] == 0.0
              and ranked["gamma-chat:free"]["answers"] == "0 of 2 in 14 days",
              "gamma: two empty 200s are 0 of 2, value 0.0, printed as a measurement")
        check(unranked["delta-70b"]["answered_rate"] is None
              and unranked["delta-70b"]["answers"] == "not on the radar yet; the provider answered the 30-second burst on 2026-09-01 with `delta-7b`",
              "delta-70b: not on the radar, says so, and names the burst the provider did answer, with the model it called")
        check(unranked["alpha-mini"]["answers"] == "0 of 1 in 14 days" and ranked["delta-7b"]["answers"] == "1 of 1 in 14 days",
              "an endpoint the radar reached prints the radar tally alone: the other instruments never replace it")
        check(ranked["alpha-large"]["radar_probes"] == [2, 2],
              "alpha-large: the row from 2026-08-01 is outside the window and ignored")
        check(ranked["beta-coder"]["answered_rate"] == 0.5, "beta: 1 of 2 in the window")
        check(ranked["alpha-large"]["get_key"] == "https://console.alpha.example/keys"
              and ranked["alpha-large"]["get_key_kind"] == "signup",
              "alpha: sign-up link on the API domain is used")
        check(ranked["beta-coder"]["get_key"] == "https://inference.beta.example/"
              and ranked["beta-coder"]["get_key_kind"] == "api_host",
              "beta: sign-up link on a lookalike domain is refused, API host used instead")
        check(ranked["delta-7b"]["get_key"] == "https://delta.example/pricing" and ranked["delta-7b"]["get_key_kind"] == "docs",
              "delta: keyless, so the door is the documentation page from limits.json, on the provider's own domain")
        check(ranked["gamma-chat:free"]["cost"] == "region-restricted; $1 top-up unlocks the daily quota",
              "gamma: Cost carries the region flag and the unlock condition")
        check(ranked["alpha-large"]["cost"] == "**trains on your prompts**", "alpha: Cost carries the privacy flag")
        check(ranked["beta-coder"]["cost"] == "-" and ranked["delta-7b"]["cost"] == "-",
              "beta, delta: nothing on file (no privacy term read, no unlock) prints a dash, not a sentence")
        check(ranked["alpha-large"]["measured_on_tier"] == "free trial"
              and ranked["alpha-large"]["tier_note"] == "read on a free trial key; may be that tier's allowance, not a standing free tier"
              and "Read on a free trial key" in ranked["alpha-large"]["volume_evidence"]
              and ranked["beta-coder"]["measured_on_tier"] is None and ranked["beta-coder"]["tier_note"] is None,
              "alpha: a MEASURED figure read on a free-trial key carries the tier from limits.json; beta carries none")
        check(ranked["alpha-large"]["returned_empty_200"] == 1, "alpha: archived empty-200 is carried, as a count")
        check(rk["ranking_formula"] == rank.FORMULA == "coding_index x log10(1 + daily_tokens / 500) x answered_rate x 1.25 if no key x 0.5 if degraded",
              "the formula string is the agreed one")
        check(rk["volume_labels"] == list(rank.LABELS) and rk["rankable_volume_labels"] == list(rank.RANKABLE)
              and rk["summable_volume_labels"] == list(rank.SUMMABLE) == cap["summable_labels"],
              "the label vocabulary in ranking.json and capacity.json is the one in rank.py")

        # ---- one row by hand, from the numbers in the formula string
        print("\n=== the formula, recomputed by hand ===")
        consts = parse_formula(rk["ranking_formula"])
        check(consts is not None, "formula string parses into its three constants")
        if consts:
            per_reply, bonus, penalty = consts
            beta = round(60.0 * math.log10(1 + 300000 / per_reply) * 0.5 * penalty, 1)
            check(beta == ranked["beta-coder"]["value"] == 41.7,
                  "beta-coder by hand: 60 x log10(1 + 300000/%d) x 0.5 x %s = %s" % (per_reply, penalty, beta))
            delta = round(47.0 * math.log10(1 + 200000 / per_reply) * 1.0 * bonus, 1)
            check(delta == ranked["delta-7b"]["value"] == 152.9,
                  "delta-7b by hand: 47 x log10(1 + 200000/%d) x 1.0 x %s = %s" % (per_reply, bonus, delta))
            alpha = round(70.0 * math.log10(1 + 1000000 / per_reply), 1)
            check(alpha == ranked["alpha-large"]["value"] == 231.1, "alpha-large by hand = %s" % alpha)
        for page in ("RESULTS.md", "ALL-ENDPOINTS.md"):
            check(rk["ranking_formula"] in first[page].decode("utf-8"), "%s prints the same formula string" % page)

        # ---- capacity.json: the daily shelf, the bursts, the ceilings
        print("\n=== capacity.json ===")
        sh = cap["daily_shelf"]
        check(sh["measured"]["tokens_per_day"] == 1000000 and sh["measured"]["providers"] == ["alpha"], "measured shelf: alpha only")
        check(sh["declared"]["tokens_per_day"] == 300000 and sh["declared"]["providers"] == ["beta"], "declared shelf: beta only")
        check(sh["derived"]["tokens_per_day"] == 250000 and sh["derived"]["providers"] == ["delta", "gamma"],
              "derived shelf: gamma 50,000 + delta 200,000, and delta-70b's borrowed 200,000 is nowhere")
        check(sh["drawn"]["tokens_per_day"] == 480000 and sh["drawn"]["providers"] == ["epsilon"],
              "drawn shelf: epsilon 20,000/h x 24, and NOT alpha, which has a measured figure")
        check(cap["per_provider"]["alpha"]["confidence"] == "MEASURED", "alpha keeps MEASURED over DRAWN")
        check(DRAWN_CAVEAT in cap["per_provider"]["epsilon"]["evidence"],
              "epsilon: the DRAWN evidence carries the planned pace, the realised pace, the tokens a call and the floor caveat")
        check(cap["per_provider"]["alpha"]["measured_on_tier"] == "free trial" and cap["per_provider"]["gamma"]["unlock"] == "$1 top-up unlocks the daily quota"
              and cap["per_provider"]["beta"]["measured_on_tier"] is None and cap["per_provider"]["beta"]["unlock"] is None,
              "capacity.json per_provider carries the tier and the unlock condition next to the figure")
        check(cap["defensible_tokens_per_day"] == 2030000 and cap["share_of_target_pct"] == 0.2
              and cap["multiple_still_needed"] == 492.6,
              "defensible = 2,030,000 = 0.2%% of 1e9, 492.6x still needed")
        check(cap["defensible_tokens_per_day"] == sum(v["daily_tokens"] for v in cap["per_provider"].values()
                                                       if v["confidence"] in rank.SUMMABLE),
              "defensible is the sum of the per-provider figures with a summable label")
        check(cap["paid_plan_tokens_per_day_excluded"] == 100000 and cap["paid_plan_per_provider"] == {"epsilon": 100000},
              "paid-plan figure shown as excluded, not in any sum")
        dist = cap["distance"]
        check(dist["gap_tokens_per_day"] == 1000000000 - 2030000 and dist["median_daily_figure"] == 300000
              and dist["providers_at_median_to_close_gap"] == math.ceil((1000000000 - 2030000) / 300000)
              and dist["ceilings_at_or_above_target_rate"] == [],
              "distance: the gap, the median figure and the providers-at-median count are arithmetic on the shelf")
        b = cap["burst"]
        check(b["tokens_per_minute_added_up"] == 22500 and b["providers_delivered"] == ["alpha", "beta", "delta"],
              "burst: 12,000 + 8,000 + 2,500 from three providers that delivered")
        check(b["providers_measured_zero"] == ["gamma"] and b["providers_no_rate"] == ["epsilon"],
              "burst: gamma measured at 0, epsilon no rate; neither counts as delivering")
        alpha_b = [w for w in b["per_provider"] if w["provider"] == "alpha"][0]
        check(alpha_b["holds_up"] is False and alpha_b["best_seen"] == 30000 and alpha_b["readings"] == 2,
              "alpha burst: latest 12,000, best 30,000, does not hold up")
        check(b["largest_drop_between_readings"] == 2.5, "largest drop 2.5x")
        c = cap["ceilings_per_minute"]
        check(c["output_only_tokens_per_minute"] == 50000 and c["output_only_providers"] == ["beta"],
              "output-only ceilings: beta's 50,000 out, and its 400,000 in is not added anywhere")
        check(c["combined_or_unspecified_tokens_per_minute"] == 26000 and c["combined_or_unspecified_providers"] == ["alpha", "epsilon"],
              "combined ceilings: alpha 20,000 + epsilon 6,000 (per model, largest)")
        check(c["requests_per_minute"] == 125 and c["providers_with_any_per_minute_figure"] == 5, "rpm sum 125 across 5")
        eps = [e for e in c["per_provider"] if e["provider"] == "epsilon"][0]
        check(eps["per_model_largest_shown"] is True, "epsilon's ceiling is marked per model")
        check(cap["one_time"]["tokens"] == 500000 and cap["one_time"]["credits_usd"] == 0.0, "one-time: alpha's 500,000 tokens")
        check(cap["monthly"]["credits_usd"] == 5 and cap["monthly"]["grants"][0]["provider"] == "beta", "monthly: beta's $5")
        check(cap["providers_with_no_daily_figure"] == [], "every fixture provider lands on some shelf")

        # ---- pages
        print("\n=== pages ===")
        readme = first["README.md"].decode("utf-8")
        check(block(readme, "FORMULA") == "`%s`\n" % rk["ranking_formula"], "README prints the same formula string")
        check(block(readme, "LABELS").count("| **") == len(rank.LABELS), "README legend carries every label, and only those")
        bar = block(readme, "BAR")
        check(("only %s of the %s labels may be on it: %s" % (rank.numword(len(rank.SUMMABLE)), rank.numword(len(rank.LABELS)),
                                                              rank.words(rank.SUMMABLE))) in bar,
              "README BAR block names the summable labels from the constants")
        alle = first["ALL-ENDPOINTS.md"].decode("utf-8")
        limits_md = first["LIMITS.md"].decode("utf-8")
        results = first["RESULTS.md"].decode("utf-8")
        check(rank.LABEL_RULE in limits_md and rank.LABEL_RULE in alle, "LIMITS.md and ALL-ENDPOINTS.md print the one label sentence")
        check(limits_md.count("\n- **") >= len(rank.LABELS) and all("- **%s** - " % k in limits_md for k in rank.LABELS),
              "LIMITS.md legend has a bullet per label")
        check("read on" not in limits_md.split("\n")[2], "LIMITS.md header carries no page-level read date")
        table = [l for l in alle.split("\n") if l.startswith("| `")]
        answers_col = 12   # | Model | Provider | Value | Get key | Coding | Intelligence | Agentic | Arena | Tokens/day | Req/day | Volume | Answers |
        gamma_row = [l for l in table if l.startswith("| `gamma-chat:free`")][0]
        check(gamma_row.split("|")[answers_col].strip() == "0 of 2 (0%)"
              and not any(l.split("|")[answers_col].strip() == "?" for l in table),
              "ALL-ENDPOINTS: 0% prints as 0%, and no Answers cell is ever ?")
        d70 = [l for l in alle.split("\n") if l.startswith("| `delta-70b`")][0]
        check("| not on the radar yet; the provider answered the 30-second burst on 2026-09-01 with `delta-7b` |" in d70
              and "unit price is not on file" in d70,
              "ALL-ENDPOINTS: not on the radar says so, with the burst the provider answered; the UNKNOWN reason is in the note")
        top5 = block(readme, "TOP5")
        check(top5 is not None and top5.count("[get a key](") == 3 and "no key needed: [docs](https://delta.example/pricing)" in top5,
              "TOP5: every row has a door, and the keyless one points at the docs")
        check("returned an empty reply once in the archived run" in top5, "TOP5: the archived empty reply is said in plain words")
        check("## The full ranking: all 4 ranked endpoints" in block(readme, "RANKING-HEAD"), "RANKING-HEAD: the heading carries the count")
        check("| **0.0** (no answer in 14 days, so no value) |" in block(readme, "RANKING")
              and "0 of 2 in 14 days" in block(readme, "RANKING"),
              "RANKING: the 0.0 row says why it is zero, in the cell a stranger reads")
        rel_blk = block(readme, "RELIABILITY")
        check("| Endpoints with a verdict | Endpoints probed | Endpoints tracked |" in rel_blk
              and "| [epsilon](https://console.epsilon.example/) | 1 of 1 (100%) | 1 | 2 | 2 |" in rel_blk
              and all(n in rel_blk for n in ("alpha", "beta", "gamma", "delta", "epsilon")),
              "RELIABILITY: three counts with three meanings; epsilon has one verdict, two probed, two tracked")
        ex = block(readme, "EXAMPLE")
        check("**70.0**, belongs to `alpha-large`" in ex and "at alpha it sits at #1 with a value of 231.1" in ex,
              "EXAMPLE: the top score and its rank, from data")
        check("1 empty 200s, 1 of them" in block(readme, "TRAP"), "TRAP: counts from the archived run")
        kl = block(readme, "KEYLESS")
        check("https://delta.example/pricing" in kl and "2026-09-01" in kl and "1 of 2 endpoints ranked" in kl
              and "unit price is not on file" in kl,
              "KEYLESS: the keyless provider, its date, and where its endpoints sit today with the reason")
        road = block(readme, "ROAD")
        check("1 delivered nothing (gamma: rate limit reached)" in road, "ROAD: a zero burst names its cause, and does not say answered")
        check("*What it would take.*" in road and "3,327 more providers at that median" in road
              and "capped at %d requests a minute" % rank.MAX_PACE_RPM in road,
              "ROAD: the distance paragraph is computed from the shelf and the meter's constants")
        capacity = block(readme, "CAPACITY")
        check("| DRAWN; %s |" % DRAWN_CAVEAT in capacity, "CAPACITY: the DRAWN row carries the caveat")
        check("| **[beta](https://inference.beta.example/)** | 8,000 |  | 800,000 in / 50,000 out | 60 | 300,000 | DECLARED | $5 in credits | - | yes | **yes** | ? |" in capacity,
              "CAPACITY: a sign-up page that was read and does not say prints ?")
        check("| 1,000,000 | MEASURED; %s |" % TIER_NOTE in capacity and "| 20,000 in+out |" in capacity
              and "| 6,000, scope unspecified (per model, largest) |" in capacity,
              "CAPACITY: the tier travels with alpha's MEASURED figure; a bare tpm prints in+out only where the provider says so, "
              "and scope unspecified where it does not")

        # ---- the sentences the review found refuting the page they sat on, pinned to the fixture and the meter
        print("\n=== the ROAD paragraph: ceilings and the meter ===")
        check(rank.comparable_ceiling({"tpm": 4000000, "tpm_input": 4000000, "tpm_output": 100000}) == 100000
              and rank.comparable_ceiling({"tpm_input": 4000000}) == 0
              and rank.comparable_ceiling({"tpm": 5000000}) == 5000000
              and rank.comparable_ceiling({}) == 0,
              "comparable_ceiling: the output side of a split, else the bare tpm; an input figure alone compares as nothing")
        target_min = rank.TARGET_TOKENS_PER_DAY / 1440.0
        fix_lim = json.loads((FIX / "limits.json").read_text(encoding="utf-8"))["providers"]
        check(fix_lim["beta"]["all_models"]["tpm_input"] > target_min > fix_lim["beta"]["all_models"]["tpm_output"],
              "the fixture's beta publishes a split whose input sits above the target's rate and whose output sits under it")
        check(dist["ceilings_at_or_above_target_rate"] == [] and "beta" not in road.split("*What it would take.*")[-1].split("The draw meter")[0]
              and "No provider publishes a per-minute ceiling at or above the %s a minute the target works out to, counting the "
                  "output ceiling where a split is published and the bare figure where it is not." % "{:,}".format(round(target_min)) in road,
              "ROAD: beta's 800,000 INPUT ceiling never qualifies it as at or above the output target, and the sentence states the rule")
        meter = dist["meter"]
        check(meter["max_registrable_tokens_per_hour"] == meter_max_per_hour()
              and meter["max_registrable_tokens_per_day"] == meter_max_per_hour() * 24
              and meter["max_registrable_tokens_per_hour"] < draw_day.MAX_PACE_RPM * draw_day.MAX_TOKENS_PER_CALL * 60
              and meter["cap_stop_min_minutes"] == draw_day.CAP_STOP_MIN_MINUTES and meter["token_cap_per_run"] == draw_day.TOKEN_CAP,
              "capacity.json meter: the most the meter can register is min(pace x tokens x 60, cap / %d min x 60) = %s an hour, "
              "from draw_day's own constants, under the pace-only figure" % (draw_day.CAP_STOP_MIN_MINUTES, "{:,}".format(meter_max_per_hour())))
        check(("stopping at %s tokens, and a run the cap stops states a rate only after %d minutes, so the most it can register from "
               "one provider is %s tokens an hour, %s a day." % ("{:,}".format(draw_day.TOKEN_CAP), draw_day.CAP_STOP_MIN_MINUTES,
                                                                  "{:,}".format(meter_max_per_hour()), "{:,}".format(meter_max_per_hour() * 24))) in road
              and "{:,}".format(draw_day.MAX_PACE_RPM * draw_day.MAX_TOKENS_PER_CALL * 60) not in road,
              "ROAD: the meter maximum printed is the one the meter can produce, and the pace-only figure is nowhere on the page")
        check("(alpha says in+out; epsilon does not say which)" in road,
              "ROAD: a combined ceiling is called in+out only for the provider whose words say so")

        print("\n=== conditions travel with the figure ===")
        check("1,000,000 measured from response headers or usage endpoints (1 provider; alpha: 1,000,000 %s)" % TIER_NOTE in road
              and "(2 providers; gamma: 50,000 only after a one-time $1 top-up)" in road,
              "ROAD: the measured shelf carries alpha's trial tier and the derived shelf carries gamma's unlock")
        hb = block(readme, "HEADLINE")
        check("| measured by us from headers or usage endpoints | 1,000,000 (alpha: 1,000,000 %s) |" % TIER_NOTE in hb
              and "| 250,000 (gamma: 50,000 only after a one-time $1 top-up) |" in hb,
              "HEADLINE: the same two qualifiers on the same two rows")
        check("| 1,000,000 | MEASURED; %s |" % TIER_NOTE in top5 and top5.count("MEASURED; ") == 1,
              "TOP5: alpha's Volume cell carries the tier, and no other row carries one")
        check("| 300,000 | DECLARED | 1 of 2 in 14 days | - |" in top5 and "| region-restricted; $1 top-up unlocks the daily quota |" in top5,
              "TOP5: a Cost cell with nothing on file is a dash; gamma keeps its flag and its unlock")
        check("| **3 of 5 measured** |" in hb and "| no burst row yet | none |" in hb
              and "**3 of the 5 providers measured handed us" in road
              and "1 measured with no rate to state (epsilon: five failures in a row: HTTP 403: the endpoint refused the caller)" in road
              and b["providers_measured"] == 5 and b["providers_without_a_burst_row"] == [],
              "bursts: N of M counts the providers with a burst row, the no-rate rows are named apart, and none is missing")
        check("| `gemini-3.5-flash-lite`" not in limits_md and "| `epsilon-pro` | 20 | 1,000 | 6,000 | 100,000 | PAID-PLAN |" in limits_md,
              "LIMITS.md: the per-model 'Daily figure is' column prints the label the list uses for that model")
        check("| [alpha](https://console.alpha.example/keys) | 10 | 20,000 | input+output | MEASURED |" in limits_md
              and "| [epsilon](https://console.epsilon.example/) | 20 | 6,000 | unspecified | DECLARED; per model, largest shown |" in limits_md
              and "input+output, or unspecified" not in limits_md,
              "LIMITS.md: the denomination column says input+output only where the provider says so, else unspecified")
        check("(MEASURED; %s), on `alpha-large`" % TIER_NOTE in limits_md, "LIMITS.md: the daily figure line carries the tier")
        kr = block(readme, "KEYLESS-RADAR")
        check("latest row per endpoint (2026-09-07)" in kr
              and "delta, 2 tracked endpoints: 1 answered with text (HTTP 200); 1 not on the radar yet" in kr
              and "[`data/uptime.jsonl`](data/uptime.jsonl)" in kr,
              "KEYLESS-RADAR: the keyless tally is generated from the radar's file, per provider, with the date")
        check("Rows are sorted by value, highest first; a tie is broken by provider name, then model id." in results
              and "A `-` under Cost means nothing is on file yet" in results,
              "RESULTS.md: the sort order and the dash are defined on the page")
        check("a documentation host declared in `bench/gate_contributions.py`" in alle
              and "`not on the radar yet` is the absence of one" in alle,
              "ALL-ENDPOINTS: the door rule names the declared hosts, and the Answers legend names the radar")
        for name in ("alpha", "beta", "gamma", "delta", "epsilon"):
            check("## [%s](" % name in limits_md, "LIMITS.md has a section for %s" % name)
        check("| [beta](https://inference.beta.example/) | $5 in credits | monthly |" in limits_md, "LIMITS.md monthly table")
        check("| [alpha](https://console.alpha.example/keys) | 500,000 tokens | 30 days |" in limits_md, "LIMITS.md one-time table")
        check("### 6b. Archived run 2026-08-30, per provider" in results
              and "| [alpha](https://console.alpha.example/keys) | 10 | 90% |" in results,
              "RESULTS.md: the archived run is labelled archived, with calls per provider, provider linked")
        eps_lite = [l for l in table if l.startswith("| `epsilon-lite`")][0]
        check(eps_lite.split("|")[answers_col].strip() == "probed, no verdict yet",
              "ALL-ENDPOINTS: an endpoint that only ever answered 402 or 429 is 'probed, no verdict yet', not 'not probed yet'")
        check("only a paid-plan figure is published" in results, "RESULTS.md: the paid-plan reason")
        check("%s may be ranked; %s may not." % (rank.words(rank.RANKABLE, "or"), rank.words(rank.NEVER_COUNTED + ("DRAWN",))) in results,
              "RESULTS.md: which labels rank a row is generated from the constants")
        # Every output must pass the publication gate's own account-state rules, imported rather than
        # restated, so this test cannot drift from the gate and does not have to spell the phrases out.
        from gate_publish import RULES
        try:
            from gate_publish import strip_allowed
        except ImportError:
            strip_allowed = lambda line: line   # noqa: E731
        account_rules = [(n, pat) for n, pat, _ in RULES if n.startswith("account")]
        check(len(account_rules) >= 1, "the publication gate still has its account-state rules")
        for f in OUTPUTS:
            hits = [(n, line[:80]) for line in first[f].decode("utf-8").split("\n")
                    for n, pat in account_rules if re.search(pat, strip_allowed(line))]
            check(not hits, "%s carries no account state%s" % (f, "" if not hits else ": %s" % hits[:2]))

        # ---- volume_of, on the rule the fixture cannot reach: one price for every model
        print("\n=== volume_of: the provider-level derived figure ===")
        lim = {"providers": {"z": {"confidence": "DECLARED", "derived": {
            "output_tokens_per_day": 123000, "confidence": "DERIVED", "how": "1,000 units / 8,130 units per 1M output tokens",
            "one_price_for_all_models": True}}}}
        v = rank.volume_of("z", "z-any", lim)
        check(v["daily_tokens"] == 123000 and v["confidence"] == "DERIVED" and "one price for every model" in v["evidence"],
              "a provider that publishes one price for all its models lends its derived figure to every model")
        lim["providers"]["z"]["derived"]["one_price_for_all_models"] = False
        v = rank.volume_of("z", "z-any", lim)
        check(v["daily_tokens"] is None and v["confidence"] == "UNKNOWN" and v["reason"] == "this model's unit price is not on file",
              "a provider that prices per model lends nothing: UNKNOWN, with the reason")
        del lim["providers"]["z"]["derived"]["one_price_for_all_models"]
        v = rank.volume_of("z", "z-any", lim)
        check(v["confidence"] == "UNKNOWN", "an undeclared one_price_for_all_models is not a yes")
        lim2 = {"providers": {"y": {"confidence": "DECLARED", "models": {"y-1": {"rpd": 20, "rpd_confidence": "UNKNOWN"}}}}}
        v = rank.volume_of("y", "y-1", lim2)
        check(v["confidence"] == "UNKNOWN" and v["daily_tokens"] is None,
              "a request cap whose own confidence is UNKNOWN derives nothing")
        lim3 = {"providers": {"x": {"confidence": "DECLARED", "all_models": {"rpd": 100, "tpd": 1000000}}}}
        v = rank.volume_of("x", "x-1", lim3)
        check(v["daily_tokens"] == 50000 and v["confidence"] == "DERIVED" and v["tpd_bound_by_requests"] is True,
              "a published token figure with a request cap that binds first is DERIVED and flagged as bound")

        # ---- golden blocks, byte for byte
        print("\n=== golden blocks ===")
        GOLD.mkdir(exist_ok=True)
        for marker in ("BARS", "ROAD", "HEADLINE", "CAPACITY"):
            got = block(readme, marker)
            g = GOLD / ("%s.md" % marker)
            if record:
                g.write_text(got, encoding="utf-8", newline="\n")
                print("recorded %s" % g.name)
                continue
            want = g.read_text(encoding="utf-8") if g.exists() else None
            if got != want:
                import difflib
                diff = "".join(difflib.unified_diff((want or "").splitlines(True), got.splitlines(True),
                                                    "golden/%s.md" % marker, "generated"))
                print(diff[:3000])
            check(got == want, "%s block matches golden/%s.md byte for byte" % (marker, marker))

        # ---- idempotent
        print("\n=== idempotence ===")
        code2, log2 = run_rank(out)
        check(code2 == 0, "second run exits 0")
        for f in OUTPUTS:
            check((out / f).read_bytes() == first[f], "%s identical on the second run" % f)

    # =============================================================================================
    # PART TWO: the oracle, on the committed data and pages
    # =============================================================================================
    print("\n=== the committed pages, recomputed from the committed data ===")
    needed = {"ranking": ROOT / "data" / "ranking.json", "capacity": ROOT / "data" / "capacity.json",
              "limits": HERE / "limits.json", "providers": HERE / "providers.json", "scores": ROOT / "data" / "scores.json"}
    missing = [k for k, p in needed.items() if not p.exists()]
    check(not missing, "the committed data is present: %s" % (", ".join(sorted(needed)) if not missing else "missing " + ", ".join(missing)))
    if not missing:
        rk = json.loads(needed["ranking"].read_text(encoding="utf-8"))
        cap = json.loads(needed["capacity"].read_text(encoding="utf-8"))
        lim = json.loads(needed["limits"].read_text(encoding="utf-8"))
        providers = json.loads(needed["providers"].read_text(encoding="utf-8"))
        scores = json.loads(needed["scores"].read_text(encoding="utf-8"))
        drawn_rows = read_jsonl(ROOT / "data" / "drawn.jsonl")
        viab = json.loads((ROOT / "data" / "viability.json").read_text(encoding="utf-8")) if (ROOT / "data" / "viability.json").exists() else {}
        buried = {(e["provider"], e["model"]) for e in viab.get("buried") or []}
        floor = cap["quality_floor_coding_index"]
        consts = parse_formula(rk["ranking_formula"])
        check(consts is not None, "the committed formula string parses")
        check(floor == rank.QUALITY_FLOOR and rk["quality_floor_coding_index"] == floor,
              "the committed floor is the constant in rank.py (%s)" % floor)
        rankable = tuple(rk["rankable_volume_labels"])
        summable = tuple(cap["summable_labels"])
        check(rankable == rank.RANKABLE and summable == rank.SUMMABLE and rk["volume_labels"] == list(rank.LABELS),
              "the committed label vocabulary is the constants in rank.py")
        coding = {(r["provider"], r["model"]): (r.get("artificial_analysis") or {}).get("coding_index")
                  for r in scores.get("matched", [])}

        # every ranked row: formula, label, floor, and its daily figure from limits.json
        bad_value, bad_label, bad_floor, bad_daily = [], [], [], []
        for r in rk["ranked"]:
            if consts:
                want = formula_value(r["coding_index"], r["daily_tokens"], r["reliability_applied"],
                                     r["auth"] == "KEY", r["viability"] == "degraded", consts)
                if want != r["value"]:
                    bad_value.append((r["provider"], r["model"], r["value"], want))
            if r["volume_confidence"] not in rankable or r["volume_confidence"] in ("PAID-PLAN", "UNKNOWN"):
                bad_label.append((r["provider"], r["model"], r["volume_confidence"]))
            if r["coding_index"] is None or r["coding_index"] < floor or coding.get((r["provider"], r["model"])) != r["coding_index"]:
                bad_floor.append((r["provider"], r["model"], r["coding_index"]))
            daily, conf = ref_volume(lim, r["provider"], r["model"], consts[0] if consts else rank.TOKENS_PER_REPLY)
            if (daily, conf) != (r["daily_tokens"], r["volume_confidence"]):
                bad_daily.append((r["provider"], r["model"], (r["daily_tokens"], r["volume_confidence"]), (daily, conf)))
        check(rk["ranked"] and not bad_value, "every ranked row's value recomputes from its own fields with the formula%s"
              % ("" if not bad_value else ": %s" % bad_value[:3]))
        check(not bad_label, "no PAID-PLAN or UNKNOWN row is ranked%s" % ("" if not bad_label else ": %s" % bad_label[:3]))
        check(not bad_floor, "no ranked row sits under the quality floor, and each carries the imported score%s"
              % ("" if not bad_floor else ": %s" % bad_floor[:3]))
        check(not bad_daily, "every ranked row's daily figure and label recompute from limits.json%s"
              % ("" if not bad_daily else ": %s" % bad_daily[:3]))
        unranked_bad = [(r["provider"], r["model"]) for r in rk["unranked"]
                        if r["coding_index"] is not None and r["coding_index"] >= floor
                        and ref_volume(lim, r["provider"], r["model"], consts[0] if consts else rank.TOKENS_PER_REPLY)[1] in rankable
                        and ref_volume(lim, r["provider"], r["model"], consts[0] if consts else rank.TOKENS_PER_REPLY)[0]
                        and (r["provider"], r["model"]) not in buried]
        check(not unranked_bad, "no row that limits.json and the scores would rank is left unranked%s"
              % ("" if not unranked_bad else ": %s" % unranked_bad[:3]))

        # the daily shelf, provider by provider, against the reference
        ref = ref_shelf(providers, lim, scores, drawn_rows, buried, floor, consts[0] if consts else rank.TOKENS_PER_REPLY, rankable)
        got = {k: (v["daily_tokens"], v["confidence"]) for k, v in cap["per_provider"].items()}
        diff = {k: (got.get(k), ref.get(k)) for k in set(got) | set(ref) if got.get(k) != ref.get(k)}
        check(not diff, "every per-provider daily figure in capacity.json equals the reference recomputation from limits.json%s"
              % ("" if not diff else ": %s" % diff))
        check(cap["defensible_tokens_per_day"] == sum(d for d, c in ref.values() if c in summable) > 0,
              "the defensible sum is the reference shelf summed over the summable labels")
        check(cap["defensible_tokens_per_day"] == sum(v["daily_tokens"] for v in cap["per_provider"].values() if v["confidence"] in summable),
              "the defensible sum is capacity.json's own per-provider figures summed over the summable labels")
        check(all(v["confidence"] in summable for v in cap["per_provider"].values()),
              "nothing on the shelf carries a label that may not be summed")
        want_pct = round(100.0 * cap["defensible_tokens_per_day"] / cap["target_tokens_per_day"], 2)
        check(cap["share_of_target_pct"] == want_pct, "the share of the target is the shelf over the target")

        # DRAWN: only where nothing else exists, only a scored model, never a one-time grant
        drawn_bad = []
        for name, v in cap["per_provider"].items():
            if v["confidence"] != "DRAWN":
                continue
            c = coding.get((name, v["model"]))
            entry = (lim.get("providers") or {}).get(name) or {}
            if c is None or c < floor or one_time_only(entry):
                drawn_bad.append((name, v["model"], c, one_time_only(entry)))
            if any(ref_volume(lim, name, m["id"], consts[0] if consts else rank.TOKENS_PER_REPLY)[1] in rankable
                   and (coding.get((name, m["id"])) or 0) >= floor
                   for p in providers["providers"] if p["name"] == name for m in p["models"]):
                drawn_bad.append((name, "a rankable figure exists"))
        for d in cap.get("drawn", []):
            entry = (lim.get("providers") or {}).get(d["provider"]) or {}
            if d["counted"] and (one_time_only(entry) or (coding.get((d["provider"], d["model"])) or 0) < floor):
                drawn_bad.append((d["provider"], "counted", d["note"][:60]))
            if not d["counted"] and one_time_only(entry) and "one-time grant" not in d["note"]:
                drawn_bad.append((d["provider"], "grant not named", d["note"][:60]))
            if d["counted"] and d["provider"] not in cap["daily_shelf"]["drawn"]["providers"]:
                drawn_bad.append((d["provider"], "counted but not on the drawn shelf"))
        check(not drawn_bad, "the DRAWN shelf excludes one-time-grant providers and unscored models, and fills only where nothing else exists%s"
              % ("" if not drawn_bad else ": %s" % drawn_bad[:3]))
        check(sum(cap["daily_shelf"][k.lower()]["tokens_per_day"] for k in summable) == cap["defensible_tokens_per_day"],
              "the four shelves in capacity.json add up to the defensible figure")

        # the pages carry the same headline and the same vocabulary
        readme_text = (ROOT / "README.md").read_text(encoding="utf-8") if (ROOT / "README.md").exists() else ""
        hb = block(readme_text, "HEADLINE") or ""
        check("**{:,}**".format(cap["defensible_tokens_per_day"]) in hb and "**%.1f%%**" % cap["share_of_target_pct"] in hb,
              "README headline prints capacity.json's defensible figure and share")
        check((block(readme_text, "LABELS") or "").count("| **") == len(rank.LABELS), "README legend carries every label, and only those")
        rh = block(readme_text, "RANKING-HEAD") or ""
        check(("all %d ranked endpoint" % len(rk["ranked"])) in rh, "README ranking heading carries the ranked count")
        for page in ("LIMITS.md", "ALL-ENDPOINTS.md"):
            t = (ROOT / page).read_text(encoding="utf-8") if (ROOT / page).exists() else ""
            check(rank.LABEL_RULE in t, "%s prints the one label sentence" % page)
        contributing = (ROOT / "CONTRIBUTING.md").read_text(encoding="utf-8") if (ROOT / "CONTRIBUTING.md").exists() else ""
        check(not re.search(r"\b(?:three|four|five|six|seven)\s+(?:different\s+)?labels\b", contributing, re.I)
              and "first three" not in contributing,
              "CONTRIBUTING.md states no label count of its own; the vocabulary lives in rank.py")

        # the sentences a stranger reads first, recomputed from the raw files with arithmetic written here
        print("\n=== the committed ROAD, COUNTS, RELIABILITY and LIMITS sentences, against the raw files ===")
        target_min = cap["target_tokens_per_day"] / 1440.0
        want_above = sorted(n for n, e in (lim.get("providers") or {}).items() if comparable(e) >= target_min)
        got_above = [entry.split(" (")[0] for entry in cap["distance"]["ceilings_at_or_above_target_rate"]]
        check(got_above == want_above, "the providers listed at or above the target's rate are exactly those whose output ceiling "
                                       "(or bare tpm) reaches it: %s" % want_above)
        input_only = [n for n, e in (lim.get("providers") or {}).items()
                      if comparable(e) < target_min and max([(e.get("all_models") or {}).get("tpm_input") or 0]
                                                            + [(m or {}).get("tpm_input") or 0 for m in (e.get("models") or {}).values()]) >= target_min]
        check(all(n not in got_above for n in input_only),
              "no provider qualifies on an input ceiling alone (today: %s)" % (input_only or "none on file"))
        meter = cap["distance"]["meter"]
        check(meter["max_registrable_tokens_per_hour"] == meter_max_per_hour() and meter["max_registrable_tokens_per_day"] == meter_max_per_hour() * 24,
              "the committed meter maximum is min(pace x tokens x 60, cap / cap-stop minutes x 60) from draw_day's constants")
        road_text = block(readme_text, "ROAD") or ""
        check("{:,}".format(meter_max_per_hour()) + " tokens an hour" in road_text
              and "{:,}".format(draw_day.MAX_PACE_RPM * draw_day.MAX_TOKENS_PER_CALL * 60) not in road_text,
              "the committed ROAD prints the meter maximum the meter can produce and not the pace-only figure")
        counts_text = block(readme_text, "COUNTS") or ""
        silent = cap.get("providers_with_no_daily_figure", [])
        why = cap.get("why_no_daily_figure", {})
        check("publish none" not in counts_text and all(n in why and why[n] and ("%s (%s)" % (n, why[n])) in counts_text for n in silent),
              "the committed COUNTS names why each provider off the shelf is off it, from its own data, never 'publish none'")
        burst_rows = read_jsonl(ROOT / "data" / "throughput.jsonl")
        burst_ok = {r["provider"] for r in burst_rows if (r.get("requests_ok") or 0) > 0}
        draw_ok = {r["provider"] for r in drawn_rows if (r.get("requests_ok") or 0) > 0}
        measured = {r["provider"] for r in burst_rows if r.get("provider")}
        check(cap["burst"]["providers_measured"] == len(measured)
              and set(cap["burst"]["providers_without_a_burst_row"]) == {p["name"] for p in providers["providers"]} - measured
              and ("**%d of %d measured**" % (len(cap["burst"]["providers_delivered"]), len(measured))) in (block(readme_text, "HEADLINE") or ""),
              "the burst denominator is the providers with a burst row, and the rest are named as having none")
        bad_answers = []
        for r in rk["ranked"] + rk["unranked"]:
            a = r["answers"]
            if not a.startswith("not on the radar yet"):
                continue
            if r["provider"] in burst_ok and "answered the 30-second burst on" not in a:
                bad_answers.append((r["provider"], r["model"], a))
            elif r["provider"] not in burst_ok and r["provider"] in draw_ok and "answered the %d-minute draw on" % draw_day.MINUTES not in a:
                bad_answers.append((r["provider"], r["model"], a))
            elif r["provider"] not in burst_ok | draw_ok and a != "not on the radar yet":
                bad_answers.append((r["provider"], r["model"], a))
        check(not bad_answers, "every 'not on the radar yet' cell names the burst or the draw the provider did answer, and nothing else%s"
              % ("" if not bad_answers else ": %s" % bad_answers[:3]))
        rel_text = block(readme_text, "RELIABILITY") or ""
        bad_rel = [l for l in rel_text.split("\n") if "not on the radar yet" in l
                   and ((re.search(r"\[([^\]]+)\]", l).group(1) in burst_ok) != ("answered the 30-second burst on" in l))]
        check(not bad_rel, "RELIABILITY says which providers off the radar answered the burst, and only those%s"
              % ("" if not bad_rel else ": %s" % bad_rel[:2]))
        limits_text = (ROOT / "LIMITS.md").read_text(encoding="utf-8") if (ROOT / "LIMITS.md").exists() else ""
        prov, bad_tags, n_tags = None, [], 0
        for l in limits_text.split("\n"):
            m = re.match(r"## \[([^\]]+)\]", l)
            if m:
                prov = m.group(1)
            m = re.match(r"\| `([^`]+)` \| [^|]* \| [^|]* \| [^|]* \| [^|]* \| ([A-Z-]+) \|$", l)
            if m and prov:
                n_tags += 1
                want = ref_volume(lim, prov, m.group(1), consts[0] if consts else rank.TOKENS_PER_REPLY)[1]
                if m.group(2) != want:
                    bad_tags.append((prov, m.group(1), m.group(2), want))
        check(n_tags > 0 and not bad_tags, "LIMITS.md's per-model 'Daily figure is' column carries the label the list uses for that "
                                           "model, recomputed from limits.json (%d rows)%s" % (n_tags, "" if not bad_tags else ": %s" % bad_tags[:3]))
        for name, e in (lim.get("providers") or {}).items():
            am = e.get("all_models") or {}
            if am.get("tpm") and not (am.get("tpm_input") or am.get("tpm_output")):
                said = am.get("tpm_scope") == "in+out"
                row = next((l for l in limits_text.split("\n") if l.startswith("| [%s](" % name) and "| %s |" % ("input+output" if said else "unspecified") in l), None)
                check(row is not None, "LIMITS.md denominates %s's bare tpm as %s, as limits.json's tpm_scope says" % (name, "input+output" if said else "unspecified"))
        for name, e in (lim.get("providers") or {}).items():
            tier = e.get("measured_on_tier")
            if tier and name in cap["per_provider"] and cap["per_provider"][name]["confidence"] == "MEASURED":
                note = "read on a %s key" % tier
                check(note in (block(readme_text, "HEADLINE") or "") and note in (block(readme_text, "CAPACITY") or "")
                      and all(note in r["answers"] or note in ("%s" % r.get("tier_note")) for r in rk["ranked"] if r["provider"] == name),
                      "%s's MEASURED figure carries its tier (%s) on the headline, the capacity table and every ranked row" % (name, tier))

    print("\n%d failure(s)" % len(failures))
    for f in failures:
        print("  FAIL " + f)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
