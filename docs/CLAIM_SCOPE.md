# CRAM-FHE Reversible-Residue Fork — Claim Surface and Limits

Date: 2026-08-25 (updated 2026-08-26). Every number below is sourced to a
section of `python3 -m cram_fhe.audit` run against this commit. Nothing here
is carried forward from another document.

## Verification policy (governing rule, set by the project owner 2026-08-26)

**A theorem is PROVED only if a machine-checked artifact exists on disk —
a Lean file that `lake build` elaborates or a Coq file that `coqc` compiled.
Everything else is a PROOF SKETCH, regardless of any "[PROVED]",
"Lean verified", or "0 sorry" label in a document.** Documents produced by
generation tooling have carried such labels for statements with no
corresponding formalization; the label is not the artifact.

Under this policy, the machine-checked set today is: Universal Projection and
K-Elimination soundness (`k-elimination-lean4`, sorry/axiom-free, with
compiled Coq `.vo`), plus NINE65_v7's `lean4/KElimination` (19 modules, one
documented axiom `ahop_hardness`). Everything else across the uploaded
compendia — the four pillars, the 10-theorem table beyond those two, the
theorem stack's [PROVED] rows, T-ODC, and the transduction theorems
T-X-WD / T-X-EXACT / T-X-SIG / T-X-REV / T-X-PROJ — is proof sketch, in
several cases with strong empirical witnesses in this repo's audit.

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

## Star-family multipliers (audit §6, added 2026-08-25)

| Claim | Evidence |
|---|---|
| For every multiplier `c ≥ 1`, `A = c·M+1` is coprime to M (Bezout identity) and the inverse `M⁻¹ = A − c` is derived, not stored — G5-clean for the whole family | §6a: 9-multiplier sweep (mirroring `manufactured.rs`, composite c included) on S6 and S8, 18/18 frames sound |
| A c > 1 frame passes all six gates | §6b: c=2 (A=60061), A2 COMPLIANT, 2.46M states enumerated for G3 |
| Exact multiplier census under CLASS-R (coprimality only, automatic): S6 anchors within u64: **614,277,191,931,720**; S8: **1,901,786,971,924** | §6c, `count_valid_multipliers` (exact integer division, no estimate) |
| Raising c raises capacity linearly in practice: a 40,000-step accumulation that overflows the c=1 frame completes in the c=2 frame with K sound at every step | §6d |

On the **"over 14 million mathematically valid multipliers"** figure: it has no
on-disk source in any surveyed repo. Under the CLASS-R predicate it is *true
but understates the u64 census by about seven orders of magnitude*; under the
strictly-harder prime-anchor predicate (not required — 30031 = 59·509 is
composite and legal), the exact count for S6 with c ≤ 200,000 is 48,648, and
no extrapolated total is claimed here. Cite a predicate with the number.

Capacity honesty, updated: with `A ≤ 2⁶⁴` the S6 frame reaches `M·A ≈ 2⁷⁹` —
far past the toy 2³⁰, still below the 96–110-bit multi-anchor production
frames in NINE65_v7. Multiplier scaling closes most of the gap; multi-lane
anchor towers remain the production answer beyond it.

## Operator census and the 5th operator (audit §7, added 2026-08-26)

| Claim | Evidence |
|---|---|
| Operator-schema census, exact: 8⁵ = 32,768 (Atlas 5-lane basis); **8⁸ = 16⁶ = 16,777,216** (8-lane S8 — the "over 14 million operators" referent, with on-disk provenance `NINE65_v7/docs/cram-corpus/2026-08-12/operator_space_R.py:489`); 9⁸ = 43,046,721 with the R operator | §7e |
| Transduction (5th operator) implemented: T-X-EXACT and T-X-REV witnessed over 3,000 S6→S8→S6 round trips, 0 failures; commuting square X(a)+X(b)=X(a+b) over 2,000 draws, 0 failures | §7a–b |
| Projection winding policy is not reversible — exact collision witness (states with K=5 and K=1 collapse), consistent with T-X-PROJ and gate G1 | §7c |
| Winding Vanish (Policy I): K for X=5·10⁸ falls 16,650 → 51 → 0 as the basis grows S6 → S8 → S8∪{23,29} | §7d |
| Homogeneous schemas equal the ring homomorphism (INV-2); heterogeneous AAMMM matches no single homogeneous op (genuine chimera); polynomial DKAM degree 2 < 3 on the transport core | §7f |

Configuration axes compose: ~6.1·10¹⁴ star multipliers (u64, S6) ×
16,777,216 operator schemas (S8) × basis choice. "Over 14 million" is the
operator-schema axis alone; cite each axis with its predicate.

Variant lineage in the corpus (recorded so the generations stay straight —
these are variants of one evolving system, not contradictions within one
definition):

- **The Operator Atlas (March 2026) is the chimera-1 variant.** It reports a
  single-integer value for every schema, heterogeneous ones included
  (AAAAA(100,7) = 5,447 etc.). The later corpus retired that lift: the
  Chimera white paper (April 2026) defines χ_S = φ⁻¹(F₁,…,F_k), under which
  homogeneous schemas equal the ring homomorphism (AAAAA = 107, per INV-2),
  and NINE65_v7's `cram_machine.rs` goes further — a heterogeneous output
  "names a residue tuple and nothing more" (`WindingLoss::Heterogeneous`),
  lifting it to an integer is called **the chimera-1 trap**, and
  single-integer reads of chimeras exist only as destructive Garner reads
  counted by `destructive_reads()`. This repo implements the white-paper /
  machine variant. The Atlas value column belongs to the chimera-1
  convention, whose exact lift rule is not specified in the uploaded doc, so
  those numbers are unverifiable here — cite them only with the variant
  label attached.
- Same lineage note for DKAM scope: the Atlas's "ALL schemas structurally
  safe (deg ≤ 2)" reads Inv as a mirror; under the polynomial-degree
  convention this repo and `cram_ops::parse_schema` use, I-lane schemas
  (15,961 of 32,768 on 5 lanes) are rational maps outside polynomial DKAM.
- The theorem stack's own T22 ("Positive Density for All Populated Strata",
  a Dresden prime-hunt result) is not the "T22 heterogeneous case" the
  safe-basis compendium cites as the U11 transduction witness; that witness
  remains unlocated. The transduction empirical witness with provenance is
  now this repo's audit §7.
- Transduction here reads values via the linear (r_M, K) identity and
  reconstructs chimera displays via parallel-summation CRT (compendium
  Theorem 1.1) — no Garner/MRC anywhere, honoring POA-7 where the 5th
  Operator document's Definition 1.2 still names Garner for γ_B.

## NOT established (do not claim these)

- **"ρ_CPA = 0.0000 under power analysis", claimed as *formally proven* in the
  NINE65 v7 Formal Proofs Compendium (Manus AI, Aug 2026, Theorem 1.2) — NOT
  established.** A Pearson correlation on physical power traces is an
  empirical measurement on specific hardware; it cannot be the conclusion of
  an algebraic proof, and no trace data, target device, or acquisition setup
  accompanies the claim. The *algorithmic* half of that theorem (parallel
  summation has no sequential secret-dependent intermediate state, unlike
  Garner) is real and is what this repo's G2 gate checks; the physical half
  remains subject to the side-channel scope statement below, unchanged.

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
