"""Structured inputs for the torsion engine scaffold."""

from __future__ import annotations

from dataclasses import dataclass

from design.torsion import TorsionDesignInput, TorsionDesignMaterialInput, TorsionSectionGeometryInput


@dataclass(slots=True)
class TorsionBeamInput:
    """Wrapper input for the reusable torsion engine."""

    design: TorsionDesignInput
    geometry: TorsionSectionGeometryInput
    materials: TorsionDesignMaterialInput

