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

Anywhere a key can be attached, use `open_url(...)` and never `urllib.request.urlopen`.
"""
import urllib.error
import urllib.request
from urllib.parse import urlparse


class NoCrossHostRedirect(urllib.request.HTTPRedirectHandler):
    """Refuse a redirect that changes host."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if urlparse(newurl).hostname != urlparse(req.full_url).hostname:
            raise urllib.error.URLError(
                "refused redirect to a different host (%s -> %s): the API key travels in the header"
                % (urlparse(req.full_url).hostname, urlparse(newurl).hostname))
        return super().redirect_request(req, fp, code, msg, headers, newurl)


OPENER = urllib.request.build_opener(NoCrossHostRedirect)


def open_url(req, timeout):
    """urlopen, minus the cross-host redirect. Raises URLError rather than following one."""
    return OPENER.open(req, timeout=timeout)
