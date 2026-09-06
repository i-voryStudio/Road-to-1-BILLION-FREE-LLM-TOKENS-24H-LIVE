# Free LLM APIs, Ranked by What You Can Actually Get Done

## What is on the table right now

<!--HEADLINE-->
| | |
|---|---|
| **Tokens per 24h we MEASURED ourselves** | **6,000,000** |
| Also claimed by providers, sourced, not measured | 275,000 |
| Published only for a PAID plan, excluded from both | 200,000 |
| Endpoints answering today | **30 of 37 tested** |
| Providers whose quota nobody publishes | **7 of 12** |
| Distance to 1,000,000,000 measured tokens/day | **167x** |
<!--/HEADLINE-->

**Where this is going, out loud: one billion free tokens a day.** That is the number the list is
built towards, and the box above measures the distance to it every day.

**Three numbers, not one, and this is the whole argument.** Measured means we saw it: a response
header, a usage endpoint, a 429 we walked into. Claimed means the provider says so on a page we read,
sourced and dated — real, and still their word. Paid-plan means the only published figure belongs to a
paid tier, so it is not free capacity at all and is excluded from both. They are separated by code, in
[`data/capacity.json`](data/capacity.json), and only the measured one is summed. Every other list adds
all three together and calls the result free.

The measured total is an **undercount**: 7 of the 12 providers publish no quota at all, so their
capacity is real and uncounted. Asking a provider directly beats reading its marketing page — one of
them exposes 5M tokens a day behind an endpoint nobody had thought to call.

## We read every other list first. Then we measured all of it again.

You already know these lists exist. [OmniRoute](https://github.com/diegosouzapw/OmniRoute) routes
across hundreds of providers, and `awesome-free-llm-apis` and seven more are catalogued in
[SOURCES.md](SOURCES.md), each credited for what it does well. We went through all of them line by
line. This is not a ninth copy of the same table: everything in here went through our own mill first,
and the mill is the product.

**Nothing here is copied.** Quality comes from official benchmarks, by attribution, because a benchmark
run by the people publishing the ranking is worth nothing. Everything else — whether the endpoint
answered today, what the quota really is, whether it takes a key, what it costs you in things that are
not money — we measure ourselves, and every number carries how we know it: MEASURED, DECLARED,
PAID-PLAN, or UNKNOWN. UNKNOWN stays UNKNOWN. We never fill a hole with someone else's number.

**What that catches, concretely, today.** OmniRoute's registry (219 provider entries, read from the
v3.8.49 release) marks 16 endpoints as needing no key or treating it as optional. Eight of those are
ordinary HTTP APIs we could call. We called all eight with no `Authorization` header:

| What we found | How many |
|---|---|
| Returned a real completion with no key | **1** — `hermes.ai.unturf.com` |
| No key required, but the shared anonymous bucket was empty both times | **1** — OVHcloud, 2 requests/minute |
| Answered `401`: the catalogue is public, the inference is not | 3 — including one serving 860 models |
| Answered `402 Payment Required` | 3 |

So of sixteen keyless endpoints on the best-known list, **one actually answers**. That is not a
criticism of them — free endpoints close quietly, and a list nobody re-runs is a list that decays. It
is the reason this one gets re-run.

**And something is looking for the next one, all day.** Two catalogue crawlers run non-stop against public, keyless catalogues, looking for endpoints this list does not have yet and checking them the same way everything else here is checked. What they find arrives as an ordinary change, with the same evidence and the same gates as every other row: nothing enters this list because a machine liked it.

**And it is re-run every day.** A scheduled job re-reads the public catalogues, re-imports the official
scores, recomputes the ranking, applies the fourteen-day death rule, and commits the difference —
[`daily-catalog.yml`](.github/workflows/daily-catalog.yml), 06:17 UTC, no secrets, so it runs on your
fork too. The liveness probe needs API keys, so it runs where the keys are and appends to
[`data/uptime.jsonl`](data/uptime.jsonl), which is the history behind every "answers X% of the time" in
the table below. If a day is missing, the file shows it missing.

### The five best free endpoints today

<!--TOP5-->
| # | Model | Provider | Value | Coding | Tokens/day |
|---|---|---|---|---|---|
| 1 | `minimax/minimax-m3:free` | xkiro | **234.4** | 58.6 | 5,000,000 |
| 2 | `qwen-3.8-27b` | cerebras | **224.8** | 68.1 | 1,000,000 |
| 3 | `qwen/qwen3.8-27b` | groq | **177.3** | 68.1 | 200,000 |
| 4 | `gemma-4-31b` | cerebras | **143.3** | 43.4 | 1,000,000 |
| 5 | `qwen/qwen3.6-27b` | groq | **139.8** | 53.7 | 200,000 |
<!--/TOP5-->

**Value = quality x volume x how often it actually answers.** Volume is in **tokens**, not requests,
because a request cap and a token cap are the same shelf in different units and the smaller one is your
real ceiling. `gemini-3.8-flash` has the best coding score in the whole list — **76.3** — and is nowhere
near the top, because Google gives you 20 requests a day.

Full ranking of the top 30: below. **Every single endpoint we track, nothing filtered:
[ALL-ENDPOINTS.md](ALL-ENDPOINTS.md).** All six filters: [RESULTS.md](RESULTS.md).

---

## The full ranking, top 30

<!--RANKING-->
| # | Model | Provider | Value | Auth | Coding | Tokens/day | Note |
|---|---|---|---|---|---|---|---|
| 1 | `minimax/minimax-m3:free` | xkiro | **234.4** | key | 58.6 | 5,000,000 | answered 2 of 2 radar probes in the last 14 days |
| 2 | `qwen-3.8-27b` | cerebras | **224.8** | key | 68.1 | 1,000,000 | **answers blank unless you turn thinking off** |
| 3 | `qwen/qwen3.8-27b` | groq | **177.3** | key | 68.1 | 200,000 | answered 2 of 2 radar probes in the last 14 days |
| 4 | `gemma-4-31b` | cerebras | **143.3** | key | 43.4 | 1,000,000 | answered 2 of 2 radar probes in the last 14 days |
| 5 | `qwen/qwen3.6-27b` | groq | **139.8** | key | 53.7 | 200,000 | answered 2 of 2 radar probes in the last 14 days |
| 6 | `gemini-3.5-flash-lite` | google | **133.1** | key | 49.3 | 250,000 | **trains on your prompts** |
| 7 | `minimax/minimax-m2.7:free` | xkiro | **105.2** | key | 52.6 | 5,000,000 | answered 1 of 2 radar probes in the last 14 days |
| 8 | `gpt-oss-120b` | cerebras | **100.4** | key | 30.4 | 1,000,000 | answered 2 of 2 radar probes in the last 14 days |
| 9 | `minimax/minimax-m3:free` | openrouter | **100.1** | key | 58.6 | 25,000 | answered 2 of 2 radar probes in the last 14 days |
| 10 | `openai/gpt-oss-120b` | groq | **79.1** | key | 30.4 | 200,000 | answered 2 of 2 radar probes in the last 14 days |
| 11 | `openai/gpt-oss-20b` | groq | **53.9** | key | 20.7 | 200,000 | answered 2 of 2 radar probes in the last 14 days |
| 12 | `gemini-3.8-flash` | google | **0.0** | key | 76.3 | 10,000 | **trains on your prompts** |
| 13 | `minimax/minimax-m2.7:free` | openrouter | **0.0** | key | 52.6 | 25,000 | answered 0 of 2 radar probes in the last 14 days |
| 14 | `nvidia/nemotron-3-ultra-550b-a55b:free` | openrouter | **0.0** | key | 49.3 | 25,000 | answered 0 of 2 radar probes in the last 14 days |
<!--/RANKING-->

Every endpoint we track, ranked or not, scored or not: **[ALL-ENDPOINTS.md](ALL-ENDPOINTS.md)**.

---

## The five filters

| | Filter | Where it comes from |
|---|---|---|
| **1** | **Value = quality x volume x reliability** | the headline ranking |
| 2 | Quality | **imported** from official benchmarks, never our own |
| 3 | Volume | measured by us, or declared with a source |
| 4 | Needs a key, or not | no-key endpoints get a declared bonus |
| 5 | **What it costs you that is not money** | read from the provider's own terms |

### Why quality is imported and everything else is measured

Running a quality benchmark of our own does not scale: free providers appear weekly, and each
would have to go through a full battery before it could be listed at all. Worse, a benchmark run by
whoever publishes the ranking is exactly what a careful reader should distrust.

    imported   what the MODEL can do        <- Artificial Analysis, Design Arena
    measured   what the PROVIDER gives you  <- quota, uptime, auth, privacy

So a new provider costs nothing to rate. Serve `qwen3.8-27b` and it inherits that model's published
scores the day we add the endpoint. That is what makes this list able to keep up.

### The trap that costs you most: a `200` with nothing in it

A model that reasons can spend its **entire token budget thinking** and return an empty message — with
HTTP 200. The status code says success. There is no text. Your quota is gone and nothing looks wrong.

Every provider family takes a different switch, and some take none at all:

```
reasoning_effort: low                            gpt-oss on Groq, Cerebras, Ollama
chat_template_kwargs: {enable_thinking: false}   NVIDIA nemotron
enable_thinking: false                           Alibaba Qwen
thinking: {type: disabled}                       z.ai GLM
```

Measured in our own run: **5 empty 200s, 4 of them on models where no switch was set.** We already
set the switch for 12 of the models we call — those are in
[`bench/providers.json`](bench/providers.json) and are the cheapest thing to copy out of this repo.

### And a quota you cannot draw on is not a quota

The fast providers are not always up. Measured across every call we made:

| Provider | Answered | What went wrong |
|---|---|---|
| alibaba | **100%** | answers reliably |
| ollama | **100%** | answers reliably |
| xkiro | **100%** | answers reliably |
| cerebras | **92%** | occasionally refuses or returns nothing |
| openrouter | **92%** | occasionally refuses or returns nothing |
| cloudflare | **90%** | occasionally refuses or returns nothing |

That rate multiplies into the ranking. A provider that refuses a third of your calls is worth a third
less than its paper number, and ranking on advertised figures alone rewards whoever advertises hardest.

### Filter 5: what it costs you that is not money

Free often means you are paying with your prompts. Google's terms say free-tier content is used to
"provide, improve, and develop Google products... and machine learning technologies", that "human
reviewers may read, annotate, and process your API input and output", and that the free tier may not be
used for apps serving users in the EEA, Switzerland or the UK. Quoted, not paraphrased —
[the full table is in RESULTS.md](RESULTS.md).

Most rows there say `UNKNOWN`, because nobody has read those terms yet. `UNKNOWN` is the honest
default: inventing a "no" is the most damaging wrong answer this repo could publish.

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

## Endpoints that need no key at all

Rare, and worth more than their raw quality: no account, no card, no e-mail. The ranking pays them a
bonus for it. Most lists that advertise "no key" are quoting a page that stopped being true a while
ago, so every one here was called with no `Authorization` header before it was listed, and the day we
did it is in the table.

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

## Where all of this comes from

Every source, every repo we read, every provider page and every benchmark we evaluated and rejected — with what we took from each and what we deliberately did not:
**[SOURCES.md](SOURCES.md)**.

## Licence

Code (`bench/`) under **MIT**. Data and tables under
**[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)**. Benchmark scores belong to their authors
and are attributed in [CREDITS.md](CREDITS.md).

Built by **[i-vory Studio](https://i-vory.studio)**.
