"""Public calculator for the torsion engine scaffold."""

from __future__ import annotations

from design.torsion import calculate_torsion_design

from .inputs import TorsionBeamInput


def design_torsion_beam(input_data: TorsionBeamInput):
    """Run torsion design using the current standalone torsion module."""
    return calculate_torsion_design(input_data.design, input_data.geometry, input_data.materials)
