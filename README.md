# ROAD TO 1 BILLION FREE LLM TOKENS/DAY

A live, measured list of every free LLM API we can find, ranked by what you can actually get done with
it: quality from official benchmarks, volume from response headers and pricing pages, and every figure
labelled by how we know it.

## The five best free endpoints today

<!--TOP5-->
| # | Model | Provider | Value | Coding | Tokens/day | Volume | Answers | Cost | Get key |
|---|---|---|---|---|---|---|---|---|---|
| 1 | `minimax/minimax-m3:free` | xkiro | **234.4** | 58.6 | 5,000,000 | MEASURED | 2 of 2 in 14 days | terms not read | [get a key](https://xkiro.com) |
| 2 | `qwen-3.8-27b` | cerebras | **224.8** | 68.1 | 1,000,000 | MEASURED | 2 of 2 in 14 days; blank 200 seen in the archived run | terms not read | [get a key](https://cloud.cerebras.ai) |
| 3 | `@cf/qwen/qwen3.8-27b` | cloudflare | **187.9** | 68.1 | 286,795 | DERIVED | 2 of 2 in 14 days; blank 200 seen in the archived run | terms not read | [get a key](https://dash.cloudflare.com/profile/api-tokens) |
| 4 | `gemini-3.8-flash-free` | aihubmix | **152.9** | 76.3 | 50,000 | DERIVED | not probed yet | terms not read; $1 top-up unlocks the daily quota | [get a key](https://aihubmix.com/) |
| 5 | `coding-kimi-k3-free` | aihubmix | **152.7** | 76.2 | 50,000 | DERIVED | not probed yet | terms not read; $1 top-up unlocks the daily quota | [get a key](https://aihubmix.com/) |
<!--/TOP5-->

**Value = quality x volume x how often it actually answers**, and the exact formula is printed on every
page, from the same constants the code runs on:

<!--FORMULA-->
`coding_index x log10(1 + daily_tokens / 500) x answered_rate x 1.25 if no key x 0.5 if degraded`
<!--/FORMULA-->

Volume is in **tokens**, not requests, because a request cap and a token cap are the same shelf in
different units and the smaller one is your real ceiling. **Volume** says how we know that figure,
**Answers** is the last 14 days of our own daily probe, **Cost** is what the free tier costs you that is
not money plus anything you must pay once to unlock it, and **Get key** is the provider's own sign-up
page, checked against its API domain so it cannot point at a lookalike.

<!--EXAMPLE-->
The best coding score in the whole list, **76.3**, belongs to `gemini-3.8-flash`, `gemini-3.8-flash-free`, and the score alone decides nothing: at aihubmix it sits at #4 with a value of 152.9: 50,000 tokens a day (DERIVED); at google it sits at #21 with a value of 0.0: its radar probes in the window (0 of 1 in 14 days) came back with no text, so the answered rate in the formula is 0.
<!--/EXAMPLE-->

## Where this is going, out loud: one billion free tokens a day

<!--ROAD-->
`░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░`  **~1.2%**

**Roughly 12,218,019 tokens a day** is what this list can defend on 2026-09-07: 6,000,000 measured from response headers or usage endpoints (2 providers); nothing published by a provider as a daily token figure; 636,795 derived from a published request cap at 500 tokens a reply or from a published unit price (5 providers); 5,581,224 extrapolated from a 60-minute draw (1 provider). The target is 1,000,000,000 a day by 2026-11-07, 81.8 times that. Nothing here is a burst multiplied out to a day.

*Bursts are a different thing.* In 30-second bursts, latest reading per provider, **11 of 18 providers handed us 140,850 tokens a minute** added together on 2026-09-07; 3 answered and delivered nothing (hetzner, mistral, ovhcloud). A burst is a rate: 100,000 tokens a minute is a fact and 144,000,000 a day is a number nobody will be allowed to spend, so the bar above is built from the daily shelf and never from this rate. Free tiers move, throttle without warning and close; one provider here dropped 46-fold between two readings taken the same day. Nothing on this page is guaranteed to you by anyone, us included.

*What they allow.* The only output-only ceiling published (hetzner: 100,000 output tokens a minute) is 14% of the 694,444 a minute the target works out to. Ceilings published as input-plus-output, or without saying which, add up to 5,298,000 a minute across 4 providers and cannot be compared with an output target, so they are not.
<!--/ROAD-->

<!--HEADLINE-->
| | |
|---|---|
| **Tokens a day this list can defend** | **12,218,019** |
| measured by us from headers or usage endpoints | 6,000,000 |
| published by the provider in tokens | 0 |
| derived from a published request cap at 500 tokens each, or a published unit price | 636,795 |
| extrapolated from a 60-minute draw, where nothing above exists | 5,581,224 |
| The target | 1,000,000,000 a day by 2026-11-07 |
| **Share of it** | **1.2%** |
| Providers with a daily figure on this shelf | 8 of 18 |
| | |
| *Bursts, which are a rate and not a day:* | |
| 30-second burst, per provider, latest reading, added up | 140,850 a minute |
| Providers that delivered anything in the burst | **11 of 18** |
| measured, delivered nothing | hetzner, mistral, ovhcloud |
| Endpoints answering today | **30 of 37 tested** |
| | |
| *What they ALLOW per minute, two shelves that never add:* | |
| Output-only ceilings, added up | 100,000 (hetzner) |
| Combined in+out ceilings, or unspecified, added up | 5,298,000 (4 providers) |
| Providers with any per-minute figure on file | 13 of 18 |
| | |
| *Shown, and not counted above:* | |
| Published only for a PAID plan | 200,000 a day (groq) |
| Once, at sign-up, in tokens | 1,000,000 per model (alibaba) |
| Once, at sign-up, in money | $6 |
| Monthly, in money | $10 (mistral) |
<!--/HEADLINE-->

## The full ranking, top 30

<!--RANKING-->
| # | Model | Provider | Value | Coding | Tokens/day | Volume | Answers | Cost | Get key |
|---|---|---|---|---|---|---|---|---|---|
| 1 | `minimax/minimax-m3:free` | xkiro | **234.4** | 58.6 | 5,000,000 | MEASURED | 2 of 2 in 14 days | terms not read | [get a key](https://xkiro.com) |
| 2 | `qwen-3.8-27b` | cerebras | **224.8** | 68.1 | 1,000,000 | MEASURED | 2 of 2 in 14 days; blank 200 seen in the archived run | terms not read | [get a key](https://cloud.cerebras.ai) |
| 3 | `@cf/qwen/qwen3.8-27b` | cloudflare | **187.9** | 68.1 | 286,795 | DERIVED | 2 of 2 in 14 days; blank 200 seen in the archived run | terms not read | [get a key](https://dash.cloudflare.com/profile/api-tokens) |
| 4 | `gemini-3.8-flash-free` | aihubmix | **152.9** | 76.3 | 50,000 | DERIVED | not probed yet | terms not read; $1 top-up unlocks the daily quota | [get a key](https://aihubmix.com/) |
| 5 | `coding-kimi-k3-free` | aihubmix | **152.7** | 76.2 | 50,000 | DERIVED | not probed yet | terms not read; $1 top-up unlocks the daily quota | [get a key](https://aihubmix.com/) |
| 6 | `coding-glm-5.3-free` | aihubmix | **149.9** | 74.8 | 50,000 | DERIVED | not probed yet | terms not read; $1 top-up unlocks the daily quota | [get a key](https://aihubmix.com/) |
| 7 | `gemma-4-31b` | cerebras | **143.3** | 43.4 | 1,000,000 | MEASURED | 2 of 2 in 14 days | terms not read | [get a key](https://cloud.cerebras.ai) |
| 8 | `gemini-3.5-flash-lite` | google | **133.1** | 49.3 | 250,000 | DERIVED | 1 of 1 in 14 days | **trains on your prompts**; human review; region-restricted | [get a key](https://aistudio.google.com/apikey) |
| 9 | `coding-minimax-m3-free` | aihubmix | **117.5** | 58.6 | 50,000 | DERIVED | not probed yet | terms not read; $1 top-up unlocks the daily quota | [get a key](https://aihubmix.com/) |
| 10 | `@cf/google/gemma-4-26b-a4b-it` | cloudflare | **108.4** | 39.3 | 286,795 | DERIVED | 2 of 2 in 14 days; blank 200 seen in the archived run | terms not read | [get a key](https://dash.cloudflare.com/profile/api-tokens) |
| 11 | `minimax/minimax-m2.7:free` | xkiro | **105.2** | 52.6 | 5,000,000 | MEASURED | 1 of 2 in 14 days | terms not read | [get a key](https://xkiro.com) |
| 12 | `gpt-oss-120b` | cerebras | **100.4** | 30.4 | 1,000,000 | MEASURED | 2 of 2 in 14 days | terms not read | [get a key](https://cloud.cerebras.ai) |
| 13 | `minimax/minimax-m3:free` | openrouter | **100.1** | 58.6 | 25,000 | DERIVED | 2 of 2 in 14 days | terms not read | [get a key](https://openrouter.ai/keys) |
| 14 | `mimo-v2-5:free` | kenari | **97.0** | 56.8 | 25,000 | DERIVED | not probed yet | terms not read | [get a key](https://kenari.id/) |
| 15 | `nemotron-3-ultra-550b-a55b:free` | kenari | **84.2** | 49.3 | 25,000 | DERIVED | not probed yet | terms not read | [get a key](https://kenari.id/) |
| 16 | `@cf/openai/gpt-oss-120b` | cloudflare | **83.9** | 30.4 | 286,795 | DERIVED | 2 of 2 in 14 days | terms not read | [get a key](https://dash.cloudflare.com/profile/api-tokens) |
| 17 | `mistral-medium-3-5:free` | kenari | **80.1** | 46.9 | 25,000 | DERIVED | not probed yet | terms not read | [get a key](https://kenari.id/) |
| 18 | `gemma-4-26b-a4b-it-free` | aihubmix | **78.8** | 39.3 | 50,000 | DERIVED | not probed yet | terms not read; $1 top-up unlocks the daily quota | [get a key](https://aihubmix.com/) |
| 19 | `nemotron-3-super-120b-a12b:free` | kenari | **64.4** | 37.7 | 25,000 | DERIVED | not probed yet | terms not read | [get a key](https://kenari.id/) |
| 20 | `@cf/meta/llama-3.3-70b-instruct-fp8-fast` | cloudflare | **23.7** | 11.9 | 48,826 | DERIVED | 2 of 2 in 14 days | terms not read | [get a key](https://dash.cloudflare.com/profile/api-tokens) |
| 21 | `gemini-3.8-flash` | google | **0.0** | 76.3 | 10,000 | DERIVED | 0 of 1 in 14 days | **trains on your prompts**; human review; region-restricted | [get a key](https://aistudio.google.com/apikey) |
| 22 | `minimax/minimax-m2.7:free` | openrouter | **0.0** | 52.6 | 25,000 | DERIVED | 0 of 2 in 14 days | terms not read | [get a key](https://openrouter.ai/keys) |
| 23 | `nvidia/nemotron-3-ultra-550b-a55b:free` | openrouter | **0.0** | 49.3 | 25,000 | DERIVED | 0 of 2 in 14 days | terms not read | [get a key](https://openrouter.ai/keys) |
<!--/RANKING-->

Every endpoint we track, ranked or not, scored or not: **[ALL-ENDPOINTS.md](ALL-ENDPOINTS.md)**. All the
tables, including quality alone and privacy cost: [RESULTS.md](RESULTS.md). Every rate limit with its
source and the date we read it: [LIMITS.md](LIMITS.md).

<!--COUNTS-->
18 providers and 63 endpoints are tracked. 23 endpoints are ranked; 40 are listed with what is missing. 35 endpoints have a radar verdict in the last 14 days, 5 were probed and only ever refused (429 or 402), and 23 have not been probed yet. 7 endpoints need no key. 8 providers have a daily figure this list can defend; 10 publish none and are counted as nothing: alibaba, groq, inferx, mistral, nvidia, ollama, ovhcloud, siliconflow, uncloseai, unorouter.
<!--/COUNTS-->

---

## How to read any row of this list

Five things decide whether a free API is worth your time, and every list we have seen collapses them
into one number. They are kept apart here on purpose.

**0. What we received, versus what they allow.** The first column of the provider table is the only one
on any list like this that nobody has to take on trust: real requests, sent in parallel for a window
of about thirty seconds with a small token budget, counting the output tokens that came back.
`bench/throughput.py` does it and the raw readings are in
[`data/throughput.jsonl`](data/throughput.jsonl). It is a **floor**: the test stops early when the
provider's own rate limit stops it, and then the number reported is the whole minute's allowance rather
than a rate scaled up from two seconds; requests already in flight are allowed to finish, which is why a
row can show up to a minute. A `0` means we got nothing, and the `Why 0` column says what the endpoint
returned instead.

**0b. Does the rate hold?** Sometimes, and sometimes not at all. One provider gave sixty thousand tokens
a minute on its first burst and under two thousand on the second, the same day, most of the second burst
ending in HTTP 409; two others held their rate almost exactly. So the column shows the **latest**
reading, and where an earlier one was much higher it says so in brackets. Treat every figure here as an
order of magnitude for comparing providers, not as an allowance anyone owes you.

**1. Per minute, or per day?** These are different shelves and adding them is the commonest mistake in
this field. A per-minute ceiling says how fast you may go; a daily cap says how much you get before the
door shuts. Almost nobody publishes both. Where a provider publishes only a per-minute figure, we write
it there and leave the daily column empty: we never multiply one into the other, because 100,000 tokens
a minute is a fact and 144 million a day is a number nobody will be allowed to spend. Per-minute
ceilings come in two denominations too, output-only and input-plus-output, and those are never added to
each other either.

**2. Recurring, once, or monthly?** A daily quota comes back every morning. A sign-up bundle, such as
Alibaba's 1,000,000 tokens per model, Cerebras's $5 or SiliconFlow's $1, arrives once and is gone. A
monthly pot, such as Mistral's $10 of credits, refreshes and runs out in between. All three are real;
added together they produce a total that stops being true after 24 hours, so each has its own column.

**3. Tokens, or requests?** A cap of 100 requests a day is not generous because the tokens are uncapped:
whichever limit bites first is your real ceiling. Where a provider caps requests, the daily token column
shows what those requests are worth at 500 tokens of output each, and the label says **DERIVED**, because
the provider published the requests and we chose the tokens per reply. That arithmetic is written into
every such row in [`data/ranking.json`](data/ranking.json).

**4. Card, phone, or nothing?** The `Card` and `Phone` columns are the ones that decide whether you can
start in the next five minutes. A phone number requirement is a hard wall for some countries. `?` means
the provider does not say, and we will not guess on your behalf.

**5. How do we know?** Every figure carries its provenance, and the difference matters more than the
number:

<!--LABELS-->
| | |
|---|---|
| **MEASURED** | we saw it ourselves: a response header, a usage endpoint, a 429 we walked into |
| **DECLARED** | the provider says so on a page we read, with the date we read it. Real, and still their word |
| **DERIVED** | arithmetic done here on figures the provider publishes, with the arithmetic shown: a request cap times 500 tokens a reply, or a unit price divided into an allowance |
| **PAID-PLAN** | the only published number belongs to a paid tier, so it is not free capacity at all. Never ranked, never summed |
| **UNKNOWN** | nobody publishes it and we have not measured it. It stays unknown. We do not borrow a number from another list to fill the hole, and unknown does not mean unlimited |
| **DRAWN** | tokens actually pulled over a 60-minute draw, times 24. An extrapolation, and it is labelled as one everywhere it appears; used only where a provider has no MEASURED, DECLARED or DERIVED daily figure |
<!--/LABELS-->

### Every provider, and what it actually gives you

Per minute first, because that is the unit this market publishes in; then the daily shelf, then the
grants. `-` means they publish nothing on that shelf, and nothing is what we write. Where a provider
publishes per-model ceilings, the largest is shown and the cell says so.

<!--CAPACITY-->
| Provider | Received /min, 30 s burst | Why 0 | Allow /min | Req/min | Per day | How we know | Monthly | Once | Key | Card | Phone |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **[alibaba](https://modelstudio.console.alibabacloud.com)** | 54,659 |  | 5,000,000 in+out | 600 | - | UNKNOWN | - | 1,000,000 tokens per model | yes | ? | **yes** |
| **[cloudflare](https://dash.cloudflare.com/profile/api-tokens)** | 27,670 |  | - | 300 | 286,795 | DERIVED | - | - | yes | no | no |
| **[inferx](https://model.inferx.net/)** | 22,005 |  | - | - | - | UNKNOWN | - | - | yes | ? | ? |
| **[nvidia](https://build.nvidia.com)** | 13,470 |  | - | - | - | UNKNOWN | - | - | yes | ? | ? |
| **[openrouter](https://openrouter.ai/keys)** | 7,997 |  | - | 20 | 25,000 | DERIVED | - | - | yes | ? | ? |
| **[aihubmix](https://aihubmix.com/)** | 7,048 |  | - | 10 | 50,000 | DERIVED | - | - | yes | no | no |
| **[kenari](https://kenari.id/)** | 2,799 |  | - | 5 | 25,000 | DERIVED | - | - | yes | no | no |
| **[ollama](https://ollama.com/settings/keys)** | 1,850 |  | - | - | - | UNKNOWN | size not published | - | yes | ? | ? |
| **[xkiro](https://xkiro.com)** | 1,446 (was 66,197) |  | - | - | 5,000,000 | MEASURED | - | - | yes | ? | ? |
| **[cerebras](https://cloud.cerebras.ai)** | 1,206 |  | - | 5 | 1,000,000 | MEASURED | - | $5 in credits | yes | ? | ? |
| **[uncloseai](https://hermes.ai.unturf.com/)** | 700 |  | - | 180 | - | UNKNOWN | - | - | **no key** | no | no |
| **[google](https://aistudio.google.com/apikey)** | - | not measured yet | 250,000 in+out (per model, largest) | 15 | 250,000 | DERIVED | - | - | yes | ? | ? |
| **[hetzner](https://console.hetzner.com/)** | 0 | five failures in a row: no response: timeout or connection failure | 4,000,000 in / 100,000 out | 10 | 5,581,224 | DRAWN | - | - | yes | or ID | optional |
| **[siliconflow](https://siliconflow.com)** | - | no rate: HTTP 402: the endpoint stops serving until a top-up | 40,000 in+out | 1,000 | - | UNKNOWN | - | $1 in credits | yes | ? | ? |
| **[groq](https://console.groq.com/keys)** | - | no rate: HTTP 403: the endpoint refused the caller | 8,000 in+out (per model, largest) | 30 | - | PAID-PLAN, not counted | - | - | yes | ? | ? |
| **[mistral](https://console.mistral.ai/)** | 0 | rate limit reached | - | - | - | UNKNOWN | $10 in credits | - | yes | no | ? |
| **[ovhcloud](https://oai.endpoints.kepler.ai.cloud.ovh.net/)** | 0 | rate limit reached | - | 2 | - | UNKNOWN | - | - | **no key** | **yes** | ? |
| **[unorouter](https://unorouter.com/)** | - | no rate: HTTP 503: no capacity behind the endpoint | - | 1 | - | UNKNOWN | - | - | yes | no | ? |
<!--/CAPACITY-->

**A ceiling you saw once is not a ceiling.** Mistral's free tier answered one of our calls with
a per-minute token ceiling header of 625,000, the largest figure we have measured anywhere. Half an hour
later, five readings a minute apart all said a per-minute request ceiling header of 0 and every call was
refused. Their pricing page explains it: the free plan is $10 a month in credits, so the ceiling is a
monthly pot, not a rate, and a header reading of zero means the pot is empty for the month. That is why
the 625,000 is recorded with its timestamps in [`bench/limits.json`](bench/limits.json) and published as
a monthly grant rather than as a per-minute ceiling.

**Most of the good ones publish a ceiling per minute and no daily figure at all.** Hetzner's free
inference documents 4,000,000 input and 100,000 output tokens per 60 seconds, and no daily row exists
on their page; we read the raw HTML to be sure, because other lists quote a 24-hour row that is not
there. Counting a provider like that as zero, which a daily-only total does, understates this list, so it
gets its own line, on its own terms, and is never multiplied out.

**The daily shelf is the only thing the bar is built from, and it is an undercount by construction.**
Measured means we saw the daily figure in a header or a usage endpoint; declared means the provider
publishes one in tokens; derived means we did arithmetic on what they publish. Paid-plan figures are
shown and excluded, and providers that publish nothing count as nothing. They are separated by code, in
[`data/capacity.json`](data/capacity.json). Asking a provider directly beats reading its marketing page:
one of them exposes 5,000,000 tokens a day behind a usage endpoint nobody had thought to call.

## And a quota you cannot draw on is not a quota

One probe per endpoint per day, every day, appended to [`data/uptime.jsonl`](data/uptime.jsonl). The
rate over the last fourteen days multiplies into the ranking, per endpoint. A provider that refuses a
third of your calls is worth a third less than its paper number, and ranking on advertised figures
alone rewards whoever advertises hardest. An endpoint we have not probed yet is not penalised: we do not
punish what we did not test, and the table says `not probed yet` rather than pretending.

<!--RELIABILITY-->
| Provider | Answered, last 14 days | Endpoints probed | Endpoints tracked |
|---|---|---|---|
| [alibaba](https://modelstudio.console.alibabacloud.com) | 8 of 8 (100%) | 4 | 4 |
| [cerebras](https://cloud.cerebras.ai) | 6 of 6 (100%) | 3 | 3 |
| [cloudflare](https://dash.cloudflare.com/profile/api-tokens) | 10 of 10 (100%) | 5 | 5 |
| [groq](https://console.groq.com/keys) | 8 of 8 (100%) | 4 | 4 |
| [nvidia](https://build.nvidia.com) | 10 of 10 (100%) | 5 | 5 |
| [ollama](https://ollama.com/settings/keys) | 6 of 6 (100%) | 3 | 3 |
| [ovhcloud](https://oai.endpoints.kepler.ai.cloud.ovh.net/) | 2 of 2 (100%) | 2 | 6 |
| [uncloseai](https://hermes.ai.unturf.com/) | 1 of 1 (100%) | 1 | 1 |
| [xkiro](https://xkiro.com) | 3 of 4 (75%) | 2 | 2 |
| [google](https://aistudio.google.com/apikey) | 2 of 3 (67%) | 3 | 3 |
| [openrouter](https://openrouter.ai/keys) | 2 of 6 (33%) | 3 | 3 |
| [aihubmix](https://aihubmix.com/) | not probed yet | 0 | 5 |
| [hetzner](https://console.hetzner.com/) | not probed yet | 0 | 2 |
| [inferx](https://model.inferx.net/) | not probed yet | 0 | 4 |
| [kenari](https://kenari.id/) | not probed yet | 0 | 5 |
| [mistral](https://console.mistral.ai/) | not probed yet | 0 | 4 |
| [siliconflow](https://siliconflow.com) | probed, no verdict yet: only 429 or 402 in the window | 1 | 1 |
| [unorouter](https://unorouter.com/) | not probed yet | 0 | 3 |
<!--/RELIABILITY-->

A `200` with no text in it counts as *not answered* here and as *alive* for the fourteen-day rule in
[GRAVEYARD.md](GRAVEYARD.md). Both are right for their question, and
[`bench/states.py`](bench/states.py) is the one place that says which is which.

---

## The five filters

| | Filter | Where it comes from |
|---|---|---|
| **1** | **Value = quality x volume x reliability** | the headline ranking |
| 2 | Quality | **imported** from official benchmarks, never our own |
| 3 | Volume | measured by us, declared with a source, or derived with the arithmetic shown |
| 4 | Needs a key, or not | no-key endpoints get a declared bonus |
| 5 | **What it costs you that is not money** | read from the provider's own terms |

### Why quality is imported and everything else is measured

Running a quality benchmark of our own does not scale: free providers appear weekly, and each would
have to go through a full battery before it could be listed at all. Worse, a benchmark run by whoever
publishes the ranking is exactly what a careful reader should distrust.

    imported   what the MODEL can do        <- Artificial Analysis, Design Arena
    measured   what the PROVIDER gives you  <- quota, uptime, auth, privacy

So a new provider costs nothing to rate. Serve `qwen3.8-27b` and it inherits that model's published
scores the day we add the endpoint. That is what makes this list able to keep up.

### The trap that costs you most: a `200` with nothing in it

A model that reasons can spend its **entire token budget thinking** and return an empty message, with
HTTP 200. The status code says success. There is no text. Your quota is gone and nothing looks wrong.

Every provider family takes a different switch, and some take none at all:

```
reasoning_effort: low                            gpt-oss on Groq, Cerebras, Ollama
chat_template_kwargs: {enable_thinking: false}   NVIDIA nemotron
enable_thinking: false                           Alibaba Qwen
thinking: {type: disabled}                       z.ai GLM
```

<!--TRAP-->
Measured in the archived run of 2026-09-06: **5 empty 200s, 4 of them on models where no switch was set.** We already set the switch for 12 of the models we call; those switches are in [`bench/providers.json`](bench/providers.json) and are the cheapest thing to copy out of this repo. The per-model list is in [RESULTS.md](RESULTS.md).
<!--/TRAP-->

### Filter 5: what it costs you that is not money

Free often means you are paying with your prompts. Google's terms say free-tier content is used to
"provide, improve, and develop Google products... and machine learning technologies", that "human
reviewers may read, annotate, and process your API input and output", and that the free tier may not be
used for apps serving users in the EEA, Switzerland or the UK. Quoted, not paraphrased:
[the full table is in RESULTS.md](RESULTS.md).

Most rows there say `UNKNOWN`, because nobody has read those terms yet. `UNKNOWN` is the honest
default: inventing a "no" is the most damaging wrong answer this repo could publish.

---

## What we measure, and what we refuse to guess

- **A row needs both halves to be ranked**: an official score AND a daily figure labelled MEASURED,
  DECLARED or DERIVED. The rest are listed separately with what is missing. Half a fact is not a rank,
  and a paid plan's number is not a free tier's.
- **Every row carries `measured_at`.** Free tiers die in months, not years: the providers on other
  people's lists that published their own retirement notices this summer are in
  [GRAVEYARD.md](GRAVEYARD.md) with the operator's sentence and what the endpoint returns now. A number
  with no date is a rumour.
- **A quota in tokens without the model it was measured on is a false number**, because some providers
  apply a per-model multiplier. We publish the model or nothing.
- **Quotas in proprietary units** ("100,000 ANY Tokens", "10 Neutrinos") are quoted as text, never
  converted into a number that would look comparable, unless the provider publishes the conversion on
  the same page, in which case the result is labelled DERIVED with the division shown.
- **Every published number is generated** by [`bench/rank.py`](bench/rank.py) from the data files, and
  [`bench/test_rank.py`](bench/test_rank.py) runs that generator against a fixture and compares the
  headline blocks byte for byte, so an edit that changes what a label means fails a test before it
  reaches this page.

## Endpoints that need no key at all

Rare, and worth more than their raw quality: no account, no card, no e-mail. The ranking pays them a
bonus for it. Most lists that advertise "no key" are quoting a page that stopped being true a while
ago, so every one here was called with no `Authorization` header before it was listed, and the day we
did it is recorded.

<!--KEYLESS-->
- **uncloseai**, [hermes.ai.unturf.com](https://hermes.ai.unturf.com/): `Lorbus/Qwen3.6-27B-int4-AutoRound` (called with no `Authorization` header on 2026-09-07).
- **ovhcloud**, [oai.endpoints.kepler.ai.cloud.ovh.net](https://oai.endpoints.kepler.ai.cloud.ovh.net/): `gpt-oss-120b`, `Qwen3.5-397B-A17B`, `Meta-Llama-3_3-70B-Instruct`, `Qwen3-Coder-30B-A3B-Instruct`, `Mistral-Small-3.2-24B-Instruct-2506`, `Qwen3.8-27B` (called with no `Authorization` header on 2026-09-07).
<!--/KEYLESS-->

## We read every other list first. Then we measured all of it again.

You already know these lists exist. [OmniRoute](https://github.com/diegosouzapw/OmniRoute) routes
across hundreds of providers, and `awesome-free-llm-apis` and seven more are catalogued in
[SOURCES.md](SOURCES.md), each credited for what it does well. We went through all of them line by
line. This is not a ninth copy of the same table: everything in here went through our own mill first,
and the mill is the product.

**Nothing here is copied.** Quality comes from official benchmarks, by attribution, because a benchmark
run by the people publishing the ranking is worth nothing. Everything else, whether the endpoint
answered today, what the quota really is, whether it takes a key, what it costs you in things that are
not money, we measure ourselves, and every number carries how we know it. UNKNOWN stays UNKNOWN. We
never fill a hole with someone else's number.

**What that catches, concretely.** OmniRoute's registry marks a set of endpoints as needing no key or
treating it as optional. Eight of those are ordinary HTTP APIs, and on 2026-09-07 we called all eight
with no `Authorization` header, exactly as a reader would:

| What we found | How many |
|---|---|
| Returned a real completion with no key | **1**: `hermes.ai.unturf.com`, now in the ranking |
| No key required, but the shared anonymous bucket was empty both times | **1**: OVHcloud, 2 requests a minute, now in the ranking |
| Answered `401`: the catalogue is public, the inference is not | 3 |
| Answered `402 Payment Required` | 3 |

So of the eight keyless endpoints we could call, one answered with text. That is not a criticism of
anyone: free endpoints close quietly, and a list nobody re-runs is a list that decays. It is the reason
this one gets re-run.

**And it is re-run every day.** A scheduled job re-reads the public catalogues, re-imports the official
scores, recomputes the ranking, applies the fourteen-day death rule, and commits the difference:
[`daily-catalog.yml`](.github/workflows/daily-catalog.yml), 06:17 UTC, no secrets, so it runs on your
fork too. The liveness probe needs API keys, so it runs where the keys are and appends to
[`data/uptime.jsonl`](data/uptime.jsonl), which is the history behind every `Answers` cell above. If a
day is missing, the file shows it missing.

---

## Bonus: how these models write a language that is not English

Before this became a ranking of endpoints, we ran our own benchmark of how well free models write
**Romanian**: four machine-checked probes and a blind jury of two judges from different model families.
It is no longer the headline, but it is still the only measurement anywhere of these models on a small
language, and the finding stands: they can all do arithmetic, and almost none of them can write.

The two judges correlated at **0.93** on whether the Romanian was correct and at **-0.07** on whether it
sounded human, so we publish that disagreement too.

Full run: [results/2026-09-06/](results/2026-09-06/) · method: [METHOD.md](METHOD.md) · judge
agreement: [agreement.md](results/2026-09-06/agreement.md)

---

## Run it yourself

```bash
python bench/scores.py --out data/scores.json --date $(date -u +%F)   # import official scores
python bench/rank.py --date $(date -u +%F) --out .                     # rebuild every table
python bench/test_rank.py                                              # the generator against its fixture
```

No API key needed for any of them: the scores come from a public endpoint and the test runs on a
fixture.

## Contributing

The most valuable pull request you can send is **reading one provider's terms and filling in filter 5**,
or **correcting a quota with its source**. Turning a wrong number into an honest `UNKNOWN` counts as a
real contribution here. See [CONTRIBUTING.md](CONTRIBUTING.md) and [SECURITY.md](SECURITY.md).

## Where all of this comes from

Every source, every repo we read, every provider page and every benchmark we evaluated and rejected,
with what we took from each and what we deliberately did not:
**[SOURCES.md](SOURCES.md)**.

## Licence

Code (`bench/`) under **MIT**. Data and tables under
**[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)**. Benchmark scores belong to their authors
and are attributed in [CREDITS.md](CREDITS.md).

Built by **[i-vory Studio](https://i-vory.studio)**.
