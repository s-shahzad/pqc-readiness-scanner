import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pqc_scan import classify  # noqa: E402


def test_pqc_hybrid():
    assert classify("X25519MLKEM768") == "pqc-hybrid"
    assert classify("SecP256r1MLKEM768") == "pqc-hybrid"
    assert classify("x25519_kyber768") == "pqc-hybrid"
    assert classify("X25519Kyber768Draft00") == "pqc-hybrid"


def test_classical():
    assert classify("X25519") == "classical"
    assert classify("secp256r1") == "classical"
    assert classify("P-256") == "classical"


def test_unknown():
    assert classify("") == "unknown"
    assert classify("totally-made-up") == "unknown"


if __name__ == "__main__":
    test_pqc_hybrid()
    test_classical()
    test_unknown()
    print("all classifier tests passed")
