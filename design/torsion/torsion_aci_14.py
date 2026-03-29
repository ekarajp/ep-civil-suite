from __future__ import annotations

from .torsion_base import TorsionDesignInput, TorsionDesignMaterialInput, TorsionSectionGeometryInput, TorsionDesignResults, calculate_standard_torsion, make_clause_map


def calculate_aci_14_torsion(
    design_input: TorsionDesignInput,
    geometry_input: TorsionSectionGeometryInput,
    material_input: TorsionDesignMaterialInput,
) -> TorsionDesignResults:
    clauses = make_clause_map(
        threshold_check="ACI 318-14 22.7.4",
        cross_section_limit="ACI 318-14 22.7.7",
        transverse_strength="ACI 318-14 22.7.6",
        longitudinal_strength="ACI 318-14 22.7.6",
        min_transverse="ACI 318-14 9.6.4.1-9.6.4.2",
        min_longitudinal="ACI 318-14 9.6.4.3",
        spacing_limit="ACI 318-14 25.7.1.2",
    )
    return calculate_standard_torsion(design_input, geometry_input, material_input, clauses)
