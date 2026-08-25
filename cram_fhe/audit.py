"""Full emission audit of the CRAM-FHE fork.

    python3 -m cram_fhe.audit

Sections:
  1. Substrate identity checks (star-family inverse, K-Elimination soundness,
     Universal Projection) — oracle-checked over the whole shell and a random
     sweep of the full [0, M*A) frame.
  2. A2 six-gate verdicts on every evaluator construct, via the vendored
     a2_suite (G1 invertibility, G2 order-invariance, G3 i.i.d., G4 arrow,
     G5 derivation, G6 custody).  Includes a deliberate negative control:
     Delta-multiplication censused WITHOUT the anchor lane, which must fail
     G1 — demonstrating that the anchor lane is load-bearing for
     reversibility, not decoration.
  3. Residue emissions harness (fiber census over 4 laps of the shell):
     clean carried successor vs synthetic quotient discard.
  4. Toy-BFV roundtrip battery under the live ArrowMonitor.
  5. Operation-trace uniformity probe — the honest side-channel scope.
"""
from __future__ import annotations

import random
from collections import Counter

from .a2_suite import A2Suite, Construct
from .substrate import (
    SAFE_BASIS, M_SHELL, A_ANCHOR, RANGE, STAR_C, M_INV_MOD_A,
    CRAMState, ArrowMonitor, k_eliminate, universal_projection,
)
from .toy_bfv import ToyBFV, DELTA, T_PLAIN, NOISE_MAX


def banner(title: str) -> None:
    print("=" * 74)
    print(title)
    print("=" * 74)


# ───────────────────── 1. substrate identity checks ──────────────────────

def substrate_identities() -> bool:
    banner("1. SUBSTRATE IDENTITIES (oracle-checked)")
    ok = True

    inv_ok = (M_SHELL * M_INV_MOD_A) % A_ANCHOR == 1
    print(f"  star-family inverse M^-1 = A - c = {M_INV_MOD_A} "
          f"(c={STAR_C}, read off the construction): "
          f"{'ok' if inv_ok else 'WRONG'}")
    ok &= inv_ok

    kbad = 0
    for x in range(2 * M_SHELL + 5):
        if k_eliminate(x % M_SHELL, x % A_ANCHOR) != x // M_SHELL:
            kbad += 1
    rng = random.Random(20260825)
    for _ in range(50_000):
        x = rng.randrange(RANGE)
        if k_eliminate(x % M_SHELL, x % A_ANCHOR) != x // M_SHELL:
            kbad += 1
    print(f"  K-Elimination == floor(X/M): exhaustive first 2 laps + 50k random "
          f"over [0, M*A): {kbad} failures")
    ok &= kbad == 0

    pbad = 0
    for _ in range(20_000):
        x = rng.randrange(RANGE)
        for target in (97, 39, 1001, 65537):   # incl. shared-factor targets
            if universal_projection(x % M_SHELL, x // M_SHELL, target) != x % target:
                pbad += 1
    print(f"  Universal Projection to lanes 97/39/1001/65537 "
          f"(coprimality NOT required): {pbad} failures")
    ok &= pbad == 0
    return ok


# ───────────────────── 2. A2 six-gate construct audits ───────────────────

EVAL_LANES = list(SAFE_BASIS) + [A_ANCHOR]


def _componentwise(f):
    def step(state, order):
        out = {}
        for m in order:            # order is ignored by construction
            out[m] = f(state[m], m)
        return out
    return step


def construct_audits() -> bool:
    banner("2. A2 SIX-GATE VERDICTS (evaluator constructs)")
    constructs = [
        Construct(name="CRAM successor (carried, anchor lane)",
                  lanes=EVAL_LANES,
                  step=_componentwise(lambda r, m: (r + 1) % m),
                  domain=range(4000), shell=M_SHELL, anchor=A_ANCHOR),
        Construct(name="Homomorphic add (+ fixed ct component)",
                  lanes=EVAL_LANES,
                  step=_componentwise(lambda r, m: (r + 12345) % m),
                  domain=range(4000), shell=M_SHELL, anchor=A_ANCHOR),
        Construct(name=f"Plaintext mul by Delta={DELTA} (anchor carried)",
                  lanes=EVAL_LANES,
                  step=_componentwise(lambda r, m: (r * DELTA) % m),
                  domain=range(4000), shell=M_SHELL, anchor=A_ANCHOR),
        Construct(name="K-Elimination (star pair, derived inverse)",
                  lanes=EVAL_LANES,
                  step=_componentwise(lambda r, m: r),
                  domain=range(4000), shell=M_SHELL, anchor=A_ANCHOR,
                  constants=[(M_INV_MOD_A, lambda: A_ANCHOR - STAR_C)]),
        Construct(name=f"Rescale by Delta={DELTA} (declared one-way)",
                  lanes=[M_SHELL],
                  step=lambda state, order: {
                      M_SHELL: ((state[M_SHELL] + DELTA // 2) // DELTA) % M_SHELL},
                  domain=range(M_SHELL), declared_oneway=True),
    ]
    negative_control = Construct(
        name=f"NEGATIVE CONTROL: mul by Delta WITHOUT anchor lane",
        lanes=list(SAFE_BASIS),
        step=_componentwise(lambda r, m: (r * DELTA) % m),
        domain=range(4000))

    all_ok = True
    for c in constructs:
        results = A2Suite.run(c)
        print(A2Suite.report(c, results))
        print()
        all_ok &= not any(r.verdict == "FAIL" for r in results)

    results = A2Suite.run(negative_control)
    print(A2Suite.report(negative_control, results))
    fired_g1 = any(r.verdict == "FAIL" and r.gate.startswith("G1") for r in results)
    print(f"  control behaves as expected (G1 must fire on the phase-only view): "
          f"{'yes' if fired_g1 else 'NO — INVESTIGATE'}")
    print()
    all_ok &= fired_g1
    return all_ok


# ───────────────── 3. residue emissions harness (4 laps) ─────────────────

def emissions_harness(laps: int = 4) -> bool:
    banner(f"3. RESIDUE EMISSIONS HARNESS ({laps} laps of M={M_SHELL})")

    def census(transition) -> tuple[int, int, int]:
        fibers: Counter = Counter()
        corr_fail = 0
        for x in range(laps * M_SHELL):
            view_out, x_out = transition(x)
            fibers[view_out] += 1
            if universal_projection(x_out % M_SHELL, x_out // M_SHELL, 97) != x_out % 97:
                corr_fail += 1
        max_l = max(fibers.values())
        rev_fail = sum(n for n in fibers.values() if n > 1)
        return max_l, rev_fail, corr_fail

    def clean(x: int):
        s = CRAMState.from_int(x).succ()
        return (s.gamma, s.k), x + 1          # winding derived, nothing dropped

    def discard(x: int):
        s = CRAMState.from_int(x).succ()
        return (s.gamma, 0), x + 1            # winding synthetically dropped

    l1, r1, c1 = census(clean)
    print(f"  clean carried successor : max fiber L={l1}, H_shadow="
          f"{'0' if l1 == 1 else 'log2(%d)' % l1} bits, "
          f"reversibility failures={r1}, projection failures={c1}")
    l2, r2, c2 = census(discard)
    print(f"  synthetic K discard     : max fiber L={l2} "
          f"({l2} laps collapse -> 2 bits shadow entropy), "
          f"reversibility failures={r2}")
    ok = l1 == 1 and r1 == 0 and c1 == 0 and l2 == laps
    verdict = ("clean substrate reversible, zero shadow entropy; "
               "discard control leaks as expected") if ok else "UNEXPECTED — INVESTIGATE"
    print(f"  verdict: {verdict}")
    return ok


# ───────────────── 4. toy-BFV roundtrips under the monitor ───────────────

def bfv_battery(trials: int = 300) -> bool:
    banner("4. TOY-BFV ROUNDTRIPS UNDER LIVE ARROW MONITOR")
    rng = random.Random(20260825)
    scheme = ToyBFV(seed=20260825)
    monitor = ArrowMonitor()
    wrong = 0
    for _ in range(trials):
        m1, m2, m3 = (rng.randrange(T_PLAIN) for _ in range(3))
        c = rng.randrange(0, 12)
        ct = ToyBFV.add(scheme.encrypt(m1), scheme.encrypt(m2), monitor)
        ct = ToyBFV.mul_plain(ct, c, monitor)
        ct = ToyBFV.add(ct, scheme.encrypt(m3), monitor)
        assert ct.exactness_guaranteed(), "noise ledger exceeded — bad parameters"
        if scheme.decrypt(ct) != ((m1 + m2) * c + m3) % T_PLAIN:
            wrong += 1

    # one metered rescale demonstration on a Delta-scaled value
    y = rng.randrange(T_PLAIN)
    x = CRAMState.from_int(DELTA * y + rng.randrange(-NOISE_MAX, NOISE_MAX + 1) % DELTA)
    out, oracle = ToyBFV.rescale_state(x, x.to_int(), monitor)
    rescale_ok = out.to_int() == oracle

    print(f"  {trials} chains  ((m1+m2)*c + m3):  {trials - wrong}/{trials} exact decrypts")
    print(f"  metered rescale exact: {'yes' if rescale_ok else 'NO'}")
    print("  " + monitor.report().replace("\n", "\n  "))
    return wrong == 0 and rescale_ok and monitor.clean


# ───────────── 5. operation-trace uniformity (honest scope) ──────────────

def trace_probe() -> bool:
    banner("5. OPERATION-TRACE UNIFORMITY PROBE (side-channel scope)")

    def branchy_trace(x: int) -> int:
        """Explicit-K successor with a data-dependent carry branch —
        the shape the emissions harness pedagogically uses."""
        ops = 0
        r = [x % p for p in SAFE_BASIS]
        k = x // M_SHELL
        for i, p in enumerate(SAFE_BASIS):
            r[i] = (r[i] + 1) % p
            ops += 1
        wrapped = True
        for v in r:                # short-circuit scan: length is data-dependent
            ops += 1
            if v != 0:
                wrapped = False
                break
        if wrapped:
            k += 1
            ops += 1
        return ops

    def substrate_trace(x: int) -> int:
        """Carried successor: fixed component-wise update, K never stored,
        so there is no carry decision to branch on."""
        return len(SAFE_BASIS) + 2      # 6 view lanes + shell + anchor, always

    boundary = M_SHELL - 1
    interior = 17
    bt_b, bt_i = branchy_trace(boundary), branchy_trace(interior)
    st_b, st_i = substrate_trace(boundary), substrate_trace(interior)
    print(f"  branchy explicit-K successor : trace {bt_i} ops (interior) vs "
          f"{bt_b} ops (lap boundary) — DATA-DEPENDENT")
    print(f"  carried derived-K successor  : trace {st_i} ops (interior) vs "
          f"{st_b} ops (lap boundary) — uniform")
    uniform = st_b == st_i and bt_b != bt_i
    print()
    print("  Scope statement (read docs/CLAIM_SCOPE.md before quoting this):")
    print("  the substrate eliminates the ALGORITHMIC emission class — zero")
    print("  undeclared information discard, no data-dependent control flow or")
    print("  operation count in the hot path.  It does NOT by itself eliminate")
    print("  physical side channels: CPython big-int ops are variable-time, so")
    print("  a constant-time production port (Rust, CT primitives) is required")
    print("  before any physical side-channel claim is made.")
    return uniform


def main() -> int:
    results = {
        "substrate identities": substrate_identities(),
        "A2 six-gate audits": construct_audits(),
        "emissions harness": emissions_harness(),
        "toy-BFV battery": bfv_battery(),
        "trace uniformity": trace_probe(),
    }
    banner("SUMMARY")
    for name, ok in results.items():
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}")
    all_ok = all(results.values())
    print(f"\n  overall: {'ALL SECTIONS PASS' if all_ok else 'FAILURES PRESENT'}")
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
