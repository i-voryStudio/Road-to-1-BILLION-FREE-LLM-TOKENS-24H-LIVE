<!-- Thanks for contributing. The checklist is short and every line of it exists because
     something went wrong once. -->

## What this changes

<!-- One sentence. -->

## How you know

**Every number in this repo carries its provenance.** Tick the one that applies:

- [ ] **MEASURED** — I ran it. Paste the command and its output below.
- [ ] **DECLARED** — the provider publishes it. Paste the URL and the date you read it.
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
- [ ] No new dependency. This repo is standard library only, and that is its main security property.
- [ ] No API key, token or account state anywhere in the diff — not even an expired one, not even as
      test data. Use the shape-only fakes in `bench/test_gate.py` as a model.

## If you added a provider

- [ ] The host is added to `ALLOWED_HOSTS` in `bench/gate_contributions.py` **in this same PR**, so a
      reviewer sees the new destination. A JSON-only change cannot add one, by design.
- [ ] `key_env` names your provider and is not already used by another one. An API key is bound to one
      host, forever: that rule is what stops this benchmark from becoming a credential harvester.

## If you added a language

- [ ] `bench/languages/<code>.json` with all four probes and three jury lenses
- [ ] Test cases in `bench/test_probes.py`, including at least one per probe that **must fail**. A
      checker tested only on correct answers is not tested.
- [ ] No real company, product or person in a prompt: the prompt is sent to ten providers and echoed
      into published results.
