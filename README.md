# Free LLM APIs, Rated by Quality and Volume

**33 free models from 10 providers, put through the same four machine-checked probes and a blind
three-lens jury — in Romanian, not English.**

Every other free-LLM list ranks by rate limit. They tell you how many requests you get. None of them
tells you whether the model can produce a paragraph you would actually publish. So we measured that.

**Every one of them can do the arithmetic. Almost none of them can write.**

| Probe | Passed |
|---|---|
| Arithmetic with one correct answer | **29 / 29** |
| Rewrite with correct diacritics | **27 / 29** |
| JSON extraction, right keys and types | **22 / 27** |
| A paragraph usable at all (checker allows 70-140 words) | **23 / 30** |
| A paragraph inside the 90-110 words actually asked for | **14 / 30** |
| Scored above 7/10 on *"sounds like a person wrote it"* | **1 / 23** |

The curve falls the moment the task stops being mechanical. On the blind jury's "sounds human" lens the
mean across 23 models is **3.5 out of 10**, and exactly one model clears 7. That is the number no
rate-limit table can show you.

Run on **6 September 2026**. Script, prompts, raw answers and every jury score are in this repo. Nothing here is
copied from a provider's documentation without being labelled `DECLARED`.

---

## Why this exists

There are at least eight of these lists. We read all of them before writing this one. They publish
roughly the same five columns: context window, max output, modality, rate limit, credit card yes/no.

The good ones verify **availability**: [mnfst](https://github.com/mnfst/awesome-free-llm-apis) states
that every row answered a live request inside a dated window;
[12britz](https://github.com/12britz/awesome-free-models) re-checks hundreds of URLs and publishes the
failures too. That is real work and it is genuinely useful.

But none of them measures **quality**, and none of them tests in any language other than English. Where
quality scores appear at all, they are links to somebody else's leaderboard, or benchmark numbers copied
out of the provider's own launch post.

That is the gap. A rate limit tells you how often you may call a model. It does not tell you that the
model will answer in cedillas, return `89.9` when the text said `89.900`, or hand you 381 words when you
asked for 100. All three happened during this run.

### Why Romanian

Because it is where models fail in ways an English benchmark cannot see. A model that reasons perfectly
in English will confidently emit `ş` (cedilla, from an old Turkish-alphabet mapping) where Romanian
requires `ș` (comma below). A native reader clocks it instantly; a benchmark scored in English never
sees it at all.

This is the repo's strength and its honest limit. Romanian is one language, and our numbers are Romanian
numbers. The fix is not for us to guess about yours — it is for the probes to live in a JSON file
anybody can copy. See **[Add your language](bench/languages/README.md)**.

---

## Results

Full tables: **[RESULTS.md](RESULTS.md)** · Rate limits with sources: **[LIMITS.md](LIMITS.md)** ·
Method and its weaknesses: **[METHOD.md](METHOD.md)** · Machine-readable:
[`data/models.json`](data/models.json), [`data/models.csv`](data/models.csv)

### Top 10 by quality

| # | Model | Provider | Quality | Probes | human / language / brief | Req/day | Evidence | Speed |
|---|---|---|---|---|---|---|---|---|
| 1 | `gemini-3.5-flash-lite` | google | **9.2** | 4/4 | 6 / 9 / 10 | 500 | DECLARED | 0.8 s |
| 2 | `qwen3.5-flash` | alibaba | **9.0** | 4/4 | 5 / 9 / 10 | ? | UNKNOWN | 1.5 s |
| 3 | `minimax/minimax-m3:free` | openrouter | **8.5** | 4/4 | 7 / 10 / 4 | 50 | DECLARED | 3.5 s |
| 4 | `minimax/minimax-m2.7:free` | xkiro | **8.5** | 4/4 | 3 / 8 / 10 | ? | UNKNOWN | 16.4 s |
| 5 | `minimax/minimax-m2.7:free` | openrouter | **8.5** | 4/4 | 3 / 8 / 10 | 50 | DECLARED | 20.4 s |
| 6 | `openai/gpt-oss-20b` | groq | **8.3** | 4/4 | 3 / 7 / 10 | 1,000 | PAID-PLAN | 0.4 s |
| 7 | `@cf/openai/gpt-oss-120b` | cloudflare | **8.3** | 4/4 | 2 / 8 / 10 | ? | UNKNOWN | 5.2 s |
| 8 | `openai/gpt-oss-120b` | groq | **8.2** | 4/4 | 3 / 7 / 9 | 1,000 | PAID-PLAN | 0.5 s |
| 9 | `gemma-4-31b` | cerebras | **7.8** | 4/4 | 3 / 5 / 9 | 2,400 | MEASURED | 0.4 s |
| 10 | `gemma4:31b` | ollama | **7.8** | 4/4 | 3 / 5 / 9 | ? | UNKNOWN | 0.8 s |

*Jury columns are 0-10 on three separate lenses. `Evidence` says how we know the requests-per-day figure: MEASURED by us, DECLARED by the provider, **PAID-PLAN** when the only published number belongs to a paid tier rather than the free one, UNKNOWN when nobody publishes it. Most free tiers fall in that last bucket — which is itself the finding.*

All 30 ranked models, the 7 that never reached the jury, and the 3 that never answered: **[RESULTS.md](RESULTS.md)**.

---|---|---|---|---|---|---|---|---|
| 1 | `gemini-3.5-flash-lite` | google | **9.2** | 4/4 | 6 / 9 / 10 | 500 | DECLARED | 0.8 s |
| 2 | `qwen3.5-flash` | alibaba | **9.0** | 4/4 | 5 / 9 / 10 | ? | UNKNOWN | 1.5 s |
| 3 | `minimax/minimax-m3:free` | openrouter | **8.5** | 4/4 | 7 / 10 / 4 | 50 | DECLARED | 3.5 s |
| 4 | `minimax/minimax-m2.7:free` | xkiro | **8.5** | 4/4 | 3 / 8 / 10 | ? | UNKNOWN | 16.4 s |
| 5 | `minimax/minimax-m2.7:free` | openrouter | **8.5** | 4/4 | 3 / 8 / 10 | 50 | DECLARED | 20.4 s |
| 6 | `openai/gpt-oss-20b` | groq | **8.3** | 4/4 | 3 / 7 / 10 | 1,000 | DECLARED | 0.4 s |
| 7 | `@cf/openai/gpt-oss-120b` | cloudflare | **8.3** | 4/4 | 2 / 8 / 10 | ? | UNKNOWN | 5.2 s |
| 8 | `openai/gpt-oss-120b` | groq | **8.2** | 4/4 | 3 / 7 / 9 | 1,000 | DECLARED | 0.5 s |
| 9 | `gemma-4-31b` | cerebras | **7.8** | 4/4 | 3 / 5 / 9 | 2,400 | MEASURED | 0.4 s |
| 10 | `gemma4:31b` | ollama | **7.8** | 4/4 | 3 / 5 / 9 | ? | UNKNOWN | 0.8 s |

*Jury columns are 0-10 on three separate lenses. `Evidence` is how we know the requests-per-day figure — MEASURED by us, DECLARED by the provider, UNKNOWN if nobody publishes it. **19 of 30 models have no published daily limit at all**, which is itself the finding: most free tiers do not tell you what you get.*

All 30, plus the three that never answered and why: **[RESULTS.md](RESULTS.md)**.

---

## Three things we found that no list prints

**1. Groq's public rate-limit table is the Developer plan, not the free tier.** The page says it: *"the
limits shown below are the base limits for the Developer plan"*. Free-tier values are not published
anywhere public. Lists that reprint 1,000 requests/day as a free-tier number are reprinting a paid
plan's figure.

**2. The limit that stops you at Groq is tokens, not requests.** 8,000 tokens per minute against 1,000
requests per day. An article-length prompt returns 413 long before request count matters. Groq's own
docs make the point — *"you can hit any limit type depending on which threshold you reach first"* — and
the token column is the one the lists leave out.

**3. Catalogues rot in hours, not months.** We read OpenRouter's public model list twice on one
afternoon. Between the two readings `z-ai/glm-5.2:free` disappeared: 431 models and 19 free became 430
and 18. Both readings, with every model id, are in
[`results/2026-09-06/openrouter-catalogue-drift.md`](results/2026-09-06/openrouter-catalogue-drift.md),
and you can reproduce it with one `curl`. This is why [`data/catalog.json`](data/catalog.json) is
regenerated daily by CI — a table hand-written in August is fiction by October.

A fourth, about our own numbers: **rate limits are per organization or per project at most providers.**
Groq's docs: *"Rate limits apply at the organization level, not individual users."* Google's are per
project. So a second API key raises nothing. You will not find a multiplied figure anywhere in this
repo, and the publication gate rejects one if anybody tries to add it.

---

## The four probes

Full text in [`bench/languages/ro.json`](bench/languages/ro.json), exactly as sent.

| Probe | Decided by | What it catches |
|---|---|---|
| **A. Arithmetic** | code | A percentage, and whether "answer with only the numbers" is obeyed. Every model that answered got it right, 29/29 — which is exactly why the probe earns its place: it establishes that what fails later is not competence. |
| **B. Rewrite with diacritics** | code | The writing-system trap. At least four correct diacritics, and **zero** cedillas. Separates models trained on edited Romanian from models trained on scraped Romanian. |
| **C. JSON extraction** | code, via a real parser | Right keys, right types. One model returned `"unitati": 89.9` for **89.900** — valid JSON, wrong by a factor of a thousand. |
| **D. Paragraph, 90–110 words** | code, then a blind jury | Whether it can write publishable prose to a length. The prompt asks for 90-110 words; the checker allows 70-140, so the score is generous about length and the README reports both numbers. Run three times, majority verdict. |

```
quality            = 50% × (probes passed / 4 × 10)  +  50% × (jury mean over 3 lenses)
quality_for_agents = the same, minus the "sounds human" lens
```

Two numbers because they answer different questions. A model that writes stiff but correct prose is
useless for a blog post and perfectly good for an extraction step, and one number would hide that.

**The jury is a language model, which is a conflict of interest.** We cannot remove it, so we expose it:
the judge is named in the results, and every judged paragraph is published. `judge.py --export` hands
you the anonymised corpus and the exact prompts so you can re-judge the lot with a different model. If
your jury disagrees with ours, [open an issue with your numbers](CONTRIBUTING.md) — that is a better
outcome for this repo than agreement. The mechanical half of every score needs no jury at all.

---

## What this does NOT measure

- **One day.** A dated snapshot. Providers change models under the same name.
- **One prompt per probe.** This measures instruction-following on a specific instruction — which is what
  you get in production — not capability in general.
- **One language.** Ours. A model that scores badly here may be excellent in English.
- **Not reasoning, code, long context or tool use.** Four narrow probes. Better benchmarks exist for the rest.
- **n=1 on probes A–C.** Only the paragraph is repeated. One 429 at the wrong moment shows up as a
  failure: NVIDIA's `kimi-k3` answered in 13 seconds in an earlier run and timed out repeatedly in this
  one. Both facts are in the repo, neither is hidden.

The long version, with the failure modes of the method itself, is in [METHOD.md](METHOD.md).

---

## Run it yourself

```bash
export GROQ_API_KEY=...          # any subset — providers with no key are skipped, not failed
python bench/benchmark.py --out results.json --language ro
python bench/judge.py results.json --export judged/    # writes the anonymised paragraphs + prompts
#   ...judge them with any model, save the scores as jury.json in the shape of results/2026-09-06/jury.json
#   or skip the jury entirely and let rank.py score the mechanical half alone:
python bench/rank.py results.json --date $(date -u +%F) --out .          # no jury
python bench/rank.py results.json --jury jury.json --date $(date -u +%F) --out .   # with one
```

20–60 minutes, mostly waiting on the slowest providers. Each runs in its own thread with its own pacing.
No dependencies beyond the Python standard library.

```bash
python bench/test_probes.py      # checkers, offline, both directions. Must exit 0.
python bench/gate_publish.py .   # blocks keys, account state, private paths. Must exit 0.
```

---

## Add your language

A language pack is one JSON file: four prompts, the pass conditions, three jury questions. The guide is
**[bench/languages/README.md](bench/languages/README.md)**, and it walks through finding the
writing-system trap that makes probe B worth running for your language — the German ß, Greek Latin
lookalikes, Vietnamese tone marks, full-width punctuation in Japanese.

Covered so far: **Romanian** (`ro`), **English** (`en`, control set).

---

## The other lists, and what each does better than us

Genuinely useful, all of them. We are one column they do not have, not a replacement.

| Repo | Stars | What it does better |
|---|---|---|
| [tashfeenahmed/freellmapi](https://github.com/tashfeenahmed/freellmapi) | 24.5k | Not a list — installable software that routes across 34 providers behind one endpoint. Different thing entirely. |
| [mnfst/awesome-free-llm-apis](https://github.com/mnfst/awesome-free-llm-apis) | 7.4k | Verifies every row against a live request inside a dated window. Far more providers than we test. |
| [open-free-llm-api/awesome-freellm-apis](https://github.com/open-free-llm-api/awesome-freellm-apis) | 2.8k | 134+ APIs from 40+ providers, refreshed daily, with one-click config snippets. The best pure catalogue. |
| [12britz/awesome-free-models](https://github.com/12britz/awesome-free-models) | 2.1k | Re-checks hundreds of endpoints and publishes the failures, not just the successes. Honest in the way that costs work. |
| [nejib1/Free-LLM](https://github.com/nejib1/Free-LLM) | 361 | Credit-card transparency per provider, and ready-to-run code per entry. |
| [amardeeplakshkar/awesome-free-llm-apis](https://github.com/amardeeplakshkar/awesome-free-llm-apis) | 158 | Permanent-free only: no trial credits, no time-limited promos. A stricter definition than ours. |
| [raullenchai/free-llm-api-resources](https://github.com/raullenchai/free-llm-api-resources) | — | Keeps alive the fork of `cheahjs/free-llm-api-resources`, the original, which now 404s. |
| [zukixa/cool-ai-stuff](https://github.com/zukixa/cool-ai-stuff) | 1.2k | Was thorough. Last updated October 2025 — included as the cautionary tale for what this repo becomes without maintenance. |

---

## Licence

Code (`bench/`) under **MIT**. Data and tables (`data/`, `RESULTS.md`, `LIMITS.md`) under
**[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)** — use them anywhere, with a link back.

Built by **[i-vory Studio](https://i-vory.studio)**, because we needed to know which free models could
write Romanian well enough to ship, and no list would tell us.
