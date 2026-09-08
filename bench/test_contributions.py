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

The third round of planted pull requests is here too: the row appended to data/drawn.jsonl that put
24 billion tokens a day on the headline, the URL swap between two existing providers that sent each
runner's key to the other host, the caveat that planted a phishing link on three generated pages, the
reasoning budget that rode in through extra_body, the future-dated radar rows that buried a live
endpoint. Each is refused for the reason stated, and each has an honest neighbour that passes.

The fourth round planted numbers UNDER the ceilings: 9,900,000,000 tokens a day under a ceiling of ten
billion, fourteen down days dated before the endpoint's own last reading (a shape this file used to
assert MUST PASS), 20,000 answers in thirty seconds, a retirement notice on a paste site, a judge from
a benchmarked family, an archive nobody recounted. Each is refused for the reason stated, each has an
honest neighbour that passes, and the daily ceilings are pinned to bench/rank.py's own target.

The last section runs the REAL data files through the whole gate and compares what it finds with a
list stated out loud below. Real findings are not fixed by loosening a rule; they are listed, so the
data owner can fix the data and delete the line.
"""
import json, re, sys, tempfile
from datetime import date, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gate_contributions as G
import draw_day as D
import throughput as T

OK_HOST = "https://api.groq.com/openai/v1/chat/completions"
KEYLESS_HOST = "https://hermes.ai.unturf.com/v1/chat/completions"
CEREBRAS_HOST = "https://api.cerebras.ai/v1/chat/completions"
ALIBABA_HOST = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1/chat/completions"
JUDGE_HOST = "https://api.z.ai/api/coding/paas/v4/chat/completions"
M = [{"id": "llama-3.3-70b"}]        # one honest model, for entries whose point lies elsewhere
DATE = "2026-09-07"
# The fixture clock. Every data-file runner below hands the gate this `today`, so a row dated FUTURE
# is refused on any real day, and a row dated DATE is old enough to lack the fields added later.
TODAY = date(2026, 9, 8)
FUTURE = "2026-09-09"
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


def check_jury_scoped(fixture):
    """The jury with a declared scope: families are checked against results/<run>/raw.json of the runs
    it scored, whatever providers.json lists today. `runs` maps a run date to the model ids its raw.json
    names; None for a run that is declared and has no raw.json."""
    scope, judges, providers, runs = fixture
    problems = []
    with tempfile.TemporaryDirectory() as d:
        bench = Path(d) / "bench"
        bench.mkdir()
        for run, ids in runs.items():
            if ids is None:
                continue
            rd = Path(d) / "results" / run
            rd.mkdir(parents=True)
            (rd / "raw.json").write_text(json.dumps({"run": run, "results": [{"model": m, "ok": True} for m in ids]}),
                                         encoding="utf-8")
        doc = {"judges": judges}
        if scope is not None:
            doc["scope"] = scope
        path = bench / "judges.json"
        path.write_text(json.dumps(doc), encoding="utf-8")
        G.check_judges(path, problems, providers=providers)
    return problems


def check_jury_against(fixture):
    """The jury against a providers list, the way collect() runs it: a judge may not share a family
    with a benchmarked model."""
    judges, providers = fixture
    problems = []
    with tempfile.TemporaryDirectory() as d:
        G.check_judges(_write(d, "judges.json", {"judges": judges}), problems, providers=providers)
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
    """The quota half over one provider entry; a (entry, known names) pair adds the cross-file check.
    The provider's API host is api.groq.com, so its own domain is groq.com and every `source` must
    sit there: a paste site is a foreign domain."""
    if isinstance(fixture, tuple):
        entry, names = fixture[0], fixture[1]
        who = fixture[2] if len(fixture) > 2 else ("someprovider", "api.groq.com")
    else:
        entry, names, who = fixture, None, ("someprovider", "api.groq.com")
    name, host = who
    problems = []
    with tempfile.TemporaryDirectory() as d:
        G.check_limits(_write(d, "limits.json", {"providers": {name: entry}}), problems, names, hosts={name: host})
    return problems


def check_bindings(fixture):
    """providers.json, judges.json and the registry, on ONE binding map - the way collect() runs them.
    A registry of None means the file is missing."""
    providers, judges, registry = fixture
    problems = []
    maps = G.new_bindings()
    with tempfile.TemporaryDirectory() as d:
        G.check_providers(_write(d, "providers.json", {"providers": providers}), problems, maps)
        G.check_judges(_write(d, "judges.json", {"judges": judges}), problems, maps)
        reg_path = Path(d) / G.REGISTRY
        if registry is not None:
            _write(d, G.REGISTRY, {"bindings": registry})
        G.check_key_bindings(reg_path, problems, maps)
    return problems


def check_language_pack(fixture):
    pack, code = fixture if isinstance(fixture, tuple) else (fixture, "ro")
    problems = []
    with tempfile.TemporaryDirectory() as d:
        G.check_language(_write(d, code + ".json", pack), problems, providers=REAL_PROVIDERS)
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
        G.check_uptime(_write(d, "uptime.jsonl", text), problems, REAL_PROVIDERS, today=TODAY)
    return problems


def check_throughput_rows(rows):
    problems = []
    with tempfile.TemporaryDirectory() as d:
        text = "\n".join(r if isinstance(r, str) else json.dumps(r) for r in rows) + "\n"
        G.check_throughput(_write(d, "throughput.jsonl", text), problems, REAL_PROVIDERS, REAL_LIMITS, today=TODAY)
    return problems


def check_drawn_rows(rows):
    problems = []
    with tempfile.TemporaryDirectory() as d:
        text = "\n".join(r if isinstance(r, str) else json.dumps(r) for r in rows) + "\n"
        G.check_drawn(_write(d, "drawn.jsonl", text), problems, REAL_PROVIDERS, REAL_LIMITS, today=TODAY)
    return problems


def check_deaths(entries):
    problems = []
    with tempfile.TemporaryDirectory() as d:
        G.check_announced_deaths(_write(d, "announced_deaths.json", {"providers": entries}), problems, REAL_PROVIDERS)
    return problems


def check_reliability_doc(fixture):
    """One archive document against a results/ tree. The fixture is the document, or (document, raw rows)
    where the rows are written as results/<run>/raw.json for the recount; a document alone is recounted
    against the raw run its own `providers` rows describe, so a shape case tests the shape and nothing
    else. None for the rows means no results/ at all."""
    doc, raw = fixture if isinstance(fixture, tuple) else (fixture, "derive")
    if raw == "real":
        return check_reliability_real(doc)
    problems = []
    with tempfile.TemporaryDirectory() as d:
        results = Path(d) / "results"
        if raw == "derive":
            raw = raw_rows_for(doc)
        if raw is not None:
            for run in (doc.get("runs_included") if isinstance(doc.get("runs_included"), list) else ["2026-09-06"]):
                run = run if isinstance(run, str) and run else "2026-09-06"
                (results / run).mkdir(parents=True, exist_ok=True)
                (results / run / "raw.json").write_text(json.dumps({"rows": [r for r in raw if r.get("_run", run) == run]}),
                                                        encoding="utf-8")
        G.check_reliability(_write(d, "reliability.json", doc), problems, REAL_PROVIDERS, today=TODAY, results=results)
    return problems


def raw_rows_for(doc):
    """Raw rows that would produce exactly the archive `doc` describes: its counts per provider, its
    observed empty 200s on their probes. What bench/reliability.py would have counted, run backwards."""
    rows, runs = [], doc.get("runs_included") if isinstance(doc.get("runs_included"), list) else ["2026-09-06"]
    run0 = runs[0] if runs and isinstance(runs[0], str) else "2026-09-06"
    trap = doc.get("reasoning_trap") if isinstance(doc.get("reasoning_trap"), dict) else {}
    empties = [t for t in (trap.get("observed") or []) if isinstance(t, dict)]
    for r in (doc.get("providers") or []):
        if not isinstance(r, dict) or not isinstance(r.get("calls"), int):
            continue
        prov = r.get("provider")
        mine = [t for t in empties if t.get("provider") == prov]
        code_of = {"ok": (200, "text"), "empty_200": (200, ""), "rate_limited": (429, ""), "overloaded": (503, ""),
                   "timeout": (0, ""), "other": (402, "")}
        for k, (code, text) in code_of.items():
            n = r.get(k) if isinstance(r.get(k), int) else 0
            for i in range(n):
                t = mine[i] if k == "empty_200" and i < len(mine) else {}
                rows.append({"provider": prov, "model": t.get("model", M0), "probe": t.get("probe", "A"),
                             "http": code, "text": text, "_run": t.get("run", run0)})
    return rows


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

    # --- extra_body: merged into the request LAST, so it can rewrite the request. An ALLOWLIST: the
    # keys that rewrite the request get their own message, everything else is refused as not a switch.
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
     [prov(models=[{"id": "m", "extra_body": {"system": "x" * 300}}])], G.EXTRA_BODY_REFUSED),
    ("extra_body with nine unknown keys: that is a request, not a switch",
     [prov(models=[{"id": "m", "extra_body": {"k%d" % i: i for i in range(9)}}])], G.EXTRA_BODY_REFUSED),
    ("extra_body with a stop list in it",
     [prov(models=[{"id": "m", "extra_body": {"stop": ["a", "b"]}}])], G.EXTRA_BODY_REFUSED),
    ("extra_body nested four levels deep under an unknown key",
     [prov(models=[{"id": "m", "extra_body": {"a": {"b": {"c": {"d": 1}}}}}])], G.EXTRA_BODY_REFUSED),
    ("extra_body that is not an object",
     [prov(models=[{"id": "m", "extra_body": "reasoning_effort=low"}])], "must be a JSON object"),
    ("the reviewer's plant: a reasoning budget of 100,000 billed outside max_tokens, and two output caps "
     "under other names, none of them in the denylist",
     [prov(models=[{"id": "m", "extra_body": {"thinking": {"type": "enabled", "budget_tokens": 100000},
                                             "max_output_tokens": 999999999, "num_predict": 999999999}}])],
     G.EXTRA_BODY_REFUSED),
    ("a stop sequence of one full stop on another provider's model: every reply truncated, its answered rate collapses",
     [prov(models=[{"id": "m", "extra_body": {"stop": "."}}])], G.EXTRA_BODY_REFUSED),
    ("thinking with a budget riding along inside the allowed switch",
     [prov(models=[{"id": "m", "extra_body": {"thinking": {"type": "enabled", "budget_tokens": 1024}}}])],
     "no budget_tokens"),
    ("a reasoning_effort value the runner does not document",
     [prov(models=[{"id": "m", "extra_body": {"reasoning_effort": "xhigh"}}])], "one of low, medium, high"),
    ("enable_thinking as a string, which some servers read as true",
     [prov(models=[{"id": "m", "extra_body": {"enable_thinking": "false"}}])], "true or false"),
    ("chat_template_kwargs carrying a second key beside the switch",
     [prov(models=[{"id": "m", "extra_body": {"chat_template_kwargs": {"enable_thinking": False, "add_generation_prompt": True}}}])],
     "nothing else"),
    ("a generation parameter in extra_body: it belongs in the language pack, where every model gets the same one",
     [prov(models=[{"id": "m", "extra_body": {"temperature": 0.7, "reasoning_effort": "low"}}])], G.EXTRA_BODY_REFUSED),

    # --- the endpoint: right host, wrong door
    ("path swap on an allowed host: the key still goes to groq, but to audio transcription",
     [prov(url="https://api.groq.com/openai/v1/audio/transcriptions")], "url path must end with"),
    ("path with a traversal in it",
     [prov(url="https://api.groq.com/openai/v1/../v1/chat/completions")], "url path must end with"),
    ("a query string on the endpoint",
     [prov(url=OK_HOST + "?api-version=2")], "query string"),
    ("an allowed host on another port: another listener is another party, the rule http_safe applies to redirects",
     [prov(url="https://api.groq.com:8443/openai/v1/chat/completions")], "writes a port"),
    ("the default port written out: still somebody typing a port on an endpoint that has no reason to carry one",
     [prov(url="https://api.groq.com:443/openai/v1/chat/completions")], "writes a port"),
    ("a port that does not parse",
     [prov(url="https://api.groq.com:notaport/openai/v1/chat/completions")], "writes a port"),
    ("the Cloudflare account placeholder on a groq URL: the account id goes to groq in the path",
     [prov(url="https://api.groq.com/openai/{CF_ACCOUNT_ID}/v1/chat/completions")],
     "belongs to api.cloudflare.com"),
    ("an undeclared placeholder that would put a second key in the path",
     [prov(url="https://api.groq.com/openai/{OPENROUTER_API_KEY}/v1/chat/completions")], "url interpolates"),

    # --- names and keys
    ("provider 'a' claiming ALIBABA_API_KEY on Alibaba's own host: a one-letter name owns every key",
     [{"name": "a", "url": ALIBABA_HOST, "key_env": "ALIBABA_API_KEY", "models": M}], "does not name this provider"),
    ("the reviewer's plant: a provider called 'api' claiming GROQ_API_KEY on the groq host, a second row on "
     "the same account, which the substring rule admitted because API is in GROQAPIKEY",
     [prov(), {"name": "api", "url": OK_HOST, "key_env": "GROQ_API_KEY", "models": M}], "does not name this provider"),
    ("a generic word as a name, with a key variable to match",
     [{"name": "free", "url": OK_HOST, "key_env": "FREE_API_KEY", "models": M}], "does not name this provider"),
    ("a three-letter name with its own variable: under the four-character floor",
     [{"name": "roq", "url": OK_HOST, "key_env": "ROQ_API_KEY", "models": M}], "does not name this provider"),
    ("a name that is a prefix of the variable's stem, not equal to it",
     [{"name": "gro", "url": OK_HOST, "key_env": "GROQ_API_KEY", "models": M}], "does not name this provider"),
    ("a lookalike name one letter off the variable's stem",
     [{"name": "grok", "url": OK_HOST, "key_env": "GROQ_API_KEY", "models": M}], "does not name this provider"),
    ("a key variable that does not end in _API_KEY or _API_TOKEN",
     [prov(key_env="GROQ_KEY")], "does not name this provider"),
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
    ("the reviewer's plant: every generation parameter declared unsupported, so this provider's runs are made "
     "under settings no other provider's are, and its scores compare with nothing",
     [prov(unsupported_params=sorted(G.GENERATION), unsupported_measured_on=DATE)], "every generation parameter"),
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
    ("every documented switch in its documented shape, one per model",
     [prov(models=[{"id": "a", "extra_body": {"reasoning_effort": "low"}},
                   {"id": "b", "extra_body": {"reasoning_effort": "high"}},
                   {"id": "c", "extra_body": {"enable_thinking": False}},
                   {"id": "d", "extra_body": {"enable_thinking": True}},
                   {"id": "e", "extra_body": {"thinking": {"type": "disabled"}}},
                   {"id": "f", "extra_body": {"thinking": {"type": "enabled"}}},
                   {"id": "g", "extra_body": {"reasoning_effort": "medium", "enable_thinking": False}}])]),
    ("a name with a hyphen whose variable spells it with an underscore: the same stem",
     [{"name": "some-provider", "url": OK_HOST, "key_env": "SOME_PROVIDER_API_KEY", "models": M}]),
    ("a key variable ending in _API_TOKEN",
     [{"name": "groq", "url": OK_HOST, "key_env": "GROQ_API_TOKEN", "models": M}]),
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
    ("all but one generation parameter unsupported: one is still sent, so the runs still compare",
     [prov(unsupported_params=sorted(G.GENERATION)[:-1], unsupported_measured_on=DATE)]),
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

# --- the registry: where each key variable may go, remembered across pull requests
REAL_JUDGES = (_real("judges.json") or {}).get("judges") or []
REAL_REGISTRY = ((_real(G.REGISTRY) or {}).get("bindings")) or {}
GROQ_BINDING = {"host": "api.groq.com", "role": "provider"}
ZAI_BINDING = {"host": "api.z.ai", "role": "judge"}


def _swapped(providers, a, b):
    """The real providers with two URLs exchanged and every key variable left where it was."""
    out = json.loads(json.dumps(providers))
    ua = next(p["url"] for p in out if p["name"] == a)
    ub = next(p["url"] for p in out if p["name"] == b)
    for p in out:
        if p["name"] == a:
            p["url"] = ub
        elif p["name"] == b:
            p["url"] = ua
    return out


BINDINGS_MUST_REFUSE = [
    ("the reviewer's plant: the real file with groq's and cerebras's URLs swapped, key variables untouched - each "
     "runner's Groq key goes to Cerebras and Cerebras key to Groq, and within the file each variable still "
     "reaches exactly one host",
     (_swapped(REAL_PROVIDERS, "groq", "cerebras"), REAL_JUDGES, REAL_REGISTRY), "sends it to"),
    ("a new provider with no line in the registry",
     ([prov()], [JUDGE], {"ZAI_API_KEY": ZAI_BINDING}), "has no line in bench/key_bindings.json"),
    ("a registry line nobody uses, so the file cannot rot into a list nobody checks",
     ([prov()], [JUDGE], {"GROQ_API_KEY": GROQ_BINDING, "ZAI_API_KEY": ZAI_BINDING,
                          "GHOST_API_KEY": {"host": "api.cerebras.ai", "role": "provider"}}), "used by no provider or judge"),
    ("the judge's key registered as a provider key: the role is part of the binding",
     ([prov()], [JUDGE], {"GROQ_API_KEY": GROQ_BINDING, "ZAI_API_KEY": {"host": "api.z.ai", "role": "provider"}}),
     "sends it to"),
    ("a registry line with the role missing",
     ([prov()], [JUDGE], {"GROQ_API_KEY": {"host": "api.groq.com"}, "ZAI_API_KEY": ZAI_BINDING}), "a binding is"),
    ("no registry at all", ([prov()], [JUDGE], None), "missing"),
]
BINDINGS_MUST_PASS = [
    ("the real providers, the real judges and the real registry", (REAL_PROVIDERS, REAL_JUDGES, REAL_REGISTRY)),
    ("one provider and the two-family jury, each key with its line",
     ([prov()], [JUDGE, MANUAL], {"GROQ_API_KEY": GROQ_BINDING, "ZAI_API_KEY": ZAI_BINDING})),
    ("a keyless provider needs no line",
     ([{"name": "uncloseai", "url": KEYLESS_HOST, "auth": "none", "models": M}], [JUDGE, MANUAL], {"ZAI_API_KEY": ZAI_BINDING})),
]

JUDGES_MUST_REFUSE = [
    ("an invented via", [dict(JUDGE, via="email"), MANUAL], "via must be"),
    ("a via judges.json does not document: 'agent' was admitted by the gate and described by nothing",
     [JUDGE, dict(MANUAL, via="agent")], "via must be"),
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
    ("an api judge on the allowed host with a port written on it",
     [dict(JUDGE, url="https://api.z.ai:8443/api/coding/paas/v4/chat/completions"), MANUAL], "writes a port"),
    ("an api judge whose extra_body carries a thinking budget",
     [dict(JUDGE, extra_body={"thinking": {"type": "enabled", "budget_tokens": 50000}}), MANUAL], "no budget_tokens"),
    ("two judges with the same name", [JUDGE, dict(MANUAL, name="glm")], "duplicate judge name"),
]
JUDGES_MUST_PASS = [
    ("an api judge and a manual one with its note: the real jury's shape", [JUDGE, MANUAL]),
    ("the real jury", REAL_JUDGES),
    ("an api judge with a reasoning switch and a budget",
     [dict(JUDGE, extra_body={"thinking": {"type": "disabled"}}, max_tokens=600, pause_seconds=2), MANUAL]),
]

# The file's first rule, enforced against the models being judged rather than only between the judges.
JURY_MUST_REFUSE = [
    ("the reviewer's plant: a manual judge from the Alibaba Qwen family scoring a jury that benchmarks qwen models",
     ([JUDGE, dict(MANUAL, family="Alibaba Qwen")], [prov(models=[{"id": "qwen/qwen3.8-27b"}])]), "providers.json benchmarks"),
    ("a GLM judge beside a benchmarked GLM model under another provider's id shape",
     ([dict(JUDGE, family="z.ai GLM"), MANUAL], [prov(models=[{"id": "coding-glm-5.3-free"}])]), "providers.json benchmarks"),
    ("a judge whose family is one word of a benchmarked model id: gpt-oss is OpenAI's",
     ([dict(JUDGE, family="OpenAI GPT"), MANUAL], [prov(models=[{"id": "openai/gpt-oss-120b"}])]), "providers.json benchmarks"),
]
SCOPE = {"runs": ["2026-09-06"], "why": "the jury scored the archived run, not today's list"}
JURY_SCOPED_MUST_REFUSE = [
    ("a scoped jury whose run holds a relative of the judge",
     (SCOPE, [dict(JUDGE, family="z.ai GLM"), MANUAL], [prov(models=[{"id": "llama-3.3-70b"}])],
      {"2026-09-06": ["glm-4-7-flash:free", "llama-3.3-70b"]}), "the runs the jury scored hold"),
    ("a scope that names a run nobody can open",
     (SCOPE, [JUDGE, MANUAL], [prov()], {"2026-09-06": None}), "is not there"),
    ("a scope without why",
     ({"runs": ["2026-09-06"]}, [JUDGE, MANUAL], [prov()], {"2026-09-06": ["llama-3.3-70b"]}), "scope must be"),
    ("a scope whose run is not a date",
     ({"runs": ["latest"], "why": "x"}, [JUDGE, MANUAL], [prov()], {}), "scope must be"),
]
JURY_SCOPED_MUST_PASS = [
    ("a GLM judge over an archived run with no GLM in it, while providers.json lists a GLM model today: the "
     "jury scored the run, not the list",
     (SCOPE, [dict(JUDGE, family="z.ai GLM"), MANUAL], [prov(models=[{"id": "coding-glm-5.3-free"}])],
      {"2026-09-06": ["llama-3.3-70b", "gemma-4-31b"]})),
    ("no scope declared: the list of today is what the jury is checked against, as before",
     (None, [dict(JUDGE, family="z.ai GLM"), MANUAL], [prov(models=[{"id": "llama-3.3-70b"}])], {})),
]
JURY_MUST_PASS = [
    ("a GLM judge and a Claude judge over providers that serve neither family",
     ([dict(JUDGE, family="z.ai GLM"), MANUAL], [prov(models=[{"id": "llama-3.3-70b"}, {"id": "gemma-4-31b"}])])),
    ("a family word too short to match anything: 'ai' in 'z.ai' is not a family",
     ([dict(JUDGE, family="z.ai GLM"), MANUAL], [prov(models=[{"id": "aion-2.0:free"}])])),
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
PASTE = "https://pastebin.example/abc"           # an https URL on a domain the provider does not own
NEURONS = {"input_per_million": 4119, "output_per_million": 34868}
DERIVED = {"output_tokens_per_day": 286795, "confidence": "DERIVED",
           "how": "10,000 Neurons/day / 34,868 Neurons per 1M output tokens, on the 8b model"}

# The daily ceilings, read from bench/rank.py through the gate so a plant is measured against the real target.
TARGET = G.daily_ceilings()["target"]
REPLY = G.daily_ceilings()["tokens_per_reply"]
LINE = G.DAILY_NEEDS_MEASUREMENT_ABOVE

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
    ("the reviewer's plant: a one-time grant of 10**15 tokens, shown on the page even though never summed",
     dict(BASE, one_time={"tokens": 10 ** 15, "confidence": "DECLARED", "source": PRICING, "read_on": DATE,
                          "quote": "a quadrillion tokens"}), "sanity ceiling"),
    ("a monthly pot of a million dollars",
     dict(BASE, monthly={"credits_usd": 10 ** 6, "confidence": "DECLARED", "source": PRICING, "read_on": DATE,
                         "quote": "$1,000,000 /mo"}), "sanity ceiling"),
    ("a grant sourced on a paste site: the provider's page or nothing",
     dict(BASE, one_time={"tokens": 5000000, "confidence": "DECLARED", "source": PASTE, "read_on": DATE,
                          "quote": "5M free tokens"}), "not this provider's domain"),
    ("the reviewer's plant: a one-time grant of 9,990,000,000 tokens, under the old ceiling of ten billion",
     dict(BASE, one_time={"tokens": 9990000000, "confidence": "DECLARED", "source": PRICING, "read_on": DATE,
                          "quote": "9.99 billion free tokens"}), "whole target"),
    ("a one-time grant one token over the target",
     dict(BASE, one_time={"tokens": TARGET + 1, "confidence": "DECLARED", "source": PRICING, "read_on": DATE,
                          "quote": "a billion and one"}), "whole target"),
    ("a one-time grant just over the measurement line, DECLARED with the provider's sentence",
     dict(BASE, one_time={"tokens": LINE + 1, "confidence": "DECLARED", "source": PRICING, "read_on": DATE,
                          "quote": "a hundred million free tokens and one"}), "admitted only as MEASURED"),
    ("a one-time grant just over the measurement line, MEASURED with no method",
     dict(BASE, one_time={"tokens": LINE + 1, "confidence": "MEASURED", "source": PRICING, "read_on": DATE}),
     "admitted only as MEASURED"),
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
    ("a one-time grant of exactly the target, MEASURED with the method: at the ceiling, not over it",
     dict(BASE, one_time={"tokens": TARGET, "confidence": "MEASURED", "source": PRICING, "read_on": DATE,
                          "measured_how": "GET /v1/usage reports the grant to the token"})),
    ("a one-time grant of exactly the measurement line, DECLARED",
     dict(BASE, one_time={"tokens": LINE, "confidence": "DECLARED", "source": PRICING, "read_on": DATE,
                          "quote": "a hundred million free tokens"})),
    ("a one-time grant just over the measurement line, MEASURED with the method",
     dict(BASE, one_time={"tokens": LINE + 1, "confidence": "MEASURED", "source": PRICING, "read_on": DATE,
                          "measured_how": "GET /v1/usage reports the grant to the token"})),
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

    # --- the daily shelf against the target. The old ceilings were ten times the target; under them one
    # typed figure put 990% of it on the front page with every check green.
    ("the reviewer's plant, verbatim: 9,900,000,000 tokens a day, MEASURED with a date and a method",
     dict(MEAS, all_models={"tpd": 9900000000}), "target"),
    ("one token a day over the target, MEASURED with the method",
     dict(MEAS, all_models={"tpd": TARGET + 1}), "target"),
    ("a request cap that derives one reply over the target: rpd x tokens a reply",
     dict(MEAS, all_models={"rpd": TARGET // REPLY + 1}), "target"),
    ("one token over the measurement line, DECLARED with source and date",
     dict(DECL, all_models={"tpd": LINE + 1}), "admitted only as MEASURED"),
    ("one token over the measurement line, MEASURED, with measured_how blank",
     {"confidence": "MEASURED", "measured_on": DATE, "measured_how": "   ", "all_models": {"tpd": LINE + 1}},
     "admitted only as MEASURED"),
    ("a request cap DECLARED that derives one reply over the measurement line",
     dict(DECL, all_models={"rpd": LINE // REPLY + 1}), "admitted only as MEASURED"),
    ("the reviewer's variant: rpd 10,000,000 DECLARED, which derives 5,000,000,000 a day",
     dict(DECL, all_models={"rpd": 10 ** 7}), "target"),
    ("a per-model daily figure over the measurement line, DECLARED with its own source",
     dict(DECL, all_models={"rpd": None}, models={"m": {"tpd": LINE + 1, "tpd_confidence": "DECLARED"}}),
     "admitted only as MEASURED"),
    ("a per-model daily figure over the target, MEASURED, inheriting the provider's method",
     dict(MEAS, all_models={"rpd": None}, models={"m": {"tpd": TARGET + 1, "tpd_confidence": "MEASURED"}}), "target"),
    ("a per-model figure with no confidence of its own under a DECLARED provider, over the line",
     dict(DECL, all_models={"rpd": None}, models={"m": {"tpd": LINE + 1}}), "admitted only as MEASURED"),
    ("a free_models_combined tier whose request cap derives over the line: rank.py reads the smallest tier",
     dict(DECL, all_models={"rpd": None}, free_models_combined={"new": {"rpd": LINE // REPLY + 1}}),
     "admitted only as MEASURED"),
    ("derived.output_tokens_per_day one over the target",
     dict(DECL, all_models={"rpm": 300}, derived=dict(DERIVED, output_tokens_per_day=TARGET + 1)), "target"),
    ("derived.output_tokens_per_day one over the measurement line: a derivation is never measured",
     dict(DECL, all_models={"rpm": 300}, derived=dict(DERIVED, output_tokens_per_day=LINE + 1)), "admitted only as MEASURED"),
    ("a Neuron allowance and a unit price each under their own ceiling that divide into a figure over the "
     "target: 999,999,999 Neurons a day at one Neuron per million tokens",
     dict(DECL, free_allocation={"neurons_per_day": 999999999}, neuron_cost_examples={"@cf/m": dict(NEURONS, output_per_million=1)}),
     "target"),
    ("a Neuron division over the measurement line: 10,000 a day at 50 per million is 200,000,000 DECLARED",
     dict(DECL, free_allocation={"neurons_per_day": 10000}, neuron_cost_examples={"@cf/m": dict(NEURONS, output_per_million=50)}),
     "admitted only as MEASURED"),
    ("measured_values.limit_per_day one over the target under a MEASURED provider",
     dict(MEAS, all_models={"rpm": 5}, measured_values={"limit_per_day": TARGET + 1}), "under"),
    ("measured_values.limit_per_day over the measurement line under a DECLARED provider",
     dict(DECL, all_models={"rpm": 5}, measured_values={"limit_per_day": LINE + 1}), "admitted only as MEASURED"),
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

    # --- evidence on a domain the provider does not own, and figures rank.py reads that were never typed
    ("the reviewer's plant: DECLARED, sourced on a paste site, 9,999,999,999 tokens a day under the ceiling",
     dict(DECL, source=PASTE, all_models={"tpd": 9999999999}), "not this provider's domain"),
    ("a model-level source on a foreign domain",
     dict(BASE, models={"m": {"rpd": 100, "rpd_confidence": "DECLARED", "source": PASTE, "read_on": DATE}}),
     "not this provider's domain"),
    ("a lookalike of the provider's own domain as a source",
     dict(DECL, source="https://console.groq.com.evil.example/docs", all_models={"rpm": 30}), "not this provider's domain"),
    ("the reviewer's plant: derived.output_tokens_per_day of 10**12, straight onto the DERIVED shelf",
     dict(DECL, all_models={"rpm": 300}, derived=dict(DERIVED, output_tokens_per_day=10 ** 12)), "target"),
    ("a derived figure that is a string", dict(DECL, derived=dict(DERIVED, output_tokens_per_day="many")), "non-negative integer"),
    ("a derived figure not labelled DERIVED: the code ignores it and the reader sees it",
     dict(DECL, derived=dict(DERIVED, confidence="DECLARED")), "labelled DERIVED"),
    ("a derived figure with the arithmetic not written out", dict(DECL, derived={"output_tokens_per_day": 286795, "confidence": "DERIVED"}),
     "needs `how`"),
    ("the reviewer's plant: a Neuron cost of 0.000001, which divides the daily allocation into 10**16 tokens",
     dict(DECL, all_models={"rpm": 300, "neurons_per_day": 10000}, free_allocation={"neurons_per_day": 10000},
          neuron_cost_examples={"@cf/m": dict(NEURONS, output_per_million=0.000001)}), "positive integer"),
    ("a Neuron cost of zero: a division by zero on the way to the headline",
     dict(DECL, free_allocation={"neurons_per_day": 10000}, neuron_cost_examples={"@cf/m": dict(NEURONS, output_per_million=0)}),
     "positive integer"),
    ("a Neuron cost entry missing its output price, which rank.py indexes into",
     dict(DECL, free_allocation={"neurons_per_day": 10000}, neuron_cost_examples={"@cf/m": {"input_per_million": 4119}}),
     "positive integer"),
    ("a Neuron cost keyed by a model id that closes a backtick on LIMITS.md",
     dict(DECL, free_allocation={"neurons_per_day": 10000}, neuron_cost_examples={"x` | [k](https://evil.example) | `": NEURONS}),
     "unexpected shape"),
    ("a per-model table keyed by a model id with a pipe in it",
     dict(DECL, all_models={"rpm": 30}, models={"a | b": {"rpm": 30}}), "unexpected shape"),
    ("free_allocation with a figure that is a word", dict(DECL, free_allocation={"neurons_per_day": "lots"}), "non-negative integer"),
    ("free_allocation with a figure past the Neurons ceiling", dict(DECL, free_allocation={"neurons_per_day": 10 ** 12}), "sanity ceiling"),
    ("measured_values with a daily figure of 10**12", dict(MEAS, measured_values={"limit_per_day": 10 ** 12}), "under"),
    ("unverified_accounts with a negative figure", dict(DECL, unverified_accounts={"rpd": -1, "confidence": "DECLARED"}),
     "non-negative integer"),
    ("authenticated_tier with a billion requests a minute", dict(DECL, authenticated_tier={"rpm": 10 ** 9, "kind": "PAID-PLAN", "why": "x"}),
     "sanity ceiling"),

    # --- free text that reaches a page. rank.py renders these raw onto LIMITS.md, RESULTS.md and ranking.json.
    ("the reviewer's plant: a caveat carrying a markdown link to a key-stealing mirror",
     dict(DECL, all_models={"rpm": 30}, caveat="See [our mirror](https://evil.example/keys) for keys."), "rendered raw"),
    ("a bare URL in a quote, rendered as a blockquote",
     dict(DECL, all_models={"rpm": 30}, quotes=["Terms at https://evil.example/terms"]), "contains a URL"),
    ("a www. address with no scheme in a caveat", dict(DECL, all_models={"rpm": 30}, caveat="Keys at www.evil.example."), "contains a URL"),
    ("a backtick in a caveat: a code span on the page, and the mark that closes another one",
     dict(DECL, all_models={"rpm": 30}, caveat="See `models` below."), "backtick"),
    ("an HTML tag in signup_requires.note",
     dict(DECL, all_models={"rpm": 30}, signup_requires={"card": "no", "phone": "no", "note": "<a href=x>Sign up</a>", "read_on": DATE}),
     "rendered raw"),
    ("a second line in all_models.note", dict(DECL, all_models={"rpm": 30, "note": "per model\nand a second line"}),
     "spans more than one line"),
    ("a URL in measured_how", dict(MEAS, all_models={"rpm": 5}, measured_how="GET https://evil.example/usage"), "contains a URL"),
    ("square brackets in binding_limit", dict(DECL, all_models={"rpm": 30}, binding_limit="[see console]"), "rendered raw"),
    ("a URL in a grant's expires text",
     dict(BASE, one_time={"tokens": 5000000, "confidence": "DECLARED", "source": PRICING, "read_on": DATE,
                          "quote": "5M free tokens", "expires": "see https://evil.example"}), "contains a URL"),
    ("a URL in rate_limit_quotes", dict(DECL, all_models={"rpm": 30}, rate_limit_quotes=["qwen | 600 | https://evil.example"]),
     "contains a URL"),
    ("a URL in a per-model note", dict(DECL, all_models={"rpm": 30}, models={"m": {"rpm": 30, "note": "docs: https://evil.example"}}),
     "contains a URL"),
    ("a URL in tpm_note", dict(DECL, all_models={"rpm": 30, "tpm": 8000}, tpm_note="see https://evil.example"), "contains a URL"),
    ("a URL in a tier's unlock text", dict(DECL, all_models={"rpm": 30}, tiers={"payer": {"rpd": 1000, "unlock": "top up at https://evil.example"}}),
     "contains a URL"),
    ("a URL in a measured_concurrency note",
     dict(MEAS, all_models={"rpm": 5}, measured_concurrency={"measured_on": DATE, "m": "8 calls, see https://evil.example"}), "contains a URL"),
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
    ("a derived sub-block, labelled DERIVED, with the arithmetic written out",
     dict(DECL, all_models={"rpm": 300, "neurons_per_day": 10000}, derived=DERIVED)),
    ("the Cloudflare shape: an allocation in Neurons, unit prices per model, and the derived figure",
     dict(DECL, all_models={"rpm": 300, "neurons_per_day": 10000}, free_allocation={"neurons_per_day": 10000},
          neuron_cost_examples={"@cf/meta/llama-3.2-1b-instruct": NEURONS, "@cf/meta/llama-3.3-70b-instruct-fp8-fast": {"input_per_million": 26668, "output_per_million": 204805}},
          derived=DERIVED)),
    ("measured_values, unverified_accounts and authenticated_tier in their real shapes",
     dict(MEAS, all_models={"rpm": 5, "tpd": 5000000}, measured_values={"limit_per_day": 5000000},
          unverified_accounts={"rpd": 100, "rph": 30, "applies_to": "two specific models on unverified accounts", "confidence": "DECLARED"},
          authenticated_tier={"rpm": 400, "kind": "PAID-PLAN", "why": "requires a project with a payment method"})),
    ("a source on the declared sign-up domain of a provider whose API lives elsewhere: the real Alibaba shape",
     (dict(DECL, source="https://www.alibabacloud.com/help/en/model-studio/rate-limit", all_models={"rpm": 600}), None,
      ("alibaba", "dashscope-intl.aliyuncs.com"))),
    ("a source on the declared terms domain: Google's rate-limit page lives on ai.google.dev",
     (dict(DECL, source="https://ai.google.dev/gemini-api/docs/rate-limits", all_models={"rpm": 15}), None,
      ("google", "generativelanguage.googleapis.com"))),
    ("free text with punctuation a page can carry: quotes, colons, a slash, an ampersand, a dollar sign",
     dict(DECL, all_models={"rpm": 30}, caveat="Their words: 'Free Trial: $5 in credits' - read on the pricing page; per key/project & org.",
          quotes=["Includes input and output tokens.", "qwen-flash | International | 600 | 5,000,000"])),
    ("a quota for a provider that is in providers.json", (dict(DECL, all_models={"rpm": 30}), {"someprovider", "groq"})),

    # --- just under the daily rules: the ceiling is a ceiling, not a wall one step short of it
    ("exactly the target, MEASURED with the method", dict(MEAS, all_models={"tpd": TARGET})),
    ("a request cap that derives exactly the target, MEASURED", dict(MEAS, all_models={"rpd": TARGET // REPLY})),
    ("exactly the measurement line, DECLARED with source and date", dict(DECL, all_models={"tpd": LINE})),
    ("one over the measurement line, MEASURED with the method", dict(MEAS, all_models={"tpd": LINE + 1})),
    ("a request cap DECLARED that derives exactly the measurement line", dict(DECL, all_models={"rpd": LINE // REPLY})),
    ("a per-model figure over the line, MEASURED, inheriting the provider's date and method",
     dict(MEAS, all_models={"rpd": None}, models={"m": {"tpd": LINE + 1, "tpd_confidence": "MEASURED"}})),
    ("a per-model figure over the line with its own date and method under a DECLARED provider",
     dict(DECL, all_models={"rpd": None},
          models={"m": {"tpd": LINE + 1, "tpd_confidence": "MEASURED", "measured_on": DATE, "measured_how": "x-ratelimit headers"}})),
    ("derived.output_tokens_per_day of exactly the measurement line",
     dict(DECL, all_models={"rpm": 300}, derived=dict(DERIVED, output_tokens_per_day=LINE))),
    ("the real xkiro shape: 5,000,000 a day MEASURED on their usage endpoint, echoed in measured_values",
     dict(MEAS, all_models={"rpd": None, "tpd": 5000000}, measured_values={"limit_per_day": 5000000})),
    ("measured_values.limit_per_day over the line under a MEASURED provider with the method",
     dict(MEAS, all_models={"rpm": 5}, measured_values={"limit_per_day": LINE + 1})),
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
    ("the reviewer's plant: a shortener on a top-level domain the old list did not name",
     pack(probes__A__prompt="Compara cu bit.ly/free-keys si raspunde cu 14400, 81600."), "bare domain"),
    ("a domain on .site", pack(probes__A__prompt="Vezi evil.site si raspunde cu 14400, 81600."), "bare domain"),
    ("a domain on .link, in capitals", pack(probes__A__prompt="Vezi EVIL.LINK si raspunde cu 14400, 81600."), "bare domain"),
    ("the reviewer's plant: a provider named by its providers.json name, not by its host stem",
     pack(probes__D__prompt="Scrie un paragraf despre banci, in stilul Alibaba, fara cifre inventate."), "names a vendor"),
    ("a provider named by the stem of its declared sign-up host",
     pack(probes__D__prompt="Scrie un paragraf despre banci, ca pe alibabacloud, fara cifre inventate."), "names a vendor"),
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
    ("a character in both diacritics and wrong_diacritics", pack(wrong_diacritics="\u0219"), "both diacritics and wrong_diacritics"),
    ("an English pack asking for diacritics it has no alphabet for",
     (dict(json.loads(json.dumps(EN)), probes=dict(EN["probes"], D=dict(EN["probes"]["D"], min_diacritics=3))), "en"),
     "min_diacritics must be 0"),
]
LANGUAGE_MUST_PASS = [
    ("the real Romanian pack", RO),
    ("the real English pack", (EN, "en")),
    ("a pack with penalties in range", pack(generation={"temperature": 0, "presence_penalty": -1.5, "frequency_penalty": 2})),
    ("abbreviations, decimals and a sentence run into the next: dots that are not domains",
     pack(probes__A__prompt="Un abonament costa 96.000 de euro pe an, i.e. 3.14 la suta, s.a.m.d. Raspunde cu 14400, 81600.")),
]


# ---------------------------------------------------------------- data/uptime.jsonl

REAL_UPTIME = [r for _, r in G.read_jsonl(HERE.parent / "data" / "uptime.jsonl", "uptime", [])] \
    if (HERE.parent / "data" / "uptime.jsonl").exists() else []


def up(**kw):
    r = {"date": DATE, "provider": P0, "model": M0, "state": "alive", "http": 200, "seconds": 0.5, "note": ""}
    r.update(kw)
    return r


def days(rows, start="2026-08-20"):
    """The same rows, one per day, in date order from `start`: what the radar writes over a run of days."""
    d0 = date.fromisoformat(start)
    return [dict(r, date=(d0 + timedelta(days=i)).isoformat()) for i, r in enumerate(rows)]


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
     [up(date="2026-08-%02d" % d, state="down", http=429) for d in range(10, 24)], "state is down with http 429"),
    ("the reviewer's plant: a row dated after today", [up(date=FUTURE)], "after today"),
    ("the reviewer's plant: fourteen down days with http 500, all dated next year, which bury a live endpoint "
     "because the burial clock counts from the latest date in the file",
     [up(date="2027-01-%02d" % d, state="down", http=500) for d in range(1, 15)], "after today"),
    ("down with http 404: the endpoint answered, so it is not down",
     [up(state="down", http=404)], "state is down with http 404"),
    ("down with http 400", [up(state="down", http=400)], "state is down with http 400"),
    ("down with http 301", [up(state="down", http=301)], "state is down with http 301"),
    ("down with http 503, which the radar files as overloaded",
     [up(state="down", http=503)], "state is down with http 503"),

    # --- back-dating and doubling: the radar appends the whole day at once, in date order
    ("the reviewer's plant: the endpoint's two real days on file, then fourteen down days with http 500 dated "
     "before them - the burial this file used to assert MUST PASS",
     [up(date="2026-09-06"), up(date="2026-09-07")]
     + [up(date="2026-08-%02d" % d, state="down", http=500) for d in range(24, 32)]
     + [up(date="2026-09-%02d" % d, state="down", http=500) for d in range(1, 7)], "back-dated"),
    ("the same plant after the endpoint's real rows were deleted: another endpoint's row dated 2026-09-07 is on "
     "file, so fourteen down days dated 2026-08-24 to 2026-09-06 are filed for days the radar already passed",
     [up(provider=P1, model=M1, date="2026-09-07")]
     + [up(date="2026-08-%02d" % d, state="down", http=500) for d in range(24, 32)]
     + [up(date="2026-09-%02d" % d, state="down", http=500) for d in range(1, 7)], "back-dated"),
    ("one row dated a day earlier than the row before it", [up(date="2026-09-07"), up(date="2026-09-06")], "back-dated"),
    ("two readings of one endpoint on one day: alive, then down",
     [up(), up(state="down", http=500)], "second row"),
    ("fourteen down rows all dated the same day: one day, not fourteen",
     [up(date="2026-09-01", state="down", http=500)] * 14, "second row"),
]
UPTIME_MUST_PASS = [
    ("every state with the code the radar writes it with, one a day",
     days([up(), up(state="empty"), up(state="rate_limited", http=429), up(state="overloaded", http=503),
           up(state="payment_required", http=402), up(state="blocked", http=403),
           up(state="no_key", http=None, seconds=None, note="no key set in this environment"),
           up(state="down", http=0, note="URLError"), up(state="down", http=None, note="no response"),
           up(state="down", http=500), up(state="down", http=502), up(state="down", http=504)])),
    ("a legitimate history: rows in date order, one a day, with fourteen down days among them",
     days([up()] * 3 + [up(state="down", http=500)] * 14 + [up()] * 2, start="2026-08-10")),
    ("the whole day for every endpoint appended at once, then the next day",
     [up(date="2026-09-06"), up(provider=P1, model=M1, date="2026-09-06"),
      up(date="2026-09-07", state="down", http=502), up(provider=P1, model=M1, date="2026-09-07")]),
    ("a no_key row beside a probed row for one endpoint-day: not a verdict, so not a second reading, the rule "
     "gate_viability.py applies",
     [up(), up(state="no_key", http=None, seconds=None, note="no key set in this environment")]),
    ("a row dated today", [up(date=str(TODAY))]),
    ("the real file's rows", REAL_UPTIME),
    ("an empty file", []),
]


# ---------------------------------------------------------------- data/throughput.jsonl

REAL_THROUGHPUT = [r for _, r in G.read_jsonl(HERE.parent / "data" / "throughput.jsonl", "throughput", [])] \
    if (HERE.parent / "data" / "throughput.jsonl").exists() else []

def tp(**kw):
    r = {"provider": P0, "model": M0, "concurrency": 8, "seconds": 30.8, "requests_ok": 22,
         "requests_rate_limited": 0, "requests_failed": 0, "output_tokens": 8141, "tokens_estimated": False,
         "tokens_per_minute_measured": int(8141 / 30.8 * 60), "first_error": None,
         "rate_basis": "delivered over 31 seconds without a refusal, scaled to a minute",
         "stopped_because": "window ended", "note": "A floor, not a ceiling.", "date": DATE}
    r.update(kw)
    return r


def _without(row, *keys):
    return {k: v for k, v in row.items() if k not in keys}


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
     [tp(provider=P1, model=M1, requests_ok=CAP1 * 2 // T.MAX_TOKENS_PER_CALL + 1, output_tokens=CAP1 * 2, seconds=60.0,
         tokens_per_minute_measured=CAP1 * 2)], "above the"),
    ("the reviewer's plant: a billion tokens from ONE request on a provider that publishes no per-minute ceiling, "
     "self-consistent with its own seconds - six billion a minute into the burst headline",
     [tp(requests_ok=1, output_tokens=10 ** 9, seconds=10.0, tokens_per_minute_measured=6 * 10 ** 9)],
     "cannot have carried more than"),
    ("one token over what the requests could carry at the meter's max_tokens plus the 10% a usage block may count past it",
     [tp(requests_ok=10, output_tokens=7701, tokens_per_minute_measured=int(7701 / 30.8 * 60))], "cannot have carried more than"),
    ("output tokens from zero successful requests", [tp(requests_ok=0, output_tokens=100, tokens_per_minute_measured=195)],
     "from zero successful requests"),
    ("a row dated after today", [tp(date=FUTURE)], "after today"),
    ("a row written from the flag date on that does not say whether its count is theirs or an estimate",
     [_without(tp(date=str(TODAY)), "tokens_estimated")], "row lacks tokens_estimated"),
    ("tokens_estimated as a string", [tp(tokens_estimated="no")], "true or false"),
    ("concurrency above the meter's own maximum", [tp(concurrency=9)], "above the 8"),
    ("a provider nobody benchmarks", [tp(provider="ghost")], "not in providers.json"),
    ("a model the provider does not list", [tp(model="ghost-model")], "is not one of"),
    ("a negative request count", [tp(requests_failed=-1)], "must be a non-negative integer"),
    ("concurrency as a boolean", [tp(concurrency=True)], "must be a non-negative integer"),
    ("a row missing the fields the runner writes", [{"provider": P0, "model": M0, "date": DATE}], "row lacks"),
    ("a skipped row carrying a rate", [{"provider": P0, "skipped": "no key", "date": DATE, "tokens_per_minute_measured": 10 ** 6}],
     "skipped row carries"),
    ("a date that is not ISO", [tp(date="Sept 7")], "date must be"),
    ("a note with a second line in it", [tp(note="A floor.\n[link](https://evil.example)")], "one line of text"),
    ("the reviewer's plant: 20,000 answers in 30.8 seconds on 8 slots, fourteen million tokens, self-consistent "
     "with its own seconds and under the per-call bound because that bound grows with the count",
     [tp(requests_ok=20000, output_tokens=14000000, tokens_per_minute_measured=int(14000000 / 30.8 * 60))],
     "more requests than the meter could have sent"),
    ("one request over what the slots could complete: 8 x (30.8 x 10 + 1) + 1",
     [tp(requests_ok=2473, output_tokens=100000, tokens_per_minute_measured=int(100000 / 30.8 * 60))],
     "more requests than the meter could have sent"),
    ("refusals count too: 2,473 rate-limited answers in the window",
     [tp(requests_ok=0, requests_rate_limited=2473, output_tokens=0, tokens_per_minute_measured=0)],
     "more requests than the meter could have sent"),
    ("a row dated before the row already on file for the same endpoint: rank.py keeps the LAST row in file order",
     [tp(date="2026-09-07"), tp(date="2026-09-06")], "back-dated"),
    ("a row dated before another endpoint's row on file: the meter ran that day and did not write this",
     [tp(provider=P1, model=M1, date="2026-09-07"), tp(date="2026-09-06")], "back-dated"),
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
     [tp(provider=P1, model=M1, requests_ok=CAP1 // 4 // T.MAX_TOKENS_PER_CALL + 1, output_tokens=CAP1 // 4, seconds=60.0,
         tokens_per_minute_measured=CAP1 // 4)]),
    ("an older row without first_error", [_without(tp(), "first_error")]),
    ("an older row without tokens_estimated, read as their count", [_without(tp(), "tokens_estimated")]),
    ("a row whose count came from words x 1.3, and says so", [tp(tokens_estimated=True)]),
    ("exactly what the requests could carry at the meter's max_tokens",
     [tp(requests_ok=10, output_tokens=7000, tokens_per_minute_measured=int(7000 / 30.8 * 60))]),
    ("a usage block that counted 48 tokens past max_tokens over ten answers, the shape aihubmix's gateway "
     "reported on 2026-09-07: inside the tolerance the meter states",
     [tp(requests_ok=10, requests_rate_limited=1, output_tokens=7048, seconds=18.0, tokens_per_minute_measured=7048,
         rate_basis="their per-minute limit stopped us", stopped_because="rate limit reached")]),
    ("exactly what the slots could complete: 8 x (30.8 x 10 + 1) = 2,472 answers",
     [tp(requests_ok=2472, output_tokens=100000, tokens_per_minute_measured=int(100000 / 30.8 * 60))]),
    ("the fastest real row: 461 refusals in 30.8 seconds on 8 slots",
     [tp(requests_ok=0, requests_failed=461, output_tokens=0, tokens_per_minute_measured=0,
         first_error="HTTP 403 the request was refused (403)")]),
    ("the first wave on a window that closed at once: 8 refusals in half a second on 8 slots",
     [tp(requests_ok=0, requests_rate_limited=8, output_tokens=0, seconds=0.5, tokens_per_minute_measured=0,
         rate_basis="their per-minute limit stopped us", stopped_because="rate limit reached")]),
    ("two readings of one endpoint on one day, in file order: what bench/throughput.py --only writes when it is "
     "run twice, and rank.py counts both as readings",
     [tp(), tp(requests_ok=1, output_tokens=700, tokens_per_minute_measured=int(700 / 30.8 * 60))]),
    ("readings across days, in date order", [tp(date="2026-09-06"), tp(date="2026-09-07"), tp(provider=P1, model=M1, date="2026-09-07")]),
    ("the real file's rows", REAL_THROUGHPUT),
]


# ---------------------------------------------------------------- data/drawn.jsonl

REAL_DRAWN = [r for _, r in G.read_jsonl(HERE.parent / "data" / "drawn.jsonl", "drawn", [])] \
    if (HERE.parent / "data" / "drawn.jsonl").exists() else []
CAP_STOP = D.CAP_STOP_PREFIX + "250,000 output tokens"
# The provider with no published per-minute ceiling (P0) publishes 5 requests a minute, so the honest
# hour below runs at 5 a minute. Alibaba publishes 600, which the meter caps at 120: the fast draws
# that reach the token cap in minutes are planted there.
ALIBABA, ALIBABA_MODEL = "alibaba", next(p for p in REAL_PROVIDERS if p["name"] == "alibaba")["models"][0]["id"]
PACE0 = D.pace_for((REAL_LIMITS.get("providers") or {}).get(P0))[0]


def dr(**kw):
    """An honest hour at the published pace: 290 answers of under 700 tokens, five failures, rate stated."""
    minutes = 60.02
    r = {"provider": P0, "model": M0, "date": DATE, "started_utc": DATE + "T14:06:37Z",
         "minutes_planned": 60.0, "minutes_run": minutes, "pace_rpm": PACE0, "pace_basis": "published rpm %d" % PACE0,
         "requests_ok": 290, "requests_429": 0, "requests_failed": 5, "first_error": "RemoteDisconnected",
         "output_tokens_drawn": 200000, "tokens_estimated": False,
         "tokens_per_hour_drawn": int(200000 / minutes * 60), "tokens_per_hour_basis": "scaled from 60.0 minutes of drawing",
         "stopped_because": "window ended: 60 minutes planned",
         "note": "Drawn at %d requests a minute, at most 2 in flight, one model, one key. A floor at our pace, not their ceiling." % PACE0}
    r.update(kw)
    return r


def fast(**kw):
    """A draw on the 120-a-minute provider that hit the 250,000 cap after eight minutes and 400 answers."""
    r = dr(provider=ALIBABA, model=ALIBABA_MODEL, pace_rpm=120, pace_basis="published rpm 600, capped at 120",
           minutes_run=8.0, requests_ok=400, requests_failed=0, first_error=None, output_tokens_drawn=250300,
           tokens_per_hour_drawn=int(250300 / 8.0 * 60), stopped_because=CAP_STOP,
           tokens_per_hour_basis="scaled from 8.0 minutes of drawing: the token cap ended the run after 400 successful requests")
    r.update(kw)
    return r


DRAWN_MUST_REFUSE = [
    ("the reviewer's plant, verbatim: a row with tokens_per_hour_drawn 1e9 and nothing else, which put "
     "24,012,218,019 tokens a day on the headline with every check green",
     [{"provider": "groq", "model": "qwen/qwen3.8-27b", "tokens_per_hour_drawn": 10 ** 9}], "row lacks"),
    ("the same plant dressed as a full row: a billion an hour from 200,000 tokens in an hour",
     [dr(tokens_per_hour_drawn=10 ** 9)], "scale to"),
    ("a rate that does not follow from its own tokens and minutes", [dr(tokens_per_hour_drawn=150000)], "scale to"),
    ("a rate above sixty times the per-minute ceiling the provider publishes: the groq row that is otherwise "
     "self-consistent (1,800 answers at 30 a minute, a million tokens in the hour, tpm 8,000)",
     [dr(provider="groq", model="qwen/qwen3.8-27b", pace_rpm=30, pace_basis="published rpm 30", requests_ok=1800,
         requests_failed=0, first_error=None, output_tokens_drawn=1000000, tokens_per_hour_drawn=int(1000000 / 60.02 * 60))],
     "above sixty times"),
    ("a row dated after today", [dr(date=FUTURE)], "after today"),
    ("a row started after today", [dr(started_utc=FUTURE + "T00:00:00Z")], "not after today"),
    ("a provider nobody draws from", [dr(provider="ghost")], "not in providers.json"),
    ("a model the provider does not list", [dr(model="ghost-model")], "is not one of"),
    ("a pace above what the meter allows for this provider: its published 5 a minute",
     [dr(pace_rpm=30, requests_ok=1700, requests_failed=0, output_tokens_drawn=1000000, tokens_per_hour_drawn=int(1000000 / 60.02 * 60))],
     "above the %d bench/draw_day.py allows" % PACE0),
    ("a pace above the safety ceiling, on the provider that publishes 600 a minute",
     [fast(pace_rpm=600, requests_ok=4000, output_tokens_drawn=250300)], "above the 120 bench/draw_day.py allows"),
    ("more requests than the metronome could have launched: 405 in an hour at 5 a minute",
     [dr(requests_ok=400)], "metronome launches at most"),
    ("more tokens than the answers could have carried at the meter's max_tokens",
     [dr(output_tokens_drawn=223301, tokens_per_hour_drawn=int(223301 / 60.02 * 60))], "cannot have carried more than"),
    ("more tokens than the largest cap plus the calls in flight: 1.5M in an hour on the fast provider",
     [fast(minutes_run=60.0, requests_ok=7000, output_tokens_drawn=1500000, tokens_per_hour_drawn=1500000,
           stopped_because="window ended: 60 minutes planned", tokens_per_hour_basis="scaled from 60.0 minutes of drawing")],
     "above the most one run can hold"),
    ("minutes_run of zero", [dr(minutes_run=0)], "positive number"),
    ("minutes_run negative", [dr(minutes_run=-5)], "positive number"),
    ("a rate stated from a fifteen-minute window that the clock ended: under the twenty-minute floor",
     [dr(minutes_run=15.0, requests_ok=70, requests_failed=0, output_tokens_drawn=40000, tokens_per_hour_drawn=160000,
         stopped_because="window ended: 15 minutes planned", minutes_planned=15.0)], "states one only after"),
    ("a rate stated from a cap stop with 30 answers: too few samples, whatever the clock says (cap lowered with --cap)",
     [fast(requests_ok=30, output_tokens_drawn=20300, tokens_per_hour_drawn=int(20300 / 8.0 * 60),
           stopped_because=D.CAP_STOP_PREFIX + "20,000 output tokens")], "states one only after"),
    ("a rate stated from a cap stop after four minutes: under the five-minute floor for a cap stop",
     [fast(minutes_run=4.0, tokens_per_hour_drawn=int(250300 / 4.0 * 60))], "states one only after"),
    ("a cap stop whose tokens never reached the cap it names: a rate rule being claimed, not a stop",
     [dr(stopped_because=CAP_STOP)], "did not reach the cap"),
    ("a cap stop naming a cap the meter cannot run with",
     [fast(stopped_because=D.CAP_STOP_PREFIX + "5,000,000 output tokens", requests_ok=7000, minutes_run=60.0,
           output_tokens_drawn=1000000, tokens_per_hour_drawn=1000000)], "cannot have run with"),
    ("a cap stop with more tokens than the calls in flight could add past the cap",
     [fast(output_tokens_drawn=260000, tokens_per_hour_drawn=int(260000 / 8.0 * 60))], "closes within the"),
    ("tokens_estimated missing", [_without(dr(), "tokens_estimated")], "row lacks tokens_estimated"),
    ("tokens_estimated as a string", [dr(tokens_estimated="no")], "true or false"),
    ("a negative request count", [dr(requests_failed=-1)], "non-negative integer"),
    ("a note with a second line in it", [dr(note="A floor.\n[link](https://evil.example)")], "one line of text"),
    ("a line that is not JSON", [dr(), "{not json"], "not valid JSON"),
    ("a draw dated before the draw already on file for the same endpoint: rank.py keeps the LAST row in file order",
     [dr(date="2026-09-07", started_utc="2026-09-07T14:06:37Z"), dr(date="2026-09-06", started_utc="2026-09-06T14:06:37Z")], "back-dated"),
    ("a second draw of one endpoint on one day, which would silently replace the first on the page",
     [dr(), dr(output_tokens_drawn=150000, tokens_per_hour_drawn=int(150000 / 60.02 * 60))], "second row"),
]
DRAWN_MUST_PASS = [
    ("an honest hour at the published pace, rate stated", [dr()]),
    ("two endpoints drawn on one day, then one of them the next day",
     [dr(), fast(), dr(date="2026-09-08", started_utc="2026-09-08T14:06:37Z")]),
    ("the token cap reached after eight minutes and 400 answers: a measured high rate, stated", [fast()]),
    ("a short run under a 429 wall, no rate, null where the rate would be",
     [dr(minutes_run=5.03, requests_ok=0, requests_429=11, requests_failed=0, first_error="HTTP 429 rate limit",
         output_tokens_drawn=0, tokens_per_hour_drawn=None,
         tokens_per_hour_basis="no hourly figure: 5.0 minutes is under the 20-minute floor",
         stopped_because="rate limited: HTTP 429 on every call for 5 minutes, their limit is holding")]),
    ("the cap reached in three and a half minutes by 360 answers: under the five-minute floor, so no rate, and a "
     "row the meter could have written (the fake in test_draw.py that closes it in three calls could not be, "
     "because 100,000 tokens a call is more than the meter asks for)",
     [fast(minutes_run=3.5, requests_ok=360, output_tokens_drawn=250300, tokens_per_hour_drawn=None,
           tokens_per_hour_basis="no hourly figure: the token cap ended the run at 3.5 minutes and 360 successful requests")]),
    ("a count that came from words x 1.3, and says so", [dr(tokens_estimated=True)]),
    ("the real file's rows", REAL_DRAWN),
    ("an empty file", []),
]


# ---------------------------------------------------------------- announced_deaths.json

NEWS_HOST = sorted(G.KNOWN_NEWS_HOSTS)[0]
OPERATOR_NAME, OPERATOR_HOST = next((k, sorted(v)[0]) for k, v in sorted(G.KNOWN_OPERATOR_HOSTS.items()))
DEATH = {"provider": "Some Retired Service", "died_on": "2026-07-30",
         "quote": "As of July 30, 2026, the service is retired and the inference API is no longer available.",
         "source": "https://%s/blog/some-retired-service-shuts-down" % NEWS_HOST, "notice_from": "third party",
         "read_on": DATE, "endpoint_today": "HTTP 410 on the old endpoint, measured " + DATE}
OPERATOR = dict(DEATH, provider=OPERATOR_NAME.title(), notice_from="operator",
                source="https://%s/changelog/retired" % OPERATOR_HOST)
PASTE_NOTICE = "https://pastebin.example/raw/abc123"
REAL_DEATHS = (G.load_json(HERE / "announced_deaths.json", []) or {}).get("providers") or []

DEATHS_MUST_REFUSE = [
    ("the planted headstone: a quote that leaves the blockquote and plants a link",
     [dict(DEATH, quote="Groq has shut down its free tier.\n\n[Migrate your keys here](https://evil.example)\n\n> and")],
     "one line"),
    ("a one-line quote with a link in it", [dict(DEATH, quote="Retired. [Migrate](https://evil.example)")], "rendered raw"),
    ("a quote with a tag in it", [dict(DEATH, quote="Retired <b>now</b>.")], "rendered raw"),
    ("the reviewer's plant: a bare URL in the quote", [dict(DEATH, quote="Retired; see https://evil.example/notice")], "contains a URL"),
    ("the reviewer's plant: a bare URL in endpoint_today",
     [dict(DEATH, endpoint_today="HTTP 410; new keys at https://evil.example/keys")], "contains a URL"),
    ("a source that is not a URL", [dict(DEATH, source="not even a url")], "source must be one https URL"),
    ("a retirement notice for a provider this repo still benchmarks",
     [dict(DEATH, provider=P0.capitalize())], "still a provider in providers.json"),
    # Written as an escape so this file stays ASCII: the o is U+043E, Cyrillic small o, which renders like
    # the Latin one. Under the exact-match rule this headstone was not a live provider's, so it passed.
    ("the reviewer's plant: a live provider's name with one letter from another alphabet",
     [dict(DEATH, provider="gr" + "\u043e" + "q")], "ASCII letters"),
    ("a provider name with a pipe in it", [dict(DEATH, provider="Some | Service")], "ASCII letters"),
    ("a death date that is not a date", [dict(DEATH, died_on="yesterday")], "died_on must be a date"),
    ("no read_on", [{k: v for k, v in DEATH.items() if k != "read_on"}], "read_on must be a date"),
    ("endpoint_today with a second line", [dict(DEATH, endpoint_today="HTTP 410\n[x](https://evil.example)")],
     "endpoint_today must be one line"),
    ("a provider name that becomes markdown in the heading", [dict(DEATH, provider="X [y](https://evil.example)")],
     "no markdown in it"),

    # --- whose word the death is, and where that word may sit
    ("the reviewer's plant: an operator notice on a paste site, under a live provider's name with a word added",
     [dict(DEATH, provider=P0.capitalize() + " AI", notice_from="operator", source=PASTE_NOTICE)],
     "not a domain this gate ties to"),
    ("a live provider's name with a word added, whatever the source",
     [dict(DEATH, provider=P0.capitalize() + " AI")], "with a word added"),
    ("a third-party notice on a paste site", [dict(DEATH, source=PASTE_NOTICE)], "declared news hosts"),
    ("a third-party notice on a blog nobody declared", [dict(DEATH, source="https://blog.example/changelog/retired")],
     "declared news hosts"),
    ("an operator notice for a headstone this gate ties to no domain",
     [dict(DEATH, notice_from="operator")], "not a domain this gate ties to"),
    ("an operator notice sitting on a news host: the operator's word lives on the operator's site",
     [dict(OPERATOR, source="https://%s/blog/retired" % NEWS_HOST)], "not a domain this gate ties to"),
    ("an operator notice on a lookalike of the operator's domain",
     [dict(OPERATOR, source="https://%s.evil.example/changelog/retired" % OPERATOR_HOST)], "not a domain this gate ties to"),
    ("no notice_from at all", [{k: v for k, v in DEATH.items() if k != "notice_from"}], "notice_from must be"),
    ("an invented author", [dict(DEATH, notice_from="a friend")], "notice_from must be"),
]
DEATHS_MUST_PASS = [
    ("a third-party notice on a declared news host, every field one line, dated and sourced", [DEATH]),
    ("an operator's notice on the operator's declared domain", [OPERATOR]),
    ("a name with a space, a period and parentheses: what operators call their products",
     [dict(DEATH, provider="Llama API v2.0 (Preview)")]),
    ("an endpoint_today naming a host without a scheme: a status line, not a link",
     [dict(DEATH, endpoint_today="HTTP 410 on models.example.net/inference/chat/completions, measured " + DATE)]),
    ("the real file's entries", REAL_DEATHS),
    ("no notices at all", []),
]


# ---------------------------------------------------------------- data/reliability.json

REL_RUN = "2026-09-06"
REL_ROW = {"provider": P0, "calls": 12, "ok": 11, "empty_200": 1, "rate_limited": 0, "overloaded": 0, "timeout": 0,
           "other": 0, "answered_rate": 0.917, "note": "occasionally refuses or returns nothing"}
REL_SWITCH = {"reasoning_effort": "low"}
REL = {"measured_at": DATE, "runs_included": [REL_RUN],
       "how": "Every call in every published run, counted by outcome. One sample from one set of accounts.",
       "reasoning_trap": {"what": "A reasoning model can spend its whole budget thinking and return an empty 200.",
                          "switches": {"reasoning_effort": "gpt-oss family on Groq, Cerebras, Ollama and OpenRouter"},
                          "observed": [{"provider": P0, "model": M0, "probe": "D", "had_switch": False, "switch": None,
                                        "run": REL_RUN}],
                          "already_switched_off_by_us": []},
       "providers": [REL_ROW]}
# The switch list is providers.json's extra_body entries, copied, so an honest document carries them all.
REL["reasoning_trap"]["already_switched_off_by_us"] = [
    {"provider": p["name"], "model": m["id"], "switch": m["extra_body"]}
    for p in REAL_PROVIDERS for m in p.get("models", []) if m.get("extra_body")]
REAL_RELIABILITY = G.load_json(HERE.parent / "data" / "reliability.json", []) \
    if (HERE.parent / "data" / "reliability.json").exists() else None


def rel(**changes):
    """The honest archive with keys replaced; nested paths written as reasoning_trap__what."""
    d = json.loads(json.dumps(REL))
    for k, v in changes.items():
        cur, parts = d, k.split("__")
        for part in parts[:-1]:
            cur = cur.setdefault(part, {})
        if v is None:
            cur.pop(parts[-1], None)
        else:
            cur[parts[-1]] = v
    return d


def rel_row(**kw):
    r = dict(REL_ROW)
    r.update(kw)
    return r


RELIABILITY_MUST_REFUSE = [
    ("the reviewer's plant: every archived provider rewritten to answered_rate 1.0 with ok = calls and empty_200 0, "
     "the trap table emptied - the counts are recomputed from results/*/raw.json, which still holds the empty 200",
     (rel(providers=[rel_row(ok=12, empty_200=0, answered_rate=1.0, note="answers reliably")],
          reasoning_trap__observed=[]), raw_rows_for(REL)), "results/*/raw.json counts"),
    ("only the rate rewritten: 1.0 over 11 of 12", rel(providers=[rel_row(answered_rate=1.0)]), "does not follow"),
    ("only the note rewritten: 'answers reliably' over 11 of 12",
     rel(providers=[rel_row(note="answers reliably")]), "earns"),
    ("counts that do not add up to calls", rel(providers=[rel_row(calls=20)]), "add up to"),
    ("a negative count", rel(providers=[rel_row(timeout=-1)]), "non-negative integer"),
    ("a rate above one", rel(providers=[rel_row(answered_rate=1.5)]), "between 0 and 1"),
    ("a rate as a string", rel(providers=[rel_row(answered_rate="high")]), "between 0 and 1"),
    ("a provider nobody benchmarks", rel(providers=[rel_row(provider="ghost")]), "not in providers.json"),
    ("two rows for one provider", rel(providers=[REL_ROW, rel_row()]), "second row"),
    ("measured_at that is not a date", rel(measured_at="yesterday"), "measured_at must be a date"),
    ("measured_at after today", rel(measured_at=FUTURE), "after today"),
    ("a run later than measured_at", rel(measured_at="2026-09-05"), "later than measured_at"),
    ("runs_included empty", rel(runs_included=[]), "non-empty list of dates"),
    ("runs_included naming a run that is not on disk",
     (rel(runs_included=[REL_RUN, "2026-09-05"]), raw_rows_for(REL)), "results/ holds"),
    ("a URL in how", rel(how="See https://evil.example/method"), "contains a URL"),
    ("a markdown link in reasoning_trap.what", rel(reasoning_trap__what="See [the keys](/mirror/keys) first"), "markdown link"),
    ("a backtick in a switch description, which closes the code block it is rendered in",
     rel(reasoning_trap__switches={"reasoning_effort": "``` [keys](https://evil.example)"}), "rendered raw inside a code block"),
    ("an observed row on a model the provider does not list",
     rel(reasoning_trap__observed=[{"provider": P0, "model": "ghost-model", "probe": "D", "had_switch": False,
                                    "switch": None, "run": REL_RUN}]), "is not one of"),
    ("an observed row whose run is not among the runs included",
     rel(reasoning_trap__observed=[{"provider": P0, "model": M0, "probe": "D", "had_switch": False, "switch": None,
                                    "run": "2026-01-01"}]), "not in runs_included"),
    ("had_switch true with switch null", rel(reasoning_trap__observed=[{"provider": P0, "model": M0, "probe": "D",
                                                                       "had_switch": True, "switch": None, "run": REL_RUN}]),
     "switch must be the reasoning switch"),
    ("had_switch false with a switch attached", rel(reasoning_trap__observed=[{"provider": P0, "model": M0, "probe": "D",
                                                                             "had_switch": False, "switch": REL_SWITCH, "run": REL_RUN}]),
     "switch must be null"),
    ("a switch that rewrites the request rather than turning reasoning down",
     rel(reasoning_trap__already_switched_off_by_us=REL["reasoning_trap"]["already_switched_off_by_us"]
         + [{"provider": P0, "model": M0, "switch": {"model": "gpt-4o"}}]), "extra_body sets 'model'"),
    ("the switch list missing an entry providers.json carries: a stale archive",
     rel(reasoning_trap__already_switched_off_by_us=REL["reasoning_trap"]["already_switched_off_by_us"][1:]),
     "providers.json carries a switch for"),
    ("a probe name that closes a table cell",
     rel(reasoning_trap__observed=[{"provider": P0, "model": M0, "probe": "D | [x](https://evil.example)",
                                    "had_switch": False, "switch": None, "run": REL_RUN}]), "probe must be"),
    ("an archive with no results/ to recount from", (REL, None), "no results/*/raw.json"),
    ("an observed empty 200 the raw run does not hold",
     (rel(reasoning_trap__observed=REL["reasoning_trap"]["observed"] * 2), raw_rows_for(REL)), "recomputed from the raw runs"),
    ("a provider row the raw run does not justify: a second provider with calls the run never made",
     (rel(providers=[REL_ROW, rel_row(provider=P1, calls=4, ok=4, empty_200=0, answered_rate=1.0, note="answers reliably")]),
      raw_rows_for(REL)), "no call for this provider"),
]
RELIABILITY_MUST_PASS = [
    ("an honest archive, recounted from the raw run it describes", REL),
    ("a provider that answered every call", rel(providers=[rel_row(ok=12, empty_200=0, answered_rate=1.0, note="answers reliably")],
                                                  reasoning_trap__observed=[])),
    ("a provider that never answered: four 402s", rel(providers=[rel_row(calls=4, ok=0, empty_200=0, other=4, answered_rate=0.0,
                                                                          note="unreliable in our measurements - see the counts")],
                                                        reasoning_trap__observed=[])),
    ("a rate at the reliable line: 19 of 20 is 0.95", rel(providers=[rel_row(calls=20, ok=19, empty_200=1, answered_rate=0.95,
                                                                              note="answers reliably")])),
    ("a rate just under the reliable line: 18 of 19 is 0.947",
     rel(providers=[rel_row(calls=19, ok=18, empty_200=1, answered_rate=0.947, note="occasionally refuses or returns nothing")])),
    ("an observed empty 200 on a model whose switch was set, and ignored",
     rel(reasoning_trap__observed=[{"provider": REL["reasoning_trap"]["already_switched_off_by_us"][0]["provider"],
                                    "model": REL["reasoning_trap"]["already_switched_off_by_us"][0]["model"],
                                    "probe": "B", "had_switch": True,
                                    "switch": REL["reasoning_trap"]["already_switched_off_by_us"][0]["switch"], "run": REL_RUN}],
         providers=[rel_row(provider=REL["reasoning_trap"]["already_switched_off_by_us"][0]["provider"])])),
    ("the real archive, recounted from the real results/ tree", (REAL_RELIABILITY, "real")),
]


def check_reliability_real(fixture):
    """The real data/reliability.json against the real results/ tree."""
    problems = []
    G.check_reliability(HERE.parent / "data" / "reliability.json", problems, REAL_PROVIDERS, today=TODAY,
                        results=HERE.parent / "results")
    return problems


# ---------------------------------------------------------------- the real data, and what it must say

# Every finding the gate reports on the real files today, as (where contains, what contains). A finding
# here is a defect in the DATA, listed so the data owner fixes the data and deletes the line; it is not
# fixed by loosening the rule that found it. Anything the gate reports that is not in this list fails
# the test, and so does anything in this list that the gate no longer reports.
EXPECTED_REAL_FINDINGS = [
    # (substring of the location, substring of the message). When a real finding is knowingly left in place,
    # it is listed here so the run stays green AND the finding stays visible; when the data is fixed, the
    # entry is reported GONE and must be deleted. Before this one, the last was a burst row whose usage
    # block counted 7,048 output tokens over ten 700-token calls: the row is what the provider reported,
    # so the bound learned the tolerance bench/throughput.py states (USAGE_OVERSHOOT) instead of the data
    # being edited to fit the rule; a billion tokens from one call is refused as before.
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
    # The two meters ask every provider for the same budget a call, and the gate bounds both files by it.
    out.append(("throughput.py and draw_day.py ask for the same max_tokens a call",
                T.MAX_TOKENS_PER_CALL == D.MAX_TOKENS_PER_CALL, "%r vs %r" % (T.MAX_TOKENS_PER_CALL, D.MAX_TOKENS_PER_CALL)))
    # The daily ceilings are the project's own target, read from rank.py: a figure that can reach the daily
    # shelf is never admitted above what the whole list is trying to reach.
    import rank as R
    c = G.daily_ceilings()
    out.append(("the gate's tpd ceiling is rank.py's TARGET_TOKENS_PER_DAY", c["tpd"] == R.TARGET_TOKENS_PER_DAY,
                "%r vs %r" % (c["tpd"], R.TARGET_TOKENS_PER_DAY)))
    out.append(("the gate's rpd ceiling times rank.py's TOKENS_PER_REPLY is the largest that does not exceed the target",
                c["rpd"] * R.TOKENS_PER_REPLY <= R.TARGET_TOKENS_PER_DAY < (c["rpd"] + 1) * R.TOKENS_PER_REPLY,
                "%r x %r vs %r" % (c["rpd"], R.TOKENS_PER_REPLY, R.TARGET_TOKENS_PER_DAY)))
    out.append(("a grant in tokens and every other daily-shaped figure are capped at the target",
                c["tokens"] == c["figure"] == R.TARGET_TOKENS_PER_DAY, "%r" % (c,)))
    out.append(("the measurement line sits under the target", 0 < G.DAILY_NEEDS_MEASUREMENT_ABOVE < R.TARGET_TOKENS_PER_DAY,
                "%r" % (G.DAILY_NEEDS_MEASUREMENT_ABOVE,)))
    out.append(("every static ceiling in LIMIT_KEYS is a positive integer and the daily ones are None, read from the target",
                all((v is None) == (k in G.DAILY_KEYS) and (v is None or (isinstance(v, int) and v > 0))
                    for k, v in G.LIMIT_KEYS.items()), "%r" % (G.LIMIT_KEYS,)))
    # The states the gate does not count as a second reading are the ones states.py calls not a verdict.
    if (HERE / "states.py").exists():
        out.append(("UPTIME_NOT_A_VERDICT equals states.NOT_A_VERDICT", set(S.NOT_A_VERDICT) == G.UPTIME_NOT_A_VERDICT,
                    "%r vs %r" % (sorted(S.NOT_A_VERDICT), sorted(G.UPTIME_NOT_A_VERDICT))))
    # The archive's buckets and readings are reliability.py's, pinned to its source since it states them inline.
    rel_src = (HERE / "reliability.py").read_text(encoding="utf-8")
    for k in G.RELIABILITY_COUNTS:
        out.append(("reliability.py counts %r" % k, ('"%s"' % k) in rel_src, ""))
    for floor, sentence in G.RELIABILITY_READINGS:
        out.append(("reliability.py writes %r" % sentence, sentence in rel_src, ""))
        out.append(("reliability.py's floor %s is in its source" % floor, floor == 0.0 or ("%.2f" % floor) in rel_src, ""))
    # The request bound is above every real burst row and above the fastest a slot could plausibly answer.
    out.append(("MAX_REQUESTS_PER_SLOT_SECOND is a small positive integer", isinstance(G.MAX_REQUESTS_PER_SLOT_SECOND, int)
                and 1 <= G.MAX_REQUESTS_PER_SLOT_SECOND <= 20, "%r" % (G.MAX_REQUESTS_PER_SLOT_SECOND,)))
    # Every declared notice host is a bare registrable domain, and every operator headstone is lowercased.
    out.append(("KNOWN_NEWS_HOSTS and KNOWN_OPERATOR_HOSTS hold bare registrable domains under lowercased names",
                all(G.registrable(h) == h for h in G.KNOWN_NEWS_HOSTS)
                and all(k == k.lower() and all(G.registrable(h) == h for h in v) for k, v in G.KNOWN_OPERATOR_HOSTS.items()), ""))
    # The gate's idea of a throughput row is exactly the row the meter writes, optional fields included.
    out.append(("THROUGHPUT_FIELDS plus the optional ones equal throughput.ROW_FIELDS",
                set(G.THROUGHPUT_FIELDS) | set(G.THROUGHPUT_OPTIONAL_FIELDS) == set(T.ROW_FIELDS),
                "%r vs %r" % (sorted(set(G.THROUGHPUT_FIELDS) | set(G.THROUGHPUT_OPTIONAL_FIELDS)), sorted(T.ROW_FIELDS))))
    # The draw meter's rules, as the grader's distance section and this gate's docstring state them.
    for label, got, want in (("the draw pace ceiling is 120 a minute", D.MAX_PACE_RPM, 120),
                             ("the draw default pace is 12 a minute", D.DEFAULT_RPM, 12),
                             ("the draw cap is 250,000 tokens", D.TOKEN_CAP, 250000),
                             ("--cap may raise it to 1,000,000 at most", D.TOKEN_CAP_MAX, 1000000),
                             ("a draw rate needs 20 minutes", D.MIN_MINUTES_FOR_RATE, 20),
                             ("or a cap stop after 5 minutes", D.CAP_STOP_MIN_MINUTES, 5),
                             ("and 50 successful requests", D.CAP_STOP_MIN_REQUESTS, 50),
                             ("at most 2 requests in flight", D.MAX_IN_FLIGHT, 2)):
        out.append((label, got == want, "%r" % (got,)))
    # The registry was generated once from the two files and is kept by hand: a drift shows up here as
    # well as in the gate, with the exact line.
    live = {}
    for p in REAL_PROVIDERS:
        if p.get("key_env"):
            live[p["key_env"]] = {"host": G.host_of(p["url"]), "role": "provider"}
    for j in REAL_JUDGES:
        if j.get("via") == "api" and j.get("key_env"):
            live[j["key_env"]] = {"host": G.host_of(j["url"]), "role": "judge"}
    diff = sorted(k for k in set(live) | set(REAL_REGISTRY) if live.get(k) != REAL_REGISTRY.get(k))
    out.append(("bench/key_bindings.json equals the bindings providers.json and judges.json make today",
                not diff, "differ on %r" % diff[:4]))
    # Every switch the real files send is on the allowlist, in the allowed shape.
    used = [m.get("extra_body") for p in REAL_PROVIDERS for m in p.get("models", []) if m.get("extra_body")]
    used += [j.get("extra_body") for j in REAL_JUDGES if j.get("extra_body")]
    stray = sorted({k for eb in used for k in eb if k not in G.ALLOWED_EXTRA_BODY})
    out.append(("every extra_body key in the real files is a documented switch", not stray, "%r" % stray))
    return out


# ---------------------------------------------------------------- runner

SECTIONS = [
    ("planted pull requests that MUST be refused", MUST_REFUSE, check, True),
    ("honest pull requests that MUST pass", MUST_PASS, check, False),
    ("raw JSON shapes that MUST be refused", RAW_MUST_REFUSE, check_raw, True),
    ("raw JSON shapes that MUST pass", RAW_MUST_PASS, check_raw, False),
    ("cross-file key theft that MUST be refused", CROSS_FILE_MUST_REFUSE, check_cross_file, True),
    ("cross-file pairs that MUST pass", CROSS_FILE_MUST_PASS, check_cross_file, False),
    ("key bindings against the registry that MUST be refused", BINDINGS_MUST_REFUSE, check_bindings, True),
    ("key bindings against the registry that MUST pass", BINDINGS_MUST_PASS, check_bindings, False),
    ("juries that MUST be refused", JUDGES_MUST_REFUSE, check_judges_list, True),
    ("juries that MUST pass", JUDGES_MUST_PASS, check_judges_list, False),
    ("juries against the benchmarked families that MUST be refused", JURY_MUST_REFUSE, check_jury_against, True),
    ("juries against the benchmarked families that MUST pass", JURY_MUST_PASS, check_jury_against, False),
    ("scoped juries that MUST be refused", JURY_SCOPED_MUST_REFUSE, check_jury_scoped, True),
    ("scoped juries that MUST pass", JURY_SCOPED_MUST_PASS, check_jury_scoped, False),
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
    ("draw rows that MUST be refused", DRAWN_MUST_REFUSE, check_drawn_rows, True),
    ("draw rows that MUST pass", DRAWN_MUST_PASS, check_drawn_rows, False),
    ("retirement notices that MUST be refused", DEATHS_MUST_REFUSE, check_deaths, True),
    ("retirement notices that MUST pass", DEATHS_MUST_PASS, check_deaths, False),
    ("archived runs that MUST be refused", RELIABILITY_MUST_REFUSE, check_reliability_doc, True),
    ("archived runs that MUST pass", RELIABILITY_MUST_PASS, check_reliability_doc, False),
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
