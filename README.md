# Free LLM APIs, Ranked by What You Can Actually Get Done

**Every other list ranks free LLM APIs by rate limit. This one ranks them by quality times volume —
because a brilliant model you may call 20 times a day is worth less than a decent one you may call
2,400 times.**

Measured on **2026-09-06**. Quality is imported from official benchmarks; everything else we measure ourselves.

## The ranking

| # | Model | Provider | Value | Auth | Coding | Req/day | Note |
|---|---|---|---|---|---|---|---|
| 1 | `qwen-3.8-27b` | cerebras | **230.2** | key | 68.1 | 2,400 | MEASURED |
| 2 | `qwen/qwen3.8-27b` | groq | **204.3** | key | 68.1 | 1,000 | PAID-PLAN |
| 3 | `qwen/qwen3.6-27b` | groq | **161.1** | key | 53.7 | 1,000 | PAID-PLAN |
| 4 | `gemma-4-31b` | cerebras | **146.7** | key | 43.4 | 2,400 | MEASURED |
| 5 | `gemini-3.5-flash-lite` | google | **133.1** | key | 49.3 | 500 | **trains on your prompts** |
| 6 | `gpt-oss-120b` | cerebras | **102.8** | key | 30.4 | 2,400 | MEASURED |
| 7 | `gemini-3.8-flash` | google | **100.9** | key | 76.3 | 20 | **trains on your prompts** |
| 8 | `minimax/minimax-m3:free` | openrouter | **100.1** | key | 58.6 | 50 | DECLARED |
| 9 | `openai/gpt-oss-120b` | groq | **91.2** | key | 30.4 | 1,000 | PAID-PLAN |
| 10 | `minimax/minimax-m2.7:free` | openrouter | **89.8** | key | 52.6 | 50 | DECLARED |

**Read the first two rows against row 7.** `gemini-3.8-flash` has the best coding score in the whole list — **76.3** —
and sits at number 7, because Google gives you **20 requests a day**. The model at number 1 scores
lower and wins anyway. That is the entire argument for ranking this way.

Full tables, all five filters: **[RESULTS.md](RESULTS.md)** · machine-readable:
[`data/ranking.json`](data/ranking.json), [`data/ranking.csv`](data/ranking.csv)

---

## The five filters

| | Filter | Where it comes from |
|---|---|---|
| **1** | **Value = quality x volume** | the headline ranking |
| 2 | Quality | **imported** from official benchmarks, never our own |
| 3 | Volume | measured by us, or declared with a source |
| 4 | Needs a key, or not | no-key endpoints get a declared bonus |
| 5 | **What it costs you that is not money** | read from the provider's own terms |

### Why quality is imported and everything else is measured

We used to run our own quality benchmark. It does not scale: free providers appear weekly, and each
would have to go through a full battery before it could be listed at all. Worse, a benchmark run by
whoever publishes the ranking is exactly what a careful reader should distrust.

    imported   what the MODEL can do        <- Artificial Analysis, Design Arena
    measured   what the PROVIDER gives you  <- quota, uptime, auth, privacy

So a new provider costs nothing to rate. Serve `qwen3.8-27b` and it inherits that model's published
scores the day we add the endpoint. That is what makes this list able to keep up.

### Filter 5, which nobody else publishes

Free often means you are paying with your prompts. Google's own terms, quoted, not paraphrased:

> When you use Unpaid Services... Google uses the content you submit... to provide, improve, and
> develop Google products and services and machine learning technologies

> human reviewers may read, annotate, and process your API input and output

And the one that should stop any European reader cold:

> **You may use only Paid Services when making API Clients available to users in the European
> Economic Area, Switzerland, or the United Kingdom.**

The free Gemini tier is contractually unusable for an app with EU users. No other free-LLM list carries
this. Most rows in filter 5 say `UNKNOWN`, because nobody has read those terms yet — and `UNKNOWN` is
the honest default: inventing a "no" would be the most damaging wrong answer this repo could publish.

---

## What we measure, and what we refuse to guess

- **A row needs both halves to be ranked**: an official score AND a known quota. 12 endpoints are
  ranked; the rest are listed separately with what is missing. Half a fact is not a rank.
- **Every row carries `measured_at`.** Free tiers die in months, not years — the catalogue we cross-check
  against lost six providers between March and August 2026. A number with no date is a rumour.
- **A quota in tokens without the model it was measured on is a false number**, because some providers
  apply a per-model multiplier. We publish the model or nothing.
- **Quotas in proprietary units** ("100,000 ANY Tokens", "10 Neutrinos") are quoted as text, never
  converted into a number that would look comparable.

## Zero of the endpoints here work without a key

That is a gap, not a feature, and it is the next thing being added — no-key endpoints exist. See
[IMPROVEMENTS.md](IMPROVEMENTS.md).

---

## Bonus: how these models write a language that is not English

Before this became a ranking of endpoints, we ran our own benchmark of how well free models write
**Romanian** — four machine-checked probes and a blind jury of two judges from different model families.
It is no longer the headline, but it is still the only measurement anywhere of these models on a small
language, and the finding stands: they can all do arithmetic, and almost none of them can write.

The two judges correlated at **0.93** on whether the Romanian was correct and at **-0.07** on whether it
sounded human — so we publish that disagreement too.

Full run: [results/2026-09-06/](results/2026-09-06/) · method: [METHOD.md](METHOD.md) · judge
agreement: [agreement.md](results/2026-09-06/agreement.md)

---

## Run it yourself

```bash
python bench/scores.py --out data/scores.json --date $(date -u +%F)   # import official scores
python bench/rank.py --date $(date -u +%F) --out .                     # rebuild every table
```

No API key needed for either: the scores come from a public endpoint.

## Contributing

The most valuable pull request you can send is **reading one provider's terms and filling in filter 5**,
or **correcting a quota with its source**. Turning a wrong number into an honest `UNKNOWN` counts as a
real contribution here. See [CONTRIBUTING.md](CONTRIBUTING.md) and [SECURITY.md](SECURITY.md).

## Licence

Code (`bench/`) under **MIT**. Data and tables under
**[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)**. Benchmark scores belong to their authors
and are attributed in [CREDITS.md](CREDITS.md).

Built by **[i-vory Studio](https://i-vory.studio)**.
