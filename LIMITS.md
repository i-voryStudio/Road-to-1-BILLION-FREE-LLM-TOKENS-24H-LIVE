# Rate limits, and how we know them

Read on 2026-09-06. Source of truth: [`bench/limits.json`](bench/limits.json) - correcting a number here is a one-line pull request.

Three confidence levels, and the difference matters more than the numbers:

- **MEASURED** - we saw it: a response header, or a 429 we walked into.
- **DECLARED** - the provider says so on a page we read, with the date we read it.
- **UNKNOWN** - nobody publishes it and we did not measure it. It stays unknown. We do not copy a figure from another list to fill the gap, and unknown does not mean unlimited.

## One-time grants, kept apart from the daily numbers

A sign-up bundle is not a daily quota. It is real once, and every figure below carries the provider's
own sentence, because a giveaway described in our words is a marketing claim with our name on it. A
grant made in money stays in money: converting it into tokens needs the provider's published price.

<!--ONE-TIME-->
| Provider | One-time | Expires | Their words |
|---|---|---|---|
| alibaba | 4,000,000 tokens | 90 days from activation | Each model (such as qwen-plus, qwen3.6-plus, or qwen3.6-plus-2026-04-02) has its own independent free quota (typically 1,000,000 tokens). Quota cannot be merged or transferred across models. |
| cerebras | $5 in credits | UNKNOWN | Free Trial: $5 in free credits after making an account |
| ollama | size not published | UNKNOWN | Free accounts include a starter amount of usage for a smaller set of starter models. Adding extra credits unlocks all models. |
| siliconflow | $1 in credits | UNKNOWN | Flexible token pricing, high usage limits, and postpaid billing - plus $1 in free credits to get you started! |
<!--/ONE-TIME-->

## groq

- **Confidence:** DECLARED
- **Limit applies per:** ORGANIZATION - so a second API key does not raise it.
- **Source:** https://console.groq.com/docs/rate-limits (read 2026-09-06)
- **The limit that actually bites:** TPM, not RPD. 8,000 tokens per minute is what you actually hit: a long prompt returns 413 long before you approach 1,000 requests. We measured that 413 on an article-length prompt.

The published table is labelled as the BASE LIMITS OF THE DEVELOPER PLAN, not the free tier. Quote: 'the limits shown below are the base limits for the Developer plan'. Free-tier values are not published; check your own console at /settings/limits. Every list that reprints 1,000 requests/day as a free-tier figure is reprinting a paid plan's number.

| Model | RPM | RPD | TPM | TPD |
|---|---|---|---|---|
| `openai/gpt-oss-120b` | 30 | 1000 | 8000 | 200000 |
| `openai/gpt-oss-20b` | 30 | 1000 | 8000 | 200000 |
| `qwen/qwen3.8-27b` | 30 | 1000 | 8000 | 200000 |
| `qwen/qwen3.6-27b` | 30 | 1000 | 8000 | 200000 |

## cerebras

- **Confidence:** MEASURED
- **Limit applies per:** ACCOUNT
- **Source:** https://inference-docs.cerebras.ai/support/pricing (read ?)
- **Measured:** 2026-09-02, read off the rate-limit response headers on the calling account
- **VOLATILE** - re-measure before relying on it.
- **The limit that actually bites:** 5 requests per minute. Two calls inside the same minute need roughly 13 s between them.

Their pricing page on 2026-09-06 describes free access only as 'Free Trial: $5 in free credits after making an account' and publishes no daily free-tier ceiling at all. The numbers below are what the calling account's headers reported on 2026-09-02. They may be trial allowance rather than a standing free tier. Re-measure before relying on them.

All models: RPM 5, RPH 150, RPD 2400, TPD 1000000

## google

- **Confidence:** DECLARED
- **Limit applies per:** PROJECT - so a second API key does not raise it.
- **Source:** https://ai.google.dev/gemini-api/docs/rate-limits and the AI Studio rate-limit console (read 2026-09-06)
- **The limit that actually bites:** Requests per DAY on the Flash models. 20/day is a handful of conversations, not a workload.

The public docs page no longer prints the per-model table; it points you at aistudio.google.com/rate-limit, which needs a login. The figures below were read off that console screen. Free tier means literally 'no billing account linked': linking one moves the project to Tier 1 and off these numbers. Because the limits are per PROJECT, a second API key in the same project buys you nothing.

| Model | RPM | RPD | TPM | TPD |
|---|---|---|---|---|
| `gemini-3.8-flash` | 5 | 20 | - | - |
| `gemini-3.5-flash-lite` | 15 | 500 | 250000 | - |
| `gemma-4-31b-it` | - | - | - | - |

## openrouter

- **Confidence:** DECLARED
- **Limit applies per:** ACCOUNT
- **Source:** https://openrouter.ai/docs/api-reference/limits (read 2026-09-06)

The daily cap depends on lifetime credits purchased, and applies across ALL :free models combined, not per model. This condition is the one most lists drop, which makes their number wrong for a new account by a factor of twenty.

| Lifetime credits purchased | Req/min | Req/day |
|---|---|---|
| under 10 dollars lifetime | 20 | 50 |
| at least 10 dollars lifetime | 20 | 1000 |

## cloudflare

- **Confidence:** DECLARED
- **Limit applies per:** ACCOUNT
- **Source:** https://developers.cloudflare.com/workers-ai/platform/pricing/ (read 2026-09-06)

The free allocation is denominated in NEURONS per day, not requests, and the neuron cost per token differs by more than a factor of ten between models: llama-3.2-1b costs 18,252 neurons per million output tokens, llama-3.3-70b costs 204,805. So a requests-per-day figure for 'Cloudflare' as a whole is meaningless. Convert per model or do not quote it.

Free allocation: {"neurons_per_day": 10000}

| Model | Neurons / M input | Neurons / M output |
|---|---|---|
| `@cf/meta/llama-3.3-70b-instruct-fp8-fast` | 26,668 | 204,805 |
| `@cf/meta/llama-3.2-1b-instruct` | 2,457 | 18,252 |

## nvidia

- **Confidence:** UNKNOWN
- **Limit applies per:** KEY

We carried a figure of 40 requests per minute per key in our own notes, but we could not find it on a public NVIDIA page when we went looking, so it is NOT published here as a rate limit. Unknown, not 40. What we do have is our own concurrency measurement below, which is worth more anyway: it says how many calls the model takes in parallel, which no rate-limit table tells you. If you find the published figure, the source URL is a one-line pull request.

**Concurrency, measured 2026-09-05** - how many calls the model takes in parallel, which no rate-limit table tells you:
- `nvidia/nemotron-3-super-120b-a12b`: 8 concurrent calls, all returned 200
- `moonshotai/kimi-k3`: serial only: 7 of 8 concurrent calls returned 429 instantly. 25-55 s per call, so roughly 60-100 per hour if nothing else shares the key.

## ollama

- **Confidence:** UNKNOWN
- **Limit applies per:** ACCOUNT
- **Source:** https://ollama.com/pricing (read 2026-09-06)

The free plan is $0 with 'starter usage credits included' and access to 'starter models' only, and the amount of those credits is not published. The API returns no rate-limit headers either, so the ceiling is genuinely unknown, not unlimited. Note also that 'run multiple models concurrently' is listed as a PAID plan feature and a higher tier advertises '10 concurrent requests', so the free plan should be assumed to be serial.

## alibaba

- **Confidence:** UNKNOWN
- **Limit applies per:** ACCOUNT

Free access comes as per-model token grants with an expiry date rather than a standing rate limit, and the amount is not visible from the API. Reachable on the international endpoint. Unknown, not unlimited.

## xkiro

- **Confidence:** UNKNOWN
- **Limit applies per:** ACCOUNT

No rate-limit headers returned and no published quota.

## siliconflow

- **Confidence:** UNKNOWN
- **Limit applies per:** ACCOUNT

NOT TESTED, and this is about the caller, not about them: the key was answered with 402, so every call returned 402. That says nothing about the provider's free tier and SiliconFlow is therefore excluded from the quality ranking rather than scored zero.

