"""Fast regression tests (a subset of the full audit; run the audit for the
complete gate tables): python3 -m pytest tests/ -q"""
import random

from cram_fhe import (
    SAFE_BASIS, M_SHELL, A_ANCHOR, CRAMState, ArrowMonitor,
    k_eliminate, universal_projection, ToyBFV, inv_mod,
)
from cram_fhe.substrate import RANGE, M_INV_MOD_A
from cram_fhe.toy_bfv import DELTA, T_PLAIN

rng = random.Random(1)


def test_star_inverse_read_off_construction():
    assert (M_SHELL * M_INV_MOD_A) % A_ANCHOR == 1
    # and it agrees with extended Euclid without being computed by it
    assert M_INV_MOD_A == inv_mod(M_SHELL, A_ANCHOR)


def test_k_elimination_sound():
    for _ in range(2000):
        x = rng.randrange(RANGE)
        assert k_eliminate(x % M_SHELL, x % A_ANCHOR) == x // M_SHELL


def test_state_roundtrip_and_projection():
    for _ in range(500):
        x = rng.randrange(RANGE)
        s = CRAMState.from_int(x)
        assert s.to_int() == x
        assert s.project(97) == x % 97
        assert s.project(39) == x % 39      # shared-factor target lane


def test_ops_match_integer_semantics():
    for _ in range(500):
        x = rng.randrange(M_SHELL)
        y = rng.randrange(M_SHELL)
        c = rng.randrange(1, 50)
        sx, sy = CRAMState.from_int(x), CRAMState.from_int(y)
        assert sx.add(sy).to_int() == x + y
        assert sx.mul_int(c).to_int() == x * c
        assert sx.succ().to_int() == x + 1


def test_overflow_guard_trips():
    s = CRAMState.from_int(RANGE - 1)
    try:
        s.succ()
    except OverflowError:
        return
    raise AssertionError("frame overflow not guarded")


def test_bfv_exact_roundtrip_under_monitor():
    scheme = ToyBFV(seed=7)
    monitor = ArrowMonitor()
    for _ in range(60):
        m1, m2 = rng.randrange(T_PLAIN), rng.randrange(T_PLAIN)
        c = rng.randrange(0, 12)
        ct = ToyBFV.mul_plain(ToyBFV.add(scheme.encrypt(m1), scheme.encrypt(m2), monitor),
                              c, monitor)
        assert ct.exactness_guaranteed()
        assert scheme.decrypt(ct) == ((m1 + m2) * c) % T_PLAIN
    assert monitor.clean


def test_successor_reversible_zero_shadow_entropy():
    seen = set()
    for x in range(2 * M_SHELL):
        s = CRAMState.from_int(x).succ()
        key = (s.gamma, s.k)
        assert key not in seen
        seen.add(key)
