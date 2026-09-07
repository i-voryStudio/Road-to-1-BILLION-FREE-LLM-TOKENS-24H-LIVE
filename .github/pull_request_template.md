<!-- Thanks for contributing. The checklist is short and every line of it exists because
     something went wrong once. -->

## What this changes

<!-- One sentence. -->

## How you know

**Every number in this repo carries its provenance.** Tick the one that applies:

- [ ] **MEASURED** — I ran it. Paste the command and its output below.
- [ ] **DECLARED** — the provider publishes it, in the unit you are recording. Paste the URL and the
      date you read it. (A token figure you computed from a request cap is not DECLARED: record the
      request cap and let `bench/rank.py` derive and label the tokens.)
- [ ] **PAID-PLAN** — the only published figure belongs to a paid tier. Mark it `rpd_is_paid_plan`;
      it will be shown and never ranked.
- [ ] **UNKNOWN** — nobody publishes it and I did not measure it. That is a valid, welcome
      contribution: replacing a wrong number with "unknown, and here is why" makes this repo better.
- [ ] Not applicable (code or docs change with no numbers in it).

```
paste the command + output, or the source URL + date
```

## Checks

- [ ] `python bench/test_probes.py` exits 0
- [ ] `python bench/test_gate.py` exits 0
- [ ] `python bench/gate_publish.py .` exits 0
- [ ] `python bench/gate_contributions.py` exits 0
- [ ] `python bench/test_rank.py` exits 0 if you touched `bench/rank.py`, `bench/limits.json` or a fixture
- [ ] No new dependency. This repo is standard library only, and that is its main security property.
- [ ] No API key, token or account state anywhere in the diff — not even an expired one, not even as
      test data. Use the shape-only fakes in `bench/test_gate.py` as a model.

## If you added a provider

Adding a provider is two edits in one PR, and the gate refuses either one alone:

- [ ] The JSON block in `bench/providers.json`: endpoint, `key_env`, `signup`, models, pacing.
- [ ] The host is added to `ALLOWED_HOSTS` in `bench/gate_contributions.py` **in this same PR**, so a
      reviewer sees the new destination. A JSON-only change cannot add one, by design.
- [ ] An entry in `bench/limits.json` with `all_models` (nulls are fine) and one in `bench/privacy.json`
      (`UNKNOWN` is fine), so the ranking prints a labelled figure rather than a missing one.
- [ ] `key_env` names your provider and is not already used by another one. An API key is bound to one
      host, forever: that rule is what stops this benchmark from becoming a credential harvester.

## If you added a language

- [ ] `bench/languages/<code>.json` with all four probes and three jury lenses
- [ ] Test cases in `bench/test_probes.py`, including at least one per probe that **must fail**. A
      checker tested only on correct answers is not tested.
- [ ] No real company, product or person in a prompt: the prompt is sent to every provider and echoed
      into published results.
