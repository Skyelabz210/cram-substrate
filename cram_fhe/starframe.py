"""General star-family frames: A = c·M + 1 for ANY multiplier c >= 1.

The adjacency frame in `substrate.py` is the c = 1 specialization.  This
module is the answer to the capacity limit recorded in docs/CLAIM_SCOPE.md:
the frame [0, M·A) grows linearly in c while every A2 property is preserved,
because the two facts that make the construction emission-clean are
multiplier-independent:

  * coprimality by construction:  1·(c·M + 1) − c·M = 1 is a Bezout identity,
    so gcd(M, A) = 1 for every c — nothing to test, nothing to store;
  * derived inverse:  M·(A − c) = M·A − (A − 1) ≡ 1 (mod A), so
    M⁻¹ mod A = A − c is read off the construction for every c — G5-clean.

K-Elimination in the general frame is the paper's Theorem 2 form
K = (r_A − r_M)·M⁻¹ mod A (one modular multiply); c = 1 collapses it to the
branch-free subtraction the default substrate uses.  Since c >= 1 implies
M < A, the residue r_M is already reduced mod A — the precondition that the
falsely-stated variant of this theorem (see docs/CLAIM_SCOPE.md) forgets.

A1: exact integers throughout.
"""
from __future__ import annotations

from dataclasses import dataclass

SAFE_BASIS_S6 = (2, 3, 5, 7, 11, 13)             # M = 30030
SAFE_BASIS_S8 = (2, 3, 5, 7, 11, 13, 17, 19)     # M_colony = 9699690


def _prod(xs) -> int:
    r = 1
    for x in xs:
        r *= x
    return r


@dataclass(frozen=True)
class StarFrame:
    """A (basis, multiplier) pair defining shell M = prod(basis) and anchor
    A = c·M + 1.  All constants are derived from (basis, c); none stored."""
    basis: tuple
    c: int

    def __post_init__(self):
        if self.c < 1:
            raise ValueError("star-family multiplier c must be at least 1")
        seen = set()
        for p in self.basis:
            if p < 2 or p in seen:
                raise ValueError("basis lanes must be distinct and >= 2")
            seen.add(p)

    @property
    def m(self) -> int:
        return _prod(self.basis)

    @property
    def a(self) -> int:
        return self.c * self.m + 1

    @property
    def m_inv(self) -> int:
        """M⁻¹ mod A = A − c, read off the construction (Theorem 5)."""
        return self.a - self.c

    @property
    def range(self) -> int:
        return self.m * self.a

    def k_eliminate(self, r_shell: int, r_anchor: int) -> int:
        """K = (r_A − r_M)·M⁻¹ mod A  (general star form; exact for X < M·A).

        r_shell < M < A always holds in a star frame, so no pre-reduction of
        r_shell mod A is needed — the precondition is structural, not assumed.
        """
        return ((r_anchor - r_shell) * self.m_inv) % self.a

    def project(self, r_shell: int, k: int, target_m: int) -> int:
        """Universal Projection: X mod T = (r_M + K·M) mod T, any T > 0."""
        return (r_shell % target_m + (k % target_m) * (self.m % target_m)) % target_m

    def from_int(self, x: int) -> "FrameState":
        if not (0 <= x < self.range):
            raise ValueError(f"value {x} outside frame [0, {self.range})")
        return FrameState(
            frame=self,
            gamma=tuple(x % p for p in self.basis),
            r_shell=x % self.m,
            r_anchor=x % self.a,
            bound=x,
        )


@dataclass(frozen=True)
class FrameState:
    """A value carried in a general star frame.  Same shape as the default
    substrate's CRAMState; the winding is derived, never stored."""
    frame: StarFrame
    gamma: tuple
    r_shell: int
    r_anchor: int
    bound: int

    @property
    def k(self) -> int:
        return self.frame.k_eliminate(self.r_shell, self.r_anchor)

    def to_int(self) -> int:
        return self.r_shell + self.k * self.frame.m

    def _guard(self, new_bound: int) -> int:
        if new_bound >= self.frame.range:
            raise OverflowError(
                f"operation would exceed the frame: bound {new_bound} >= "
                f"M*A = {self.frame.range}; raise the multiplier c or rescale")
        return new_bound

    def add(self, other: "FrameState") -> "FrameState":
        if other.frame != self.frame:
            raise ValueError("cannot mix frames without transduction")
        b = self._guard(self.bound + other.bound)
        f = self.frame
        return FrameState(
            frame=f,
            gamma=tuple((x + y) % p for x, y, p in zip(self.gamma, other.gamma, f.basis)),
            r_shell=(self.r_shell + other.r_shell) % f.m,
            r_anchor=(self.r_anchor + other.r_anchor) % f.a,
            bound=b,
        )

    def add_int(self, cst: int) -> "FrameState":
        if cst < 0:
            raise ValueError("hot path is over naturals")
        b = self._guard(self.bound + cst)
        f = self.frame
        return FrameState(
            frame=f,
            gamma=tuple((x + cst) % p for x, p in zip(self.gamma, f.basis)),
            r_shell=(self.r_shell + cst) % f.m,
            r_anchor=(self.r_anchor + cst) % f.a,
            bound=b,
        )

    def mul_int(self, cst: int) -> "FrameState":
        if cst < 0:
            raise ValueError("hot path is over naturals")
        b = self._guard(self.bound * cst)
        f = self.frame
        return FrameState(
            frame=f,
            gamma=tuple((x * cst) % p for x, p in zip(self.gamma, f.basis)),
            r_shell=(self.r_shell * cst) % f.m,
            r_anchor=(self.r_anchor * cst) % f.a,
            bound=b,
        )

    def succ(self) -> "FrameState":
        return self.add_int(1)


def count_valid_multipliers(m: int, max_anchor: int) -> int:
    """Exact count of multipliers c >= 1 with A = c·m + 1 <= max_anchor.

    Under the CLASS-R criterion (coprimality only — which every star anchor
    satisfies by the Bezout identity), THIS is the census of mathematically
    valid multipliers: every such c is valid, so the count is
    floor((max_anchor − 1) / m).  Exact integer arithmetic, no estimate.
    """
    if max_anchor <= m:
        return 0
    return (max_anchor - 1) // m


def _is_probable_prime(n: int) -> bool:
    """Deterministic Miller-Rabin for n < 3.3·10^24 (fixed base set)."""
    if n < 2:
        return False
    for p in (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41):
        if n % p == 0:
            return n == p
    d, s = n - 1, 0
    while d % 2 == 0:
        d //= 2
        s += 1
    for a in (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41):
        x = pow(a, d, n)
        if x in (1, n - 1):
            continue
        for _ in range(s - 1):
            x = x * x % n
            if x == n - 1:
                break
        else:
            return False
    return True


def count_prime_anchor_multipliers(m: int, c_max: int) -> int:
    """Exact count of c in [1, c_max] whose anchor A = c·m + 1 is PRIME —
    a strictly harder validity predicate than CLASS-R requires (composite
    anchors are legal; 30031 = 59·509 itself is composite)."""
    return sum(1 for c in range(1, c_max + 1) if _is_probable_prime(c * m + 1))
