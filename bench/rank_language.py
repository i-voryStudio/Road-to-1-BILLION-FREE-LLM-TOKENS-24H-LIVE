#!/usr/bin/env python3
"""ARCHIVE: the Romanian-language quality benchmark we ran ourselves on 2026-09-06.

This is no longer the main ranking. Running our own benchmark does not scale: new free providers appear
weekly, and each would have to go through the whole battery before it could be listed at all. Quality
now comes from official benchmarks (bench/scores.py), and we measure only what nobody else can tell
you - quota, uptime, auth, and what the free tier costs you in things that are not money.

The run this produced is kept in results/2026-09-06/ and the code is kept working, because deleting a
measurement because it stopped being the headline is how a repo starts lying about its own history.
It is still the only measurement anywhere of how these models write a language that is not English.

Turn raw probe results, jury verdicts and rate limits into the language tables.

    python bench/rank_language.py results.json --jury jury.json --date 2026-09-06 --out .

Writes RESULTS.md into --out and data/models.{json,csv} (LIMITS.md is written by rank.py). Everything
published about the language run is generated from here, so two tables cannot disagree with each other.
The judges block written into data/models.json is copied from bench/judges.json, the one file that says
how each judge is reached, never from the jury file: the jury file records verdicts, and a description of
a judge that lives in two files is a description that will disagree with itself.

Scoring, stated once so it is arguable:
    quality            = 50% mechanical (probes passed / total * 10) + 50% jury mean over all lenses
    quality_for_agents = the same, but the jury mean drops the "sounds human" lens

Why two numbers: a model that writes stiff but correct prose is useless for a blog post and perfectly
good for an extraction step. One number would hide that, so we publish both and say which is which.
A model whose paragraph failed the mechanical check never reached the jury. It is NOT given half a
score on the same scale - that would silently be a zero on the jury half. It gets its mechanical score
out of 10, is marked `scale: probes only`, and is listed in its own section, because a probes-only
number and a probes-plus-jury number are two different measurements.
"""
import argparse, csv, json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TIER = [(2000, "HIGH"), (400, "MEDIUM"), (1, "LOW")]


def volume_for(provider, model, limits):
    """Return (requests_per_day, tier, confidence, evidence) for one model."""
    p = limits["providers"].get(provider)
    if not p:
        return None, "UNKNOWN", "UNKNOWN", "Provider not in limits.json."
    entry = (p.get("models") or {}).get(model) or p.get("all_models") or {}
    rpd = entry.get("rpd")
    conf = entry.get("rpd_confidence") or p.get("confidence", "UNKNOWN")
    bits = [p.get("caveat", "")]
    # Some providers state the cap as a condition rather than a number (OpenRouter's depends on lifetime
    # credits). Publish the figure a NEW account actually gets, and say what raises it.
    if rpd is None and p.get("free_models_combined"):
        tiers = p["free_models_combined"]
        baseline = min((v["rpd"] for v in tiers.values()), default=None)
        best = max((v["rpd"] for v in tiers.values()), default=None)
        rpd = baseline
        if baseline != best:
            bits.append("This is what a NEW account gets; it rises to %s/day once the conditions in "
                        "LIMITS.md are met. Shared across all free models, not per model." % best)
    if rpd is None:
        conf = "UNKNOWN"  # no number means no number, whatever the provider declares about other things
    # If the published figure belongs to a PAID plan, saying "DECLARED" next to it in a free-tier table
    # would repeat the exact mistake this repo calls out in its own README.
    if entry.get("rpd_is_paid_plan"):
        conf = "PAID-PLAN"
        bits.append("This requests-per-day figure is the provider's %s plan, not its free tier. The free "
                    "figure is not published anywhere public." % (p.get("rpd_plan") or "paid"))
    if entry.get("note"):
        bits.append(entry["note"])
    if p.get("binding_limit"):
        bits.append("Binding limit: " + p["binding_limit"])
    if p.get("scope"):
        bits.append("Limit applies per %s." % p["scope"].upper())
    if p.get("volatile"):
        bits.append("VOLATILE: this figure moved under us at least once.")
    tier = "UNKNOWN"
    if rpd:
        tier = next((name for floor, name in TIER if rpd >= floor), "LOW")
    return rpd, tier, conf, " ".join(b for b in bits if b).strip()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("results")
    ap.add_argument("--jury", default=None)
    ap.add_argument("--judges", default=str(HERE / "judges.json"),
                    help="the one description of the jury; its judges block is what data/models.json carries")
    ap.add_argument("--limits", default=str(HERE / "limits.json"))
    ap.add_argument("--out", default=".")
    ap.add_argument("--exclude", default="siliconflow",
                    help="providers to leave out of the quality ranking, comma-separated. Default excludes "
                         "siliconflow: every call returned 402, which is a fact about the account, not about them.")
    ap.add_argument("--date", required=True, help="the date the battery was run, YYYY-MM-DD")
    a = ap.parse_args()

    raw = json.loads(Path(a.results).read_text(encoding="utf-8"))
    limits = json.loads(Path(a.limits).read_text(encoding="utf-8"))
    jury = json.loads(Path(a.jury).read_text(encoding="utf-8")) if a.jury else {"verdicts": [], "key": {}, "lenses": []}
    # The judges are described ONCE, in bench/judges.json. The jury file may carry a copy for the
    # archive, but the copy is never what a page or data/models.json prints.
    judges = []
    if a.jury and Path(a.judges).exists():
        judges = json.loads(Path(a.judges).read_text(encoding="utf-8")).get("judges") or []
    excluded = {x.strip() for x in a.exclude.split(",") if x.strip()}
    out = Path(a.out)

    # Jury scores, indexed by the model they belong to once the blind key is applied. With more than
    # one judge, a lens score is the MEAN across judges - and the spread between them is kept, because
    # a lens the judges disagree about is a lens whose score should be read with suspicion.
    # bench/agreement.py reports that spread properly; this keeps just enough to flag it in the table.
    raw_scores = {}
    for v in jury.get("verdicts", []):
        model_key = jury.get("key", {}).get(v["id"])
        if model_key:
            raw_scores.setdefault(model_key, {}).setdefault(v["lens"], []).append(v["score"])
    by_model, jury_spread = {}, {}
    for model_key, per_lens in raw_scores.items():
        by_model[model_key] = {l: round(sum(v) / len(v), 1) for l, v in per_lens.items()}
        spread = {l: max(v) - min(v) for l, v in per_lens.items() if len(v) > 1}
        if spread:
            jury_spread[model_key] = spread
    n_judges = len({v.get("judge", "unnamed") for v in jury.get("verdicts", [])})
    lenses = jury.get("lenses", [])
    agent_lenses = [l for l in lenses if l != "sounds_human"]

    per = {}
    for row in raw["rows"]:
        k = (row["provider"], row["model"])
        d = per.setdefault(k, {"passed": 0, "of": 0, "seconds": [], "probes": {}, "http": []})
        d["passed"] += 1 if row["passed"] else 0
        d["of"] += 1
        d["seconds"].append(row["seconds"])
        d["http"].append(row["http"])
        d["probes"][row["probe"]] = {"passed": row["passed"], "note": row["note"], "kind": row["kind"],
                                     "attempts": row.get("attempts", 1),
                                     "attempts_passed": row.get("attempts_passed",
                                                                1 if row["passed"] else 0)}

    models, unreachable = [], []
    for (provider, model), d in sorted(per.items()):
        # A probe that never got an answer is not a quality failure. 503, 429, 402 and timeouts say the
        # endpoint was unavailable or the account was, and scoring those as zero would publish a lie.
        delivered = [h for h in d["http"] if h == 200]
        blocked = len(d["http"]) - len(delivered)
        # Below half the probes answered, whatever came back is not a measurement of the model. Ranking
        # a model on one probe out of four would put a number next to it that we did not earn.
        if len(delivered) * 2 < len(d["http"]):
            unreachable.append({"provider": provider, "model": model, "http": d["http"],
                                "answered": len(delivered), "of": len(d["http"]),
                                "why": next((v["note"] for v in d["probes"].values()
                                             if not v["passed"] and "HTTP" in v["note"]), "")[:120]})
            continue
        if provider in excluded:
            continue
        # Score on the probes that actually ran, not on the ones the network ate.
        answered = max(1, d["of"] - blocked)
        mech = d["passed"] / answered * 10
        # Every probe runs several times, so the mechanical half is a range, not a point. The low end
        # counts only probes that passed EVERY attempt; the high end counts those that passed at least
        # one. A model whose two ends are far apart is unstable, and that is worth seeing.
        always = sum(1 for v in d["probes"].values()
                     if v["attempts"] and v["attempts_passed"] == v["attempts"])
        ever = sum(1 for v in d["probes"].values() if v["attempts_passed"] > 0)
        mech_low, mech_high = always / answered * 10, min(ever, answered) / answered * 10
        stability = {p: "%d/%d" % (v["attempts_passed"], v["attempts"]) for p, v in d["probes"].items()}
        j = by_model.get("%s | %s" % (provider, model), {})
        scored = [j[l] for l in lenses if l in j]
        scored_agent = [j[l] for l in agent_lenses if l in j]
        judged = bool(scored)
        jury_mean = sum(scored) / len(scored) if scored else None
        jury_agent = sum(scored_agent) / len(scored_agent) if scored_agent else None
        rpd, tier, conf, evidence = volume_for(provider, model, limits)
        # A model whose paragraph failed the mechanical check never reached the jury. Giving it half a
        # score would put it on the same 0-10 scale as models that were judged, which is comparing two
        # different measurements. It gets its mechanical score out of 10 and is ranked separately.
        models.append({
            "provider": provider, "model": model,
            "quality": round(0.5 * mech + 0.5 * jury_mean, 1) if judged else round(mech, 1),
            "quality_for_agents": round(0.5 * mech + 0.5 * jury_agent, 1) if jury_agent is not None else round(mech, 1),
            "scale": "probes+jury" if judged else "probes only",
            "quality_low": round(0.5 * mech_low + 0.5 * jury_mean, 1) if judged else round(mech_low, 1),
            "quality_high": round(0.5 * mech_high + 0.5 * jury_mean, 1) if judged else round(mech_high, 1),
            "probe_stability": stability,
            "unstable": any(0 < v["attempts_passed"] < v["attempts"] for v in d["probes"].values()),
            "judged": judged,
            "probes_passed": d["passed"], "probes_total": d["of"], "probes_answered": d["of"] - blocked,
            "http_failures": blocked, "http_codes": d["http"],
            "jury": {l: j.get(l) for l in lenses},
            "jury_spread": jury_spread.get("%s | %s" % (provider, model), {}),
            "avg_seconds": round(sum(d["seconds"]) / len(d["seconds"]), 1),
            "requests_per_day": rpd, "volume_tier": tier, "volume_confidence": conf, "volume_evidence": evidence,
            "probe_detail": {p: v["note"] for p, v in d["probes"].items()},
        })
    models.sort(key=lambda m: (-m["quality"], m["avg_seconds"]))
    # With no jury file at all, every model is on the mechanical scale and that IS the main ranking.
    # With one, the main ranking is the judged models and the rest get their own section.
    have_jury = bool(lenses)
    judged_models = [m for m in models if m["judged"]] if have_jury else models
    mech_only = [m for m in models if not m["judged"]] if have_jury else []

    (out / "data").mkdir(parents=True, exist_ok=True)
    (out / "data" / "models.json").write_text(json.dumps({
        "measured_on": a.date, "language": raw.get("language"),
        "paragraph_attempts": raw.get("paragraph_attempts", 1),
        "judges": judges,
        "judges_source": "bench/judges.json" if judges else None,
        "jury_lenses": lenses,
        "scoring": "quality = 50% probes passed + 50% jury mean. quality_for_agents drops the sounds_human lens. "
                   "A model whose paragraph failed the mechanical check never reached the jury and is scored on "
                   "the mechanical half alone (judged=false).",
        "excluded_providers": sorted(excluded),
        "unreachable": unreachable,
        "models": models,
    }, indent=1, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")

    # probes_answered is in here on purpose: without it the CSV says "1/4" where RESULTS.md says "1/2",
    # because probes that got no answer are excluded from the score but still counted in the total.
    cols = ["provider", "model", "quality", "scale", "quality_for_agents", "judged",
            "probes_passed", "probes_answered", "probes_total", "http_failures",
            "avg_seconds", "requests_per_day", "volume_tier", "volume_confidence"]
    with open(out / "data" / "models.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(models)

    def table(rows, quality_key="quality"):
        jury_head = " / ".join(l.replace("_", " ") for l in lenses) if lenses else "Jury"
        head = ("| # | Model | Provider | Quality | Probes | %s | Req/day | Evidence | Speed |\n"
                "|---|---|---|---|---|---|---|---|---|\n" % jury_head)
        body = ""
        for i, m in enumerate(rows, 1):
            jury_cell = " / ".join(str(m["jury"].get(l)) if m["jury"].get(l) is not None else "-" for l in lenses) if m["judged"] else "not judged"
            rpd = "{:,}".format(m["requests_per_day"]) if m["requests_per_day"] else "?"
            probes = "%d/%d" % (m["probes_passed"], m["probes_answered"])
            if m["http_failures"]:
                probes += " ⚠"  # some probes never got an answer; see the footnote
            # A single number claims a confidence we did not earn. Show the range whenever the model
            # did not return the same verdict on every attempt.
            score = "**%s**" % m[quality_key]
            if m.get("unstable") and m.get("quality_low") is not None:
                score += "<br><sub>%s-%s</sub>" % (m["quality_low"], m["quality_high"])
            body += "| %d | `%s` | %s | %s | %s | %s | %s | %s | %.1f s |\n" % (
                i, m["model"], m["provider"], score, probes,
                jury_cell, rpd, m["volume_confidence"], m["avg_seconds"])
        note = ""
        if any(m.get("unstable") for m in rows):
            note += ("\nThe smaller number under a score is the RANGE across repeated attempts: the low end "
                     "counts only probes that passed every time, the high end those that passed at least "
                     "once. A score with no range under it was identical on every attempt. **%d of %d "
                     "models here were not.**\n"
                     % (sum(1 for m in rows if m.get("unstable")), len(rows)))
        if any(m["http_failures"] for m in rows):
            note = ("\n⚠ = one or more probes never received an answer (503, 429, 402 or a timeout). Those "
                    "probes are excluded from the score rather than counted as failures, because an "
                    "unavailable endpoint is not a bad model. The `Probes` column shows passes out of "
                    "probes actually answered; the HTTP codes are in `data/models.json`.\n")
        return head + body + note

    known = [m for m in judged_models if m["requests_per_day"]]
    lines = [
        "# Full results",
        "",
        "Battery run on **%s**, probes in **%s**. %s"
        % (a.date, raw.get("language"),
           ("The paragraph probe was run %d times per model and the verdict is the majority of those."
            % raw.get("paragraph_attempts", 1)) if raw.get("paragraph_attempts", 1) > 1
           else "Every probe was run once."),
        "Judges: %s. Generated by `bench/rank_language.py` - do not edit by hand."
        % (", ".join("`%s` (%s, via %s)" % (j.get("name"), j.get("family", "family not declared"), j.get("via", "?"))
                     for j in judges) or "none"),
        "",
        ("How much the judges agreed: [agreement.md](results/%s/agreement.md). Read it before trusting "
         "a jury column - on our first run the two judges correlated at 0.93 on language correctness "
         "and at -0.07 on whether a text sounds human, which are very different things to know."
         % a.date) if n_judges > 1 else
        "Only one judge ran, so there is no agreement to report and the jury half rests on a single "
        "model's opinion. Run `bench/judge.py --api` with a second judge from another family.",
        "",
        "`Evidence` is how we know the requests-per-day figure: MEASURED by us, DECLARED by the provider, "
        "PAID-PLAN when the only published number belongs to a paid tier rather than the free one, or "
        "UNKNOWN when nobody publishes it. See [LIMITS.md](LIMITS.md) for the per-provider detail and the "
        "caveats, which matter more than the numbers.",
        "",
        ("## 1. Quality (models that reached the jury)" if have_jury
         else "## 1. Mechanical score (no jury was run)"), "",
        ("Only models whose paragraph passed the mechanical check are here: they are the ones with both "
         "halves of the score. The rest are in section 5, on a different scale, because a mechanical "
         "score and a mechanical-plus-jury score are two different measurements and averaging them into "
         "one column would be a quiet lie."
         if have_jury else
         "No jury file was supplied, so every score here is the mechanical half alone, out of 10. These "
         "numbers are reproducible with no model in the loop at all - which is their point - but they "
         "say nothing about whether the prose is any good."), "",
        table(judged_models),
        "", "## 2. Quality x volume (only models whose daily limit is known)", "", table(known),
        "", "## 3. Quality for agent work (drops the 'sounds human' lens)",
        "",
        "For extraction, classification and tool calls, prose voice is irrelevant and correctness is not. "
        "This ranking is the one to use when the model is a component, not a writer.",
        "", table(sorted(judged_models, key=lambda m: (-m["quality_for_agents"], m["avg_seconds"])), "quality_for_agents"),
        "", "## 4. What each model actually did on each probe", "",
        "| Model | " + " | ".join(sorted({p for m in models for p in m["probe_detail"]})) + " |",
        "|---|" + "---|" * len(sorted({p for m in models for p in m["probe_detail"]})),
    ]
    probes = sorted({p for m in models for p in m["probe_detail"]})
    for m in models:
        cells = [" ".join(m["probe_detail"].get(p, "-").replace("|", "/").split())[:70] for p in probes]
        lines.append("| `%s` | %s |" % (m["model"], " | ".join(cells)))
    if mech_only:
        lines += ["", "## 5. Mechanical score only (never reached the jury)", "",
                  "These models answered, but their paragraph failed the mechanical check, so there was",
                  "nothing to judge. The number below is the mechanical score out of 10 and is NOT",
                  "comparable with the tables above, which carry a jury half as well. Ranking them",
                  "together would be averaging two different measurements into one column.", "",
                  "| Model | Provider | Probes | Mechanical /10 | Why no paragraph | Speed |",
                  "|---|---|---|---|---|---|"]
        for m in sorted(mech_only, key=lambda x: -x["quality"]):
            why = " ".join((m["probe_detail"].get("D") or "-").replace("|", "/").split())[:60]
            lines.append("| `%s` | %s | %d/%d | **%s** | %s | %.1f s |"
                         % (m["model"], m["provider"], m["probes_passed"], m["probes_answered"],
                            m["quality"], why, m["avg_seconds"]))

    if unreachable or excluded:
        lines += ["", "## Not ranked", "",
                  "Scoring a model that never answered would be publishing a lie about it. These are listed "
                  "with what happened instead.", ""]
    if unreachable:
        lines += ["A model is only ranked if at least half its probes came back. Below that, whatever "
                  "answered is not a measurement of the model.", "",
                  "| Model | Provider | Answered | HTTP codes | What happened |", "|---|---|---|---|---|"]
        for u in unreachable:
            # Provider error bodies are JSON with newlines in them; a raw paste breaks the table.
            why = " ".join(u["why"].replace("|", "/").split())[:110]
            lines.append("| `%s` | %s | %d/%d | %s | %s |" % (u["model"], u["provider"],
                                                              u.get("answered", 0), u.get("of", 0),
                                                              ", ".join(str(h) for h in u["http"]), why))
        lines += ["", "A `0` code is a timeout on our side. `402` is the account's balance, not the "
                      "provider's capability. `429` and `503` mean the endpoint was rate-limiting or "
                      "overloaded at that moment, which is worth knowing about a free tier, but is not a "
                      "measurement of the model.", ""]
    if excluded:
        lines += ["- Excluded by request: " + ", ".join(sorted(excluded)) + ". See LIMITS.md."]
    (out / "RESULTS.md").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")

    # LIMITS.md is written by bench/rank.py, whole, from bench/limits.json - not here. This file used
    # to write it too, which gave one page two writers and a stale header; see rank.py.

    judged = sum(1 for m in models if m["judged"])
    print("wrote RESULTS.md, data/models.json, data/models.csv")
    print("  %d models ranked (%d judged, %d mechanical-only), %d with a known daily limit"
          % (len(models), judged, len(models) - judged, len(known)))
    if unreachable:
        print("  %d never answered, not ranked: %s"
              % (len(unreachable), ", ".join(u["model"] for u in unreachable)))
    partial = [m for m in models if m["http_failures"]]
    if partial:
        print("  %d answered only partially, scored on what came back: %s"
              % (len(partial), ", ".join("%s (%d/%d)" % (m["model"], m["probes_answered"], m["probes_total"])
                                         for m in partial)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
