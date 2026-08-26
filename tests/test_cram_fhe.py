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


# ── cross-validation against NINE65_v7 production semantics ──────────────
# Mirrors crates/nine65/src/arithmetic/k_elimination.rs::adjacency_tests and
# crates/exact_transcendentals/src/cram_anchor.rs.

def test_adjacency_sign_is_minus_not_plus():
    """Port of the pinned NINE65_v7 regression: the published anchor read
    (gamma + K) mod A is a sign error; the winding read is gamma - K.  The
    wrong form must MEASURABLY disagree (nonzero count, so the test can never
    go vacuous), and the general projection (gamma + K*M) mod A must always
    agree with ground truth."""
    disagree = 0
    for x in list(range(0, 3 * M_SHELL, 7)) + [RANGE - 1, RANGE // 2]:
        r, k = x % M_SHELL, x // M_SHELL
        wrong = (r + k) % A_ANCHOR
        right_minus = (r - k) % A_ANCHOR
        right_general = universal_projection(r, k, A_ANCHOR)
        assert right_minus == x % A_ANCHOR
        assert right_general == x % A_ANCHOR
        if wrong != x % A_ANCHOR:
            disagree += 1
    assert disagree > 0, "wrong form never disagreed — test went vacuous"


def test_adjacency_exhaustive_small_fixture():
    """Exhaustive [3,5,7] fixture from k_elimination.rs: M'=105, A'=106,
    every X in [0, M'*A'): derived K equals floor(X/M') and X reconstructs."""
    mp, ap = 105, 106
    for x in range(mp * ap):
        k = (x % mp - x % ap) % ap
        assert k == x // mp
        assert x % mp + k * mp == x


def test_boundary_probes_full_shell():
    """Random sampling never lands on the boundaries; enumerate them
    explicitly (k_elimination.rs:1583 pattern) on the full 30030/30031 pair."""
    ks = [0, 1, 2, 59, 509, A_ANCHOR - 2, A_ANCHOR - 1]
    probes = {0, 1, 2, M_SHELL - 1, M_SHELL, M_SHELL + 1,
              A_ANCHOR - 1, A_ANCHOR, A_ANCHOR + 1, RANGE - 1}
    probes.update(k * M_SHELL for k in ks)
    probes.update(k * M_SHELL + (M_SHELL - 1) for k in ks[:-1])
    for x in sorted(probes):
        if not 0 <= x < RANGE:
            continue
        assert k_eliminate(x % M_SHELL, x % A_ANCHOR) == x // M_SHELL
        s = CRAMState.from_int(x)
        assert s.to_int() == x


# ── general star frames (arbitrary multiplier c) ─────────────────────────

def test_star_frame_c1_matches_default_substrate():
    from cram_fhe.starframe import StarFrame, SAFE_BASIS_S6
    f = StarFrame(basis=SAFE_BASIS_S6, c=1)
    assert (f.m, f.a, f.m_inv) == (M_SHELL, A_ANCHOR, M_INV_MOD_A)
    for _ in range(500):
        x = rng.randrange(RANGE)
        assert f.k_eliminate(x % f.m, x % f.a) == k_eliminate(x % M_SHELL, x % A_ANCHOR)
        assert f.from_int(x).to_int() == x


def test_star_frame_arbitrary_multipliers_sound():
    from cram_fhe.starframe import StarFrame, SAFE_BASIS_S6, SAFE_BASIS_S8
    for basis in (SAFE_BASIS_S6, SAFE_BASIS_S8):
        for c in (1, 2, 7, 1001, 1_048_576, 12_345_678):
            f = StarFrame(basis=basis, c=c)
            assert (f.m * f.m_inv) % f.a == 1          # derived, for every c
            for x in [0, 1, f.m - 1, f.m, f.a - 1, f.a, f.range - 1] + [
                    rng.randrange(f.range) for _ in range(300)]:
                assert f.k_eliminate(x % f.m, x % f.a) == x // f.m
                s = f.from_int(x)
                assert s.to_int() == x
                assert f.project(x % f.m, x // f.m, 39) == x % 39


def test_star_frame_ops_match_integer_semantics():
    from cram_fhe.starframe import StarFrame, SAFE_BASIS_S6
    f = StarFrame(basis=SAFE_BASIS_S6, c=1001)
    for _ in range(300):
        x, y = rng.randrange(f.m), rng.randrange(f.m)
        cst = rng.randrange(1, 5000)
        assert f.from_int(x).add(f.from_int(y)).to_int() == x + y
        assert f.from_int(x).mul_int(cst).to_int() == x * cst


def test_multiplier_census_exact():
    from cram_fhe.starframe import count_valid_multipliers
    assert count_valid_multipliers(30030, 2**64 - 1) == (2**64 - 2) // 30030
    assert count_valid_multipliers(30030, 2**64 - 1) > 14_000_000
    assert count_valid_multipliers(9_699_690, 2**64 - 1) > 14_000_000
    assert count_valid_multipliers(30030, 30030) == 0
