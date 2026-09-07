# Credits

The quality scores in this repo are **not ours**. We import them, and they belong to the people who
built the benchmarks. Attribution is not a formality here: the whole argument of this list is that
quality comes from independent sources rather than from whoever publishes the ranking.

## Benchmark scores

| Source | What it provides | How we get it |
|---|---|---|
| **[Artificial Analysis](https://artificialanalysis.ai)** | `intelligence_index`, `coding_index`, `agentic_index` | republished per model on OpenRouter's public models endpoint |
| **[Design Arena](https://design-arena.ai)** | ELO, win rate and rank per category, from head-to-head comparisons | same endpoint |

Both are fetched from `https://openrouter.ai/api/v1/models`, which requires no key and no scraping.
We do not modify, recompute or re-weight the scores. Every fetch is dated in
[`data/scores.json`](data/scores.json), and a model with no published score is marked UNSCORED rather
than estimated.

If you maintain either benchmark and want the attribution changed, or want us to stop republishing
your numbers, open an issue and we will act on it.

## Provider catalogue

The list of free providers we cross-check against was informed by
**[OmniRoute](https://github.com/diegosouzapw/OmniRoute)** (MIT), which maintains the largest
catalogue of providers we found. We use it as a map of what exists, not as a source of facts: every quota, auth type and
privacy claim in this repo is either measured by us or read from the provider's own terms, with the
date beside it.

Two things we deliberately did **not** take from it: their `hasFree` boolean, which covers both a
recurring quota and credits that run out, and their headline provider count, which contains
duplicates.

## The Romanian language benchmark

That one **is** ours, and it is the only thing in this repo we ran ourselves. Method, prompts, raw
answers and judge scores are all published: [METHOD.md](METHOD.md), [results/](results/).

Probe design was informed by the mechanically-verifiable style of
**[IFEval](https://huggingface.co/datasets/google/IFEval)** (Apache 2.0): every check decided by code,
never by opinion.
