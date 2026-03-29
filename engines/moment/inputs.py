"""Structured inputs and outputs for the moment design engine."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from engines.common import (
    BeamSectionInput,
    DesignCode,
    MaterialPropertiesInput,
    MaterialPropertySettings,
    ReinforcementArrangementInput,
)
from engines.common.validation import validate_non_negative, validate_positive


class MomentDesignCase(str, Enum):
    """Moment-design mode used by the current beam applications."""

    POSITIVE = "positive"
    NEGATIVE_LEGACY = "negative_legacy"


@dataclass(slots=True)
class MomentBeamInput:
    """All data required to design one beam bending case."""

    design_code: DesignCode
    materials: MaterialPropertiesInput
    geometry: BeamSectionInput
    stirrup_diameter_mm: int
    factored_moment_kgm: float
    positive_compression_reinforcement: ReinforcementArrangementInput
    positive_tension_reinforcement: ReinforcementArrangementInput
    negative_compression_reinforcement: ReinforcementArrangementInput = field(default_factory=ReinforcementArrangementInput)
    negative_tension_reinforcement: ReinforcementArrangementInput = field(default_factory=ReinforcementArrangementInput)
    material_settings: MaterialPropertySettings = field(default_factory=MaterialPropertySettings)
    design_case: MomentDesignCase = MomentDesignCase.POSITIVE

    def __post_init__(self) -> None:
        validate_positive(self.stirrup_diameter_mm, "stirrup_diameter_mm")
        validate_non_negative(self.factored_moment_kgm, "factored_moment_kgm")


@dataclass(slots=True)
class MomentDesignResult:
    """Structured result returned by the moment design engine."""

    phi: float
    ru_kg_per_cm2: float
    rho_required: float
    as_required_cm2: float
    as_provided_cm2: float
    rho_provided: float
    rho_min: float
    rho_max: float
    as_min_cm2: float
    as_max_cm2: float
    as_status: str
    a_cm: float
    c_cm: float
    dt_cm: float
    ety: float
    et: float
    mn_kgm: float
    phi_mn_kgm: float
    ratio: float
    ratio_status: str
    design_status: str
    review_note: str = ""

