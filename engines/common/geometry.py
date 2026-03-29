"""Shared beam geometry and reinforcement spacing calculations."""

from __future__ import annotations

from dataclasses import dataclass, field
import math

from .result_objects import (
    BeamGeometryResults,
    BeamSectionInput,
    LayerSpacingResult,
    ReinforcementArrangementInput,
    ReinforcementSpacingResults,
)
from .units import diameter_cm, safe_divide
from .validation import validate_positive


@dataclass(slots=True)
class BeamGeometryInputData:
    """All reinforcement data needed to derive reusable beam geometry results."""

    geometry: BeamSectionInput
    positive_compression_reinforcement: ReinforcementArrangementInput
    positive_tension_reinforcement: ReinforcementArrangementInput
    stirrup_diameter_mm: int
    negative_compression_reinforcement: ReinforcementArrangementInput = field(default_factory=ReinforcementArrangementInput)
    negative_tension_reinforcement: ReinforcementArrangementInput = field(default_factory=ReinforcementArrangementInput)
    include_negative: bool = False

    def __post_init__(self) -> None:
        validate_positive(self.stirrup_diameter_mm, "stirrup_diameter_mm")


def calculate_reinforcement_spacing(
    geometry: BeamSectionInput,
    reinforcement: ReinforcementArrangementInput,
    stirrup_diameter_mm: int,
) -> ReinforcementSpacingResults:
    """Evaluate clear spacing for each reinforcement layer."""
    layer_results: list[LayerSpacingResult] = []
    overall_status = "OK"

    for layer_index, layer in enumerate(reinforcement.layers(), start=1):
        diameters_cm = [_group_diameter_cm(group) for group in layer.groups()]
        total_bars = layer.total_bars
        spacing_cm = _calculate_layer_spacing_cm(geometry, layer, stirrup_diameter_mm)

        required_spacing_cm: float | None
        status: str
        message = ""
        if total_bars == 0:
            required_spacing_cm = None
            spacing_value = None
            status = "N/A"
        elif total_bars == 1:
            required_spacing_cm = None
            spacing_value = None
            status = "OK"
            message = "Single bar in layer; clear spacing check is not governing."
        else:
            required_spacing_cm = max(
                geometry.minimum_clear_spacing_cm,
                diameters_cm[0],
                diameters_cm[1],
            )
            spacing_value = spacing_cm
            status = "OK" if spacing_cm >= required_spacing_cm else "NOT OK"
            if status == "NOT OK":
                message = (
                    f"Provided clear spacing {spacing_cm:.2f} cm is less than "
                    f"required {required_spacing_cm:.2f} cm."
                )
                overall_status = "NOT OK"

        layer_results.append(
            LayerSpacingResult(
                layer_index=layer_index,
                group_a_diameter_mm=layer.group_a.diameter_mm,
                group_a_count=layer.group_a.count,
                group_b_diameter_mm=layer.group_b.diameter_mm,
                group_b_count=layer.group_b.count,
                spacing_cm=spacing_value,
                required_spacing_cm=required_spacing_cm,
                status=status,
                message=message,
            )
        )

    return ReinforcementSpacingResults(
        layer_1=layer_results[0],
        layer_2=layer_results[1],
        layer_3=layer_results[2],
        overall_status=overall_status,
    )


def calculate_beam_geometry(input_data: BeamGeometryInputData) -> BeamGeometryResults:
    """Calculate reusable beam geometry values for moment and shear design."""
    geometry = input_data.geometry
    cover_plus_stirrup_cm = geometry.cover_cm + diameter_cm(input_data.stirrup_diameter_mm)

    positive_compression_centroid_cm = _calculate_centroid_from_face_cm(
        geometry,
        input_data.positive_compression_reinforcement,
        input_data.stirrup_diameter_mm,
        denominator_groups=((0, 0), (0, 1), (1, 0), (1, 1), (2, 0), (2, 1)),
    )
    positive_tension_centroid_from_bottom_cm = _calculate_centroid_from_face_cm(
        geometry,
        input_data.positive_tension_reinforcement,
        input_data.stirrup_diameter_mm,
        denominator_groups=((0, 0), (0, 1), (1, 0), (1, 1)),
    )

    negative_compression_centroid_cm: float | None = None
    negative_tension_centroid_from_top_cm: float | None = None
    d_minus_cm: float | None = None
    negative_compression_spacing: ReinforcementSpacingResults | None = None
    negative_tension_spacing: ReinforcementSpacingResults | None = None
    if input_data.include_negative:
        negative_compression_centroid_cm = _calculate_centroid_from_face_cm(
            geometry,
            input_data.negative_compression_reinforcement,
            input_data.stirrup_diameter_mm,
            denominator_groups=((0, 0), (0, 1), (1, 0), (1, 1), (2, 0), (2, 1)),
        )
        negative_tension_centroid_from_top_cm = _calculate_centroid_from_face_cm(
            geometry,
            input_data.negative_tension_reinforcement,
            input_data.stirrup_diameter_mm,
            denominator_groups=((0, 0), (0, 1), (1, 0), (1, 1)),
        )
        d_minus_cm = geometry.depth_cm - negative_tension_centroid_from_top_cm
        negative_compression_spacing = calculate_reinforcement_spacing(
            geometry,
            input_data.negative_compression_reinforcement,
            input_data.stirrup_diameter_mm,
        )
        negative_tension_spacing = calculate_reinforcement_spacing(
            geometry,
            input_data.negative_tension_reinforcement,
            input_data.stirrup_diameter_mm,
        )

    return BeamGeometryResults(
        section_area_cm2=geometry.width_cm * geometry.depth_cm,
        gross_moment_of_inertia_cm4=geometry.width_cm * (geometry.depth_cm**3) / 12.0,
        cover_plus_stirrup_cm=cover_plus_stirrup_cm,
        positive_compression_centroid_d_prime_cm=positive_compression_centroid_cm,
        positive_tension_centroid_from_bottom_d_cm=positive_tension_centroid_from_bottom_cm,
        negative_compression_centroid_from_bottom_cm=negative_compression_centroid_cm,
        negative_tension_centroid_from_top_cm=negative_tension_centroid_from_top_cm,
        d_plus_cm=geometry.depth_cm - positive_tension_centroid_from_bottom_cm,
        d_minus_cm=d_minus_cm,
        positive_compression_spacing=calculate_reinforcement_spacing(
            geometry,
            input_data.positive_compression_reinforcement,
            input_data.stirrup_diameter_mm,
        ),
        positive_tension_spacing=calculate_reinforcement_spacing(
            geometry,
            input_data.positive_tension_reinforcement,
            input_data.stirrup_diameter_mm,
        ),
        negative_compression_spacing=negative_compression_spacing,
        negative_tension_spacing=negative_tension_spacing,
    )


def _calculate_centroid_from_face_cm(
    geometry: BeamSectionInput,
    reinforcement: ReinforcementArrangementInput,
    stirrup_diameter_mm: int,
    denominator_groups: tuple[tuple[int, int], ...],
) -> float:
    numerator = 0.0
    layers = reinforcement.layers()

    for layer_index, layer in enumerate(layers):
        base_distance_cm = _layer_base_distance_cm(
            geometry,
            reinforcement,
            stirrup_diameter_mm,
            layer_index,
        )
        for group in layer.groups():
            numerator += (base_distance_cm + (_group_diameter_cm(group) / 2.0)) * group.count

    denominator = 0
    for layer_index, group_index in denominator_groups:
        layer = layers[layer_index]
        group = layer.groups()[group_index]
        denominator += group.count

    return safe_divide(numerator, denominator)


def _layer_base_distance_cm(
    geometry: BeamSectionInput,
    reinforcement: ReinforcementArrangementInput,
    stirrup_diameter_mm: int,
    layer_index: int,
) -> float:
    base_distance_cm = geometry.cover_cm + diameter_cm(stirrup_diameter_mm)
    layers = reinforcement.layers()

    for previous_index in range(layer_index):
        previous_layer = layers[previous_index]
        previous_diameter_a_cm = _group_diameter_cm(previous_layer.group_a)
        previous_diameter_b_cm = _group_diameter_cm(previous_layer.group_b)
        base_distance_cm += max(previous_diameter_a_cm, previous_diameter_b_cm) + max(
            geometry.minimum_clear_spacing_cm,
            previous_diameter_a_cm,
            previous_diameter_b_cm,
        )

    return base_distance_cm


def _calculate_layer_spacing_cm(
    geometry: BeamSectionInput,
    layer,
    stirrup_diameter_mm: int,
) -> float:
    total_bars = layer.total_bars
    if total_bars <= 1:
        return math.nan
    clear_width_cm = geometry.width_cm - (geometry.cover_cm * 2.0) - (diameter_cm(stirrup_diameter_mm) * 2.0)
    occupied_width_cm = (
        _group_diameter_cm(layer.group_a) * layer.group_a.count
        + _group_diameter_cm(layer.group_b) * layer.group_b.count
    )
    return (clear_width_cm - occupied_width_cm) / (total_bars - 1)


def _group_diameter_cm(group) -> float:
    return diameter_cm(group.diameter_mm)
