from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import math

from .torsion_units import cm2_to_mm2, cm_to_mm, kgf_m_to_n_mm, ksc_to_mpa, mm2_to_cm2, n_mm_to_kgf_m


TORSION_PHI = 0.75
NORMAL_WEIGHT_LAMBDA = 1.0
STANDARD_TRUSS_ANGLE_DEG = 45.0
STANDARD_COT_THETA = 1.0
ACI_318_19_ALT_PROCEDURE_MESSAGE = (
    "ACI 318-19 allows an alternative torsion design procedure for this geometry, "
    "but this app currently uses the standard torsion design method only."
)


class TorsionDesignCode(str, Enum):
    ACI318_99 = "ACI 318-99"
    ACI318_11 = "ACI 318-11"
    ACI318_14 = "ACI 318-14"
    ACI318_19 = "ACI 318-19"


class TorsionDemandType(str, Enum):
    EQUILIBRIUM = "equilibrium torsion"
    COMPATIBILITY = "compatibility torsion"


@dataclass(slots=True)
class TorsionDesignInput:
    enabled: bool = False
    factored_torsion_kgfm: float = 0.0
    design_code: TorsionDesignCode = TorsionDesignCode.ACI318_19
    demand_type: TorsionDemandType = TorsionDemandType.EQUILIBRIUM
    provided_longitudinal_steel_cm2: float = 0.0
    provided_longitudinal_bar_diameter_mm: int | None = None
    provided_longitudinal_bar_count: int = 0
    provided_longitudinal_bar_fy_ksc: float = 4000.0

    def __post_init__(self) -> None:
        _validate_non_negative(self.factored_torsion_kgfm, "factored_torsion_kgfm")
        _validate_non_negative(self.provided_longitudinal_steel_cm2, "provided_longitudinal_steel_cm2")
        _validate_non_negative(self.provided_longitudinal_bar_count, "provided_longitudinal_bar_count")
        _validate_positive(self.provided_longitudinal_bar_fy_ksc, "provided_longitudinal_bar_fy_ksc")
        if self.provided_longitudinal_bar_diameter_mm is not None:
            _validate_positive(self.provided_longitudinal_bar_diameter_mm, "provided_longitudinal_bar_diameter_mm")
        if (self.provided_longitudinal_bar_diameter_mm is None) != (self.provided_longitudinal_bar_count == 0):
            if self.provided_longitudinal_bar_diameter_mm is None and self.provided_longitudinal_bar_count == 0:
                return
            raise ValueError("provided_longitudinal_bar_diameter_mm and provided_longitudinal_bar_count must be given together.")

    @property
    def resolved_provided_longitudinal_steel_cm2(self) -> float:
        if self.provided_longitudinal_bar_diameter_mm is None or self.provided_longitudinal_bar_count == 0:
            return self.provided_longitudinal_steel_cm2
        diameter_cm = self.provided_longitudinal_bar_diameter_mm / 10.0
        return (math.pi * (diameter_cm**2) / 4.0) * self.provided_longitudinal_bar_count


@dataclass(slots=True)
class TorsionSectionGeometryInput:
    width_cm: float
    depth_cm: float
    cover_cm: float
    stirrup_diameter_mm: int
    stirrup_spacing_cm: float
    stirrup_legs: int

    def __post_init__(self) -> None:
        _validate_positive(self.width_cm, "width_cm")
        _validate_positive(self.depth_cm, "depth_cm")
        _validate_non_negative(self.cover_cm, "cover_cm")
        _validate_positive(self.stirrup_diameter_mm, "stirrup_diameter_mm")
        _validate_positive(self.stirrup_spacing_cm, "stirrup_spacing_cm")
        _validate_positive(self.stirrup_legs, "stirrup_legs")


@dataclass(slots=True)
class TorsionDesignMaterialInput:
    concrete_strength_ksc: float
    transverse_steel_yield_ksc: float
    longitudinal_steel_yield_ksc: float
    lightweight_lambda: float = NORMAL_WEIGHT_LAMBDA

    def __post_init__(self) -> None:
        _validate_positive(self.concrete_strength_ksc, "concrete_strength_ksc")
        _validate_positive(self.transverse_steel_yield_ksc, "transverse_steel_yield_ksc")
        _validate_positive(self.longitudinal_steel_yield_ksc, "longitudinal_steel_yield_ksc")
        _validate_positive(self.lightweight_lambda, "lightweight_lambda")


@dataclass(frozen=True, slots=True)
class TorsionStep:
    variable: str
    equation: str
    substitution: str
    result: str
    units: str
    clause: str
    note: str = ""
    status: str = ""


@dataclass(slots=True)
class TorsionDesignResults:
    enabled: bool
    code_version: str
    demand_type: TorsionDemandType
    design_method: str
    status: str
    pass_fail_summary: str
    tu_kgfm: float
    threshold_torsion_kgfm: float
    cracking_torsion_kgfm: float | None
    acp_mm2: float
    pcp_mm: float
    aoh_mm2: float
    ao_mm2: float
    ph_mm: float
    wall_thickness_mm: float
    aspect_ratio_h_over_bt: float
    transverse_reinf_required_mm2_per_mm: float
    transverse_reinf_required_governing: str
    longitudinal_reinf_required_mm2: float
    longitudinal_reinf_required_governing: str
    transverse_reinf_provided_mm2_per_mm: float
    longitudinal_reinf_provided_mm2: float
    max_spacing_mm: float
    can_neglect_torsion: bool
    cross_section_ok: bool
    alternative_procedure_allowed: bool
    alternative_procedure_message: str = ""
    governing_equation: str = ""
    warnings: tuple[str, ...] = ()
    steps: tuple[TorsionStep, ...] = ()


@dataclass(frozen=True, slots=True)
class _ClauseMap:
    threshold_check: str
    cross_section_limit: str
    transverse_strength: str
    longitudinal_strength: str
    min_transverse: str
    min_longitudinal: str
    spacing_limit: str
    alternative_procedure: str | None = None


def calculate_torsion_design(
    design_input: TorsionDesignInput,
    geometry_input: TorsionSectionGeometryInput,
    material_input: TorsionDesignMaterialInput,
) -> TorsionDesignResults:
    if design_input.design_code == TorsionDesignCode.ACI318_99:
        from .torsion_aci_99 import calculate_aci_99_torsion

        return calculate_aci_99_torsion(design_input, geometry_input, material_input)
    if design_input.design_code == TorsionDesignCode.ACI318_11:
        from .torsion_aci_11 import calculate_aci_11_torsion

        return calculate_aci_11_torsion(design_input, geometry_input, material_input)
    if design_input.design_code == TorsionDesignCode.ACI318_14:
        from .torsion_aci_14 import calculate_aci_14_torsion

        return calculate_aci_14_torsion(design_input, geometry_input, material_input)
    from .torsion_aci_19 import calculate_aci_19_torsion

    return calculate_aci_19_torsion(design_input, geometry_input, material_input)


def calculate_standard_torsion(
    design_input: TorsionDesignInput,
    geometry_input: TorsionSectionGeometryInput,
    material_input: TorsionDesignMaterialInput,
    clauses: _ClauseMap,
    *,
    enable_alternative_procedure_flag: bool = False,
) -> TorsionDesignResults:
    if not design_input.enabled:
        return TorsionDesignResults(
            enabled=False,
            code_version=design_input.design_code.value,
            demand_type=design_input.demand_type,
            design_method="Standard thin-walled tube / space-truss method",
            status="DISABLED",
            pass_fail_summary="Torsion design is disabled.",
            tu_kgfm=design_input.factored_torsion_kgfm,
            threshold_torsion_kgfm=0.0,
            cracking_torsion_kgfm=None,
            acp_mm2=0.0,
            pcp_mm=0.0,
            aoh_mm2=0.0,
            ao_mm2=0.0,
            ph_mm=0.0,
            wall_thickness_mm=0.0,
            aspect_ratio_h_over_bt=0.0,
            transverse_reinf_required_mm2_per_mm=0.0,
            transverse_reinf_required_governing="",
            longitudinal_reinf_required_mm2=0.0,
            longitudinal_reinf_required_governing="",
            transverse_reinf_provided_mm2_per_mm=0.0,
            longitudinal_reinf_provided_mm2=0.0,
            max_spacing_mm=0.0,
            can_neglect_torsion=True,
            cross_section_ok=True,
            alternative_procedure_allowed=False,
            governing_equation="",
            warnings=(),
            steps=(),
        )

    geometry = _resolve_torsion_geometry(geometry_input)
    concrete_strength_mpa = ksc_to_mpa(material_input.concrete_strength_ksc)
    transverse_yield_mpa = ksc_to_mpa(material_input.transverse_steel_yield_ksc)
    longitudinal_yield_mpa = ksc_to_mpa(material_input.longitudinal_steel_yield_ksc)
    tu_nmm = kgf_m_to_n_mm(design_input.factored_torsion_kgfm)
    sqrt_fc = math.sqrt(concrete_strength_mpa)
    stirrup_leg_area_mm2 = math.pi * (geometry_input.stirrup_diameter_mm**2) / 4
    provided_transverse_mm2_per_mm = stirrup_leg_area_mm2 / geometry.spacing_mm
    provided_longitudinal_mm2 = cm2_to_mm2(design_input.resolved_provided_longitudinal_steel_cm2)
    alternative_procedure_allowed = enable_alternative_procedure_flag and geometry.aspect_ratio_h_over_bt >= 3.0

    warnings: list[str] = []
    if geometry_input.stirrup_legs < 2:
        warnings.append("Closed stirrups are required for the implemented torsion method; current stirrup input has fewer than 2 legs.")
    if design_input.demand_type == TorsionDemandType.COMPATIBILITY:
        warnings.append("Compatibility torsion is evaluated using the user-entered Tu without redistribution.")
    if alternative_procedure_allowed and clauses.alternative_procedure is not None:
        warnings.append(ACI_318_19_ALT_PROCEDURE_MESSAGE)

    # Threshold torsion check per the selected ACI clause map, e.g. ACI 318-19 22.7.4.
    threshold_torsion_nmm = (
        TORSION_PHI
        * material_input.lightweight_lambda
        * sqrt_fc
        * (geometry.acp_mm2**2)
        / (12.0 * geometry.pcp_mm)
    )
    threshold_torsion_kgfm = n_mm_to_kgf_m(threshold_torsion_nmm)
    can_neglect_torsion = tu_nmm <= threshold_torsion_nmm + 1e-9

    # Pure torsion cross-section limit per the selected ACI clause map, e.g. ACI 318-19 22.7.7.
    cross_section_limit_lhs_mpa = tu_nmm * geometry.ph_mm / (1.7 * (geometry.aoh_mm2**2))
    cross_section_limit_rhs_mpa = TORSION_PHI * 0.83 * material_input.lightweight_lambda * sqrt_fc
    cross_section_ok = cross_section_limit_lhs_mpa <= cross_section_limit_rhs_mpa + 1e-9

    # Closed-stirrup torsion reinforcement demand per the selected ACI clause map, e.g. ACI 318-19 22.7.6.
    at_over_s_strength = tu_nmm / (
        TORSION_PHI * 2.0 * geometry.ao_mm2 * transverse_yield_mpa * STANDARD_COT_THETA
    )
    at_over_s_min_1 = 0.75 * sqrt_fc * geometry.width_mm / (24.0 * transverse_yield_mpa)
    at_over_s_min_2 = 0.175 * geometry.width_mm / transverse_yield_mpa
    min_transverse_requirement = max(at_over_s_min_1, at_over_s_min_2)
    transverse_governing = (
        f"{clauses.transverse_strength}"
        if at_over_s_strength >= min_transverse_requirement - 1e-9
        else f"{clauses.min_transverse}"
    )
    at_over_s_required = max(at_over_s_strength, min_transverse_requirement)

    # Longitudinal torsion reinforcement demand per the selected ACI clause map, e.g. ACI 318-19 22.7.6 and 9.6.4.3.
    longitudinal_strength = (
        at_over_s_required
        * geometry.ph_mm
        * (transverse_yield_mpa / longitudinal_yield_mpa)
        * (STANDARD_COT_THETA**2)
    )
    longitudinal_minimum = max(
        (
            5.0
            * sqrt_fc
            * geometry.acp_mm2
            / (12.0 * longitudinal_yield_mpa)
        )
        - at_over_s_required * geometry.ph_mm * (transverse_yield_mpa / longitudinal_yield_mpa),
        0.0,
    )
    longitudinal_governing = (
        f"{clauses.longitudinal_strength}"
        if longitudinal_strength >= longitudinal_minimum - 1e-9
        else f"{clauses.min_longitudinal}"
    )
    longitudinal_required_mm2 = max(longitudinal_strength, longitudinal_minimum)

    max_spacing_mm = min(geometry.ph_mm / 8.0, 300.0)
    spacing_ok = geometry.spacing_mm <= max_spacing_mm + 1e-9
    transverse_ok = provided_transverse_mm2_per_mm >= at_over_s_required - 1e-9
    longitudinal_ok = provided_longitudinal_mm2 >= longitudinal_required_mm2 - 1e-9
    assumptions_ok = geometry_input.stirrup_legs >= 2

    # Reserve FAIL for torsion strength-type failure. Detailing and reinforcement
    # shortfalls are reported as requirements not met so the UI can distinguish
    # them from capacity-ratio failures in moment, shear, and interaction checks.
    if can_neglect_torsion:
        status = "PASS"
        pass_fail_summary = "Torsion can be neglected by the code threshold check."
    elif not cross_section_ok:
        status = "FAIL"
        pass_fail_summary = "The section does not satisfy the implemented pure-torsion cross-sectional strength check."
    elif transverse_ok and longitudinal_ok and spacing_ok and assumptions_ok:
        status = "PASS"
        pass_fail_summary = "Provided torsion reinforcement satisfies the implemented standard torsion checks."
    else:
        status = "DOES NOT MEET REQUIREMENTS"
        pass_fail_summary = "Provided torsion reinforcement does not meet one or more torsion reinforcement requirements."

    if not can_neglect_torsion and not cross_section_ok:
        warnings.append("The section fails the implemented pure-torsion cross-sectional limit check.")
    if not can_neglect_torsion and not transverse_ok:
        warnings.append("Provided transverse torsion reinforcement does not meet the required At/s.")
    if not can_neglect_torsion and not longitudinal_ok:
        warnings.append("Provided longitudinal torsion reinforcement does not meet the required Al.")
    if not can_neglect_torsion and not spacing_ok:
        warnings.append("Provided stirrup spacing does not meet the maximum spacing permitted for torsion.")

    governing_equation = transverse_governing if at_over_s_required >= min_transverse_requirement - 1e-9 else clauses.min_transverse
    steps = _build_torsion_steps(
        design_input,
        geometry,
        threshold_torsion_kgfm,
        cross_section_limit_lhs_mpa,
        cross_section_limit_rhs_mpa,
        at_over_s_strength,
        min_transverse_requirement,
        at_over_s_required,
        longitudinal_strength,
        longitudinal_minimum,
        longitudinal_required_mm2,
        provided_transverse_mm2_per_mm,
        provided_longitudinal_mm2,
        max_spacing_mm,
        clauses,
        transverse_governing,
        longitudinal_governing,
        can_neglect_torsion,
        cross_section_ok,
        status,
    )

    return TorsionDesignResults(
        enabled=design_input.enabled,
        code_version=design_input.design_code.value,
        demand_type=design_input.demand_type,
        design_method="Standard thin-walled tube / space-truss method",
        status=status,
        pass_fail_summary=pass_fail_summary,
        tu_kgfm=design_input.factored_torsion_kgfm,
        threshold_torsion_kgfm=threshold_torsion_kgfm,
        cracking_torsion_kgfm=None,
        acp_mm2=geometry.acp_mm2,
        pcp_mm=geometry.pcp_mm,
        aoh_mm2=geometry.aoh_mm2,
        ao_mm2=geometry.ao_mm2,
        ph_mm=geometry.ph_mm,
        wall_thickness_mm=geometry.wall_thickness_mm,
        aspect_ratio_h_over_bt=geometry.aspect_ratio_h_over_bt,
        transverse_reinf_required_mm2_per_mm=0.0 if can_neglect_torsion else at_over_s_required,
        transverse_reinf_required_governing=transverse_governing,
        longitudinal_reinf_required_mm2=0.0 if can_neglect_torsion else longitudinal_required_mm2,
        longitudinal_reinf_required_governing=longitudinal_governing,
        transverse_reinf_provided_mm2_per_mm=provided_transverse_mm2_per_mm,
        longitudinal_reinf_provided_mm2=provided_longitudinal_mm2,
        max_spacing_mm=max_spacing_mm,
        can_neglect_torsion=can_neglect_torsion,
        cross_section_ok=cross_section_ok,
        alternative_procedure_allowed=alternative_procedure_allowed,
        alternative_procedure_message=ACI_318_19_ALT_PROCEDURE_MESSAGE if alternative_procedure_allowed else "",
        governing_equation=governing_equation,
        warnings=tuple(warnings),
        steps=tuple(steps),
    )


def make_clause_map(
    threshold_check: str,
    cross_section_limit: str,
    transverse_strength: str,
    longitudinal_strength: str,
    min_transverse: str,
    min_longitudinal: str,
    spacing_limit: str,
    alternative_procedure: str | None = None,
) -> _ClauseMap:
    return _ClauseMap(
        threshold_check=threshold_check,
        cross_section_limit=cross_section_limit,
        transverse_strength=transverse_strength,
        longitudinal_strength=longitudinal_strength,
        min_transverse=min_transverse,
        min_longitudinal=min_longitudinal,
        spacing_limit=spacing_limit,
        alternative_procedure=alternative_procedure,
    )


@dataclass(frozen=True, slots=True)
class _ResolvedTorsionGeometry:
    width_mm: float
    depth_mm: float
    spacing_mm: float
    acp_mm2: float
    pcp_mm: float
    aoh_mm2: float
    ao_mm2: float
    ph_mm: float
    wall_thickness_mm: float
    aspect_ratio_h_over_bt: float


def _resolve_torsion_geometry(geometry_input: TorsionSectionGeometryInput) -> _ResolvedTorsionGeometry:
    width_mm = cm_to_mm(geometry_input.width_cm)
    depth_mm = cm_to_mm(geometry_input.depth_cm)
    cover_mm = cm_to_mm(geometry_input.cover_cm)
    spacing_mm = cm_to_mm(geometry_input.stirrup_spacing_cm)
    centerline_offset_mm = cover_mm + (geometry_input.stirrup_diameter_mm / 2.0)
    core_width_mm = width_mm - (2.0 * centerline_offset_mm)
    core_depth_mm = depth_mm - (2.0 * centerline_offset_mm)
    if core_width_mm <= 0 or core_depth_mm <= 0:
        raise ValueError("Torsion geometry is invalid because the stirrup centerline core becomes non-positive.")

    # Aoh, Ao, and ph follow the ACI thin-walled tube idealization for closed stirrups.
    acp_mm2 = width_mm * depth_mm
    pcp_mm = 2.0 * (width_mm + depth_mm)
    aoh_mm2 = core_width_mm * core_depth_mm
    ao_mm2 = 0.85 * aoh_mm2
    ph_mm = 2.0 * (core_width_mm + core_depth_mm)
    wall_thickness_mm = aoh_mm2 / ph_mm
    aspect_ratio_h_over_bt = depth_mm / width_mm
    return _ResolvedTorsionGeometry(
        width_mm=width_mm,
        depth_mm=depth_mm,
        spacing_mm=spacing_mm,
        acp_mm2=acp_mm2,
        pcp_mm=pcp_mm,
        aoh_mm2=aoh_mm2,
        ao_mm2=ao_mm2,
        ph_mm=ph_mm,
        wall_thickness_mm=wall_thickness_mm,
        aspect_ratio_h_over_bt=aspect_ratio_h_over_bt,
    )


def _build_torsion_steps(
    design_input: TorsionDesignInput,
    geometry: _ResolvedTorsionGeometry,
    threshold_torsion_kgfm: float,
    cross_section_limit_lhs_mpa: float,
    cross_section_limit_rhs_mpa: float,
    at_over_s_strength: float,
    min_transverse_requirement: float,
    at_over_s_required: float,
    longitudinal_strength: float,
    longitudinal_minimum: float,
    longitudinal_required_mm2: float,
    provided_transverse_mm2_per_mm: float,
    provided_longitudinal_mm2: float,
    max_spacing_mm: float,
    clauses: _ClauseMap,
    transverse_governing: str,
    longitudinal_governing: str,
    can_neglect_torsion: bool,
    cross_section_ok: bool,
    status: str,
) -> list[TorsionStep]:
    return [
        TorsionStep("Tu", "-", "User input", f"{design_input.factored_torsion_kgfm:.3f}", "kgf-m", "Input"),
        TorsionStep("Acp", "bw * h", "-", f"{geometry.acp_mm2:.3f}", "mm2", "Geometry"),
        TorsionStep("pcp", "2 * (bw + h)", "-", f"{geometry.pcp_mm:.3f}", "mm", "Geometry"),
        TorsionStep("Aoh", "xoh * yoh", "Centerline of outermost closed stirrup", f"{geometry.aoh_mm2:.3f}", "mm2", "Geometry"),
        TorsionStep("Ao", "0.85 * Aoh", "-", f"{geometry.ao_mm2:.3f}", "mm2", "Geometry"),
        TorsionStep("ph", "2 * (xoh + yoh)", "-", f"{geometry.ph_mm:.3f}", "mm", "Geometry"),
        TorsionStep(
            "Threshold torsion",
            "phi * lambda * sqrt(f'c) * Acp^2 / (12 * pcp)",
            clauses.threshold_check,
            f"{threshold_torsion_kgfm:.3f}",
            "kgf-m",
            clauses.threshold_check,
            status="OK" if can_neglect_torsion else "CHECK",
        ),
        TorsionStep(
            "Cross-section limit",
            "Tu * ph / (1.7 * Aoh^2) <= phi * 0.83 * lambda * sqrt(f'c)",
            f"{cross_section_limit_lhs_mpa:.3f} <= {cross_section_limit_rhs_mpa:.3f}",
            f"{cross_section_limit_lhs_mpa:.3f} / {cross_section_limit_rhs_mpa:.3f}",
            "MPa",
            clauses.cross_section_limit,
            status="OK" if cross_section_ok else "FAIL",
        ),
        TorsionStep(
            "At/s strength",
            "Tu / (phi * 2 * Ao * fyt * cot(theta))",
            "-",
            f"{at_over_s_strength:.6f}",
            "mm2/mm",
            clauses.transverse_strength,
        ),
        TorsionStep(
            "At/s minimum",
            "max(0.75*sqrt(f'c)*bw/(24*fyt), 0.175*bw/fyt)",
            "-",
            f"{min_transverse_requirement:.6f}",
            "mm2/mm",
            clauses.min_transverse,
        ),
        TorsionStep(
            "At/s required",
            "max(strength, minimum)",
            transverse_governing,
            f"{0.0 if can_neglect_torsion else at_over_s_required:.6f}",
            "mm2/mm",
            transverse_governing,
        ),
        TorsionStep(
            "Al strength",
            "(At/s) * ph * (fyt/fyl) * cot^2(theta)",
            "-",
            f"{longitudinal_strength:.3f}",
            "mm2",
            clauses.longitudinal_strength,
        ),
        TorsionStep(
            "Al minimum",
            "max(5*sqrt(f'c)*Acp/(12*fyl) - (At/s)*ph*(fyt/fyl), 0)",
            "-",
            f"{longitudinal_minimum:.3f}",
            "mm2",
            clauses.min_longitudinal,
        ),
        TorsionStep(
            "Al required",
            "max(strength, minimum)",
            longitudinal_governing,
            f"{0.0 if can_neglect_torsion else longitudinal_required_mm2:.3f}",
            "mm2",
            longitudinal_governing,
        ),
        TorsionStep("At/s provided", "Area of one stirrup leg / s", "-", f"{provided_transverse_mm2_per_mm:.6f}", "mm2/mm", "Provided"),
        TorsionStep("Al provided", "User input", "-", f"{provided_longitudinal_mm2:.3f}", "mm2", "Provided"),
        TorsionStep("s max", "min(ph/8, 300 mm)", "-", f"{max_spacing_mm:.3f}", "mm", clauses.spacing_limit),
        TorsionStep("Summary", "-", "-", status, "-", "Result"),
    ]


def _validate_positive(value: float, field_name: str) -> None:
    if value <= 0:
        raise ValueError(f"{field_name} must be greater than zero.")


def _validate_non_negative(value: float, field_name: str) -> None:
    if value < 0:
        raise ValueError(f"{field_name} must be zero or greater.")
