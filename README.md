# Free LLM APIs, Ranked by What You Can Actually Get Done

## What is on the table right now

| | |
|---|---|
| **Tokens per 24h**, confirmed | **6,475,000** |
| Endpoints answering today | **28 of 33** |
| Providers whose quota nobody publishes | **5 of 10** |

That total is the **confirmed minimum, and it is an undercount** — 5 of the 10 providers publish no
quota at all, so their capacity is real and uncounted. We would rather understate than invent. It also
moved five-fold in one afternoon when we stopped reading marketing pages and asked the providers
directly: one of them exposes 5M tokens a day behind an endpoint nobody had thought to call.

### The five best free endpoints today

| # | Model | Provider | Value | Coding | Tokens/day |
|---|---|---|---|---|---|
| 1 | `minimax/minimax-m3:free` | xkiro | **234.4** | 58.6 | 5,000,000 |
| 2 | `minimax/minimax-m2.7:free` | xkiro | **210.4** | 52.6 | 5,000,000 |
| 3 | `qwen-3.8-27b` | cerebras | **206.2** | 68.1 | 1,000,000 |
| 4 | `qwen/qwen3.8-27b` | groq | **155.1** | 68.1 | 200,000 |
| 5 | `gemma-4-31b` | cerebras | **131.4** | 43.4 | 1,000,000 |

**Value = quality x volume x how often it actually answers.** Volume is in **tokens**, not requests,
because a request cap and a token cap are the same shelf in different units and the smaller one is your
real ceiling. `gemini-3.8-flash` has the best coding score in the whole list — **76.3** — and is nowhere
near the top, because Google gives you 20 requests a day.

Full ranking of the top 30: below. **Every single endpoint we track, nothing filtered:
[ALL-ENDPOINTS.md](ALL-ENDPOINTS.md).** All six filters: [RESULTS.md](RESULTS.md).

---

## The full ranking, top 30

<!--RANKING-->
| # | Model | Provider | Value | Auth | Coding | Req/day | Note |
|---|---|---|---|---|---|---|---|
| 1 | `minimax/minimax-m3:free` | xkiro | **234.4** | key | 58.6 | 5,000,000 | answers 100% of the time |
| 2 | `minimax/minimax-m2.7:free` | xkiro | **210.4** | key | 52.6 | 5,000,000 | answers 100% of the time |
| 3 | `qwen-3.8-27b` | cerebras | **206.2** | key | 68.1 | 1,000,000 | **answers blank unless you turn thinking off** |
| 4 | `qwen/qwen3.8-27b` | groq | **155.1** | key | 68.1 | 200,000 | answers 88% of the time |
| 5 | `gemma-4-31b` | cerebras | **131.4** | key | 43.4 | 1,000,000 | answers 92% of the time |
| 6 | `qwen/qwen3.6-27b` | groq | **122.3** | key | 53.7 | 200,000 | answers 88% of the time |
| 7 | `gpt-oss-120b` | cerebras | **92.0** | key | 30.4 | 1,000,000 | answers 92% of the time |
| 8 | `minimax/minimax-m3:free` | openrouter | **91.8** | key | 58.6 | 25,000 | answers 92% of the time |
| 9 | `gemini-3.5-flash-lite` | google | **88.8** | key | 49.3 | 250,000 | **trains on your prompts** |
| 10 | `minimax/minimax-m2.7:free` | openrouter | **82.4** | key | 52.6 | 25,000 | answers 92% of the time |
| 11 | `nvidia/nemotron-3-ultra-550b-a55b:free` | openrouter | **77.2** | key | 49.3 | 25,000 | answers 92% of the time |
| 12 | `openai/gpt-oss-120b` | groq | **69.2** | key | 30.4 | 200,000 | answers 88% of the time |
| 13 | `gemini-3.8-flash` | google | **67.3** | key | 76.3 | 10,000 | **trains on your prompts** |
| 14 | `openai/gpt-oss-20b` | groq | **47.1** | key | 20.7 | 200,000 | answers 88% of the time |
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
