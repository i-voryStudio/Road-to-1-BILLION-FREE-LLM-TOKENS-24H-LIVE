# Contributing

Four kinds of contribution, in rough order of how useful they are.

## 1. Correct a rate limit

The most valuable thing you can send. Rate limits move constantly and providers stop publishing them
without warning.

All of them live in [`bench/limits.json`](bench/limits.json), so a correction is a one-line change. What
a good correction includes:

- the new number,
- **how you know it** — a response header you saw, a page you read with the date, or a 429 you walked into,
- and the right `confidence`: `MEASURED` if you saw it, `DECLARED` if the provider says so in the
  unit you are recording, `UNKNOWN` if nobody publishes it. A daily token figure you computed
  from a request cap is not DECLARED: record the request cap and `bench/rank.py` derives the
  tokens and labels the result `DERIVED`, with the arithmetic. A figure published only for a paid
  plan carries `rpd_is_paid_plan: true` and is shown but never ranked.

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

## 3. Add a provider we do not have

Adding a provider is **six edits in one pull request**. The contribution gate refuses the block when 2
or 3 is missing, and when 4 is missing where it applies; without 5 and 6 the row prints UNKNOWN, which
is correct and less useful.

1. The provider's block in [`bench/providers.json`](bench/providers.json): endpoint, key variable,
   sign-up page, model list, pacing.
2. Its line in [`bench/key_bindings.json`](bench/key_bindings.json): the one host its key variable may
   reach, in the role `provider`. A key variable with no registry line is a key with no declared
   destination, so the gate refuses the block.
3. Its API host in `ALLOWED_HOSTS` in [`bench/gate_contributions.py`](bench/gate_contributions.py). A
   JSON-only addition is refused by design: this benchmark sends real API keys to every host it knows,
   so every destination is declared in code, where a reviewer sees it.
4. Its sign-up host in `KNOWN_SIGNUP_HOSTS`, in the same file, when the sign-up page lives on a different
   domain from the API (a console on another host). A door is where people type passwords, so it too is
   declared in code; without it the gate refuses the `signup` URL.
5. An entry in `bench/limits.json` with `all_models` (every value may be `null`). A bare `tpm` carries `tpm_scope` (`in+out`, `output` or `unspecified`), and a MEASURED figure read
   on a trial tier carries `measured_on_tier`; both print wherever the figure prints.
6. An entry in `bench/privacy.json` (all `UNKNOWN` is fine).

What you cannot send is a measurement. If you hold a key we do not, run the battery and put the figures
in the pull request description, where they are evidence for the reviewer:

```bash
export YOUR_PROVIDER_API_KEY=...
python bench/benchmark.py --out results.json --only yourprovider
```

Quote the figures, never the raw file: it echoes your prompts and the provider's error bodies, which can
carry the state of your account. The row is measured again from the machine that holds the keys before
any number is published, and until then the provider is listed as not probed yet. "What a pull request
may not touch", below, says why a measurement inside a pull request is refused outright.

## 4. Disagree with the jury of the archived language benchmark

The quality half of the main ranking is **imported** from official benchmarks and has no jury. The
jury belongs to the archived Romanian benchmark in `results/`, where half of each score came from a
language model judging paragraphs, which is a conflict of interest that can only be exposed, not
removed. So, for that benchmark:

```bash
python bench/judge.py results.json --export judged/
```

That writes the anonymised paragraphs and the exact prompts. Judge them with any model you like, or by
hand, and open an issue with your numbers. **A pull request that shows our ranking does not survive a
different jury is a good outcome for this repo, not an attack on it.** The mechanical half of every
score is reproducible without any of this — that half is not a matter of opinion.

## What a pull request may not touch

**Measurements are made, never contributed.** These files are written only by the meters that run on
the machine holding the keys and by the scheduled daily job:

- `data/uptime.jsonl` and `data/uptime-superseded.jsonl`: the daily liveness radar, and the rows the
  fourteen-day rule archived;
- `data/throughput.jsonl`: the 30-second burst; `data/drawn.jsonl`: the 60-minute draw;
- `data/reliability.json`, `data/scores.json`, `data/scores-drift.jsonl` and `data/catalog.json`: what
  the daily job recomputes, imports and re-reads;
- everything under `results/`: the archived benchmark runs.

A pull request that adds, changes, moves or deletes a line in any of them is refused by CI, whatever the
line says. This is not a judgement on the line. No gate can tell a row the meter wrote from a row typed
to look like one, so the question is not asked: measurements reach `main` by push from the machine
that made them, and only from there.

Three files decide where a key goes, and in them a pull request may **add** and never edit. An entry
that exists on `main` in `bench/key_bindings.json`, in `bench/providers.json`, or in `ALLOWED_HOSTS`,
`KNOWN_SIGNUP_HOSTS` and `KNOWN_TERMS_HOSTS` in `bench/gate_contributions.py` must still be there,
unchanged. That is what makes the key registry a wall rather than a note for the reviewer: swapping
two URLs and swapping the two registry lines to match is two existing lines changed, refused before
anyone reads what they say.

Retiring a provider is the one legitimate removal. It is its own pull request, with nothing else in it,
and its title starts with `retire:`. Under that title an existing entry may be removed from those three
files, still never changed, and the measurement files stay closed. Everything else, `bench/limits.json`
and `bench/privacy.json` included, is a normal change.

The gate is [`bench/gate_pr.py`](bench/gate_pr.py). `python bench/gate_pr.py --base origin/main` runs
it on your branch; `--list-walls` prints the list above from the gate itself, and `bench/test_pr.py`
fails if this page and the gate ever disagree.

## Before you open a pull request

```bash
python bench/test_probes.py        # the probe checkers, both directions. Must exit 0.
python bench/gate_publish.py .     # blocks keys, account state, private paths. Must exit 0.
python bench/gate_contributions.py # one key, one host; every daily figure under the target; every data row in date order and recomputable from what wrote it. Must exit 0.
python bench/gate_pr.py --base origin/main  # no measurement file touched, no existing key line edited. Must exit 0.
python bench/test_rank.py          # the page generator against its fixture. Must exit 0.
```

CI runs all of them. The publication gate exists because raw benchmark output is exactly the kind of file
nobody reads before committing: it echoes your prompts back, and providers echo your account state back
inside error bodies.

## House rules for the data

- **The volume labels are one vocabulary in one place**: the `LABELS` dict in `bench/rank.py`, with
  `RANKABLE` saying which may rank a row and `SUMMABLE` saying which may be summed into the daily shelf.
  Every legend and every sentence about them on README.md, LIMITS.md, RESULTS.md and ALL-ENDPOINTS.md is
  generated from those constants, so this file does not repeat the list or the count. A daily figure
  carries the label its evidence deserves, and the generated legend says what each label means.
- **An endpoint that refused the caller is recorded as what it returned**, an HTTP code and a date, never as
  a statement about anyone's account. A `402` says the endpoint stops serving without credit; it
  does not score the provider zero and it does not describe a balance.
- **Every number on every public page is generated**, and by exactly these scripts: `bench/rank.py`
  writes the README.md blocks between markers, RESULTS.md, ALL-ENDPOINTS.md, LIMITS.md,
  `data/ranking.json`, `data/ranking.csv` and `data/capacity.json`; `bench/gate_viability.py` writes
  GRAVEYARD.md and `data/viability.json`; `bench/rank_language.py` writes `data/models.json` and
  `data/models.csv` for the archived language run, taking its judges block from `bench/judges.json`.
  SOURCES.md carries hand-typed star counts inside one declared block, dated, and `bench/gate_claims.py`
  refuses them anywhere else. Edit the data, not the Markdown, or your change will be overwritten on the
  next run.
