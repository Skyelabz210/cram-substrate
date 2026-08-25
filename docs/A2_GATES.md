# Gate Reference

Contents: G1 invertibility · G2 order-invariance · G3 i.i.d. · G4 arrow coherence ·
G5 derivation · G6 custody · Coverage and blind spots · Reference verdicts

---

## G1 — invertibility (fiber census)

Enumerate the construct over its domain, bucket inputs by output, and take the largest
fiber L. Then H_shadow = log₂L, and H_shadow = 0 exactly when the map is a bijection.

This is the same quantity the transition-defect formulation measures from the other
side: a step that drops a carry has fiber L > 1, and the E(t) defect of G4 is nonzero on
exactly those steps. Two instruments, one emission.

**Why fiber census rather than a reversibility attempt:** trying to invert tells you
whether *your* inverse works. Counting fibers tells you whether *any* inverse could.

**Declared one-way.** A rescale by Δ has fibers of size Δ, so H_shadow = log₂Δ per
coefficient — and that is precisely the sub-Δ noise interval being discarded. The entropy
ledger and the noise budget are the same number. Declaring the operator converts the
verdict from FAIL to METERED. The declaration is the contract; an undeclared one-way step
is a fault regardless of how small the loss is.

---

## G2 — order-invariance (the cascade detector)

Two probes:

1. **Permutation.** Run the step with the lane evaluation order shuffled. A compliant
   construct is a product of independent lane maps, so the order cannot matter.
2. **Taint.** Corrupt one lane's *output* slot mid-flight. A compliant construct's other
   lanes are unaffected, because a lane may read another lane's *input residue* but never
   another lane's *running output*.

Garner fails probe 1 by construction: digit *i* is computed against the accumulated value
of digits 0..*i*−1, so permuting the lanes changes every digit. In the reference run,
509 of 600 permutations changed the result.

**This gate is what makes the "A2 = no cross-lane traffic" reading wrong.** Universal
Projection reads every lane and passes: each lane contributes independently to a linear
combination, and no running value is threaded through. The distinction is cascade vs
combination, not one lane vs many.

---

## G3 — i.i.d. (exact pair factorization)

For each lane pair (a, b), enumerate all a·b states and count the joint occurrences of
(x mod a, x mod b). Independence holds exactly when every joint count is equal and the
support is complete — which happens exactly when gcd(a, b) = 1.

Never sample. Independence is proved by exact factorization; dependence is proved by an
exact rational witness. A statistical test would answer a different question and would
answer it approximately, which A1 does not permit.

**A G3 failure is usually not a fault.** Lanes that share a factor are a *syndrome
regime*: the redundancy is free integrity checking, and the shared-factor resolver handles
division there. Report the regime, don't refuse the lane.

---

## G4 — arrow coherence

Two invariants on the carried identity (r, K) against shell M and anchor A:

- **Transition defect** E(t) = [Δv − Δr − M·Δκ]_A must be 0 across every step, including
  lap crossings and transduction crossings. It fires on a dropped carry and on
  frame-confused winding.
- **Carry provenance** ΔK = 1 iff r = M − 1, and 0 otherwise. The unit carry has exactly
  one legitimate cause; a ΔK with any other provenance is manufactured.

Applicable only when the construct declares a shell and anchor. Constructs with no carried
winding skip this gate rather than being credited with passing it.

---

## G5 — derivation (the separator)

Every constant the construct reads at run time must come with a derivation that
reproduces it from the construction. Stored values fail.

**Why this cannot be folded into G1.** The precomputed-constant recovery path is a perfect
bijection: fiber L = 1, H_shadow = 0, E(t) = 0, joints factorize. It passes every other
gate in the suite and it is still an A2 violation, because it carries state that is not
derivable — the exact thing the axiom's "no precomputed constants" clause names. Emission
gate and A2 gate are different gates. This construct is kept in the reference set
permanently as the proof that they are.

**The derivations that make constants unnecessary:**
- Star family A = c·M + 1 ⇒ M⁻¹ mod A = A − c, read off the construction, no egcd.
- Adjacency A = P + 1 ⇒ coprimality by the Bezout identity 1·(P+1) − 1·P = 1, which is an
  identity rather than a test, so nothing is stored and nothing is computed.
- Tower ratios: every shell's inverse at every later anchor is a negated integer tower
  ratio read from the construction.

---

## G6 — custody (the blind spot)

A **coherent ghost** is a state that is arithmetically valid, sits at the correct winding
level, and was never produced by an authorized step. Every arithmetic detector passes it,
because there is nothing arithmetically wrong with it — that is what makes it coherent.

Custody is therefore not an optional extra: it is the only gate that closes this case.
The blind-spot argument runs: lineage is *definitionally* complete (a state either has an
authorized provenance or it does not), the arrow is *dynamically* complete (it catches
every illegitimate transition), and the remaining detectors are cheap monitors that catch
the same faults earlier and faster.

---

## Coverage and blind spots

| Fault | Caught by |
|---|---|
| mixed-radix cascade | G2 |
| dropped carry | G1 + G4 |
| quotient discard | G1 |
| stored CRT constant | **G5 only** |
| frame-confused winding | G4 |
| correlated lanes | G3 |
| coherent ghost | **G6 only** |
| Fermat inverse on a composite modulus | none — this is a *tooling* error, guarded by using extended Euclid throughout, not detected after the fact |

The last row matters. A wrong inverse produces a construct that may pass every gate while
computing the wrong thing, because the gates test structure, not arithmetic truth against
an oracle. Always pair the suite with an oracle check on the construct's actual output.

---

## Reference verdicts (regression baseline)

| Construct | Verdict | Gate |
|---|---|---|
| Universal Projection → 39 (shared-factor target) | COMPLIANT | — |
| K-Elimination, star pair, derived inverse | COMPLIANT | — |
| Fifth Operator, lanewise quotient | COMPLIANT | — |
| Garner / mixed-radix reconstruction | VIOLATION | G2 |
| Recovery via precomputed constant | VIOLATION | G5 |
| Quotient discard (K dropped) | VIOLATION | G1 |
| Rescale by Δ (declared one-way) | COMPLIANT, metered | G1 METERED |

If a change to the suite alters any row above, the suite changed its mind about something
canonical — investigate before accepting.
