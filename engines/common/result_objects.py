"""Shared structured inputs and outputs for beam design engines."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import math

from .validation import validate_non_negative, validate_positive


class DesignCode(str, Enum):
    """Supported design code families for current beam engines."""

    ACI318_99 = "ACI318-99, EIT 1008-38"
    ACI318_11 = "ACI318-11"
    ACI318_14 = "ACI318-14"
    ACI318_19 = "ACI318-19"
    ACI318_25 = "ACI318-25"


class ShearSpacingMode(str, Enum):
    """How the provided stirrup spacing is selected."""

    AUTO = "Auto"
    MANUAL = "Manual"


@dataclass(slots=True)
class BeamSectionInput:
    """Rectangular beam section dimensions used by beam engines."""

    width_cm: float = 20.0
    depth_cm: float = 40.0
    cover_cm: float = 4.0
    minimum_clear_spacing_cm: float = 2.5

    def __post_init__(self) -> None:
        validate_positive(self.width_cm, "width_cm")
        validate_positive(self.depth_cm, "depth_cm")
        validate_non_negative(self.cover_cm, "cover_cm")
        validate_positive(self.minimum_clear_spacing_cm, "minimum_clear_spacing_cm")
        if self.cover_cm >= self.depth_cm:
            raise ValueError("cover_cm must be smaller than depth_cm.")


@dataclass(slots=True)
class RebarGroupInput:
    """A bar group with a common diameter and count."""

    diameter_mm: int | None = None
    count: int = 0

    def __post_init__(self) -> None:
        if self.diameter_mm == 0:
            self.diameter_mm = None
        if self.count < 0:
            raise ValueError("count must be zero or greater.")
        if self.diameter_mm is not None and self.diameter_mm < 0:
            raise ValueError("diameter_mm must be positive when provided.")
        if self.count == 0 and self.diameter_mm is None:
            return
        if self.count == 0 or self.diameter_mm is None:
            raise ValueError("diameter_mm and count must both be provided for a rebar group.")

    @property
    def diameter_cm(self) -> float:
        if self.diameter_mm is None:
            return 0.0
        return self.diameter_mm / 10.0

    @property
    def area_cm2(self) -> float:
        if self.diameter_mm is None or self.count == 0:
            return 0.0
        return (math.pi * (self.diameter_cm**2) / 4.0) * self.count


@dataclass(slots=True)
class RebarLayerInput:
    """A reinforcement layer with corner bars and optional middle bars."""

    group_a: RebarGroupInput = field(default_factory=RebarGroupInput)
    group_b: RebarGroupInput = field(default_factory=RebarGroupInput)

    def __post_init__(self) -> None:
        if self.group_a.count not in {0, 2}:
            raise ValueError("group_a count must be 0 or 2 because group_a represents corner bars.")
        if self.group_b.count > 0 and self.group_a.count != 2:
            raise ValueError("group_a corner bars must be provided when group_b middle bars are used.")

    def groups(self) -> tuple[RebarGroupInput, RebarGroupInput]:
        return (self.group_a, self.group_b)

    @property
    def total_bars(self) -> int:
        return self.group_a.count + self.group_b.count

    @property
    def area_cm2(self) -> float:
        return self.group_a.area_cm2 + self.group_b.area_cm2


@dataclass(slots=True)
class ReinforcementArrangementInput:
    """Up to three reinforcement layers used by beam design engines."""

    layer_1: RebarLayerInput = field(default_factory=RebarLayerInput)
    layer_2: RebarLayerInput = field(default_factory=RebarLayerInput)
    layer_3: RebarLayerInput = field(default_factory=RebarLayerInput)

    def layers(self) -> tuple[RebarLayerInput, RebarLayerInput, RebarLayerInput]:
        return (self.layer_1, self.layer_2, self.layer_3)

    @property
    def total_area_cm2(self) -> float:
        return sum(layer.area_cm2 for layer in self.layers())


@dataclass(slots=True)
class LayerSpacingResult:
    """Clear spacing status for one reinforcement layer."""

    layer_index: int
    group_a_diameter_mm: int | None
    group_a_count: int
    group_b_diameter_mm: int | None
    group_b_count: int
    spacing_cm: float | None
    required_spacing_cm: float | None
    status: str
    message: str = ""


@dataclass(slots=True)
class ReinforcementSpacingResults:
    """Clear spacing results for a full reinforcement arrangement."""

    layer_1: LayerSpacingResult
    layer_2: LayerSpacingResult
    layer_3: LayerSpacingResult
    overall_status: str

    def layers(self) -> tuple[LayerSpacingResult, LayerSpacingResult, LayerSpacingResult]:
        return (self.layer_1, self.layer_2, self.layer_3)


@dataclass(slots=True)
class BeamGeometryResults:
    """Derived section properties reused by moment and shear engines."""

    section_area_cm2: float
    gross_moment_of_inertia_cm4: float
    cover_plus_stirrup_cm: float
    positive_compression_centroid_d_prime_cm: float
    positive_tension_centroid_from_bottom_d_cm: float
    negative_compression_centroid_from_bottom_cm: float | None
    negative_tension_centroid_from_top_cm: float | None
    d_plus_cm: float
    d_minus_cm: float | None
    positive_compression_spacing: ReinforcementSpacingResults
    positive_tension_spacing: ReinforcementSpacingResults
    negative_compression_spacing: ReinforcementSpacingResults | None
    negative_tension_spacing: ReinforcementSpacingResults | None

