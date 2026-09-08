#!/usr/bin/env python3
"""Refuse a pull request that contributes a measurement, or rewrites where a key goes. Exit 0 clean,
1 refused (every message names the file and the rule), 2 the gate could not run.

    python bench/gate_pr.py                                      # origin/main...HEAD, run from the repo root
    python bench/gate_pr.py --base <ref> --head <ref>            # any two commits; base...head is the pull request
    python bench/gate_pr.py --base <ref> --title "retire: x"     # a retirement, rule 3
    python bench/gate_pr.py --files-from-dirs BASE_DIR HEAD_DIR  # two trees, no git: what the test drives
    python bench/gate_pr.py --list-walls                         # the files and the rule on each

MEASUREMENTS ARE MADE, NEVER CONTRIBUTED. Every other gate in this repo reads the CONTENT of a file and
asks whether a row could be true: a radar row with a past date and a 5xx, a drawn row inside the meter's
own bounds, a limit under its ceiling. A content rule cannot tell a row the meter wrote from a row a
contributor typed to look like one, and each of those rules was shown to admit a planted row with every
CI step green: fourteen back-dated 500s buried a live #1, one drawn row at the meter's bounds lifted the
headline by 46%, a rewritten reliability.json passed every step, and two registry lines swapped alongside
two URLs sent every runner's key to the other host. This gate does not read rows. It reads the DIFF, and
the question it asks is structural: is this a file a pull request may write at all?

  1. MEASUREMENT FILES are written only by the meters on the machine that holds the keys (the radar, the
     burst meter, the draw, the benchmark) and by the scheduled daily job. A pull request that adds,
     changes, renames or deletes any line in one of them is refused, whatever the line says. They reach
     main by push from the machine that made them, never through a pull request.
  2. ADDITIONS-ONLY FILES decide where a key goes. A pull request may ADD an entry to
     bench/key_bindings.json, to bench/providers.json and to the host maps in bench/gate_contributions.py
     (ALLOWED_HOSTS, KNOWN_SIGNUP_HOSTS, KNOWN_TERMS_HOSTS); it may not change or remove one that exists
     on the base branch. That is what turns the key registry from a review hint into a wall: a URL swap
     plus a registry swap in one pull request changes two existing lines, and two existing lines changed
     is a refusal before anyone reads what they say. The host maps must stay literals that this gate can
     read without importing anything: a map that is assigned twice, augmented, mutated by a method call
     or built from an expression is refused as a change to every entry in it.
  3. RETIRING a provider is the one legitimate removal, and it is a separate pull request whose title
     starts with `retire:`. Under that title an existing entry may be REMOVED from the additions-only
     files; it still may not be changed, and rule 1 still holds.

Everything else is a normal change, reviewed by a person and by the other gates: bench/limits.json,
bench/privacy.json, the generator, the gates, the tests, the pages, and the generator's own outputs
(README.md, RESULTS.md, ALL-ENDPOINTS.md, LIMITS.md, GRAVEYARD.md, data/ranking.json, data/ranking.csv,
data/capacity.json, data/viability.json), which CI regenerates and diffs anyway.

The diff is `git diff --name-status --no-renames base...head`: three dots, so it is what the pull request
adds on top of the merge base and not what main did meanwhile (the radar pushing to main while a pull
request is open must not turn the pull request red). Renames are switched off, so a moved measurement
file shows as a deletion plus an addition and is refused as both. File contents come from
`git show ref:path`. Every child process is a list of arguments, never a shell string, and nothing here
is imported from the repo it checks: CI runs the copy of this file from the base branch, so a pull
request cannot loosen the wall it is being checked against.
"""
import argparse
import ast
import json
import subprocess
import sys
from pathlib import Path

# ---------------------------------------------------------------------------------------- the walls

# Rule 1. Any status on any of these paths is a refusal. The comment says which program writes the file.
MEASUREMENT_FILES = (
    "data/uptime.jsonl",             # the daily liveness radar, bench/probe_alive.py
    "data/uptime-superseded.jsonl",  # radar rows the fourteen-day rule archived, bench/gate_viability.py
    "data/throughput.jsonl",         # the 30-second burst meter, bench/throughput.py
    "data/drawn.jsonl",              # the 60-minute draw, bench/draw_day.py
    "data/reliability.json",         # recomputed from results/ by the daily job, bench/reliability.py
    "data/scores.json",              # imported scores, replaced only through bench/gate_drift.py --apply
    "data/scores-drift.jsonl",       # the drift gate's own log of refusals
    "data/catalog.json",             # the catalogues the daily job re-reads, bench/refresh_catalog.py
)
MEASUREMENT_DIRS = ("results/",)     # every archived benchmark run: raw.json and its companions

# Rule 2. JSON files where every entry that exists on the base branch must be present and unchanged.
# path -> (the key holding the entries, what one entry is called in a message)
ADD_ONLY_JSON = {
    "bench/key_bindings.json": ("bindings", "key variable"),
    "bench/providers.json": ("providers", "provider"),
}
# Rule 2, the host maps: literals in one Python file, read with ast, never imported.
HOST_MAPS_FILE = "bench/gate_contributions.py"
HOST_MAPS = ("ALLOWED_HOSTS", "KNOWN_SIGNUP_HOSTS", "KNOWN_TERMS_HOSTS")
_MUTATORS = {"add", "remove", "discard", "pop", "clear", "update", "setdefault", "difference_update",
             "intersection_update", "symmetric_difference_update", "popitem"}

# Rule 3.
RETIRE_PREFIX = "retire:"

RULE_1 = "rule 1, measurements are made, never contributed"
RULE_2 = "rule 2, additions only"
RULE_3 = "rule 3, a removal needs a `retire:` title"


def is_measurement(path):
    return path in MEASUREMENT_FILES or any(path.startswith(d) for d in MEASUREMENT_DIRS)


def is_retirement(title):
    return bool(title) and title.strip().lower().startswith(RETIRE_PREFIX)


# ------------------------------------------------------------------------------- the two sides

class GitSides:
    """base...head in a git repository. Contents come from `git show ref:path`."""

    def __init__(self, root, base, head):
        self.root, self.base, self.head = Path(root), base, head

    def _git(self, *args):
        cmd = ["git", "-C", str(self.root)] + list(args)
        try:
            r = subprocess.run(cmd, capture_output=True, timeout=300)
        except (OSError, subprocess.TimeoutExpired) as e:
            raise RuntimeError("git could not run: %s" % e)
        return r.returncode, r.stdout, r.stderr.decode("utf-8", errors="replace").strip()

    def describe(self):
        return "%s...%s" % (self.base, self.head)

    def changes(self):
        for ref in (self.base, self.head):
            rc, _, err = self._git("rev-parse", "--verify", "--quiet", ref + "^{commit}")
            if rc != 0:
                raise RuntimeError("cannot resolve %r as a commit (%s). In CI this needs fetch-depth: 0; "
                                   "locally it needs the base branch fetched." % (ref, err or "no such ref"))
        rc, out, err = self._git("diff", "--name-status", "--no-renames", "-z",
                                 "%s...%s" % (self.base, self.head))
        if rc != 0:
            raise RuntimeError("git diff %s failed: %s" % (self.describe(), err))
        parts = out.decode("utf-8", errors="replace").split("\0")
        changes, i = [], 0
        while i + 1 < len(parts):
            status, path = parts[i], parts[i + 1]
            if status == "":
                break
            changes.append((status[:1], path))
            i += 2
        return changes

    def read(self, side, path):
        ref = self.base if side == "base" else self.head
        rc, out, err = self._git("show", "%s:%s" % (ref, path))
        if rc != 0:
            if "does not exist" in err or "exists on disk, but not in" in err or "bad object" in err:
                return None
            raise RuntimeError("git show %s:%s failed: %s" % (ref, path, err))
        return out


class DirSides:
    """Two directory trees, no git: base and head as they would be checked out."""

    SKIP = {".git", "__pycache__"}

    def __init__(self, base_dir, head_dir):
        self.base, self.head = Path(base_dir), Path(head_dir)
        for d in (self.base, self.head):
            if not d.is_dir():
                raise RuntimeError("%s is not a directory" % d)

    def describe(self):
        return "%s -> %s" % (self.base, self.head)

    def _files(self, root):
        out = {}
        for p in root.rglob("*"):
            if not p.is_file():
                continue
            rel = p.relative_to(root)
            if any(part in self.SKIP for part in rel.parts):
                continue
            out[rel.as_posix()] = p
        return out

    def changes(self):
        b, h = self._files(self.base), self._files(self.head)
        changes = []
        for path in sorted(set(b) | set(h)):
            if path not in h:
                changes.append(("D", path))
            elif path not in b:
                changes.append(("A", path))
            elif b[path].read_bytes() != h[path].read_bytes():
                changes.append(("M", path))
        return changes

    def read(self, side, path):
        p = (self.base if side == "base" else self.head) / path
        return p.read_bytes() if p.is_file() else None


# ------------------------------------------------------------------------------------ the rules

class Refused(Exception):
    """A property of the pull request: exit 1."""


class CannotRun(Exception):
    """A property of the base branch or the machine: exit 2."""


def _entries_json(path, raw, side):
    """The entries of an additions-only JSON file as {name: block}. None when the file is absent."""
    if raw is None:
        return None
    key, noun = ADD_ONLY_JSON[path]
    err = Refused if side == "head" else CannotRun
    try:
        data = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as e:
        raise err("%s on the %s side cannot be parsed as JSON (%s)" % (path, side, e))
    entries = data.get(key) if isinstance(data, dict) else None
    if isinstance(entries, dict):
        return dict(entries)
    if isinstance(entries, list):
        out = {}
        for i, block in enumerate(entries):
            name = block.get("name") if isinstance(block, dict) else None
            if not isinstance(name, str) or not name:
                raise err("%s on the %s side: %s #%d has no name" % (path, side, noun, i + 1))
            if name in out:
                raise err("%s on the %s side: %s %r appears twice" % (path, side, noun, name))
            out[name] = block
        return out
    raise err("%s on the %s side has no %r list or map" % (path, side, key))


def _entries_of_map(name, value, side):
    """The entries of one host map: a set of hosts, or a set of (provider, host) pairs."""
    err = Refused if side == "head" else CannotRun
    strs = (str,)
    if name == "ALLOWED_HOSTS":
        if not isinstance(value, (set, frozenset, list, tuple)) or not all(isinstance(v, strs) for v in value):
            raise err("%s on the %s side is not a set of strings" % (name, side))
        return set(value)
    if not isinstance(value, dict):
        raise err("%s on the %s side is not a dict" % (name, side))
    out = set()
    for k, hosts in value.items():
        if not isinstance(k, strs) or not isinstance(hosts, (set, frozenset, list, tuple)) \
                or not all(isinstance(h, strs) for h in hosts):
            raise err("%s on the %s side: entry %r is not a name mapped to a set of strings" % (name, side, k))
        for h in hosts:
            out.add((k, h))
    return out


def host_map_literals(src, side):
    """{name: literal value} for the three host maps, read with ast. Each must be bound exactly once, at
    module level, to a literal, and never mutated by a method call or deleted anywhere in the file."""
    err = Refused if side == "head" else CannotRun
    try:
        tree = ast.parse(src)
    except SyntaxError as e:
        raise err("%s on the %s side does not parse: %s" % (HOST_MAPS_FILE, side, e))
    found = {}
    for node in tree.body:
        targets, value = [], None
        if isinstance(node, ast.Assign):
            targets, value = node.targets, node.value
        elif isinstance(node, ast.AnnAssign):
            targets, value = [node.target], node.value
        for t in targets:
            if isinstance(t, ast.Name) and t.id in HOST_MAPS:
                if t.id in found:
                    raise err("%s is assigned twice at module level on the %s side; a map bound twice is "
                              "a change to every entry in it" % (t.id, side))
                try:
                    found[t.id] = ast.literal_eval(value)
                except (ValueError, TypeError, SyntaxError):
                    raise err("%s on the %s side is not a literal set or dict; the gate reads the literal "
                              "and refuses a map built from an expression" % (t.id, side))
    for name in HOST_MAPS:
        if name not in found:
            raise err("%s has no module-level literal on the %s side" % (name, side))
    bindings = {name: 0 for name in HOST_MAPS}
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id in HOST_MAPS:
            if isinstance(node.ctx, ast.Del):
                raise err("%s is deleted on the %s side" % (node.id, side))
            if isinstance(node.ctx, ast.Store):
                bindings[node.id] += 1
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) \
                and isinstance(node.func.value, ast.Name) and node.func.value.id in HOST_MAPS \
                and node.func.attr in _MUTATORS:
            raise err("%s.%s() is called on the %s side; the map must stay the literal a reviewer reads"
                      % (node.func.value.id, node.func.attr, side))
    for name, n in bindings.items():
        if n != 1:
            raise err("%s is bound %d times on the %s side (augmented, rebound in a function, or used as a "
                      "loop target); it must be bound once, to the literal" % (name, n, side))
    return found


def check_add_only(path, status, sides, retire):
    """Rule 2 and rule 3 on one additions-only file. Returns (problems, notes)."""
    problems, notes = [], []
    if status == "D":
        problems.append((path, RULE_2, "the file was deleted; every entry it held is gone"))
        return problems, notes
    if status not in ("A", "M", "T"):
        problems.append((path, RULE_2, "unexpected status %r" % status))
        return problems, notes
    base_raw = sides.read("base", path) if status != "A" else None
    head_raw = sides.read("head", path)
    if head_raw is None:
        problems.append((path, RULE_2, "the file is missing on the head side"))
        return problems, notes
    try:
        _compare_entries(path, base_raw, head_raw, retire, problems, notes)
    except Refused as e:
        # a head side the gate cannot read is a change to every entry in the file
        problems.append((path, RULE_2, str(e)))
    return problems, notes


def _compare_entries(path, base_raw, head_raw, retire, problems, notes):
    if path in ADD_ONLY_JSON:
        noun = ADD_ONLY_JSON[path][1]
        base = _entries_json(path, base_raw, "base") or {}
        head = _entries_json(path, head_raw, "head")
        for name in sorted(base):
            if name not in head:
                if retire:
                    notes.append("%s: %s %r removed under a retire: title" % (path, noun, name))
                else:
                    problems.append((path, RULE_3, "%s %r exists on the base branch and is removed here"
                                     % (noun, name)))
            elif head[name] != base[name]:
                problems.append((path, RULE_2, "%s %r exists on the base branch and is changed here; an "
                                 "existing %s may only be added next to, never edited" % (noun, name, noun)))
        return
    base_maps = host_map_literals(base_raw.decode("utf-8", errors="replace"), "base") if base_raw else None
    head_maps = host_map_literals(head_raw.decode("utf-8", errors="replace"), "head")
    if base_maps is None:
        return
    for name in HOST_MAPS:
        b = _entries_of_map(name, base_maps[name], "base")
        h = _entries_of_map(name, head_maps[name], "head")
        for entry in sorted(b):
            if entry in h:
                continue
            shown = entry if isinstance(entry, str) else "%s -> %s" % entry
            if retire:
                notes.append("%s: %s entry %s removed under a retire: title" % (path, name, shown))
            else:
                problems.append((path, RULE_3, "%s entry %s exists on the base branch and is missing here; "
                                 "a host may be added, never removed or replaced" % (name, shown)))
    return


def check(sides, title=""):
    """Every rule on every changed path. Returns (changes, problems, notes)."""
    retire = is_retirement(title)
    changes = sides.changes()
    problems, notes = [], []
    for status, path in changes:
        if is_measurement(path):
            problems.append((path, RULE_1, "status %s. This file is written only by the meters on the machine "
                             "that holds the keys and by the daily job; a pull request may not add, change, "
                             "rename or delete a line in it, whatever the line says" % status))
        elif path in ADD_ONLY_JSON or path == HOST_MAPS_FILE:
            p, n = check_add_only(path, status, sides, retire)
            problems.extend(p)
            notes.extend(n)
    return changes, problems, notes


# ----------------------------------------------------------------------------------------- cli

def list_walls():
    print("rule 1, measurements are made, never contributed. Any change to these is refused:")
    for p in MEASUREMENT_FILES:
        print("  %s" % p)
    for d in MEASUREMENT_DIRS:
        print("  %s**" % d)
    print("rule 2, additions only. An existing entry may not change or disappear:")
    for p, (key, noun) in ADD_ONLY_JSON.items():
        print("  %s  (%r: one %s per entry)" % (p, key, noun))
    print("  %s  (%s)" % (HOST_MAPS_FILE, ", ".join(HOST_MAPS)))
    print("rule 3. A removal from a rule-2 file is admitted only when the title starts with %r; a change never."
          % RETIRE_PREFIX)


def main():
    ap = argparse.ArgumentParser(description="the structural wall on a pull request")
    ap.add_argument("--root", default=".", help="the repository (default: the current directory)")
    ap.add_argument("--base", default="origin/main", help="the branch the pull request targets")
    ap.add_argument("--head", default="HEAD", help="the pull request's commit")
    ap.add_argument("--title", default="", help="the pull request title; `retire:` admits removals (rule 3)")
    ap.add_argument("--files-from-dirs", nargs=2, metavar=("BASE_DIR", "HEAD_DIR"),
                    help="compare two directory trees instead of two git refs")
    ap.add_argument("--list-walls", action="store_true", help="print the files and the rule on each, then exit")
    a = ap.parse_args()

    if a.list_walls:
        list_walls()
        return 0
    try:
        sides = DirSides(*a.files_from_dirs) if a.files_from_dirs else GitSides(a.root, a.base, a.head)
        changes, problems, notes = check(sides, a.title)
    except Refused as e:
        print("REFUSED: %s" % e)
        return 1
    except (CannotRun, RuntimeError) as e:
        print("gate_pr could not run: %s" % e)
        return 2

    print("gate_pr: %s, %d changed path(s)%s" % (sides.describe(), len(changes),
                                                 ", retire: title" if is_retirement(a.title) else ""))
    for n in notes:
        print("  note  %s" % n)
    if problems:
        for path, rule, why in problems:
            print("  REFUSED %s: %s. %s" % (path, rule, why))
        print("\n%d REFUSAL(S). Measurements are made, never contributed, and an existing key line is never "
              "edited: see CONTRIBUTING.md." % len(problems))
        return 1
    print("CLEAN - no measurement file touched, and every entry the base branch has in %s and the host maps "
          "is still there, unchanged." % ", ".join(ADD_ONLY_JSON))
    return 0


if __name__ == "__main__":
    sys.exit(main())
