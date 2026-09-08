#!/usr/bin/env python3
"""Calibrate the pull-request gate in BOTH directions, on the shape of a pull request.

    python bench/test_pr.py

A gate is only worth its exit code if you have watched it fail. This file builds a small repository
tree, applies to a copy of it the pull requests a hostile or careless contributor would send, and
asserts that bench/gate_pr.py refuses each one NAMING THE FILE AND THE RULE, and refuses nothing else
in that pull request: a refusal for some other file is a miss, because the rule under test never fired.
Then it applies the honest pull requests and asserts the gate lets them through.

The planted shapes are the ones a content gate admitted: a radar row appended, a drawn row deleted, a
scores file edited, two registry lines swapped next to two URLs, a host removed from the allow-list, a
provider removed with no `retire:` title. The honest ones are the ones a contributor actually sends: a
new provider added in all six places, a limit corrected, the pages regenerated, a docs change, and a
retirement that says so in its title.

Where git is on the machine the same rules are exercised on a scratch repository with a base branch
and a pull-request branch, including the one property the directory mode cannot show: a measurement
pushed to main while the pull request is open does not make the pull request red, because the gate
reads base...head, not base..head.

Last, the pages: every walled file the gate names must be named in CONTRIBUTING.md and SECURITY.md, so
the list a contributor reads cannot drift from the list the gate enforces.
"""
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
GATE = HERE / "gate_pr.py"
sys.path.insert(0, str(HERE))
import gate_pr as P

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
CEREBRAS_URL = "https://api.cerebras.ai/v1/chat/completions"
NEW_URL = "https://api.newprov.example/v1/chat/completions"


# ------------------------------------------------------------------------------------ the fixture

def radar(date, provider, model, state="alive", http=200):
    return json.dumps({"date": date, "provider": provider, "model": model, "state": state, "http": http}) + "\n"


def drawn(provider, model, tokens):
    return json.dumps({"date": "2026-09-07", "provider": provider, "model": model, "pace_rpm": 10,
                       "minutes_run": 60.0, "requests_ok": 300, "requests_failed": 0,
                       "output_tokens_drawn": tokens, "tokens_per_hour_drawn": tokens}) + "\n"


GATE_STUB = '''"""A stub of the contribution gate: only the host maps matter to the pull-request gate."""
KNOWN_KEY_ALIASES = {"google": "GEMINI_API_KEY"}

ALLOWED_HOSTS = {
    "api.groq.com",
    "api.cerebras.ai",   # free tier (see bench/limits.json)
    "api.z.ai",          # judge, not a benchmarked provider
}

KNOWN_SIGNUP_HOSTS = {
    # provider: hosts where you obtain a key, when it differs from the API host (a console elsewhere)
    "groq": {"groq.com"},
    "cerebras": {"cerebras.ai"},
}

KNOWN_TERMS_HOSTS = {
    "ovhcloud": {"ovhcloud.com"},   # the docs (and the terms) live on another host
}

LIMIT_KEYS = {"rpd": 10 ** 7}
GRANT_CEILINGS = {"tokens": LIMIT_KEYS["rpd"]}   # not a literal, and not one of the three maps


def host_of(url):
    return url.split("/")[2]


def main():
    return 0
'''


def provider_block(name, url, key_env, signup):
    return {"name": name, "url": url, "key_env": key_env, "signup": signup, "pause_seconds": 5,
            "models": [{"id": "llama-3.3-70b"}]}


def fixture():
    """path -> text of the base tree."""
    files = {
        "data/uptime.jsonl": radar("2026-09-06", "groq", "llama-3.3-70b") + radar("2026-09-06", "cerebras", "llama-3.3-70b"),
        "data/uptime-superseded.jsonl": radar("2026-09-05", "groq", "llama-3.3-70b", "down", 500),
        "data/throughput.jsonl": json.dumps({"date": "2026-09-07", "provider": "groq", "model": "llama-3.3-70b",
                                             "concurrency": 8, "seconds": 30.0, "requests_ok": 40,
                                             "output_tokens": 28000, "tokens_per_minute_measured": 56000}) + "\n",
        "data/drawn.jsonl": drawn("groq", "llama-3.3-70b", 200000) + drawn("cerebras", "llama-3.3-70b", 150000),
        "data/reliability.json": json.dumps({"providers": [{"provider": "groq", "answered_rate": 0.5}]}, indent=1),
        "data/scores.json": json.dumps({"fetched_on": "2026-09-06", "models": {"llama-3.3-70b": {"coding_index": 40.0}}}, indent=1),
        "data/scores-drift.jsonl": json.dumps({"date": "2026-09-06", "refused": False}) + "\n",
        "data/catalog.json": json.dumps({"date": "2026-09-06", "providers": {}}, indent=1),
        "results/2026-09-06/raw.json": json.dumps({"runs": [{"provider": "groq", "ok": True}]}, indent=1),
        "results/2026-09-06/agreement.md": "# Agreement\n\nThe two judges agreed on 9 of 10 paragraphs.\n",
        "data/ranking.json": json.dumps({"measured_at": "2026-09-06", "ranked": [{"provider": "groq", "value": 100.0}]}, indent=1),
        "data/ranking.csv": "provider,value\ngroq,100.0\n",
        "data/capacity.json": json.dumps({"defensible_tokens_per_day": 350000}, indent=1),
        "data/viability.json": json.dumps({"buried": []}, indent=1),
        "bench/key_bindings.json": json.dumps({
            "_comment": ["which host each key variable may reach"],
            "bindings": {
                "GROQ_API_KEY": {"host": "api.groq.com", "role": "provider"},
                "CEREBRAS_API_KEY": {"host": "api.cerebras.ai", "role": "provider"},
                "ZAI_API_KEY": {"host": "api.z.ai", "role": "judge"},
            }}, indent=1),
        "bench/providers.json": json.dumps({
            "_comment": ["every provider speaks the same shape"],
            "providers": [
                provider_block("groq", GROQ_URL, "GROQ_API_KEY", "https://console.groq.com/keys"),
                provider_block("cerebras", CEREBRAS_URL, "CEREBRAS_API_KEY", "https://cloud.cerebras.ai"),
            ]}, indent=1),
        "bench/gate_contributions.py": GATE_STUB,
        "bench/limits.json": json.dumps({
            "groq": {"all_models": {"rpd": 1000, "tpd": None}, "confidence": "DECLARED",
                     "source": "https://console.groq.com/docs/rate-limits", "read_on": "2026-09-06"},
            "cerebras": {"all_models": {"rpd": None, "tpd": 1000000}, "confidence": "MEASURED",
                         "measured_on": "2026-09-06", "measured_how": "response headers"},
        }, indent=1),
        "bench/privacy.json": json.dumps({"groq": {"trains_on_free_tier": "UNKNOWN"},
                                          "cerebras": {"trains_on_free_tier": "UNKNOWN"}}, indent=1),
        "bench/rank.py": "#!/usr/bin/env python3\n\"\"\"The page generator.\"\"\"\nTARGET = 10 ** 9\n",
        "README.md": "# Free LLM APIs\n\n<!--HEADLINE-->\n| Tokens a day | 350,000 |\n<!--/HEADLINE-->\n\nRead METHOD.md.\n",
        "RESULTS.md": "# Results\n\n| 1 | `llama-3.3-70b` | groq | **100.0** |\n",
        "CONTRIBUTING.md": "# Contributing\n\nCorrect a rate limit in bench/limits.json.\n",
        "METHOD.md": "# Method\n\nFour models, two judges.\n",
    }
    return files


def write_tree(root, files):
    for rel, text in files.items():
        p = Path(root) / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8", newline="\n")


# ------------------------------------------------------------------------------ mutations

def read(head, rel):
    return (Path(head) / rel).read_text(encoding="utf-8")


def write(head, rel, text):
    p = Path(head) / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8", newline="\n")


def edit_json(head, rel, fn):
    data = json.loads(read(head, rel))
    fn(data)
    write(head, rel, json.dumps(data, indent=1))


def replace(head, rel, old, new):
    text = read(head, rel)
    assert old in text, "fixture drift: %r not in %s" % (old, rel)
    write(head, rel, text.replace(old, new, 1))


def remove(head, rel):
    (Path(head) / rel).unlink()


def swap_registry_and_urls(head):
    """The URL swap plus the registry swap in one pull request: the contribution gate's registry check
    sees one key per host and one host per key and says CLEAN; here two existing lines changed."""
    def swap_bindings(d):
        d["bindings"]["GROQ_API_KEY"]["host"] = "api.cerebras.ai"
        d["bindings"]["CEREBRAS_API_KEY"]["host"] = "api.groq.com"
    edit_json(head, "bench/key_bindings.json", swap_bindings)

    def swap_urls(d):
        by = {p["name"]: p for p in d["providers"]}
        by["groq"]["url"], by["cerebras"]["url"] = CEREBRAS_URL, GROQ_URL
    edit_json(head, "bench/providers.json", swap_urls)


def add_provider(head):
    """The six edits of a new provider, in one pull request."""
    edit_json(head, "bench/providers.json",
              lambda d: d["providers"].append(provider_block("newprov", NEW_URL, "NEWPROV_API_KEY",
                                                             "https://console.newprov.example/keys")))
    edit_json(head, "bench/key_bindings.json",
              lambda d: d["bindings"].__setitem__("NEWPROV_API_KEY", {"host": "api.newprov.example", "role": "provider"}))
    replace(head, "bench/gate_contributions.py", '    "api.z.ai",', '    "api.newprov.example",  # measured answering 2026-09-08\n    "api.z.ai",')
    replace(head, "bench/gate_contributions.py", '    "cerebras": {"cerebras.ai"},', '    "cerebras": {"cerebras.ai"},\n    "newprov": {"newprov.example"},')
    edit_json(head, "bench/limits.json",
              lambda d: d.__setitem__("newprov", {"all_models": {"rpd": None, "tpd": None}, "confidence": "UNKNOWN"}))
    edit_json(head, "bench/privacy.json", lambda d: d.__setitem__("newprov", {"trains_on_free_tier": "UNKNOWN"}))


def retire_groq(head):
    """A retirement: the provider block, its binding and its hosts removed, nothing changed."""
    edit_json(head, "bench/providers.json",
              lambda d: d.__setitem__("providers", [p for p in d["providers"] if p["name"] != "groq"]))
    edit_json(head, "bench/key_bindings.json", lambda d: d["bindings"].pop("GROQ_API_KEY"))
    replace(head, "bench/gate_contributions.py", '    "api.groq.com",\n', "")
    replace(head, "bench/gate_contributions.py", '    "groq": {"groq.com"},\n', "")
    edit_json(head, "bench/limits.json", lambda d: d.pop("groq"))
    edit_json(head, "bench/privacy.json", lambda d: d.pop("groq"))


def regenerate(head):
    """What a contributor commits after `python bench/rank.py`: pages and generator outputs."""
    replace(head, "README.md", "| Tokens a day | 350,000 |", "| Tokens a day | 351,000 |")
    replace(head, "RESULTS.md", "**100.0**", "**100.4**")
    edit_json(head, "data/ranking.json", lambda d: d["ranked"][0].__setitem__("value", 100.4))
    write(head, "data/ranking.csv", "provider,value\ngroq,100.4\n")
    edit_json(head, "data/capacity.json", lambda d: d.__setitem__("defensible_tokens_per_day", 351000))
    edit_json(head, "data/viability.json", lambda d: d.__setitem__("buried", []))
    write(head, "GRAVEYARD.md", "# Graveyard\n\nNothing buried.\n")


U = "data/uptime.jsonl"
R = P.RULE_1
A = P.RULE_2
T = P.RULE_3

# (label, mutation, title, {file: rule, ...}) : the gate must exit 1 and refuse EXACTLY these files.
MUST_REFUSE = [
    ("a line appended to data/uptime.jsonl",
     lambda h: write(h, U, read(h, U) + radar("2026-09-07", "groq", "llama-3.3-70b", "down", 500)), "", {U: R}),
    ("a row deleted from data/drawn.jsonl",
     lambda h: write(h, "data/drawn.jsonl", drawn("groq", "llama-3.3-70b", 200000)), "", {"data/drawn.jsonl": R}),
    ("data/scores.json edited",
     lambda h: edit_json(h, "data/scores.json", lambda d: d["models"]["llama-3.3-70b"].__setitem__("coding_index", 90.0)),
     "", {"data/scores.json": R}),
    ("data/reliability.json rewritten",
     lambda h: edit_json(h, "data/reliability.json", lambda d: d["providers"][0].__setitem__("answered_rate", 1.0)),
     "", {"data/reliability.json": R}),
    ("a burst row appended to data/throughput.jsonl",
     lambda h: write(h, "data/throughput.jsonl", read(h, "data/throughput.jsonl") + read(h, "data/throughput.jsonl")),
     "", {"data/throughput.jsonl": R}),
    ("an archived radar row edited in data/uptime-superseded.jsonl",
     lambda h: write(h, "data/uptime-superseded.jsonl", ""), "", {"data/uptime-superseded.jsonl": R}),
    ("data/catalog.json edited",
     lambda h: edit_json(h, "data/catalog.json", lambda d: d.__setitem__("providers", {"x": 1})), "", {"data/catalog.json": R}),
    ("a results file sent in a pull request",
     lambda h: write(h, "results/2026-09-08/raw.json", '{"runs": []}\n'), "", {"results/2026-09-08/raw.json": R}),
    ("an archived run's raw.json edited",
     lambda h: write(h, "results/2026-09-06/raw.json", '{"runs": []}\n'), "", {"results/2026-09-06/raw.json": R}),
    ("a measurement file moved (renames are switched off: a deletion and an addition)",
     lambda h: (write(h, "data/archive/uptime.jsonl", read(h, U)), remove(h, U)), "", {U: R}),
    ("two registry lines swapped next to two URLs",
     swap_registry_and_urls, "", {"bench/key_bindings.json": A, "bench/providers.json": A}),
    ("an existing provider's URL changed",
     lambda h: edit_json(h, "bench/providers.json", lambda d: d["providers"][0].__setitem__("url", NEW_URL)),
     "", {"bench/providers.json": A}),
    ("an existing provider's key variable changed",
     lambda h: edit_json(h, "bench/providers.json", lambda d: d["providers"][1].__setitem__("key_env", "GROQ_API_KEY")),
     "", {"bench/providers.json": A}),
    ("an existing binding's host changed",
     lambda h: edit_json(h, "bench/key_bindings.json", lambda d: d["bindings"]["GROQ_API_KEY"].__setitem__("host", "api.newprov.example")),
     "", {"bench/key_bindings.json": A}),
    ("an existing binding's role changed",
     lambda h: edit_json(h, "bench/key_bindings.json", lambda d: d["bindings"]["ZAI_API_KEY"].__setitem__("role", "provider")),
     "", {"bench/key_bindings.json": A}),
    ("a binding removed with no retire: title",
     lambda h: edit_json(h, "bench/key_bindings.json", lambda d: d["bindings"].pop("CEREBRAS_API_KEY")),
     "", {"bench/key_bindings.json": T}),
    ("a provider removed with no retire: title",
     lambda h: edit_json(h, "bench/providers.json", lambda d: d["providers"].pop(0)), "", {"bench/providers.json": T}),
    ("bench/key_bindings.json deleted",
     lambda h: remove(h, "bench/key_bindings.json"), "", {"bench/key_bindings.json": A}),
    ("bench/providers.json that no longer parses",
     lambda h: write(h, "bench/providers.json", "{not json"), "", {"bench/providers.json": "cannot be parsed"}),
    ("a host removed from ALLOWED_HOSTS",
     lambda h: replace(h, "bench/gate_contributions.py", '    "api.groq.com",\n', ""), "", {"bench/gate_contributions.py": T}),
    ("a host replaced in ALLOWED_HOSTS",
     lambda h: replace(h, "bench/gate_contributions.py", '"api.groq.com"', '"api.newprov.example"'), "",
     {"bench/gate_contributions.py": T}),
    ("a sign-up host removed from KNOWN_SIGNUP_HOSTS",
     lambda h: replace(h, "bench/gate_contributions.py", '    "groq": {"groq.com"},\n', ""), "",
     {"bench/gate_contributions.py": T}),
    ("a terms host changed in KNOWN_TERMS_HOSTS",
     lambda h: replace(h, "bench/gate_contributions.py", '"ovhcloud.com"', '"ovhcloud.example"'), "",
     {"bench/gate_contributions.py": T}),
    ("ALLOWED_HOSTS turned into an expression",
     lambda h: replace(h, "bench/gate_contributions.py", "ALLOWED_HOSTS = {", "ALLOWED_HOSTS = set(__import__('os').environ.get('H', '').split()) | {"),
     "", {"bench/gate_contributions.py": "not a literal"}),
    ("ALLOWED_HOSTS assigned a second time at the bottom of the file",
     lambda h: write(h, "bench/gate_contributions.py", read(h, "bench/gate_contributions.py") + '\nALLOWED_HOSTS = {"api.newprov.example"}\n'),
     "", {"bench/gate_contributions.py": "assigned twice"}),
    ("ALLOWED_HOSTS augmented after the literal",
     lambda h: write(h, "bench/gate_contributions.py", read(h, "bench/gate_contributions.py") + '\nALLOWED_HOSTS |= {"api.newprov.example"}\n'),
     "", {"bench/gate_contributions.py": "bound 2 times"}),
    ("ALLOWED_HOSTS.discard() called later in the file",
     lambda h: write(h, "bench/gate_contributions.py", read(h, "bench/gate_contributions.py") + '\nALLOWED_HOSTS.discard("api.groq.com")\n'),
     "", {"bench/gate_contributions.py": "discard() is called"}),
    ("KNOWN_SIGNUP_HOSTS rebound inside a function",
     lambda h: write(h, "bench/gate_contributions.py", read(h, "bench/gate_contributions.py") + '\ndef widen():\n    global KNOWN_SIGNUP_HOSTS\n    KNOWN_SIGNUP_HOSTS = {}\n'),
     "", {"bench/gate_contributions.py": "bound 2 times"}),
    ("bench/gate_contributions.py deleted",
     lambda h: remove(h, "bench/gate_contributions.py"), "", {"bench/gate_contributions.py": A}),
    ("retire: title, but a radar row appended too",
     lambda h: (retire_groq(h), write(h, U, read(h, U) + radar("2026-09-07", "cerebras", "llama-3.3-70b"))),
     "retire: groq", {U: R}),
    ("retire: title, but an existing binding's host changed",
     lambda h: edit_json(h, "bench/key_bindings.json", lambda d: d["bindings"]["GROQ_API_KEY"].__setitem__("host", "api.newprov.example")),
     "retire: groq", {"bench/key_bindings.json": A}),
    ("retire: title, but a host swapped rather than removed in ALLOWED_HOSTS is still a removal plus an addition and passes there; the URL edit on the surviving provider is what is refused",
     lambda h: (replace(h, "bench/gate_contributions.py", '"api.groq.com"', '"api.newprov.example"'),
                edit_json(h, "bench/providers.json", lambda d: d["providers"][0].__setitem__("url", NEW_URL))),
     "retire: groq", {"bench/providers.json": A}),
    ("a retirement whose title says something else",
     retire_groq, "remove groq, it is dead", {"bench/providers.json": T, "bench/key_bindings.json": T, "bench/gate_contributions.py": T}),
]

# (label, mutation, title): the gate must exit 0.
MUST_PASS = [
    ("nothing changed", lambda h: None, ""),
    ("a new provider added in all six places", add_provider, ""),
    ("a limits.json figure corrected",
     lambda h: edit_json(h, "bench/limits.json", lambda d: d["groq"]["all_models"].__setitem__("rpd", 1200)), ""),
    ("a privacy.json entry corrected",
     lambda h: edit_json(h, "bench/privacy.json", lambda d: d["groq"].__setitem__("trains_on_free_tier", "no")), ""),
    ("the pages regenerated: README, RESULTS, GRAVEYARD, ranking, capacity and viability changed", regenerate, ""),
    ("a docs-only change",
     lambda h: (write(h, "CONTRIBUTING.md", read(h, "CONTRIBUTING.md") + "\nSay how you know.\n"),
                write(h, "README.md", read(h, "README.md").replace("Read METHOD.md.", "Read METHOD.md first."))), ""),
    ("a comment changed inside a host map, entries untouched",
     lambda h: replace(h, "bench/gate_contributions.py", "# judge, not a benchmarked provider", "# the judge's host"), ""),
    ("the generator and the gate's code edited, host maps untouched",
     lambda h: (write(h, "bench/rank.py", read(h, "bench/rank.py") + "\n\ndef shelf():\n    return 0\n"),
                replace(h, "bench/gate_contributions.py", "def main():\n    return 0", "def main():\n    return int(False)")), ""),
    ("a second sign-up host added to an existing provider",
     lambda h: replace(h, "bench/gate_contributions.py", '"groq": {"groq.com"}', '"groq": {"groq.com", "groqcloud.example"}'), ""),
    ("a new file under data/ that is not a measurement",
     lambda h: write(h, "data/notes.json", '{"note": "a hand-kept list"}\n'), ""),
    ("a retirement under a retire: title", retire_groq, "retire: groq"),
    ("a retirement under a retire: title, any case, leading space", retire_groq, "  Retire: groq (dead since August)"),
    ("a new provider added under a retire: title", add_provider, "retire: nothing, but the title says so"),
    ("the additions-only files created from nothing (a fork with no registry yet)",
     lambda h: (remove(h, "bench/key_bindings.json"), None), ""),
]


# ------------------------------------------------------------------------------- the runner

def run_gate(*args):
    r = subprocess.run([sys.executable, str(GATE)] + [str(a) for a in args],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def refused_files(out):
    """{path: the rest of the line} for every REFUSED line."""
    got = {}
    for line in out.splitlines():
        s = line.strip()
        if s.startswith("REFUSED ") and ":" in s:
            path, _, rest = s[len("REFUSED "):].partition(":")
            got[path.strip()] = rest.strip()
        elif s.startswith("REFUSED:"):
            got["<whole>"] = s
    return got


def dir_cases(base_files):
    failures, checks = [], 0
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp) / "base"
        write_tree(base, base_files)
        for label, mutate, title, expected in MUST_REFUSE:
            checks += 1
            head = Path(tmp) / "head"
            if head.exists():
                shutil.rmtree(head)
            shutil.copytree(base, head)
            mutate(head)
            code, out = run_gate("--files-from-dirs", base, head, "--title", title)
            got = refused_files(out)
            problems = []
            if code != 1:
                problems.append("exit %d, wanted 1" % code)
            whole = got.pop("<whole>", None)
            for path, rule in expected.items():
                if path in got:
                    if rule and rule not in got[path]:
                        problems.append("%s refused, but not for %r: %s" % (path, rule, got[path][:120]))
                elif whole and path in whole and (not rule or rule in whole):
                    pass
                else:
                    problems.append("%s not refused" % path)
            for path in got:
                if path not in expected:
                    problems.append("%s refused too, and it should not be: %s" % (path, got[path][:120]))
            print("  %-4s %s" % ("ok" if not problems else "FAIL", label))
            for p in problems:
                print("         -> %s" % p)
            if problems:
                failures.append(("MUST_REFUSE", label, "; ".join(problems)))
        print()
        for label, mutate, title in MUST_PASS:
            checks += 1
            head = Path(tmp) / "head"
            if head.exists():
                shutil.rmtree(head)
            shutil.copytree(base, head)
            mutate(head)
            if label.startswith("the additions-only files created"):
                # the base side has no registry; the head side has one. Every entry is new.
                code, out = run_gate("--files-from-dirs", head, base, "--title", title)
            else:
                code, out = run_gate("--files-from-dirs", base, head, "--title", title)
            ok = code == 0 and not refused_files(out)
            print("  %-4s %s" % ("ok" if ok else "FAIL", label))
            if not ok:
                print("         -> exit %d\n%s" % (code, "\n".join("         " + l for l in out.splitlines()[:8])))
                failures.append(("MUST_PASS", label, "exit %d" % code))
    return checks, failures


def git_cmd(repo):
    return ["git", "-C", str(repo), "-c", "user.name=Someone", "-c", "user.email=gate-pr-test@example.com",
            "-c", "commit.gpgsign=false", "-c", "core.autocrlf=false"]


def git_cases(base_files):
    """A scratch repository: main with the base tree, a pull-request branch, and a radar push to main."""
    failures, checks = [], 0
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp) / "repo"
        repo.mkdir()
        g = git_cmd(repo)

        def sh(*args):
            subprocess.run(g + list(args), check=True, capture_output=True)

        try:
            subprocess.run(["git", "-c", "init.defaultBranch=main", "init", "-q", str(repo)], check=True, capture_output=True)
            write_tree(repo, base_files)
            sh("add", "-A")
            sh("commit", "-q", "-m", "base")
            sh("checkout", "-q", "-b", "pr")
            add_provider(repo)
            write(repo, "CONTRIBUTING.md", read(repo, "CONTRIBUTING.md") + "\nSay how you know.\n")
            sh("add", "-A")
            sh("commit", "-q", "-m", "add newprov, six edits")
            sh("checkout", "-q", "main")
            write(repo, U, read(repo, U) + radar("2026-09-07", "groq", "llama-3.3-70b"))
            sh("add", "-A")
            sh("commit", "-q", "-m", "radar: 2026-09-07, pushed from the machine that holds the keys")
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            print("  skip git is needed for this direction and failed: %s" % e)
            return 0, [("git", "scratch repo", "git failed: %s" % e)]

        def case(label, want_code, args, want_files=()):
            nonlocal checks
            checks += 1
            code, out = run_gate("--root", repo, *args)
            got = refused_files(out)
            problems = []
            if code != want_code:
                problems.append("exit %d, wanted %d" % (code, want_code))
            for f in want_files:
                if f not in got:
                    problems.append("%s not refused" % f)
            for f in got:
                if f not in want_files:
                    problems.append("%s refused too: %s" % (f, got[f][:100]))
            print("  %-4s %s" % ("ok" if not problems else "FAIL", label))
            for p in problems:
                print("         -> %s" % p)
            if problems:
                failures.append(("git", label, "; ".join(problems)))

        case("an honest pull request, while main took a radar push meanwhile (base...head, not base..head)",
             0, ["--base", "main", "--head", "pr"])
        case("the same, seen from the radar's side: main against the pull request is the radar row",
             1, ["--base", "pr", "--head", "main"], (U,))
        sh("checkout", "-q", "pr")
        write(repo, U, read(repo, U) + radar("2026-09-07", "cerebras", "llama-3.3-70b", "down", 500))
        sh("add", "-A")
        sh("commit", "-q", "-m", "also a radar row")
        case("the pull request then appends a radar row of its own", 1, ["--base", "main", "--head", "pr"], (U,))
        sh("checkout", "-q", "main")
        sh("checkout", "-q", "-b", "retire")
        retire_groq(repo)
        sh("add", "-A")
        sh("commit", "-q", "-m", "retire: groq")
        case("a retirement branch with the title", 0, ["--base", "main", "--head", "retire", "--title", "retire: groq"])
        case("the same branch without the title", 1, ["--base", "main", "--head", "retire"],
             ("bench/providers.json", "bench/key_bindings.json", "bench/gate_contributions.py"))
        case("a base ref that does not exist is exit 2, not a pass", 2, ["--base", "no-such-branch", "--head", "main"])
        sh("checkout", "-q", "main")
        write(repo, "data/uptime-moved.jsonl", read(repo, U))
        remove(repo, U)
        sh("add", "-A")
        sh("commit", "-q", "-m", "move the radar file")
        case("a measurement file renamed on the head side is a deletion, refused", 1,
             ["--base", "main~1", "--head", "main"], (U,))
    return checks, failures


def page_cases():
    """The pages name every walled file, so the list a contributor reads is the list the gate enforces."""
    failures, checks = [], 0
    pages = {"CONTRIBUTING.md": (ROOT / "CONTRIBUTING.md"), "SECURITY.md": (ROOT / "SECURITY.md")}
    texts = {}
    for name, p in pages.items():
        texts[name] = p.read_text(encoding="utf-8") if p.exists() else ""
    walled = list(P.MEASUREMENT_FILES) + [d.rstrip("/") + "/" for d in P.MEASUREMENT_DIRS]
    for name, text in texts.items():
        for path in walled + list(P.ADD_ONLY_JSON) + [P.HOST_MAPS_FILE, "retire:"]:
            checks += 1
            ok = path in text
            if not ok:
                failures.append(("pages", name, "%s is not named on the page" % path))
                print("  FAIL %s does not name %s" % (name, path))
    template = ROOT / ".github" / "pull_request_template.md"
    checks += 1
    ttext = template.read_text(encoding="utf-8") if template.exists() else ""
    if "retire:" not in ttext or "gate_pr.py" not in ttext:
        failures.append(("pages", "pull_request_template.md", "must name gate_pr.py and the retire: title"))
        print("  FAIL the pull request template does not name gate_pr.py and the retire: title")
    if not failures:
        print("  ok   CONTRIBUTING.md and SECURITY.md name every walled file, the additions-only files and the retire: title")
        print("  ok   the pull request template names gate_pr.py and the retire: title")
    checks += 1
    code, out = run_gate("--list-walls")
    missing = [p for p in walled if p.rstrip("/") not in out]
    if code != 0 or missing:
        failures.append(("pages", "--list-walls", "exit %d, missing %s" % (code, missing)))
        print("  FAIL --list-walls: exit %d, missing %s" % (code, missing))
    else:
        print("  ok   --list-walls prints every walled file")
    return checks, failures


def main():
    base_files = fixture()
    total, failures = 0, []

    print("=== two trees, no git: what must be refused, and for which file ===")
    n, f = dir_cases(base_files)
    total += n
    failures += f

    print("\n=== a scratch repository: base...head ===")
    n, f = git_cases(base_files)
    total += n
    failures += f

    print("\n=== the pages say what the gate enforces ===")
    n, f = page_cases()
    total += n
    failures += f

    print("\n%d checks, %d failures" % (total, len(failures)))
    if failures:
        for where, label, why in failures:
            print("  %s: %s: %s" % (where, label, why))
        print("THE GATE IS MISCALIBRATED. Fix it before merging anything.")
        return 1
    print("CLEAN - the gate refuses what it must and admits what it must.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
