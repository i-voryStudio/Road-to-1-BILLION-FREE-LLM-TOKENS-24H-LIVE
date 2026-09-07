# Every endpoint we track

All 63 of them, ranked or not, scored or not, alive or not, across 18 providers. The tables in [RESULTS.md](RESULTS.md) filter and sort; this one never does. 35 of the 63 have an answered-or-not verdict from the radar in the last 14 days; 5 were probed and only ever refused (429 or 402), which is not a verdict either way; 23 have not been probed yet. [GRAVEYARD.md](GRAVEYARD.md) counts every endpoint the radar has touched.

Measured **2026-09-07**. `?` means we do not know, and we would rather write that than guess.

| Model | Provider | Value | Get key | Coding | Intelligence | Agentic | Arena | Tokens/day | Req/day | Volume | Answers | Trains on prompts | Note |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `minimax/minimax-m3:free` | xkiro | 234.4 | [get a key](https://xkiro.com) | 58.6 | 35.7 | 31 | 1267 | 5,000,000 | ? | MEASURED | 2 of 2 (100%) | UNKNOWN |  |
| `qwen-3.8-27b` | cerebras | 224.8 | [get a key](https://cloud.cerebras.ai) | 68.1 | 41.4 | 46.8 | ? | 1,000,000 | 2,400 | MEASURED | 2 of 2 (100%) | UNKNOWN | answers blank unless thinking is off |
| `@cf/qwen/qwen3.8-27b` | cloudflare | 187.9 | [get a key](https://dash.cloudflare.com/profile/api-tokens) | 68.1 | 41.4 | 46.8 | ? | 286,795 | ? | DERIVED | 2 of 2 (100%) | UNKNOWN | answers blank unless thinking is off |
| `gemini-3.8-flash-free` | aihubmix | 152.9 | [get a key](https://aihubmix.com/) | 76.3 | 47.1 | 41.2 | 1321 | 50,000 | 100 | DERIVED | not probed yet | UNKNOWN | $1 top-up unlocks the daily quota |
| `coding-kimi-k3-free` | aihubmix | 152.7 | [get a key](https://aihubmix.com/) | 76.2 | 50.2 | 50.9 | 1393 | 50,000 | 100 | DERIVED | not probed yet | UNKNOWN | $1 top-up unlocks the daily quota |
| `coding-glm-5.3-free` | aihubmix | 149.9 | [get a key](https://aihubmix.com/) | 74.8 | 48.6 | 53.6 | ? | 50,000 | 100 | DERIVED | not probed yet | UNKNOWN | $1 top-up unlocks the daily quota |
| `gemma-4-31b` | cerebras | 143.3 | [get a key](https://cloud.cerebras.ai) | 43.4 | ? | 6.8 | ? | 1,000,000 | 2,400 | MEASURED | 2 of 2 (100%) | UNKNOWN |  |
| `gemini-3.5-flash-lite` | google | 133.1 | [get a key](https://aistudio.google.com/apikey) | 49.3 | 27.6 | 16.1 | ? | 250,000 | 500 | DERIVED | 1 of 1 (100%) | yes | May not be used for apps serving users in the EEA, Switzerland or the UK |
| `coding-minimax-m3-free` | aihubmix | 117.5 | [get a key](https://aihubmix.com/) | 58.6 | 35.7 | 31 | 1267 | 50,000 | 100 | DERIVED | not probed yet | UNKNOWN | $1 top-up unlocks the daily quota |
| `@cf/google/gemma-4-26b-a4b-it` | cloudflare | 108.4 | [get a key](https://dash.cloudflare.com/profile/api-tokens) | 39.3 | ? | ? | ? | 286,795 | ? | DERIVED | 2 of 2 (100%) | UNKNOWN | answers blank unless thinking is off |
| `minimax/minimax-m2.7:free` | xkiro | 105.2 | [get a key](https://xkiro.com) | 52.6 | ? | ? | 1251 | 5,000,000 | ? | MEASURED | 1 of 2 (50%) | UNKNOWN |  |
| `gpt-oss-120b` | cerebras | 100.4 | [get a key](https://cloud.cerebras.ai) | 30.4 | 15.6 | 6.3 | 980 | 1,000,000 | 2,400 | MEASURED | 2 of 2 (100%) | UNKNOWN | we send `{"reasoning_effort": "low"}` |
| `minimax/minimax-m3:free` | openrouter | 100.1 | [get a key](https://openrouter.ai/keys) | 58.6 | 35.7 | 31 | 1267 | 25,000 | 50 | DERIVED | 2 of 2 (100%) | UNKNOWN |  |
| `mimo-v2-5:free` | kenari | 97.0 | [get a key](https://kenari.id/) | 56.8 | ? | ? | 1277 | 25,000 | 50 | DERIVED | not probed yet | UNKNOWN |  |
| `nemotron-3-ultra-550b-a55b:free` | kenari | 84.2 | [get a key](https://kenari.id/) | 49.3 | ? | 21.7 | 1153 | 25,000 | 50 | DERIVED | not probed yet | UNKNOWN |  |
| `@cf/openai/gpt-oss-120b` | cloudflare | 83.9 | [get a key](https://dash.cloudflare.com/profile/api-tokens) | 30.4 | 15.6 | 6.3 | 980 | 286,795 | ? | DERIVED | 2 of 2 (100%) | UNKNOWN |  |
| `mistral-medium-3-5:free` | kenari | 80.1 | [get a key](https://kenari.id/) | 46.9 | ? | 9.4 | ? | 25,000 | 50 | DERIVED | not probed yet | UNKNOWN |  |
| `gemma-4-26b-a4b-it-free` | aihubmix | 78.8 | [get a key](https://aihubmix.com/) | 39.3 | ? | ? | ? | 50,000 | 100 | DERIVED | not probed yet | UNKNOWN | $1 top-up unlocks the daily quota |
| `nemotron-3-super-120b-a12b:free` | kenari | 64.4 | [get a key](https://kenari.id/) | 37.7 | ? | 4.2 | ? | 25,000 | 50 | DERIVED | not probed yet | UNKNOWN |  |
| `@cf/meta/llama-3.3-70b-instruct-fp8-fast` | cloudflare | 23.7 | [get a key](https://dash.cloudflare.com/profile/api-tokens) | 11.9 | ? | ? | ? | 48,826 | ? | DERIVED | 2 of 2 (100%) | UNKNOWN |  |
| `gemini-3.8-flash` | google | 0.0 | [get a key](https://aistudio.google.com/apikey) | 76.3 | 47.1 | 41.2 | 1321 | 10,000 | 20 | DERIVED | 0 of 1 (0%) | yes | May not be used for apps serving users in the EEA, Switzerland or the UK |
| `minimax/minimax-m2.7:free` | openrouter | 0.0 | [get a key](https://openrouter.ai/keys) | 52.6 | ? | ? | 1251 | 25,000 | 50 | DERIVED | 0 of 2 (0%) | UNKNOWN |  |
| `nvidia/nemotron-3-ultra-550b-a55b:free` | openrouter | 0.0 | [get a key](https://openrouter.ai/keys) | 49.3 | ? | 21.7 | 1153 | 25,000 | 50 | DERIVED | 0 of 2 (0%) | UNKNOWN | we send `{"chat_template_kwargs": {"enable_thinking": false}}` |
| `gemma-4-31b-it` | google | not ranked | [get a key](https://aistudio.google.com/apikey) | 43.4 | ? | 6.8 | ? | ? | ? | UNKNOWN | 1 of 1 (100%) | yes | answers blank unless thinking is off; daily volume unknown - see LIMITS.md; May not be used for apps serving users in the EEA, Switzerland or the UK |
| `Qwen/Qwen3.6-35B-A3B-FP8` | hetzner | not ranked | [get a key](https://console.hetzner.com/) | 41.9 | ? | ? | ? | ? | ? | UNKNOWN | not probed yet | UNKNOWN | daily volume unknown - see LIMITS.md |
| `Qwen3.8-27B` | hetzner | not ranked | [get a key](https://console.hetzner.com/) | 68.1 | 41.4 | 46.8 | ? | ? | ? | UNKNOWN | not probed yet | UNKNOWN | daily volume unknown - see LIMITS.md |
| `Qwen3-Coder-Next-FP8` | inferx | not ranked | [get a key](https://model.inferx.net/) | 36.2 | ? | ? | ? | ? | ? | UNKNOWN | not probed yet | UNKNOWN | daily volume unknown - see LIMITS.md |
| `Qwen3.6-35B-A3B-FP8` | inferx | not ranked | [get a key](https://model.inferx.net/) | 41.9 | ? | ? | ? | ? | ? | UNKNOWN | not probed yet | UNKNOWN | daily volume unknown - see LIMITS.md |
| `Qwen3.8-27B-FP8` | inferx | not ranked | [get a key](https://model.inferx.net/) | 68.1 | 41.4 | 46.8 | ? | ? | ? | UNKNOWN | not probed yet | UNKNOWN | daily volume unknown - see LIMITS.md |
| `deepseek-v4-flash` | inferx | not ranked | [get a key](https://model.inferx.net/) | 56.2 | ? | 23.8 | 1222 | ? | ? | UNKNOWN | not probed yet | UNKNOWN | daily volume unknown - see LIMITS.md |
| `mistral-small-2603` | mistral | not ranked | [get a key](https://console.mistral.ai/) | 26.6 | ? | ? | ? | ? | ? | UNKNOWN | not probed yet | UNKNOWN | daily volume unknown - see LIMITS.md |
| `moonshotai/kimi-k3` | nvidia | not ranked | [get a key](https://build.nvidia.com) | 76.2 | 50.2 | 50.9 | 1393 | ? | ? | UNKNOWN | 2 of 2 (100%) | UNKNOWN | daily volume unknown - see LIMITS.md |
| `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning` | nvidia | not ranked | [get a key](https://build.nvidia.com) | 13.8 | ? | ? | ? | ? | ? | UNKNOWN | 2 of 2 (100%) | UNKNOWN | daily volume unknown - see LIMITS.md |
| `nvidia/nemotron-3-super-120b-a12b` | nvidia | not ranked | [get a key](https://build.nvidia.com) | 37.7 | ? | 4.2 | ? | ? | ? | UNKNOWN | 2 of 2 (100%) | UNKNOWN | we send `{"chat_template_kwargs": {"enable_thinking": false}}`; daily volume unknown - see LIMITS.md |
| `nvidia/nemotron-3-ultra-550b-a55b` | nvidia | not ranked | [get a key](https://build.nvidia.com) | 49.3 | ? | 21.7 | 1153 | ? | ? | UNKNOWN | 2 of 2 (100%) | UNKNOWN | we send `{"chat_template_kwargs": {"enable_thinking": false}}`; daily volume unknown - see LIMITS.md |
| `nvidia/nemotron-3.5-lightning-30b-a3b` | nvidia | not ranked | [get a key](https://build.nvidia.com) | 26.8 | ? | ? | ? | ? | ? | UNKNOWN | 2 of 2 (100%) | UNKNOWN | daily volume unknown - see LIMITS.md |
| `gemma4:31b` | ollama | not ranked | [get a key](https://ollama.com/settings/keys) | 43.4 | ? | 6.8 | ? | ? | ? | UNKNOWN | 2 of 2 (100%) | UNKNOWN | daily volume unknown - see LIMITS.md |
| `gpt-oss:120b` | ollama | not ranked | [get a key](https://ollama.com/settings/keys) | 30.4 | 15.6 | 6.3 | 980 | ? | ? | UNKNOWN | 2 of 2 (100%) | UNKNOWN | we send `{"reasoning_effort": "low"}`; daily volume unknown - see LIMITS.md |
| `gpt-oss:20b` | ollama | not ranked | [get a key](https://ollama.com/settings/keys) | 20.7 | ? | 1.4 | ? | ? | ? | UNKNOWN | 2 of 2 (100%) | UNKNOWN | we send `{"reasoning_effort": "low"}`; daily volume unknown - see LIMITS.md |
| `Meta-Llama-3_3-70B-Instruct` | ovhcloud | not ranked | no key needed: [oai.endpoints.kepler.ai.cloud.ovh.net](https://oai.endpoints.kepler.ai.cloud.ovh.net/) | 11.9 | ? | ? | ? | ? | ? | UNKNOWN | probed, no verdict yet | UNKNOWN | daily volume unknown - see LIMITS.md |
| `Qwen3.5-397B-A17B` | ovhcloud | not ranked | no key needed: [oai.endpoints.kepler.ai.cloud.ovh.net](https://oai.endpoints.kepler.ai.cloud.ovh.net/) | 48.2 | ? | 10.6 | 1196 | ? | ? | UNKNOWN | probed, no verdict yet | UNKNOWN | daily volume unknown - see LIMITS.md |
| `Qwen3.8-27B` | ovhcloud | not ranked | no key needed: [oai.endpoints.kepler.ai.cloud.ovh.net](https://oai.endpoints.kepler.ai.cloud.ovh.net/) | 68.1 | 41.4 | 46.8 | ? | ? | ? | UNKNOWN | 1 of 1 (100%) | UNKNOWN | daily volume unknown - see LIMITS.md |
| `gpt-oss-120b` | ovhcloud | not ranked | no key needed: [oai.endpoints.kepler.ai.cloud.ovh.net](https://oai.endpoints.kepler.ai.cloud.ovh.net/) | 30.4 | 15.6 | 6.3 | 980 | ? | ? | UNKNOWN | probed, no verdict yet | UNKNOWN | daily volume unknown - see LIMITS.md |
| `Lorbus/Qwen3.6-27B-int4-AutoRound` | uncloseai | not ranked | no key needed: [hermes.ai.unturf.com](https://hermes.ai.unturf.com/) | 53.7 | ? | 20.1 | ? | ? | ? | UNKNOWN | 1 of 1 (100%) | UNKNOWN | daily volume unknown - see LIMITS.md |
| `deepseek-v4-flash:free` | unorouter | not ranked | [get a key](https://unorouter.com/) | 56.2 | ? | 23.8 | 1222 | ? | ? | UNKNOWN | not probed yet | UNKNOWN | daily volume unknown - see LIMITS.md |
| `deepseek-v4-pro:free` | unorouter | not ranked | [get a key](https://unorouter.com/) | 59.4 | ? | 27.9 | 1258 | ? | ? | UNKNOWN | not probed yet | UNKNOWN | daily volume unknown - see LIMITS.md |
| `qwen-flash` | alibaba | not ranked | [get a key](https://modelstudio.console.alibabacloud.com) | ? | ? | ? | ? | ? | ? | UNKNOWN | 2 of 2 (100%) | UNKNOWN | we send `{"enable_thinking": false}`; no official benchmark score published for this model |
| `qwen-plus` | alibaba | not ranked | [get a key](https://modelstudio.console.alibabacloud.com) | ? | ? | ? | ? | ? | ? | UNKNOWN | 2 of 2 (100%) | UNKNOWN | we send `{"enable_thinking": false}`; no official benchmark score published for this model |
| `qwen-turbo` | alibaba | not ranked | [get a key](https://modelstudio.console.alibabacloud.com) | ? | ? | ? | ? | ? | ? | UNKNOWN | 2 of 2 (100%) | UNKNOWN | we send `{"enable_thinking": false}`; no official benchmark score published for this model |
| `qwen3.5-flash` | alibaba | not ranked | [get a key](https://modelstudio.console.alibabacloud.com) | ? | ? | ? | ? | ? | ? | UNKNOWN | 2 of 2 (100%) | UNKNOWN | we send `{"enable_thinking": false}`; no official benchmark score published for this model |
| `@cf/mistralai/mistral-small-3.1-24b-instruct` | cloudflare | not ranked | [get a key](https://dash.cloudflare.com/profile/api-tokens) | ? | ? | ? | ? | 286,795 | ? | DERIVED | 2 of 2 (100%) | UNKNOWN | no official benchmark score published for this model |
| `glm-4-7-flash:free` | kenari | not ranked | [get a key](https://kenari.id/) | ? | ? | ? | 1194 | 25,000 | 50 | DERIVED | not probed yet | UNKNOWN | no official benchmark score published for this model |
| `codestral-2508` | mistral | not ranked | [get a key](https://console.mistral.ai/) | ? | ? | ? | 1024 | ? | ? | UNKNOWN | not probed yet | UNKNOWN | no official benchmark score published for this model |
| `magistral-small-latest` | mistral | not ranked | [get a key](https://console.mistral.ai/) | ? | ? | ? | ? | ? | ? | UNKNOWN | not probed yet | UNKNOWN | no official benchmark score published for this model |
| `mistral-medium-latest` | mistral | not ranked | [get a key](https://console.mistral.ai/) | ? | ? | ? | ? | ? | ? | UNKNOWN | not probed yet | UNKNOWN | no official benchmark score published for this model |
| `Mistral-Small-3.2-24B-Instruct-2506` | ovhcloud | not ranked | no key needed: [oai.endpoints.kepler.ai.cloud.ovh.net](https://oai.endpoints.kepler.ai.cloud.ovh.net/) | ? | ? | ? | 924 | ? | ? | UNKNOWN | 1 of 1 (100%) | UNKNOWN | no official benchmark score published for this model |
| `Qwen3-Coder-30B-A3B-Instruct` | ovhcloud | not ranked | no key needed: [oai.endpoints.kepler.ai.cloud.ovh.net](https://oai.endpoints.kepler.ai.cloud.ovh.net/) | ? | ? | ? | ? | ? | ? | UNKNOWN | probed, no verdict yet | UNKNOWN | no official benchmark score published for this model |
| `Qwen/Qwen3-Coder-30B-A3B-Instruct` | siliconflow | not ranked | [get a key](https://siliconflow.com) | ? | ? | ? | ? | ? | ? | UNKNOWN | probed, no verdict yet | UNKNOWN | no official benchmark score published for this model |
| `aion-2.0:free` | unorouter | not ranked | [get a key](https://unorouter.com/) | ? | ? | ? | ? | ? | ? | UNKNOWN | not probed yet | UNKNOWN | no official benchmark score published for this model |
| `openai/gpt-oss-120b` | groq | not ranked | [get a key](https://console.groq.com/keys) | 30.4 | 15.6 | 6.3 | 980 | 200,000 | 1,000 | PAID-PLAN | 2 of 2 (100%) | UNKNOWN | we send `{"reasoning_effort": "low"}`; only a paid-plan figure is published |
| `openai/gpt-oss-20b` | groq | not ranked | [get a key](https://console.groq.com/keys) | 20.7 | ? | 1.4 | ? | 200,000 | 1,000 | PAID-PLAN | 2 of 2 (100%) | UNKNOWN | we send `{"reasoning_effort": "low"}`; only a paid-plan figure is published |
| `qwen/qwen3.6-27b` | groq | not ranked | [get a key](https://console.groq.com/keys) | 53.7 | ? | 20.1 | ? | 200,000 | 1,000 | PAID-PLAN | 2 of 2 (100%) | UNKNOWN | only a paid-plan figure is published |
| `qwen/qwen3.8-27b` | groq | not ranked | [get a key](https://console.groq.com/keys) | 68.1 | 41.4 | 46.8 | ? | 200,000 | 1,000 | PAID-PLAN | 2 of 2 (100%) | UNKNOWN | only a paid-plan figure is published |

## What the columns mean

- **Value** - `coding_index x log10(1 + daily_tokens / 500) x answered_rate x 1.25 if no key x 0.5 if degraded`. Blank where we lack a score or a rankable daily figure: a row needs both halves, and half a fact is not a rank.
- **Get key** - the provider's own sign-up page, or its API host where it publishes none; the link's domain is checked against the API host, so it cannot point at a lookalike.
- **Coding / Intelligence / Agentic / Arena** - imported from official benchmarks, never run by us. `?` means that model has no published score.
- **Tokens/day** - the smaller of the token cap and the request cap times 500.
- **Volume** - how we know that figure:
  - **MEASURED** - we saw it ourselves: a response header, a usage endpoint, a 429 we walked into.
  - **DECLARED** - the provider says so on a page we read, with the date we read it. Real, and still their word.
  - **DERIVED** - arithmetic done here on figures the provider publishes, with the arithmetic shown: a request cap times 500 tokens a reply, or a unit price divided into an allowance.
  - **PAID-PLAN** - the only published number belongs to a paid tier, so it is not free capacity at all. Never ranked, never summed.
  - **UNKNOWN** - nobody publishes it and we have not measured it. It stays unknown. We do not borrow a number from another list to fill the hole, and unknown does not mean unlimited.
  - **DRAWN** - tokens actually pulled over a 60-minute draw, times 24. An extrapolation, and it is labelled as one everywhere it appears; used only where a provider has no MEASURED, DECLARED or DERIVED daily figure.
- **Answers** - radar probes in the last 14 days that came back with text, `yes of total`. 0% is a measurement; `not probed yet` is the absence of one.
- **Trains on prompts** - from the provider's own terms. `UNKNOWN` means nobody has read them yet, and that is the honest default.

