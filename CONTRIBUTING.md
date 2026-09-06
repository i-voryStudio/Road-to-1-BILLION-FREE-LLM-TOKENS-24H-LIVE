# Contributing

Four kinds of contribution, in rough order of how useful they are.

## 1. Correct a rate limit

The most valuable thing you can send. Rate limits move constantly and providers stop publishing them
without warning.

All of them live in [`bench/limits.json`](bench/limits.json), so a correction is a one-line change. What
a good correction includes:

- the new number,
- **how you know it** — a response header you saw, a page you read with the date, or a 429 you walked into,
- and the right `confidence`: `MEASURED` if you saw it, `DECLARED` if the provider says so, `UNKNOWN`
  if nobody publishes it.

`UNKNOWN` is a valid, welcome contribution. Changing a wrong number to "unknown, and here is why" makes
this repo better. Please do **not** copy a figure from another list to fill a gap — that is how the same
stale number ends up in eight repos at once.

Two things that get a correction rejected:

- **A limit multiplied across accounts or keys.** Most limits apply per organization or per project, so
  the multiplication is usually false, and where it is true it reads as advice to evade a quota. The
  publication gate blocks it automatically.
- **A number with no stated source.** "I think it's 500/day" is not a correction.

## 2. Add your language

The whole reason the probes live in JSON files. See
[`bench/languages/README.md`](bench/languages/README.md) — a language pack is one file, and the guide
walks through the writing-system trap that makes probe B worth running for your language.

If your language is added and you run the battery, you become the maintainer of that pack's results.
That is the deal, and it is a small job: one re-run when the numbers look stale.

## 3. Send results from providers we do not have

We can only measure providers we hold a key for. If you have one we do not:

```bash
export YOUR_PROVIDER_API_KEY=...
python bench/benchmark.py --out results.json --only yourprovider
```

Open a pull request with the results file, the date, and the provider entry for
[`bench/providers.json`](bench/providers.json). Adding a provider is a JSON block: endpoint, key
variable, model list, pacing.

## 4. Disagree with the jury

Half of each quality score comes from a language model judging paragraphs, which is a conflict of
interest we cannot remove — only expose. So:

```bash
python bench/judge.py results.json --export judged/
```

That writes the anonymised paragraphs and the exact prompts. Judge them with any model you like, or by
hand, and open an issue with your numbers. **A pull request that shows our ranking does not survive a
different jury is a good outcome for this repo, not an attack on it.** The mechanical half of every
score is reproducible without any of this — that half is not a matter of opinion.

## Before you open a pull request

```bash
python bench/test_probes.py      # the probe checkers, both directions. Must exit 0.
python bench/gate_publish.py .   # blocks keys, account state, private paths. Must exit 0.
```

CI runs both. The publication gate exists because raw benchmark output is exactly the kind of file
nobody reads before committing: it echoes your prompts back, and providers echo your account state back
inside error bodies.

## House rules for the data

- **Measured, declared and unknown are three different things** and never get flattened into one column.
- **A provider we could not test properly is excluded, not scored zero.** SiliconFlow is out of the
  ranking because the key was answered with 402 — that is a fact about the calling account, not about them.
- **Every table in this repo is generated** by `bench/rank.py`. Edit the data, not the Markdown, or your
  change will be overwritten on the next run.
