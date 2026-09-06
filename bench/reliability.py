#!/usr/bin/env python3
"""Measure how often a provider actually answers, and flag the reasoning trap.

    python bench/reliability.py --out data/reliability.json --date 2026-09-06

TWO THINGS THAT NO RATE LIMIT TELLS YOU

**1. A published quota is not availability.** A provider can advertise 2,400 requests a day and still
refuse a third of them at the moment you need them. We count what actually came back across every call
we have made: 200s, 429s, 503s and timeouts, per provider.

**2. The reasoning trap, which is worse because it looks like success.** Models that reason will spend
the whole token budget thinking and return an EMPTY message - with HTTP 200. Nothing in the status code
says anything went wrong. You get a bill (or a spent quota) and no text.

Every provider takes a different switch to turn that off, and some take none at all:

    reasoning_effort: low                       OpenAI-style (gpt-oss on Groq, Cerebras, Ollama)
    chat_template_kwargs: {enable_thinking:false}   NVIDIA nemotron
    enable_thinking: false                      Alibaba Qwen
    thinking: {type: disabled}                  z.ai GLM
    (none)                                      you cannot turn it off, so budget for it

MEASURED, 2026-09-06: four of the five empty responses in our own run came from reasoning-capable
models on providers where we had NOT set a switch. The fifth had a switch that the provider ignored.
Meanwhile twelve models in our own providers.json already carry a switch - we had learned this lesson
and never published it, which is exactly the kind of knowledge a list like this should be carrying.

This feeds the ranking as a multiplier: a provider that answers 90% of the time is worth 90% of its
paper quota. Ranking on advertised numbers alone rewards whoever advertises hardest.
"""
import argparse, json, sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent

# The switch each provider family accepts, so a reader can copy it. Measured by using it, not guessed.
THINKING_SWITCH = {
    "reasoning_effort": "gpt-oss family on Groq, Cerebras, Ollama and OpenRouter",
    "chat_template_kwargs.enable_thinking": "NVIDIA nemotron, on NVIDIA and via OpenRouter",
    "enable_thinking": "Alibaba Qwen on DashScope",
    "thinking.type": "z.ai GLM",
}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default="data/reliability.json")
    ap.add_argument("--date", required=True)
    a = ap.parse_args()

    runs = sorted((ROOT / "results").glob("*/raw.json"))
    if not runs:
        print("no runs in results/ to measure")
        return 2

    per = defaultdict(lambda: {"calls": 0, "ok": 0, "empty_200": 0, "rate_limited": 0,
                               "overloaded": 0, "timeout": 0, "other": 0})
    traps, switched = [], []
    providers = json.loads((HERE / "providers.json").read_text(encoding="utf-8"))["providers"]
    has_switch = {(p["name"], m["id"]): m.get("extra_body")
                  for p in providers for m in p["models"] if m.get("extra_body")}

    for run in runs:
        raw = json.loads(run.read_text(encoding="utf-8"))
        for r in raw["rows"]:
            d = per[r["provider"]]
            d["calls"] += 1
            code, text = r["http"], (r.get("text") or "").strip()
            if code == 200 and text:
                d["ok"] += 1
            elif code == 200:
                # The dangerous case: a success that carries nothing.
                d["empty_200"] += 1
                key = (r["provider"], r["model"])
                traps.append({"provider": r["provider"], "model": r["model"], "probe": r["probe"],
                              "had_switch": bool(has_switch.get(key)),
                              "switch": has_switch.get(key),
                              "run": run.parent.name})
            elif code == 429:
                d["rate_limited"] += 1
            elif code == 503:
                d["overloaded"] += 1
            elif code == 0:
                d["timeout"] += 1
            else:
                d["other"] += 1

    for (prov, model), switch in sorted(has_switch.items()):
        switched.append({"provider": prov, "model": model, "switch": switch})

    rows = []
    for name, d in sorted(per.items()):
        answered = d["ok"] / d["calls"] if d["calls"] else 0
        rows.append({
            "provider": name, **d,
            "answered_rate": round(answered, 3),
            "note": ("answers reliably" if answered >= 0.95 else
                     "occasionally refuses or returns nothing" if answered >= 0.85 else
                     "unreliable in our measurements - see the counts"),
        })
    rows.sort(key=lambda r: -r["answered_rate"])

    out = {
        "measured_at": a.date,
        "runs_included": [r.parent.name for r in runs],
        "how": "Every call in every published run, counted by outcome. answered_rate is 200-with-text "
               "over total calls. This is one sample on the calling accounts, not an uptime guarantee - a small "
               "sample from one afternoon says less than a month of daily probes will.",
        "reasoning_trap": {
            "what": "A reasoning model can spend its whole token budget thinking and return an empty "
                    "message with HTTP 200. The status code says success. There is no text.",
            "switches": THINKING_SWITCH,
            "observed": traps,
            "already_switched_off_by_us": switched,
        },
        "providers": rows,
    }
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n",
                           encoding="utf-8", newline="\n")

    print("measured %d calls across %d run(s)" % (sum(d["calls"] for d in per.values()), len(runs)))
    print("%-12s %6s %6s %8s %6s %6s %8s  %s"
          % ("provider", "calls", "ok", "empty200", "429", "503", "timeout", "rate"))
    for r in rows:
        print("%-12s %6d %6d %8d %6d %6d %8d  %.0f%%"
              % (r["provider"], r["calls"], r["ok"], r["empty_200"], r["rate_limited"],
                 r["overloaded"], r["timeout"], 100 * r["answered_rate"]))
    no_switch = [t for t in traps if not t["had_switch"]]
    print("\nreasoning trap: %d empty 200s, %d of them on models with NO thinking switch set"
          % (len(traps), len(no_switch)))
    for t in no_switch:
        print("  %-12s %s" % (t["provider"], t["model"]))
    print("\nwrote %s" % a.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
