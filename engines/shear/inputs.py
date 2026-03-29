"""Structured inputs and outputs for the shear design engine."""

from __future__ import annotations

from dataclasses import dataclass, field

from engines.common import (
    BeamSectionInput,
    DesignCode,
    MaterialPropertiesInput,
    ReinforcementArrangementInput,
    ShearSpacingMode,
)
from engines.common.validation import validate_non_negative, validate_positive


@dataclass(slots=True)
class ShearBeamInput:
    """All data required to design beam shear reinforcement."""

    design_code: DesignCode
    materials: MaterialPropertiesInput
    geometry: BeamSectionInput
    factored_shear_kg: float
    stirrup_diameter_mm: int
    legs_per_plane: int
    spacing_mode: ShearSpacingMode
    provided_spacing_cm: float
    positive_compression_reinforcement: ReinforcementArrangementInput
    positive_tension_reinforcement: ReinforcementArrangementInput
    negative_compression_reinforcement: ReinforcementArrangementInput = field(default_factory=ReinforcementArrangementInput)
    negative_tension_reinforcement: ReinforcementArrangementInput = field(default_factory=ReinforcementArrangementInput)
    include_negative_geometry: bool = False

    def __post_init__(self) -> None:
        validate_non_negative(self.factored_shear_kg, "factored_shear_kg")
        validate_positive(self.stirrup_diameter_mm, "stirrup_diameter_mm")
        validate_positive(self.legs_per_plane, "legs_per_plane")
        validate_positive(self.provided_spacing_cm, "provided_spacing_cm")


@dataclass(slots=True)
class ShearDesignResult:
    """Structured result returned by the shear design engine."""

    phi: float
    vc_kg: float
    phi_vc_kg: float
    vc_max_kg: float | None
    vc_capped_by_max: bool
    vs_max_kg: float
    phi_vs_max_kg: float
    phi_vs_required_kg: float
    nominal_vs_required_kg: float
    av_cm2: float
    av_min_cm2: float
    size_effect_factor: float
    size_effect_applied: bool
    s_max_from_av_cm: float
    s_max_from_vs_cm: float
    required_spacing_cm: float
    provided_spacing_cm: float
    spacing_mode: ShearSpacingMode
    vs_provided_kg: float
    phi_vs_provided_kg: float
    vn_kg: float
    phi_vn_kg: float
    stirrup_spacing_cm: float
    capacity_ratio: float
    design_status: str
    section_change_required: bool = False
    section_change_note: str = ""
    review_note: str = ""

