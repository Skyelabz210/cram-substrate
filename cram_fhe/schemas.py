"""Heterogeneous operator schemas (chimeras) over a CRAM basis.

The operator alphabet is the eight root operators of the CRAM Operator Atlas:

    A add   S sub   M mul   D div (a·b⁻¹)   Q sqr   N neg   I inv   _ id

A schema assigns one operator per lane; the output is a chimera — an element
of the product ring ∏ Z/pᵢZ that is generally NOT in the image of the
diagonal embedding, i.e. it corresponds to no single integer computed by one
homogeneous operation.  Formal definition (Chimera white paper §2.3):

    χ_S(a, b) = φ⁻¹( F₁(a mod m₁, b mod m₁), …, F_k(a mod m_k, b mod m_k) )

Consequences this module enforces and tests rely on:

  * Homogeneous schemas ARE the ring homomorphism (theorem-stack INV-2):
    χ_AAAA…(a,b) = (a+b) mod M, χ_MMMM… = (a·b) mod M, χ_SSSS… = (a−b) mod M.
    (The Operator Atlas's named-schema values — e.g. AAAAA(100,7) = 5,447 —
    are the earlier chimera-1 VARIANT's single-integer lift of the tuple, a
    convention the later corpus retired as "the chimera-1 trap"
    (cram_machine.rs).  This module implements the white-paper/machine
    variant, where the formal definition and INV-2 govern and heterogeneous
    outputs are residue tuples, not integers.)
  * Division/inverse lanes refuse non-units instead of corrupting them
    (the Fifth-Operator convention; E-DIV taxonomy).
  * Reconstruction for display uses parallel-summation CRT (the Lagrange
    basis sum — every term independent), never Garner/MRC.  Hot-path code
    never reconstructs at all (POA-7: reconstruction is output only).

A1: exact integers throughout.
"""
from __future__ import annotations

from .substrate import inv_mod

ATLAS_BASIS = (3, 5, 7, 11, 13)          # 5-lane atlas basis, M = 15015

OPERATOR_DEGREE = {
    # polynomial degree of the lane map (Atlas table); I is a degree-1
    # rational map (Möbius) whose polynomial representative has degree p-2,
    # so polynomial-DKAM does not cover it — flagged separately.
    "A": 1, "S": 1, "M": 2, "D": 2, "Q": 2, "N": 1, "_": 1, "I": None,
}


def _lane_op(code: str, a: int, b: int, p: int) -> int:
    if code == "A":
        return (a + b) % p
    if code == "S":
        return (a - b) % p
    if code == "M":
        return (a * b) % p
    if code == "D":
        try:
            return (a * inv_mod(b, p)) % p
        except ValueError:
            return a % p                    # non-unit divisor: refuse, don't corrupt
    if code == "Q":
        return (a * a) % p
    if code == "N":
        return (-a) % p
    if code == "I":
        try:
            return inv_mod(a, p)
        except ValueError:
            return a % p                    # non-unit: refuse, don't corrupt
    if code == "_":
        return a % p
    raise ValueError(f"unknown operator {code!r}")


def apply_schema(schema: str, a: int, b: int, basis=ATLAS_BASIS) -> tuple:
    """Chimera residue tuple χ_S(a, b) — a product-ring element.

    The tuple is the object; it has no winding and, for heterogeneous
    schemas, no single-integer identity.  Reconstruction (below) is a
    display/projection convenience only.
    """
    if len(schema) != len(basis):
        raise ValueError("schema length must equal lane count")
    return tuple(_lane_op(c, a % p, b % p, p) for c, p in zip(schema, basis))


def parallel_summation_crt(residues: tuple, basis=ATLAS_BASIS) -> int:
    """φ⁻¹ by the Lagrange/parallel-summation form (compendium Theorem 1.1):
    every term rᵢ·Mᵢ·(Mᵢ⁻¹ mod pᵢ) is computed independently; no digit reads
    any other digit.  Cold path (display only), and still cascade-free."""
    m = 1
    for p in basis:
        m *= p
    total = 0
    for r, p in zip(residues, basis):
        mi = m // p
        total += r * mi * inv_mod(mi, p)
    return total % m


def dkam_max_degree(schema: str) -> int | None:
    """Largest polynomial lane degree, or None if the schema contains an
    inverse lane (rational map — outside polynomial DKAM)."""
    degs = [OPERATOR_DEGREE[c] for c in schema]
    return None if None in degs else max(degs)


def schema_census(n_lanes: int, alphabet: int = 8) -> int:
    """Exact operator-schema count: alphabet ** n_lanes."""
    return alphabet ** n_lanes


def matches_homogeneous(residues: tuple, a: int, b: int, basis=ATLAS_BASIS) -> set:
    """Which homogeneous operations ∘ ∈ {+, −, ×} satisfy χ = φ(a ∘ b)?

    Every residue tuple over a coprime basis is φ(x) for exactly one
    x mod M; the chimera's point is that for a heterogeneous schema that x
    is NOT any single-operation result.  Returns the (possibly empty) set of
    homogeneous ops the tuple coincides with — empty = genuine chimera."""
    hits = set()
    for name, val in (("add", a + b), ("sub", a - b), ("mul", a * b)):
        if all(r == val % p for r, p in zip(residues, basis)):
            hits.add(name)
    return hits
