#!/usr/bin/env python3
"""Import official benchmark scores for the models our free providers serve. No API key needed.

    python bench/scores.py --out data/scores.json --date 2026-09-06

WHY WE IMPORT INSTEAD OF RUNNING OUR OWN

We used to run a benchmark of our own. It does not scale: every time a new free provider appears - and
they appear weekly - we would have to run the whole battery against it before we could say anything.
Worse, a benchmark run by the same people who publish the ranking is exactly the kind of thing a reader
should distrust.

So quality comes from OFFICIAL benchmarks, and we measure only what nobody else can tell you: whether
the endpoint is alive today, what the real quota is, whether it needs a key, and what it costs you in
things that are not money.

The division of labour, stated once:

    imported   what the MODEL can do        <- Artificial Analysis, Design Arena
    measured   what the PROVIDER gives you  <- quota, uptime, latency, auth, privacy

This also means a new provider costs nothing to rate: if it serves `qwen3.8-27b`, it inherits that
model's published scores the moment we add its endpoint.

SOURCE

Both come from OpenRouter's public models endpoint, which republishes them per model. No key, no
scraping, no terms to argue about. Attribution is in CREDITS.md, and every score carries the date we
fetched it, because a score with no date is a rumour.
"""
import argparse, json, re, sys, urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
SOURCE = "https://openrouter.ai/api/v1/models"
UA = {"User-Agent": "free-llm-benchmark/1.0 (+https://github.com/i-voryStudio)"}


def normalise(model_id):
    """Strip the things that differ between providers serving the SAME model.

    Cloudflare calls it `@cf/openai/gpt-oss-120b`, Groq calls it `openai/gpt-oss-120b`, Ollama calls it
    `gpt-oss:120b`, Cerebras just `gpt-oss-120b`. Same weights, four names. Without this, three quarters
    of our rows would show no score for models that are very well measured elsewhere.
    """
    s = model_id.lower()
    s = re.sub(r"^@cf/", "", s)
    s = re.sub(r":free$|:batch$|:extended$|:thinking$|-latest$", "", s)
    s = s.split("/")[-1]
    s = s.replace(":", "-")                 # ollama's gpt-oss:120b -> gpt-oss-120b
    # OVHcloud writes the version with an underscore: Meta-Llama-3_3-70B-Instruct. The underscore is a
    # decimal point, and only between two digits - anywhere else it is just a separator and gets dropped
    # with the rest of the punctuation below.
    s = re.sub(r"(?<=\d)_(?=\d)", ".", s)
    # Serving suffixes describe HOW a provider runs the weights, not WHICH weights. Cloudflare's
    # `llama-3.3-70b-instruct-fp8-fast` and OpenRouter's `llama-3.3-70b-instruct` are the same model,
    # and leaving these on cost us three published scores that were sitting right there.
    # A vendor prefix written with a hyphen instead of a slash. OVHcloud serves
    # `Meta-Llama-3_3-70B-Instruct`; the benchmark knows it as `meta-llama/llama-3.3-70b-instruct`, whose
    # last path segment is `llama-3.3-70b-instruct`. Only organisation names are listed, never a model
    # family, so nothing here can merge two different models.
    for vendor in ("meta-", "mistralai-", "nvidia-", "openai-", "google-",
                   "deepseek-ai-", "moonshotai-"):
        if s.startswith(vendor) and len(s) > len(vendor) + 2:
            s = s[len(vendor):]
            break
    # An instruct build carrying its release date: `mistral-small-3.2-24b-instruct-2506`. The date is
    # dropped ONLY when `-instruct` sits in front of it, because a bare trailing number can be the model
    # version itself - `mistral-small-2603` is a different model, not a dated build of `mistral-small`.
    s = re.sub(r"-instruct-\d{4}$", "-instruct", s)
    # Serving suffixes describe HOW a provider runs the weights, not WHICH weights, and they stack:
    # `Qwen3.6-27B-int4-AutoRound` is two of them on one model. Strip until nothing changes, or the
    # outer one hides the inner one and the score stays lost.
    for _ in range(6):
        before = s
        for suffix in ("-fp8-fast", "-fp8", "-fp16", "-bf16", "-awq", "-gptq", "-int8", "-int4",
                       "-autoround", "-instruct", "-it", "-chat", "-hf", "-fast", "-turbo-instruct"):
            if s.endswith(suffix) and len(s) > len(suffix) + 2:
                s = s[: -len(suffix)]
        if s == before:
            break
    return re.sub(r"[^a-z0-9.]", "", s)


def same_model(a, b):
    """True when two normalised ids name the same weights.

    Exact match, or one is the other plus a parameter-shape tail the provider spells out and the
    benchmark does not (`nemotron-3.5-lightning-30b-a3b` against `nemotron-3.5-lightning`). The tail
    must look like a size or MoE shape - never arbitrary extra words, because attaching one model's
    reputation to another model's endpoint is the worst error this file could make.
    """
    if a == b:
        return True
    long, short = (a, b) if len(a) > len(b) else (b, a)
    if not long.startswith(short):
        return False
    tail = long[len(short):]
    return bool(re.fullmatch(r"[0-9]{1,3}[bm](a[0-9]{1,3}b)?", tail))


def build_index(models):
    idx = {}
    for m in models:
        b = m.get("benchmarks") or {}
        aa = b.get("artificial_analysis") or {}
        da = b.get("design_arena") or []
        if not aa and not da:
            continue
        entry = {"source_id": m["id"], "artificial_analysis": {k: v for k, v in aa.items() if v is not None}}
        if da:
            # Design Arena publishes an ELO per category. Keep the overall model arena entry and the
            # code category, which is the one that matters for "can I get work done with this".
            best = {}
            for row in da:
                if not isinstance(row, dict):
                    continue
                cat = row.get("category")
                if cat in ("codecategories", "website", "gamedev"):
                    best[cat] = {"elo": row.get("elo"), "win_rate": row.get("win_rate"), "rank": row.get("rank")}
            if best:
                entry["design_arena"] = best
        key = normalise(m["id"])
        # A model can appear several times (:batch, :extended). Keep the richest entry.
        if key not in idx or len(json.dumps(entry)) > len(json.dumps(idx[key])):
            idx[key] = entry
    return idx


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default="data/scores.json")
    ap.add_argument("--providers", default=str(HERE / "providers.json"))
    ap.add_argument("--date", required=True, help="YYYY-MM-DD, passed in so the output is reproducible")
    a = ap.parse_args()

    req = urllib.request.Request(SOURCE, headers=UA)
    with urllib.request.urlopen(req, timeout=90) as f:
        payload = json.load(f)
    models = payload.get("data", [])
    if not models:
        print("the source returned no models - refusing to overwrite good data with an empty answer")
        return 2
    idx = build_index(models)
    print("read %d models from the public catalogue, %d carry official scores" % (len(models), len(idx)))

    ours = json.loads(Path(a.providers).read_text(encoding="utf-8"))["providers"]
    rows, missing = [], []
    for p in ours:
        for m in p["models"]:
            key = normalise(m["id"])
            hit = idx.get(key)
            if not hit:
                # Second pass: same weights under a different spelling. Only accepted when exactly one
                # candidate matches - an ambiguous match is no match, and is reported as UNSCORED.
                cands = [k for k in idx if same_model(key, k)]
                hit = idx[cands[0]] if len(cands) == 1 else None
            if hit:
                rows.append({"provider": p["name"], "model": m["id"], "matched_as": hit["source_id"],
                             **{k: v for k, v in hit.items() if k != "source_id"}})
            else:
                missing.append({"provider": p["name"], "model": m["id"]})

    out = {
        "fetched_on": a.date,
        "source": SOURCE,
        "source_note": "Scores are republished by OpenRouter from Artificial Analysis and Design Arena. "
                       "We do not run them ourselves and do not modify them. See CREDITS.md.",
        "benchmarks": {
            "artificial_analysis": "intelligence_index, coding_index and agentic_index, 0-100. Higher is better.",
            "design_arena": "ELO, win rate and rank per category, from head-to-head comparisons.",
        },
        "matched": rows,
        "unmatched": missing,
    }
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")

    total = len(rows) + len(missing)
    print("matched %d of %d of our models (%d%%)" % (len(rows), total, round(100.0 * len(rows) / max(1, total))))
    if missing:
        print("\nno official score published for these - the row says UNSCORED, it does not guess:")
        for m in missing:
            print("  %-12s %s" % (m["provider"], m["model"]))
    print("\nwrote %s" % a.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
