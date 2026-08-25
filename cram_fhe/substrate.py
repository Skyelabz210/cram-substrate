"""The reversible residue substrate.

A value X with 0 <= X < M*A is carried as:

    gamma    : its residue views on the Safe Basis lanes {2,3,5,7,11,13}
    r_shell  : X mod M          (M = 30030, the shell)
    r_anchor : X mod A          (A = M + 1, the adjacency anchor)

Because gcd(M, A) = 1 the pair (r_shell, r_anchor) determines X exactly on
[0, M*A), so every component-wise update is a bijection on the represented
range — the substrate is reversible with zero shadow entropy, and the winding
number K = floor(X / M) is never carried as state.  It is derived on demand by
K-Elimination (Theorem 2):

    K = (r_A - r_M) * M^{-1} mod A

and for the adjacency anchor A = M + 1 the inverse is read off the
construction (Theorem 5 / Theorem 7): M = A - 1 = -1 (mod A), so M^{-1} = M and

    K = (r_M - r_A) mod A.

No stored constant, no extended-Euclid call in the hot path — G5-clean.

Every operation updates each component independently by the same linear rule
(no lane reads another lane's running output), so lane evaluation order cannot
matter — G2-clean by construction.

A1: exact integers throughout.  The one float in this file is math.log2 inside
audit reporting (entropy in bits for human display); it never touches the
substrate state.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import gcd

SAFE_BASIS = (2, 3, 5, 7, 11, 13)

M_SHELL = 1
for _p in SAFE_BASIS:
    M_SHELL *= _p                      # 30030
A_ANCHOR = M_SHELL + 1                 # 30031 = 59 * 509, coprime by adjacency
RANGE = M_SHELL * A_ANCHOR             # representable range [0, M*A)

# Star-family read-off: A = c*M + 1 with c = 1  =>  M^{-1} mod A = A - c.
STAR_C = (A_ANCHOR - 1) // M_SHELL     # 1, derived, not stored
M_INV_MOD_A = A_ANCHOR - STAR_C        # = M_SHELL; verified in the test suite


def egcd(a: int, b: int) -> tuple[int, int, int]:
    """Iterative extended Euclid (no recursion-depth ceiling)."""
    old_r, r = a, b
    old_s, s = 1, 0
    old_t, t = 0, 1
    while r != 0:
        q = old_r // r
        old_r, r = r, old_r - q * r
        old_s, s = s, old_s - q * s
        old_t, t = t, old_t - q * t
    return old_r, old_s, old_t


def inv_mod(a: int, m: int) -> int:
    """Modular inverse by extended Euclid only.

    Never pow(a, m-2, m): Fermat is silently wrong on composite moduli, and
    composite moduli are the default case here (the anchor is 59*509).
    """
    g, x, _ = egcd(a % m, m)
    if g != 1:
        raise ValueError(f"no inverse: gcd({a},{m})={g}")
    return x % m


def k_eliminate(r_shell: int, r_anchor: int) -> int:
    """K = floor(X/M) for X < M*A, from two independent lane reads.

    Adjacency closed form: K = (r_M - r_A) mod A.  Lane-independent, O(1),
    no reconstruction, no stored inverse.
    """
    return (r_shell - r_anchor) % A_ANCHOR


def universal_projection(r_shell: int, k: int, target_m: int) -> int:
    """X mod target_m = (r_M + K*M) mod target_m  (Theorem 1).

    Valid for ANY positive target modulus — no coprimality, no primality.
    """
    return (r_shell % target_m + (k % target_m) * (M_SHELL % target_m)) % target_m


@dataclass(frozen=True)
class CRAMState:
    """A value carried in the reversible residue space.

    `bound` is an exact-integer upper bound on the represented value,
    maintained alongside the state exactly the way a noise budget is: it
    guards the K-Elimination range condition X < M*A.  It is audit metadata,
    not part of the arithmetic state.
    """
    gamma: tuple      # residues on SAFE_BASIS lanes (views of r_shell)
    r_shell: int      # X mod M
    r_anchor: int     # X mod A
    bound: int        # exact upper bound on X (inclusive)

    # ── construction / observation ────────────────────────────────────────
    @classmethod
    def from_int(cls, x: int) -> "CRAMState":
        if not (0 <= x < RANGE):
            raise ValueError(f"value {x} outside representable range [0, {RANGE})")
        return cls(
            gamma=tuple(x % p for p in SAFE_BASIS),
            r_shell=x % M_SHELL,
            r_anchor=x % A_ANCHOR,
            bound=x,
        )

    @property
    def k(self) -> int:
        """Winding number, derived on demand — never stored."""
        return k_eliminate(self.r_shell, self.r_anchor)

    def to_int(self) -> int:
        """X = r_M + K*M.  A linear combination of two lane reads (the same
        shape as Universal Projection), not a Garner cascade."""
        return self.r_shell + self.k * M_SHELL

    def project(self, target_m: int) -> int:
        """Residue of the carried value on any view lane (Theorem 1)."""
        return universal_projection(self.r_shell, self.k, target_m)

    # ── hot-path operations (all component-wise, order-invariant) ─────────
    def _guard(self, new_bound: int) -> int:
        if new_bound >= RANGE:
            raise OverflowError(
                f"operation would exceed the anchor frame: bound {new_bound} >= "
                f"M*A = {RANGE}; rescale or extend the tower first")
        return new_bound

    def add(self, other: "CRAMState") -> "CRAMState":
        b = self._guard(self.bound + other.bound)
        return CRAMState(
            gamma=tuple((a + c) % p for a, c, p in zip(self.gamma, other.gamma, SAFE_BASIS)),
            r_shell=(self.r_shell + other.r_shell) % M_SHELL,
            r_anchor=(self.r_anchor + other.r_anchor) % A_ANCHOR,
            bound=b,
        )

    def add_int(self, c: int) -> "CRAMState":
        if c < 0:
            raise ValueError("hot path is over naturals; negate via ring complement")
        b = self._guard(self.bound + c)
        return CRAMState(
            gamma=tuple((a + c) % p for a, p in zip(self.gamma, SAFE_BASIS)),
            r_shell=(self.r_shell + c) % M_SHELL,
            r_anchor=(self.r_anchor + c) % A_ANCHOR,
            bound=b,
        )

    def mul_int(self, c: int) -> "CRAMState":
        if c < 0:
            raise ValueError("hot path is over naturals; negate via ring complement")
        b = self._guard(self.bound * c)
        return CRAMState(
            gamma=tuple((a * c) % p for a, p in zip(self.gamma, SAFE_BASIS)),
            r_shell=(self.r_shell * c) % M_SHELL,
            r_anchor=(self.r_anchor * c) % A_ANCHOR,
            bound=b,
        )

    def succ(self) -> "CRAMState":
        return self.add_int(1)


class ArrowMonitor:
    """Online arrow-coherence checking (gate G4, run live, with an oracle).

    The gates reference is explicit that the structural gates must be paired
    with an oracle check on actual output.  This monitor shadows the substrate
    with the true integer (cold path, audit only) and on EVERY transition
    verifies:

      * transition defect  E(t) = [dv - dr - M*dK]_A == 0
      * K-Elimination soundness live: derived K == floor(X/M)
      * carry provenance on unit steps: dK == 1 iff r_shell was M-1

    The oracle is what makes the check non-tautological: with K derived from
    the same two residues the algebraic identity E(t)=0 holds by construction,
    so a meaningful monitor must compare against the authoritative integer.
    That also makes it the range tripwire — the first thing that breaks when
    X leaves [0, M*A) is derived-K soundness.
    """

    def __init__(self) -> None:
        self.transitions = 0
        self.defects = 0
        self.k_unsound = 0
        self.carry_bad = 0
        self.metered_bits: list[tuple[str, int]] = []   # (op, fiber size L)

    def check(self, op: str, x_before: int, s_before: CRAMState,
              x_after: int, s_after: CRAMState) -> None:
        self.transitions += 1
        dv = (s_after.r_anchor - s_before.r_anchor)
        dr = (s_after.r_shell - s_before.r_shell)
        dk_true = x_after // M_SHELL - x_before // M_SHELL
        if (dv - dr - M_SHELL * dk_true) % A_ANCHOR != 0:
            self.defects += 1
        if s_after.k != x_after // M_SHELL or s_before.k != x_before // M_SHELL:
            self.k_unsound += 1
        if op == "succ":
            expect = 1 if s_before.r_shell == M_SHELL - 1 else 0
            if dk_true != expect:
                self.carry_bad += 1

    def meter(self, op: str, fiber: int) -> None:
        """Record a DECLARED one-way discard (e.g. rescale by Delta):
        its fiber size is the intended cost; log2(fiber) bits is exactly the
        noise budget being spent."""
        self.metered_bits.append((op, fiber))

    @property
    def clean(self) -> bool:
        return self.defects == 0 and self.k_unsound == 0 and self.carry_bad == 0

    def report(self) -> str:
        from math import log2   # display only; never touches substrate state
        lines = [
            f"arrow monitor: {self.transitions} transitions",
            f"  E(t) defects:            {self.defects}",
            f"  K-elimination unsound:   {self.k_unsound}",
            f"  carry provenance bad:    {self.carry_bad}",
        ]
        if self.metered_bits:
            for op, fib in self.metered_bits:
                lines.append(f"  METERED {op}: fiber L={fib}, "
                             f"H_shadow={log2(fib):.3f} bits (declared discard)")
        else:
            lines.append("  metered discards:        none")
        lines.append(f"  verdict: {'ARROW-COHERENT' if self.clean else 'DEFECTIVE'}")
        return "\n".join(lines)
