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

## Cross-repo provenance (surveyed 2026-08-25)

Seven sibling repos were surveyed to ground this fork against what actually
exists. File references below were read during the survey; re-verify before
citing them elsewhere.

### Production alignment (NINE65_v7)

- The fork's closed form `K = (r_M − r_A) mod A` is exactly production
  `AdjacencyKElim::extract_k` (`crates/nine65/src/arithmetic/k_elimination.rs`,
  one branchless modular subtraction), and the derived inverse matches
  `alpha_inv_anchor()` (returns `alpha_cap`; nothing stored) and the star-family
  `t_inverse_mod_q() = q − c` in `params/manufactured.rs`.
- `universal_projection` here matches `universal_project` in
  `arithmetic/unified_rescale.rs`, including the no-coprimality property.
- **Sign pin**: NINE65_v7 documents the published anchor read `(γ + K) mod A`
  as a paper error — the winding read is `γ − K` (equivalently the general
  `γ + K·M`). Its never-vacuous regression
  (`adjacency_sign_is_minus_not_plus`) is ported to `tests/` here, along with
  its exhaustive `[3,5,7] → M=105, A=106` fixture and boundary probes.
- **Rescale reconciliation**: NINE65_v7 calls its K-Elimination rescale
  *exact* and backs that with exhaustive-range tests; this fork declares its
  rescale *one-way, metered*. Both are true of different properties:
  "exact" = the implemented map equals the intended rounded quotient with
  zero implementation error; "one-way" = that intended quotient is
  non-injective with fiber Δ. NINE65_v7's millibit noise ledger
  (`noise/budget.rs`) and this fork's `H_shadow = log₂Δ` meter are the same
  quantity in different units.
- **Capacity honesty**: this fork's frame is `M·A ≈ 2³⁰`; production frames
  are 96–110 bits on large hunted primes. This fork is a correctness and
  audit reference, not a capacity model.
- **CT support**: production has real CT primitives (`security/secret_data.rs`
  `ct_eq`/`ct_select`, branchless u128 mod-arithmetic in `k_elimination.rs`,
  a dudect-style verification suite) and an open measured finding (F-3:
  operand-magnitude timing on the general `extract_k`) whose documented
  structural fix is precisely the adjacency form this fork uses — it removes
  the division rather than making it constant-time. This supports, and
  bounds, the side-channel scope statement above.

### Formal verification status (what is actually machine-checked)

- **Proved, sorry/axiom-free, in `k-elimination-lean4`**: Universal
  Projection (`validation_v3` / `key_congruence`) and K-Elimination soundness
  (`Soundness.k_elimination_sound`), plus matching Coq with committed `.vo`
  artifacts. NINE65_v7's `lean4/KElimination` (19 modules, one documented
  axiom `ahop_hardness`) is the formalization of record there.
- **Of the source compendium's 10 theorems marked "PROVED · 0 sorry", 8 have
  no Lean or Coq declaration in any surveyed repo**: star-family
  transparency, star-family free inverse, adjacency lane residue, adjacency
  anchor inverse, shared-factor forward, one-wave digit extraction,
  arbitrary plaintext modulus, and K-Elimination-is-not-Garner. They are
  empirically exercised (here and in NINE65_v7's Rust tests) but their
  formalization is pending; the compendium's status table overstates.
- **`qmnf-lean-coq-security-proofs` must not be cited as verification**:
  235 real `sorry`s, 43 axioms, side-channel/independence "theorems" that
  are `True`-goals closed by `trivial`, and a K-Elimination theorem stated
  falsely (raw `v_M` subtracted without mod-A reduction; false whenever
  M > A under ℕ truncation). This fork's closed form avoids that trap only
  because the adjacency pair guarantees `A > M ⇒ r_M < A`; that precondition
  is part of the claim.

### Witness citations corrected

- `unified_rescale.py` ("0/900 arithmetic fails, 0/300 decrypt fails") does
  not exist in any surveyed repo. The real artifact is
  `unified_rescale.rs` (Rust, NINE65_v7), whose tests are exhaustive-range,
  not trial batteries. A citable numeric witness with provenance is this
  repo's own battery: 300 chains / 900 hot-path ops / 1801 monitored
  transitions, 0 failures — quote it as that, not as the nonexistent `.py`.
- "T22 heterogeneous case" (U11 witness) has no referent on disk in any
  surveyed repo; the nearest artifact is heterogeneous-base transduction in
  NINE65_v7 `exact_transcendentals/src/transduction.rs`. Treat U11 as
  sketch-only until a witness exists.
- Genuine depth-3 ct×ct chains exist in NINE65 v6's `rns_fhe.rs` test suite,
  not here (this fork has no ct×ct multiply).

### Predecessor delta (the defensible contribution)

- Every QMNF k-free predecessor stores its inverse as a precomputed field
  built by extended Euclid at construction (`QMNF_System`:
  `hcvlang/src/kfree_crt.rs` `cp_inv_mod_cr`, `hcvlang/src/plmg_core.rs`,
  `crates/qmnf-arithmetic/src/k_elimination.rs` `m_inv_mod_a`). Under this
  repo's G5 gate those are stored-constant violations even though they are
  perfect bijections. This fork and NINE65_v7's adjacency path derive the
  inverse from the construction — that is the concrete, checkable delta,
  and it also removes QMNF's runtime coprimality-failure branch.
- NINE65-v5's `entropy/crt_shadow.rs` takes the inverted stance — it
  *harvests* discarded quotients as entropy. This fork's zero-discard hot
  path and v5's harvester are mutually exclusive design points; don't blend
  their claims.
- `QMNF_System`'s `gso_fhe_noise.py` explicitly relies on correlations
  "impossible with i.i.d. sampling" — an anti-i.i.d. design. Claims from
  that path are not A2-clean under this repo's gates.

## Scope of A2 (restated to prevent drift)

A2 is **no synthetic emissions**, not "no cross-lane traffic". K-Elimination
and Universal Projection read across lanes and are compliant; Garner is not,
because digit *i* consumes the running value of digits 0..*i*−1. Emission-clean
(G1) does not imply A2-clean (G5): the stored-constant recovery path is a
perfect bijection and still a violation. Both gates run; both are reported.
