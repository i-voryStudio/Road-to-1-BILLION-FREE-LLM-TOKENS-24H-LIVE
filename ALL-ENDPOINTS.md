# Every endpoint we track

All 61 of them, ranked or not, scored or not, alive or not. The tables in [RESULTS.md](RESULTS.md) filter and sort; this one never does.

Measured **2026-09-07**. `?` means we do not know, and we would rather write that than guess.

| Model | Provider | Value | Auth | Coding | Intelligence | Agentic | Arena | Tokens/day | Req/day | Evidence | Answers | Trains on prompts | Note |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `minimax/minimax-m3:free` | xkiro | 234.4 | key | 58.6 | 35.7 | 31 | 1267 | 5,000,000 | ? | MEASURED | 100% | UNKNOWN |  |
| `qwen-3.8-27b` | cerebras | 224.8 | key | 68.1 | 41.4 | 46.8 | ? | 1,000,000 | 2,400 | MEASURED | 100% | UNKNOWN | answers blank unless thinking is off |
| `qwen/qwen3.8-27b` | groq | 177.3 | key | 68.1 | 41.4 | 46.8 | ? | 200,000 | 1,000 | PAID-PLAN | 100% | UNKNOWN |  |
| `gemma-4-31b` | cerebras | 143.3 | key | 43.4 | ? | 6.8 | ? | 1,000,000 | 2,400 | MEASURED | 100% | UNKNOWN |  |
| `qwen/qwen3.6-27b` | groq | 139.8 | key | 53.7 | ? | 20.1 | ? | 200,000 | 1,000 | PAID-PLAN | 100% | UNKNOWN |  |
| `gemini-3.5-flash-lite` | google | 133.1 | key | 49.3 | 27.6 | 16.1 | ? | 250,000 | 500 | DECLARED | 100% | yes | May not be used for apps serving users in the EEA, Switzerland or the UK |
| `minimax/minimax-m2.7:free` | xkiro | 105.2 | key | 52.6 | ? | ? | 1251 | 5,000,000 | ? | MEASURED | 50% | UNKNOWN |  |
| `gpt-oss-120b` | cerebras | 100.4 | key | 30.4 | 15.6 | 6.3 | 980 | 1,000,000 | 2,400 | MEASURED | 100% | UNKNOWN | we send `{"reasoning_effort": "low"}` |
| `minimax/minimax-m3:free` | openrouter | 100.1 | key | 58.6 | 35.7 | 31 | 1267 | 25,000 | 50 | DECLARED | 100% | UNKNOWN |  |
| `openai/gpt-oss-120b` | groq | 79.1 | key | 30.4 | 15.6 | 6.3 | 980 | 200,000 | 1,000 | PAID-PLAN | 100% | UNKNOWN | we send `{"reasoning_effort": "low"}` |
| `openai/gpt-oss-20b` | groq | 53.9 | key | 20.7 | ? | 1.4 | ? | 200,000 | 1,000 | PAID-PLAN | 100% | UNKNOWN | we send `{"reasoning_effort": "low"}` |
| `gemini-3.8-flash` | google | 0.0 | key | 76.3 | 47.1 | 41.2 | 1321 | 10,000 | 20 | DECLARED | ? | yes | May not be used for apps serving users in the EEA, Switzerland or the UK |
| `minimax/minimax-m2.7:free` | openrouter | 0.0 | key | 52.6 | ? | ? | 1251 | 25,000 | 50 | DECLARED | ? | UNKNOWN |  |
| `nvidia/nemotron-3-ultra-550b-a55b:free` | openrouter | 0.0 | key | 49.3 | ? | 21.7 | 1153 | 25,000 | 50 | DECLARED | ? | UNKNOWN | we send `{"chat_template_kwargs": {"enable_thinking": false}}` |
| `gemini-3.8-flash-free` | aihubmix | not ranked | key | 76.3 | 47.1 | 41.2 | 1321 | ? | ? | UNKNOWN | ? | UNKNOWN | daily volume unknown - see LIMITS.md |
| `coding-glm-5.3-free` | aihubmix | not ranked | key | 74.8 | 48.6 | 53.6 | ? | ? | ? | UNKNOWN | ? | UNKNOWN | daily volume unknown - see LIMITS.md |
| `coding-kimi-k3-free` | aihubmix | not ranked | key | 76.2 | 50.2 | 50.9 | 1393 | ? | ? | UNKNOWN | ? | UNKNOWN | daily volume unknown - see LIMITS.md |
| `coding-minimax-m3-free` | aihubmix | not ranked | key | 58.6 | 35.7 | 31 | 1267 | ? | ? | UNKNOWN | ? | UNKNOWN | daily volume unknown - see LIMITS.md |
| `gemma-4-26b-a4b-it-free` | aihubmix | not ranked | key | 39.3 | ? | ? | ? | ? | ? | UNKNOWN | ? | UNKNOWN | daily volume unknown - see LIMITS.md |
| `@cf/openai/gpt-oss-120b` | cloudflare | not ranked | key | 30.4 | 15.6 | 6.3 | 980 | ? | ? | UNKNOWN | 100% | UNKNOWN | daily volume unknown - see LIMITS.md |
| `@cf/meta/llama-3.3-70b-instruct-fp8-fast` | cloudflare | not ranked | key | 11.9 | ? | ? | ? | ? | ? | UNKNOWN | 100% | UNKNOWN | daily volume unknown - see LIMITS.md |
| `@cf/google/gemma-4-26b-a4b-it` | cloudflare | not ranked | key | 39.3 | ? | ? | ? | ? | ? | UNKNOWN | 100% | UNKNOWN | answers blank unless thinking is off; daily volume unknown - see LIMITS.md |
| `@cf/qwen/qwen3.8-27b` | cloudflare | not ranked | key | 68.1 | 41.4 | 46.8 | ? | ? | ? | UNKNOWN | 100% | UNKNOWN | answers blank unless thinking is off; daily volume unknown - see LIMITS.md |
| `gemma-4-31b-it` | google | not ranked | key | 43.4 | ? | 6.8 | ? | ? | ? | UNKNOWN | 100% | yes | answers blank unless thinking is off; daily volume unknown - see LIMITS.md; May not be used for apps serving users in the EEA, Switzerland or the UK |
| `Qwen3.8-27B-FP8` | inferx | not ranked | key | 68.1 | 41.4 | 46.8 | ? | ? | ? | UNKNOWN | ? | UNKNOWN | daily volume unknown - see LIMITS.md |
| `Qwen3-Coder-Next-FP8` | inferx | not ranked | key | 36.2 | ? | ? | ? | ? | ? | UNKNOWN | ? | UNKNOWN | daily volume unknown - see LIMITS.md |
| `Qwen3.6-35B-A3B-FP8` | inferx | not ranked | key | 41.9 | ? | ? | ? | ? | ? | UNKNOWN | ? | UNKNOWN | daily volume unknown - see LIMITS.md |
| `deepseek-v4-flash` | inferx | not ranked | key | 56.2 | ? | 23.8 | 1222 | ? | ? | UNKNOWN | ? | UNKNOWN | daily volume unknown - see LIMITS.md |
| `nemotron-3-ultra-550b-a55b:free` | kenari | not ranked | key | 49.3 | ? | 21.7 | 1153 | ? | ? | UNKNOWN | ? | UNKNOWN | daily volume unknown - see LIMITS.md |
| `nemotron-3-super-120b-a12b:free` | kenari | not ranked | key | 37.7 | ? | 4.2 | ? | ? | ? | UNKNOWN | ? | UNKNOWN | daily volume unknown - see LIMITS.md |
| `mimo-v2-5:free` | kenari | not ranked | key | 56.8 | ? | ? | 1277 | ? | ? | UNKNOWN | ? | UNKNOWN | daily volume unknown - see LIMITS.md |
| `mistral-medium-3-5:free` | kenari | not ranked | key | 46.9 | ? | 9.4 | ? | ? | ? | UNKNOWN | ? | UNKNOWN | daily volume unknown - see LIMITS.md |
| `mistral-small-2603` | mistral | not ranked | key | 26.6 | ? | ? | ? | ? | ? | UNKNOWN | ? | UNKNOWN | daily volume unknown - see LIMITS.md |
| `nvidia/nemotron-3-super-120b-a12b` | nvidia | not ranked | key | 37.7 | ? | 4.2 | ? | ? | ? | UNKNOWN | 100% | UNKNOWN | we send `{"chat_template_kwargs": {"enable_thinking": false}}`; daily volume unknown - see LIMITS.md |
| `nvidia/nemotron-3-ultra-550b-a55b` | nvidia | not ranked | key | 49.3 | ? | 21.7 | 1153 | ? | ? | UNKNOWN | 100% | UNKNOWN | we send `{"chat_template_kwargs": {"enable_thinking": false}}`; daily volume unknown - see LIMITS.md |
| `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning` | nvidia | not ranked | key | 13.8 | ? | ? | ? | ? | ? | UNKNOWN | 100% | UNKNOWN | daily volume unknown - see LIMITS.md |
| `nvidia/nemotron-3.5-lightning-30b-a3b` | nvidia | not ranked | key | 26.8 | ? | ? | ? | ? | ? | UNKNOWN | 100% | UNKNOWN | daily volume unknown - see LIMITS.md |
| `moonshotai/kimi-k3` | nvidia | not ranked | key | 76.2 | 50.2 | 50.9 | 1393 | ? | ? | UNKNOWN | 100% | UNKNOWN | daily volume unknown - see LIMITS.md |
| `gemma4:31b` | ollama | not ranked | key | 43.4 | ? | 6.8 | ? | ? | ? | UNKNOWN | 100% | UNKNOWN | daily volume unknown - see LIMITS.md |
| `gpt-oss:120b` | ollama | not ranked | key | 30.4 | 15.6 | 6.3 | 980 | ? | ? | UNKNOWN | 100% | UNKNOWN | we send `{"reasoning_effort": "low"}`; daily volume unknown - see LIMITS.md |
| `gpt-oss:20b` | ollama | not ranked | key | 20.7 | ? | 1.4 | ? | ? | ? | UNKNOWN | 100% | UNKNOWN | we send `{"reasoning_effort": "low"}`; daily volume unknown - see LIMITS.md |
| `gpt-oss-120b` | ovhcloud | not ranked | no key | 30.4 | 15.6 | 6.3 | 980 | ? | ? | UNKNOWN | ? | UNKNOWN | daily volume unknown - see LIMITS.md |
| `Qwen3.5-397B-A17B` | ovhcloud | not ranked | no key | 48.2 | ? | 10.6 | 1196 | ? | ? | UNKNOWN | ? | UNKNOWN | daily volume unknown - see LIMITS.md |
| `Meta-Llama-3_3-70B-Instruct` | ovhcloud | not ranked | no key | 11.9 | ? | ? | ? | ? | ? | UNKNOWN | ? | UNKNOWN | daily volume unknown - see LIMITS.md |
| `Qwen3.8-27B` | ovhcloud | not ranked | no key | 68.1 | 41.4 | 46.8 | ? | ? | ? | UNKNOWN | 100% | UNKNOWN | daily volume unknown - see LIMITS.md |
| `Lorbus/Qwen3.6-27B-int4-AutoRound` | uncloseai | not ranked | no key | 53.7 | ? | 20.1 | ? | ? | ? | UNKNOWN | 100% | UNKNOWN | daily volume unknown - see LIMITS.md |
| `deepseek-v4-flash:free` | unorouter | not ranked | key | 56.2 | ? | 23.8 | 1222 | ? | ? | UNKNOWN | ? | UNKNOWN | daily volume unknown - see LIMITS.md |
| `deepseek-v4-pro:free` | unorouter | not ranked | key | 59.4 | ? | 27.9 | 1258 | ? | ? | UNKNOWN | ? | UNKNOWN | daily volume unknown - see LIMITS.md |
| `qwen-flash` | alibaba | not ranked | key | ? | ? | ? | ? | ? | ? | UNKNOWN | 100% | UNKNOWN | we send `{"enable_thinking": false}`; no official benchmark score published for this model |
| `qwen-plus` | alibaba | not ranked | key | ? | ? | ? | ? | ? | ? | UNKNOWN | 100% | UNKNOWN | we send `{"enable_thinking": false}`; no official benchmark score published for this model |
| `qwen-turbo` | alibaba | not ranked | key | ? | ? | ? | ? | ? | ? | UNKNOWN | 100% | UNKNOWN | we send `{"enable_thinking": false}`; no official benchmark score published for this model |
| `qwen3.5-flash` | alibaba | not ranked | key | ? | ? | ? | ? | ? | ? | UNKNOWN | 100% | UNKNOWN | we send `{"enable_thinking": false}`; no official benchmark score published for this model |
| `@cf/mistralai/mistral-small-3.1-24b-instruct` | cloudflare | not ranked | key | ? | ? | ? | ? | ? | ? | UNKNOWN | 100% | UNKNOWN | no official benchmark score published for this model |
| `glm-4-7-flash:free` | kenari | not ranked | key | ? | ? | ? | 1194 | ? | ? | UNKNOWN | ? | UNKNOWN | no official benchmark score published for this model |
| `codestral-2508` | mistral | not ranked | key | ? | ? | ? | 1024 | ? | ? | UNKNOWN | ? | UNKNOWN | no official benchmark score published for this model |
| `mistral-medium-latest` | mistral | not ranked | key | ? | ? | ? | ? | ? | ? | UNKNOWN | ? | UNKNOWN | no official benchmark score published for this model |
| `magistral-small-latest` | mistral | not ranked | key | ? | ? | ? | ? | ? | ? | UNKNOWN | ? | UNKNOWN | no official benchmark score published for this model |
| `Qwen3-Coder-30B-A3B-Instruct` | ovhcloud | not ranked | no key | ? | ? | ? | ? | ? | ? | UNKNOWN | ? | UNKNOWN | no official benchmark score published for this model |
| `Mistral-Small-3.2-24B-Instruct-2506` | ovhcloud | not ranked | no key | ? | ? | ? | 924 | ? | ? | UNKNOWN | 100% | UNKNOWN | no official benchmark score published for this model |
| `Qwen/Qwen3-Coder-30B-A3B-Instruct` | siliconflow | not ranked | key | ? | ? | ? | ? | ? | ? | UNKNOWN | ? | UNKNOWN | no official benchmark score published for this model |
| `aion-2.0:free` | unorouter | not ranked | key | ? | ? | ? | ? | ? | ? | UNKNOWN | ? | UNKNOWN | no official benchmark score published for this model |

## What the columns mean

- **Value** — `coding_index x log10(1 + requests/day)`, times 1.25 if no key is needed, times how often the provider actually answered us. Blank where we lack a score or a quota: a row needs both halves, and half a fact is not a rank.
- **Coding / Intelligence / Agentic / Arena** — imported from official benchmarks, never run by us. `?` means that model has no published score.
- **Evidence** — how we know the quota: MEASURED by us, DECLARED by the provider, PAID-PLAN when the only published figure belongs to a paid tier, UNKNOWN when nobody publishes it.
- **Answers** — share of the probe's calls that came back with something in them.
- **Trains on prompts** — from the provider's own terms. `UNKNOWN` means nobody has read them yet, and that is the honest default.

