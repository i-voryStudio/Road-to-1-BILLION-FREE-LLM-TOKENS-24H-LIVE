#!/usr/bin/env python3
"""Tests for the publication gate. No network, no keys, no API calls.

A gate that has never caught anything is not a gate, it is a green light. Every case below is a leak
the gate MUST catch, and each one names the RULE that has to fire: "exit 1 on the right file" is
satisfied by any rule firing for any reason, and a case that does not name its rule proves nothing
about the rule it was written for. The first day's misses are still here (a key beside `${HOME}`, in a
Makefile, in a workflow, in a copy named gate_publish.py); the second wave came from a review that
planted twenty leak shapes and watched nineteen walk through: keys with no known prefix, keys in
JSON fields, headers without the word Bearer, four path forms, trailers, first-person account
state, a text file with an image extension, a tracked folder named venv, UTF-16, encodings a regex
cannot see through, and names that were never matched against anything. The third wave came from the
re-review of that fix: bare keys with prefixes the list did not have, a key in an array under a plural
field, a key split over two source lines, a short base64 value, a key inside a PNG's text chunk, a
private name spelled with one Cyrillic letter, the reworded account-state sentences, Romanian ones,
rate-limit headers echoing our quota, three more ways of crediting a tool, a public IP address, and
the fact that the gate and its test were exempt from every rule, so a key pasted into either shipped.
The fourth wave came from the review after that, which planted nineteen more shapes and copied
fourteen sentences out of the repository's own history, and watched all of them pass: the account
rule had been calibrated to the previous review's exact phrasings, not to the class. So the class is
what is planted now: the key as the thing that answered, a grant next to a verb of consumption, our
own call, our own tooling, our own measured header, a remaining-header echo in every dress (a JSON
field, a colon, a space, capitals), a limit header dumped bare; plus a key hard-wrapped over two
lines, base64 after `echo` and in a `data:` URI, an HTML entity in a key prefix, a doubled URL
encoding, a bare 96-hex string, a deflated zip under a .png name, a UNC path, a global IPv6 address,
and the same granularity of tool trace for every vendor.

The other direction is tested with the same care: SHA-pinned actions, URLs with a 40-hex segment,
model ids that look like base64, documented `export X=...` lines, the jury's own names, the
documentation IP ranges of both families, a PNG with nothing in it, a clean zip, a results file with a
bare HTTP 402 and, above all, measurement provenance that describes the ENDPOINT ("rate-limit
response headers on a free-trial key reported x-ratelimit-limit-requests-day 2400", "the endpoint
answered HTTP 429 on 2026-09-06", a keyless endpoint's anonymous bucket read in prose) must all stay
clean, or the gate becomes a thing people bypass.

Then the real repo: the gate must open every file the test thinks is scannable, with "scannable"
defined by the gate's own function so the two cannot disagree, and the repo must pass. The history
mode gets a scratch git repo with the class planted in it (an account-state sentence in a data file,
committed and then removed; a tooling note; a header echo; a JSON remaining field; a key in a commit
message; an author on a private domain) and a control repo that must stay CLEAN. The fingerprint
round-trip, the partial self-exemption and the private list get a scratch directory or repo each.

The key-shaped strings in this file are assembled from pieces the gate does not glue back together
(`%` formatting, `join`), never written whole, because this file is scanned with the key rules like
any other. Every phrase, trailer and address fixture is assembled from pieces as well: the literal
never sits in this file, so a rewrite of the history with literal replacement rules cannot rewrite a
fixture, and no line here reads as a real trailer from a real vendor's mailbox.

    python bench/test_gate.py
"""
import base64, gzip, io, json, re, shutil, struct, subprocess, sys, tempfile, zipfile, zlib
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
GATE = HERE / "gate_publish.py"
sys.path.insert(0, str(HERE))
import gate_publish as G

# Key-shaped strings that are not keys, assembled so this file does not trip the key rules it is scanned with.
FAKE_GROQ = "gsk_" + "A" * 32
FAKE_OPENAI = "sk-" + "B" * 32
FAKE_B64_AUTH = base64.b64encode(("user:" + FAKE_GROQ).encode()).decode()
FAKE_B64_KEY = base64.b64encode(("key=" + FAKE_GROQ).encode()).decode()
FAKE_JWT = ".".join(("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9", "eyJzdWIiOiIxMjM0NTY3ODkwIn0",
                     "SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"))
RANDOM_TOKEN = "q8Zk2mN7vL4pX9wR3tY6uH1jB5cF0dG8sA2eK4iM"
SHA256_HEX = "".join(("9f86d081884c7d659a2feaa0c55ad015", "a3bf4f1b2b0b822cd15d6c15b0f00a08"))
HEX96 = "".join(("9f86d081884c7d659a2feaa0c55ad015", "a3bf4f1b2b0b822cd15d6c15b0f00a08", "2c26b46b68ffc68ff99b453c1d304134"))
RANDOM_BYTES_B64 = base64.b64encode(bytes(range(7, 71))).decode()
PINNED = ("      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1  # v7.0.1, pinned\n"
          "      - uses: actions/setup-python@5fda3b95a4ea91299a34e894583c3862153e4b97  # v7.0.0, pinned\n")

# Trailers, vendor addresses and tool credits, in pieces: no literal trailer and no vendor domain sits here.
TRAILER = "Co-Authored" + "-By: Some Assistant <noreply@" + "example.com>\n"
TRAILER_ANY = "Co-authored" + "-by: Someone <someone@" + "example.com>\n"
VENDOR_MAIL = "reviewed by someone@" + "openai" + ".com\n"
GEN_BY = "Generated " + "by "
POWERED_BY = "Powered " + "by "


def png_chunk(kind, data):
    body = kind + data
    return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)


def png(*extra):
    """A valid 1x1 PNG, with any extra chunks placed between the header and the pixel data."""
    ihdr = png_chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
    idat = png_chunk(b"IDAT", zlib.compress(b"\x00\x00\x00\x00"))
    return b"\x89PNG\r\n\x1a\n" + ihdr + b"".join(extra) + idat + png_chunk(b"IEND", b"")


def zip_bytes(members):
    """A deflated zip: the members' text is compressed, so a string scan of the bytes cannot see it."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, body in members.items():
            zf.writestr(name, body)
    return buf.getvalue()


REAL_PNG = png()
PNG_WITH_KEY = png(png_chunk(b"tEXt", b"Comment\x00key=" + FAKE_GROQ.encode()))
ZIP_WITH_KEY = zip_bytes({"notes.txt": "key: %s\n" % FAKE_GROQ})
ZIP_CLEAN = zip_bytes({"README.txt": "nothing to see here, twice over, nothing to see here\n"})
ZIP_NESTED = zip_bytes({"inner.zip": ZIP_WITH_KEY})
GZ_WITH_KEY = gzip.compress(("key: %s\n" % FAKE_GROQ).encode())
GZ_CLEAN = gzip.compress(b"a clean log line, and another clean log line\n")

# The private names used in these tests are the two fictional ones shipped as the example list. Every
# fixture directory gets that list as its own .gate-private, so no real name is written anywhere here.
EXAMPLE_LIST = ROOT / ".gate-private.example"
EXAMPLE_NAMES = [l.strip() for l in EXAMPLE_LIST.read_text(encoding="utf-8").splitlines()
                 if l.strip() and not l.startswith("#")]
P1, P2 = EXAMPLE_NAMES[0], EXAMPLE_NAMES[1]

# (path inside the fixture, contents (str or bytes), rule that must fire, why it must be caught)
MUST_CATCH = [
    # --- the first day's misses
    ("plain.md", "key: %s\n" % FAKE_GROQ, "key: Groq shape",
     "a bare key in a markdown file: the simplest case there is"),
    ("beside_shell_var.md", "key: %s used with ${HOME}\n" % FAKE_GROQ, "key: Groq shape",
     "key on the same line as a shell variable: an allow-pattern must not blind the whole line"),
    ("beside_own_link.md", "%s see https://github.com/i-voryStudio\n" % FAKE_GROQ, "key: Groq shape",
     "key on the same line as our own repo link"),
    ("glued_to_own_link.md", "see https://github.com/i-voryStudio/%s\n" % FAKE_GROQ, "key: Groq shape",
     "key glued to our own link as a path segment: the allow-pattern must blank the link, not the key"),
    ("beside_recompile.md", 're.compile(r"x")  # %s\n' % FAKE_OPENAI, "key: OpenAI or OpenRouter shape",
     "key on a line that also contains re.compile("),
    ("Makefile", "deploy:\n\tcurl -H 'Authorization: Bearer %s'\n" % FAKE_GROQ, "key: Groq shape",
     "key in a file with no extension at all"),
    ("keys.ini", "[default]\napi_key = %s\n" % FAKE_GROQ, "key: Groq shape",
     "key in an .ini file, an extension not on any allowlist"),
    ("notes.txt.bak", "key: %s\n" % FAKE_GROQ, "key: Groq shape",
     "key in a backup file, the classic thing nobody remembers to delete"),
    (".github/workflows/leak.yml", "env:\n  KEY: %s\n" % FAKE_GROQ, "key: Groq shape",
     "key inside .github/workflows: the single most likely place for a real one"),
    ("sub/gate_publish.py", "key = '%s'\n" % FAKE_OPENAI, "key: OpenAI or OpenRouter shape",
     "key in a file that merely shares the gate's filename: self-exemption must be by path, not name"),
    ("balance.json", '{"error": "your account balance is insufficient"}\n', "account state, provider phrasing",
     "our own billing state, in the provider's words"),
    ("quota.json", '{"error": {"code": "insufficient_quota"}}\n', "account state, provider phrasing",
     "the other phrase every OpenAI-compatible error body uses for the same thing"),
    ("multiplied.md", "Limit: 40/min x 4 keys = 160/min\n", "multi-key arithmetic",
     "a rate limit multiplied across keys: usually false, and reads as quota evasion"),
    ("multiplied_no_x.md", "with 4 keys, so 160/min\n", "multi-key arithmetic",
     "the same arithmetic phrased without an x"),
    ("multiplied_accounts.md", "5 accounts * 200/day\n", "multi-key arithmetic",
     "accounts instead of keys, star instead of x"),
    ("path.md", "Ran from C:/Users/someone/Documents/project\n", "Windows user path",
     "an absolute path off somebody's machine"),
    ("mail.md", "Contact: real.person@some-company.ro\n", "private email", "a real email address"),
    # --- keys with no known prefix, and prefixes the first version did not know
    ("env.md", "MISTRAL_API_KEY=a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6\n", "secret assigned to a variable",
     "a prefix-less key assigned to PROVIDER_API_KEY: a word boundary before 'api' never matches this"),
    ("env2.md", "export KENARI_API_KEY=%s\n" % ("k" * 40), "secret assigned to a variable",
     "a prefix-less key after export"),
    ("cf.md", "CF_API_TOKEN=%s\n" % ("Q" * 40), "secret assigned to a variable",
     "a 40-character token assigned to a _TOKEN variable"),
    ("password.ini", "password = hunter2hunter2hunter2\n", "secret assigned to a variable", "a password"),
    ("cfg.yml", "api_key:\n  %s\n" % ("b" * 40), "secret assigned to a variable",
     "a YAML two-line assignment: the value is on the next line"),
    ("zai.md", "ZAI_API_KEY=%s.%s\n" % ("f" * 32, "Z" * 16), "key: id.secret shape",
     "the id.secret shape, 32 hex then 16 alphanumerics"),
    ("json.md", '{"key": "%s"}\n' % ("x" * 40), "secret in a JSON field",
     "a key in a JSON field named key"),
    ("token.json", '{"token": "%s"}\n' % ("t" * 20), "secret in a JSON field",
     "a token in a JSON field named token"),
    ("auth.md", "Authorization: %s\n" % ("T" * 40), "Authorization header value",
     "an Authorization header without the word Bearer"),
    ("curl.md", "Authorization: bearer %s\n" % ("b" * 40), "Authorization header value",
     "a lowercase bearer: the header rule is case-insensitive"),
    ("bearer_inline.md", "curl -H 'bearer %s'\n" % ("b" * 40), "Bearer token inline",
     "a bearer token with no header name in front of it"),
    ("csk.md", "csk-%s\n" % ("c" * 40), "key: Cerebras shape", "a Cerebras key"),
    ("hf.md", "hf_%s\n" % ("H" * 34), "key: Hugging Face shape", "a Hugging Face token"),
    ("nvapi.md", "nvapi-%s\n" % ("n" * 40), "key: NVIDIA shape", "an NVIDIA key"),
    ("google.md", "AIza%s\n" % ("G" * 35), "key: Google shape", "a Google key"),
    ("github.md", "ghp_%s\n" % ("g" * 36), "key: GitHub shape", "a GitHub token"),
    ("glpat.md", "glpat-%s\n" % ("G" * 22), "key: GitLab shape", "a GitLab token"),
    ("slack.md", "xoxb-%s\n" % "1234567890-abcdefghijk", "key: Slack shape", "a Slack token"),
    ("aws.md", "AKIA%s\n" % "IOSFODNN7EXAMPLE", "key: AWS shape", "an AWS access key id"),
    ("jwt.md", "token=%s\n" % FAKE_JWT, "key: JWT shape", "a signed JWT"),
    ("openrouter.md", "sk-or-v1-%s\n" % ("a" * 48), "key: OpenAI or OpenRouter shape", "an OpenRouter key"),
    ("id_rsa.txt", "-----BEGIN RSA %s-----\n" % "PRIVATE KEY", "private key block", "a private key"),
    ("urlcred.md", "https://someone:%s@host.example.com/\n" % "S3cretPassw0rd", "credentials in a URL",
     "a password in the userinfo part of a URL"),
    # --- prefixes the second review found missing, and shapes with no assignment in front of them
    ("stripe.md", "rotate sk_live_%s soon\n" % ("Q" * 24), "key: Stripe shape", "a live payment key, bare in prose"),
    ("stripe_test.md", "rk_test_%s\n" % ("Q" * 24), "key: Stripe shape", "the restricted and test-mode forms"),
    ("xai.md", "xai-%s\n" % ("Z" * 40), "key: xAI shape", "an xAI key with nothing assigning it"),
    ("ya29.md", "ya29.a0Af%s\n" % ("B" * 60), "key: Google OAuth token shape", "a Google OAuth access token"),
    ("xapp.md", "slack xapp-%s\n" % ("1-A0123456789-0123456789012-" + "a" * 30), "key: Slack shape",
     "a Slack app-level token"),
    ("hex64.md", "value %s\n" % SHA256_HEX, "key: bare 64-plus hex",
     "a bare 64-hex string with no label at all: the raw shape of several providers' keys"),
    ("hex96.md", "value %s\n" % HEX96, "key: bare 64-plus hex",
     "a bare 96-hex string: the rule that stopped at exactly 64 never saw one"),
    ("plural.json", '{"api_keys": ["%s"]}\n' % RANDOM_TOKEN, "secret in a JSON field",
     "a secret inside an array under a plural field name"),
    ("plural.py", 'api_keys = ["%s"]\n' % RANDOM_TOKEN, "secret assigned to a variable",
     "the same array assigned to a variable"),
    ("paren.py", 'KEY = ("gsk_AAAA"\n       "%s")\n' % ("A" * 32), "key: Groq shape",
     "a key split over two source lines by parenthesised adjacency"),
    ("short_b64.json", '{"blob": "%s"}\n' % base64.b64encode(("sk-" + "C" * 27).encode()).decode(),
     "key: OpenAI or OpenRouter shape, base64-decoded", "a base64 value under 48 characters that decodes to a key"),
    # --- values with no name at all: statistics
    ("session.env", "SESSION=%s\n" % RANDOM_TOKEN, "high-entropy string after assignment",
     "a random token assigned to a variable whose name says nothing"),
    ("digest.md", "sig: %s\n" % SHA256_HEX, "high-entropy hex after assignment",
     "a long hex value under a name that does not say it is a hash"),
    ("docker.json", '{"auths":{"r.example":{"auth":"%s"}}}\n' % FAKE_B64_AUTH, "key: Groq shape, base64-decoded",
     "a key hidden inside a base64 auth value: the value is decoded and scanned"),
    ("random.env", "SECRET=%s\n" % RANDOM_BYTES_B64, "base64 blob after assignment or echo",
     "a base64 blob of bytes after an assignment"),
    # --- the fourth wave: a key that is only invisible to a regex, in the shapes the review planted
    ("wrapped.yaml", "note: the key gsk_%s\n  %s was used\n" % ("A" * 12, "A" * 20), "key: Groq shape",
     "a key hard-wrapped over two lines inside a string: the tail of one line is glued to the head of the next"),
    ("wrapped_prose.md", "rotate gsk_%s\n%s before Monday\n" % ("A" * 8, "A" * 24), "key: Groq shape",
     "the same wrap in prose, with the break early in the key"),
    ("echo.sh", "echo %s | base64 -d\n" % FAKE_B64_KEY, "key: Groq shape, base64-decoded",
     "a base64 key fed to base64 -d through echo: no assignment in front of it"),
    ("datauri.md", "data:text/plain;base64,%s\n" % FAKE_B64_KEY, "key: Groq shape, base64-decoded",
     "a base64 key inside a data: URI"),
    ("echo_blob.sh", "echo -n %s | base64 -d > blob\n" % RANDOM_BYTES_B64, "base64 blob after assignment or echo",
     "a blob of random bytes after echo with a flag"),
    ("entity.md", "gsk&#95;%s\n" % ("A" * 32), "key: Groq shape",
     "an HTML entity hiding the underscore of the prefix"),
    ("entity_named.md", "gsk&lowbar;%s\n" % ("A" * 32), "key: Groq shape",
     "the named entity for the same underscore"),
    ("double_urlenc.md", "https://x.example/?k=gsk%%255F%s\n" % ("A" * 32), "key: Groq shape",
     "a doubled URL encoding: one unquote leaves %5F in place"),
    # --- machines, in more forms
    ("ip.md", "server at 51.15.23.42 answered\n", "public IPv4 address",
     "a public address: the machine the run came from, or the one it went to"),
    ("ip_json.json", '{"client_ip": "8.8.4.4"}\n', "public IPv4 address", "a public address in a JSON field"),
    ("ipv6.md", "server at 2001:4860:4860::8844 answered\n", "public IPv6 address",
     "a global IPv6 address: a machine, in the other family"),
    ("ipv6_json.json", '{"client_ip": "2606:4700:4700::1111"}\n', "public IPv6 address",
     "a global IPv6 address in a JSON field"),
    ("unc.md", "ran from \\\\host\\share\\Users\\someone\\x\n", "UNC user path",
     "a UNC path: the machine is named by its network name, the user by the folder"),
    ("unc_json.json", '{"path": "\\\\\\\\host\\\\share\\\\Users\\\\someone"}\n', "UNC user path",
     "the same path JSON-escaped, the form a results file writes"),
    ("unc_slash.md", "ran from //host/share/Users/someone/x\n", "UNC user path",
     "the forward-slash form a Unix shell on Windows writes for a share"),
    # --- every path form
    ("gitbash.md", "ran from /c/Users/SOMEONE/Documents/x\n", "Git Bash or WSL user path", "the Git Bash form"),
    ("wsl.md", "ran from /mnt/c/Users/SOMEONE/x\n", "Git Bash or WSL user path", "the WSL form"),
    ("cygwin.md", "ran from /cygdrive/c/Users/someone/x\n", "Git Bash or WSL user path", "the Cygwin form"),
    ("mac.md", "ran from /Users/someone/Documents/x\n", "macOS user path", "a macOS home"),
    ("mac_bare.md", "/Users/someone/proj\n", "macOS user path", "a macOS home with nothing before it"),
    ("home_upper.md", "ran from /home/SOMEONE/x\n", "Linux home path", "a Linux home with an uppercase user"),
    ("home_env.md", "HOME=/home/someone\n", "Linux home path", "a Linux home with no trailing slash"),
    ("root.md", "cache in /root/.cache/x\n", "root home path", "root's home"),
    ("trace.json", '{"path": "C:\\\\Users\\\\someone\\\\proj"}\n', "Windows user path",
     "a JSON-escaped Windows path, the form every results file and traceback uses"),
    ("fwd.md", "C:/Users/someone/x and c:\\users\\someone\\y\n", "Windows user path",
     "forward slashes and lowercase"),
    ("C_Users_someone_notes.md", "clean\n", "slugified user path",
     "a user path with the separators replaced, in a file NAME"),
    # --- traces of a code-generation tool, one granularity for every vendor. Every fixture is assembled
    #     from pieces, so no trailer and no vendor address sits in this file whole.
    ("trailer.md", TRAILER, "assistant trace", "a co-author trailer"),
    ("trailer_any.md", TRAILER_ANY, "assistant trace",
     "any co-author trailer at all, even with a placeholder address"),
    ("assistant.md", GEN_BY + "Claude Code. The user " + "asked for a table.\n", "assistant trace",
     "prose left by a code-generation tool"),
    ("user_said.md", "the user " + "said it should be shorter\n", "assistant trace", "the other prose form"),
    ("gen_link.md", "Generated " + "with [Some Tool](https://example.com/tool)\n", "assistant trace",
     "the markdown-link form of the trailer"),
    ("gen_codex.md", GEN_BY + "Codex CLI\n", "assistant trace", "the same credit for the second vendor's tool"),
    ("gen_gemini.md", "Generated " + "with Gemini CLI\n", "assistant trace", "the third"),
    ("gen_copilot.md", GEN_BY + "GitHub Copilot\n", "assistant trace", "the fourth"),
    ("gen_using.md", "Generated " + "using ChatGPT\n", "assistant trace", "the credit with 'using' as the preposition"),
    ("vendor_mail.md", VENDOR_MAIL, "assistant trace", "a vendor address"),
    ("made_with.md", "Made " + "with Cursor.\n", "assistant trace", "the made-with credit"),
    ("written_by.md", "Written " + "by ChatGPT, reviewed by us.\n", "assistant trace", "the written-by credit"),
    ("powered.md", POWERED_BY + "Claude\n", "assistant trace", "the powered-by credit"),
    ("powered_gpt.md", POWERED_BY + "ChatGPT\n", "assistant trace", "the same credit for another vendor"),
    ("product_bare.md", "fixed in " + "Codex CLI, then in " + "Gemini CLI\n", "assistant trace",
     "a tool's product name bare in prose: every vendor's agent product, at the granularity one vendor had"),
    ("drafted.md", "Fable 5.1 " + "drafted this section.\n", "assistant trace",
     "a model name with a version number, then a verb of authorship"),
    ("drafted_gpt.md", "GPT-5 " + "drafted this section.\n", "assistant trace", "the same shape for the second vendor"),
    ("drafted_gemini.md", "Gemini 3 Flash " + "reviewed this section.\n", "assistant trace", "the third, with a tier word"),
    ("checked.md", "Opus 5 " + "checked the maths\n", "assistant trace", "a verb of review after a model family"),
    ("reviewed.md", "Claude " + "reviewed this\n", "assistant trace", "the same verb without a version"),
    ("wrote.md", "Claude " + "wrote the first draft\n", "assistant trace", "a model name and a verb of authorship"),
    ("copilot_wrote.md", "Copilot " + "suggested the loop\n", "assistant trace", "the fourth vendor with a verb"),
    # --- the state of the account behind the key, in the first person. Assembled from pieces.
    ("balance2.md", "our " + "key had no " + "balance, so every call returned 402\n", "account state, first person",
     "account state in the first person"),
    ("balance3.md", "credits " + "remaining: $0.37, quota " + "exceeded for today\n", "account state, first person",
     "the credits wording"),
    ("usage.md", '"remaining_' + 'at_measurement": 4984208\n', "account state, first person",
     "a consumption figure from the account behind the key"),
    ("used.md", '"used_' + 'today_at_measurement": 15792\n', "account state, first person", "the other figure"),
    ("this_account.md", "the ceiling this " + "account is given moves\n", "account state, first person",
     "the phrase this-account"),
    ("valid_key.md", "HTTP 401 with a valid " + "new key, measured today\n", "account state, first person",
     "the phrase about a new key"),
    ("refused.md", "403: refused " + "this client\n", "account state, first person", "the 403 wording"),
    ("rejected.md", "401: rejected " + "the credential\n", "account state, first person", "the 401 wording"),
    ("our_accounts.md", "one sample, our " + "accounts, not an uptime guarantee\n", "account state, first person",
     "the plural first-person form"),
    # --- the third wave: the rewordings the re-review found, the Romanian forms, and the header echoes
    ("my_key.md", "my " + "key ran out of " + "credits yesterday\n", "account state, first person",
     "the singular first person, and running out of credits"),
    ("low_balance.md", "the account shows low " + "balance today\n", "account state, first person",
     "the low-balance wording"),
    ("used_up.md", "answered 402 once the sign-up credit was " + "used up\n", "account state, first person",
     "used up, after the word credit"),
    ("used_up_grant.md", "used " + "up the whole grant in a day\n", "account state, first person",
     "used up, before the word grant"),
    ("this_key.md", "the endpoint answered 429 to " + "this key\n", "account state, first person",
     "a specific key being refused: a fact about the key, not the endpoint"),
    ("separate.md", "returns 429 without a " + "separate balance\n", "account state, first person",
     "the balance wording the re-review found"),
    ("tooling.md", "Run through our own agent " + "tooling, so a stranger cannot reproduce it\n",
     "account state, first person", "our own tooling: a fact about us"),
    ("agents.md", "Two of our " + "own agents run non-stop\n", "account state, first person", "our own agents"),
    ("ro_key.md", "cheia " + "noastră a rămas fără credit\n", "account state, first person",
     "Romanian, first person, with diacritics"),
    ("ro_account.md", "contul " + "nostru a fost blocat; soldul " + "nostru e zero; creditul " + "nostru s-a dus\n",
     "account state, first person", "Romanian: the account, the balance, the credit"),
    ("ro_plain.md", "cheia " + "noastra a ramas fara credit, contul " + "meu e blocat, cheia " + "mea e veche\n",
     "account state, first person", "Romanian without diacritics, and the singular forms"),
    ("hdr_remaining.md", "x-ratelimit-" + "remaining-tokens: 4984208\n", "account state, first person",
     "a rate-limit header echoing what is left on our account"),
    ("hdr_limit.md", "x-ratelimit-" + "limit-requests-day: 2400\n", "account state, first person",
     "the limit header with a number: the ceiling this account was given"),
    # --- the fourth wave: the CLASS, in the sentences copied out of the repository's own history
    ("key_returned.md", "Measured 2026-09-07, the key " + "returned 402 Payment Required, so that sign-up credit "
     + "had already been consumed.\n", "account state, first person",
     "the key as the thing that answered, and a credit next to a verb of consumption"),
    ("dollar_used.md", "so that dollar " + "had already been used up\n", "account state, first person",
     "a dollar next to used up"),
    ("credit_consumed.md", "the credit " + "had been consumed by noon\n", "account state, first person",
     "the perfect form"),
    ("credits_consumed.md", "credits " + "consumed: 12\n", "account state, first person",
     "the bare noun-verb pair"),
    ("credit_run_out.md", "the sign-up credit " + "had run out by the second day\n", "account state, first person",
     "run out in the perfect: ours, not a kind of tier"),
    ("own_call.md", "response headers on our " + "own call: x-ratelimit-limit 5, x-ratelimit-" + "remaining 4\n",
     "account state, first person", "our own call, and a header list after a colon"),
    ("own_header.md", "Our " + "own measured header on 2026-09-07 read x-ratelimit-limit 5\n",
     "account state, first person", "our own measured header"),
    ("own_tooling.md", "reached through our " + "own tooling. NOT reproducible by a stranger\n",
     "account state, first person", "our own tooling, without the word agent in front"),
    ("hdr_json.json", '{"x-ratelimit-' + 'remaining": "4"}\n', "account state, first person",
     "a remaining header as a JSON field: no hyphen after remaining, quotes instead of a colon"),
    ("hdr_bare_remaining.md", "x-ratelimit-" + "remaining 4\n", "account state, first person",
     "a remaining header echoed with a space and no colon"),
    ("hdr_bare_limit.md", "x-ratelimit-" + "limit-tokens-day 1000000\n", "account state, first person",
     "a limit header dumped bare on a line of its own"),
    ("hdr_bullet_limit.md", "- x-ratelimit-" + "limit-requests-day 2400\n", "account state, first person",
     "the same dump as a list item"),
    ("hdr_caps.md", "X-RateLimit-" + "Remaining: 4984208\n", "account state, first person",
     "the header in its canonical capitals, with a colon and no suffix"),
    ("my_account.md", "my " + "account was suspended\n", "account state, first person", "my account"),
    ("our_quota.md", "our " + "quota for today is gone\n", "account state, first person", "our quota"),
    ("balance_left.md", "balance" + ": $0.37 left\n", "account state, first person", "a balance figure"),
    ("ran_out.md", "we ran " + "out of quota\n", "account state, first person", "ran out of quota"),
    # --- file handling
    ("notes.png", "%s\n" % FAKE_GROQ, "key: Groq shape",
     "a text file with an image extension: content decides, not the name"),
    ("venv/leak.md", "%s\n" % FAKE_GROQ, "key: Groq shape",
     "a key inside a tracked folder named venv: only what git ignores is skipped"),
    ("node_modules/pkg/.npmrc", "//registry.example/:_authToken=%s\n" % FAKE_GROQ, "key: Groq shape",
     "a key inside a tracked node_modules"),
    ("docs/.git/credentials", "https://user:%s@github.com\n" % FAKE_GROQ, "key: Groq shape",
     "a nested .git is an ordinary directory; only the repo's own .git is skipped"),
    ("utf16.md", ("key: %s\n" % FAKE_GROQ).encode("utf-16-le"), "key: Groq shape",
     "UTF-16 without a BOM, the PowerShell redirect default: decoded, not skipped as binary"),
    ("utf16bom.md", ("key: %s\n" % FAKE_GROQ).encode("utf-16"), "key: Groq shape", "UTF-16 with a BOM"),
    ("stray_nul.log", b"ok\x00\nkey: " + FAKE_GROQ.encode() + b"\n", "key: Groq shape",
     "a log with one stray NUL byte is still a log"),
    ("blob.dat", b"\x00\x01\x02\xff\xfe\x80\x00\x00binary" * 40, "binary blob with a text name",
     "a genuinely binary file under a name that is not on the binary denylist"),
    ("chart.png", PNG_WITH_KEY, "key: Groq shape",
     "a valid PNG whose text chunk carries a key: a binary file is not skipped, its strings are read"),
    ("chart.dat", PNG_WITH_KEY, "key: Groq shape",
     "the same PNG under a text name: flagged as a blob AND string-scanned"),
    ("notes.zip", ZIP_WITH_KEY, "key: Groq shape",
     "a key inside a deflated zip: the strings of the bytes cannot see it, the inflated member can"),
    ("chart2.png", ZIP_WITH_KEY, "key: Groq shape",
     "the same zip named .png: the magic bytes decide, and the member is still inflated"),
    ("photo.png", ZIP_CLEAN, "archive under another extension",
     "a zip under an image's name is a finding by itself, even when its members are clean"),
    ("nested.zip", ZIP_NESTED, "key: Groq shape", "a key two archives deep"),
    ("notes.txt.gz", GZ_WITH_KEY, "key: Groq shape", "a key inside a gzip stream"),
    ("banner.png", GZ_WITH_KEY, "key: Groq shape", "a gzip stream named .png"),
    # --- encodings a regex cannot see through
    ("urlenc.md", "https://x.example/?k=gsk%%5F%s\n" % ("A" * 32), "key: Groq shape", "URL-encoded underscore"),
    ("uesc.json", '{"k": "\\u0067sk_%s"}\n' % ("A" * 32), "key: Groq shape", "a JSON \\u escape in the prefix"),
    ("zwsp.md", "key: gsk_\u200b%s\n" % ("A" * 32), "key: Groq shape", "a zero-width space inside the prefix"),
    ("lrm.md", "key: gsk_%s\u200e%s\n" % ("A" * 10, "A" * 22), "key: Groq shape",
     "a left-to-right mark inside the key, outside the first six invisible characters the gate knew"),
    ("cgj.md", "key: gsk_%s\u034f%s\n" % ("A" * 10, "A" * 22), "key: Groq shape",
     "a combining grapheme joiner inside the key"),
    ("concat.py", 'KEY = "gsk_" + "%s"\n' % ("A" * 32), "key: Groq shape",
     "a key split across two string literals, the trick this very file uses to hide its fakes"),
    ("obfmail.md", "write to name [at] domain.ro\n", "private email", "an obfuscated address"),
    ("obfmail2.md", "name (at) domain (dot) ro\n", "private email", "the other obfuscation"),
    ("mailto.md", "mailto:someone@some-company.ro\n", "private email",
     "mailto: is an address, not URL userinfo"),
    # --- private names, by fingerprint, in content and in names
    ("brand.md", "see %s and the %s deck\n" % (P1, P2), "private name", "a private name in content"),
    ("brand_spaced.md", "the %s deck\n" % P1.replace("-", " ").title(), "private name",
     "a private name with spaces instead of hyphens: matching is normalised"),
    ("brand_glued.md", "the %s deck\n" % P1.replace("-", ""), "private name", "a private name with nothing between the words"),
    ("cyrillic.md", "the %s deck\n" % P1.replace("a", "\u0430", 1), "private name",
     "a private name with one Cyrillic a in it: lookalikes are folded before fingerprinting"),
    ("greek.md", "the %s deck\n" % P1.replace("o", "\u03bf", 1), "private name",
     "a private name with one Greek omicron in it"),
    ("results/%s-run.json" % P1, '{"ok": true}\n', "private name", "a private name in a file NAME"),
    ("%s/readme.md" % P2, "clean\n", "private name", "a private name in a DIRECTORY name"),
]

# Must NOT be flagged: legitimate content that resembles the patterns. (path, contents, why)
MUST_PASS = [
    ("docs.md", "Set it with: export GROQ_API_KEY=...\nThen read $GROQ_API_KEY in the script.\n",
     "documenting the shape of a variable is not leaking a key"),
    ("docs2.md", "export GROQ_API_KEY=... CEREBRAS_API_KEY=...\nOPENROUTER_API_KEY=your-openrouter-key-here\n"
     "GROQ_API_KEY=<paste the key from the console>\n", "placeholders in every documented form"),
    ("ours.md", "Built by i-vory Studio, see https://github.com/i-voryStudio\n", "our own public profile link"),
    ("redacted.json", '{"error": "<account state redacted>"}\n', "already redacted, by design"),
    ("placeholder.md", "Write to noreply@example.com or user@host, someone@users.noreply.github.com, noreply@github.com\n",
     "placeholder addresses and the two GitHub no-reply forms"),
    (".github/workflows/pinned.yml", PINNED, "SHA-pinned actions: 40 hex characters after an @, not after an assignment"),
    ("url40.md", "https://github.com/i-voryStudio/live-free-llm-apis/blob/3d3c42e5aac5ba805825da76410c181273ba90b1/README.md\n"
     "https://huggingface.co/x/y/resolve/3d3c42e5aac5ba805825da76410c181273ba90b1/config.json\n",
     "a URL with a 40-hex path segment"),
    ("digest_labelled.md", "sha256: %s\nimage@sha256:%s\n" % (SHA256_HEX, SHA256_HEX),
     "a 64-hex value labelled as a hash, in both spellings"),
    ("hash96.md", "sha384: %s\n" % HEX96, "a 96-hex value labelled as a hash: the widened rule still reads the label"),
    ("wrapped_hash.md", "sha256sum of the file is %s\n%s (split by the editor)\n" % (SHA256_HEX[:32], SHA256_HEX[32:]),
     "a hash wrapped over two lines under a hash word: glued, then admitted by the word"),
    ("wrapped_prose.md", "the quick brown\nfoxes jumped over the lazy dogs again\n",
     "two prose lines whose join is two words, not a key"),
    ("models.json", '{"id": "Llama4Maverick17B128EInstructFP8", "model": "meta-llama/llama-4-scout-17b-16e-instruct",\n'
     ' "slug": "meta/llama4maverick17b128einstructfp8turbo2507preview",\n'
     ' "long": "Llama4Maverick17B128EInstructFP8Turbo2507PreviewLongName"}\n',
     "model ids that look like base64 or like random tokens"),
    ("note.md", "Note: we do not train on inputs, and a note about that is in privacy.json.\n",
     "a legitimate file with the word note in it"),
    ("results.json", '{"provider": "siliconflow", "http": 402, "error": "<account state redacted>", "ok": false}\n',
     "the provider's HTTP code, with no first-person state next to it"),
    ("per_key.md", "1000 requests/day per account, 8000 tokens per minute per key\n",
     "a limit stated per key is not a limit multiplied across keys"),
    ("generated.md", "Generated by `bench/rank.py` on **2026-09-07** - do not edit by hand.\n"
     "This is the whole argument for `data/catalog.json` being regenerated by CI rather\n"
     "- **The disagreement is published**, in `results/<date>/agreement.md`, generated by\n",
     "our own generator notes"),
    ("curl.md", 'curl -H "Authorization: Bearer $GROQ_API_KEY" -H "Authorization: Bearer ${OPENROUTER_API_KEY}"\n',
     "headers built from environment variables"),
    ("providers.json", '{"key_env": "OPENROUTER_API_KEY", "url": "https://openrouter.ai/api/v1/chat/completions", '
     '"max_tokens": 500, "needs_key": false}\n', "the provider table's own field names"),
    ("code.py", '        headers["Authorization"] = "Bearer " + key\n        if model_key:\n'
     '            by_model.setdefault(model_key, {})[v["lens"]] = v["score"]\n'
     'BALANCE = re.compile(r"(balance|insufficient\\s+funds|billing)", re.I)\n'
     'TOKENS_PER_REPLY = 500\n', "code that builds a header from a variable, and a key-named variable in an if"),
    ("max_tokens.py", '            "max_tokens": MAX_TOKENS_PER_CALL, "temperature": 0.7, **(extra_body or {})}\n',
     "a plural secret-word field holding a constant, not an array: the widening for plural fields stops here"),
    ("judges.json", '{"name": "claude", "model": "claude-opus-5", "family": "Anthropic Claude"}\n',
     "the jury's own model names"),
    ("jury_model.json", '{"model": "claude-opus-5", "via": "manual"}\n',
     "the jury's declared model id: a name without a verb of authorship after it"),
    ("jury_family.md", "The second judge's family is Anthropic Claude, declared in judges.json.\n",
     "the jury's declared family name in prose"),
    ("model_names.md", "openai/gpt-oss-120b, gemini-3.5-flash-lite and claude-opus-5 are model ids; Gemini 2.5 Flash is in "
     "the table; the copilot said nothing; Codex is a model family.\n",
     "model and product names with no verb of authorship and no credit in front of them"),
    ("headers.py", '    "x-ratelimit-remaining-requests-day": "x-ratelimit-remaining-requests-day",\n',
     "a long low-entropy header name after a colon"),
    ("headers_plain.md", "x-ratelimit-remaining-requests-day: <n>, x-ratelimit-limit-tokens-day: see the provider's table\n",
     "rate-limit header names with no number after them"),
    ("header_map.py", '    "cerebras": {"requests_left": "x-ratelimit-remaining-requests-day"},\n',
     "a header name as a mapping value: a name, not an echo"),
    # --- measurement provenance that describes the ENDPOINT: the subject is the provider, not the caller
    ("provenance.json", '{"measured_how": "rate-limit response headers on a free-trial key, read 2026-09-02 and again '
     '2026-09-07: x-ratelimit-limit-requests-day 2400, x-ratelimit-limit-tokens-day 1000000, 5 requests/minute. '
     'The figures held across five days."}\n',
     "provenance of a measured ceiling: the headers reported the endpoint's limits, in a sentence"),
    ("provenance.md", "- **Measured:** 2026-09-07, rate-limit response headers on a free-trial key reported "
     "x-ratelimit-limit-requests-day 2400 and x-ratelimit-limit-tokens 8000 per minute; they said "
     "x-ratelimit-limit-tokens-minute 625000 and the call returned a completion.\n",
     "the same provenance on a page, with the reporting verbs the pages use"),
    ("endpoint_answered.md", "Reachable on the coding-plan endpoint; the general paas/v4 endpoint answered HTTP 429 on "
     "2026-09-06. On 2026-09-07 the chat endpoint answered HTTP 402 Payment Required.\n",
     "an endpoint that answered a status code: a fact about the endpoint"),
    ("anonymous.json", '{"auth_measured_how": "The endpoint takes no credential, but the anonymous bucket is 2 requests '
     'per minute and it answered 429 with x-ratelimit-remaining-minute 0 on both attempts, 90 seconds apart."}\n',
     "a keyless endpoint's anonymous bucket read in prose: a word in front of the header, no account behind it"),
    ("headers_seen.json", '{"headers_seen": {\n    "x-ratelimit-limit": "5"\n  }}\n',
     "the ceiling header alone as a field, the shape limits.json keeps"),
    ("their_reading.md", "their sentence, not our reading; Mistral's free tier answered one of our calls with a ceiling; "
     "four of the five empty responses in our own run came from reasoning models; the model spent its whole "
     "token budget; to our credit the figure was published; a figure of 40 per key in our own notes.\n",
     "first-person words that are about the method, not the account"),
    ("credits_kind.md", "It covers both a recurring quota and credits that run out, and their headline provider count.\n",
     "credits that run out: a KIND of free tier, present tense, not ours"),
    ("not_reproducible.md", "manual - scored by hand through a chat interface. NOT reproducible by a stranger, and "
     "METHOD.md says so.\n", "a declared limitation of the method, not a fact about an account"),
    ("dollars.md", "Ten dollars a month of credits, and no published conversion into tokens. The generous number costs "
     "one dollar. A new account gets 10 trial calls. The one-time dollar underneath it.\n",
     "money words with no verb of consumption next to them"),
    ("doc_ips.md", "RFC 5737 gives 192.0.2.1, 198.51.100.7 and 203.0.113.42 for documentation; loopback is 127.0.0.1,\n"
     "LANs use 10.0.0.1, 172.16.5.5 and 192.168.1.1, link-local is 169.254.1.1, carrier NAT 100.64.0.1,\n"
     "multicast 224.0.0.1, broadcast 255.255.255.255, and 10.0.26200.1 is a build number, not an address\n",
     "documentation, private, loopback, link-local, shared, multicast and broadcast ranges, and a version string"),
    ("doc_ipv6.md", "RFC 3849 gives 2001:db8::1 and 2001:db8:85a3::8a2e:370:7334 for documentation, and 3fff::1 is the\n"
     "newer block; loopback is ::1, unspecified ::, link-local fe80::1, unique-local fd12:3456::1, multicast\n"
     "ff02::1; a MAC address is 00:1a:2b:3c:4d:5e, a time is 12:34:56, a stamp is 2026-09-07T00:05:00Z,\n"
     "a::b and ::2 are reserved, std::string is C++ and x[::2] is Python\n",
     "the IPv6 documentation, loopback, link-local, unique-local, multicast and reserved blocks, and the "
     "colon-separated things that are not addresses"),
    ("unc_doc.md", "a share is written \\\\server\\share in Windows; a protocol-relative link is //cdn.example/lib.js\n",
     "a UNC share with no user folder under it, and a protocol-relative link"),
    ("fixture.py", '[{"name": "inline", "url": "https://" + "user:pw" + "@" + "hermes.ai.unturf.com/v1/chat/completions"}]\n',
     "URL userinfo is not an email address"),
    ("CODEOWNERS", "/bench/gate_publish.py         @i-voryStudio\n", "a GitHub handle is not an address"),
    ("handle.md", "ping @someone. Then we continue.\n", "a handle followed by a full stop"),
    ("entities.md", "Tom &amp; Jerry, 5 &lt; 6, &copy; 2026, the &#8220;quoted&#8221; word\n",
     "HTML entities that decode to punctuation, not to a key"),
    ("docs/users-guide.md", "clean\n", "the word users in a name, with nothing slugified about it"),
    ("pic.jpeg", b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00\xff\xd9",
     "a genuine JPEG: binary, on the denylist, string-scanned, nothing found"),
    ("tiny.png", b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89",
     "a genuine PNG header: same"),
    ("real.png", REAL_PNG, "a complete PNG with no text chunk: binary, on the denylist, string-scanned, nothing found"),
    ("bundle.zip", ZIP_CLEAN, "a zip under its own name with a clean member: inflated, scanned, nothing found"),
    ("log.txt.gz", GZ_CLEAN, "a gzip stream under its own name with a clean line inside"),
]

_FINDING = re.compile(r"^  (\S.*?):(\d+)  (\S.*)$", re.M)
_HISTORY_FINDING = re.compile(r"^  [0-9a-f]{10} (\S.*?):(\d+)  (\S.*)$", re.M)


def run_gate(*args, gate=GATE):
    r = subprocess.run([sys.executable, str(gate)] + [str(a) for a in args],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def findings(out, pattern=_FINDING):
    return [(m.group(1).replace("\\", "/"), int(m.group(2)), m.group(3)) for m in pattern.finditer(out)]


def fired(got, rel):
    return sorted({r for f, _, r in got if f == rel or rel.startswith(f + "/")})


def hit(got, rel, rule, line=None):
    """True when `rule` fired on `rel`, on `line` if one is given."""
    return any(f == rel and r == rule and (line is None or n == line) for f, n, r in got)


def write(root, rel, body):
    f = Path(root) / rel
    f.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(body, bytes):
        f.write_bytes(body)
    else:
        f.write_text(body, encoding="utf-8", newline="\n")


def fixture(tmp):
    """Every fixture root carries the example private list, so the private-name cases have names."""
    (Path(tmp) / G.PRIVATE_LIST).write_text(EXAMPLE_LIST.read_text(encoding="utf-8"), encoding="utf-8")


def rule_known(name):
    base = name[:-len(", base64-decoded")] if name.endswith(", base64-decoded") else name
    return base in G.RULE_NAMES


def git_cmd(tmp, email="someone@some-company.ro"):
    return ["git", "-C", tmp, "-c", "user.name=Someone", "-c", "user.email=%s" % email,
            "-c", "commit.gpgsign=false", "-c", "core.autocrlf=false"]


def git(g, *args):
    subprocess.run(g + list(args), check=True, capture_output=True)


def main():
    failures = []
    total = len(MUST_CATCH) + len(MUST_PASS)

    def report(section, checks, detail=""):
        nonlocal total
        total += len(checks)
        for label, ok in checks:
            print("%s %s" % ("ok  " if ok else "FAIL", label))
            if not ok:
                failures.append((section, label, "see output", detail.strip()[:400]))

    # --- direction 0: every rule a case names must exist, or the case would fail forever and for
    #     the wrong reason.
    for rel, _, rule, _ in MUST_CATCH:
        if not rule_known(rule):
            failures.append(("unknown rule", rel, "case names a rule the gate does not have: %r" % rule, ""))

    # --- direction 1: every leak must be caught BY THE RULE NAMED, one fixture at a time so a single
    #     catch cannot mask the ones that were missed.
    print("=== must be CAUGHT, by the rule named (one file at a time) ===")
    for rel, body, rule, why in MUST_CATCH:
        with tempfile.TemporaryDirectory() as tmp:
            fixture(tmp)
            write(tmp, rel, body)
            code, out = run_gate(tmp)
            got = findings(out)
            ok = code == 1 and rule in fired(got, rel)
            print("%s %-30s [%s]  %s" % ("ok  " if ok else "MISS", rel, rule, why))
            if not ok:
                failures.append(("not caught", rel, "expected [%s], fired %s" % (rule, fired(got, rel) or "nothing"),
                                 out.strip()[:300]))

    # --- direction 2: legitimate content must not be flagged
    print("\n=== must PASS ===")
    with tempfile.TemporaryDirectory() as tmp:
        fixture(tmp)
        for rel, body, why in MUST_PASS:
            write(tmp, rel, body)
        code, out = run_gate(tmp)
        got = findings(out)
        for rel, _, why in MUST_PASS:
            bad = fired(got, rel)
            print("%s %-30s %s" % ("ok  " if not bad else "FALSE POSITIVE", rel, why))
            if bad:
                failures.append(("false positive", rel, "flagged as %s" % bad, ""))
        total += 2
        if code != 0 and not any(k == "false positive" for k, *_ in failures):
            failures.append(("false positive", "MUST_PASS set", "gate exited %d with no file blamed" % code,
                             out.strip()[:400]))
        # And the binaries, archives included, were read as binaries (strings, members), not counted as text.
        binaries = sum(1 for _, body, _ in MUST_PASS if isinstance(body, bytes))
        m = re.search(r"checked (\d+) text files .*?\((\d+) binary, strings only, (\d+) of them archives", out)
        if not m or int(m.group(2)) != binaries or int(m.group(3)) != 2:
            failures.append(("binary handling", "MUST_PASS set",
                             "expected %d files read as genuine binaries, 2 of them archives, got %s" %
                             (binaries, "%s / %s" % (m.group(2), m.group(3)) if m else "?"), ""))

    # --- direction 3: the real repo. The gate must open every file that is scannable by ITS OWN
    #     definition (same function, so the count and the gate cannot disagree), and it must pass. The
    #     gate and its test are among those files now, under the key rules.
    print("\n=== the real repo ===")
    code, out = run_gate(ROOT)
    checked = -1
    m = re.search(r"^checked (\d+) text files", out, re.M)
    if m:
        checked = int(m.group(1))
    on_disk = sum(1 for _, _, kind in G.scannable(ROOT) if kind == "text")
    print("     gate opened %d files, %d scannable text files on disk" % (checked, on_disk))
    total += 2
    if checked != on_disk:
        failures.append(("blind spot", "repo", "gate opened %d of %d files: the ones it skips are the ones a "
                         "leak hides in" % (checked, on_disk), ""))
        print("FAIL gate skipped %d files" % (on_disk - checked))
    else:
        print("ok   every scannable file opened")
    if code != 0:
        by_rule = {}
        for f, n, r in findings(out):
            by_rule.setdefault(r, []).append("%s:%d" % (f, n))
        detail = "\n".join("%s: %s" % (r, ", ".join(v[:6]) + (" ..." if len(v) > 6 else "")) for r, v in sorted(by_rule.items()))
        failures.append(("repo not clean", "repo", "the published repo must pass its own gate; this is a data "
                         "cleanup, not a gate defect, and the gate is not weakened to make it pass", detail))
        print("FAIL repo does not pass its own gate (%d findings)" % sum(len(v) for v in by_rule.values()))
    else:
        print("ok   repo clean")

    # --- direction 4: history mode, calibrated on the class it exists for. A scratch repo where the
    #     leaks were committed and then removed, so the working tree is clean and only the history
    #     knows; and a control repo with the provenance sentences the pages keep, which must stay CLEAN.
    #     Every planted line is assembled from pieces, and each is asserted by rule name and, where two
    #     shapes share a file, by line.
    print("\n=== history ===")
    leak_data = "\n".join((
        "{",
        ' "caveat": "Measured 2026-09-07, the key ' + 'returned 402 Payment Required, so that sign-up credit '
        + 'had already been consumed.",',
        ' "headers_seen": {',
        '  "x-ratelimit-' + 'remaining": "4"',
        " }",
        "}",
    )) + "\n"
    clean_data = "\n".join((
        "{",
        ' "measured_how": "rate-limit response headers on a free-trial key, read 2026-09-02 and again 2026-09-07: '
        'x-ratelimit-limit-requests-day 2400, x-ratelimit-limit-tokens-day 1000000, 5 requests/minute.",',
        ' "note": "the general paas/v4 endpoint answered HTTP 429 on 2026-09-06",',
        ' "headers_seen": {',
        '  "x-ratelimit-limit": "5"',
        " }",
        "}",
    )) + "\n"
    tooling_note = '{"how": "reached through our ' + 'own tooling. NOT reproducible by a stranger"}\n'
    header_echo = "x-ratelimit-" + "limit-tokens-day 1000000\n"
    leak_message = ("remove notes\n\nrotated " + FAKE_GROQ + " out of the notes\n\n"
                    + "Co-authored" + "-by: Some Tool <tool@" + "example.com>\n")
    with tempfile.TemporaryDirectory() as tmp:
        g = git_cmd(tmp)
        try:
            git(g, "init", "-q")
            write(tmp, "leak.md", "key: %s\n" % FAKE_GROQ)
            write(tmp, "data/limits.json", leak_data)
            write(tmp, "bench/judges.json", tooling_note)
            write(tmp, "notes.md", header_echo)
            git(g, "add", "leak.md", "data/limits.json", "bench/judges.json", "notes.md")
            git(g, "commit", "-q", "-m", "add notes")
            git(g, "rm", "-q", "leak.md", "bench/judges.json", "notes.md")
            write(tmp, "data/limits.json", clean_data)
            git(g, "add", "data/limits.json")
            git(g, "commit", "-q", "-m", leak_message)
            ok_git = True
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            ok_git = False
            failures.append(("history", "scratch repo", "git is needed for this check and failed: %s" % e, ""))
        if ok_git:
            code_tree, _ = run_gate(tmp)
            code_hist, out_hist = run_gate("--history", tmp)
            got = findings(out_hist, _HISTORY_FINDING)
            account = "account state, first person"
            report("history", [
                ("working tree is clean after the delete", code_tree == 0),
                ("history exits 1", code_hist == 1),
                ("deleted key found in the patch", hit(got, "leak.md", "key: Groq shape")),
                ("account-state sentence in a data file, committed then removed", hit(got, "data/limits.json", account, 2)),
                ("JSON x-ratelimit-remaining field in the same file", hit(got, "data/limits.json", account, 4)),
                ("our-own-tooling note", hit(got, "bench/judges.json", account, 1)),
                ("header echo on a line of its own", hit(got, "notes.md", account, 1)),
                ("key in a commit message", hit(got, "(message)", "key: Groq shape")),
                ("trailer in a commit message", hit(got, "(message)", "assistant trace")),
                ("author address on a private domain", hit(got, "(author)", "private email")),
                ("the clean replacement of the data file is not blamed",
                 not any(f == "data/limits.json" and n > 4 for f, n, _ in got)),
            ], out_hist)
    with tempfile.TemporaryDirectory() as tmp:
        g = git_cmd(tmp, email="someone@users.noreply.github.com")
        try:
            git(g, "init", "-q")
            write(tmp, "data/limits.json", clean_data)
            write(tmp, "README.md", "Measured from rate-limit headers; the endpoint answered HTTP 429 once.\n")
            git(g, "add", "data/limits.json", "README.md")
            git(g, "commit", "-q", "-m", "add the measured limits, with their provenance")
            ok_git = True
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            ok_git = False
            failures.append(("history", "control repo", "git is needed for this check and failed: %s" % e, ""))
        if ok_git:
            code_tree, out_tree = run_gate(tmp)
            code_hist, out_hist = run_gate("--history", tmp)
            report("history", [
                ("control repo: working tree is clean", code_tree == 0),
                ("control repo: history with provenance sentences and a no-reply author is CLEAN", code_hist == 0),
            ], out_tree + out_hist)

    # --- direction 5: the fingerprint round-trip, and the shipped file is what the gate expects.
    print("\n=== fingerprints ===")
    with tempfile.TemporaryDirectory() as tmp:
        names = EXAMPLE_NAMES + ["Two Word Name", "secret-deck.json"]
        write(tmp, "names.txt", "# comment\n\n" + "\n".join(names) + "\n")
        out_json = Path(tmp) / "fp.json"
        code, out = run_gate("--fingerprint", Path(tmp) / "names.txt", "--out", out_json)
        ok = code == 0 and out_json.is_file()
        fps = set(json.loads(out_json.read_text(encoding="utf-8"))["fingerprints"]) if ok else set()
        checks = [
            ("--fingerprint writes the file", ok),
            ("every name is in it, normalised, with the stems of dotted names", fps == G.fingerprints_for(names)),
            ("a hyphenated form of a two-word name matches", bool(G.private_hits("see two-word-name here", fps))),
            ("the bare stem of a dotted name matches", bool(G.private_hits("the secret-deck slides", fps))),
            ("a lookalike spelling matches", bool(G.private_hits("see tw\u043e-w\u03bfrd-name here", fps))),
            ("an unrelated line does not", not G.private_hits("nothing to see here", fps)),
            ("a name glued into a longer run does not, and the docstring says so",
             not G.private_hits("twowordnamev2", fps) and bool(re.search(r"glued\s+into\s+a\s+longer", G.__doc__))),
        ]
        # No fingerprint file is published: a truncated hash confirms a guess for anyone holding a
        # candidate list, and a short name falls to an offline search. The names and their fingerprints
        # stay on the machine that has .gate-private; CI runs without them and says so.
        checks.append(("no fingerprint file ships with the repo", not G.FINGERPRINTS.is_file()))
        with tempfile.TemporaryDirectory() as bare:
            write(bare, "README.md", "nothing private here" + chr(10))
            code_b, out_b = run_gate(bare)
            checks.append(("a checkout with no .gate-private scans clean and says the rule was off",
                           code_b == 0 and "private-name rule: off" in out_b))
        report("fingerprints", checks, out)

    # --- direction 6: the gate and its test are scanned with the key rules, so a key pasted into either
    #     is caught, while the phrase fixtures they carry by construction do not fire. Run on a COPY of
    #     both files, by the copy's own gate, so the exemption resolves to the copy.
    print("\n=== the gate and its test, under the key rules ===")
    with tempfile.TemporaryDirectory() as tmp:
        fixture(tmp)
        (Path(tmp) / "bench").mkdir()
        for f in ("gate_publish.py", "test_gate.py"):
            shutil.copy(HERE / f, Path(tmp) / "bench" / f)
        copy_gate = Path(tmp) / "bench" / "gate_publish.py"
        code0, out0 = run_gate(tmp, gate=copy_gate)
        with open(Path(tmp) / "bench" / "test_gate.py", "a", encoding="utf-8", newline="\n") as fh:
            fh.write("\nLIVE = %r\n" % FAKE_GROQ)
        with open(copy_gate, "a", encoding="utf-8", newline="\n") as fh:
            fh.write("\n# %s\n" % FAKE_OPENAI)
        code1, out1 = run_gate(tmp, gate=copy_gate)
        got = findings(out1)
        phrase_rules = {"assistant trace", "account state, first person", "private email", "private name",
                        "high-entropy string after assignment", "Windows user path", "UNC user path",
                        "public IPv4 address", "public IPv6 address", "base64 blob after assignment or echo"}
        with open(Path(tmp) / G.PRIVATE_LIST, "a", encoding="utf-8", newline="\n") as fh:
            fh.write("\n%s\n" % FAKE_GROQ)
        code2, out2 = run_gate(tmp, gate=copy_gate)
        got2 = findings(out2)
        report("exempt files", [
            ("the current gate and test pass the key rules", code0 == 0),
            ("the two files are counted as opened", "2 with key rules only" in out0 or "3 with key rules only" in out0),
            ("a key pasted into the test is caught", "key: Groq shape" in fired(got, "bench/test_gate.py")),
            ("a key pasted into the gate is caught", "key: OpenAI or OpenRouter shape" in fired(got, "bench/gate_publish.py")),
            ("the phrase fixtures inside them still do not fire",
             not (set(fired(got, "bench/test_gate.py")) | set(fired(got, "bench/gate_publish.py"))) & phrase_rules),
            ("a key-shaped line in the private list is caught", "key: Groq shape" in fired(got2, G.PRIVATE_LIST)),
        ], out0 + out1 + out2)

    # --- direction 7: the private list is scanned even though git ignores it, and refused if git tracks it.
    print("\n=== the private list ===")
    with tempfile.TemporaryDirectory() as tmp:
        g = git_cmd(tmp)
        try:
            git(g, "init", "-q")
            write(tmp, ".gitignore", "%s\n" % G.PRIVATE_LIST)
            write(tmp, G.PRIVATE_LIST, EXAMPLE_LIST.read_text(encoding="utf-8") + "secret-deck.json\n")
            write(tmp, "notes.md", "the secret-deck slides\n")
            git(g, "add", ".gitignore", "notes.md")
            git(g, "commit", "-q", "-m", "notes")
            code_a, out_a = run_gate(tmp)
            got_a = findings(out_a)
            git(g, "add", "-f", G.PRIVATE_LIST)
            git(g, "commit", "-q", "-m", "oops")
            code_b, out_b = run_gate(tmp)
            got_b = findings(out_b)
            code_h, out_h = run_gate("--history", tmp)
            got_h = findings(out_h, _HISTORY_FINDING)
            report("private list", [
                ("an ignored private list is not refused", "private list tracked by git" not in fired(got_a, G.PRIVATE_LIST)),
                ("the stem of a dotted name in it is caught in content", "private name" in fired(got_a, "notes.md")),
                ("a force-added private list is refused", code_b == 1 and "private list tracked by git" in fired(got_b, G.PRIVATE_LIST)),
                ("the history sees the commit that carries it",
                 code_h == 1 and any(f == G.PRIVATE_LIST and r == "private list tracked by git" for f, _, r in got_h)),
            ], out_a + out_b + out_h)
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            failures.append(("private list", "scratch repo", "git is needed for this check and failed: %s" % e, ""))

    print("\n%d checks, %d failures" % (total, len(failures)))
    for kind, where, why, detail in failures:
        print("  [%s] %s - %s" % (kind, where, why))
        if detail:
            print("      %s" % detail.replace("\n", "\n      "))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
