#!/usr/bin/env python3
"""Calibrate the contribution gate in BOTH directions, on the shape of a pull request.

    python bench/test_contributions.py

A gate is only worth its exit code if you have watched it fail. This file plants the pull requests a
hostile or careless contributor would actually send, and asserts the gate refuses each one; then it
plants the honest ones and asserts the gate lets them through. A gate that says no to everything is as
useless as one that says yes to everything, and the second half of this file is what proves it is not.

The keyless cases are new and matter most: an endpoint that needs no key earns a 1.25x bonus in the
ranking, so "no key" is now a claim worth faking. It has to be declared as `auth: "none"`, never
inferred from a missing field.
"""
import json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gate_contributions as G


def check(entries):
    """Run only the provider half of the gate over a list of entries, return the problems."""
    problems = []

    class Fake:
        name = "providers.json"

    tmp = HERE / "_test_providers.json"
    tmp.write_text(json.dumps({"providers": entries}), encoding="utf-8")
    try:
        G.check_providers(tmp, problems)
    finally:
        tmp.unlink()
    return problems


OK_HOST = "https://api.groq.com/openai/v1/chat/completions"
KEYLESS_HOST = "https://hermes.ai.unturf.com/v1/chat/completions"

MUST_REFUSE = [
    ("the original attack: a stranger's host claiming an existing key variable",
     [{"name": "fastllm", "url": "https://attacker.example/v1/chat/completions", "key_env": "GROQ_API_KEY"}]),
    ("silent keyless: no key_env and no declaration, which would collect the no-key bonus",
     [{"name": "quiet", "url": KEYLESS_HOST}]),
    ("declared keyless AND a key variable, so nobody can tell which one the ranking used",
     [{"name": "twofaced", "url": KEYLESS_HOST, "auth": "none", "key_env": "TWOFACED_API_KEY"}]),
    ("an invented auth value that reads as permissive",
     [{"name": "maybe", "url": KEYLESS_HOST, "auth": "optional"}]),
    ("keyless does not exempt a host from the allowlist",
     [{"name": "elsewhere", "url": "https://attacker.example/v1/chat/completions", "auth": "none"}]),
    ("keyless over plain http",
     [{"name": "insecure", "url": "http://hermes.ai.unturf.com/v1/chat/completions", "auth": "none"}]),
    # Assembled rather than written out: a URL with userinfo in it is shaped exactly like an email
    # address, and the publication gate refuses this file if one appears as a literal. Two gates
    # disagreeing about the same string is not a reason to weaken either.
    ("keyless with credentials embedded in the URL",
     [{"name": "inline", "url": "https://" + "user:pw" + "@" + "hermes.ai.unturf.com/v1/chat/completions",
       "auth": "none"}]),
    ("keyless entries are still checked for model ids",
     [{"name": "modelless", "url": KEYLESS_HOST, "auth": "none", "models": [{"name": "no id here"}]}]),
    ("keyless pointing at localhost",
     [{"name": "loopback", "url": "https://127.0.0.1/v1/chat/completions", "auth": "none"}]),
    ("two entries, one key variable, two different hosts",
     [{"name": "groq", "url": OK_HOST, "key_env": "GROQ_API_KEY"},
      {"name": "cerebras", "url": "https://api.cerebras.ai/v1/chat/completions", "key_env": "GROQ_API_KEY"}]),
    ("a key variable that names a different provider",
     [{"name": "cerebras", "url": "https://api.cerebras.ai/v1/chat/completions", "key_env": "GROQ_API_KEY"}]),
]

MUST_PASS = [
    ("an honest keyless provider on an allowed host",
     [{"name": "uncloseai", "url": KEYLESS_HOST, "auth": "none",
       "models": [{"id": "Lorbus/Qwen3.6-27B-int4-AutoRound"}]}]),
    ("an honest key provider",
     [{"name": "groq", "url": OK_HOST, "key_env": "GROQ_API_KEY", "models": [{"id": "llama-3.3-70b"}]}]),
    ("keyless and key side by side on different hosts",
     [{"name": "groq", "url": OK_HOST, "key_env": "GROQ_API_KEY"},
      {"name": "uncloseai", "url": KEYLESS_HOST, "auth": "none"}]),
    ("a declared alias still works",
     [{"name": "google", "url": "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
       "key_env": "GEMINI_API_KEY", "signup": "https://aistudio.google.com/apikey"}]),
]


def check_privacy_entry(entry):
    """Run only the privacy half of the gate over one provider entry."""
    problems = []
    tmp = HERE / "_test_privacy.json"
    tmp.write_text(json.dumps({"providers": {"someprovider": entry}}), encoding="utf-8")
    try:
        G.check_privacy(tmp, problems)
    finally:
        tmp.unlink()
    return problems


def check_cross_file(providers, judges):
    """Both files, ONE key-binding map - the way main() runs them."""
    problems = []
    maps = G.new_bindings()
    tp = HERE / "_test_providers.json"
    tj = HERE / "_test_judges.json"
    tp.write_text(json.dumps({"providers": providers}), encoding="utf-8")
    tj.write_text(json.dumps({"judges": judges}), encoding="utf-8")
    try:
        G.check_providers(tp, problems, maps)
        G.check_judges(tj, problems, maps)
    finally:
        tp.unlink()
        tj.unlink()
    return problems


JUDGE = {"name": "glm", "via": "api", "family": "glm", "url": "https://api.z.ai/api/coding/paas/v4/chat/completions",
         "key_env": "ZAI_API_KEY"}

CROSS_FILE_MUST_REFUSE = [
    ("a contributed provider claims the JUDGE's key and points it at another allowed host",
     [{"name": "groq", "url": OK_HOST, "key_env": "ZAI_API_KEY"}], [JUDGE]),
    ("and the same theft in the other direction: a judge claims a provider's key",
     [{"name": "groq", "url": OK_HOST, "key_env": "GROQ_API_KEY"}],
     [dict(JUDGE, key_env="GROQ_API_KEY")]),
]

PRIVACY_MUST_REFUSE = [
    ("says it does not train on your prompts, with no source at all",
     {"trains_on_free_tier": "no"}),
    ("says it does not train, sourced and dated, but quotes nothing",
     {"trains_on_free_tier": "no", "source": "https://example.com/terms", "read_on": "2026-09-07"}),
    ("says it does not train, and the quote it offers says nothing of the kind",
     {"trains_on_free_tier": "no", "source": "https://example.com/terms", "read_on": "2026-09-07",
      "quotes": ["We may use your content to provide and improve the Services."]}),
    ("a dated claim with a source that is not https",
     {"logs_prompts": "yes", "source": "http://example.com/terms", "read_on": "2026-09-07",
      "quotes": ["We log prompts."]}),
    ("a sourced, quoted claim with no date",
     {"human_review": "yes", "source": "https://example.com/terms",
      "quotes": ["Human reviewers may read your input."]}),
]

PRIVACY_MUST_PASS = [
    ("UNKNOWN everywhere needs nothing - not knowing is allowed, guessing is not",
     {"trains_on_free_tier": "UNKNOWN", "logs_prompts": "UNKNOWN"}),
    ("a 'no' with a source, a date and a quote that actually negates",
     {"trains_on_free_tier": "no", "source": "https://example.com/terms", "read_on": "2026-09-07",
      "quotes": ["We do not use your prompts to train our models."]}),
    ("a 'yes' with a source, a date and their own sentence",
     {"trains_on_free_tier": "yes", "source": "https://example.com/terms", "read_on": "2026-09-07",
      "quotes": ["Google uses the content you submit to improve our products."]}),
]


def main():
    bad = 0
    print("planted pull requests that MUST be refused:")
    for label, entries in MUST_REFUSE:
        problems = check(entries)
        ok = bool(problems)
        print("  %-4s %s" % ("ok" if ok else "MISS", label))
        if not ok:
            bad += 1
        elif "-v" in sys.argv:
            for _, what in problems:
                print("         -> %s" % what[:110])

    print("\nhonest pull requests that MUST pass:")
    for label, entries in MUST_PASS:
        problems = check(entries)
        ok = not problems
        print("  %-4s %s" % ("ok" if ok else "FAIL", label))
        if not ok:
            bad += 1
            for _, what in problems:
                print("         -> %s" % what[:160])

    print()
    print("cross-file key theft that MUST be refused:")
    for label, provs, judges in CROSS_FILE_MUST_REFUSE:
        problems = check_cross_file(provs, judges)
        ok = bool(problems)
        print("  %-4s %s" % ("ok" if ok else "MISS", label))
        if not ok:
            bad += 1

    print()
    print("privacy claims that MUST be refused:")
    for label, entry in PRIVACY_MUST_REFUSE:
        problems = check_privacy_entry(entry)
        ok = bool(problems)
        print("  %-4s %s" % ("ok" if ok else "MISS", label))
        if not ok:
            bad += 1

    print()
    print("privacy claims that MUST pass:")
    for label, entry in PRIVACY_MUST_PASS:
        problems = check_privacy_entry(entry)
        ok = not problems
        print("  %-4s %s" % ("ok" if ok else "FAIL", label))
        if not ok:
            bad += 1
            for _, what in problems:
                print("         -> %s" % what[:150])

    total = (len(MUST_REFUSE) + len(MUST_PASS) + len(CROSS_FILE_MUST_REFUSE)
             + len(PRIVACY_MUST_REFUSE) + len(PRIVACY_MUST_PASS))
    print("\n%d of %d cases behaved as required" % (total - bad, total))
    if bad:
        print("THE GATE IS MISCALIBRATED. Fix it before merging anything.")
        return 1
    print("CLEAN - the gate refuses what it must and admits what it must.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
