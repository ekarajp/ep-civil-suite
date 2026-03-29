from __future__ import annotations

from .torsion_base import TorsionDesignInput, TorsionDesignMaterialInput, TorsionSectionGeometryInput, TorsionDesignResults, calculate_standard_torsion, make_clause_map


def calculate_aci_99_torsion(
    design_input: TorsionDesignInput,
    geometry_input: TorsionSectionGeometryInput,
    material_input: TorsionDesignMaterialInput,
) -> TorsionDesignResults:
    clauses = make_clause_map(
        threshold_check="ACI 318-99 11.6.1",
        cross_section_limit="ACI 318-99 11.6.3.1",
        transverse_strength="ACI 318-99 11.6.3.3",
        longitudinal_strength="ACI 318-99 11.6.3.7",
        min_transverse="ACI 318-99 11.6.5.1-11.6.5.2",
        min_longitudinal="ACI 318-99 11.6.5.3",
        spacing_limit="ACI 318-99 11.6.6.1",
    )
    return calculate_standard_torsion(design_input, geometry_input, material_input, clauses)
