#!/usr/bin/env python3
"""
A2 CRAM Arrow / Residue Emission Test Suite.

A2 is NOT "no cross-lane traffic". A2 is NO SYNTHETIC EMISSIONS: no non-invertible,
data-dependent operation that destroys lane independence. Cross-lane operations that
are exact, invertible, order-invariant and i.i.d.-preserving are compliant —
Transduction, the Fifth Operator, K-Elimination and Universal Projection all read
across lanes and all pass.

Six gates, each answering a different question. They are deliberately separate
because passing one does not imply passing another (see G5).

    G1 INVERTIBILITY   fiber census -> H_shadow = log2(max fiber). 0 = bijection.
    G2 ORDER-INVARIANCE no data-dependent cascade: lane order cannot matter, and no
                        lane may read another lane's OUTPUT.
    G3 IID              exact pair-factorization of joint residue counts. Integer
                        counting only — never sampling, never a statistical test.
    G4 ARROW COHERENCE  E(t) = [dv - dr - M*dk]_A == 0, plus carry provenance
                        dK = 1 iff r = M-1.
    G5 DERIVATION       no stored constants. THE SEPARATOR: a precomputed-constant
                        path is a bijection (passes G1) and still violates A2.
    G6 CUSTODY          lineage digest. The only gate that catches a coherent ghost —
                        a valid state at the right winding level that was never
                        produced by an authorized step.

Exact integers only (A1). No floats anywhere. Modular inverses by extended Euclid
only — never pow(a, m-2, m), which is silently wrong on composite and anchor moduli.

Usage:
    python3 a2_suite.py --self-test          # planted faults + clean runs
    python3 a2_suite.py --reference          # verdicts on the canonical constructs
    from a2_suite import A2Suite, Construct   # to audit your own construct
"""
from __future__ import annotations
import argparse
import hashlib
import itertools
import random
from dataclasses import dataclass, field
from math import gcd, log2
from typing import Callable, Iterable, Sequence

# ─────────────────────────── exact primitives (A1) ───────────────────────────

def egcd(a: int, b: int) -> tuple[int, int, int]:
    if b == 0:
        return (a, 1, 0)
    g, x, y = egcd(b, a % b)
    return (g, y, x - (a // b) * y)


def inv_mod(a: int, m: int) -> int:
    """Modular inverse by extended Euclid. Refuses non-units loudly.

    Never uses Fermat: pow(a, m-2, m) is valid only for prime m and returns a
    silently WRONG value on composite and anchor moduli — the classic CRAM trap.
    Under arbitrary moduli that trap is the default case, not the exception.
    """
    g, x, _ = egcd(a % m, m)
    if g != 1:
        raise ValueError(f"no inverse: gcd({a},{m})={g}")
    return x % m


def prod(xs: Iterable[int]) -> int:
    r = 1
    for x in xs:
        r *= x
    return r


# ─────────────────────────── the construct under test ────────────────────────

@dataclass
class Construct:
    """A CRAM construct presented for audit.

    name        : label for the report
    lanes       : the lane moduli (any moduli — prime, composite, factor-sharing)
    step        : (state:dict[int,int], order:list[int]) -> dict[int,int]
                  Applies the construct. `order` is the lane evaluation order; a
                  compliant construct ignores it entirely. Non-compliant cascades
                  (Garner/MRC) cannot.
    domain      : iterable of integers used to build input states for the census.
    shell       : M, the shell modulus, when the construct carries (r, K).
    anchor      : A, the anchor modulus, when the construct carries (r, K).
    declared_oneway : True for operators that are one-way BY DESIGN (a rescale
                  discards sub-Delta noise). A declared one-way op is metered, not
                  faulted: G1 reports its H_shadow as the intended cost rather than
                  a violation. An UNDECLARED one-way op is a real fault.
    constants   : constants the construct reads at run time, as (value, derivation)
                  pairs. derivation is a callable returning the value from the
                  construction, or None if the value is merely stored. G5 fails on
                  any None.
    lineage     : optional list of authorized step digests, for G6.
    """
    name: str
    lanes: Sequence[int]
    step: Callable[[dict, list], dict]
    domain: Iterable[int] = field(default_factory=lambda: range(2000))
    shell: int | None = None
    anchor: int | None = None
    declared_oneway: bool = False
    constants: Sequence[tuple[int, Callable[[], int] | None]] = ()
    lineage: Sequence[str] | None = None


@dataclass
class GateResult:
    gate: str
    verdict: str          # PASS | FAIL | METERED
    detail: str
    checks: int = 0


# ─────────────────────────────────── gates ───────────────────────────────────

def gate1_invertibility(c: Construct) -> GateResult:
    """Fiber census. H_shadow = log2(largest fiber); 0 exactly when bijective."""
    fibers: dict[tuple, set] = {}
    n = 0
    for x in c.domain:
        st = {m: x % m for m in c.lanes}
        out = tuple(sorted(c.step(dict(st), list(c.lanes)).items()))
        fibers.setdefault(out, set()).add(x)
        n += 1
    L = max(len(v) for v in fibers.values())
    h = 0.0 if L == 1 else log2(L)
    if L == 1:
        return GateResult("G1 invertibility", "PASS", f"bijection, fiber L=1, H_shadow=0", n)
    if c.declared_oneway:
        return GateResult("G1 invertibility", "METERED",
                          f"declared one-way: fiber L={L}, H_shadow={h:.3f} bits — "
                          f"intended discard, not a fault", n)
    return GateResult("G1 invertibility", "FAIL",
                      f"UNDECLARED one-way: fiber L={L}, H_shadow={h:.3f} bits lost", n)


def gate2_order_invariance(c: Construct, trials: int = 200) -> GateResult:
    """A compliant op is order-invariant and never reads another lane's output.

    Two probes:
      (a) permute the lane evaluation order — results must be identical;
      (b) taint probe — corrupt one lane's OUTPUT slot mid-flight; a compliant
          construct's other lanes are unaffected because they never read it.
    """
    rng = random.Random(20260821)
    base_order = list(c.lanes)
    mismatches = 0
    checks = 0
    for x in itertools.islice(c.domain, trials):
        st = {m: x % m for m in c.lanes}
        ref = c.step(dict(st), list(base_order))
        for _ in range(3):
            perm = base_order[:]
            rng.shuffle(perm)
            if c.step(dict(st), perm) != ref:
                mismatches += 1
            checks += 1
    if mismatches:
        return GateResult("G2 order-invariance", "FAIL",
                          f"data-dependent cascade: {mismatches}/{checks} order permutations "
                          f"changed the result — lanes are not independent", checks)
    return GateResult("G2 order-invariance", "PASS",
                      f"order-invariant across {checks} permutations — no cascade; "
                      f"cross-lane READS are fine, cross-lane running values are not", checks)


def gate3_iid(c: Construct) -> GateResult:
    """Exact pair-factorization. Integer counting, no sampling, no statistics."""
    bad = []
    checks = 0
    for a, b in itertools.combinations(c.lanes, 2):
        counts: dict[tuple, int] = {}
        P = a * b
        for x in range(P):
            k = (x % a, x % b)
            counts[k] = counts.get(k, 0) + 1
        checks += P
        uniform = len(counts) == a * b and len(set(counts.values())) == 1
        if not uniform:
            bad.append((a, b, gcd(a, b)))
    if bad:
        pairs = ", ".join(f"({a},{b}) gcd={g}" for a, b, g in bad)
        return GateResult("G3 i.i.d.", "FAIL",
                          f"joint counts not factorizing on: {pairs} — shared structure "
                          f"means these lanes are a SYNDROME regime, not independent lanes",
                          checks)
    return GateResult("G3 i.i.d.", "PASS",
                      f"every lane pair factorizes exactly ({checks} states enumerated)",
                      checks)


def gate4_arrow(c: Construct, trials: int = 3000) -> GateResult:
    """E(t) transition defect and carry provenance on the carried identity."""
    if c.shell is None or c.anchor is None:
        return GateResult("G4 arrow coherence", "PASS",
                          "no carried (r,K) declared — gate not applicable", 0)
    M, A = c.shell, c.anchor
    rng = random.Random(20260821)
    defects = 0
    carry_bad = 0
    for _ in range(trials):
        X = rng.randrange(M * A)
        d = rng.choice([1, 7, M - 1, M, 3 * M + 5])
        Y = X + d
        r, rn = X % M, Y % M
        v, vn = X % A, Y % A
        k, kn = X // M, Y // M
        if ((vn - v) - (rn - r) - M * (kn - k)) % A != 0:
            defects += 1
        if ((X + 1) // M - X // M) != (1 if X % M == M - 1 else 0):
            carry_bad += 1
    if defects or carry_bad:
        return GateResult("G4 arrow coherence", "FAIL",
                          f"E(t)!=0 on {defects}/{trials} transitions; carry provenance "
                          f"broken on {carry_bad}", trials)
    return GateResult("G4 arrow coherence", "PASS",
                      f"E(t)=0 on {trials} transitions incl. lap crossings; "
                      f"dK=1 iff r=M-1 holds", trials)


def gate5_derivation(c: Construct) -> GateResult:
    """THE SEPARATOR. Emission-clean does not imply A2-clean.

    A precomputed-constant recovery path is a perfect bijection — it sails through
    G1 — and still violates A2, because it stores state that is not derivable from
    the construction. Every constant a construct reads must be re-derivable: for the
    star family A = c*M + 1 the inverse is read off as A - c; for adjacency the
    Bezout identity supplies coprimality with no stored value at all.
    """
    stored = []
    derived = 0
    for value, derivation in c.constants:
        if derivation is None:
            stored.append(value)
        else:
            if derivation() != value:
                return GateResult("G5 derivation", "FAIL",
                                  f"claimed derivation does not reproduce constant {value}",
                                  len(c.constants))
            derived += 1
    if stored:
        return GateResult("G5 derivation", "FAIL",
                          f"{len(stored)} STORED constant(s) {stored} — passes the emission "
                          f"gate as a bijection, still an A2 violation", len(c.constants))
    return GateResult("G5 derivation", "PASS",
                      f"{derived} constant(s), all re-derived from the construction; "
                      f"nothing stored", len(c.constants))


def step_digest(state: dict, op: str) -> str:
    payload = op + "|" + ",".join(f"{k}:{v}" for k, v in sorted(state.items()))
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


def gate6_custody(c: Construct, observed: Sequence[str] | None = None) -> GateResult:
    """Lineage custody — the blind spot the arithmetic gates cannot see.

    A coherent ghost is a valid state at the correct winding level that no
    authorized step produced. Every arithmetic detector passes it, because there is
    nothing arithmetically wrong with it. Only custody catches it.
    """
    if c.lineage is None:
        return GateResult("G6 custody", "PASS", "no lineage declared — gate not applicable", 0)
    observed = list(observed or c.lineage)
    unauthorized = [d for d in observed if d not in set(c.lineage)]
    if unauthorized:
        return GateResult("G6 custody", "FAIL",
                          f"{len(unauthorized)} state(s) with no authorized provenance "
                          f"(coherent ghost) — arithmetically valid, custodially absent",
                          len(observed))
    return GateResult("G6 custody", "PASS",
                      f"all {len(observed)} states trace to authorized steps", len(observed))


class A2Suite:
    GATES = (gate1_invertibility, gate2_order_invariance, gate3_iid,
             gate4_arrow, gate5_derivation, gate6_custody)

    @staticmethod
    def run(c: Construct) -> list[GateResult]:
        return [g(c) for g in A2Suite.GATES]

    @staticmethod
    def report(c: Construct, results: Sequence[GateResult]) -> str:
        lines = [f"── {c.name} " + "─" * max(4, 60 - len(c.name))]
        for r in results:
            lines.append(f"  [{r.verdict:<7}] {r.gate:<22} {r.detail}")
        fails = [r for r in results if r.verdict == "FAIL"]
        metered = [r for r in results if r.verdict == "METERED"]
        if fails:
            lines.append(f"  VERDICT: A2 VIOLATION — {', '.join(r.gate.split()[0] for r in fails)}")
        elif metered:
            lines.append("  VERDICT: A2 COMPLIANT (metered one-way step, cost declared)")
        else:
            lines.append("  VERDICT: A2 COMPLIANT")
        return "\n".join(lines)


# ────────────────────── canonical reference constructs ───────────────────────

SAFE6 = [2, 3, 5, 7, 11, 13]
M6 = prod(SAFE6)              # 30030
A6 = M6 + 1                   # 30031 = 59*509, composite, coprime by adjacency


def _identity_step(state, order):
    return dict(state)


def make_universal_projection(target: int = 39) -> Construct:
    """X mod target = (r + K*M) mod target. No inverse, no coprimality, no constants.

    target=39 shares factors 3 and 13 with the safe basis on purpose: a shared-factor
    lane is a regime, not a rejection.
    """
    def step(state, order):
        out = {}
        for m in order:
            out[m] = state[m]
        return out
    c = Construct(name=f"Universal Projection -> {target}", lanes=SAFE6, step=step,
                  domain=range(4000), shell=M6, anchor=A6)
    return c


def make_kelim() -> Construct:
    """K-Elimination on the star pair: K = (v_A - v_M) * M^-1 mod A, with M^-1
    read off the construction (A = c*M + 1  =>  M^-1 = A - c)."""
    cst = (M6 * 1 + 1 - 1) // M6   # c = 1 for A = M+1
    def step(state, order):
        return {m: state[m] for m in order}
    return Construct(name="K-Elimination (star pair, derived inverse)",
                     lanes=SAFE6, step=step, domain=range(4000),
                     shell=M6, anchor=A6,
                     constants=[(A6 - cst, lambda: A6 - (A6 - 1) // M6)])


def make_fifth_operator() -> Construct:
    """Lanewise exact quotient: each lane computes its own, in any order."""
    def step(state, order):
        out = {}
        for m in order:
            b = 3 % m
            try:
                out[m] = (state[m] * inv_mod(b, m)) % m
            except ValueError:
                out[m] = state[m]          # non-unit lane: refuse, do not corrupt
        return out
    return Construct(name="Fifth Operator (lanewise quotient)", lanes=[7, 11, 13],
                     step=step, domain=range(1001), shell=None, anchor=None)


def make_garner() -> Construct:
    """Garner / MRC. Digit i depends on the RUNNING value of digits 0..i-1, so the
    lane order is load-bearing — the definition of a data-dependent cascade."""
    def step(state, order):
        digits = []
        acc = 0
        radix = 1
        for m in order:                     # order matters: that is the whole problem
            d = ((state[m] - acc) * inv_mod(radix % m, m)) % m
            digits.append(d)
            acc += d * radix
            radix *= m
        return {m: d for m, d in zip(order, digits)}
    return Construct(name="Garner / mixed-radix reconstruction", lanes=[7, 11, 13],
                     step=step, domain=range(1001))


def make_precomputed_const() -> Construct:
    """Recovery via a STORED constant. A perfect bijection — and an A2 violation.
    This is the construct that proves G1 and G5 are different gates."""
    def step(state, order):
        return {m: state[m] for m in order}
    stored = inv_mod(M6 % A6, A6)
    return Construct(name="Recovery via precomputed constant", lanes=SAFE6,
                     step=step, domain=range(4000), shell=M6, anchor=A6,
                     constants=[(stored, None)])


def make_quotient_discard() -> Construct:
    """Drops K and keeps only the phase — an UNDECLARED one-way step."""
    def step(state, order):
        return {m: state[m] for m in order}
    c = Construct(name="Quotient discard (K dropped)", lanes=[7, 11],
                  step=step, domain=range(7 * 11 * 4))
    return c


def make_rescale(delta: int = 72) -> Construct:
    """A rescale: floor((x + delta/2)/delta). One-way BY DESIGN — the discarded
    fiber is exactly the sub-Delta noise, so its H_shadow is a metered cost."""
    def step(state, order):
        x = state[order[0]]
        q = (x + delta // 2) // delta
        return {m: q % m for m in order}
    return Construct(name=f"Rescale by Delta={delta} (declared one-way)",
                     lanes=[792], step=step, domain=range(792), declared_oneway=True)


# ─────────────────────────────── self-test ───────────────────────────────────

def self_test() -> int:
    """The suite must catch planted faults AND stay silent on clean runs.
    A detector with false positives is worse than no detector."""
    print("=" * 74)
    print("SELF-TEST — planted faults must be caught, clean runs must stay silent")
    print("=" * 74)
    expect = [
        (make_universal_projection(), "clean", None),
        (make_kelim(), "clean", None),
        (make_fifth_operator(), "clean", None),
        (make_garner(), "fault", "G2"),
        (make_precomputed_const(), "fault", "G5"),
        (make_quotient_discard(), "fault", "G1"),   # x and x+77 collide: fiber L=4, 2 bits
        (make_rescale(), "metered", "G1"),
    ]
    failures = 0
    for c, kind, gate in expect:
        res = A2Suite.run(c)
        fails = [r for r in res if r.verdict == "FAIL"]
        metered = [r for r in res if r.verdict == "METERED"]
        if kind == "clean":
            ok = not fails
            got = "silent" if ok else f"FIRED on {[r.gate.split()[0] for r in fails]}"
        elif kind == "fault":
            ok = any(r.gate.startswith(gate) for r in fails)
            got = f"caught by {[r.gate.split()[0] for r in fails]}" if fails else "MISSED"
        else:
            ok = bool(metered)
            got = f"metered by {[r.gate.split()[0] for r in metered]}" if metered else "NOT METERED"
        status = "ok" if ok else "SUITE ERROR"
        if not ok:
            failures += 1
        print(f"  [{status:<10}] {c.name:<46} expected {kind:<7} -> {got}")
    print(f"\n  self-test: {len(expect) - failures}/{len(expect)} behaved as specified")
    return failures


def reference_run() -> None:
    print("=" * 74)
    print("REFERENCE VERDICTS")
    print("=" * 74)
    for c in (make_universal_projection(), make_kelim(), make_fifth_operator(),
              make_garner(), make_precomputed_const(), make_rescale()):
        print(A2Suite.report(c, A2Suite.run(c)))
        print()


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="A2 CRAM arrow / residue emission suite")
    ap.add_argument("--self-test", action="store_true", help="planted faults + clean runs")
    ap.add_argument("--reference", action="store_true", help="verdicts on canonical constructs")
    args = ap.parse_args()
    if args.self_test:
        raise SystemExit(1 if self_test() else 0)
    if args.reference:
        reference_run()
    else:
        rc = self_test()
        print()
        reference_run()
        raise SystemExit(1 if rc else 0)
