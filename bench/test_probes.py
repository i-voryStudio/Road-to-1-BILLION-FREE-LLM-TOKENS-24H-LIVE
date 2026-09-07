#!/usr/bin/env python3
"""Unit tests for the probe checkers. No network, no keys, no API calls.

Every one of these cases is a real answer shape a free model returned during our runs. Two of them cost
us a wrong scoreboard before they were pinned here: "14400, 81600" (a list read as one number) and
"14400,81600" (a list separator read as a thousands separator). A checker that silently misreads either
one rewrites the whole ranking, so both directions are tested: correct answers must pass, wrong answers
must fail.

The second half pins the one door every key-carrying script goes through: the redirect handler in
http_safe.py, and the rule that nobody opens a raw connection around it.

    python bench/test_probes.py
"""
import ast, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import benchmark as B

RO = json.loads((Path(__file__).resolve().parent / "languages" / "ro.json").read_text(encoding="utf-8"))
EN = json.loads((Path(__file__).resolve().parent / "languages" / "en.json").read_text(encoding="utf-8"))

CASES = [
    # (probe, language pack, answer text, must pass?, what it pins down)
    ("A", RO, "14400, 81600", True, "plain list, the shape the prompt asks for"),
    ("A", RO, "14400,81600", True, "list with no space: the comma is NOT a thousands separator here"),
    ("A", RO, "14.400, 81.600", True, "Romanian thousands separator is the dot"),
    ("A", RO, "14,400, 81,600", True, "English thousands separator"),
    ("A", RO, "14 400, 81 600", True, "space as thousands separator"),
    ("A", RO, "Reducerea este de 14400 euro, iar de plată rămân 81600 euro.", True, "numbers inside a sentence"),
    ("A", RO, "14400 și 81000", False, "second number wrong"),
    ("A", RO, "144000, 816000", False, "both off by a factor of ten"),
    ("A", RO, "1440081600", False, "digits run together, no separator: not the two numbers"),
    ("A", RO, "214400, 81600", False, "first number has a leading digit glued on"),
    ("A", RO, "", False, "empty answer"),

    ("B", RO, "Dacă vrei să cumperi un abonament anual trebuie să ai suma pregătită.", True, "correct diacritics"),
    ("B", RO, "Daca vrei sa cumperi un abonament anual trebuie sa ai suma pregatita.", False, "no diacritics at all"),
    ("B", RO, "Dacă vrei şă cumperi un abonament anual trebuie şă ai suma pregătită.", False,
     "cedilla instead of comma-below: the single most common Romanian failure"),
    ("B", RO, "Dacă vrei să cumperi ceva anual trebuie să ai suma pregătită.", False, "dropped the required word"),

    ("C", RO, '{"serie": "Meridian", "module": 2, "watti": 54, "revizie": 3, "unitati": 89900}', True, "exact object"),
    ("C", RO, 'Iată JSON-ul:\n```json\n{"serie": "Seria Meridian", "module": 2, "watti": 54, "revizie": 3, "unitati": 89900}\n```',
     True, "wrapped in prose and a code fence, values still right"),
    ("C", RO, '{"serie": "Meridian", "module": "2", "watti": 54, "revizie": 3, "unitati": 89900}', False,
     "number sent as a string, which is exactly what the prompt forbids"),
    ("C", RO, '{"serie": "Meridian", "module": 2, "watti": 54, "revizie": 3}', False, "missing key"),
    ("C", RO, "serie: Meridian, module: 2", False, "not JSON at all"),

    ("D", RO, ("Băncile cer de obicei un avans între zece și douăzeci la sută din valoarea bunului, iar motivul "
               "ține de risc. Un cumpărător care pune bani proprii de la început are mai mult de pierdut dacă nu "
               "mai plătește, așa că se poartă altfel cu ratele. Pentru bancă, avansul acoperă și diferența dintre "
               "prețul plătit azi și cât s-ar obține pe bun dacă ar trebui vândut repede, într-o piață care nu "
               "așteaptă. De aceea suma cerută crește atunci când bunul e mai greu de vândut sau când venitul "
               "celui care împrumută pare nesigur, și scade când garanția e solidă și ușor de evaluat corect."),
     True, "in range, diacritics, no markdown"),
    ("D", RO, "Prea scurt.", False, "under the word floor"),
    ("D", RO, ("- Băncile cer un avans\n- Motivul ține de risc\n- Avansul acoperă diferența de preț și oferă "
               "garanție suplimentară pentru instituția care împrumută banii clientului său obișnuit."),
     False, "a list, which the prompt forbids"),

    ("A", EN, "14400, 81600", True, "English pack, same arithmetic"),
    ("B", EN, "If you wanted to buy an annual subscription you needed to have the money ready.", True,
     "past tense, no contractions"),
    ("B", EN, "If you'd wanted to buy an annual subscription you'd have needed the money ready.", False,
     "contractions, which the prompt forbids"),
]


# --- generation parameters -------------------------------------------------------------------------
# Sending these explicitly is what makes a second run comparable with the first. Leaving them out means
# every provider applies its own default, the defaults differ and change without notice, and the whole
# ranking quietly stops being reproducible. These cases pin the wiring, offline.

def check_generation():
    fails = []
    gen = {"temperature": 0, "top_p": 1, "seed": 20260906}

    body, applied, dropped = B.build_body("m", "p", None, 100, gen, [])
    for k, v in gen.items():
        if body.get(k) != v:
            fails.append("%s missing from the request body: a parameter we do not send is a parameter "
                         "the provider chooses for us" % k)
    if dropped:
        fails.append("nothing was declared unsupported, yet %s was dropped" % dropped)

    body, applied, dropped = B.build_body("m", "p", None, 100, gen, ["seed"])
    if "seed" in body:
        fails.append("seed was sent to a provider that declares it unsupported: measured on 2026-09-06, "
                     "Google returns HTTP 400 for it and the whole run would fail")
    if dropped != ["seed"] or "seed" in applied:
        fails.append("a dropped parameter must be reported as dropped, not as applied: the results file "
                     "has to say which settings each model was actually measured under")
    if body.get("temperature") != 0:
        fails.append("dropping one parameter must not drop the others")

    # A provider's own extra_body still wins: some models need enable_thinking or reasoning_effort.
    body, _, _ = B.build_body("m", "p", {"temperature": 0.7}, 100, gen, [])
    if body["temperature"] != 0.7:
        fails.append("a provider's explicit extra_body must override the language default")

    for f in fails:
        print("FAIL generation: %s" % f)
    if not fails:
        print("ok   generation      parameters sent explicitly, declared-unsupported ones dropped")
    return fails


# --- the one door ----------------------------------------------------------------------------------
# Every script that can put a key in a header. throughput.py was missing from this list for a day,
# which is exactly how a raw urlopen gets back in: not by anyone deciding to, but by a new file nobody
# added to the list.
KEY_CARRYING = ("benchmark.py", "probe_alive.py", "judge.py", "measure_limits.py", "throughput.py")

# Names that open a connection without going through http_safe. A call to any of these in a
# key-carrying file is a second door, whatever module it was imported from and whatever alias it has.
BYPASS = {"urlopen", "build_opener", "install_opener", "HTTPConnection", "HTTPSConnection"}


def raw_openers(source):
    """Every call to a bypass name and every import of one, found with the parser rather than with a
    substring - so `from urllib.request import urlopen` followed by `urlopen(req)`, or
    `import urllib.request as u` then `u.urlopen(req)`, are seen for what they are. The first version
    of this test looked for the literal text "urllib.request.urlopen(" and nothing else."""
    hits = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.ImportFrom):
            for alias in node.names:
                if alias.name in BYPASS:
                    hits.append("line %d: from %s import %s" % (node.lineno, node.module, alias.name))
        elif isinstance(node, ast.Call):
            f = node.func
            name = f.id if isinstance(f, ast.Name) else f.attr if isinstance(f, ast.Attribute) else None
            if name in BYPASS:
                hits.append("line %d: %s(" % (node.lineno, name))
    return hits


# The detector is itself calibrated in both directions: each of these must be caught, and the clean
# shape must not be. A detector that has never been watched catching anything is a comment.
PLANTED_OPENERS = [
    ("the dotted call", "import urllib.request\nurllib.request.urlopen(req)\n"),
    ("the bare import", "from urllib.request import urlopen\n"),
    ("the bare call after an import", "from urllib.request import urlopen\nurlopen(req)\n"),
    ("an aliased module", "import urllib.request as u\nu.urlopen(req)\n"),
    ("an aliased name", "from urllib.request import urlopen as fetch\n"),
    ("a private opener", "import urllib.request\nOPENER = urllib.request.build_opener()\n"),
    ("a raw https connection", "import http.client\nc = http.client.HTTPSConnection('x')\n"),
]
CLEAN_OPENER = "from http_safe import open_url\nwith open_url(req, 30) as f:\n    f.read()\n"


def redirect_cases():
    """The cross-origin redirects must raise, the same-origin ones must be allowed.

    Both directions, because a handler that refuses everything breaks every provider that redirects
    /v1/chat/completions to a versioned path, and a handler that allows everything hands the key over.
    """
    from http_safe import NoCrossHostRedirect
    import urllib.error
    import urllib.request

    h = NoCrossHostRedirect()
    out = []

    def req():
        # A real Request, not a stand-in: the parent handler reads half a dozen attributes off it and a
        # fake that satisfies only the ones we thought of would test our fake, not the handler.
        return urllib.request.Request("https://api.groq.com/openai/v1/chat/completions",
                                      data=b"{}", headers={"Authorization": "Bearer x"})

    def refused(label, newurl):
        try:
            h.redirect_request(req(), None, 302, "Found", {}, newurl)
            out.append((label, False, "it was FOLLOWED - the key would have left"))
        except urllib.error.URLError:
            out.append((label, True, ""))
        except Exception as e:
            out.append((label, False, "raised %s instead of URLError" % type(e).__name__))

    def allowed(label, newurl):
        try:
            r = h.redirect_request(req(), None, 302, "Found", {}, newurl)
            out.append((label, r is not None, "returned None"))
        except Exception as e:
            out.append((label, False, "raised %s" % type(e).__name__))

    refused("cross-host redirect refused", "https://evil.example/steal")
    refused("same host, https to http refused: the key would travel in cleartext",
            "http://api.groq.com/openai/v1/chat/completions")
    refused("same host, different port refused: another listener is another party",
            "https://api.groq.com:8443/openai/v1/chat/completions")
    refused("same host, a port that does not parse, refused rather than guessed",
            "https://api.groq.com:notaport/openai/v1/chat/completions")
    allowed("same-host redirect still allowed", "https://api.groq.com/openai/v1/chat/completions/")
    allowed("same host with the default port written out is the same origin",
            "https://api.groq.com:443/openai/v1/chat/completions/")
    allowed("host case does not make a new origin", "https://API.GROQ.COM/openai/v1/chat/completions/")

    # The detector, calibrated.
    for label, snippet in PLANTED_OPENERS:
        hits = raw_openers(snippet)
        out.append(("opener detector catches %s" % label, bool(hits), "not detected"))
    out.append(("opener detector admits open_url", not raw_openers(CLEAN_OPENER), "false alarm"))

    # And nobody may quietly go back to the unprotected call.
    for name in KEY_CARRYING:
        src = (Path(__file__).resolve().parent / name).read_text(encoding="utf-8")
        hits = raw_openers(src)
        out.append(("%s opens nothing around http_safe" % name, not hits,
                    "; ".join(hits) + " - use open_url from http_safe" if hits else ""))
    return out


def main():
    failures = []
    for probe, lang, text, should_pass, why in CASES:
        spec = lang["probes"][probe]
        got, note = B.check(probe, spec, text, lang)
        mark = "ok  " if got == should_pass else "FAIL"
        if got != should_pass:
            failures.append((probe, lang["code"], why, should_pass, got, note))
        print("%s %s/%s  expected %-5s got %-5s  %s"
              % (mark, lang["code"], probe, should_pass, got, why))

    print()
    for f in check_generation():
        # 6 fields, like every other failure, so the report below can print them. It used to append a
        # 4-tuple into a list unpacked as 6, which meant the FIRST generation failure crashed the
        # reporter instead of reporting - a test that breaks when it finds something.
        failures.append(("build_body", "generation", f, "-", "-", ""))

    extra = []
    print("redirect and opener discipline:")
    redirects = redirect_cases()
    for label, ok, why in redirects:
        print("  %-4s %s%s" % ("ok" if ok else "FAIL", label,
                               "  -> " + why if (why and not ok) else ""))
        if not ok:
            extra.append(("http_safe", "opener", label, "protected", "unprotected", why))
    failures += extra

    total = len(CASES) + 1 + len(redirects)
    print()
    print("%d cases, %d failures" % (total, len(failures)))
    for probe, code, why, want, got, note in failures:
        print("  %s/%s expected %s, got %s (%s) - %s" % (code, probe, want, got, note, why))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
