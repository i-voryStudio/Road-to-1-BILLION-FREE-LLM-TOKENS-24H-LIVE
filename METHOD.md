# Method

Every number in this repo comes from here. If you think a score is wrong, this page is where to attack it.

## The short version

Each model gets four probes. Three are decided by code, one by a blind jury.

```
quality            = 50% * (probes passed / answered * 10)  +  50% * (mean jury score across 3 lenses)
quality_for_agents = the same, with the "sounds human" lens removed from the jury mean
```

A model whose paragraph failed the mechanical check never reaches the jury, so it has no second half.
It does **not** get half a score on this scale — that would be a silent zero on the jury half. It gets
its mechanical score out of 10, is flagged `scale: "probes only"`, and is listed in its own section of
RESULTS.md. A probes-only number and a probes-plus-jury number are two different measurements, and
averaging them into one ranking would be exactly the sort of quiet dishonesty this method is built to
avoid.

## The four probes

The prompts live in [`bench/languages/ro.json`](bench/languages/ro.json), verbatim, in the form they
were sent. Not paraphrased for the README — the file the script reads is the file you can read.

### A. Arithmetic with one correct answer

> An annual subscription costs 96,000 euro. The discount is 15%. What is the discount and what is left
> to pay? Answer with ONLY the two amounts, as whole numbers, separated by a comma, no other text.

Passes if both `14400` and `81600` appear. Two things fail here, and only one of them is arithmetic:
models that get the sum wrong, and models that cannot resist adding an explanation after being told not
to. Both are real failures for anyone piping output into another program.

The checker has to tell a list separator from a thousands separator — `14400, 81600` is two numbers,
`14,400` is one. It decides by grouping width: a separator only counts as thousands if exactly three
digits follow. Both directions are pinned in [`bench/test_probes.py`](bench/test_probes.py), because
getting this wrong silently rewrites the entire table. It did, twice, while this was being built.

### B. Rewrite with the writing system enforced

The model rewrites one sentence with correct Romanian diacritics. Passes if it emits at least four of
`ă â î ș ț`, keeps a required word, stays within a length window, and — the part that does the work —
emits **zero** cedilla characters `ş ţ`.

Romanian s and t take a comma below (U+0219, U+021B). The cedilla forms (U+015F, U+0163) come from an
old Turkish-alphabet mapping and are simply wrong, but they are everywhere in training data, so models
mix them in constantly. A Romanian reader sees it immediately. This single check separates models that
have actually seen edited Romanian from models that have seen scraped Romanian.

### C. JSON extraction

Extract five fields from one sentence, numbers as numbers, no prose, no code fence. The answer is fed to
a real JSON parser and every key compared by value and type. `"module": "2"` fails: the prompt said
numbers as numbers, and a string there breaks whatever consumes it.

The most instructive failure in our run: a model returned `"unitati": 89.9` for **89.900**, reading the
Romanian thousands separator as a decimal point. It produced perfectly valid JSON with a value wrong by
a factor of a thousand — exactly the kind of error that survives a schema check and reaches production.

### D. Paragraph, 90 to 110 words

The prompt asks for 90 to 110 words. The checker accepts **70 to 140**, deliberately: a model that
writes 88 words of good Romanian has not failed at writing, it has failed at counting, and those are
worth separating. The consequence is that "23 of 30 produced a usable paragraph" is a generous
reading — only 14 of those 23 landed inside the 90-110 the prompt asked for. Both numbers are in the
README, because publishing only the generous one would be the kind of thing this repo exists to catch.

Mechanically: word count in range, at least ten diacritics, zero cedillas, no markdown. Then, if it
passes, it goes to the jury.

Run **three times** with a majority verdict, because it is the only probe a model can fail by accident.
The other three are stable enough to run once. All three attempts are kept in the results file.

## A probe that never got an answer is not a failure

This is the rule that most changes the table, so it is worth stating on its own.

When a call comes back `503` (overloaded), `429` (rate limited), `402` (the account was answered with 402) or
times out, the model never saw the prompt. Counting that as a failed probe would publish a claim about
the model's ability that we did not measure. So:

- Probes that got no answer are **excluded from the denominator**. The `Probes` column reads passes out
  of probes *answered*, and a ⚠ marks any model where the two differ.
- A model where **nothing** came back is **not ranked at all**. It goes in a separate table with its HTTP
  codes, because "this free endpoint was unavailable when we tried" is genuinely useful to know — it is
  just not a quality score.
- Every HTTP code from every call is in `data/models.json`, so you can disagree with where we drew that
  line.

In this run that distinction moved four models. Google's `gemini-3.8-flash` returned `503` on three of
four probes; ranking it on the one that got through would be close to meaningless, and ranking it at
0/4 would be a lie. NVIDIA's `moonshotai/kimi-k3` timed out on every call at 180 seconds — the same
model answered in about 13 seconds during an earlier run, which tells you something real about free-tier
capacity and nothing at all about the model's Romanian.

## The blind jury

Only probe D is judged. Two things keep that from being decoration:

**Blind.** Paragraphs are stripped of the model that produced them and shuffled under IDs (`P01`, `P02`,
…) with a fixed seed (20260905). The judge never learns whose text it is scoring, and anyone re-running
the shuffle on the same input gets the same IDs.

**Three separate lenses, three separate calls.** One "rate this 0-10" collapses three different failures
into one number and hides all of them:

| Lens | The question |
|---|---|
| `sounds_human` | Does this read like a person wrote it, or like a language model? |
| `language_correctness` | Is the Romanian correct — diacritics, agreement, prepositions, and does anything read as translated from English? |
| `follows_instruction` | Did it do exactly what was asked: the word count, no title, no list, no invented figures? |

The exact prompts are in the `jury` block of the language pack, and `judge.py --export` writes them out
next to the anonymised paragraphs.

### The jury is a conflict of interest, stated plainly — and now measured

**Every judge is itself a language model.** None is a neutral instrument, and each may favour text that
resembles its own output. That cannot be removed. It can be measured, and since 6 September 2026 it is:

- **Two judges, from different families.** `claude` (Anthropic) and `glm` (z.ai), declared with their
  family in [`bench/judges.json`](bench/judges.json). Neither family appears in `providers.json`, so
  neither is scoring a relative. `gate_contributions.py` refuses a jury drawn from a single family.
- **A lens score is the mean of the two.** The spread between them is kept per model.
- **The disagreement is published**, in `results/<date>/agreement.md`, generated by
  [`bench/agreement.py`](bench/agreement.py).

And the first run said something we did not expect, which is exactly why it is worth measuring:

| Lens | Correlation between judges | Mean gap | What it means |
|---|---|---|---|
| `language_correctness` | **0.93** | 1.60 | They rank the texts almost identically. One is simply stricter. This lens is solid. |
| `follows_instruction` | **0.73** | 1.10 | Close agreement. Countable constraints are hard to disagree about. |
| `sounds_human` | **−0.07** | 1.70 | Essentially no relationship. The two models do not mean the same thing by it. |

**So the three lenses are not equally trustworthy, and we say so rather than averaging them into one
confident number.** Whether Romanian is correct can be judged consistently by two different models.
Whether a paragraph "sounds like a person" cannot — at least not by these two. Read the human-sounding
column as two opinions that happened to point in the same direction, not as a measurement.

That finding costs us something: it weakens the headline lens of our own benchmark. Publishing it is
the point. A jury whose disagreement is hidden is not a jury, it is a decoration.

### One judge is reproducible, one is not

`glm` runs through a public API: anyone with a z.ai key can reproduce its scores exactly. `claude` was
scored by hand through a chat interface, not by API, and **a stranger cannot reproduce it**. That is a real limitation of the
published numbers and it is stated here rather than glossed over. To get a fully reproducible jury, run
`judge.py --api` with two API judges of your own and compare. If your numbers disagree with ours,
[open an issue](CONTRIBUTING.md) — that is a better outcome for this repo than agreement.

`judge.py --export` gives you the anonymised corpus and the exact prompts, so re-judging costs nothing
but your own API calls.

## What this does NOT measure

Read this before quoting a number from here.

- **One day.** A snapshot, dated. Providers change models under the same name, and a model that scored
  8.2 in September may be a different set of weights in November. The date is on every table for that
  reason.
- **One prompt per probe.** A model that fails probe A on this phrasing might pass on another. We measure
  *instruction following on a specific instruction*, which is what you get in production, but it is not
  the same as measuring capability.
- **One language.** Romanian. A model that scores badly here may be excellent in English. That is the
  point — English-only benchmarks would not show you this — but it does not generalise to your language
  until someone runs it there. See [`bench/languages/README.md`](bench/languages/README.md).
- **Not reasoning, not code, not long context, not tool use.** Four narrow probes. There are good
  benchmarks for the rest; this is not one of them.
- **the calling accounts, on the network, on one afternoon.** Latency figures especially: they include our
  round-trip and whatever load the provider was under. Treat them as order-of-magnitude.
- **n=1 on probes A to C.** Only the paragraph probe is repeated. A single 429 or timeout at the wrong
  moment shows up as a failure — see NVIDIA's `kimi-k3` in the results, which answered in 13 seconds
  during an earlier run and timed out repeatedly during this one. Both facts are in the repo.

## Reproducing it

```bash
export GROQ_API_KEY=...          # any subset; providers with no key are skipped, not failed
python bench/benchmark.py --out results.json --language ro
python bench/judge.py results.json --export judged/    # writes paragraphs + prompts for you to judge
python bench/rank.py results.json --date 2026-09-06 --out .                    # mechanical half only
python bench/rank.py results.json --jury jury.json --date 2026-09-06 --out .   # once you have a jury.json
```

The battery takes 20 to 60 minutes, most of it waiting on the slowest providers. Each provider runs in
its own thread with its own pacing, so a slow one does not hold up the rest.

`python bench/test_probes.py` runs the checkers against known-good and known-bad answers with no network
access at all. Run it after touching anything in `check()`.
