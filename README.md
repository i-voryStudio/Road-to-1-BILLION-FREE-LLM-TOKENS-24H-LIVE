# Free LLM APIs, Ranked by What You Can Actually Get Done

## What is on the table right now

| | |
|---|---|
| **Requests per 24h**, across providers with a confirmed quota | **3,950** |
| **Tokens per 24h**, confirmed | **1,200,000** |
| Endpoints answering today | **28 of 33** |
| Providers whose daily quota nobody publishes | **6 of 10** |

Those totals are the **confirmed minimum**, not a marketing number: six of the ten providers publish no
daily quota at all, so their capacity is real but uncounted. We would rather understate than invent.

### The five best free endpoints today

| # | Model | Provider | Value | Coding | Req/day |
|---|---|---|---|---|---|
| 1 | `qwen-3.8-27b` | cerebras | **211.1** | 68.1 | 2,400 |
| 2 | `qwen/qwen3.8-27b` | groq | **178.8** | 68.1 | 1,000 |
| 3 | `qwen/qwen3.6-27b` | groq | **141.0** | 53.7 | 1,000 |
| 4 | `gemma-4-31b` | cerebras | **134.5** | 43.4 | 2,400 |
| 5 | `gpt-oss-120b` | cerebras | **94.2** | 30.4 | 2,400 |

**Value = quality x volume**, and that is the whole point. `gemini-3.8-flash` has the best coding score
in the entire list — **76.3** — and does not appear above, because Google gives you **20 requests a
day**. A weaker model you can call 2,400 times beats a brilliant one you can call twenty.

Every other list ranks these by rate limit alone. Full tables and all six filters:
**[RESULTS.md](RESULTS.md)**.

---

## How this list is built, and why you can check every number

**We read every free-LLM list on GitHub before writing ours** — all eight of them, plus the
[OmniRoute](https://github.com/diegosouzapw/OmniRoute) catalogue of 351 providers, every provider's own
rate-limit and terms pages, and two benchmark suites we evaluated and rejected. What we took from each,
and what we deliberately refused to take, is written down: **[SOURCES.md](SOURCES.md)**.

**A research loop runs continuously — on these same free APIs — looking for new ones.** Free endpoints
appear weekly and die in months, usually with no announcement. The catalogue we cross-check against lost
six providers between March and August 2026. A list nobody re-reads becomes fiction; this one is
re-measured every day, and what dies gets a date and a headstone in
**[GRAVEYARD.md](GRAVEYARD.md)** rather than quietly disappearing.

**Quality is imported, never run by us.** Scores come from official benchmarks (Artificial Analysis,
Design Arena). We measure only what nobody else can tell you: the real quota, whether it answers today,
whether it needs a key, and what the free tier costs you in things that are not money.

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

We used to run our own quality benchmark. It does not scale: free providers appear weekly, and each
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

## Where all of this comes from

Every source, every repo we read, every provider page and every benchmark we evaluated and rejected — with what we took from each and what we deliberately did not:
**[SOURCES.md](SOURCES.md)**.

## Licence

Code (`bench/`) under **MIT**. Data and tables under
**[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)**. Benchmark scores belong to their authors
and are attributed in [CREDITS.md](CREDITS.md).

Built by **[i-vory Studio](https://i-vory.studio)**.
