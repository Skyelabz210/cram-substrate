# Proof-Sketch Register — CRAM-FHE Reversible-Residue Fork

One entry per mathematical claim this repo's code relies on. Status values
follow the verification policy in `CLAIM_SCOPE.md`:

- **MACHINE-CHECKED** — a lake-built Lean or coqc-compiled Coq artifact
  exists on disk (the file is named).
- **SKETCH + WITNESS** — prose proof below, plus the audit section that
  exercises it empirically (`python3 -m cram_fhe.audit`).
- **SKETCH** — prose proof below, no machine artifact, no dedicated witness.

Notation: basis B with shell `M = ∏ B`; star anchor `A = c·M + 1`, `c ≥ 1`;
for a value `0 ≤ X < M·A`: `r_M = X mod M`, `r_A = X mod A`, `K = ⌊X/M⌋`.

---

## PS-1 — Universal Projection

**Statement.** For any `X = r_M + K·M` and ANY modulus `T > 0`:
`X mod T = (r_M mod T + (K mod T)·(M mod T)) mod T`. No coprimality or
primality of `T` is required.

**Sketch.** Immediate from the ring homomorphism `Z → Z/TZ`: reduction mod T
commutes with `+` and `·`, so the residue of the sum is the sum of residues
of the parts. Every modulus is a view lane.

**Status.** MACHINE-CHECKED — `k-elimination-lean4/KElimination.lean`
(`validation_v3`, `key_congruence`), Coq `coq/K_Elimination.v`
(`key_congruence`, compiled `.vo` on disk). Witness: audit §1, §3.

---

## PS-2 — K-Elimination soundness

**Statement.** For `gcd(M, A) = 1` and `0 ≤ X < M·A`:
`K = ((r_A − (r_M mod A)) · M⁻¹) mod A` equals `⌊X/M⌋`.

**Sketch.** Write `X = qM + r_M` with `q = ⌊X/M⌋`. Since `X < M·A`, `q < A`.
Reduce mod A: `r_A ≡ qM + r_M (mod A)`, so `q ≡ (r_A − r_M)·M⁻¹ (mod A)`,
where `M⁻¹` exists by coprimality. Because `0 ≤ q < A`, the least
non-negative residue is exactly `q`. **The reduction `r_M mod A` matters**:
with raw `r_M` and natural-number subtraction the statement is false whenever
`M > A` (the trap recorded in CLAIM_SCOPE for the qmnf proofs repo). In a
star frame `A > M` always, so `r_M mod A = r_M` structurally.

**Status.** MACHINE-CHECKED — `k-elimination-lean4/KElimination.lean`
(`Soundness.k_elimination_sound`, `k_elimination_complete`), Coq
`k_elimination_core` (`.vo` on disk). Witness: audit §1 (exhaustive 2 laps +
50k random), §6a across 18 (basis, c) frames.

---

## PS-3 — Star-family derived inverse

**Statement.** For `A = c·M + 1`: `gcd(M, A) = 1` and `M⁻¹ mod A = A − c`,
for every `c ≥ 1`.

**Sketch.** Coprimality: `1·A − c·M = 1` is a Bezout certificate. Inverse:
`M·(A − c) = M·A − c·M = M·A − (A − 1) ≡ 1 (mod A)`. Both facts are read off
the construction — nothing stored, nothing computed at runtime (gate G5).

**Status.** SKETCH + WITNESS (audit §1, §6a; test
`test_star_inverse_read_off_construction` cross-checks against extended
Euclid). Not yet formalized; this is a one-line `ring`-style Lean lemma —
top of the formalization backlog.

---

## PS-4 — Adjacency collapse (c = 1 fast path)

**Statement.** For `A = M + 1`: `K = (r_M − r_A) mod A`, one branch-free
modular subtraction, no multiply.

**Sketch.** `M ≡ −1 (mod A)` so `M⁻¹ ≡ −1`. Substituting into PS-2:
`K ≡ (r_A − r_M)·(−1) ≡ r_M − r_A (mod A)`. Matches production
`AdjacencyKElim::extract_k` (NINE65_v7) including the sign: the anchor read
is `γ − K`, and the published `γ + K` form is a pinned error (regression
ported to `tests/`).

**Status.** SKETCH + WITNESS (audit §1; exhaustive [3,5,7]→105/106 fixture
and boundary probes in `tests/`). Special case of PS-2, so its formal core
is machine-checked; the collapsed form itself is not separately formalized.

---

## PS-5 — Substrate reversibility (zero shadow entropy)

**Statement.** Each hot-path evaluator op (successor, add, add-const;
mul by u with `gcd(u, M·A) = 1`) is a bijection on the represented range
`[0, M·A)`; the carried state has fiber size L = 1, H_shadow = 0.

**Sketch.** `gcd(M, A) = 1` makes `(r_M, r_A) ↦ X` a bijection
`Z/MZ × Z/AZ ≅ Z/(M·A)Z` (CRT). Component-wise addition is translation on
the product group — bijective. Multiplication by a unit is a group
automorphism — bijective. The γ-views are projections of `r_M`, carrying no
independent state. Non-unit multiplication (e.g. by Δ) is injective on
integers but not on the phase-only view — which is exactly why the anchor
lane is load-bearing (negative control, audit §2).

**Status.** SKETCH + WITNESS (audit §2 gates G1–G5 per construct; §3 fiber
census over 120,120 states; §6b on a c=2 frame).

---

## PS-6 — Metered rescale: entropy ledger = noise ledger

**Statement.** Rescale `X ↦ ⌊(X + Δ/2)/Δ⌋` has fibers of size exactly Δ, so
H_shadow = log₂Δ per invocation, and this is the same quantity BFV noise
accounting charges for the Δ-division.

**Sketch.** The preimage of each quotient q is the interval
`[qΔ − Δ/2, qΔ + Δ/2)` of length Δ — the sub-Δ interval is the discarded
noise. "Exact" in the production sense (implemented map = intended rounded
quotient, zero implementation error) and "one-way" (intended quotient is
Δ-to-1) are claims about different properties; both hold.

**Status.** SKETCH + WITNESS (audit §2 METERED, §4; NINE65_v7
`unified_rescale.rs` exhaustive-range tests for the exactness half).

---

## PS-7 — Multiplier census

**Statement.** Every `c ≥ 1` yields a valid star anchor under CLASS-R
(coprimality-only), so the count of valid multipliers with `A ≤ 2⁶⁴−1` is
`⌊(2⁶⁴−2)/M⌋` exactly: 614,277,191,931,720 for S6; 1,901,786,971,924 for S8.

**Sketch.** Validity is PS-3's Bezout certificate, which holds for all c;
the census is then integer division of the anchor budget by M. The "over
14 million" figure is satisfied but refers to the OPERATOR census (PS-10a).

**Status.** SKETCH + WITNESS (audit §6c; `test_multiplier_census_exact`).

---

## PS-8 — Transduction exactness and reversibility (T-X-EXACT, T-X-REV)

**Statement.** For frames F_A, F_B and `X < min(range_A, range_B)`, the
recompute-policy transduction satisfies `val_B(X(s)) = val_A(s)`, and the
round trip is the identity. Moreover transduction commutes with addition:
`X(a) + X(b) = X(a + b)` when all values stay in range.

**Sketch.** Recompute-policy transduction is `enc_B ∘ val_A`. `val_A` is
injective on states (PS-2 recovers K exactly), `enc_B ∘ val_B = id` up to
canonicalization, so the round trip composes to the identity. Commuting
square: both sides equal `enc_B(val_A(a) + val_A(b))` because addition in
each frame is integer addition under the range guard (PS-5).

**Status.** SKETCH + WITNESS (audit §7a–b: 3,000 round trips, 2,000
commuting-square draws, 0 failures). The 5th-operator document's versions
(T-X-WD/EXACT/SIG/REV) are prose; none machine-checked.

---

## PS-9 — Projection non-reversibility (T-X-PROJ)

**Statement.** Any winding policy that discards nonzero K is not injective,
hence not reversible.

**Sketch.** Two states `(r, K₁) ≠ (r, K₂)` represent distinct integers
`γ + K₁M ≠ γ + K₂M` but map to the same output once K is dropped: two
inputs, one output, no inverse. This is the same fact gate G1 measures as
fiber size (the K-discard control has L = laps).

**Status.** SKETCH + WITNESS (audit §7c exact collision witness; §3
discard control, L = 4 at 4 laps).

---

## PS-10 — Chimera schema layer

**(a) Census.** `#schemas = alphabet^lanes`: 8⁵ = 32,768; 8⁸ = 16⁶ =
16,777,216 (the "over 14 million operators"; provenance
`NINE65_v7/docs/cram-corpus/2026-08-12/operator_space_R.py:489`); 9⁸ =
43,046,721 with R. *Sketch:* independent choice per lane — counting.

**(b) Homogeneous schemas are the ring homomorphism (INV-2).** All-Add
equals `(a+b) mod M`, all-Mul `(a·b) mod M`, all-Sub `(a−b) mod M`.
*Sketch:* CRT is a ring isomorphism; identical per-lane operations are the
image of the single global operation. Consequence recorded in CLAIM_SCOPE:
the Operator Atlas's named-schema value table (AAAAA(100,7)=5,447)
contradicts this and is unverified.

**(c) Heterogeneous schemas leave the diagonal.** A chimera generally equals
`φ(x)` for an x that is no single homogeneous result: distinct lane
operators impose distinct polynomial constraints, and coincidence with e.g.
`a+b` on every lane would force the Mul lanes to satisfy
`(a+b) ≡ a·b (mod p)` for all inputs — false already at `(a,b) = (1,1)`
unless p | 1. *Status:* SKETCH + WITNESS (audit §7f; the audit checks the
specific instance, the general statement is the sketch).

**(d) DKAM degree.** Schemas over {A,S,M,D,Q,N,_} have polynomial lane
degree ≤ 2 < 3 = ρ(transport core); I-lanes are degree-1 rational (Möbius)
maps whose polynomial representative has degree p−2, outside polynomial
DKAM — 15,961 of 32,768 five-lane schemas contain one. *Status:* SKETCH
(degree bookkeeping); the DKAM criterion itself is upstream
(`t_infinite_dkam_ns` is claimed Lean-proved in NINE65_v7 — not re-verified
here, so treat as sketch under the policy until its lake build is confirmed).

---

## PS-11 — Trace uniformity (side-channel scope)

**Statement.** With K derived (never stored) there is no carry decision in
the hot path: every op is the same fixed set of component-wise modular
updates, so the operation COUNT and control flow are input-independent.

**Sketch.** By construction: succ/add/mul update each of the 8 components
by one modular op, unconditionally; the branchy explicit-K successor by
contrast executes a data-dependent scan and conditional increment. This is
an algorithmic statement only — physical constant-time additionally
requires constant-time modular primitives on the target hardware (CPython
big-ints are not; see CLAIM_SCOPE's side-channel scope).

**Status.** SKETCH + WITNESS (audit §5: 8 ops always vs 9/13 data-dependent).

---

## Formalization backlog (effort-ordered)

1. PS-3 star inverse and PS-4 collapse — one-line `ring`/`omega` lemmas.
2. Compendium theorems 4–9 (star transparency, adjacency residue/inverse,
   shared-factor forward, one-wave digits) — short, self-contained.
3. PS-8 T-X-EXACT / T-X-REV over `enc`/`val` — mechanical once enc/val are
   defined; PS-9 is a two-line injectivity argument.
4. PS-5 bijection lemmas over `ZMod (M·A)`.
5. T-ODC (division closure) — needs FPD formalized first; largest item.
