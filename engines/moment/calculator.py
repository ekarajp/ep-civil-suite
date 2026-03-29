"""Public calculator for the reusable beam moment design engine."""

from __future__ import annotations

from engines.common import calculate_beam_geometry, calculate_material_properties
from engines.common.geometry import BeamGeometryInputData
from engines.common.units import diameter_cm, safe_divide

from .checks import calculate_as_status
from .formulas import ECU, calculate_flexural_phi, calculate_rho_max, calculate_rho_min, calculate_rho_required
from .inputs import MomentBeamInput, MomentDesignCase, MomentDesignResult


def design_moment_beam(input_data: MomentBeamInput) -> MomentDesignResult:
    """Design a rectangular reinforced-concrete beam for one bending case."""
    material_results = calculate_material_properties(input_data.materials, input_data.material_settings)
    geometry_results = calculate_beam_geometry(
        BeamGeometryInputData(
            geometry=input_data.geometry,
            positive_compression_reinforcement=input_data.positive_compression_reinforcement,
            positive_tension_reinforcement=input_data.positive_tension_reinforcement,
            stirrup_diameter_mm=input_data.stirrup_diameter_mm,
            negative_compression_reinforcement=input_data.negative_compression_reinforcement,
            negative_tension_reinforcement=input_data.negative_tension_reinforcement,
            include_negative=input_data.design_case == MomentDesignCase.NEGATIVE_LEGACY,
        )
    )

    if input_data.design_case == MomentDesignCase.POSITIVE:
        tension_reinforcement = input_data.positive_tension_reinforcement
        d_for_design_cm = geometry_results.d_plus_cm
        as_min_depth_cm = geometry_results.d_plus_cm
        mn_depth_cm = geometry_results.d_plus_cm
        first_tension_group = input_data.positive_tension_reinforcement.layer_1.group_a
        review_note = ""
    else:
        tension_reinforcement = input_data.negative_tension_reinforcement
        d_for_design_cm = geometry_results.d_minus_cm
        if d_for_design_cm is None:
            raise ValueError("Negative bending geometry is not available for the selected moment design case.")
        as_min_depth_cm = geometry_results.d_plus_cm
        mn_depth_cm = geometry_results.d_plus_cm
        first_tension_group = input_data.negative_tension_reinforcement.layer_1.group_a
        review_note = (
            "Negative-moment block currently uses d+ for As_min and Mn rather than d-. "
            "Manual engineering review is required before using this result for issued design documents."
        )

    as_provided_cm2 = tension_reinforcement.total_area_cm2
    rho_provided = safe_divide(as_provided_cm2, input_data.geometry.width_cm * d_for_design_cm)
    a_cm = safe_divide(
        as_provided_cm2 * input_data.materials.main_steel_yield_ksc,
        0.85 * input_data.materials.concrete_strength_ksc * input_data.geometry.width_cm,
    )
    c_cm = safe_divide(a_cm, material_results.beta_1)
    dt_cm = (
        input_data.geometry.depth_cm
        - input_data.geometry.cover_cm
        - diameter_cm(input_data.stirrup_diameter_mm)
        - (first_tension_group.diameter_cm / 2.0)
    )
    ety = safe_divide(input_data.materials.main_steel_yield_ksc, material_results.es_ksc)
    et = safe_divide(ECU * (dt_cm - c_cm), c_cm)
    phi = calculate_flexural_phi(input_data.design_code, et, ety)
    ru_kg_per_cm2 = safe_divide(
        input_data.factored_moment_kgm * 100.0,
        phi * input_data.geometry.width_cm * (d_for_design_cm**2),
    )
    rho_required = calculate_rho_required(
        input_data.materials.concrete_strength_ksc,
        input_data.materials.main_steel_yield_ksc,
        ru_kg_per_cm2,
    )
    rho_min = calculate_rho_min(
        input_data.design_code,
        input_data.materials.concrete_strength_ksc,
        input_data.materials.main_steel_yield_ksc,
    )
    rho_max = calculate_rho_max(
        input_data.design_code,
        input_data.materials.concrete_strength_ksc,
        input_data.materials.main_steel_yield_ksc,
        material_results.beta_1,
        material_results.es_ksc,
    )
    as_required_cm2 = rho_required * input_data.geometry.width_cm * d_for_design_cm
    as_min_cm2 = rho_min * input_data.geometry.width_cm * as_min_depth_cm
    as_max_cm2 = rho_max * input_data.geometry.width_cm * d_for_design_cm
    mn_kgm = as_provided_cm2 * input_data.materials.main_steel_yield_ksc * (mn_depth_cm - (a_cm / 2.0)) / 100.0
    phi_mn_kgm = mn_kgm * phi
    ratio = safe_divide(input_data.factored_moment_kgm, phi_mn_kgm)
    as_status = calculate_as_status(rho_provided, rho_min, rho_max)
    ratio_status = "OK" if phi_mn_kgm >= input_data.factored_moment_kgm else "NOT OK"
    design_status = "PASS" if as_status == "OK" and ratio_status == "OK" else "FAIL"

    return MomentDesignResult(
        phi=phi,
        ru_kg_per_cm2=ru_kg_per_cm2,
        rho_required=rho_required,
        as_required_cm2=as_required_cm2,
        as_provided_cm2=as_provided_cm2,
        rho_provided=rho_provided,
        rho_min=rho_min,
        rho_max=rho_max,
        as_min_cm2=as_min_cm2,
        as_max_cm2=as_max_cm2,
        as_status=as_status,
        a_cm=a_cm,
        c_cm=c_cm,
        dt_cm=dt_cm,
        ety=ety,
        et=et,
        mn_kgm=mn_kgm,
        phi_mn_kgm=phi_mn_kgm,
        ratio=ratio,
        ratio_status=ratio_status,
        design_status=design_status,
        review_note=review_note,
    )
