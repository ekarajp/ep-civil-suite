"""Public calculator for the reusable beam shear design engine."""

from __future__ import annotations

import math

from engines.common import DesignCode, calculate_beam_geometry
from engines.common.geometry import BeamGeometryInputData
from engines.common.units import auto_select_spacing_cm, bar_area_cm2, safe_divide

from .checks import build_shear_review_note
from .formulas import (
    calculate_aci318_19_size_effect_factor,
    calculate_aci318_19_vc_max_kg,
    calculate_av_min_per_spacing_cm,
    calculate_shear_phi,
)
from .inputs import ShearBeamInput, ShearDesignResult


def design_shear_beam(input_data: ShearBeamInput) -> ShearDesignResult:
    """Design beam shear reinforcement with the current app logic."""
    geometry_results = calculate_beam_geometry(
        BeamGeometryInputData(
            geometry=input_data.geometry,
            positive_compression_reinforcement=input_data.positive_compression_reinforcement,
            positive_tension_reinforcement=input_data.positive_tension_reinforcement,
            stirrup_diameter_mm=input_data.stirrup_diameter_mm,
            negative_compression_reinforcement=input_data.negative_compression_reinforcement,
            negative_tension_reinforcement=input_data.negative_tension_reinforcement,
            include_negative=input_data.include_negative_geometry,
        )
    )
    phi_shear = calculate_shear_phi(input_data.design_code)
    d_plus_cm = geometry_results.d_plus_cm
    sqrt_fc = math.sqrt(input_data.materials.concrete_strength_ksc)
    base_vc_kg = 0.53 * sqrt_fc * input_data.geometry.width_cm * d_plus_cm
    vs_max_kg = 2.1 * sqrt_fc * input_data.geometry.width_cm * d_plus_cm
    phi_vs_max_kg = phi_shear * vs_max_kg
    av_cm2 = bar_area_cm2(input_data.stirrup_diameter_mm) * input_data.legs_per_plane
    av_min_per_spacing_cm = calculate_av_min_per_spacing_cm(
        sqrt_fc,
        input_data.geometry.width_cm,
        input_data.materials.shear_steel_yield_ksc,
    )
    s_max_from_av_cm = min(
        safe_divide(av_cm2 * input_data.materials.shear_steel_yield_ksc, 0.2 * sqrt_fc * input_data.geometry.width_cm),
        safe_divide(av_cm2 * input_data.materials.shear_steel_yield_ksc, 3.5 * input_data.geometry.width_cm),
    )

    def _calculate_shear_state(vc_kg_value: float) -> tuple[float, float, float, float, float, float]:
        phi_vc_kg_value = phi_shear * vc_kg_value
        phi_vs_required_kg_value = max(input_data.factored_shear_kg - phi_vc_kg_value, 0.0)
        nominal_vs_required_kg_value = safe_divide(phi_vs_required_kg_value, phi_shear)
        if nominal_vs_required_kg_value <= 1.1 * sqrt_fc * input_data.geometry.width_cm * d_plus_cm:
            s_max_from_vs_cm_value = min(d_plus_cm / 2.0, 60.0)
        else:
            s_max_from_vs_cm_value = min(d_plus_cm / 4.0, 30.0)

        if phi_vs_required_kg_value == 0:
            strength_spacing_cm_value = math.inf
        else:
            strength_spacing_cm_value = safe_divide(
                av_cm2 * input_data.materials.shear_steel_yield_ksc * d_plus_cm,
                nominal_vs_required_kg_value,
            )

        required_spacing_cm_value = min(strength_spacing_cm_value, s_max_from_av_cm, s_max_from_vs_cm_value)
        provided_spacing_cm_value = (
            auto_select_spacing_cm(required_spacing_cm_value)
            if input_data.spacing_mode == input_data.spacing_mode.AUTO
            else input_data.provided_spacing_cm
        )
        return (
            phi_vc_kg_value,
            phi_vs_required_kg_value,
            nominal_vs_required_kg_value,
            s_max_from_vs_cm_value,
            required_spacing_cm_value,
            provided_spacing_cm_value,
        )

    (
        phi_vc_kg,
        phi_vs_required_kg,
        nominal_vs_required_kg,
        s_max_from_vs_cm,
        required_spacing_cm,
        provided_spacing_cm,
    ) = _calculate_shear_state(base_vc_kg)

    av_min_cm2 = av_min_per_spacing_cm * provided_spacing_cm
    size_effect_factor = 1.0
    size_effect_applied = False
    vc_kg = base_vc_kg
    if input_data.design_code == DesignCode.ACI318_19 and av_cm2 < av_min_cm2 - 1e-9:
        size_effect_factor = calculate_aci318_19_size_effect_factor(d_plus_cm)
        size_effect_applied = size_effect_factor < 1.0 - 1e-9
        vc_kg = base_vc_kg * size_effect_factor
        (
            phi_vc_kg,
            phi_vs_required_kg,
            nominal_vs_required_kg,
            s_max_from_vs_cm,
            required_spacing_cm,
            provided_spacing_cm,
        ) = _calculate_shear_state(vc_kg)
        av_min_cm2 = av_min_per_spacing_cm * provided_spacing_cm

    vc_max_kg: float | None = None
    vc_capped_by_max = False
    if input_data.design_code == DesignCode.ACI318_19:
        vc_max_kg = calculate_aci318_19_vc_max_kg(
            sqrt_fc,
            input_data.geometry.width_cm,
            d_plus_cm,
            size_effect_factor,
        )
        if vc_kg > vc_max_kg + 1e-9:
            vc_kg = vc_max_kg
            vc_capped_by_max = True
            (
                phi_vc_kg,
                phi_vs_required_kg,
                nominal_vs_required_kg,
                s_max_from_vs_cm,
                required_spacing_cm,
                provided_spacing_cm,
            ) = _calculate_shear_state(vc_kg)
            av_min_cm2 = av_min_per_spacing_cm * provided_spacing_cm

    vs_provided_kg = safe_divide(
        av_cm2 * input_data.materials.shear_steel_yield_ksc * d_plus_cm,
        provided_spacing_cm,
    )
    phi_vs_provided_kg = phi_shear * vs_provided_kg
    effective_vs_kg = min(vs_provided_kg, vs_max_kg)
    vn_kg = vc_kg + effective_vs_kg
    phi_vn_kg = phi_shear * vn_kg
    capacity_ratio = safe_divide(input_data.factored_shear_kg, phi_vn_kg)
    phi_vn_limit_kg = phi_vc_kg + phi_vs_max_kg

    spacing_ok = provided_spacing_cm <= required_spacing_cm + 1e-9
    strength_limit_ok = nominal_vs_required_kg <= vs_max_kg + 1e-9
    capacity_ok = phi_vn_kg >= input_data.factored_shear_kg
    section_change_required = input_data.factored_shear_kg > phi_vn_limit_kg + 1e-9
    design_status = "PASS" if spacing_ok and strength_limit_ok and capacity_ok else "FAIL"

    section_change_note = ""
    if section_change_required:
        section_change_note = (
            "Applied shear exceeds the maximum design shear strength of the current section, even when the shear reinforcement contribution is limited to Vs,max. "
            "Increase the beam section and/or revise the section properties."
        )
    review_note = build_shear_review_note(
        av_cm2=av_cm2,
        av_min_cm2=av_min_cm2,
        design_code_label=input_data.design_code.value,
        provided_spacing_cm=provided_spacing_cm,
        required_spacing_cm=required_spacing_cm,
        section_change_required=section_change_required,
        section_change_note=section_change_note,
        strength_limit_ok=strength_limit_ok,
        vc_capped_by_max=vc_capped_by_max,
        vc_max_kg=vc_max_kg,
        size_effect_factor=size_effect_factor,
        vs_provided_kg=vs_provided_kg,
        vs_max_kg=vs_max_kg,
    )

    return ShearDesignResult(
        phi=phi_shear,
        vc_kg=vc_kg,
        phi_vc_kg=phi_vc_kg,
        vc_max_kg=vc_max_kg,
        vc_capped_by_max=vc_capped_by_max,
        vs_max_kg=vs_max_kg,
        phi_vs_max_kg=phi_vs_max_kg,
        phi_vs_required_kg=phi_vs_required_kg,
        nominal_vs_required_kg=nominal_vs_required_kg,
        av_cm2=av_cm2,
        av_min_cm2=av_min_cm2,
        size_effect_factor=size_effect_factor,
        size_effect_applied=size_effect_applied,
        s_max_from_av_cm=s_max_from_av_cm,
        s_max_from_vs_cm=s_max_from_vs_cm,
        required_spacing_cm=required_spacing_cm,
        provided_spacing_cm=provided_spacing_cm,
        spacing_mode=input_data.spacing_mode,
        vs_provided_kg=vs_provided_kg,
        phi_vs_provided_kg=phi_vs_provided_kg,
        vn_kg=vn_kg,
        phi_vn_kg=phi_vn_kg,
        stirrup_spacing_cm=provided_spacing_cm,
        capacity_ratio=capacity_ratio,
        design_status=design_status,
        section_change_required=section_change_required,
        section_change_note=section_change_note,
        review_note=review_note,
    )

