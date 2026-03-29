from design.torsion import (
    ACI_318_19_ALT_PROCEDURE_MESSAGE,
    TorsionDemandType,
    TorsionDesignCode,
    TorsionDesignInput,
    TorsionDesignMaterialInput,
    TorsionSectionGeometryInput,
)
from engines.torsion import TorsionBeamInput, design_torsion_beam


def test_design_torsion_beam_wraps_existing_torsion_module() -> None:
    results = design_torsion_beam(
        TorsionBeamInput(
            design=TorsionDesignInput(
                enabled=True,
                factored_torsion_kgfm=2500.0,
                design_code=TorsionDesignCode.ACI318_19,
                demand_type=TorsionDemandType.EQUILIBRIUM,
                provided_longitudinal_steel_cm2=12.0,
            ),
            geometry=TorsionSectionGeometryInput(
                width_cm=20.0,
                depth_cm=65.0,
                cover_cm=4.0,
                stirrup_diameter_mm=9,
                stirrup_spacing_cm=10.0,
                stirrup_legs=2,
            ),
            materials=TorsionDesignMaterialInput(
                concrete_strength_ksc=240.0,
                transverse_steel_yield_ksc=2400.0,
                longitudinal_steel_yield_ksc=4000.0,
            ),
        )
    )

    assert results.enabled is True
    assert results.alternative_procedure_allowed is True
    assert ACI_318_19_ALT_PROCEDURE_MESSAGE in results.warnings
