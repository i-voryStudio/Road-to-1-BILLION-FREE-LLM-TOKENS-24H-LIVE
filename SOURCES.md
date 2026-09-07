# Sources

Everything this repo stands on, with what we took from each and what we deliberately did not. If a
number here has no source, it is a bug — tell us.

## Benchmark scores (imported, not ours)

| Source | What we take | How |
|---|---|---|
| **[Artificial Analysis](https://artificialanalysis.ai)** | `intelligence_index`, `coding_index`, `agentic_index` | republished per model on OpenRouter's public models endpoint |
| **[Design Arena](https://design-arena.ai)** | ELO, win rate and rank per category | same endpoint |
| **[OpenRouter](https://openrouter.ai)** `/api/v1/models` | the live model catalogue, and the two score sets above | public, no key, no scraping |

We do not modify, recompute or re-weight any score. Every fetch is dated in
[`data/scores.json`](data/scores.json). A model with no published score is marked UNSCORED, never
estimated.

## The provider catalogue we cross-check against

**[OmniRoute](https://github.com/diegosouzapw/OmniRoute)** (MIT, 62k stars, 351 providers) is the most
complete map of free LLM endpoints we found. We read its full provider catalogue — `noauth.ts`,
`apikey/gateways.ts`, `inference-hosts.ts`, `regional.ts`, `frontier-labs.ts`, `specialty-media.ts`,
`enterprise-cloud.ts` — and used it to find what we were missing.

**As a map, not as a source of facts.** Every quota, auth type and privacy claim in this repo is either
measured by us or read from the provider's own terms, with the date beside it. What we did not take,
and why:

- **Their headline count of 352 providers.** It contains measured duplicates: `naga-ai` and `naga-ac`
  are the same host, `sparkdesk` is an alias over `iflytek`, `doubao` takes its key from the same
  console as `volcengine`.
- **Their `hasFree: true` boolean.** It covers both a recurring quota and credits that run out — the
  same flag sits on a provider giving 1M requests a month and one giving a single grant.
- **Classification by absence.** In their frontier-labs file, 9 of 11 providers read as paid because a
  flag is missing, not because anything says so. Absence is not evidence.
- **Providers reached by reverse-engineered protocols or a browser session**, and anything requiring
  your personal account cookie.
- **Providers whose own terms forbid the use we would be publishing** — reselling access, commercial
  traffic, or redistribution.

Their `docs/OMNIROUTE_QUOTA_TELEMETRY.md` also sharpened our own vocabulary, and two of its rules are
now ours: *unknown is not exhausted*, and *response headers are read only through an explicit per-provider
mapping — generic header names are never assumed globally*.

## The other free-LLM lists, all of them read before we wrote ours

We read these in full to find out what was already covered. Each does something we do not:

| Repo | Stars | What it does better than us |
|---|---|---|
| [tashfeenahmed/freellmapi](https://github.com/tashfeenahmed/freellmapi) | 24.5k | not a list — installable software routing across 34 providers |
| [mnfst/awesome-free-llm-apis](https://github.com/mnfst/awesome-free-llm-apis) | 7.4k | verifies every row against a live request inside a dated window |
| [open-free-llm-api/awesome-freellm-apis](https://github.com/open-free-llm-api/awesome-freellm-apis) | 2.8k | 134+ APIs from 40+ providers, refreshed daily, with config snippets |
| [12britz/awesome-free-models](https://github.com/12britz/awesome-free-models) | 2.1k | re-checks hundreds of endpoints and publishes the failures too |
| [zukixa/cool-ai-stuff](https://github.com/zukixa/cool-ai-stuff) | 1.2k | was thorough; last updated October 2025 — the cautionary tale |
| [nejib1/Free-LLM](https://github.com/nejib1/Free-LLM) | 361 | credit-card transparency per provider, runnable code per entry |

### What re-testing those lists actually returns

Their tables are the best-organised in this field and their credit-card column is a genuinely useful
idea we did not have. What their numbers are not is current. On 2026-09-07 we called every endpoint
that three separate published lists describe as needing **no API key**, with no `Authorization` header,
exactly as a reader would:

| Endpoint | Published as | Answered with |
|---|---|---|
| `api.llm7.io` | 30 requests/minute, no signup | `401 Missing API key` |
| `text.pollinations.ai` | ~1 request/15s, anonymous | `402 Payment Required` |
| `inference-api.nousresearch.com` | no key | model retired, `404` |
| `api.inference.net` | no key | `401 Missing Authorization Bearer token` |
| `inference.api.nscale.com` | no key | `401 Unauthorized` |
| `api.aionlabs.ai` | no key | `401 credentials were not provided` |

Six for six. This is not a criticism of the people who wrote those lists — free endpoints close
quietly and a list nobody re-runs decays within weeks. It is the reason every row here carries the day
it was called, and the reason the two keyless endpoints we do publish were called without a key before
they were listed.
| [amardeeplakshkar/awesome-free-llm-apis](https://github.com/amardeeplakshkar/awesome-free-llm-apis) | 158 | permanent-free only: no trials, no promos — a stricter definition |
| [raullenchai/free-llm-api-resources](https://github.com/raullenchai/free-llm-api-resources) | — | keeps alive the fork of `cheahjs/free-llm-api-resources`, which now 404s |

**What none of them publishes, and why this repo exists:** a ranking by quality *times* volume, whether
the provider actually answers, and what the free tier costs you in things that are not money.

## Provider terms and rate-limit pages, read directly

Read on the dates recorded in [`bench/limits.json`](bench/limits.json) and
[`bench/privacy.json`](bench/privacy.json):

- [Groq rate limits](https://console.groq.com/docs/rate-limits) — where we found that the published
  table is the **Developer plan**, not the free tier
- [Cerebras pricing](https://inference-docs.cerebras.ai/support/pricing)
- [Google Gemini API rate limits](https://ai.google.dev/gemini-api/docs/rate-limits) and
  [terms](https://ai.google.dev/gemini-api/terms) — quoted directly in filter 5
- [OpenRouter limits](https://openrouter.ai/docs/api-reference/limits) — where the daily cap turns out
  to depend on lifetime credits purchased
- [Cloudflare Workers AI pricing](https://developers.cloudflare.com/workers-ai/platform/pricing/) —
  where the free allowance is in neurons, not requests
- [Ollama pricing](https://ollama.com/pricing)

## Benchmarks we evaluated and did not use

Kept here because a rejected option with a reason is worth more than a silent one:

- **[IFEval](https://huggingface.co/datasets/google/IFEval)** (Apache 2.0) and
  **[MMLU-Pro](https://huggingface.co/datasets/TIGER-Lab/MMLU-Pro)** (MIT) — we planned to run these
  ourselves on every free endpoint. Dropped: running any benchmark ourselves does not scale when new
  providers appear weekly, and a benchmark run by whoever publishes the ranking is exactly what a
  reader should distrust. Their design still shaped ours: **every check decided by code, never by
  opinion.**
- **[LiveBench](https://github.com/LiveBench/LiveBench)** — contamination-free and monthly-refreshed,
  but its licence on the data files was not clear enough to redistribute confidently.
- **Open LLM Leaderboard** — frozen since March 2025.

## The one thing here that is ours

The **Romanian language benchmark** in [results/](results/): four machine-checked probes and a blind
jury of two judges from different model families. Method, prompts, raw answers and every judge score
are published, including the finding that argues against our own headline — the two judges correlate
at 0.93 on whether the Romanian is correct and at **−0.07** on whether it sounds human.

It is no longer the ranking, for the reason above. It stays because it is still the only measurement
anywhere of these models on a small language, and because deleting a measurement when it stops being
convenient is how a repo starts lying about its own history.
