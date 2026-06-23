#!/usr/bin/env python3
"""PQC-readiness scanner.

Checks whether TLS endpoints negotiate post-quantum (hybrid) key exchange,
fall back to classical-only, or can be silently downgraded.

Threat model: harvest-now-decrypt-later. An endpoint that still negotiates
only classical key exchange (X25519, P-256) is recordable today and
decryptable once a cryptographically relevant quantum computer exists. An
endpoint that *can* do PQC but does not negotiate it by default is a sign of
an incomplete or misconfigured migration.

This is a measurement tool, not an attack tool. It only completes normal TLS
handshakes against hosts you give it.

Requires an OpenSSL that knows PQC groups (OpenSSL 3.5+ or an OQS-enabled
build) for PQC detection; classical detection works with any modern OpenSSL.
"""
import argparse
import json
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, asdict, field

# TLS 1.3 named groups, normalized (lowercase, alphanumeric only).
_CLASSICAL = {
    "x25519", "x448", "secp256r1", "secp384r1", "secp521r1", "prime256v1",
    "ffdhe2048", "ffdhe3072", "ffdhe4096", "p256", "p384", "p521",
}
_PQC = {
    "x25519mlkem768", "secp256r1mlkem768", "secp384r1mlkem1024",
    "x25519kyber768draft00", "x25519kyber768", "p256kyber768",
    "mlkem512", "mlkem768", "mlkem1024",
    "kyber512", "kyber768", "kyber1024",
}

# Groups we offer when probing whether a host supports PQC at all (OpenSSL 3.5+ names).
_PQC_OFFER = "X25519MLKEM768:SecP256r1MLKEM768:X448MLKEM1024"


def _norm(group: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (group or "").lower())


def classify(group: str) -> str:
    """Classify a negotiated TLS group name as pqc-hybrid, classical, or unknown."""
    n = _norm(group)
    if not n:
        return "unknown"
    if "mlkem" in n or "kyber" in n or n in _PQC:
        return "pqc-hybrid"
    if n in _CLASSICAL:
        return "classical"
    return "unknown"


def _run_openssl(host: str, port: int, openssl: str, groups: str | None, timeout: int):
    cmd = [openssl, "s_client", "-connect", f"{host}:{port}", "-servername", host, "-tls1_3"]
    if groups:
        cmd += ["-groups", groups]
    try:
        p = subprocess.run(
            cmd, input=b"", capture_output=True, timeout=timeout
        )
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        return None, str(e)
    return (p.stdout + p.stderr).decode("utf-8", "replace"), None


def _parse_group(text: str) -> str:
    # OpenSSL 3.x: "Negotiated TLS1.3 group: X25519MLKEM768"
    m = re.search(r"Negotiated TLS1\.3 group:\s*(\S+)", text)
    if m:
        return m.group(1)
    # Fallback: "Peer Temp Key: X25519, 253 bits" or "Peer Temp Key: ECDH, prime256v1, 256 bits"
    m = re.search(r"(?:Peer|Server) Temp Key:\s*(.+)", text)
    if m:
        parts = [p.strip() for p in m.group(1).split(",")]
        for p in parts:
            if re.search(r"[A-Za-z]", p) and "bit" not in p.lower() and p.upper() != "ECDH":
                return p
        return parts[0]
    return ""


@dataclass
class Result:
    host: str
    port: int
    default_group: str = ""
    default_class: str = "unknown"
    supports_pqc: bool = False
    verdict: str = ""
    error: str = ""


def scan_host(host: str, port: int = 443, openssl: str = "openssl", timeout: int = 15) -> Result:
    r = Result(host=host, port=port)
    text, err = _run_openssl(host, port, openssl, None, timeout)
    if err:
        r.error = err
        r.verdict = "ERROR"
        return r
    r.default_group = _parse_group(text)
    r.default_class = classify(r.default_group)

    if r.default_class == "pqc-hybrid":
        r.supports_pqc = True
    else:
        # Offer PQC groups explicitly and see if the host will negotiate one.
        text2, err2 = _run_openssl(host, port, openssl, _PQC_OFFER, timeout)
        if not err2 and classify(_parse_group(text2)) == "pqc-hybrid":
            r.supports_pqc = True

    if r.default_class == "pqc-hybrid":
        r.verdict = "MIGRATED (negotiates PQC by default)"
    elif r.supports_pqc:
        r.verdict = "PARTIAL (PQC available but classical negotiated by default / downgradeable)"
    elif r.default_class == "classical":
        r.verdict = "CLASSICAL ONLY (exposed to harvest-now-decrypt-later)"
    else:
        r.verdict = "UNKNOWN (could not determine group)"
    return r


def main(argv=None):
    ap = argparse.ArgumentParser(description="Scan TLS hosts for post-quantum readiness.")
    ap.add_argument("hosts", nargs="*", help="host or host:port (or use --file)")
    ap.add_argument("--file", help="file with one host[:port] per line")
    ap.add_argument("--openssl", default=shutil.which("openssl") or "openssl")
    ap.add_argument("--json", action="store_true", help="emit JSON instead of a table")
    ap.add_argument("--timeout", type=int, default=15)
    args = ap.parse_args(argv)

    targets = list(args.hosts)
    if args.file:
        with open(args.file) as fh:
            targets += [ln.strip() for ln in fh if ln.strip() and not ln.startswith("#")]
    if not targets:
        ap.error("give at least one host or --file")

    results = []
    for t in targets:
        host, _, port = t.partition(":")
        results.append(scan_host(host, int(port) if port else 443, args.openssl, args.timeout))

    if args.json:
        print(json.dumps([asdict(r) for r in results], indent=2))
    else:
        w = max((len(r.host) for r in results), default=4)
        print(f"{'HOST':<{w}}  {'DEFAULT GROUP':<20} {'PQC?':<5} VERDICT")
        for r in results:
            print(f"{r.host:<{w}}  {r.default_group or '-':<20} {('yes' if r.supports_pqc else 'no'):<5} {r.verdict}")
    # Exit non-zero if any host is classical-only, for CI gating.
    return 1 if any(r.default_class == "classical" and not r.supports_pqc for r in results) else 0


if __name__ == "__main__":
    sys.exit(main())
