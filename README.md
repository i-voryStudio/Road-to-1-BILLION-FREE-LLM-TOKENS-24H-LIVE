# ROAD TO 1 BILLION FREE QUALITY LLM TOKENS / 24H

A live, measured list of every free LLM API we can find, ranked by what you can actually get done with
it: quality from official benchmarks, volume from response headers and pricing pages, and every figure
labelled by how we know it. Free here means no money spent, and a figure that needs a top-up first, or
that was read on a trial tier, says so wherever it is printed; quality here means an official coding
index at or above the floor printed under the table.

**Where the method comes from.** We take apart the biggest open routing and agent tools as they
ship, OmniRoute, Hermes Agent and Agent-Reach among them, and put every free endpoint they reach
for through our own meters. That research runs continuously; this list is the part of it a
stranger can check, which is why every figure here carries the day it was measured and the way it
was obtained.

## How far this is from a billion a day

<!--BARS-->
**Everything free, whatever the quality**  
`████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░`  **20.3%** of the target rate: **140,850 tokens a minute** measured across 11 of the 17 providers tested, against the 694,444 a minute that 1,000,000,000 a day works out to.

**Quality only, an official coding index at or above 45**  
`██░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░`  **6.0%** of the target rate: **41,995 tokens a minute** from 6 providers whose measured model clears the floor: aihubmix, inferx, kenari, openrouter, uncloseai, xkiro.

Both bars are **rates**, read in 30-second bursts, latest reading per provider, against the target converted to a rate. A rate held for thirty seconds is not a rate held for a day, so nothing here is multiplied into a day: the daily shelf further down is counted from published and measured daily figures only, and it is the conservative number.

### What they promise, and what arrived

| | |
|---|---|
| Advertised, if you take every per-minute ceiling times 1440, the way most lists do | **13,389,120,000 a day** |
| Advertised, counting only the daily figures providers actually publish | 7,975,000 a day |
| Measured by us and defensible today | **6,300,000 a day** |

The first row is their arithmetic, not ours, and it is here so you can see the size of it: **2,125 times** the last row, from the same 18 providers, on the same day. A per-minute ceiling is what a provider will refuse to exceed in any one minute, not a promise it will serve that rate for 1,440 minutes, and every provider on this list that we pushed for an hour proved the difference. The gap between the first row and the last is what this page is a list of.
<!--/BARS-->

## The five best free endpoints today

<!--TOP5-->
| # | Model | Provider | Value | Coding | Tokens/day | Volume | Answers | Cost | Get key |
|---|---|---|---|---|---|---|---|---|---|
| 1 | `minimax/minimax-m3:free` | xkiro | **234.4** | 58.6 | 5,000,000 | MEASURED | 2 of 2 in 14 days | - | [get a key](https://xkiro.com) |
| 2 | `qwen-3.8-27b` | cerebras | **224.8** | 68.1 | 1,000,000 | MEASURED; read on a free trial key; may be that tier's allowance, not a standing free tier | 2 of 2 in 14 days; returned an empty reply once in the archived run | - | [get a key](https://cloud.cerebras.ai) |
| 3 | `gemini-3.5-flash-lite` | google | **133.1** | 49.3 | 250,000 | DERIVED | 1 of 1 in 14 days | **trains on your prompts**; human review; region-restricted | [get a key](https://aistudio.google.com/apikey) |
| 4 | `minimax/minimax-m2.7:free` | xkiro | **105.2** | 52.6 | 5,000,000 | MEASURED | 1 of 2 in 14 days | - | [get a key](https://xkiro.com) |
| 5 | `minimax/minimax-m3:free` | openrouter | **100.1** | 58.6 | 25,000 | DERIVED | 2 of 2 in 14 days | - | [get a key](https://openrouter.ai/keys) |
<!--/TOP5-->

<!--QUALITY-->
**Quality has a number here: an official coding index of at least 45**, imported from Artificial Analysis and never run by us. The lowest-scoring endpoints that still clear it today, so you can see where the floor sits: `mistral-medium-3-5:free` at kenari (46.9), `gemini-3.5-flash-lite` at google (49.3), `nemotron-3-ultra-550b-a55b:free` at kenari (49.3), `nvidia/nemotron-3-ultra-550b-a55b:free` at openrouter (49.3). 10 ranked endpoints clear it; 22 scored endpoints sit under it and are listed in [RESULTS.md](RESULTS.md), never ranked, with none of their tokens on the bar.
<!--/QUALITY-->

**Value = quality x volume x how often it actually answers**, and the exact formula is printed on every
page, from the same constants the code runs on:

<!--FORMULA-->
`coding_index x log10(1 + daily_tokens / 500) x answered_rate x 1.25 if no key x 0.5 if degraded`
<!--/FORMULA-->

Volume is in **tokens**, not requests, because a request cap and a token cap are the same shelf in
different units and the smaller one is your real ceiling. Rows are sorted by value, highest first; a tie
is broken by provider name, then model id. **Volume** says how we know that figure, and a MEASURED figure
read on a tier that may not be the standing free tier says so in the same cell. **Answers** is the radar:
our own probe, one per endpoint per day, over the last 14 days; the 30-second burst and the 60-minute
draw are other instruments, and an endpoint the radar has not reached yet says `not on the radar yet`,
with what those instruments saw. **Cost** is what the free tier costs you that is not money plus anything
you must pay once to unlock it, and a `-` means nothing is on file yet, neither a privacy term read nor an
unlock condition. **Get key** is the provider's own sign-up page, or its documentation page where no key
is needed, checked against its API domain, or against a sign-up host or, for a keyless provider, a
documentation host declared in `bench/gate_contributions.py`, so it cannot point at a lookalike.

<!--EXAMPLE-->
The best coding score in the whole list, **76.3**, belongs to `gemini-3.8-flash`, `gemini-3.8-flash-free`, and the score alone decides nothing: at google it is not ranked: daily volume unknown: the 20 requests a day on the screen read 2026-09-06 belonged to gemini-3.7-flash; no daily figure for gemini-3.8-flash has been read - see LIMITS.md; at aihubmix it is not ranked: the daily figure exists only after a one-time $1 top-up, and free here means no money spent, so this row is listed under the ranking and never in it.
<!--/EXAMPLE-->

## Where this is going, out loud: one billion free tokens a day

<!--ROAD-->
**Roughly 6,300,000 quality tokens a day** is what this list can defend on 2026-09-19: 6,000,000 measured from response headers or usage endpoints (2 providers; cerebras: 1,000,000 read on a free trial key; may be that tier's allowance, not a standing free tier); nothing counted as published by a provider as a daily token figure; 300,000 derived from a published request cap at 500 tokens a reply or from the model's own published unit price (3 providers). The target is 1,000,000,000 a day by 2026-11-07, 158.7 times that. Nothing here is a burst multiplied out to a day.

*One measured hour is not a day.* alibaba drew 699,585 tokens in one measured hour on 2026-09-07. If that hour repeated 24 times it would be 16,790,040 a day, and nobody has measured that, so the figure is printed here and never added to the shelf. Drawn at a planned pace of 30 requests a minute and a realised 29.0 (624 launched over 22 minutes, at most 2 in flight) x 700 tokens a call: a floor for the hour measured, times 24, not their ceiling. The only free capacity here is a one-time grant of 1,000,000 tokens for this model, which at this rate lasts about 1.4 hours. hetzner drew 232,551 tokens in one measured hour on 2026-09-07. If that hour repeated 24 times it would be 5,581,224 a day, and nobody has measured that, so the figure is printed here and never added to the shelf. Drawn at a planned pace of 10 requests a minute and a realised 5.6 (338 launched over 60 minutes, at most 2 in flight) x 700 tokens a call: a floor for the hour measured, times 24, not their ceiling. kenari drew 29,236 tokens in one measured hour on 2026-09-07. If that hour repeated 24 times it would be 701,664 a day, and nobody has measured that, so the figure is printed here and never added to the shelf. Drawn at a planned pace of 5 requests a minute and a realised 2.2 (63 launched over 29 minutes, at most 2 in flight) x 700 tokens a call: a floor for the hour measured, times 24, not their ceiling. kenari also publishes a DERIVED daily figure, and that is the one on the shelf.

*Bursts are a different thing.* In 30-second bursts, latest reading per provider, **11 of the 17 providers measured handed us 140,850 tokens a minute** added together on 2026-09-07; 3 delivered nothing (hetzner: five failures in a row: no response: timeout or connection failure; mistral: rate limit reached; ovhcloud: rate limit reached); 3 measured with no rate to state (groq: five failures in a row: HTTP 403: the endpoint refused the caller; siliconflow: five failures in a row: HTTP 402: the endpoint stops serving until a top-up; unorouter: five failures in a row: HTTP 503: no capacity behind the endpoint); 1 provider has no burst row yet: google. A burst is a rate: 100,000 tokens a minute is a fact and 144,000,000 a day is a number nobody will be allowed to spend, so the bar above is built from the daily shelf and never from this rate. Free tiers move, throttle without warning and close; one provider here dropped 46-fold between two readings taken the same day. Nothing on this page is guaranteed to you by anyone, us included.

*What they allow.* The only output-only ceiling published (hetzner: 100,000 output tokens a minute) is 14% of the 694,444 a minute the target works out to. Ceilings published as input-plus-output, or without saying which, add up to 5,290,000 a minute across 3 providers (alibaba says in+out; google and siliconflow do not say which) and cannot be compared with an output target, so they are not.

*What it would take.* The shelf above is 6,300,000 tokens a day across 5 providers with any daily figure; the median figure among them is 250,000 a day. The gap to 1,000,000,000 is 993,700,000 a day, which is 3,975 more providers at that median. No provider publishes a per-minute ceiling at or above the 694,444 a minute the target works out to, counting the output ceiling where a split is published and the bare figure where it is not. The draw meter runs once, for 60 minutes, at the provider's published pace capped at 120 requests a minute, asking for 700 tokens a call and stopping at 250,000 tokens, and a run the cap stops states a rate only after 5 minutes, so the most it can register from one provider is 3,000,000 tokens an hour, 72,000,000 a day. A longer draw, a faster published pace, or more providers with a daily figure are the only things that move the bar; nothing else on this page will.
<!--/ROAD-->

<!--HEADLINE-->
| The daily shelf, one figure per provider | |
|---|---|
| **Tokens a day this list can defend** | **6,300,000** |
| measured by us from headers or usage endpoints | 6,000,000 (cerebras: 1,000,000 read on a free trial key; may be that tier's allowance, not a standing free tier) |
| published by the provider in tokens | 0 |
| derived from a published request cap at 500 tokens each, or the model's own published unit price | 300,000 |
| The target | 1,000,000,000 quality tokens a day by 2026-11-07 |
| **Share of it** | **0.6%** |
| Providers with a daily figure on this shelf | 5 of 18 |

| Per minute: a rate, never a day | |
|---|---|
| 30-second burst, per provider, latest reading, added up | 140,850 a minute |
| Providers that delivered anything in the burst | **11 of 17 measured** |
| measured, delivered nothing | hetzner (five failures in a row: no response: timeout or connection failure), mistral (rate limit reached), ovhcloud (rate limit reached) |
| measured, no rate to state | groq (five failures in a row: HTTP 403: the endpoint refused the caller), siliconflow (five failures in a row: HTTP 402: the endpoint stops serving until a top-up), unorouter (five failures in a row: HTTP 503: no capacity behind the endpoint) |
| no burst row yet | google |
| Endpoints answering today | **0 of 0 tested** |
| Output-only ceilings published, added up | 100,000 (hetzner) |
| Combined in+out ceilings, or unspecified, added up; never added to the row above | 5,290,000 (3 providers) |
| Providers with a free per-minute figure on file | 12 of 18 |

| Shown, and never counted above | |
|---|---|
| Published only for a PAID plan | 200,000 a day (groq) |
| Behind a payment before the free quota starts | 50,000 a day (aihubmix, after a one-time $1 top-up) |
| One measured hour x 24, never added to the shelf | 16,790,040 (alibaba, from 699,585 an hour), 5,581,224 (hetzner, from 232,551 an hour), 701,664 (kenari, from 29,236 an hour) |
| Once, at sign-up, in tokens | 1,000,000 per model (alibaba) |
| Once, at sign-up, in money | $6 |
| Monthly, in money | $10 (mistral) |
<!--/HEADLINE-->

<!--RANKING-HEAD-->
## The full ranking: all 10 ranked endpoints
<!--/RANKING-HEAD-->

<!--RANKING-->
| # | Model | Provider | Value | Coding | Tokens/day | Volume | Answers | Cost | Get key |
|---|---|---|---|---|---|---|---|---|---|
| 1 | `minimax/minimax-m3:free` | xkiro | **234.4** | 58.6 | 5,000,000 | MEASURED | 2 of 2 in 14 days | - | [get a key](https://xkiro.com) |
| 2 | `qwen-3.8-27b` | cerebras | **224.8** | 68.1 | 1,000,000 | MEASURED; read on a free trial key; may be that tier's allowance, not a standing free tier | 2 of 2 in 14 days; returned an empty reply once in the archived run | - | [get a key](https://cloud.cerebras.ai) |
| 3 | `gemini-3.5-flash-lite` | google | **133.1** | 49.3 | 250,000 | DERIVED | 1 of 1 in 14 days | **trains on your prompts**; human review; region-restricted | [get a key](https://aistudio.google.com/apikey) |
| 4 | `minimax/minimax-m2.7:free` | xkiro | **105.2** | 52.6 | 5,000,000 | MEASURED | 1 of 2 in 14 days | - | [get a key](https://xkiro.com) |
| 5 | `minimax/minimax-m3:free` | openrouter | **100.1** | 58.6 | 25,000 | DERIVED | 2 of 2 in 14 days | - | [get a key](https://openrouter.ai/keys) |
| 6 | `mimo-v2-5:free` | kenari | **97.0** | 56.8 | 25,000 | DERIVED | not on the radar yet; the provider answered the 30-second burst on 2026-09-07 with `nemotron-3-ultra-550b-a55b:free` | - | [get a key](https://kenari.id/) |
| 7 | `nemotron-3-ultra-550b-a55b:free` | kenari | **84.2** | 49.3 | 25,000 | DERIVED | not on the radar yet; answered the 30-second burst on 2026-09-07 | - | [get a key](https://kenari.id/) |
| 8 | `mistral-medium-3-5:free` | kenari | **80.1** | 46.9 | 25,000 | DERIVED | not on the radar yet; the provider answered the 30-second burst on 2026-09-07 with `nemotron-3-ultra-550b-a55b:free` | - | [get a key](https://kenari.id/) |
| 9 | `minimax/minimax-m2.7:free` | openrouter | **0.0** (no answer in 14 days, so no value) | 52.6 | 25,000 | DERIVED | 0 of 2 in 14 days | - | [get a key](https://openrouter.ai/keys) |
| 10 | `nvidia/nemotron-3-ultra-550b-a55b:free` | openrouter | **0.0** (no answer in 14 days, so no value) | 49.3 | 25,000 | DERIVED | 0 of 2 in 14 days | - | [get a key](https://openrouter.ai/keys) |
<!--/RANKING-->

### Listed, never ranked: the quota starts after a payment

Free here means no money spent. These endpoints publish a real recurring quota, and it begins
only once money has changed hands, so they are shown with the condition and left out of the
ranking and out of the daily shelf.

<!--UNLOCK-->
| Model | Provider | Coding | Tokens/day | Volume | What unlocks it | Get key |
|---|---|---|---|---|---|---|
| `gemini-3.8-flash-free` | aihubmix | 76.3 | 50,000 | DERIVED | a one-time $1 top-up | [get a key](https://aihubmix.com/) |
| `coding-kimi-k3-free` | aihubmix | 76.2 | 50,000 | DERIVED | a one-time $1 top-up | [get a key](https://aihubmix.com/) |
| `coding-glm-5.3-free` | aihubmix | 74.8 | 50,000 | DERIVED | a one-time $1 top-up | [get a key](https://aihubmix.com/) |
| `coding-minimax-m3-free` | aihubmix | 58.6 | 50,000 | DERIVED | a one-time $1 top-up | [get a key](https://aihubmix.com/) |
| `gemma-4-26b-a4b-it-free` | aihubmix | 39.3 | 50,000 | DERIVED | a one-time $1 top-up | [get a key](https://aihubmix.com/) |
<!--/UNLOCK-->

Every endpoint we track, ranked or not, scored or not: **[ALL-ENDPOINTS.md](ALL-ENDPOINTS.md)**. All the
tables, including quality alone and privacy cost: [RESULTS.md](RESULTS.md). Every rate limit with its
source and the date we read it: [LIMITS.md](LIMITS.md).

<!--COUNTS-->
18 providers and 63 endpoints are tracked. 10 endpoints are ranked; 53 are listed with what is missing. 35 endpoints have a radar verdict in the last 14 days, 5 were probed and only ever refused (429 or 402), and 23 are not on the radar yet. 7 endpoints need no key. 5 providers have a daily figure this list can defend; 13 have no figure this list can defend and are counted as nothing, each for the reason in its own data: aihubmix (has a DERIVED figure of 50,000 on `coding-glm-5.3-free`, and that model scores 74.8, under the quality floor of 45); alibaba (publishes only a one-time grant of 1,000,000 tokens per model); cloudflare (has a DERIVED figure of 48,826 on `@cf/meta/llama-3.3-70b-instruct-fp8-fast`, and that model scores 11.9, under the quality floor of 45); groq (publishes a daily figure only for a paid plan); hetzner (publishes only a per-minute ceiling); inferx (publishes no figure at all); mistral (publishes only a monthly grant of $10 in credits); nvidia (publishes no figure at all); ollama (publishes only a monthly grant, size not published); ovhcloud (publishes only a per-minute ceiling); siliconflow (publishes only a one-time grant of $1 in credits); uncloseai (publishes only a per-minute ceiling); unorouter (publishes only a per-minute ceiling).
<!--/COUNTS-->

---

## How to read any row of this list

Five things decide whether a free API is worth your time, and every list we have seen collapses them
into one number. They are kept apart here on purpose.

**0. What we received, versus what they allow.** The Received column of the provider table is the only one
on any list like this that nobody has to take on trust: real requests, sent in parallel for a window
of about thirty seconds with a small token budget, counting the output tokens that came back.
`bench/throughput.py` does it and the raw readings are in
[`data/throughput.jsonl`](data/throughput.jsonl). It is a **floor**: the test stops early when the
provider's own rate limit stops it, and then the number reported is the whole minute's allowance rather
than a rate scaled up from two seconds; requests already in flight are allowed to finish, which is why a
row can show up to a minute. A `0` means we got nothing, and the `Why 0` column says what the endpoint
returned instead. The probe behind the Answers column, this burst meter and the 60-minute draw behind
the DRAWN label all run on the same visit, once every fourteen days, from one machine that holds the
keys; the CI job never holds a key and only checks and regenerates. Fourteen days is a deliberate
choice: a free endpoint that has to be re-tested more often than that is not stable enough to plan
with, and the cost of testing it is real.

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
the provider's sign-up page was read and does not say, and we will not guess on your behalf; `not read`
means nobody has read that provider's sign-up page yet, which is a different fact.

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
| **DRAWN** | tokens actually pulled over a 60-minute draw at the provider's published pace. One measured hour is a fact; the same hour twenty-four times over is not, so the day it would make is printed with that condition attached and never added to the shelf |
<!--/LABELS-->

### Every provider, and what it actually gives you

Per minute first, because that is the unit this market publishes in; then the daily shelf, then the
grants. `-` means they publish nothing on that shelf, and nothing is what we write. Where a provider
publishes per-model ceilings, the largest is shown and the cell says so.

<!--CAPACITY-->
| Provider | Received /min, 30 s burst | Why 0 | Allow /min | Req/min | Per day | How we know | Monthly | Once | Key | Card | Phone |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **[alibaba](https://modelstudio.console.alibabacloud.com)** | 54,659 |  | 5,000,000 in+out (per model, largest) | 600 | - | UNKNOWN | - | 1,000,000 tokens per model | yes | ? | **yes** |
| **[cloudflare](https://dash.cloudflare.com/profile/api-tokens)** | 27,670 |  | - | 300 | - | UNKNOWN | - | - | yes | no | no |
| **[inferx](https://model.inferx.net/)** | 22,005 |  | - | - | - | UNKNOWN | - | - | yes | ? | ? |
| **[nvidia](https://build.nvidia.com)** | 13,470 |  | - | - | - | UNKNOWN | - | - | yes | ? | ? |
| **[openrouter](https://openrouter.ai/keys)** | 7,997 |  | - | 20 | 25,000 | DERIVED | - | - | yes | not read | not read |
| **[aihubmix](https://aihubmix.com/)** | 7,048 |  | - | 10 | 50,000 | DERIVED, not counted: the quota starts after a one-time $1 top-up | - | - | yes | no | no |
| **[kenari](https://kenari.id/)** | 2,799 |  | - | 5 | 25,000 | DERIVED | - | - | yes | no | no |
| **[ollama](https://ollama.com/settings/keys)** | 1,850 |  | - | - | - | UNKNOWN | size not published | - | yes | ? | ? |
| **[xkiro](https://xkiro.com)** | 1,446 (was 66,197) |  | - | - | 5,000,000 | MEASURED | - | - | yes | not read | not read |
| **[cerebras](https://cloud.cerebras.ai)** | 1,206 |  | - | 5 | 1,000,000 | MEASURED; read on a free trial key; may be that tier's allowance, not a standing free tier | - | $5 in credits | yes | not read | not read |
| **[uncloseai](https://ai.unturf.com)** | 700 |  | - | 180 | - | UNKNOWN | - | - | **no key** | no | no |
| **[google](https://aistudio.google.com/apikey)** | - | not measured yet | 250,000, scope unspecified (per model, largest) | 15 | 250,000 | DERIVED | - | - | yes | not read | not read |
| **[hetzner](https://console.hetzner.com/)** | 0 | five failures in a row: no response: timeout or connection failure; the same day's 60-minute draw at a planned 10 requests a minute received 333 replies of up to 700 tokens, which is where the drawn hour comes from and is not on the shelf | 4,000,000 in / 100,000 out | 10 | - | UNKNOWN | - | - | yes | or ID | optional |
| **[siliconflow](https://siliconflow.com)** | - | no rate: HTTP 402: the endpoint stops serving until a top-up | 40,000, scope unspecified | 1,000 | - | UNKNOWN | - | $1 in credits | yes | ? | ? |
| **[groq](https://console.groq.com/keys)** | - | no rate: HTTP 403: the endpoint refused the caller | 8,000, scope unspecified (per model, largest), PAID-PLAN | 30 | - | PAID-PLAN, not counted | - | - | yes | not read | not read |
| **[mistral](https://console.mistral.ai/)** | 0 | rate limit reached | - | - | - | UNKNOWN | $10 in credits | - | yes | no | ? |
| **[ovhcloud](https://docs.ovhcloud.com/en/guides/public-cloud/ai-machine-learning/ai-endpoints-capabilities)** | 0 | rate limit reached | - | 2 | - | UNKNOWN | - | - | **no key** | **yes** | ? |
| **[unorouter](https://unorouter.com/)** | - | no rate: HTTP 503: no capacity behind the endpoint | - | 1 | - | UNKNOWN | - | - | yes | no | ? |
<!--/CAPACITY-->

**A ceiling you saw once is not a ceiling.** Mistral's free tier answered one of our calls with a
tokens-per-minute limit header reading 625,000, the largest figure we have measured anywhere. Half an
hour later, five readings a minute apart all carried a requests-per-minute limit header of zero and every
call was refused with HTTP 429. Their pricing page explains it: the free plan is $10 a month in credits,
so the ceiling is a monthly pot, not a rate, and a limit header of zero is what that pot looks like from
the outside for the rest of the month. That is why
the 625,000 is recorded with its timestamps in [`bench/limits.json`](bench/limits.json) and published as
a monthly grant rather than as a per-minute ceiling.

**Most of the good ones publish a ceiling per minute and no daily figure at all.** Hetzner's free
inference documents 4,000,000 input and 100,000 output tokens per 60 seconds, and no daily row exists
on their page; we read the raw HTML to be sure, because other lists quote a 24-hour row that is not
there. Counting a provider like that as zero, which a daily-only total does, understates this list, so
that per-minute ceiling gets its own line, on its own terms, and the ceiling is never multiplied out into
a day. What a provider like that gets instead is a DRAWN line: what a 60-minute draw at its published
pace actually returned, printed with the day it would make if that hour repeated 24 times, and with the
condition said in the same sentence. That line is never added to the daily shelf, because one measured
hour multiplied by 24 is the same arithmetic this page refuses everywhere else, and it is reconciled on
the same row with what the 30-second burst received the same day.

<!--BAR-->
**The daily shelf is the only thing the bar is built from, and it is an undercount by construction.** One figure per provider, the largest among its models that clear the quality floor of 45, and only three of the six labels may be on it: MEASURED, DECLARED and DERIVED. PAID-PLAN, UNKNOWN and DRAWN are shown and never counted, and a provider that publishes nothing counts as nothing. The shelves are separated by code, in [`data/capacity.json`](data/capacity.json), and the legend above says what each label means.
<!--/BAR-->

Asking a provider directly beats reading its marketing page: the largest measured figure on the shelf
sits behind a usage endpoint nobody had thought to call.

## And a quota you cannot draw on is not a quota

One probe per endpoint per visit, once every fourteen days, appended to
[`data/uptime.jsonl`](data/uptime.jsonl). The rate over the last fourteen days multiplies into the
ranking, per endpoint, so each endpoint carries one or two probes in the window and the cell prints how
many days are actually on file. An endpoint that dies the day after a visit is listed as answering for
up to two weeks: that is the price of not hammering free tiers, and the date on every row says when it
was last true. A provider that refuses a
third of your calls is worth a third less than its paper number, and ranking on advertised figures
alone rewards whoever advertises hardest. An endpoint the radar has not reached yet is not penalised: we do
not punish what we did not test, and the table says `not on the radar yet` rather than pretending, with
what the burst or the draw saw where one of them got an answer.

<!--RELIABILITY-->
| Provider | Answered, last 14 days | Endpoints with a verdict | Endpoints probed | Endpoints tracked |
|---|---|---|---|---|
| [alibaba](https://modelstudio.console.alibabacloud.com) | 8 of 8 (100%) | 4 | 4 | 4 |
| [cerebras](https://cloud.cerebras.ai) | 6 of 6 (100%) | 3 | 3 | 3 |
| [cloudflare](https://dash.cloudflare.com/profile/api-tokens) | 10 of 10 (100%) | 5 | 5 | 5 |
| [groq](https://console.groq.com/keys) | 8 of 8 (100%) | 4 | 4 | 4 |
| [nvidia](https://build.nvidia.com) | 10 of 10 (100%) | 5 | 5 | 5 |
| [ollama](https://ollama.com/settings/keys) | 6 of 6 (100%) | 3 | 3 | 3 |
| [ovhcloud](https://docs.ovhcloud.com/en/guides/public-cloud/ai-machine-learning/ai-endpoints-capabilities) | 2 of 2 (100%) | 2 | 6 | 6 |
| [uncloseai](https://ai.unturf.com) | 1 of 1 (100%) | 1 | 1 | 1 |
| [xkiro](https://xkiro.com) | 3 of 4 (75%) | 2 | 2 | 2 |
| [google](https://aistudio.google.com/apikey) | 2 of 3 (67%) | 3 | 3 | 3 |
| [openrouter](https://openrouter.ai/keys) | 2 of 6 (33%) | 3 | 3 | 3 |
| [aihubmix](https://aihubmix.com/) | not on the radar yet; answered the 30-second burst on 2026-09-07 | 0 | 0 | 5 |
| [hetzner](https://console.hetzner.com/) | not on the radar yet; answered the 60-minute draw on 2026-09-07 | 0 | 0 | 2 |
| [inferx](https://model.inferx.net/) | not on the radar yet; answered the 30-second burst on 2026-09-07 | 0 | 0 | 4 |
| [kenari](https://kenari.id/) | not on the radar yet; answered the 30-second burst on 2026-09-07 | 0 | 0 | 5 |
| [mistral](https://console.mistral.ai/) | not on the radar yet | 0 | 0 | 4 |
| [siliconflow](https://siliconflow.com) | probed, no verdict yet: only 429 or 402 in the window | 0 | 1 | 1 |
| [unorouter](https://unorouter.com/) | not on the radar yet | 0 | 0 | 3 |
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

- **A row needs both halves to be ranked**: an official score at or above the quality floor AND a daily
  figure carrying a label the legend above marks as rankable. The rest are listed separately with what is
  missing. Half a fact is not a rank, and a paid plan's number is not a free tier's.
- **Every row carries `measured_at`.** Free tiers die in months, not years: the providers on other
  people's lists whose retirement was announced this summer are in [GRAVEYARD.md](GRAVEYARD.md) with the
  notice's sentence, who wrote it (the operator, or a third party reporting on the operator), and what
  the endpoint returns now. A number with no date is a rumour.
- **A quota in tokens without the model it was measured on is a false number**, because some providers
  apply a per-model multiplier. We publish the model or nothing: a figure derived from another model's
  unit price is never printed for a model whose own price is not on file, and that model's volume stays
  UNKNOWN until someone reads its price.
- **Quotas in proprietary units** ("100,000 ANY Tokens", "10 Neutrinos") are quoted as text, never
  converted into a number that would look comparable, unless the provider publishes the conversion on
  the same page, in which case the result is labelled DERIVED with the division shown.
- **Every published number is generated** from the data files: [`bench/rank.py`](bench/rank.py) writes
  the ranking pages and [`bench/gate_viability.py`](bench/gate_viability.py) writes
  [GRAVEYARD.md](GRAVEYARD.md). [`bench/test_rank.py`](bench/test_rank.py) runs the generator against a
  fixture and compares the headline blocks byte for byte, then recomputes the committed pages from the
  committed data with arithmetic of its own, so an edit that changes what a label means, or a multiplier
  slipped in for one provider, fails a test before it reaches this page.

## Endpoints that need no key at all

Rare, and worth more than their raw quality: no account, no card, no e-mail. The ranking pays them a
bonus for it. Most lists that advertise "no key" are quoting a page that stopped being true a while
ago, so every one here was called with no `Authorization` header before it was listed, and the day we
did it is recorded.

<!--KEYLESS-->
- **uncloseai**, [hermes.ai.unturf.com](https://ai.unturf.com): `Lorbus/Qwen3.6-27B-int4-AutoRound` (called with no `Authorization` header on 2026-09-07). Today: 0 of 1 endpoint ranked; unranked because daily volume unknown - see LIMITS.md (1).
- **ovhcloud**, [oai.endpoints.kepler.ai.cloud.ovh.net](https://docs.ovhcloud.com/en/guides/public-cloud/ai-machine-learning/ai-endpoints-capabilities): `gpt-oss-120b`, `Qwen3.5-397B-A17B`, `Meta-Llama-3_3-70B-Instruct`, `Qwen3-Coder-30B-A3B-Instruct`, `Mistral-Small-3.2-24B-Instruct-2506`, `Qwen3.8-27B` (called with no `Authorization` header on 2026-09-07). Today: 0 of 6 endpoints ranked; unranked because below the quality floor: coding index 11.9, the floor is 45 (1); below the quality floor: coding index 30.4, the floor is 45 (1); daily volume unknown - see LIMITS.md (2); no official benchmark score published for this model (2).
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
treating it as optional. The ones this list tracks were each called with no `Authorization` header before
they were listed, and the radar calls them again every day; an entry from those catalogues that answers a
keyless call with a demand for a credential or for payment is not listed and not counted, because a
public catalogue is not a free inference API. What the radar sees, from its own file rather than from a
tally typed by hand:

<!--KEYLESS-RADAR-->
What the radar's own file says about the keyless endpoints this list tracks, latest row per endpoint (2026-09-07), every call sent with no `Authorization` header: uncloseai, 1 tracked endpoint: 1 answered with text (HTTP 200); ovhcloud, 6 tracked endpoints: 2 answered with text (HTTP 200); 4 answered HTTP 429: rate limited. The file is [`data/uptime.jsonl`](data/uptime.jsonl); a `200` with no text counts as not answered here, and `bench/states.py` says why.
<!--/KEYLESS-RADAR-->

That is not a criticism of anyone: free endpoints close quietly, and a list nobody re-runs is a list that
decays. It is the reason this one gets re-run.

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
python bench/scores.py --out /tmp/scores-new.json --date $(date -u +%F)   # import official scores to a temp file
python bench/gate_drift.py --previous data/scores.json --current /tmp/scores-new.json --apply --date $(date -u +%F)   # the drift gate applies them, or refuses
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
