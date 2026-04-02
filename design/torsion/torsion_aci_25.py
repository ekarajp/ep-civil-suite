from __future__ import annotations

from .torsion_base import TorsionDesignInput, TorsionDesignMaterialInput, TorsionSectionGeometryInput, TorsionDesignResults, calculate_standard_torsion, make_clause_map


def calculate_aci_25_torsion(
    design_input: TorsionDesignInput,
    geometry_input: TorsionSectionGeometryInput,
    material_input: TorsionDesignMaterialInput,
) -> TorsionDesignResults:
    clauses = make_clause_map(
        threshold_check="ACI 318-25 22.7.4",
        cross_section_limit="ACI 318-25 22.7.7.1",
        transverse_strength="ACI 318-25 22.7.6",
        longitudinal_strength="ACI 318-25 22.7.6",
        min_transverse="ACI 318-25 9.6.4.1-9.6.4.2",
        min_longitudinal="ACI 318-25 9.6.4.3",
        spacing_limit="ACI 318-25 9.7.6.3.3",
        alternative_procedure="ACI 318-25 9.5.4.6",
    )
    return calculate_standard_torsion(
        design_input,
        geometry_input,
        material_input,
        clauses,
        enable_alternative_procedure_flag=True,
    )
