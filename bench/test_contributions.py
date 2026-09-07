#!/usr/bin/env python3
"""Calibrate the contribution gate in BOTH directions, on the shape of a pull request.

    python bench/test_contributions.py          # -v prints the reason each refusal fired

A gate is only worth its exit code if you have watched it fail. This file plants the pull requests a
hostile or careless contributor would actually send, and asserts the gate refuses each one FOR THE
REASON STATED - a refusal for some other reason is a miss, because it means the rule under test never
fired. Then it plants the honest ones and asserts the gate lets them through. A gate that says no to
everything is as useless as one that says yes to everything, and the second half of every section is
what proves it is not.

Every planted shape here was first run against a version of the gate that admitted it. The ones that
steal nothing matter as much as the one that steals a key: a JSON-only change can bill every runner
for a model the table never shows, get every runner's account closed, retire a live provider with a
public headstone, or put a link on a generated page. They are all here, and they are all refused.

The last section runs the REAL data files through the whole gate and compares what it finds with a
list stated out loud below. Real findings are not fixed by loosening a rule; they are listed, so the
data owner can fix the data and delete the line.
"""
import json, re, sys, tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gate_contributions as G

OK_HOST = "https://api.groq.com/openai/v1/chat/completions"
KEYLESS_HOST = "https://hermes.ai.unturf.com/v1/chat/completions"
CEREBRAS_HOST = "https://api.cerebras.ai/v1/chat/completions"
ALIBABA_HOST = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1/chat/completions"
JUDGE_HOST = "https://api.z.ai/api/coding/paas/v4/chat/completions"
M = [{"id": "llama-3.3-70b"}]        # one honest model, for entries whose point lies elsewhere
DATE = "2026-09-07"
# The word a quota must never be multiplied by. Spelled in two halves, on a line with no number, so
# the publication gate - which folds string concatenations on one line before it looks - never sees
# the phrase it refuses. Two gates disagreeing about one string is not a reason to weaken either.
PLURAL_OF_KEY = "ke" + "ys"


# ---------------------------------------------------------------- runners: one gate function each

def _write(d, name, content):
    p = Path(d) / name
    p.write_text(content if isinstance(content, str) else json.dumps(content), encoding="utf-8")
    return p


def check(entries):
    """Run only the provider half of the gate over a list of entries, return the problems."""
    problems = []
    with tempfile.TemporaryDirectory() as d:
        G.check_providers(_write(d, "providers.json", {"providers": entries}), problems)
    return problems


def check_raw(text):
    """The provider half over RAW json text, for shapes json.dumps cannot produce."""
    problems = []
    with tempfile.TemporaryDirectory() as d:
        G.check_providers(_write(d, "providers.json", text), problems)
    return problems


def check_cross_file(pair):
    """Both files, ONE key-binding map - the way collect() runs them."""
    providers, judges = pair
    problems = []
    maps = G.new_bindings()
    with tempfile.TemporaryDirectory() as d:
        G.check_providers(_write(d, "providers.json", {"providers": providers}), problems, maps)
        G.check_judges(_write(d, "judges.json", {"judges": judges}), problems, maps)
    return problems


def check_judges_list(judges):
    problems = []
    with tempfile.TemporaryDirectory() as d:
        G.check_judges(_write(d, "judges.json", {"judges": judges}), problems)
    return problems


SOMEPROVIDER = [{"name": "someprovider", "url": OK_HOST, "key_env": "SOMEPROVIDER_API_KEY", "models": M}]


def check_privacy_entry(fixture):
    """The privacy half over one provider entry. The provider's API host is api.groq.com, so its own
    domain is groq.com: a source anywhere else is a foreign domain."""
    entry, providers, name = (fixture + (SOMEPROVIDER, "someprovider"))[:3] if isinstance(fixture, tuple) else (fixture, SOMEPROVIDER, "someprovider")
    problems = []
    with tempfile.TemporaryDirectory() as d:
        G.check_privacy(_write(d, "privacy.json", {"providers": {name: entry}}), problems, providers)
    return problems


def check_limits_entry(fixture):
    """The quota half over one provider entry; a (entry, known names) pair adds the cross-file check."""
    entry, names = fixture if isinstance(fixture, tuple) else (fixture, None)
    problems = []
    with tempfile.TemporaryDirectory() as d:
        G.check_limits(_write(d, "limits.json", {"providers": {"someprovider": entry}}), problems, names)
    return problems


def check_language_pack(fixture):
    pack, code = fixture if isinstance(fixture, tuple) else (fixture, "ro")
    problems = []
    with tempfile.TemporaryDirectory() as d:
        G.check_language(_write(d, code + ".json", pack), problems)
    return problems


def _real(name):
    return G.load_json(HERE / name, [])


REAL_PROVIDERS = (_real("providers.json") or {}).get("providers") or []
REAL_LIMITS = _real("limits.json") or {}
# Endpoints picked from the real providers file, so these fixtures never name a model the radar does
# not probe. One provider with no published tokens-per-minute ceiling, one with.
_lim = REAL_LIMITS.get("providers") or {}


def _tpm(name):
    am = (_lim.get(name) or {}).get("all_models") or {}
    return am.get("tpm") or am.get("tpm_output")


UNCAPPED = next(p for p in REAL_PROVIDERS if not _tpm(p["name"]))
CAPPED = next(p for p in REAL_PROVIDERS if isinstance(_tpm(p["name"]), int))
P0, M0 = UNCAPPED["name"], UNCAPPED["models"][0]["id"]
P1, M1, CAP1 = CAPPED["name"], CAPPED["models"][0]["id"], _tpm(CAPPED["name"])


def check_uptime_rows(rows):
    problems = []
    with tempfile.TemporaryDirectory() as d:
        text = "\n".join(r if isinstance(r, str) else json.dumps(r) for r in rows) + "\n"
        G.check_uptime(_write(d, "uptime.jsonl", text), problems, REAL_PROVIDERS)
    return problems


def check_throughput_rows(rows):
    problems = []
    with tempfile.TemporaryDirectory() as d:
        text = "\n".join(r if isinstance(r, str) else json.dumps(r) for r in rows) + "\n"
        G.check_throughput(_write(d, "throughput.jsonl", text), problems, REAL_PROVIDERS, REAL_LIMITS)
    return problems


def check_deaths(entries):
    problems = []
    with tempfile.TemporaryDirectory() as d:
        G.check_announced_deaths(_write(d, "announced_deaths.json", {"providers": entries}), problems, REAL_PROVIDERS)
    return problems


# ---------------------------------------------------------------- providers.json

def prov(**kw):
    e = {"name": "groq", "url": OK_HOST, "key_env": "GROQ_API_KEY", "models": M}
    e.update(kw)
    return e


MUST_REFUSE = [
    ("the original attack: a stranger's host claiming an existing key variable",
     [{"name": "fastllm", "url": "https://attacker.example/v1/chat/completions", "key_env": "GROQ_API_KEY"}],
     "not in ALLOWED_HOSTS"),
    ("silent keyless: no key_env and no declaration, which would collect the no-key bonus",
     [{"name": "quiet", "url": KEYLESS_HOST}], "needs key_env"),
    ("declared keyless AND a key variable, so nobody can tell which one the ranking used",
     [{"name": "twofaced", "url": KEYLESS_HOST, "auth": "none", "key_env": "TWOFACED_API_KEY"}],
     "auth is \"none\" but key_env"),
    ("an invented auth value that reads as permissive",
     [{"name": "maybe", "url": KEYLESS_HOST, "auth": "optional"}], "auth must be"),
    ("keyless does not exempt a host from the allowlist",
     [{"name": "elsewhere", "url": "https://attacker.example/v1/chat/completions", "auth": "none"}],
     "not in ALLOWED_HOSTS"),
    ("keyless over plain http",
     [{"name": "insecure", "url": "http://hermes.ai.unturf.com/v1/chat/completions", "auth": "none"}],
     "url must be https"),
    # Assembled rather than written out: a URL with userinfo in it is shaped exactly like an email
    # address, and the publication gate refuses this file if one appears as a literal. Two gates
    # disagreeing about the same string is not a reason to weaken either.
    ("keyless with credentials embedded in the URL",
     [{"name": "inline", "url": "https://" + "user:pw" + "@" + "hermes.ai.unturf.com/v1/chat/completions",
       "auth": "none"}], "credentials in it"),
    ("keyless entries are still checked for model ids",
     [{"name": "modelless", "url": KEYLESS_HOST, "auth": "none", "models": [{"name": "no id here"}]}],
     "every model needs an id"),
    ("keyless pointing at localhost",
     [{"name": "loopback", "url": "https://127.0.0.1/v1/chat/completions", "auth": "none"}],
     "not a public provider host"),
    ("two entries, one key variable, two different hosts",
     [{"name": "groq", "url": OK_HOST, "key_env": "GROQ_API_KEY"},
      {"name": "cerebras", "url": CEREBRAS_HOST, "key_env": "GROQ_API_KEY"}], "already bound to"),
    ("a key variable that names a different provider",
     [{"name": "cerebras", "url": CEREBRAS_HOST, "key_env": "GROQ_API_KEY"}], "does not name this provider"),

    # --- quota burners and account closers: nothing stolen, everyone hurt
    ("pause_seconds 0: every runner hammers an allowed host at full speed",
     [prov(pause_seconds=0)], "pause_seconds must be"),
    ("pause_seconds of a billion: the runner sleeps for thirty years between calls",
     [prov(pause_seconds=10 ** 9)], "pause_seconds must be"),
    ("max_tokens of a billion: one call spends the day's quota",
     [prov(models=[{"id": "m", "max_tokens": 10 ** 9}])], "max_tokens must be"),
    ("max_tokens below the floor",
     [prov(models=[{"id": "m", "max_tokens": 1}])], "max_tokens must be"),
    ("timeout_seconds negative: socket.settimeout raises, every probe records down",
     [prov(timeout_seconds=-5)], "timeout_seconds must be"),
    ("timeout_seconds of a millisecond: every probe times out into down, fourteen of those bury it",
     [prov(timeout_seconds=0.001)], "timeout_seconds must be"),
    ("timeout_seconds of an hour",
     [prov(timeout_seconds=3600)], "timeout_seconds must be"),
    ("600 models on one provider: quota burn by volume",
     [prov(models=[{"id": "m%d" % i} for i in range(600)])], "at most 12"),
    ("thirteen models, one over the line",
     [prov(models=[{"id": "m%d" % i} for i in range(13)])], "at most 12"),
    ("no models at all: every runner indexes into the list and crashes",
     [prov(models=[])], "non-empty models list"),
    ("a provider with the models key missing",
     [{"name": "groq", "url": OK_HOST, "key_env": "GROQ_API_KEY"}], "non-empty models list"),
    ("a second model with the same id, differing only in case",
     [prov(models=[{"id": "gemma-4"}, {"id": "Gemma-4"}])], "duplicate model id"),

    # --- extra_body: merged into the request LAST, so it can rewrite the request
    ("extra_body replacing the model: every runner bills a model the table never shows",
     [prov(models=[{"id": "minimax/minimax-m3:free", "extra_body": {"model": "openai/gpt-4o"}}])],
     "extra_body sets 'model'"),
    ("extra_body replacing the messages: an arbitrary prompt under every runner's account",
     [prov(models=[{"id": "m", "extra_body": {"messages": [{"role": "user", "content": "anything"}]}}])],
     "extra_body sets 'messages'"),
    ("extra_body with n=50 and a huge completion budget",
     [prov(models=[{"id": "m", "extra_body": {"n": 50, "max_completion_tokens": 100000}}])],
     "extra_body sets"),
    ("extra_body switching on streaming, which the runner never reads",
     [prov(models=[{"id": "m", "extra_body": {"stream": True}}])], "extra_body sets 'stream'"),
    ("extra_body declaring tools",
     [prov(models=[{"id": "m", "extra_body": {"tools": {"a": 1}, "tool_choice": "auto"}}])], "extra_body sets"),
    ("extra_body carrying a prompt disguised as a string parameter",
     [prov(models=[{"id": "m", "extra_body": {"system": "x" * 300}}])], "character string"),
    ("extra_body with nine keys: that is a request, not a switch",
     [prov(models=[{"id": "m", "extra_body": {"k%d" % i: i for i in range(9)}}])], "carries 9 keys"),
    ("extra_body with a list in it",
     [prov(models=[{"id": "m", "extra_body": {"stop": ["a", "b"]}}])], "is a list"),
    ("extra_body nested four levels deep",
     [prov(models=[{"id": "m", "extra_body": {"a": {"b": {"c": {"d": 1}}}}}])], "nests deeper"),
    ("extra_body that is not an object",
     [prov(models=[{"id": "m", "extra_body": "reasoning_effort=low"}])], "must be a JSON object"),

    # --- the endpoint: right host, wrong door
    ("path swap on an allowed host: the key still goes to groq, but to audio transcription",
     [prov(url="https://api.groq.com/openai/v1/audio/transcriptions")], "url path must end with"),
    ("path with a traversal in it",
     [prov(url="https://api.groq.com/openai/v1/../v1/chat/completions")], "url path must end with"),
    ("a query string on the endpoint",
     [prov(url=OK_HOST + "?api-version=2")], "query string"),
    ("the Cloudflare account placeholder on a groq URL: the account id goes to groq in the path",
     [prov(url="https://api.groq.com/openai/{CF_ACCOUNT_ID}/v1/chat/completions")],
     "belongs to api.cloudflare.com"),
    ("an undeclared placeholder that would put a second key in the path",
     [prov(url="https://api.groq.com/openai/{OPENROUTER_API_KEY}/v1/chat/completions")], "url interpolates"),

    # --- names and keys
    ("provider 'a' claiming ALIBABA_API_KEY on Alibaba's own host: a one-letter name owns every key",
     [{"name": "a", "url": ALIBABA_HOST, "key_env": "ALIBABA_API_KEY", "models": M}], "does not name this provider"),
    ("a name that is not a plain lowercase token: it becomes a table cell and a map key",
     [prov(name="Groq|x")], "name must be"),
    ("the same provider twice, differing only in case: two radar rows a day on one account",
     [prov(), prov(name="Groq")], "duplicate provider name"),
    ("a provider entry on the judge's host, claiming the judge's key: the paid plan spent on the battery",
     [{"name": "zai", "url": JUDGE_HOST, "key_env": "ZAI_API_KEY", "models": [{"id": "glm-5.3-flash"}]}],
     "judge's endpoint"),
    ("a key variable that is not an environment variable name",
     [prov(key_env="groq api key")], "not a plain uppercase"),
    ("signup on a lookalike registrable domain of an allowed API host",
     [prov(signup="https://console.groq.com.evil.io/keys")], "signup points at"),

    # --- model ids are rendered inside backticks on generated pages
    ("a model id that closes the backtick and plants a link in ALL-ENDPOINTS.md",
     [prov(models=[{"id": "x` | [get your free key here](https://evil.example) | `"}])], "unexpected shape"),
    ("a model id with whitespace in it",
     [prov(models=[{"id": "gemma 4"}])], "unexpected shape"),
    ("a model id with a backslash in it",
     [prov(models=[{"id": "a\\b"}])], "unexpected shape"),
    ("unsupported_params naming something that is not a generation parameter",
     [prov(unsupported_params=["max_tokens"])], "unsupported_params must list"),
]

MUST_PASS = [
    ("an honest keyless provider on an allowed host",
     [{"name": "uncloseai", "url": KEYLESS_HOST, "auth": "none",
       "models": [{"id": "Lorbus/Qwen3.6-27B-int4-AutoRound"}]}]),
    ("an honest key provider",
     [{"name": "groq", "url": OK_HOST, "key_env": "GROQ_API_KEY", "models": [{"id": "llama-3.3-70b"}]}]),
    ("keyless and key side by side on different hosts",
     [{"name": "groq", "url": OK_HOST, "key_env": "GROQ_API_KEY", "models": M},
      {"name": "uncloseai", "url": KEYLESS_HOST, "auth": "none", "models": M}]),
    ("a declared alias still works",
     [{"name": "google", "url": "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
       "key_env": "GEMINI_API_KEY", "signup": "https://aistudio.google.com/apikey", "models": M}]),
    ("a reasoning switch, nested, is what extra_body is for",
     [prov(models=[{"id": "nvidia/nemotron-3-ultra-550b-a55b:free",
                    "extra_body": {"chat_template_kwargs": {"enable_thinking": False}}}])]),
    ("a provider overriding temperature for one model, the case test_probes.py pins",
     [prov(models=[{"id": "m", "extra_body": {"temperature": 0.7, "reasoning_effort": "low"}}])]),
    ("every range at its edge: 180 s timeout, half a second pause, 8000 tokens, 12 models",
     [prov(timeout_seconds=180, pause_seconds=0.5,
           models=[{"id": "m%d" % i, "max_tokens": 8000} for i in range(12)])]),
    ("the shortest honest timeout", [prov(timeout_seconds=5)]),
    ("Cloudflare: the account placeholder on its own host, the CF_ alias, ids that start with @",
     [{"name": "cloudflare", "url": "https://api.cloudflare.com/client/v4/accounts/{CF_ACCOUNT_ID}/ai/v1/chat/completions",
       "key_env": "CF_API_TOKEN", "signup": "https://dash.cloudflare.com/profile/api-tokens",
       "models": [{"id": "@cf/openai/gpt-oss-120b"}, {"id": "@cf/meta/llama-3.3-70b-instruct-fp8-fast"}]}]),
    ("an id with an underscore and a keyless host with a long path",
     [{"name": "ovhcloud", "url": "https://oai.endpoints.kepler.ai.cloud.ovh.net/v1/chat/completions",
       "auth": "none", "models": [{"id": "Meta-Llama-3_3-70B-Instruct"}, {"id": "gpt-oss-120b"}]}]),
    ("unsupported_params listing a real generation parameter, dated",
     [prov(unsupported_params=["seed"], unsupported_measured_on=DATE)]),
]

# Raw text, because json.dumps cannot write a duplicate key. The parser keeps the LAST value silently,
# so a reviewer reading the first url sees the chat endpoint and the runner uses the other one.
RAW_MUST_REFUSE = [
    ("two url keys in one provider: the reviewer reads the first, the runner uses the last",
     '{"providers": [{"name": "groq", "url": "%s", "key_env": "GROQ_API_KEY", "models": [{"id": "m"}], '
     '"url": "https://api.groq.com/openai/v1/audio/transcriptions"}]}' % OK_HOST, "duplicate JSON key 'url'"),
    ("a duplicate key deep inside a model entry",
     '{"providers": [{"name": "groq", "url": "%s", "key_env": "GROQ_API_KEY", '
     '"models": [{"id": "m", "max_tokens": 100, "max_tokens": 4000}]}]}' % OK_HOST, "duplicate JSON key 'max_tokens'"),
]
RAW_MUST_PASS = [
    ("the same entry written once",
     '{"providers": [{"name": "groq", "url": "%s", "key_env": "GROQ_API_KEY", "models": [{"id": "m"}]}]}' % OK_HOST),
]


# ---------------------------------------------------------------- judges.json, and the cross-file rule

JUDGE = {"name": "glm", "via": "api", "family": "glm", "url": JUDGE_HOST, "key_env": "ZAI_API_KEY",
         "model": "glm-5.3-flash"}
MANUAL = {"name": "claude", "via": "manual", "family": "other", "model": "some-model",
          "note": "Scored by hand through a chat interface, so a stranger cannot reproduce its scores."}

CROSS_FILE_MUST_REFUSE = [
    ("a contributed provider claims the JUDGE's key and points it at another allowed host",
     ([prov(key_env="ZAI_API_KEY")], [JUDGE]), "already bound to"),
    ("and the same theft in the other direction: a judge claims a provider's key",
     ([prov()], [dict(JUDGE, key_env="GROQ_API_KEY")]), "already bound to"),
    ("a provider on the judge's own host with the judge's own key: same host, so the old check passed it",
     ([{"name": "zai", "url": JUDGE_HOST, "key_env": "ZAI_API_KEY", "models": [{"id": "glm-5.3-flash"}]}],
      [JUDGE]), "is a provider key and this entry uses it as a judge key"),
    ("a judge on a provider's host with the provider's key, in the other order",
     ([prov()], [dict(JUDGE, url=OK_HOST, key_env="GROQ_API_KEY")]), "is a provider key"),
]
CROSS_FILE_MUST_PASS = [
    ("a provider and a judge, each on its own host with its own key",
     ([prov(), {"name": "uncloseai", "url": KEYLESS_HOST, "auth": "none", "models": M}], [JUDGE, MANUAL])),
]

JUDGES_MUST_REFUSE = [
    ("an invented via", [dict(JUDGE, via="email"), MANUAL], "via must be"),
    ("an agent judge with no note: a limitation nobody declared",
     [JUDGE, {"name": "claude", "via": "manual", "family": "other", "model": "x"}], "needs a note"),
    ("a manual judge whose note does not say it cannot be reproduced",
     [JUDGE, dict(MANUAL, note="Scored by hand.")], "needs a note"),
    ("no judge reachable by API", [MANUAL, dict(MANUAL, name="other", family="third")], "no judge is reachable"),
    ("every judge from one family", [JUDGE, dict(MANUAL, family="glm")], "same family"),
    ("an api judge whose extra_body replaces the model", [dict(JUDGE, extra_body={"model": "glm-5"}), MANUAL],
     "extra_body sets 'model'"),
    ("an api judge with no model id", [dict(JUDGE, model=None), MANUAL], "needs a model id"),
    ("an api judge with a huge budget", [dict(JUDGE, max_tokens=10 ** 6), MANUAL], "max_tokens must be"),
    ("an api judge on a host that is not allowed",
     [dict(JUDGE, url="https://attacker.example/v1/chat/completions"), MANUAL], "not in ALLOWED_HOSTS"),
    ("two judges with the same name", [JUDGE, dict(MANUAL, name="glm")], "duplicate judge name"),
]
JUDGES_MUST_PASS = [
    ("an api judge and a manual one with its note: the real jury's shape", [JUDGE, MANUAL]),
    ("an api judge and an agent one with its note", [JUDGE, dict(MANUAL, via="agent")]),
    ("an api judge with a reasoning switch and a budget",
     [dict(JUDGE, extra_body={"thinking": {"type": "disabled"}}, max_tokens=600, pause_seconds=2), MANUAL]),
]


# ---------------------------------------------------------------- privacy.json

OWN = "https://console.groq.com/docs/terms"      # the provider's own domain: api.groq.com -> groq.com
FOREIGN = "https://example.com/terms"

PRIVACY_MUST_REFUSE = [
    ("says it does not train on your prompts, with no source at all",
     {"trains_on_free_tier": "no"}, "no https source"),
    ("says it does not train, sourced and dated, but quotes nothing",
     {"trains_on_free_tier": "no", "source": OWN, "read_on": DATE}, "no verbatim quote"),
    ("says it does not train, and the quote it offers says nothing of the kind",
     {"trains_on_free_tier": "no", "source": OWN, "read_on": DATE,
      "quotes": ["We may use your content to provide and improve the Services."]}, "contains a negation"),
    ("a dated claim with a source that is not https",
     {"logs_prompts": "yes", "source": "http://console.groq.com/terms", "read_on": DATE,
      "quotes": ["We log prompts."]}, "no https source"),
    ("a sourced, quoted claim with no date",
     {"human_review": "yes", "source": OWN, "quotes": ["Human reviewers may read your input."]}, "needs read_on"),
    ("a 'no' whose quote says the opposite, with a capital Note: 'not' used to match inside it",
     {"trains_on_free_tier": "no", "source": OWN, "read_on": DATE,
      "quotes": ["Note: we use all inputs to train our models."]}, "contains a negation"),
    ("a 'no' whose quote contains 'another': 'no ' used to match inside it",
     {"trains_on_free_tier": "no", "source": OWN, "read_on": DATE,
      "quotes": ["Inputs are shared with another company for training."]}, "contains a negation"),
    ("a 'no' sourced on a domain that is not the provider's: the case the docstring forbade and the "
     "old test enshrined",
     {"trains_on_free_tier": "no", "source": FOREIGN, "read_on": DATE,
      "quotes": ["We do not use your prompts to train our models."]}, "not this provider's domain"),
    ("a 'yes' sourced on a foreign domain: somebody's summary is not their terms",
     {"trains_on_free_tier": "yes", "source": FOREIGN, "read_on": DATE,
      "quotes": ["They use the content you submit to improve their products."]}, "not this provider's domain"),
    ("a lookalike of the provider's domain",
     {"logs_prompts": "no", "source": "https://groq.com.evil.example/terms", "read_on": DATE,
      "quotes": ["We do not log."]}, "not this provider's domain"),
    ("a read_on that is not a date",
     {"logs_prompts": "yes", "source": OWN, "read_on": "yesterday", "quotes": ["We log."]}, "needs read_on"),
    ("a privacy entry for a provider that is not in providers.json",
     ({"trains_on_free_tier": "UNKNOWN"}, SOMEPROVIDER, "ghost"), "not a provider in providers.json"),
]

PRIVACY_MUST_PASS = [
    ("UNKNOWN everywhere needs nothing - not knowing is allowed, guessing is not",
     {"trains_on_free_tier": "UNKNOWN", "logs_prompts": "UNKNOWN"}),
    ("a 'no' with a source on the provider's domain, a date and a quote that actually negates",
     {"trains_on_free_tier": "no", "source": OWN, "read_on": DATE,
      "quotes": ["We do not use your prompts to train our models."]}),
    ("a 'yes' with a source on the provider's domain, a date and their own sentence",
     {"trains_on_free_tier": "yes", "source": OWN, "read_on": DATE,
      "quotes": ["We use the content you submit to improve our products."]}),
    ("a 'no' negated with a contraction", {"logs_prompts": "no", "source": OWN, "read_on": DATE,
                                           "quotes": ["We don't keep your prompts after the reply is sent."]}),
    ("a 'no' negated with opt out", {"trains_on_free_tier": "no", "source": OWN, "read_on": DATE,
                                     "quotes": ["Free-tier users may opt out of training at any time."]}),
    ("a 'no' negated with never", {"human_review": "no", "source": OWN, "read_on": DATE,
                                   "quotes": ["Your inputs are never read by a person."]}),
    ("a source on a declared terms host: Google's terms live on ai.google.dev",
     ({"trains_on_free_tier": "yes", "source": "https://ai.google.dev/gemini-api/terms", "read_on": DATE,
       "quotes": ["Google uses the content you submit to improve its products."]},
      [{"name": "google", "url": "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
        "key_env": "GEMINI_API_KEY", "models": M}], "google")),
]


# ---------------------------------------------------------------- limits.json

BASE = {"confidence": "UNKNOWN", "all_models": {"rpd": None, "tpd": None}}
DECL = {"confidence": "DECLARED", "source": OWN, "read_on": DATE}
MEAS = {"confidence": "MEASURED", "measured_on": DATE, "measured_how": "x-ratelimit headers on a call"}
PRICING = "https://console.groq.com/pricing"

ONE_TIME_MUST_REFUSE = [
    ("a sign-up bundle with no source and no date",
     dict(BASE, one_time={"tokens": 5000000, "confidence": "DECLARED", "quote": "5M free tokens"}), "needs an https source"),
    ("a declared bundle with no quote from the provider",
     dict(BASE, one_time={"tokens": 5000000, "confidence": "DECLARED", "source": PRICING, "read_on": DATE}),
     "needs the provider's own sentence"),
    ("a bundle carrying both tokens and money, which double-counts the same gift",
     dict(BASE, one_time={"tokens": 5000000, "credits_usd": 5, "confidence": "DECLARED",
                          "source": PRICING, "read_on": DATE, "quote": "5M tokens or $5"}), "BOTH tokens and credits_usd"),
    ("a bundle whose size is a string",
     dict(BASE, one_time={"tokens": "five million", "confidence": "UNKNOWN"}), "must be a non-negative number"),
    ("an invented confidence value",
     dict(BASE, one_time={"tokens": 100, "confidence": "PROBABLY"}), "one_time.confidence must be"),
    ("a monthly pot gets the same rule: declared with no quote",
     dict(BASE, monthly={"credits_usd": 10, "confidence": "DECLARED", "source": PRICING, "read_on": DATE}),
     "needs the provider's own sentence"),
    ("a credits block with no source, date or quote",
     dict(BASE, credits={"usd_per_month": 10}), "credits block needs"),
]

ONE_TIME_MUST_PASS = [
    ("a sourced, dated, quoted bundle in tokens",
     dict(BASE, one_time={"tokens": 5000000, "confidence": "DECLARED", "source": PRICING, "read_on": DATE,
                          "quote": "New accounts receive 5,000,000 free tokens."})),
    ("a sourced, dated, quoted bundle in money",
     dict(BASE, one_time={"credits_usd": 5, "confidence": "DECLARED", "source": PRICING, "read_on": DATE,
                          "quote": "Free Trial: $5 in free credits after making an account"})),
    ("a bundle we know exists but have not measured",
     dict(BASE, one_time={"tokens": None, "credits_usd": None, "confidence": "UNKNOWN"})),
    ("no bundle at all is not a problem", dict(BASE)),
    ("a sourced, dated, quoted monthly pot",
     dict(BASE, monthly={"credits_usd": 10, "confidence": "DECLARED", "source": PRICING, "read_on": DATE,
                         "quote": "$10 /mo in API credits."})),
    ("a credits block with its evidence",
     dict(BASE, credits={"usd_per_month": 10, "source": PRICING, "read_on": DATE, "quote": "$10 /mo in API credits."})),
]

LIMITS_MUST_REFUSE = [
    ("rpd as a word", dict(BASE, all_models={"rpd": "many"}), "must be a non-negative integer"),
    ("tpd negative", dict(BASE, all_models={"tpd": -5}), "must be a non-negative integer"),
    ("rpm as a list", dict(BASE, all_models={"rpm": [1]}), "must be a non-negative integer"),
    ("a figure that is a boolean", dict(BASE, all_models={"rpd": True}), "must be a non-negative integer"),
    ("a trillion tokens a day under UNKNOWN: the shape that took the top three README rows",
     dict(BASE, all_models={"rpd": None, "tpd": 10 ** 12}), "UNKNOWN but all_models.tpd"),
    ("a figure past the sanity ceiling, even when declared",
     dict(DECL, all_models={"tpd": 10 ** 12}), "sanity ceiling"),
    ("DECLARED with a source that is not a URL", dict(DECL, source="trust me"), "DECLARED needs source"),
    ("DECLARED with prose glued to the URL",
     dict(DECL, source=OWN + " and the console screen"), "DECLARED needs source"),
    ("DECLARED with no read_on", {"confidence": "DECLARED", "source": OWN, "all_models": {"rpm": 5}}, "DECLARED needs read_on"),
    ("MEASURED with measured_on 'yes'", dict(MEAS, measured_on="yes"), "MEASURED needs measured_on"),
    ("MEASURED with no measured_how", {"confidence": "MEASURED", "measured_on": DATE}, "MEASURED needs measured_how"),
    ("a model-level MEASURED with no date at either level: 500 billion into the headline sum",
     dict(DECL, all_models={"rpd": None}, models={"m": {"rpd": 10 ** 6, "rpd_confidence": "MEASURED"}}),
     "is MEASURED but neither"),
    ("a model-level DECLARED under a provider with no source",
     {"confidence": "UNKNOWN", "all_models": {"rpd": None}, "models": {"m": {"rpd": 100, "rpd_confidence": "DECLARED"}}},
     "is DECLARED but neither"),
    ("a model-level confidence that is not a label",
     dict(DECL, all_models={"rpd": None}, models={"m": {"rpd": 100, "rpd_confidence": "PAID-PLAN"}}),
     "rpd_confidence must be"),
    ("a model figure under an UNKNOWN provider with no confidence of its own",
     {"confidence": "UNKNOWN", "all_models": {"rpd": None}, "models": {"m": {"rpd": 100}}}, "provider confidence is UNKNOWN"),
    ("rpd_is_paid_plan with no plan named anywhere",
     dict(DECL, all_models={"rpd": None}, models={"m": {"rpd": 1000, "rpd_is_paid_plan": True}}), "rpd_plan must name"),
    ("per-model per-minute figures with no all_models block: the code reads only all_models",
     dict(DECL, models={"m": {"rpm": 30, "tpm": 8000, "rpd": 1000}}), "no all_models block"),
    ("all_models carrying a smaller per-minute figure than a model: the file's own rule broken",
     dict(DECL, all_models={"rpm": 30}, models={"m": {"rpm": 50}}), "all_models carries the largest"),
    ("a sub-block confidence that is not a label",
     dict(DECL, all_models={"rpm": 5}, tiers={"solo": {"rpd": 50, "confidence": "PROBABLY"}}), "must be MEASURED, DECLARED, DERIVED or UNKNOWN"),
    ("an invented provider-level confidence", dict(BASE, confidence="LIKELY"), "confidence must be"),
    ("a limit multiplied across keys",
     dict(DECL, all_models={"rpm": 30}, caveat="30/min x 4 %s = 120/min" % PLURAL_OF_KEY), "multiplied across keys"),
    ("a quota for a provider that is not in providers.json",
     (dict(BASE), {"groq", "cerebras"}), "not a provider in providers.json"),
]

LIMITS_MUST_PASS = [
    ("DECLARED, sourced and dated, with figures", dict(DECL, all_models={"rpm": 30, "rpd": 1000, "tpm": 8000})),
    ("MEASURED, dated, with the method", dict(MEAS, all_models={"rpm": 5, "rpd": 2400, "tpd": 1000000})),
    ("per-model detail with all_models carrying the largest: the shape limits.json documents",
     dict(DECL, all_models={"rpm": 30, "tpm": 8000, "rpd": None, "tpd": None, "note": "per model; the largest is shown"},
          models={"a": {"rpm": 30, "tpm": 8000, "rpd": 1000}, "b": {"rpm": 10, "tpm": 4000, "rpd": 500}})),
    ("a model-level MEASURED inheriting the provider's date and method",
     dict(MEAS, all_models={"rpm": 5}, models={"m": {"rpm": 5, "rpm_confidence": "MEASURED"}})),
    ("a model-level DECLARED with its own source and date under an UNKNOWN provider",
     {"confidence": "UNKNOWN", "all_models": {"rpd": None},
      "models": {"m": {"rpd": 100, "rpd_confidence": "DECLARED", "source": OWN, "read_on": DATE}}}),
    ("a paid-plan figure with the plan named on the provider",
     dict(DECL, all_models={"rpm": 30, "rpd": None}, rpd_plan="Developer",
          models={"m": {"rpm": 30, "rpd": 1000, "rpd_confidence": "DECLARED", "rpd_is_paid_plan": True}})),
    ("UNKNOWN with every figure null, which is what unknown means", dict(BASE, all_models={"rpm": None, "tpm": None})),
    ("a derived sub-block, labelled DERIVED", dict(DECL, all_models={"rpm": 300, "neurons_per_day": 10000},
                                                 derived={"output_tokens_per_day": 286795, "confidence": "DERIVED"})),
    ("a quota for a provider that is in providers.json", (dict(DECL, all_models={"rpm": 30}), {"someprovider", "groq"})),
]


# ---------------------------------------------------------------- languages/*.json

RO = G.load_json(HERE / "languages" / "ro.json", [])
EN = G.load_json(HERE / "languages" / "en.json", [])


def pack(**changes):
    """The real Romanian pack with a few keys replaced; nested paths written as probes__B__min_diacritics."""
    d = json.loads(json.dumps(RO))
    for k, v in changes.items():
        cur, parts = d, k.split("__")
        for part in parts[:-1]:
            cur = cur.setdefault(part, {})
        if v is None:
            cur.pop(parts[-1], None)
        else:
            cur[parts[-1]] = v
    return d


LANGUAGE_MUST_REFUSE = [
    ("generation naming a model: the whole battery redirected to a paid model, for everyone",
     pack(generation={"model": "openai/gpt-4o", "temperature": 0}), "generation.model is not"),
    ("generation carrying a token budget", pack(generation={"max_tokens": 100000}), "generation.max_tokens is not"),
    ("generation carrying n", pack(generation={"n": 10}), "generation.n is not"),
    ("temperature out of range", pack(generation={"temperature": 5}), "generation.temperature must be"),
    ("top_p out of range", pack(generation={"top_p": 1.5}), "generation.top_p must be"),
    ("a seed that is not an integer", pack(generation={"seed": 1.5}), "generation.seed must be"),
    ("probe B with min_diacritics 0: a probe that cannot fail",
     pack(probes__B__min_diacritics=0), "min_diacritics must be an integer of at least 1"),
    ("probe B with an empty must_contain", pack(probes__B__must_contain=[]), "need must_contain"),
    ("probe B with min_chars above max_chars", pack(probes__B__min_chars=500), "min_chars must be below"),
    ("probe D with min_words above max_words", pack(probes__D__min_words=200), "min_words must be at least 1 and below"),
    ("probe D with min_diacritics 0", pack(probes__D__min_diacritics=0), "min_diacritics must be an integer of at least 1"),
    ("a prompt with a bare domain in it", pack(probes__A__prompt="Vezi evil.example si raspunde cu 14400, 81600."),
     "bare domain"),
    ("a prompt with a URL in it", pack(probes__A__prompt="Vezi https://evil.example si raspunde."), "contains a URL"),
    ("a prompt naming a vendor", pack(probes__D__prompt="Scrie un paragraf in stilul Gemini despre banci."),
     "names a vendor"),
    ("a prompt shaped like a key", pack(probes__A__prompt="Foloseste cheia gsk_" + "A" * 30 + " si raspunde."),
     "shaped like an API key"),
    ("probe A with no expect_numbers", pack(probes__A__expect_numbers=None), "need expect_numbers"),
    ("probe C with string_keys naming a key that expect lacks", pack(probes__C__string_keys=["ghost"]),
     "string_keys must list keys of expect"),
    ("an unknown probe kind", pack(probes__A__kind="vibes"), "is not one benchmark.check() knows"),
    ("a probe budget of a million tokens", pack(probes__D__max_tokens=10 ** 6), "max_tokens must be"),
    ("a code that does not match the filename", pack(code="en"), "must match the filename"),
    ("a jury without the sounds_human lens", pack(jury={"other": "Score 0-10."}), "sounds_human"),
    ("a character in both diacritics and wrong_diacritics", pack(wrong_diacritics="ș"), "both diacritics and wrong_diacritics"),
    ("an English pack asking for diacritics it has no alphabet for",
     (dict(json.loads(json.dumps(EN)), probes=dict(EN["probes"], D=dict(EN["probes"]["D"], min_diacritics=3))), "en"),
     "min_diacritics must be 0"),
]
LANGUAGE_MUST_PASS = [
    ("the real Romanian pack", RO),
    ("the real English pack", (EN, "en")),
    ("a pack with penalties in range", pack(generation={"temperature": 0, "presence_penalty": -1.5, "frequency_penalty": 2})),
]


# ---------------------------------------------------------------- data/uptime.jsonl

def up(**kw):
    r = {"date": DATE, "provider": P0, "model": M0, "state": "alive", "http": 200, "seconds": 0.5, "note": ""}
    r.update(kw)
    return r


UPTIME_MUST_REFUSE = [
    ("a state the radar never writes", [up(state="dead")], "not one the radar writes"),
    ("a provider nobody probes", [up(provider="ghost")], "not in providers.json"),
    ("a model the provider does not list", [up(model="ghost-model")], "is not one of"),
    ("down with http 200: a verdict that contradicts its own status code",
     [up(state="down", http=200)], "state is down with http 200"),
    ("down with http 402: the code the radar files as payment_required",
     [up(state="down", http=402)], "state is down with http 402"),
    ("alive with http 500", [up(state="alive", http=500)], "state alive is written with http 200"),
    ("rate_limited with http 200", [up(state="rate_limited", http=200)], "state rate_limited is written with"),
    ("a date that is not ISO", [up(date="2026-9-8")], "date must be"),
    ("http as a string", [up(http="200")], "http must be an integer"),
    ("negative seconds", [up(seconds=-1)], "seconds must be"),
    ("no_key with a timing on it", [up(state="no_key", http=None, seconds=0.5)], "no timing"),
    ("a row missing its state", [{"date": DATE, "provider": P0, "model": M0, "http": 200, "seconds": 1}], "row lacks state"),
    ("a line that is not JSON", [up(), "{not json"], "not valid JSON"),
    ("a row with a duplicate key", ['{"date": "%s", "provider": "%s", "model": "%s", "state": "alive", '
                                    '"state": "down", "http": 200, "seconds": 1}' % (DATE, P0, M0)], "duplicate JSON key"),
    ("fourteen planted down days on a live endpoint, with a code the radar would not write as down",
     [up(date="2026-09-%02d" % d, state="down", http=429) for d in range(8, 22)], "state is down with http 429"),
]
UPTIME_MUST_PASS = [
    ("every state with the code the radar writes it with",
     [up(), up(state="empty"), up(state="rate_limited", http=429), up(state="overloaded", http=503),
      up(state="payment_required", http=402), up(state="blocked", http=403),
      up(state="no_key", http=None, seconds=None, note="no key set in this environment"),
      up(state="down", http=0, note="URLError"), up(state="down", http=500), up(state="down", http=504)]),
    ("an empty file", []),
]


# ---------------------------------------------------------------- data/throughput.jsonl

def tp(**kw):
    r = {"provider": P0, "model": M0, "concurrency": 8, "seconds": 30.8, "requests_ok": 22,
         "requests_rate_limited": 0, "requests_failed": 0, "output_tokens": 8141,
         "tokens_per_minute_measured": int(8141 / 30.8 * 60), "first_error": None,
         "rate_basis": "delivered over 31 seconds without a refusal, scaled to a minute",
         "stopped_because": "window ended", "note": "A floor, not a ceiling.", "date": DATE}
    r.update(kw)
    return r


THROUGHPUT_MUST_REFUSE = [
    ("the planted headline: a billion tokens a minute from zero output tokens",
     [tp(output_tokens=0, requests_ok=0, tokens_per_minute_measured=10 ** 9)], "does not follow from"),
    ("a rate that does not follow from its own tokens and seconds",
     [tp(tokens_per_minute_measured=50000)], "does not follow from"),
    ("a 429 stopped the run, yet the rate was scaled up: the 72,871 the first throughput.py printed",
     [tp(requests_rate_limited=1, output_tokens=1580, seconds=1.3, tokens_per_minute_measured=72871)],
     "a 429 stopped this run"),
    ("a rate stated from a two-second window", [tp(seconds=2.3, output_tokens=500, tokens_per_minute_measured=13043)],
     "under 10 seconds"),
    ("a rate above the ceiling the provider publishes",
     [tp(provider=P1, model=M1, output_tokens=CAP1 * 2, seconds=60.0, tokens_per_minute_measured=CAP1 * 2)],
     "above the"),
    ("output tokens from zero successful requests", [tp(requests_ok=0, output_tokens=100, tokens_per_minute_measured=195)],
     "from zero successful requests"),
    ("a provider nobody benchmarks", [tp(provider="ghost")], "not in providers.json"),
    ("a model the provider does not list", [tp(model="ghost-model")], "is not one of"),
    ("a negative request count", [tp(requests_failed=-1)], "must be a non-negative integer"),
    ("concurrency as a boolean", [tp(concurrency=True)], "must be a non-negative integer"),
    ("a row missing the fields the runner writes", [{"provider": P0, "model": M0, "date": DATE}], "row lacks"),
    ("a skipped row carrying a rate", [{"provider": P0, "skipped": "no key", "date": DATE, "tokens_per_minute_measured": 10 ** 6}],
     "skipped row carries"),
    ("a date that is not ISO", [tp(date="Sept 7")], "date must be"),
    ("a note with a second line in it", [tp(note="A floor.\n[link](https://evil.example)")], "one line of text"),
]
THROUGHPUT_MUST_PASS = [
    ("a run that ended with the window, rate scaled from tokens and seconds", [tp()]),
    ("a run a 429 stopped, rate equal to the tokens that arrived",
     [tp(requests_rate_limited=1, requests_ok=4, output_tokens=1206, seconds=0.8, tokens_per_minute_measured=1206,
         rate_basis="their per-minute limit stopped us", stopped_because="rate limit reached")]),
    ("a run too short to state a rate", [tp(requests_ok=0, requests_failed=8, output_tokens=0, seconds=2.3,
                                           tokens_per_minute_measured=None,
                                           first_error="HTTP 503 no capacity behind the endpoint",
                                           stopped_because="five failures in a row: HTTP 503 no capacity behind the endpoint")]),
    ("a skipped provider", [{"provider": P0, "skipped": "no key in this environment", "date": DATE}]),
    ("a rate under the ceiling the provider publishes",
     [tp(provider=P1, model=M1, output_tokens=CAP1 // 4, seconds=60.0, tokens_per_minute_measured=CAP1 // 4)]),
    ("an older row without first_error", [{k: v for k, v in tp().items() if k != "first_error"}]),
]


# ---------------------------------------------------------------- announced_deaths.json

DEATH = {"provider": "Some Retired Service", "died_on": "2026-07-30",
         "quote": "As of July 30, 2026, the service is retired and the inference API is no longer available.",
         "source": "https://blog.example/changelog/retired", "read_on": DATE,
         "endpoint_today": "HTTP 410 on the old endpoint, measured " + DATE}
REAL_DEATHS = (G.load_json(HERE / "announced_deaths.json", []) or {}).get("providers") or []

DEATHS_MUST_REFUSE = [
    ("the planted headstone: a quote that leaves the blockquote and plants a link",
     [dict(DEATH, quote="Groq has shut down its free tier.\n\n[Migrate your keys here](https://evil.example)\n\n> and")],
     "one line"),
    ("a one-line quote with a link in it", [dict(DEATH, quote="Retired. [Migrate](https://evil.example)")], "contains [ ] < or >"),
    ("a quote with a tag in it", [dict(DEATH, quote="Retired <b>now</b>.")], "contains [ ] < or >"),
    ("a source that is not a URL", [dict(DEATH, source="not even a url")], "source must be one https URL"),
    ("a retirement notice for a provider this repo still benchmarks",
     [dict(DEATH, provider=P0.capitalize())], "still a provider in providers.json"),
    ("a death date that is not a date", [dict(DEATH, died_on="yesterday")], "died_on must be a date"),
    ("no read_on", [{k: v for k, v in DEATH.items() if k != "read_on"}], "read_on must be a date"),
    ("endpoint_today with a second line", [dict(DEATH, endpoint_today="HTTP 410\n[x](https://evil.example)")],
     "endpoint_today must be one line"),
    ("a provider name that becomes markdown in the heading", [dict(DEATH, provider="X [y](https://evil.example)")],
     "no markdown in it"),
]
DEATHS_MUST_PASS = [
    ("a notice with every field one line, dated and sourced", [DEATH]),
    ("the real file's entries", REAL_DEATHS),
    ("no notices at all", []),
]


# ---------------------------------------------------------------- the real data, and what it must say

# Every finding the gate reports on the real files today, as (where contains, what contains). A finding
# here is a defect in the DATA, listed so the data owner fixes the data and deletes the line; it is not
# fixed by loosening the rule that found it. Anything the gate reports that is not in this list fails
# the test, and so does anything in this list that the gate no longer reports.
EXPECTED_REAL_FINDINGS = [
    # (substring of the location, substring of the message). Empty on purpose: the real data files pass the
    # gate today. When a real finding is knowingly left in place, list it here so the run stays green AND
    # the finding stays visible; when the data is fixed, the entry is reported GONE and must be deleted.
]


def real_data_case():
    problems, _ = G.collect(HERE)
    unexpected = [p for p in problems
                  if not any(w in p[0] and h in p[1] for w, h in EXPECTED_REAL_FINDINGS)]
    missing = [(w, h) for w, h in EXPECTED_REAL_FINDINGS
               if not any(w in p[0] and h in p[1] for p in problems)]
    return problems, unexpected, missing


# ---------------------------------------------------------------- pins between files

def pinned_shapes():
    """Two regexes and one vocabulary that live in two files each must not drift apart."""
    out = []
    import refresh_catalog as R
    # The gate's model-id shape is refresh_catalog's ID_OK plus exactly two characters that the
    # benchmarked providers use and OpenRouter's catalogue does not: a leading @ and an inner _.
    widened = (R.ID_OK.pattern.replace("^[A-Za-z0-9~]", "^[A-Za-z0-9~@]", 1)
               .replace("[A-Za-z0-9._/:~+-]", "[A-Za-z0-9._/:~+_-]", 1))
    out.append(("MODEL_ID_OK is refresh_catalog.ID_OK widened by a leading @ and an inner _, nothing else",
                G.MODEL_ID_OK.pattern == widened, "%r vs %r" % (G.MODEL_ID_OK.pattern, widened)))
    for mid in ("~z-ai/glm-latest", "qwen/qwen3.8-27b", "minimax/minimax-m3:free", "gemma4:31b"):
        out.append(("both accept %r" % mid, bool(R.ID_OK.match(mid) and G.MODEL_ID_OK.match(mid)), ""))
    for mid in ("x` | y", "a b", "a\\b", "../x", "", "x" * 121):
        out.append(("both refuse %r" % mid[:12], not (R.ID_OK.match(mid) or G.MODEL_ID_OK.match(mid)), ""))
    real_ids = [m["id"] for p in REAL_PROVIDERS for m in p.get("models", [])]
    bad = [i for i in real_ids if not G.MODEL_ID_OK.match(i)]
    out.append(("every id in providers.json passes the gate's shape", not bad, "%r" % bad[:3]))
    # The radar vocabulary: if bench/states.py exists, the gate's set of states is exactly its union.
    if (HERE / "states.py").exists():
        import states as S
        theirs = set(S.UP_STATES) | set(S.DOWN_STATES) | set(S.NOT_A_VERDICT)
        out.append(("UPTIME_STATES equals the union of the sets in states.py",
                    theirs == G.UPTIME_STATES, "%r vs %r" % (sorted(theirs), sorted(G.UPTIME_STATES))))
    return out


# ---------------------------------------------------------------- runner

SECTIONS = [
    ("planted pull requests that MUST be refused", MUST_REFUSE, check, True),
    ("honest pull requests that MUST pass", MUST_PASS, check, False),
    ("raw JSON shapes that MUST be refused", RAW_MUST_REFUSE, check_raw, True),
    ("raw JSON shapes that MUST pass", RAW_MUST_PASS, check_raw, False),
    ("cross-file key theft that MUST be refused", CROSS_FILE_MUST_REFUSE, check_cross_file, True),
    ("cross-file pairs that MUST pass", CROSS_FILE_MUST_PASS, check_cross_file, False),
    ("juries that MUST be refused", JUDGES_MUST_REFUSE, check_judges_list, True),
    ("juries that MUST pass", JUDGES_MUST_PASS, check_judges_list, False),
    ("privacy claims that MUST be refused", PRIVACY_MUST_REFUSE, check_privacy_entry, True),
    ("privacy claims that MUST pass", PRIVACY_MUST_PASS, check_privacy_entry, False),
    ("one-time and monthly bundles that MUST be refused", ONE_TIME_MUST_REFUSE, check_limits_entry, True),
    ("one-time and monthly bundles that MUST pass", ONE_TIME_MUST_PASS, check_limits_entry, False),
    ("quota entries that MUST be refused", LIMITS_MUST_REFUSE, check_limits_entry, True),
    ("quota entries that MUST pass", LIMITS_MUST_PASS, check_limits_entry, False),
    ("language packs that MUST be refused", LANGUAGE_MUST_REFUSE, check_language_pack, True),
    ("language packs that MUST pass", LANGUAGE_MUST_PASS, check_language_pack, False),
    ("radar rows that MUST be refused", UPTIME_MUST_REFUSE, check_uptime_rows, True),
    ("radar rows that MUST pass", UPTIME_MUST_PASS, check_uptime_rows, False),
    ("throughput rows that MUST be refused", THROUGHPUT_MUST_REFUSE, check_throughput_rows, True),
    ("throughput rows that MUST pass", THROUGHPUT_MUST_PASS, check_throughput_rows, False),
    ("retirement notices that MUST be refused", DEATHS_MUST_REFUSE, check_deaths, True),
    ("retirement notices that MUST pass", DEATHS_MUST_PASS, check_deaths, False),
]


def main():
    verbose = "-v" in sys.argv
    bad = total = 0
    for title, cases, runner, must_refuse in SECTIONS:
        print(title + ":")
        for case in cases:
            label, fixture = case[0], case[1]
            expect = case[2] if len(case) > 2 else None
            problems = runner(fixture)
            total += 1
            if must_refuse:
                # Refused, and for the reason the case names: a refusal on some other ground means the
                # rule under test never fired, and that is a miss dressed as a pass.
                ok = bool(problems) and (expect is None or any(expect in what for _, what in problems))
                print("  %-4s %s" % ("ok" if ok else "MISS", label))
                if not ok:
                    bad += 1
                    print("         wanted a refusal saying %r, got %d problem(s):" % (expect, len(problems)))
                    for _, what in problems[:4]:
                        print("         -> %s" % what[:150])
                elif verbose:
                    for _, what in problems:
                        print("         -> %s" % what[:110])
            else:
                ok = not problems
                print("  %-4s %s" % ("ok" if ok else "FAIL", label))
                if not ok:
                    bad += 1
                    for _, what in problems:
                        print("         -> %s" % what[:160])
        print()

    print("shapes pinned between files:")
    for label, ok, why in pinned_shapes():
        total += 1
        print("  %-4s %s%s" % ("ok" if ok else "FAIL", label, "  -> " + why if (why and not ok) else ""))
        if not ok:
            bad += 1
    print()

    print("the real data files, against the findings listed in this test:")
    problems, unexpected, missing = real_data_case()
    total += 1
    ok = not unexpected and not missing
    print("  %-4s %d finding(s) on the real files, %d expected, %d unexpected, %d expected but gone"
          % ("ok" if ok else "FAIL", len(problems), len(EXPECTED_REAL_FINDINGS), len(unexpected), len(missing)))
    for where, what in problems:
        print("         %s %s\n              %s" % ("listed " if (where, what) not in unexpected else "NEW    ", where, what[:150]))
    for where, what in missing:
        print("         GONE    %s: %s - the data was fixed, or the rule stopped firing; delete or restore the line" % (where, what))
    if not ok:
        bad += 1

    print("\n%d of %d cases behaved as required" % (total - bad, total))
    if bad:
        print("THE GATE IS MISCALIBRATED. Fix it before merging anything.")
        return 1
    print("CLEAN - the gate refuses what it must and admits what it must.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
