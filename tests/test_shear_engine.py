import pytest

from engines.common import (
    BeamSectionInput,
    DesignCode,
    MaterialPropertiesInput,
    RebarGroupInput,
    RebarLayerInput,
    ReinforcementArrangementInput,
    ShearSpacingMode,
)
from engines.shear import ShearBeamInput, design_shear_beam


def _positive_compression() -> ReinforcementArrangementInput:
    return ReinforcementArrangementInput(
        layer_1=RebarLayerInput(group_a=RebarGroupInput(diameter_mm=12, count=2)),
    )


def _positive_tension() -> ReinforcementArrangementInput:
    return ReinforcementArrangementInput(
        layer_1=RebarLayerInput(
            group_a=RebarGroupInput(diameter_mm=12, count=2),
            group_b=RebarGroupInput(diameter_mm=12, count=1),
        ),
    )


def test_design_shear_beam_matches_default_behavior() -> None:
    results = design_shear_beam(
        ShearBeamInput(
            design_code=DesignCode.ACI318_19,
            materials=MaterialPropertiesInput(),
            geometry=BeamSectionInput(),
            factored_shear_kg=5000.0,
            stirrup_diameter_mm=9,
            legs_per_plane=2,
            spacing_mode=ShearSpacingMode.AUTO,
            provided_spacing_cm=15.0,
            positive_compression_reinforcement=_positive_compression(),
            positive_tension_reinforcement=_positive_tension(),
        )
    )

    assert results.phi == pytest.approx(0.75)
    assert results.vc_kg == pytest.approx(5665.40003883221)
    assert results.required_spacing_cm == pytest.approx(17.25)
    assert results.provided_spacing_cm == pytest.approx(15.0)
    assert results.av_cm2 == pytest.approx(1.2723450247038663)
    assert results.design_status == "PASS"


def test_design_shear_beam_manual_spacing_can_fail() -> None:
    results = design_shear_beam(
        ShearBeamInput(
            design_code=DesignCode.ACI318_19,
            materials=MaterialPropertiesInput(),
            geometry=BeamSectionInput(),
            factored_shear_kg=5000.0,
            stirrup_diameter_mm=9,
            legs_per_plane=2,
            spacing_mode=ShearSpacingMode.MANUAL,
            provided_spacing_cm=20.0,
            positive_compression_reinforcement=_positive_compression(),
            positive_tension_reinforcement=_positive_tension(),
        )
    )

    assert results.design_status == "FAIL"
    assert "exceeds required spacing" in results.review_note

