# Every endpoint we track

All 33 of them, ranked or not, scored or not, alive or not. The tables in [RESULTS.md](RESULTS.md) filter and sort; this one never does.

Measured **2026-09-07**. `?` means we do not know, and we would rather write that than guess.

| Model | Provider | Value | Auth | Coding | Intelligence | Agentic | Arena | Tokens/day | Req/day | Evidence | Answers | Trains on prompts | Note |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `minimax/minimax-m3:free` | xkiro | 234.4 | key | 58.6 | 35.7 | 31 | 1267 | 5,000,000 | ? | MEASURED | 100% | UNKNOWN |  |
| `minimax/minimax-m2.7:free` | xkiro | 210.4 | key | 52.6 | ? | ? | 1251 | 5,000,000 | ? | MEASURED | 100% | UNKNOWN |  |
| `qwen-3.8-27b` | cerebras | 206.2 | key | 68.1 | 41.4 | 46.8 | ? | 1,000,000 | 2,400 | MEASURED | 92% | UNKNOWN | answers blank unless thinking is off |
| `qwen/qwen3.8-27b` | groq | 155.1 | key | 68.1 | 41.4 | 46.8 | ? | 200,000 | 1,000 | PAID-PLAN | 88% | UNKNOWN |  |
| `gemma-4-31b` | cerebras | 131.4 | key | 43.4 | ? | 6.8 | ? | 1,000,000 | 2,400 | MEASURED | 92% | UNKNOWN |  |
| `qwen/qwen3.6-27b` | groq | 122.3 | key | 53.7 | ? | 20.1 | ? | 200,000 | 1,000 | PAID-PLAN | 88% | UNKNOWN |  |
| `gpt-oss-120b` | cerebras | 92.0 | key | 30.4 | 15.6 | 6.3 | 980 | 1,000,000 | 2,400 | MEASURED | 92% | UNKNOWN | we send `{"reasoning_effort": "low"}` |
| `minimax/minimax-m3:free` | openrouter | 91.8 | key | 58.6 | 35.7 | 31 | 1267 | 25,000 | 50 | DECLARED | 92% | UNKNOWN |  |
| `gemini-3.5-flash-lite` | google | 88.8 | key | 49.3 | 27.6 | 16.1 | ? | 250,000 | 500 | DECLARED | 67% | yes | May not be used for apps serving users in the EEA, Switzerland or the UK |
| `minimax/minimax-m2.7:free` | openrouter | 82.4 | key | 52.6 | ? | ? | 1251 | 25,000 | 50 | DECLARED | 92% | UNKNOWN |  |
| `nvidia/nemotron-3-ultra-550b-a55b:free` | openrouter | 77.2 | key | 49.3 | ? | 21.7 | 1153 | 25,000 | 50 | DECLARED | 92% | UNKNOWN | we send `{"chat_template_kwargs": {"enable_thinking": false}}` |
| `openai/gpt-oss-120b` | groq | 69.2 | key | 30.4 | 15.6 | 6.3 | 980 | 200,000 | 1,000 | PAID-PLAN | 88% | UNKNOWN | we send `{"reasoning_effort": "low"}` |
| `gemini-3.8-flash` | google | 67.3 | key | 76.3 | 47.1 | 41.2 | 1320 | 10,000 | 20 | DECLARED | 67% | yes | May not be used for apps serving users in the EEA, Switzerland or the UK |
| `openai/gpt-oss-20b` | groq | 47.1 | key | 20.7 | ? | 1.4 | ? | 200,000 | 1,000 | PAID-PLAN | 88% | UNKNOWN | we send `{"reasoning_effort": "low"}` |
| `@cf/openai/gpt-oss-120b` | cloudflare | not ranked | key | 30.4 | 15.6 | 6.3 | 980 | ? | ? | UNKNOWN | 90% | UNKNOWN | daily volume unknown - see LIMITS.md |
| `@cf/meta/llama-3.3-70b-instruct-fp8-fast` | cloudflare | not ranked | key | 11.9 | ? | ? | ? | ? | ? | UNKNOWN | 90% | UNKNOWN | daily volume unknown - see LIMITS.md |
| `@cf/google/gemma-4-26b-a4b-it` | cloudflare | not ranked | key | 39.3 | ? | ? | ? | ? | ? | UNKNOWN | 90% | UNKNOWN | answers blank unless thinking is off; daily volume unknown - see LIMITS.md |
| `@cf/qwen/qwen3.8-27b` | cloudflare | not ranked | key | 68.1 | 41.4 | 46.8 | ? | ? | ? | UNKNOWN | 90% | UNKNOWN | answers blank unless thinking is off; daily volume unknown - see LIMITS.md |
| `gemma-4-31b-it` | google | not ranked | key | 43.4 | ? | 6.8 | ? | ? | ? | UNKNOWN | 67% | yes | answers blank unless thinking is off; daily volume unknown - see LIMITS.md; May not be used for apps serving users in the EEA, Switzerland or the UK |
| `nvidia/nemotron-3-super-120b-a12b` | nvidia | not ranked | key | 37.7 | ? | 4.2 | ? | ? | ? | UNKNOWN | 65% | UNKNOWN | we send `{"chat_template_kwargs": {"enable_thinking": false}}`; daily volume unknown - see LIMITS.md |
| `nvidia/nemotron-3-ultra-550b-a55b` | nvidia | not ranked | key | 49.3 | ? | 21.7 | 1153 | ? | ? | UNKNOWN | 65% | UNKNOWN | we send `{"chat_template_kwargs": {"enable_thinking": false}}`; daily volume unknown - see LIMITS.md |
| `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning` | nvidia | not ranked | key | 13.8 | ? | ? | ? | ? | ? | UNKNOWN | 65% | UNKNOWN | daily volume unknown - see LIMITS.md |
| `nvidia/nemotron-3.5-lightning-30b-a3b` | nvidia | not ranked | key | 26.8 | ? | ? | ? | ? | ? | UNKNOWN | 65% | UNKNOWN | daily volume unknown - see LIMITS.md |
| `moonshotai/kimi-k3` | nvidia | not ranked | key | 76.2 | 50.2 | 50.9 | 1392 | ? | ? | UNKNOWN | 65% | UNKNOWN | daily volume unknown - see LIMITS.md |
| `gemma4:31b` | ollama | not ranked | key | 43.4 | ? | 6.8 | ? | ? | ? | UNKNOWN | 100% | UNKNOWN | daily volume unknown - see LIMITS.md |
| `gpt-oss:120b` | ollama | not ranked | key | 30.4 | 15.6 | 6.3 | 980 | ? | ? | UNKNOWN | 100% | UNKNOWN | we send `{"reasoning_effort": "low"}`; daily volume unknown - see LIMITS.md |
| `gpt-oss:20b` | ollama | not ranked | key | 20.7 | ? | 1.4 | ? | ? | ? | UNKNOWN | 100% | UNKNOWN | we send `{"reasoning_effort": "low"}`; daily volume unknown - see LIMITS.md |
| `qwen-flash` | alibaba | not ranked | key | ? | ? | ? | ? | ? | ? | UNKNOWN | 100% | UNKNOWN | we send `{"enable_thinking": false}`; no official benchmark score published for this model |
| `qwen-plus` | alibaba | not ranked | key | ? | ? | ? | ? | ? | ? | UNKNOWN | 100% | UNKNOWN | we send `{"enable_thinking": false}`; no official benchmark score published for this model |
| `qwen-turbo` | alibaba | not ranked | key | ? | ? | ? | ? | ? | ? | UNKNOWN | 100% | UNKNOWN | we send `{"enable_thinking": false}`; no official benchmark score published for this model |
| `qwen3.5-flash` | alibaba | not ranked | key | ? | ? | ? | ? | ? | ? | UNKNOWN | 100% | UNKNOWN | we send `{"enable_thinking": false}`; no official benchmark score published for this model |
| `@cf/mistralai/mistral-small-3.1-24b-instruct` | cloudflare | not ranked | key | ? | ? | ? | ? | ? | ? | UNKNOWN | 90% | UNKNOWN | no official benchmark score published for this model |
| `Qwen/Qwen3-Coder-30B-A3B-Instruct` | siliconflow | not ranked | key | ? | ? | ? | ? | ? | ? | UNKNOWN | ? | UNKNOWN | no official benchmark score published for this model |

## What the columns mean

- **Value** — `coding_index x log10(1 + requests/day)`, times 1.25 if no key is needed, times how often the provider actually answered us. Blank where we lack a score or a quota: a row needs both halves, and half a fact is not a rank.
- **Coding / Intelligence / Agentic / Arena** — imported from official benchmarks, never run by us. `?` means that model has no published score.
- **Evidence** — how we know the quota: MEASURED by us, DECLARED by the provider, PAID-PLAN when the only published figure belongs to a paid tier, UNKNOWN when nobody publishes it.
- **Answers** — share of the probe's calls that came back with something in them.
- **Trains on prompts** — from the provider's own terms. `UNKNOWN` means nobody has read them yet, and that is the honest default.

