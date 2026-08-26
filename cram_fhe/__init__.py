"""CRAM-FHE fork: leveled FHE evaluation carried entirely in the i.i.d.-safe
reversible residue space, with A2 arrow/emission checking on every transition.

Exact integers only (A1). Modular inverses by extended Euclid or read off the
construction (star family / adjacency) — never Fermat.
"""
from .substrate import (
    SAFE_BASIS, M_SHELL, A_ANCHOR, CRAMState, ArrowMonitor,
    k_eliminate, universal_projection, egcd, inv_mod,
)
from .toy_bfv import ToyBFV, Ciphertext
from .starframe import StarFrame, FrameState, count_valid_multipliers

__all__ = [
    "SAFE_BASIS", "M_SHELL", "A_ANCHOR", "CRAMState", "ArrowMonitor",
    "k_eliminate", "universal_projection", "egcd", "inv_mod",
    "ToyBFV", "Ciphertext", "StarFrame", "FrameState", "count_valid_multipliers",
]
