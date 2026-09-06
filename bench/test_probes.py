#!/usr/bin/env python3
"""Unit tests for the probe checkers. No network, no keys, no API calls.

Every one of these cases is a real answer shape a free model returned during our runs. Two of them cost
us a wrong scoreboard before they were pinned here: "14400, 81600" (a list read as one number) and
"14400,81600" (a list separator read as a thousands separator). A checker that silently misreads either
one rewrites the whole ranking, so both directions are tested: correct answers must pass, wrong answers
must fail.

    python bench/test_probes.py
"""
import json, sys
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
    failures += [("generation", "build_body", f, "") for f in check_generation()]

    print("\n%d cases, %d failures" % (len(CASES) + 1, len(failures)))
    for probe, code, why, want, got, note in failures:
        print("  %s/%s expected %s, got %s (%s) - %s" % (code, probe, want, got, note, why))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
