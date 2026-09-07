#!/usr/bin/env python3
"""The one opener every script here uses when a credential can be attached to the request.

WHY THIS FILE EXISTS

`urllib` keeps the `Authorization` header across a 302. So a provider - or anyone able to answer for
one, including whoever holds a lapsed domain - can bounce our request to a server of their choosing and
be handed the API key. The host allowlist checks where we AIM; this checks where we LAND, and without
both, the allowlist is decoration.

`benchmark.py` has had this protection since the first day. `probe_alive.py`, `judge.py` and
`measure_limits.py` did not: all three called plain `urllib.request.urlopen`, all three attach a key,
and `probe_alive.py` runs daily. Three of the four doors were locked. The rule now lives in one file
so there is one door to lock, and `test_probes.py` checks it is still locked.

WHAT "A DIFFERENT PLACE" MEANS. The first version compared hostnames only, and that left two doors
open on the same host: a redirect from https to http on api.example would have been followed with the
key in a cleartext header, and a redirect to another port would have reached whatever listens there.
The destination is the whole origin - scheme, host and port - and a redirect that changes any of the
three is refused.

The same rule applies where we AIM, not only where we land: `gate_contributions.py` refuses a
provider URL that writes a port at all, through `written_port` below, because the runners speak to the
default port only and another listener on an allowed host is another party.

Anywhere a key can be attached, use `open_url(...)` and never `urllib.request.urlopen`.
"""
import urllib.error
import urllib.request
from urllib.parse import urlparse

DEFAULT_PORT = {"https": 443, "http": 80}


def origin_of(url):
    """(scheme, host, port) - the three things that decide who receives the request."""
    u = urlparse(url)
    try:
        port = u.port
    except ValueError:
        port = -1   # a port that does not parse is a destination that does not match anything
    return (u.scheme.lower(), (u.hostname or "").lower(), port or DEFAULT_PORT.get(u.scheme.lower()))


def written_port(url):
    """The port as WRITTEN in the URL: None when none is written, the number when one is, and -1 when
    what is written does not parse as one. `https://api.example:443/` returns 443, not None: the
    origin is the same, but somebody typed a port, and a contributed endpoint has no reason to."""
    try:
        return urlparse(url).port
    except ValueError:
        return -1


class NoCrossHostRedirect(urllib.request.HTTPRedirectHandler):
    """Refuse a redirect that changes scheme, host or port."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        here, there = origin_of(req.full_url), origin_of(newurl)
        if here != there:
            raise urllib.error.URLError(
                "refused redirect to a different origin (%s://%s:%s -> %s://%s:%s): the API key travels "
                "in the header" % (here + there))
        return super().redirect_request(req, fp, code, msg, headers, newurl)


OPENER = urllib.request.build_opener(NoCrossHostRedirect)


def open_url(req, timeout):
    """urlopen, minus the cross-origin redirect. Raises URLError rather than following one."""
    return OPENER.open(req, timeout=timeout)
