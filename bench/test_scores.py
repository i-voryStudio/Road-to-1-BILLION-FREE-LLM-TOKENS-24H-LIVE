#!/usr/bin/env python3
"""Calibrate the model-matching rules in BOTH directions. Exit 0 clean, 1 miscalibrated.

    python bench/test_scores.py

`scores.py` decides which published benchmark score belongs to which endpoint. Its own docstring names
the failure it must never commit: "attaching one model's reputation to another model's endpoint is the
worst error this file could make". That is not a hypothetical - the size-tail rule shipped on
2026-09-07 answered TRUE for `kimi-k3` against `kimi-k3-8b`, which are a 2.8-trillion-parameter model
and an 8-billion-parameter one.

So the rule gets a test with the wrong answers written down, not just the right ones. Half of this file
is pairs that MUST NOT match.
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from scores import normalise, same_model


def match(a, b):
    return same_model(normalise(a), normalise(b))


# The same weights under two providers' spellings. These MUST match, or a well-measured model shows
# UNSCORED and the ranking loses a row it had every right to.
MUST_MATCH = [
    ("@cf/openai/gpt-oss-120b", "openai/gpt-oss-120b", "cloudflare's @cf/ prefix"),
    ("gpt-oss:120b", "gpt-oss-120b", "ollama's colon"),
    ("@cf/meta/llama-3.3-70b-instruct-fp8-fast", "meta-llama/llama-3.3-70b-instruct", "fp8-fast serving suffix"),
    ("Meta-Llama-3_3-70B-Instruct", "meta-llama/llama-3.3-70b-instruct", "OVHcloud's underscore version"),
    ("Lorbus/Qwen3.6-27B-int4-AutoRound", "qwen/qwen3.6-27b", "stacked quantisation suffixes"),
    ("Mistral-Small-3.2-24B-Instruct-2506", "mistralai/mistral-small-3.2-24b", "instruct build with a date"),
    ("minimax/minimax-m3:free", "minimax/minimax-m3", "the :free tier suffix"),
    ("gemma-4-31b-it", "google/gemma-4-31b", "the -it instruction-tuned suffix"),
    ("qwen-3.8-27b", "qwen/qwen3.8-27b", "cerebras writes the family with a hyphen"),
]

# Different weights. Every one of these MUST NOT match, and each is a real shape seen in a live
# catalogue. A false match here publishes a big model's score against a small model's endpoint.
MUST_NOT_MATCH = [
    ("kimi-k3", "kimi-k3-8b", "2.8T MoE against an 8B distill - the case that shipped broken"),
    ("glm-5.3", "glm-5.3-9b", "flagship against the 9B"),
    ("minimax-m3", "minimax-m3-8b", "same family, different weights"),
    ("gpt-oss-120b", "gpt-oss-20b", "120B against 20B"),
    ("gemma-4-31b", "gemma-4-26b-a4b", "31B dense against a 26B MoE"),
    ("qwen3.8-27b", "qwen3.6-27b", "same size, different generation"),
    ("mistral-small-2603", "mistral-small-3.2-24b", "a dated model id is not a dated build"),
    ("llama-3.3-70b", "llama-3.1-70b", "same size, different version"),
    ("nemotron-3-super-120b-a12b", "nemotron-3-ultra-550b-a55b", "super against ultra"),
    ("qwen3.5-397b-a17b", "qwen3.5-9b", "397B against 9B"),
]


def main():
    bad = 0
    print("pairs that MUST match (same weights, two spellings):")
    for a, b, why in MUST_MATCH:
        ok = match(a, b)
        print("  %-4s %-42s %-34s %s" % ("ok" if ok else "MISS", a[:42], b[:34], why))
        bad += 0 if ok else 1

    print("\npairs that MUST NOT match (different weights):")
    for a, b, why in MUST_NOT_MATCH:
        ok = not match(a, b)
        print("  %-4s %-42s %-34s %s" % ("ok" if ok else "FALSE", a[:42], b[:34], why))
        bad += 0 if ok else 1

    total = len(MUST_MATCH) + len(MUST_NOT_MATCH)
    print("\n%d of %d pairs behaved as required" % (total - bad, total))
    if bad:
        print("MISCALIBRATED. A false match publishes one model's reputation on another model's endpoint.")
        return 1
    print("CLEAN - the matcher joins what is the same and refuses what is not.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
