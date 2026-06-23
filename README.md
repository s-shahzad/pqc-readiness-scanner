# pqc-readiness-scanner

A small measurement tool that checks whether TLS endpoints have actually moved
to post-quantum key exchange, or only look like they have.

It answers one question for a fleet of hosts: when these endpoints negotiate a
TLS 1.3 connection, do they use a post-quantum hybrid key exchange (for example
X25519MLKEM768), do they fall back to classical-only (X25519, P-256), or can
they be downgraded to classical even though they support PQC?

## Why this exists

The migration to post-quantum cryptography is not one switch. A standard ships,
and then thousands of servers, load balancers, and embedded devices have to be
reconfigured, most of them by people who are not cryptographers. The interesting
security failures are not in the schemes. They are in the rollout: a host that
was supposed to migrate but still negotiates classical key exchange, a hybrid
handshake that silently downgrades, a fleet where half the nodes moved and half
did not.

The threat is harvest-now-decrypt-later. Traffic that uses only classical key
exchange today can be recorded now and decrypted later by an adversary with a
quantum computer. So "did the migration actually happen, everywhere" is a real,
measurable security question, and almost nobody is measuring it.

## What it does

For each host it:

1. Completes a normal TLS 1.3 handshake and records the negotiated group.
2. If that group is classical, offers PQC groups explicitly to see whether the
   host *could* have negotiated PQC (a sign of an incomplete or downgradeable
   migration).
3. Prints a per-host verdict: MIGRATED, PARTIAL (downgradeable), CLASSICAL ONLY,
   or UNKNOWN.

It is a measurement tool, not an attack tool. It only completes ordinary
handshakes against hosts you supply.

## Usage

```
python pqc_scan.py cloudflare.com google.com
python pqc_scan.py --file examples/hosts.txt --json
```

Exit code is non-zero if any host is classical-only, so it can gate a CI
pipeline ("fail the build if any endpoint in our fleet has not migrated").

## Requirements

- Python 3.10+
- OpenSSL on PATH. PQC detection needs OpenSSL 3.5+ or an OQS-enabled build;
  classical detection works with any modern OpenSSL. The `--openssl` flag points
  at a specific binary.

## Limitations (honest)

- v0.1 covers TLS over TCP. SSH, IKE/IPsec, and OT/IoT protocols (OCPP, MQTT)
  are on the roadmap, not done.
- PQC group names are still settling across stacks; the classifier treats any
  group containing `mlkem` or `kyber` as PQC and keeps an explicit allow-list.
- It reports what is negotiated, not whether the rest of the certificate chain
  or signatures are post-quantum.

## Roadmap

- CBOM output (cryptographic bill of materials) per host.
- SSH and IKE probes.
- Passive mode: classify PQC readiness from a pcap instead of active probing.
- A small dataset of real-world PQC adoption over time.

## Author

Azhad Shahzad Shaik (shaikazhadshahzad@gmail.com) · ORCID 0009-0009-6450-5837

## License

MIT. See LICENSE.
