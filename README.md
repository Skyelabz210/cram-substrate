# cram-substrate

Exact integer residue-native computation substrate: CRT bases, winding towers,
K-Elimination, FPD, transduction, shadow signatures, and finite-support
continuation.

## CRAM-FHE reversible-residue fork (`cram_fhe/`)

A leveled-FHE evaluation prototype whose hot path lives entirely in the
i.i.d.-safe reversible residue space, with A2 arrow/emission checking on every
transition.

**Carried state.** A value `X ∈ [0, M·A)` is held as its Safe-Basis views
`γ = (X mod p)` for `p ∈ {2,3,5,7,11,13}`, its shell residue `X mod M`
(`M = 30030`) and its anchor residue `X mod A` (`A = M+1 = 30031`, coprime by
adjacency). The winding number `K = ⌊X/M⌋` is **derived on demand** by
K-Elimination — for the adjacency pair it collapses to `K = (r_M − r_A) mod A`
with the inverse `M⁻¹ = A − c` read off the star-family construction, nothing
stored (G5-clean). Because K is derived rather than carried, the hot path has
no carry branch: every operation is a fixed set of component-wise modular
updates, order-invariant and reversible, and the operation trace is
input-independent.

**Audit.** `python3 -m cram_fhe.audit` runs five sections: oracle-checked
substrate identities; the six A2 gates (G1 invertibility, G2 order-invariance,
G3 i.i.d., G4 arrow coherence, G5 derivation, G6 custody) on every evaluator
construct plus a deliberate negative control; a 4-lap fiber-census emissions
harness; a 300-chain toy-BFV roundtrip battery under a live arrow monitor
(`E(t) = [Δv − Δr − M·ΔK]_A = 0`, K-Elimination soundness, carry provenance);
and an operation-trace uniformity probe. The single one-way step, rescale by
Δ, is declared and METERED: its `H_shadow = log₂Δ` is exactly the noise budget
spent.

**Claim discipline.** Read `docs/CLAIM_SCOPE.md` before quoting any result,
and `docs/PROOF_SKETCHES.md` for the proof-sketch register — one entry per
mathematical claim the code relies on, with status per the verification
policy (machine-checked Lean/Coq artifact named, or proof sketch + audit
witness).
In particular: the audit establishes freedom from *algorithmic* emissions and
a uniform op-trace, which is a *precondition* for constant-time
implementation — it is **not** a physical side-channel elimination claim, and
the toy parameters (`t=30, Δ=1001, Q=30030`) carry no lattice security.

```
python3 -m cram_fhe.audit          # full audit, all gate tables
python3 -m cram_fhe.a2_suite       # vendored A2 suite self-test + references
python3 -m pytest tests/ -q        # fast regression subset
```

Provenance: axioms and identities follow the CRAM/QMNF formal proof compendium
(A1 zero-float / A2 no synthetic emissions; Universal Projection,
K-Elimination, star-family inverse, adjacency, one-wave digits). The A2 gate
suite is vendored in `cram_fhe/a2_suite.py`; its gate derivations are in
`docs/A2_GATES.md`.
