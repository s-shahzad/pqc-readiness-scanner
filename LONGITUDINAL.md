# Longitudinal re-scan log

Same methodology as the baseline throughout: `pqc_scan.py`, single vantage,
8 s timeout, OpenSSL 3.5.6, default probe + PQC capability probe.

## T0 — baseline (2026-06-25)

- OT/IoT/critical-infrastructure: N=124 (`seed-ot-iot.json`, `seed-ot-iot-2.json`, `seed-ot-iot-3.json`)
  - 49 migrated / 55 classical-only / 20 unknown
- Web calibration: N=40 (`scan-results.json`)
  - 21 migrated / 16 classical-only / 3 unknown

## T1 — 2026-07-02 (T0 + 7 days)

Files: `rescan-ot-iot-2026-07-02.json`, `rescan-web-2026-07-02.json`
(web host list extracted to `web-hosts.txt`).

- OT/IoT: 123/124 verdicts unchanged. Single change: `aspentech.com`
  CLASSICAL -> UNKNOWN (no negotiated group returned within the probe
  window; a vantage/timeout artifact, not evidence of migration).
- Web: 40/40 verdicts unchanged.

**Observations**

1. Zero post-quantum migrations observed in either population over one week.
   Every classical-only host at T0, including the industrial-automation
   vendor cohort and the cryptography-authority sites (nist.gov,
   openssl.org), remained classical-only at T1.
2. Verdict stability of 99.4% (163/164) across independent runs a week apart
   supports the reproducibility of the single-vantage handshake methodology;
   the one flip was in the direction of measurement noise (UNKNOWN), not a
   classification change between migrated and classical.

Next re-scan: monthly cadence (~2026-08-01) unless a major vendor announces
a migration.
