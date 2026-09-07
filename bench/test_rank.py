#!/usr/bin/env python3
"""The page generator, run against a fixture and compared with what it must produce. Exit 0 clean, 1 not.

    python bench/test_rank.py             # check
    python bench/test_rank.py --record    # rewrite the golden blocks from the current output (review the diff!)

`bench/rank.py` writes every number on every public page. Until this file existed it had no test, so a
label could change meaning - DECLARED printed on a figure nobody declared, a paid plan's number ranked at
#3, a 0% answered rate printed as "?" - and nothing but a reader would notice. Now:

  1. A fixture of five invented providers under bench/tests/fixture/ walks every label path: MEASURED,
     DECLARED, DERIVED (from a request cap and from a unit price), PAID-PLAN, UNKNOWN, DRAWN; a keyless
     provider; a degraded endpoint; a 0%-answered endpoint; a 0-rate burst row; a no-rate burst row; a
     burst row from the older script with no `first_error`; a buried endpoint; a sign-up link on a
     lookalike domain that must fall back to the API host.
  2. data/ranking.json fields are asserted one by one.
  3. The ROAD, HEADLINE and CAPACITY blocks are compared BYTE FOR BYTE with golden files.
  4. One row's value is recomputed by hand from the numbers in the published formula string.
  5. rank.py is run twice and every output must be identical: a generator that is not idempotent would
     make the daily job commit noise.

No network, no keys, standard library only.
"""
import json, math, re, shutil, subprocess, sys, tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
FIX = HERE / "tests" / "fixture"
GOLD = FIX / "golden"
RANK = HERE / "rank.py"

README_TEMPLATE = "\n".join([
    "# fixture README", "",
    "<!--TOP5-->", "<!--/TOP5-->", "",
    "<!--FORMULA-->", "<!--/FORMULA-->", "",
    "<!--LABELS-->", "<!--/LABELS-->", "",
    "<!--EXAMPLE-->", "<!--/EXAMPLE-->", "",
    "<!--ROAD-->", "<!--/ROAD-->", "",
    "<!--HEADLINE-->", "<!--/HEADLINE-->", "",
    "<!--RANKING-->", "<!--/RANKING-->", "",
    "<!--COUNTS-->", "<!--/COUNTS-->", "",
    "<!--CAPACITY-->", "<!--/CAPACITY-->", "",
    "<!--RELIABILITY-->", "<!--/RELIABILITY-->", "",
    "<!--TRAP-->", "<!--/TRAP-->", "",
    "<!--KEYLESS-->", "<!--/KEYLESS-->", "",
]) + "\n"

OUTPUTS = ["README.md", "RESULTS.md", "ALL-ENDPOINTS.md", "LIMITS.md",
           "data/ranking.json", "data/ranking.csv", "data/capacity.json"]


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


def main():
    record = "--record" in sys.argv
    failures = []

    def check(cond, what):
        print("%s %s" % ("ok  " if cond else "FAIL", what))
        if not cond:
            failures.append(what)

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

        # ---- 2. ranking.json, field by field
        print("\n=== ranking.json ===")
        check([r["model"] for r in rk["ranked"]] == ["alpha-large", "delta-70b", "delta-7b", "beta-coder", "gamma-chat:free"],
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
        check(ranked["delta-70b"]["volume_confidence"] == "DERIVED" and ranked["delta-70b"]["daily_tokens"] == 200000
              and "not on file" in ranked["delta-70b"]["volume_evidence"],
              "delta-70b: derived from the provider-level block, and says the model's own price is not on file")
        check(unranked["epsilon-pro"]["why_unranked"] == "only a paid-plan figure is published"
              and unranked["epsilon-pro"]["volume_confidence"] == "PAID-PLAN"
              and unranked["epsilon-pro"]["daily_tokens"] == 100000,
              "epsilon-pro: PAID-PLAN is shown and not ranked")
        check(unranked["alpha-mini"]["why_unranked"].startswith("no official benchmark score"),
              "alpha-mini: no score, not ranked")
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
        check(ranked["delta-70b"]["answered_rate"] is None and ranked["delta-70b"]["answers"] == "not probed yet"
              and ranked["delta-70b"]["reliability_applied"] == 1.0,
              "delta-70b: never probed, not penalised, says so")
        check(ranked["alpha-large"]["radar_probes"] == [2, 2],
              "alpha-large: the row from 2026-08-01 is outside the window and ignored")
        check(ranked["beta-coder"]["answered_rate"] == 0.5, "beta: 1 of 2 in the window")
        check(ranked["alpha-large"]["get_key"] == "https://console.alpha.example/keys"
              and ranked["alpha-large"]["get_key_kind"] == "signup",
              "alpha: sign-up link on the API domain is used")
        check(ranked["beta-coder"]["get_key"] == "https://inference.beta.example/"
              and ranked["beta-coder"]["get_key_kind"] == "api_host",
              "beta: sign-up link on a lookalike domain is refused, API host used instead")
        check(ranked["delta-7b"]["get_key"] == "https://open.delta.example/", "delta: keyless, API host printed")
        check(ranked["gamma-chat:free"]["cost"] == "region-restricted; $1 top-up unlocks the daily quota",
              "gamma: Cost carries the region flag and the unlock condition")
        check(ranked["alpha-large"]["cost"] == "**trains on your prompts**", "alpha: Cost carries the privacy flag")
        check(ranked["alpha-large"]["returned_empty_200"] is True, "alpha: archived empty-200 is carried")
        check(rk["ranking_formula"] == "coding_index x log10(1 + daily_tokens / 500) x answered_rate x 1.25 if no key x 0.5 if degraded",
              "the formula string is the agreed one")

        # ---- 4. one row by hand, from the numbers in the formula string
        print("\n=== the formula, recomputed by hand ===")
        m = re.match(r"coding_index x log10\(1 \+ daily_tokens / (\d+)\) x answered_rate x ([\d.]+) if no key x ([\d.]+) if degraded$",
                     rk["ranking_formula"])
        check(m is not None, "formula string parses into its three constants")
        if m:
            per_reply, bonus, penalty = int(m.group(1)), float(m.group(2)), float(m.group(3))
            beta = round(60.0 * math.log10(1 + 300000 / per_reply) * 0.5 * penalty, 1)
            check(beta == ranked["beta-coder"]["value"] == 41.7,
                  "beta-coder by hand: 60 x log10(1 + 300000/%d) x 0.5 x %s = %s" % (per_reply, penalty, beta))
            delta = round(40.0 * math.log10(1 + 200000 / per_reply) * 1.0 * bonus, 1)
            check(delta == ranked["delta-7b"]["value"] == 130.2,
                  "delta-7b by hand: 40 x log10(1 + 200000/%d) x 1.0 x %s = %s" % (per_reply, bonus, delta))
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
              "derived shelf: gamma 50,000 + delta 200,000")
        check(sh["drawn"]["tokens_per_day"] == 480000 and sh["drawn"]["providers"] == ["epsilon"],
              "drawn shelf: epsilon 20,000/h x 24, and NOT alpha, which has a measured figure")
        check(cap["per_provider"]["alpha"]["confidence"] == "MEASURED", "alpha keeps MEASURED over DRAWN")
        check(cap["defensible_tokens_per_day"] == 2030000 and cap["share_of_target_pct"] == 0.2
              and cap["multiple_still_needed"] == 492.6,
              "defensible = 2,030,000 = 0.2%% of 1e9, 492.6x still needed")
        check(cap["paid_plan_tokens_per_day_excluded"] == 100000 and cap["paid_plan_per_provider"] == {"epsilon": 100000},
              "paid-plan figure shown as excluded, not in any sum")
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
        check(block(readme, "LABELS").count("| **") == 6, "README legend carries the six labels")
        alle = first["ALL-ENDPOINTS.md"].decode("utf-8")
        limits_md = first["LIMITS.md"].decode("utf-8")
        results = first["RESULTS.md"].decode("utf-8")
        table = [l for l in alle.split("\n") if l.startswith("| `")]
        answers_col = 12   # | Model | Provider | Value | Get key | Coding | Intelligence | Agentic | Arena | Tokens/day | Req/day | Volume | Answers |
        gamma_row = [l for l in table if l.startswith("| `gamma-chat:free`")][0]
        check(gamma_row.split("|")[answers_col].strip() == "0 of 2 (0%)"
              and not any(l.split("|")[answers_col].strip() == "?" for l in table),
              "ALL-ENDPOINTS: 0% prints as 0%, and no Answers cell is ever ?")
        d70 = [l for l in alle.split("\n") if l.startswith("| `delta-70b`")][0]
        check("| not probed yet |" in d70, "ALL-ENDPOINTS: never probed says so")
        top5 = block(readme, "TOP5")
        check(top5 is not None and top5.count("[get a key](") == 3 and "no key needed: [open.delta.example]" in top5,
              "TOP5: every row has a door")
        check("| **0.0** |" in block(readme, "RANKING") and "0 of 2 in 14 days" in block(readme, "RANKING"),
              "RANKING: the 0.0 row and its cause")
        rel_blk = block(readme, "RELIABILITY")
        check(rel_blk.count("|") > 0 and "| [delta](https://open.delta.example/) | 1 of 1 (100%) | 1 | 2 |" in rel_blk
              and all(n in rel_blk for n in ("alpha", "beta", "gamma", "delta", "epsilon")),
              "RELIABILITY: every provider, from the radar")
        ex = block(readme, "EXAMPLE")
        check("**70.0**, belongs to `alpha-large`" in ex and "at alpha it sits at #1 with a value of 231.1" in ex,
              "EXAMPLE: the top score and its rank, from data")
        check("1 empty 200s, 1 of them" in block(readme, "TRAP"), "TRAP: counts from the archived run")
        check("open.delta.example" in block(readme, "KEYLESS") and "2026-09-01" in block(readme, "KEYLESS"),
              "KEYLESS: the keyless endpoint with its date")
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
        # Every output must pass the publication gate's own account-state rules, imported rather than
        # restated, so this test cannot drift from the gate and does not have to spell the phrases out.
        sys.path.insert(0, str(HERE))
        from gate_publish import RULES, strip_allowed
        account_rules = [(n, pat) for n, pat, _ in RULES if n.startswith("account")]
        check(len(account_rules) >= 1, "the publication gate still has its account-state rules")
        for f in OUTPUTS:
            hits = [(n, line[:80]) for line in first[f].decode("utf-8").split("\n")
                    for n, pat in account_rules if re.search(pat, strip_allowed(line))]
            check(not hits, "%s carries no account state%s" % (f, "" if not hits else ": %s" % hits[:2]))

        # ---- 3. golden blocks, byte for byte
        print("\n=== golden blocks ===")
        GOLD.mkdir(exist_ok=True)
        for marker in ("ROAD", "HEADLINE", "CAPACITY"):
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

        # ---- 5. idempotent
        print("\n=== idempotence ===")
        code2, log2 = run_rank(out)
        check(code2 == 0, "second run exits 0")
        for f in OUTPUTS:
            check((out / f).read_bytes() == first[f], "%s identical on the second run" % f)

    print("\n%d failure(s)" % len(failures))
    for f in failures:
        print("  FAIL " + f)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
