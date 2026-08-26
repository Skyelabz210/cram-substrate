"""A structural toy BFV layer over the reversible residue substrate.

Every ciphertext component is carried as a CRAMState: the evaluator's hot path
is component-wise residue arithmetic on the Safe Basis + shell + anchor lanes,
reversible on [0, M*A), with the winding derived by K-Elimination and every
transition checked by the ArrowMonitor.

Parameters (STRUCTURAL PROTOTYPE — NOT SECURE):

    t     = 30            plaintext modulus
    Delta = 1001 = 7*11*13
    Q     = t * Delta = 30030 = M  (the shell IS the ciphertext ring)

The scheme is a scalar LWE toy: ct = (a, b) with b = a*s + Delta*m + e (mod Q).
It exists to exercise the substrate — encrypt, homomorphic add, plaintext
multiply, the U12-style declared-one-way rescale, exact decrypt — under audit.
The moduli are far too small for lattice security and there is no ct*ct
multiplication (no tensoring/relinearisation).  Do not confuse the emission
audit passing with a security claim about these parameters.

Hot path (homomorphic evaluation): component-wise, reversible, A2-audited.
Cold path (client side, reconstruction permitted per A2 scope): key
generation, encryption's mod-Q reduction, decryption.
"""
from __future__ import annotations

import random
import secrets
from dataclasses import dataclass

from .substrate import (
    A_ANCHOR, M_SHELL, ArrowMonitor, CRAMState,
)

T_PLAIN = 30
DELTA = M_SHELL // T_PLAIN        # 1001
Q = T_PLAIN * DELTA               # 30030 == M_SHELL
NOISE_MAX = 8                     # fresh-noise magnitude bound

assert Q == M_SHELL


@dataclass(frozen=True)
class Ciphertext:
    a: CRAMState
    b: CRAMState
    noise_bound: int              # exact-integer bound on |accumulated noise|
    oracle_a: int                 # audit shadow (cold path): true integers
    oracle_b: int

    def exactness_guaranteed(self) -> bool:
        """Decryption is exact while the noise ledger stays under Delta/2.
        This is the same number the METERED rescale fiber reports — the
        entropy ledger and the noise ledger are one number."""
        return self.noise_bound < DELTA // 2


class ToyBFV:
    def __init__(self, seed: int | None = None):
        # Deterministic seeding is for reproducible audits only.
        self._rng = random.Random(seed) if seed is not None else secrets.SystemRandom()
        self.s = self._rng.randrange(Q)

    # ── cold path (client side; reconstruction permitted here) ────────────
    def encrypt(self, m: int) -> Ciphertext:
        if not (0 <= m < T_PLAIN):
            raise ValueError(f"plaintext must be in [0,{T_PLAIN})")
        a = self._rng.randrange(Q)
        e = self._rng.randrange(-NOISE_MAX, NOISE_MAX + 1)
        b = (a * self.s + DELTA * m + e) % Q
        return Ciphertext(
            a=CRAMState.from_int(a), b=CRAMState.from_int(b),
            noise_bound=NOISE_MAX, oracle_a=a, oracle_b=b,
        )

    def decrypt(self, ct: Ciphertext) -> int:
        a = ct.a.to_int() % Q
        b = ct.b.to_int() % Q
        d = (b - a * self.s) % Q
        return ((d + DELTA // 2) // DELTA) % T_PLAIN

    # ── hot path (evaluator; component-wise on the residue substrate) ─────
    @staticmethod
    def add(x: Ciphertext, y: Ciphertext, monitor: ArrowMonitor | None = None) -> Ciphertext:
        a = x.a.add(y.a)
        b = x.b.add(y.b)
        out = Ciphertext(a=a, b=b, noise_bound=x.noise_bound + y.noise_bound,
                         oracle_a=x.oracle_a + y.oracle_a,
                         oracle_b=x.oracle_b + y.oracle_b)
        if monitor is not None:
            monitor.check("add", x.oracle_a, x.a, out.oracle_a, out.a)
            monitor.check("add", x.oracle_b, x.b, out.oracle_b, out.b)
        return out

    @staticmethod
    def mul_plain(x: Ciphertext, c: int, monitor: ArrowMonitor | None = None) -> Ciphertext:
        if not (0 <= c < T_PLAIN):
            raise ValueError("plaintext scalar out of range")
        a = x.a.mul_int(c)
        b = x.b.mul_int(c)
        out = Ciphertext(a=a, b=b, noise_bound=x.noise_bound * c,
                         oracle_a=x.oracle_a * c, oracle_b=x.oracle_b * c)
        if monitor is not None:
            monitor.check("mul_plain", x.oracle_a, x.a, out.oracle_a, out.a)
            monitor.check("mul_plain", x.oracle_b, x.b, out.oracle_b, out.b)
        return out

    # ── U12-style rescale: the one DECLARED one-way step ──────────────────
    @staticmethod
    def rescale_state(x: CRAMState, oracle_x: int,
                      monitor: ArrowMonitor | None = None) -> tuple[CRAMState, int]:
        """floor((X + Delta/2) / Delta), re-raised into the substrate.

        One-way BY DESIGN: the discarded fiber is exactly the sub-Delta
        interval, so H_shadow = log2(Delta) bits per invocation — the noise
        budget being spent, metered, not hidden.  Pipeline shape follows U12:
        +Delta/2 -> quotient via the carried (r_M, K) identity -> re-raise.
        """
        shifted = x.add_int(DELTA // 2)
        xi = shifted.to_int()          # r_M + K*M: two lane reads, linear
        q = xi // DELTA
        out = CRAMState.from_int(q)
        if monitor is not None:
            monitor.meter(f"rescale Delta={DELTA}", DELTA)
            # the re-raised value is checked for arrow coherence as a fresh state
            monitor.check("rescale-reraise", q, out, q, out)
        return out, (oracle_x + DELTA // 2) // DELTA
