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
- [ ] `python bench/gate_pr.py --base origin/main` exits 0. Measurements are made, never contributed: no
      line added, changed, moved or removed in `data/uptime.jsonl`, `data/throughput.jsonl`,
      `data/drawn.jsonl`, `data/reliability.json`, `data/scores.json` or anything under `results/` (the
      full list is `python bench/gate_pr.py --list-walls`), and no entry that exists on `main` in
      `bench/key_bindings.json`, `bench/providers.json` or the host maps edited. CI refuses either,
      whatever the line says.
- [ ] `python bench/test_rank.py` exits 0 if you touched `bench/rank.py`, `bench/limits.json` or a fixture
- [ ] No new dependency. This repo is standard library only, and that is its main security property.
- [ ] No API key, token or account state anywhere in the diff — not even an expired one, not even as
      test data. Use the shape-only fakes in `bench/test_gate.py` as a model.

## If you added a provider

Six edits in one PR. The gate refuses the block when 2 or 3 is missing, and when 4 is missing where it
applies; without 5 and 6 the row prints UNKNOWN.

- [ ] 1. The block in `bench/providers.json`: endpoint, `key_env`, `signup`, models, pacing.
- [ ] 2. Its line in `bench/key_bindings.json`: the one host the key variable may reach, role `provider`.
- [ ] 3. Its API host in `ALLOWED_HOSTS` in `bench/gate_contributions.py` **in this same PR**, so a
      reviewer sees the new destination. A JSON-only change cannot add one, by design.
- [ ] 4. Its sign-up host in `KNOWN_SIGNUP_HOSTS` in the same file, if the sign-up page sits on a different
      domain from the API: a door is where people type passwords, so it is declared in code too. Without
      it the gate refuses the `signup` URL.
- [ ] 5. An entry in `bench/limits.json` with `all_models` (nulls are fine). A bare `tpm` carries `tpm_scope` (`in+out`, `output` or `unspecified`), and a MEASURED figure read
      on a trial tier carries `measured_on_tier`; both print wherever the figure prints.
- [ ] 6. An entry in `bench/privacy.json` (`UNKNOWN` is fine).
- [ ] `key_env` names your provider and is not already used by another one. A key variable is bound to one
      host for good: an existing line in the registry, in `providers.json` or in the host maps is never
      edited in a PR, only added next to, and CI refuses the edit before reading it.
- [ ] If you ran the battery, the figures are in the description above, not in `results/` or `data/`.

## If you retired a provider

- [ ] The title starts with `retire:` and the PR removes that provider and nothing else: its block, its
      registry line, its hosts, its `limits.json` and `privacy.json` entries. Under that title CI admits the
      removals; it still refuses an edited entry and any touch on a measurement file.

## If you added a language

- [ ] `bench/languages/<code>.json` with all four probes and three jury lenses
- [ ] Test cases in `bench/test_probes.py`, including at least one per probe that **must fail**. A
      checker tested only on correct answers is not tested.
- [ ] No real company, product or person in a prompt: the prompt is sent to every provider and echoed
      into published results.
