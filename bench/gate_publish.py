#!/usr/bin/env python3
"""Refuse to publish if anything in the repo leaks a key, an account state, or a private detail.

Run before every push. Exit 0 clean, 1 something must be fixed, 2 the gate could not run, and the
last one is not a pass either.

    python bench/gate_publish.py .                             # the working tree; this is what CI runs
    python bench/gate_publish.py --history .                   # every commit git still knows about
    python bench/gate_publish.py --fingerprint .gate-private   # fingerprints of the local list, for a local file

This exists because the raw output of a benchmark is exactly the kind of file nobody reads before
committing: it echoes your prompts back, and providers echo your account state back inside error
bodies. Our own first run put a real project name and its price into the results 31 times.

DESIGN RULES, each of them written after the gate failed a test that pinned it:

1. **An allow-pattern removes a substring, never a line.** The obvious implementation, "if the line
   matches something allowed, skip the line", means a key sitting next to `${HOME}`, or next to our
   own repo link, is invisible. The allowed substrings are blanked out and whatever remains is still
   checked. And the blanked substring is exactly the allowed thing, not "the allowed thing and whatever
   is glued to it": the first version of the own-repo pattern also erased a key written as a path
   segment of the link.
2. **Content decides what is binary, never the extension.** A text file named `notes.png` is scanned.
   A UTF-16 file (the default of a PowerShell redirect) is decoded, not skipped for "having NUL
   bytes", and a log with one stray NUL is still a log. A file that is genuinely binary is not skipped
   either: its printable ASCII runs of twenty characters or more are pulled out and scanned with the
   key rules, because a PNG carries text chunks and a PDF carries metadata, and a key pasted into
   either ships as well as one in a README. A zip or gzip file is recognised by its magic bytes,
   whatever its name: its printable strings are scanned like any binary AND every member is inflated
   and scanned as a file of its own, because a deflated entry hides its text from a string scan. The
   extension denylist only decides whether the binary itself is a finding: an image is expected, a
   blob with a text name is not, and an archive under an image's name is not either.
3. **Self-exemption is by resolved path, never by filename, and it is partial.** The gate necessarily
   contains the patterns it hunts for, and so does its test. Comparing names means any file called
   `gate_publish.py`, anywhere in the tree, exempts itself. And the exemption covers only the rules
   these two files must trip by construction: the phrase rules (their regexes name the phrases), the
   fingerprints (the test carries the example names) and the entropy rules (the test carries random
   fixtures). The KEY rules stay on for them, in the tree and in the history, so a live key pasted
   into either file is caught like anywhere else. Their fixtures are therefore assembled from pieces
   the gate does not glue back together (`%` formatting, `join`), never written whole. The same
   partial exemption covers the local private list, which must never hold a key-shaped line, and
   which is refused outright if git tracks it, whatever .gitignore says.
4. **Skip only what git ignores, plus the repo's own `.git`.** A folder named `venv` or `node_modules`
   that git tracks is a folder git will publish, so it is scanned like any other.
5. **Names are content.** Every file and directory name goes through the same rules and the same
   private list as the lines inside it. A private project name in a path ships just as well.
6. **The private list never ships, in any form.** The names live in `.gate-private`, one per line,
   git-ignored, read at runtime when present, and their fingerprints are computed on the spot: the
   first 16 hex characters of sha256 over each name normalised (lowercased, lookalike letters from
   other scripts folded to Latin, everything that is not a letter or a digit removed). A dotted name
   such as `plan.json` is fingerprinted twice, whole and as its bare stem, so the word alone is caught
   too. A truncated hash is not a secret kept: it confirms a guess for anyone holding a candidate
   list, and a short name falls to an offline search, so no fingerprint file is published either. The
   rule therefore runs where `.gate-private` is, which is the machine that pushes; CI runs the key and
   phrase rules and says on its summary line that the private-name rule was off.
   Every scanned line and path is folded the same way, cut into alphanumeric runs, and every
   window of one to four consecutive runs is hashed and looked up, so the name is caught whether it
   appears alone, hyphenated, dotted, with a space in it, or spelled with a Cyrillic or Greek letter
   in place of a Latin one. CI catches the names without knowing them. Known limitation: a name glued
   into a longer alphanumeric run (`nameV2`, `thename`) is a different run and is not caught; the
   fingerprint scheme cannot do substrings without publishing a searchable oracle for the names.
   This hides them from a reader, not from a dictionary attack on the hashes; that is a property of
   any fingerprint scheme and the reason the plaintext stays local.
7. **Encodings are decoded before matching.** `%XX` escapes are decoded until none is left, so a
   doubled encoding is no hiding place; HTML entities (`&#95;` for an underscore), `\\uXXXX` and
   `\\xXX` escapes are decoded; zero-width and direction-control characters are stripped; adjacent
   string literals are glued back together whether joined with `+`, with `.`, or by plain adjacency
   across a line break inside parentheses; a base64 value of 32 characters or more after an
   assignment, after `echo` or `printf`, or inside a `data:` URI is decoded and scanned as text; and
   a key hard-wrapped over two lines is read glued, the last token of a line joined to the first token
   of the next and the key rules run over the join. A key that is only invisible to a regex is still a
   key.
8. **Every rule has a name and the test asserts the name.** "Exit 1 on the right file" is satisfied by
   any rule firing for any reason; a case that names its rule proves the rule it was written for.
9. **A dotted quad is a machine, and so is a global IPv6 address.** A public address in a results
   file is the server the run came from or the client it went to; a provider is named by its
   hostname. The private, loopback, link-local, shared, multicast, reserved and documentation ranges
   of both families are clean, because those are the addresses documentation is written with.
10. **Account state is a class, not a list of yesterday's sentences.** The first-person rule matches
   the shapes of the class: first person plus a noun that belongs to the caller (our own call, our own
   tooling, our own measured header, my account, our quota); a key described as the thing that answered
   (the key returned 402); a grant, credit, dollar or balance next to a verb of consumption (consumed,
   used up, spent); and any echo of a `remaining` rate-limit header with a number after it, in a JSON
   field, with a colon, with a space or bare, plus a `limit` header dumped on a line of its own. What
   it admits, on purpose, is provenance that describes the ENDPOINT: "rate-limit response headers on a
   free-trial key reported x-ratelimit-limit-requests-day 2400", "the endpoint answered HTTP 429 on
   2026-09-06", a header NAME in prose with no number, and a keyless endpoint's anonymous bucket
   read in a sentence. The line between the two is the subject of the sentence: the caller or the
   provider. Every one of those admissions is a MUST_PASS case, next to the shapes it must refuse.

`bench/test_gate.py` pins every one of those in both directions. Run it after touching this file.
"""
import argparse, base64, binascii, collections, hashlib, html, io, ipaddress, json, math, os, re
import subprocess, sys, unicodedata, urllib.parse, zipfile, zlib
from pathlib import Path

MAX_BYTES = 5 * 1024 * 1024
PRIVATE_LIST = ".gate-private"                       # local, git-ignored, one name per line
FINGERPRINTS = Path(__file__).resolve().parent / "private_fingerprints.json"
WINDOW = 4                                            # consecutive alphanumeric runs joined for a lookup
MIN_STRING = 20                                       # shortest printable run pulled out of a binary file
MAX_ARCHIVE_DEPTH = 2                                 # an archive inside an archive is opened; one deeper is a finding

# Rule 2: what to expect when a file turns out to be genuinely binary. Anything else that is binary is
# a finding, because a blob nobody can read is not a blob known to be clean. Both kinds still get their
# printable strings scanned with the key rules.
BINARY_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".bmp", ".tiff", ".pdf", ".zip",
                   ".gz", ".tar", ".xz", ".bz2", ".zst", ".7z", ".rar", ".woff", ".woff2", ".ttf",
                   ".otf", ".eot", ".mp4", ".mov", ".avi", ".mp3", ".wav", ".flac", ".ogg", ".pyc",
                   ".pyd", ".so", ".dll", ".dylib", ".exe", ".bin", ".o", ".a", ".lib", ".wasm",
                   ".jar", ".class", ".parquet", ".db", ".sqlite", ".npz", ".pkl", ".whl"}
# Rule 2, archives: the names under which a zip or a gzip stream is expected. A PK or gzip signature
# under any other name is a container pretending to be something else, and that is a finding by itself.
ARCHIVE_SUFFIXES = {".zip", ".jar", ".war", ".ear", ".whl", ".egg", ".npz", ".apk", ".ipa", ".xpi", ".vsix",
                    ".nupkg", ".docx", ".xlsx", ".pptx", ".odt", ".ods", ".odp", ".epub", ".kmz", ".gz", ".tgz"}
_ZIP_MAGICS = (b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08")
_GZIP_MAGIC = b"\x1f\x8b"

# --------------------------------------------------------------------------------------------------
# The rules. (name, pattern, why it must not ship). Names are part of the contract: test_gate.py
# asserts them, and a renamed rule is a test that stops meaning what it says.

_SECRET_WORD = r"(?:api[_\-]?key|apikey|(?<![A-Za-z])key|access[_\-]?token|token|secret|passw(?:or)?d|auth)"
_VALUE = r"[A-Za-z0-9_\-./+=]"

# Rule 10, the pieces of the account-state class. Kept as named pieces so the rule reads as what it
# is: first person plus a noun of the caller's; a key that answered; a grant next to a verb of
# consumption; a remaining-header echo in any dress.
_ACCOUNT_NOUN = r"(?:credit|grant|balance|dollar|allowance)s?"
# Past and perfect forms only: "credits that run out" describes a KIND of free tier, "the credit had
# run out" describes ours.
_SPENT_VERB = r"(?:used\s+up|consumed|spent|exhausted|drained|depleted|burned\s+through|ran\s+out|(?:ha[sd]|have)\s+run\s+out)"
_FIRST_PERSON = (
    r"our\s+(?:own\s+)?keys?|our\s+(?:own\s+)?accounts?|my\s+keys?|my\s+accounts?|our\s+own\s+agents?|agent\s+tooling"
    r"|our\s+(?:own\s+)?tooling|our\s+own\s+calls?|our\s+own\s+(?:measured\s+)?headers?"
    r"|our\s+own\s+measured\s+(?:readings?|values?|figures?)|(?:my|our)\s+(?:quota|credits|balance|allowance)s?"
    r"|this\s+account|to\s+this\s+key|no\s+balance|low\s+balance|is\s+spent"
    r"|(?:the|this|that|our|my)\s+keys?\s+(?:returned|answered|got|received|came\s+back)"
    r"|(?:the\s+)?accounts?\s+(?:was|were|has\s+been|have\s+been|got)\s+(?:suspended|banned|locked|flagged|closed)"
    r"|without\s+a\s+separate\s+balance|credits?\s+remaining|remaining\s+credits?"
    r"|ran\s+out\s+of\s+(?:credits?|quota|balance|allowance|money)"
    r"|quota\s+exceeded|refused\s+this\s+client|rejected\s+the\s+credential|with\s+a\s+valid\s+new\s+key"
    r"|" + _ACCOUNT_NOUN + r"\b[^.;:\n]{0,40}?\b" + _SPENT_VERB + r"|" + _SPENT_VERB + r"\b[^.;:\n]{0,40}?\b" + _ACCOUNT_NOUN +
    r"|cheia\s+noastr[aă]|contul\s+nostru|creditul\s+nostru|soldul\s+nostru|cheia\s+mea|contul\s+meu"
)
# A remaining-header with a number after it is what is left on OUR account, whatever the punctuation:
# `"x-ratelimit-remaining": "4"`, `X-RateLimit-Remaining: 4984208`, `x-ratelimit-remaining 4`. The
# lookbehinds admit the same header inside a sentence about the endpoint ("answered 429 with
# x-ratelimit-remaining-minute 0"): a header echo starts a line, a field or a list, prose puts a
# word in front of it. A limit-header is the ceiling, admitted in prose and in a bare JSON field, and
# refused when dumped raw: `x-ratelimit-limit-<suffix>: <n>` anywhere, or `x-ratelimit-limit... <n>`
# standing alone on a line.
_HEADER_ECHO = (
    r"remaining_at|used_today|balance\s*[:=]\s*\$?\s*\d"
    r"|(?<![A-Za-z0-9] )(?<![A-Za-z0-9\-])(?:x-)?rate-?limit-remaining(?:-[a-z]+)*[\"']?\s*[:=]?\s*[\"']?\d"
    r"|x-ratelimit-limit-[a-z\-]*:\s*[\"']?\d"
    r"|^\s*(?:[-*]\s+)?x-ratelimit-limit(?:-[a-z]+)*\s+\d"
)

# The assistant-trace pieces, one granularity for every vendor: the tool as a credit ("generated by",
# "powered by"), the tool's product name bare in prose, and the model family with a verb of authorship.
# The addresses named are the ones a co-author trailer of these tools carries; google.com and
# github.com are too broad to be a trace on their own and fall to the private-email rule.
_TOOL = (r"(?:claude(?:\s+code)?|chatgpt|gpt-?\d[\w.\-]*|gpt|codex(?:\s+cli)?|(?:github\s+)?copilot"
         r"|cursor(?:\s+(?:agent|composer))?|gemini(?:\s+cli)?|grok|an?\s+(?:ai|llm|assistant|language\s+model))")
_PRODUCT = (r"(?:claude\s+code|codex\s+cli|gemini\s+cli|github\s+copilot|copilot\s+(?:cli|chat|agent|workspace)"
            r"|cursor\s+(?:agent|composer|ide))")
_MODEL = (r"(?:fable|opus|sonnet|haiku|claude|chatgpt|gpt-?\d[\w.\-]*|o[1-9](?:-(?:mini|pro))?|codex|copilot"
          r"|composer|cursor|gemini|grok)")
_CREDIT_VERB = r"(?:generated|made|written|built|created|authored|drafted|powered|assisted|reviewed)"
_AUTHOR_VERB = (r"(?:drafted|wrote|generated|helped|produced|reviewed|checked|fixed|suggested|proposed|rewrote"
                r"|summari[sz]ed|translated)")

RULES = [
    ("key: OpenAI or OpenRouter shape", r"\bsk-[A-Za-z0-9_\-]{20,}", "a live key"),
    ("key: Stripe shape", r"\b[sr]k_(?:live|test)_[A-Za-z0-9]{16,}", "a live key"),
    ("key: Groq shape", r"\bgsk_[A-Za-z0-9_\-]{20,}", "a live key"),
    ("key: NVIDIA shape", r"\bnvapi-[A-Za-z0-9_\-]{20,}", "a live key"),
    ("key: xAI shape", r"\bxai-[A-Za-z0-9_\-]{20,}", "a live key"),
    ("key: Google shape", r"\bAIza[A-Za-z0-9_\-]{30,}", "a live key"),
    ("key: Google OAuth token shape", r"\bya29\.[A-Za-z0-9_\-]{20,}",
     "a live access token, which is a credential for as long as it is valid"),
    ("key: GitHub shape", r"\bgh[pousr]_[A-Za-z0-9]{30,}|\bgithub_pat_[A-Za-z0-9_]{20,}", "a live key"),
    ("key: Hugging Face shape", r"\bhf_[A-Za-z0-9]{30,}", "a live key"),
    ("key: Cerebras shape", r"\bcsk-[A-Za-z0-9]{30,}", "a live key"),
    ("key: GitLab shape", r"\bglpat-[A-Za-z0-9_\-]{20,}", "a live key"),
    ("key: Slack shape", r"\bxox[abprs]-[A-Za-z0-9\-]{10,}|\bxapp-\d-[A-Za-z0-9\-]{10,}", "a live key"),
    ("key: AWS shape", r"\bAKIA[0-9A-Z]{16}\b", "a live key"),
    ("key: JWT shape", r"\beyJ[A-Za-z0-9_\-]{8,}\.[A-Za-z0-9_\-]{8,}\.[A-Za-z0-9_\-]{8,}",
     "a signed token, which is a credential for as long as it is valid"),
    ("key: id.secret shape", r"\b[0-9a-f]{32}\.[A-Za-z0-9]{16}\b", "a live key"),
    ("key: bare 64-plus hex", r"(?<![A-Za-z0-9])[0-9a-fA-F]{64,}(?![A-Za-z0-9])",
     "a hex string of 64 characters or more with nothing near it saying it is a hash: the raw shape of "
     "a key at several providers, at 64 and at 96"),
    ("Authorization header value",
     r"(?i)\bauthorization\b[\"'\]]*\s*[:=]\s*[\"']?\s*(?:bearer|basic|token|apikey|api-key)?\s*[\"']?\s*"
     + _VALUE + r"{20,}",
     "a live token, with or without the word Bearer in front of it"),
    ("Bearer token inline", r"(?i)\bbearer\s+[\"']?" + _VALUE + r"{20,}", "a live token"),
    # The plural form is admitted only when a list follows: `max_tokens: MAX_TOKENS_PER_CALL` is a
    # constant under a plural secret-word, and `"api_keys": ["..."]` is the leak.
    ("secret assigned to a variable",
     r"(?i)" + _SECRET_WORD + r"(?:[\"'\]]*\s*[:=]\s*|s[\"'\]]*\s*[:=]\s*\[\s*)[\"']?\s*(?P<value>" + _VALUE + r"{16,})",
     "a secret assigned to a variable; the name of the variable says what the value is"),
    ("secret in a JSON field",
     r"(?i)\"(?:key|token|secret|auth|authorization|password|passwd|api[_\-]?key|apikey|access[_\-]?token"
     r"|private[_\-]?key|client[_\-]?secret)(?:\"\s*:\s*|s\"\s*:\s*\[\s*)\"(?P<value>[^\"\s]{16,})\"",
     "a secret in a field whose name says what it is, alone or first in a list"),
    ("private key block", r"-----BEGIN [A-Z ]*PRIVATE KEY-----", "a private key"),
    ("account state, provider phrasing",
     r"(?i)your account balance|insufficient balance|account_balance|insufficient funds|insufficient_quota"
     r"|exceeded your current quota",
     "the billing state of the account behind the key, which is a fact about the caller and not about the provider"),
    ("account state, first person",
     r"(?i)\b(?:" + _FIRST_PERSON + r")\b|" + _HEADER_ECHO,
     "a sentence about the account behind the key, or an echo of its quota, which is a fact about the caller "
     "and not about the provider"),
    ("assistant trace",
     r"(?i)co-authored-by\s*:|@(?:anthropic|openai|cursor)\.com\b|@cursor\.sh\b"
     r"|\b" + _PRODUCT + r"\b|\bthe\s+user\s+(?:asked|said|requested|wants)\b"
     r"|\bgenerated\s+(?:by|with)\s*\["
     r"|\b" + _CREDIT_VERB + r"\s+(?:by|with|using)\s+" + _TOOL + r"\b"
     r"|\b" + _MODEL + r"(?:\s+\d[\d.]*)?(?:\s+(?:flash|pro|ultra|mini|max|lite|thinking))?\s+" + _AUTHOR_VERB + r"\b",
     "a trailer or a phrase left behind by a code-generation tool; the authorship here is ours"),
    ("Windows user path", r"(?i)\b[a-z]:(?:\\\\|\\|/)+users(?:\\\\|\\|/)+[^\\/\s\"',;)]+",
     "a path off someone's machine"),
    ("UNC user path",
     r"(?i)(?<![A-Za-z0-9\\])(?:\\\\){1,2}[a-z0-9._\-]+(?:(?:\\\\|\\)+[^\\/\s\"',;)]+)*?(?:\\\\|\\)+users(?:\\\\|\\)+[^\\/\s\"',;)]+"
     r"|(?<![A-Za-z0-9:/])//[a-z0-9._\-]+(?:/[^/\s\"',;)]+)*?/users/[^/\s\"',;)]+",
     "a path off someone's machine, addressed by the machine's name on the network"),
    ("Git Bash or WSL user path", r"(?i)(?<![A-Za-z0-9])/(?:mnt/|cygdrive/)?[a-z]/users/[^/\s\"',;)]+",
     "a path off someone's machine, in the form a Unix shell on Windows writes it"),
    ("macOS user path", r"(?<![A-Za-z0-9])/Users/[^/\s\"',;)]+", "a path off someone's machine"),
    ("Linux home path", r"(?<![A-Za-z0-9])/home/[A-Za-z0-9._\-]+", "a path off a server"),
    ("root home path", r"(?<![A-Za-z0-9])/root(?:/[^\s\"',;)]*|\b)", "a path off a server, as root"),
    ("slugified user path", r"\b[A-Za-z][_\-]{1,2}Users[_\-]{1,2}[A-Za-z0-9]+",
     "a path off someone's machine with the separators replaced, the way a tool names its scratch folders"),
    ("public IPv4 address", r"(?<![\d.])(?:\d{1,3}\.){3}\d{1,3}(?![\d.])",
     "an address that points at a machine someone runs; a provider is named by its hostname, so a dotted "
     "quad here is our server or our client"),
    ("public IPv6 address",
     r"(?<![A-Za-z0-9:.])(?:[0-9A-Fa-f]{0,4}:){2,7}[0-9A-Fa-f]{0,4}(?:(?:\d{1,3}\.){3}\d{1,3})?(?![A-Za-z0-9:]|\.[A-Za-z0-9])",
     "an address that points at a machine someone runs, in the other family; the documentation, loopback, "
     "link-local, unique-local, multicast and reserved blocks are clean"),
    ("credentials in a URL", r"(?i)\b[a-z][a-z0-9+.\-]*://[^/\s:@\"']+:[^/\s@\"']{3,}@[A-Za-z0-9.\-]+",
     "a password or token in the userinfo part of a URL"),
    ("private email",
     r"(?i)(?<![A-Za-z0-9._%+\-])[A-Za-z0-9._%+\-]+(?:@|\s*\[at\]\s*|\s*\(at\)\s*|\s*\{at\}\s*)[A-Za-z0-9\-]+"
     r"(?:(?:\.|\s*\[dot\]\s*|\s*\(dot\)\s*)[A-Za-z0-9\-]+)*(?:\.|\s*\[dot\]\s*|\s*\(dot\)\s*)[A-Za-z]{2,}\b",
     "a real address, obfuscated or not"),
    ("multi-key arithmetic",
     r"(?i)[x×*]\s*\d+\s*(?:keys|chei|accounts)\b|\b\d+\s*(?:keys|chei|accounts)\s*[x×*]"
     r"|\b\d+\s+(?:keys|chei|accounts)\b[^.\n]{0,40}?\b\d[\d,.]*\s*(?:/|per\s+)(?:min|minute|day|hour|h|s|sec|second)\b",
     "a rate limit multiplied across keys, which reads as quota evasion and is usually false anyway, "
     "because most limits apply per account or per organization"),
]
_COMPILED = [(name, re.compile(pattern), why) for name, pattern, why in RULES]

# Rule 3: the rules that stay ON for the gate, its test and the private list. Everything whose name
# starts with "key:" plus the four that catch a credential by its surroundings rather than its prefix.
_KEY_RULE_EXTRA = {"private key block", "credentials in a URL", "Authorization header value", "Bearer token inline"}


def is_key_rule(name):
    return name.startswith("key:") or name in _KEY_RULE_EXTRA


KEY_RULE_NAMES = [name for name, _, _ in RULES if is_key_rule(name)]

# A value that is obviously a placeholder is documentation, not a leak.
_PLACEHOLDER = re.compile(r"(?i)your|example|placeholder|change[_\-]?me|redacted|dummy|sample|insert"
                          r"|paste|replace|\.\.\.|<|>")
# A label under which a long hex string is a hash, not a key. Matched against the text BEFORE the
# assignment operator, so the label is the last word there: `sha256:`, `"digest":`, `image@sha256:`.
_HASH_LABEL = re.compile(r"(?i)(?:commit|sha\d*(?:sum)?|shasum|md5(?:sum)?|hash|digest|checksum|rev|revision|ref"
                         r"|oid|etag|integrity|fingerprints?)[\"'\]]*\s*$")
# A word that, anywhere in the sixty characters before a bare hex string, says it is a hash.
_HASH_WORD = re.compile(r"(?i)\b(?:sha-?\d*(?:sum)?|shasum|digest|hash(?:e[sd])?|checksums?|integrity|commit|fingerprints?"
                        r"|blake\w*|md5(?:sum)?|oid|etag|rev|revision)\b")
_HEX_AFTER_ASSIGNMENT = re.compile(r"[=:]\s*[\"']?\s*\b([0-9a-fA-F]{32,})\b")
_TOKEN_AFTER_ASSIGNMENT = re.compile(r"[=:]\s*[\"']?\s*\b([A-Za-z0-9_\-]{32,})\b")
# A base64 value in a position where a value goes: after an assignment, after `echo` or `printf`
# (the shell way of feeding `base64 -d`), inside a `data:` URI, or after a here-string.
_BASE64_AFTER_ASSIGNMENT = re.compile(
    r"(?:[=:]|\becho(?:\s+-[a-zA-Z]+)*\s|\bprintf\s+(?:[\"']%s[\"']\s+)?|base64,|<<<)"
    r"\s*[\"']?\s*(?<![A-Za-z0-9+/])([A-Za-z0-9+/]{32,}={0,2})(?![A-Za-z0-9+/=])")
_BASE64_STATISTICS_MIN = 48    # below this a base64 value is only decoded and read, never judged on its statistics
# A YAML line that is only a secret-shaped key and a colon, so the value is on the next line. Anchored
# to the start of the line on purpose: `if model_key:` in Python ends the same way and must not pull
# the next statement in as its "value".
_YAML_DANGLING = re.compile(r"(?i)^\s*-?\s*[\"']?[A-Za-z0-9_.\-]*" + _SECRET_WORD + r"[\"']?\s*:\s*[|>]?\s*$")
# A line that ends inside a parenthesised concatenation, and a line that continues one: the two are
# glued so a literal split over a line break is read as the one string the language makes of it.
_ENDS_WITH_LITERAL = re.compile(r"[\"'](?:\s*[+.\\])?\s*$")
_STARTS_WITH_LITERAL = re.compile(r"^\s*(?:[+.]\s*)?[\"']")
# A key hard-wrapped by an editor: the line ends in the head of a token and the next line starts with
# its tail. The two are joined and the KEY rules run over the join; nothing else is, because prose
# wraps too and a joined pair of words is not a secret.
_WRAP_TAIL = re.compile(r"([A-Za-z0-9_\-]{2,})\s*$")
_WRAP_HEAD = re.compile(r"^\s*([A-Za-z0-9_\-]{8,})")

COMPUTED_RULE_NAMES = ["high-entropy hex after assignment", "high-entropy string after assignment",
                       "base64 blob after assignment or echo", "private name", "private list out of sync",
                       "private list tracked by git", "binary blob with a text name",
                       "archive under another extension",
                       "file over %d MB not scanned" % (MAX_BYTES // 1024 // 1024), "unreadable"]
RULE_NAMES = [name for name, _, _ in RULES] + COMPUTED_RULE_NAMES

# Rule 1: these are BLANKED OUT of a line, then the rest of the line is still checked.
ALLOW = [
    re.compile(r"https://github\.com/i-voryStudio(?:/live-free-llm-apis)?(?![A-Za-z0-9_\-])"),  # our profile, and only that
    re.compile(r"[A-Za-z0-9._%+\-]+(?:@|\s*\[at\]\s*)(?:example\.[a-z]+|users\.noreply\.github\.com)"),  # placeholders
    re.compile(r"\bnoreply@github\.com|user@host|your@email"),
    re.compile(r"export [A-Z_]+=\.\.\."),                              # documenting the shape
    re.compile(r"\$\{?[A-Z_][A-Z0-9_]*\}?"),                           # shell variable references
    re.compile(r"<account state redacted>"),                           # already redacted, by design
]

# Zero-width, joiner, direction-control and variation characters: invisible in an editor, a wall to a
# regex. Written as escapes so they can be seen.
_ZERO_WIDTH = re.compile("[\u200b-\u200f\u2028-\u202e\u2060-\u2064\u034f\u180e\u061c\ufeff\u00ad\ufe00-\ufe0f]")
_UNICODE_ESCAPE = re.compile(r"\\u([0-9a-fA-F]{4})|\\x([0-9a-fA-F]{2})")
_LITERAL_JOIN = re.compile(r"[\"']\s*[+.]?\s*[\"']")
_PERCENT = re.compile(r"%[0-9A-Fa-f]{2}")
_ENTITY = re.compile(r"&(?:#\d{1,7}|#[xX][0-9a-fA-F]{1,6}|[A-Za-z][A-Za-z0-9]{1,31});")
_ALNUM_RUN = re.compile(r"[A-Za-z0-9]+")
_ASCII_RUN = re.compile(rb"[\x20-\x7e]{%d,}" % MIN_STRING)

# Rule 6: letters from other scripts that print like Latin ones, folded before fingerprinting. Cyrillic
# and Greek, both cases, only the shapes that are indistinguishable in a common typeface.
_HOMOGLYPHS = str.maketrans({
    "а": "a", "е": "e", "о": "o", "р": "p", "с": "c", "х": "x", "у": "y", "і": "i", "ѕ": "s", "ј": "j",
    "ԛ": "q", "ԝ": "w", "һ": "h", "ԁ": "d", "ɩ": "i", "ӏ": "l", "ь": "b", "ԍ": "g",
    "А": "A", "В": "B", "Е": "E", "К": "K", "М": "M", "Н": "H", "О": "O", "Р": "P", "С": "C", "Т": "T",
    "Х": "X", "У": "Y", "Ѕ": "S", "І": "I", "Ј": "J", "Ԛ": "Q", "Ԝ": "W", "Ԍ": "G", "Ӏ": "I", "Ғ": "F",
    "ο": "o", "α": "a", "ι": "i", "κ": "k", "ν": "v", "ρ": "p", "τ": "t", "υ": "u", "χ": "x", "γ": "y",
    "ε": "e", "ϲ": "c", "ϳ": "j", "ⅼ": "l", "ⅰ": "i",
    "Α": "A", "Β": "B", "Ε": "E", "Ζ": "Z", "Η": "H", "Ι": "I", "Κ": "K", "Μ": "M", "Ν": "N", "Ο": "O",
    "Ρ": "P", "Τ": "T", "Υ": "Y", "Χ": "X", "Ϲ": "C",
})
# Extensions after which the part before the dot is a name in its own right, so it is fingerprinted
# too. Deliberately not top-level domains: the stem of `something.ro` is not a name we own.
_STEM_EXTENSIONS = {"json", "jsonl", "md", "txt", "csv", "tsv", "py", "js", "ts", "html", "htm", "css",
                    "yml", "yaml", "toml", "ini", "cfg", "conf", "log", "sh", "ps1", "bat", "xlsx", "xls",
                    "docx", "doc", "pptx", "pdf", "zip", "png", "jpg", "jpeg", "svg", "xml", "sql", "db",
                    "sqlite", "ipynb", "env", "bak", "old"}


# --------------------------------------------------------------------------------------------------
# Normalisation (rule 7) and the allow-list (rule 1)

def normalise_line(line):
    """Decode the encodings a regex cannot see through, then glue split literals back together."""
    if _ENTITY.search(line):
        line = html.unescape(line)
    for _ in range(3):                      # a doubled %XX encoding takes two rounds; a third catches a tripled one
        if not _PERCENT.search(line):
            break
        decoded = urllib.parse.unquote(line)
        if decoded == line:
            break
        line = decoded
    if _ENTITY.search(line):                # an entity that was itself percent-encoded
        line = html.unescape(line)
    line = _UNICODE_ESCAPE.sub(lambda m: chr(int(m.group(1) or m.group(2), 16)), line)
    line = _ZERO_WIDTH.sub("", line)
    line = _LITERAL_JOIN.sub("", line)
    return line


def strip_allowed(line):
    """Blank out the legitimate substrings, keep the rest of the line under inspection."""
    for p in ALLOW:
        line = p.sub(" ", line)
    return line


def fold(text):
    """Compatibility-normalise and fold lookalike letters to Latin, so a name spelled with one Cyrillic
    letter fingerprints the same as the name itself."""
    return unicodedata.normalize("NFKC", text).translate(_HOMOGLYPHS)


# --------------------------------------------------------------------------------------------------
# The private list (rule 6)

def normalise_name(name):
    return re.sub(r"[^a-z0-9]", "", fold(name).lower())


def fingerprint(name):
    return hashlib.sha256(normalise_name(name).encode("utf-8")).hexdigest()[:16]


def expand_names(names):
    """Every name, plus the bare stem of every name that ends in a file extension."""
    out = []
    for n in names:
        out.append(n)
        stem, dot, ext = n.rpartition(".")
        if dot and ext.lower() in _STEM_EXTENSIONS and len(normalise_name(stem)) >= 3:
            out.append(stem)
    return out


def fingerprints_for(names):
    return {fingerprint(n) for n in expand_names(names)}


def read_private_list(path):
    names = []
    for raw in Path(path).read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if line and not line.startswith("#"):
            names.append(line)
    return names


def load_fingerprints(root):
    """The set of fingerprints to look for, and a note about where they came from.

    One source: the local plaintext list, when it is there. Nothing about it is published, not even
    truncated hashes, because a hash confirms a guess for anyone holding a candidate list and a short
    name falls to an offline search. So the rule is on where the list is, which is the machine that
    pushes and the pre-push run, and off everywhere else, and every run says which on its summary line.
    """
    fps, sources = set(), []
    local = Path(root) / PRIVATE_LIST
    if local.is_file():
        fps = fingerprints_for(read_private_list(local))
        sources.append("private-name rule: on, %d names from %s" % (len(fps), PRIVATE_LIST))
    else:
        sources.append("private-name rule: off, no %s here" % PRIVATE_LIST)
    return fps, sources, False


def private_hits(text, fps):
    """Fingerprints of every window of one to WINDOW alphanumeric runs in the text that is on the list."""
    if not fps:
        return set()
    runs = _ALNUM_RUN.findall(fold(text).lower())
    hits = set()
    for i in range(len(runs)):
        joined = ""
        for w in range(WINDOW):
            if i + w >= len(runs):
                break
            joined += runs[i + w]
            fp = hashlib.sha256(joined.encode("utf-8")).hexdigest()[:16]
            if fp in fps:
                hits.add(fp)
    return hits


def write_fingerprints(names_file, out):
    names = read_private_list(names_file)
    too_long = [n for n in names if len(_ALNUM_RUN.findall(fold(n))) > WINDOW]
    if too_long:
        print("%d name(s) have more than %d alphanumeric runs and would never match; shorten them"
              % (len(too_long), WINDOW))
        return 2
    doc = {
        "what": "Fingerprints of the names that must never appear in this repo, so CI can refuse them "
                "without the names themselves being published.",
        "how": "sha256 over the name lowercased, lookalike letters folded to Latin, everything that is not a "
               "letter or a digit removed, first 16 hex characters; a name with a file extension is also "
               "fingerprinted as its bare stem. A scanned line or path is folded the same way, split into "
               "alphanumeric runs, and every window of one to %d consecutive runs is hashed and looked up here."
               % WINDOW,
        "regenerate": "python bench/gate_publish.py --fingerprint %s" % PRIVATE_LIST,
        "window": WINDOW,
        "fingerprints": sorted(fingerprints_for(names)),
    }
    Path(out).write_text(json.dumps(doc, indent=1) + "\n", encoding="utf-8", newline="\n")
    print("wrote %d fingerprints for %d names to %s" % (len(doc["fingerprints"]), len(names), out))
    return 0


# --------------------------------------------------------------------------------------------------
# Computed rules: entropy and base64

def shannon(s):
    counts = collections.Counter(s)
    n = len(s)
    return -sum(c / n * math.log2(c / n) for c in counts.values())


def class_change_rate(s):
    """How often consecutive characters switch between upper, lower and digit.

    A random key switches at about 62% of positions; a CamelCase model id at about 35%; a sentence
    with the spaces removed lower still. Shannon entropy alone cannot tell `Llama4Maverick17B128E...`
    (4.5 bits) from a key, this can.
    """
    def cls(ch):
        return "U" if ch.isupper() else "l" if ch.islower() else "d" if ch.isdigit() else "o"
    classes = [cls(ch) for ch in s]
    changes = sum(1 for a, b in zip(classes, classes[1:]) if a != b)
    return changes / max(1, len(classes) - 1)


def printable_ratio(data):
    return sum(1 for ch in data if 32 <= ch < 127 or ch in b"\t\r\n") / max(1, len(data))


def _label_is_hash(line, start):
    return bool(_HASH_LABEL.search(line[:start]))


def _hash_word_near(line, start):
    return bool(_HASH_WORD.search(line[max(0, start - 60):start]))


def _is_url_userinfo(line, start):
    """True when the text at `start` is the password half of a URL's userinfo, not a mailbox."""
    before = line[:start]
    return before.endswith((":", "/")) and not before.lower().endswith("mailto:")


def _is_public_ipv4(quad):
    """Rule 9: a dotted quad outside every range that documentation, a LAN or the machine itself uses."""
    parts = [int(x) for x in quad.split(".")]
    if any(p > 255 for p in parts):
        return False
    a, b, c, _ = parts
    if a in (0, 10, 127) or a >= 224:                       # this network, private, loopback, multicast, reserved
        return False
    if a == 100 and 64 <= b <= 127:                          # shared address space (carrier NAT)
        return False
    if a == 169 and b == 254:                                # link-local
        return False
    if a == 172 and 16 <= b <= 31:                           # private
        return False
    if a == 192 and (b == 168 or (b == 0 and c in (0, 2))):  # private, protocol assignments, TEST-NET-1
        return False
    if a == 198 and (b in (18, 19) or (b == 51 and c == 100)):  # benchmarking, TEST-NET-2
        return False
    if a == 203 and b == 0 and c == 113:                     # TEST-NET-3
        return False
    return True


def _is_public_ipv6(text):
    """Rule 9, the other family: the candidate must parse as an IPv6 address and sit in a global
    block. The stdlib knows the documentation (2001:db8::/32, 3fff::/20), unique-local, link-local
    and loopback blocks as private; `is_global` alone still says yes to ::/8 and to multicast, so
    those are refused by name. Times, MAC addresses and C++ scopes fail to parse and drop out here."""
    if text.count(":") < 2:
        return False
    try:
        ip = ipaddress.IPv6Address(text)
    except ValueError:
        return False
    return (ip.is_global and not ip.is_private and not ip.is_reserved and not ip.is_multicast
            and not ip.is_loopback and not ip.is_link_local and not ip.is_unspecified)


def _accept(name, line, m):
    """The per-rule second look, for the rules whose pattern alone over-matches."""
    if name in ("secret assigned to a variable", "secret in a JSON field"):
        return not _PLACEHOLDER.search(m.group("value"))
    if name == "private email":
        return not _is_url_userinfo(line, m.start())   # user:password@host is the URL-credentials rule's
    if name == "key: bare 64-plus hex":
        return shannon(m.group(0)) >= 3.0 and not _hash_word_near(line, m.start())
    if name == "public IPv4 address":
        return _is_public_ipv4(m.group(0))
    if name == "public IPv6 address":
        return _is_public_ipv6(m.group(0))
    return True


def computed_hits(line):
    """Yield (name, why) for the rules that need arithmetic rather than a pattern."""
    for m in _HEX_AFTER_ASSIGNMENT.finditer(line):
        v = m.group(1)
        if shannon(v) >= 3.5 and not _label_is_hash(line, m.start()):
            yield ("high-entropy hex after assignment",
                   "a 32-plus hex value assigned under a name that does not say it is a hash")
    for m in _TOKEN_AFTER_ASSIGNMENT.finditer(line):
        v = m.group(1)
        if re.fullmatch(r"[0-9a-fA-F]+", v) or _PLACEHOLDER.search(v):
            continue
        if (re.search(r"[A-Za-z]", v) and re.search(r"[0-9]", v) and shannon(v) >= 4.5
                and class_change_rate(v) >= 0.5 and not _label_is_hash(line, m.start())):
            yield ("high-entropy string after assignment",
                   "a value with the statistics of a random token, assigned to something")
    for m in _BASE64_AFTER_ASSIGNMENT.finditer(line):
        v = m.group(1)
        if len(v) < _BASE64_STATISTICS_MIN:
            continue
        decoded = decode_base64(v)
        if decoded is None:
            continue
        # Either it decodes to text (a docker auth, a user:password pair) or it has the statistics of
        # random bytes. A long model id in the base64 alphabet has neither: it decodes to noise and
        # its characters do not switch class the way random ones do.
        random_like = (shannon(v) >= 4.0 and re.search(r"[A-Z]", v) and re.search(r"[a-z]", v)
                       and re.search(r"[0-9]", v) and class_change_rate(v) >= 0.5)
        if (printable_ratio(decoded) > 0.9 and len(decoded) >= 16) or random_like:
            yield ("base64 blob after assignment or echo",
                   "a base64 value after an assignment, after echo, or in a data: URI: either random bytes "
                   "or text someone wanted hidden")


def decode_base64(v):
    v = v + "=" * (-len(v) % 4)
    try:
        return base64.b64decode(v, validate=True)
    except (binascii.Error, ValueError):
        return None


def decoded_text(v):
    """The text a base64 value hides, or None when it is not text; 32 characters is enough to hide a key."""
    decoded = decode_base64(v)
    if not decoded or printable_ratio(decoded) < 0.9:
        return None
    try:
        return decoded.decode("utf-8")
    except UnicodeDecodeError:
        return None


# --------------------------------------------------------------------------------------------------
# One line, all rules

def scan_line(raw, next_raw=None, fps=frozenset(), rules=True):
    """Every (name, why) that fires on one line.

    `rules` is True for everything, "keys" for the key rules alone (rule 3: the gate, its test and the
    private list), False for the fingerprints alone. A dangling `api_key:` pulls in the next line, and
    so does a string literal left open for a continuation; a token cut by a hard wrap is glued to its
    tail on the next line for the key rules (rule 7).
    """
    line = strip_allowed(normalise_line(raw))
    nxt = strip_allowed(normalise_line(next_raw)) if next_raw is not None else None
    joined = False
    if nxt is not None:
        if _YAML_DANGLING.search(line):
            line, joined = line.rstrip() + " " + nxt.strip(), True
        elif _ENDS_WITH_LITERAL.search(line) and _STARTS_WITH_LITERAL.match(next_raw):
            line, joined = _LITERAL_JOIN.sub("", line.rstrip() + " " + nxt.strip()), True
    keys_only = rules == "keys"
    found = []
    if rules:
        for name, pattern, why in _COMPILED:
            if keys_only and not is_key_rule(name):
                continue
            if any(_accept(name, line, m) for m in pattern.finditer(line)):
                found.append((name, why))
        if nxt is not None and not joined:
            tail, head = _WRAP_TAIL.search(line), _WRAP_HEAD.match(nxt)
            if tail and head and len(tail.group(1)) + len(head.group(1)) >= MIN_STRING:
                glued = line[:tail.start(1)] + tail.group(1) + head.group(1)
                seen = {n for n, _ in found}
                for name, pattern, why in _COMPILED:
                    if is_key_rule(name) and name not in seen and any(_accept(name, glued, m) for m in pattern.finditer(glued)):
                        found.append((name, why + " (wrapped over two lines)"))
        if not keys_only:
            found.extend(computed_hits(line))
        for m in _BASE64_AFTER_ASSIGNMENT.finditer(line):
            inner = decoded_text(m.group(1))
            if inner is None:
                continue
            for name, why in scan_line(inner, None, frozenset(), rules="keys" if keys_only else True):
                found.append((name + ", base64-decoded", why))
    if not keys_only:
        for fp in sorted(private_hits(line, fps)):
            found.append(("private name", "an internal name that must not leave the house (fingerprint %s)" % fp[:8]))
    return found


def binary_strings(raw):
    """The printable ASCII runs of MIN_STRING characters or more inside a binary file: PNG text chunks,
    PDF metadata, ZIP file names, anything a key could have been pasted into."""
    return [r.decode("ascii") for r in _ASCII_RUN.findall(raw)]


# --------------------------------------------------------------------------------------------------
# Files: what to open (rules 3 and 4) and how to read it (rule 2)

def git_ignored(root):
    """The set of paths git would refuse to publish. Empty if git cannot tell us, on purpose.

    The gate's job is to scan everything that COULD reach the public repo, and the honest definition of
    that is "everything git would take". If git is missing or fails, this returns an empty set and
    EVERYTHING gets scanned. Failing towards more scanning is the only safe direction for a gate.
    """
    try:
        r = subprocess.run(["git", "-C", str(root), "ls-files", "--others", "--ignored",
                            "--exclude-standard", "--directory"],
                           capture_output=True, text=True, timeout=60)
        if r.returncode != 0:
            return set()
        return {(Path(root) / line.strip()).resolve()
                for line in r.stdout.split(chr(10)) if line.strip()}
    except Exception:
        return set()


def git_tracks(root, rel):
    """True only when git says the path is in the index; anything else, including no git, is False."""
    try:
        r = subprocess.run(["git", "-C", str(root), "ls-files", "--error-unmatch", "--", rel],
                           capture_output=True, text=True, timeout=60)
        return r.returncode == 0
    except Exception:
        return False


def is_ignored(path, ignored):
    p = Path(path).resolve()
    return any(p == i or i in p.parents for i in ignored)


def key_rules_only(root):
    """Rule 3: the three files that get the key rules and nothing else, by resolved path."""
    here = Path(__file__).resolve()
    return {here, (here.parent / "test_gate.py").resolve(), (Path(root) / PRIVATE_LIST).resolve()}


def archive_kind(raw):
    """"zip" or "gzip" when the bytes carry that signature, else None. Content decides, never the name."""
    if raw[:4] in _ZIP_MAGICS:
        return "zip"
    if raw[:2] == _GZIP_MAGIC:
        return "gzip"
    return None


def load_bytes(raw):
    """(payload, kind) for bytes already in hand: "archive" with the raw bytes when they are a zip or a
    gzip stream; "text" with the decoded text; "binary" with the raw bytes for string extraction.

    Order matters. A UTF-16 file made of ASCII is also valid UTF-8 (NUL is a code point), so UTF-16 is
    detected first, by BOM or by the NUL-on-every-other-byte pattern. Then strict UTF-8. A file that is
    neither and has a NUL byte is binary. A file that is neither and has no NUL is 8-bit text and gets
    read as such. Whatever survived with a NUL in it has the NULs removed: for a log with one stray
    NUL that is the log, and for a UTF-16 file that slipped past the heuristic it is the ASCII text.
    """
    if archive_kind(raw):
        return raw, "archive"
    text = None
    if raw.startswith(b"\xef\xbb\xbf"):
        text = raw[3:].decode("utf-8", errors="replace")
    elif raw[:2] in (b"\xff\xfe", b"\xfe\xff"):
        text = raw.decode("utf-16", errors="replace")
    else:
        head = raw[:65536]
        nul = head.count(b"\x00")
        if nul and len(head) >= 4:
            even = sum(1 for i in range(0, len(head), 2) if head[i] == 0)
            odd = sum(1 for i in range(1, len(head), 2) if head[i] == 0)
            half = len(head) / 2
            if odd / half > 0.3 and even / half < 0.05:
                text = raw.decode("utf-16-le", errors="replace")
            elif even / half > 0.3 and odd / half < 0.05:
                text = raw.decode("utf-16-be", errors="replace")
        if text is None:
            try:
                text = raw.decode("utf-8")
            except UnicodeDecodeError:
                if nul:
                    return raw, "binary"
                text = raw.decode("latin-1")
    if "\x00" in text:
        text = text.replace("\x00", "")
    return text, "text"


def load_text(path):
    """(payload, kind) for a file on disk: what load_bytes says, or "too-large" / "unreadable: ..."."""
    try:
        if path.stat().st_size > MAX_BYTES:
            return None, "too-large"
        raw = path.read_bytes()
    except Exception as e:
        return None, "unreadable: %s" % e
    return load_bytes(raw)


def archive_members(raw, name):
    """[(member name, member bytes or None, problem or None)] for a zip or gzip payload, each member
    inflated with a size cap so a bomb stops at MAX_BYTES + 1. A gzip stream has one member, named
    after the file with its .gz taken off."""
    if archive_kind(raw) == "gzip":
        inner = name[:-3] if name.lower().endswith(".gz") else name + "!inflated"
        try:
            data = zlib.decompressobj(16 + zlib.MAX_WBITS).decompress(raw, MAX_BYTES + 1)
        except zlib.error as e:
            return [(inner, None, "unreadable: %s" % e)]
        return [(inner, None, "too-large")] if len(data) > MAX_BYTES else [(inner, data, None)]
    out = []
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as zf:
            for info in zf.infolist():
                if info.is_dir():
                    continue
                try:
                    with zf.open(info) as fh:
                        data = fh.read(MAX_BYTES + 1)
                except (RuntimeError, NotImplementedError, zipfile.BadZipFile, zlib.error, EOFError, OSError, ValueError) as e:
                    out.append((info.filename, None, "unreadable: %s" % e))
                    continue
                out.append((info.filename, None, "too-large") if len(data) > MAX_BYTES else (info.filename, data, None))
    except (zipfile.BadZipFile, zipfile.LargeZipFile, OSError, ValueError, EOFError) as e:
        out.append((name, None, "unreadable: %s" % e))
    return out


def walk(root):
    """Every file and directory under root that git could publish, plus the local private list.

    Yields (path, rel, is_dir). Skips the repo's own .git and whatever git ignores; nothing else. The
    private list is git-ignored by design and is still yielded, because it gets the key rules (rule 3).
    """
    root = Path(root).resolve()
    ignored = git_ignored(root)
    private = (root / PRIVATE_LIST).resolve()
    skipped_ignored = 0
    for dirpath, dirnames, filenames in os.walk(root):
        dp = Path(dirpath)
        keep = []
        for d in sorted(dirnames):
            full = dp / d
            if dp == root and d == ".git":
                continue
            if ignored and is_ignored(full, ignored):
                skipped_ignored += 1
                continue
            keep.append(d)
            yield full, str(full.relative_to(root)).replace(os.sep, "/"), True
        dirnames[:] = keep
        for f in sorted(filenames):
            full = dp / f
            if ignored and is_ignored(full, ignored) and full.resolve() != private:
                skipped_ignored += 1
                continue
            yield full, str(full.relative_to(root)).replace(os.sep, "/"), False
    walk.skipped_ignored = skipped_ignored


def scannable(root):
    """[(path, rel, kind)] for every file walk() yields, with the kind load_text() gives it.

    test_gate.py uses this for the denominator of its blind-spot check, so the test and the gate cannot
    disagree about what "a file the gate should have opened" means.
    """
    return [(p, rel, load_text(p)[1]) for p, rel, is_dir in walk(root) if not is_dir]


# --------------------------------------------------------------------------------------------------
# The two scan modes

def scan_archive(rel, raw, fps, findings, depth=1):
    """Rule 2 for a zip or gzip payload: its printable strings under the key rules, like any binary,
    then every member inflated and scanned as the file it is, text with every rule, binary by its
    strings, an archive one level deeper. Findings carry the archive's path and the member's name."""
    for s in binary_strings(raw):
        for name, why in scan_line(s, None, fps, rules="keys"):
            findings.append((rel, 0, name, why + " (in the printable strings of an archive)"))
    for member, data, problem in archive_members(raw, rel):
        where = " (in member %s of the archive)" % member
        if problem == "too-large":
            findings.append((rel, 0, "file over %d MB not scanned" % (MAX_BYTES // 1024 // 1024),
                             "member %s of the archive is too large to check, and a file too large to check is "
                             "not a file known to be clean" % member))
            continue
        if problem:
            findings.append((rel, 0, "unreadable", "member %s of the archive: %s" % (member, problem)))
            continue
        for name, why in scan_line(member, None, fps):
            findings.append((rel, 0, name, why + " (in the name of member %s of the archive)" % member))
        payload, kind = load_bytes(data)
        if kind == "archive":
            if depth >= MAX_ARCHIVE_DEPTH:
                findings.append((rel, 0, "unreadable", "member %s is an archive nested %d deep and was not opened; "
                                 "flatten it or keep it out" % (member, depth + 1)))
            else:
                scan_archive(rel, payload, fps, findings, depth + 1)
            continue
        if kind == "binary":
            for s in binary_strings(payload):
                for name, why in scan_line(s, None, fps, rules="keys"):
                    findings.append((rel, 0, name, why + " (in the printable strings of member %s of the archive)" % member))
            continue
        lines = payload.split("\n")
        for n, raw_line in enumerate(lines, 1):
            nxt = lines[n] if n < len(lines) else None
            for name, why in scan_line(raw_line, nxt, fps):
                findings.append((rel, n, name, why + where))


def scan_tree(root):
    root = Path(root).resolve()
    fps, sources, out_of_sync = load_fingerprints(root)
    keyed_paths = key_rules_only(root)
    findings, checked, binaries, archives, keyed = [], 0, 0, 0, 0
    if FINGERPRINTS.is_file():
        findings.append((FINGERPRINTS.relative_to(Path(root)).as_posix() if FINGERPRINTS.is_relative_to(Path(root))
                         else FINGERPRINTS.name, 0, "fingerprint file in the tree",
                         "truncated hashes of the private names confirm a guess for anyone holding a candidate "
                         "list, and a short name falls to an offline search; the list and its fingerprints stay "
                         "in %s, which git ignores" % PRIVATE_LIST))
    for path, rel, is_dir in walk(root):
        for name, why in scan_line(rel, None, fps):
            findings.append((rel, 0, name, why + " (in the name)"))
        if is_dir:
            continue
        mode = True
        if path.resolve() in keyed_paths:
            mode, keyed = "keys", keyed + 1
            if rel == PRIVATE_LIST and git_tracks(root, rel):
                findings.append((rel, 0, "private list tracked by git",
                                 "the plaintext list of private names is in git's index, so it ships with the "
                                 "next push whatever .gitignore says; git rm --cached it"))
        payload, kind = load_text(path)
        if kind == "too-large":
            findings.append((rel, 0, "file over %d MB not scanned" % (MAX_BYTES // 1024 // 1024),
                             "a file too large to check is not a file known to be clean"))
            continue
        if kind == "archive":
            binaries, archives = binaries + 1, archives + 1
            if path.suffix.lower() not in ARCHIVE_SUFFIXES:
                findings.append((rel, 0, "archive under another extension",
                                 "a zip or gzip file whose name says it is something else; content decides, and "
                                 "a container that hides its nature is not a file known to be clean"))
            scan_archive(rel, payload, fps, findings)
            continue
        if kind == "binary":
            binaries += 1
            if path.suffix.lower() not in BINARY_SUFFIXES:
                findings.append((rel, 0, "binary blob with a text name",
                                 "a file the gate cannot read is not a file known to be clean; give it "
                                 "a binary extension if it is meant to ship, or keep it out"))
            for s in binary_strings(payload):
                for name, why in scan_line(s, None, fps, rules="keys"):
                    findings.append((rel, 0, name, why + " (in the printable strings of a binary file)"))
            continue
        if kind != "text":
            findings.append((rel, 0, "unreadable", kind))
            continue
        checked += 1
        lines = payload.split("\n")
        for n, raw in enumerate(lines, 1):
            nxt = lines[n] if n < len(lines) else None
            for name, why in scan_line(raw, nxt, fps, rules=mode):
                findings.append((rel, n, name, why))
    print("checked %d text files under %s (%d binary, strings only, %d of them archives inflated; %d with key rules only; "
          "%d git-ignored entries; %s)"
          % (checked, root, binaries, archives, keyed, getattr(walk, "skipped_ignored", 0),
             ", ".join(sources) or "no private list"))
    return findings


_DIFF_HEADER = re.compile(r"^diff --git a/(.*) b/(.*)$")
_HUNK = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@")


def scan_history(root):
    """Every commit git still knows about: added lines, file names, messages, author and committer.

    A manual pre-push check, not a CI step: the working tree can be clean while a key that was
    committed and then deleted still sits in every clone. Reachable through the reflog too, so a
    commit that was amended away is still seen until git actually forgets it. The gate and its test
    get the key rules here as well (rule 3), and a commit that carries the private list is a finding.
    Known limit: git prints a binary file's diff as "Binary files differ", so a key inside a committed
    image or archive is seen by the tree scan of that commit's checkout, not by this mode.
    """
    root = Path(root).resolve()
    fps, sources, _ = load_fingerprints(root)
    keyed_rel = {"bench/gate_publish.py", "bench/test_gate.py", PRIVATE_LIST}
    cmd = ["git", "-C", str(root), "log", "--all", "--reflog", "--no-color", "--no-ext-diff", "-p",
           "--format=%x01commit %H%x0aauthor %an <%ae>%x0acommitter %cn <%ce>%x0a%x02%B%x03"]
    try:
        r = subprocess.run(cmd, capture_output=True, timeout=600)
    except Exception as e:
        print("git log failed: %s" % e)
        return None
    if r.returncode != 0:
        print("git log failed: %s" % r.stderr.decode("utf-8", errors="replace").strip())
        return None
    out = r.stdout.decode("utf-8", errors="replace")
    findings, commits = [], 0
    for chunk in out.split("\x01commit ")[1:]:
        commits += 1
        sha = chunk[:40]
        head, _, rest = chunk.partition("\x02")
        message, _, patch = rest.partition("\x03")
        for hl in head.split("\n")[1:]:
            for name, why in scan_line(hl, None, fps):
                findings.append((sha, "(%s)" % hl.split(" ")[0], 0, name, why))
        msg_lines = message.split("\n")
        for n, ml in enumerate(msg_lines, 1):
            nxt = msg_lines[n] if n < len(msg_lines) else None
            for name, why in scan_line(ml, nxt, fps):
                findings.append((sha, "(message)", n, name, why))
        cur, new_ln, prev, plines = None, 0, "", patch.split("\n")
        for i, pl in enumerate(plines):
            m = _DIFF_HEADER.match(pl)
            if m:
                cur = m.group(2).strip('"')
                for name, why in scan_line(cur, None, fps):
                    findings.append((sha, cur, 0, name, why + " (in the name)"))
                if cur == PRIVATE_LIST:
                    findings.append((sha, cur, 0, "private list tracked by git",
                                     "this commit carries the plaintext list of private names"))
                prev = pl
                continue
            h = _HUNK.match(pl)
            if h:
                new_ln = int(h.group(1))
            elif pl.startswith("+++ ") and prev.startswith("--- "):
                pass
            elif pl.startswith("+"):
                nxt = plines[i + 1][1:] if i + 1 < len(plines) and plines[i + 1].startswith("+") else None
                for name, why in scan_line(pl[1:], nxt, fps, rules="keys" if cur in keyed_rel else True):
                    findings.append((sha, cur, new_ln, name, why))
                new_ln += 1
            elif pl.startswith(" "):
                new_ln += 1
            prev = pl
    print("scanned %d commits under %s (%s)" % (commits, root, ", ".join(sources) or "no private list"))
    return findings


# --------------------------------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("root", nargs="?", default=".", help="the repo to scan")
    ap.add_argument("--history", action="store_true", help="scan every commit reachable via git log --all --reflog")
    ap.add_argument("--fingerprint", metavar="FILE", help="write the fingerprints of the names in FILE and exit")
    ap.add_argument("--out", metavar="JSON", default=str(Path(PRIVATE_LIST + ".fingerprints").resolve()),
                    help="where --fingerprint writes; keep it out of the tree")
    a = ap.parse_args()

    if a.fingerprint:
        if not Path(a.fingerprint).is_file():
            print("no such file: %s" % a.fingerprint)
            return 2
        return write_fingerprints(a.fingerprint, a.out)

    root = Path(a.root).resolve()
    if not root.is_dir():
        print("not a directory: %s" % root)
        return 2

    if a.history:
        findings = scan_history(root)
        if findings is None:
            return 2
        if not findings:
            print("CLEAN - nothing in the history. Safe to push.")
            return 0
        print("\n%d FINDINGS in the history - rewrite or drop these commits before pushing:\n" % len(findings))
        for sha, file, line, what, why in findings:
            print("  %s %s:%s  %s" % (sha[:10], file, line, what))
            print("      %s" % why)
        return 1

    findings = scan_tree(root)
    if not findings:
        print("CLEAN - nothing found. Safe to publish.")
        return 0
    print("\n%d FINDINGS - do not publish until these are gone:\n" % len(findings))
    for file, line, what, why in findings:
        print("  %s:%s  %s" % (file, line, what))
        print("      %s" % why)
    return 1


if __name__ == "__main__":
    sys.exit(main())
