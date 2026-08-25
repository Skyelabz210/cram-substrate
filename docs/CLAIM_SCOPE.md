# CRAM-FHE Reversible-Residue Fork — Claim Surface and Limits

Date: 2026-08-25. Every number below is sourced to a section of
`python3 -m cram_fhe.audit` run against this commit. Nothing here is carried
forward from another document.

## Established (measured by the audit in this repo)

| Claim | Evidence |
|---|---|
| Star-family inverse `M⁻¹ = A − c` is construction-read (nothing stored) | §1; G5 PASS on the K-Elimination construct |
| K-Elimination `K = (r_M − r_A) mod A` equals `⌊X/M⌋` on `[0, M·A)` | §1: exhaustive over first 2 laps + 50k random draws, 0 failures |
| Universal Projection is exact on arbitrary target lanes, coprimality not required | §1: lanes 97, 39, 1001, 65537; 0 failures |
| Every hot-path evaluator op (successor, homomorphic add, plaintext mul) is a bijection with zero shadow entropy, order-invariant, i.i.d.-preserving, arrow-coherent, constant-free | §2: G1–G6 PASS on each construct |
| The anchor lane is load-bearing: the same Δ-multiplication censused on the phase-only view leaks 7.066 bits (fiber L=134) | §2 negative control, G1 FAIL as expected |
| The carried successor is reversible over 4 laps of the shell (120,120 states), zero shadow entropy; discarding K collapses exactly `laps` states per fiber (2 bits at 4 laps) | §3 |
| 300/300 homomorphic chains `((m1+m2)·c + m3)` decrypt exactly under a live arrow monitor: 1801 transitions, 0 E(t) defects, 0 K-soundness failures, 0 carry-provenance failures | §4 |
| The only one-way step is the declared rescale; its metered cost, H_shadow = log₂(1001) ≈ 9.967 bits, **is** the noise budget spent — the entropy ledger and the noise ledger are one number | §2 (METERED), §4 |
| Hot-path operation count is input-independent (8 component updates per op, no carry branch, because K is derived rather than carried); the explicit-K branchy variant is data-dependent (9 vs 13 ops) | §5 |

## NOT established (do not claim these)

- **"Completely eliminates side channels" — NOT established, and not a claim
  this repo makes.** The audit gates measure *algorithmic* emissions:
  information-theoretic discard (G1), order/cascade dependence (G2), lane
  correlation (G3), arrow defects (G4), stored state (G5), provenance (G6).
  Physical side channels — timing, cache, power, EM — are properties of an
  implementation on hardware, not of the algebraic map. What the fork
  actually buys on that front is a *precondition*: with K derived instead of
  carried there is no data-dependent carry branch and the op-trace is uniform
  (§5), so a constant-time implementation is *possible* without restructuring.
  It is not automatic. This Python prototype runs on CPython big-ints, which
  are variable-time; any physical side-channel claim requires a constant-time
  port (Rust, CT primitives per the NINE65 coding rules) plus empirical
  leakage assessment (e.g. TVLA-style) on the target hardware.
- **Lattice security of the toy parameters — none.** t=30, Δ=1001, Q=30030 is
  a structural prototype. No LWE hardness estimate applies at these sizes and
  none is claimed. The paper's own Part VI flags composite-modulus security as
  requiring external adversarial review; that stands.
- **Ciphertext×ciphertext multiplication** is not implemented (no
  tensoring/relinearisation). The battery exercises add and plaintext-mul
  depth only.
- **Range discipline is a proof obligation, not magic.** K-Elimination is
  sound only on `[0, M·A)`. The substrate guards this with an exact-integer
  bound ledger and the oracle-paired arrow monitor; exceeding the frame is
  detected, not prevented.
- The Lean statements quoted in the source paper (`the_safe_basis.pdf`) were
  not rebuilt here; the audit checks the arithmetic identities empirically,
  which is weaker than a machine-checked proof.

## Scope of A2 (restated to prevent drift)

A2 is **no synthetic emissions**, not "no cross-lane traffic". K-Elimination
and Universal Projection read across lanes and are compliant; Garner is not,
because digit *i* consumes the running value of digits 0..*i*−1. Emission-clean
(G1) does not imply A2-clean (G5): the stored-constant recovery path is a
perfect bijection and still a violation. Both gates run; both are reported.
