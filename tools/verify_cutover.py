#!/usr/bin/env python3
"""WS-SITE22 DNS-cutover verifier for horsepowercoaching.co.uk -> Netlify.

Run at cutover time (see docs/runbooks/dns-cutover.md). Read-only: it resolves
DNS and makes GET requests, and changes nothing. Dependencies: the Python
standard library plus the system `curl` binary, nothing else.

Usage:
    python3 tools/verify_cutover.py [hostname]

`hostname` (default horsepowercoaching.co.uk) is the HTTP endpoint whose content,
redirects and SEO files are checked. It lets you validate the Netlify preview
BEFORE the DNS change:

    python3 tools/verify_cutover.py horsepower-coaching.netlify.app

The DNS checks (apex A record, www CNAME) always target the production cutover
domain horsepowercoaching.co.uk, because that is the thing being cut over. So:

  * Pre-cutover, against the Netlify preview host: every HTTP check PASSes and only
    the two apex-DNS checks FAIL (the apex still points at GoDaddy). That is the
    expected pre-flight result.
  * Post-cutover, against horsepowercoaching.co.uk: everything PASSes.

Exit code is non-zero if ANY check fails.
"""
import os
import socket
import subprocess
import sys
from urllib.parse import urlparse

# The production domain the cutover is FOR (DNS checks always target this).
PROD_HOST = "horsepowercoaching.co.uk"
PROD_ORIGIN = "https://" + PROD_HOST
GITHUB_IO = "tomcooling-cpu.github.io"          # the preview host must NOT leak into prod SEO
NETLIFY_APEX_IP = "75.2.60.5"                    # Netlify load balancer (apex A record)
NETLIFY_APP = "horsepower-coaching.netlify.app"  # www CNAME target
CURL_TIMEOUT = "20"

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
REDIRECTS = os.path.join(REPO, "site", "_redirects")

_results = []


def record(ok, label, detail=""):
    _results.append(bool(ok))
    tag = "PASS" if ok else "FAIL"
    line = f"  [{tag}] {label}"
    if detail:
        line += f"  ({detail})"
    print(line)


def curl(url, follow=False, head_only=True):
    """Return (returncode, http_code, redirect_url, body). curl validates the TLS
    certificate by default (no -k), so an invalid cert makes this fail."""
    fmt = "%{http_code} %{redirect_url}"
    cmd = ["curl", "-sS", "--max-time", CURL_TIMEOUT, "-w", fmt]
    if follow:
        cmd.append("-L")
    if head_only:
        cmd += ["-o", os.devnull]
    cmd.append(url)
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=int(CURL_TIMEOUT) + 5)
    except Exception as exc:
        return (1, "000", "", f"curl error: {exc}")
    out = p.stdout
    body = ""
    if not head_only:
        # body precedes the write-out format on the last line
        idx = out.rfind("\n")
        body, tail = (out[:idx], out[idx + 1:]) if idx >= 0 else ("", out)
    else:
        tail = out.strip().splitlines()[-1] if out.strip() else ""
    parts = tail.split()
    code = parts[0] if parts else "000"
    redirect = parts[1] if len(parts) > 1 else ""
    return (p.returncode, code, redirect, body)


def check_dns():
    print("DNS (production apex, cutover target %s):" % PROD_HOST)
    # Apex A record -> Netlify load balancer 75.2.60.5
    try:
        _name, _aliases, ips = socket.gethostbyname_ex(PROD_HOST)
        record(NETLIFY_APEX_IP in ips, f"apex {PROD_HOST} A -> {NETLIFY_APEX_IP}",
               "got " + ", ".join(ips))
    except OSError as exc:
        record(False, f"apex {PROD_HOST} A -> {NETLIFY_APEX_IP}", str(exc))
    # www CNAME -> horsepower-coaching.netlify.app (stdlib exposes the CNAME chain
    # via the canonical name + alias list returned by gethostbyname_ex).
    www = "www." + PROD_HOST
    try:
        canon, aliases, _ips = socket.gethostbyname_ex(www)
        chain = " ".join([canon] + list(aliases)).lower()
        record(NETLIFY_APP in chain, f"www {www} CNAME -> {NETLIFY_APP}",
               "chain: " + chain)
    except OSError as exc:
        record(False, f"www {www} CNAME -> {NETLIFY_APP}", str(exc))


def load_godaddy_redirects():
    """The 11 GoDaddy-era 301s from site/_redirects (blog-slug 301s excluded; the
    blog is checked separately). Reuses the shipped map, so this never drifts."""
    pairs = []
    with open(REDIRECTS, encoding="utf-8") as fh:
        for raw in fh:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            if len(parts) == 3 and parts[2] == "301" and not parts[0].startswith("/blog"):
                pairs.append((parts[0], parts[1]))
    return pairs


def check_http(host):
    base = "https://" + host
    print("HTTPS + content (%s):" % base)

    rc, code, _r, _b = curl(base + "/", head_only=True)
    record(rc == 0 and code == "200", "https:// serves 200 with a valid certificate",
           f"curl rc={rc}, HTTP {code}")

    rc, code, _r, body = curl(base + "/", head_only=False)
    low = body.lower()
    record("Plan Store" in body and "oswald" in low and "woff2" in low,
           "/ serves the new site (\"Plan Store\" + oswald woff2 font)",
           f"Plan Store={'Plan Store' in body}, oswald woff2={'oswald' in low and 'woff2' in low}")

    print("GoDaddy-era 301 redirects:")
    redirects = load_godaddy_redirects()
    record(len(redirects) == 11, "found the 11 GoDaddy 301 rules in site/_redirects",
           f"found {len(redirects)}")
    for src, target in redirects:
        rc, code, redirect, _b = curl(base + src, head_only=True)
        dest_path = urlparse(redirect).path if redirect else ""
        ok = rc == 0 and code in ("301", "308") and dest_path == target
        record(ok, f"301 {src} -> {target}", f"HTTP {code} -> {redirect or '(none)'}")

    print("Blog slug + SEO files:")
    rc, code, _r, _b = curl(base + "/blog/f/everesting---climbing-the-mountain",
                            follow=True, head_only=True)
    record(rc == 0 and code == "200", "/blog/f/everesting---climbing-the-mountain resolves",
           f"HTTP {code}")

    for path in ("/robots.txt", "/sitemap.xml", "/llms.txt"):
        rc, code, _r, _b = curl(base + path, head_only=True)
        record(rc == 0 and code == "200", f"{path} serves 200", f"HTTP {code}")

    rc, code, _r, body = curl(base + "/sitemap.xml", head_only=False)
    record(PROD_ORIGIN in body and GITHUB_IO not in body,
           "sitemap URLs use the production host (no preview host)",
           f"prod host={PROD_ORIGIN in body}, github.io leak={GITHUB_IO in body}")


def main():
    host = sys.argv[1] if len(sys.argv) > 1 else PROD_HOST
    print(f"Cutover verification: HTTP host = {host}, DNS target = {PROD_HOST}\n")
    check_dns()
    print()
    check_http(host)
    print()
    passed = sum(1 for r in _results if r)
    failed = sum(1 for r in _results if not r)
    print(f"Summary: {passed} passed, {failed} failed, {len(_results)} total.")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
