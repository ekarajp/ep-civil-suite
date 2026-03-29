import pytest

from engines.common import (
    BeamSectionInput,
    DesignCode,
    MaterialPropertiesInput,
    RebarGroupInput,
    RebarLayerInput,
    ReinforcementArrangementInput,
)
from engines.moment import MomentBeamInput, MomentDesignCase, design_moment_beam


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


def _negative_compression() -> ReinforcementArrangementInput:
    return ReinforcementArrangementInput(
        layer_1=RebarLayerInput(group_a=RebarGroupInput(diameter_mm=12, count=2)),
    )


def _negative_tension() -> ReinforcementArrangementInput:
    return ReinforcementArrangementInput(
        layer_1=RebarLayerInput(
            group_a=RebarGroupInput(diameter_mm=16, count=2),
            group_b=RebarGroupInput(diameter_mm=16, count=1),
        ),
    )


def test_design_moment_beam_matches_positive_default_behavior() -> None:
    results = design_moment_beam(
        MomentBeamInput(
            design_code=DesignCode.ACI318_19,
            materials=MaterialPropertiesInput(),
            geometry=BeamSectionInput(),
            stirrup_diameter_mm=9,
            factored_moment_kgm=4000.0,
            positive_compression_reinforcement=_positive_compression(),
            positive_tension_reinforcement=_positive_tension(),
        )
    )

    assert results.phi == pytest.approx(0.9)
    assert results.as_required_cm2 == pytest.approx(3.383248620248353)
    assert results.as_provided_cm2 == pytest.approx(3.392920065876977)
    assert results.as_min_cm2 == pytest.approx(2.415)
    assert results.as_max_cm2 == pytest.approx(11.260800000000001)
    assert results.mn_kgm == pytest.approx(4456.506032607666)
    assert results.phi_mn_kgm == pytest.approx(4010.8554293468997)
    assert results.design_status == "PASS"


def test_design_moment_beam_supports_negative_legacy_case() -> None:
    results = design_moment_beam(
        MomentBeamInput(
            design_code=DesignCode.ACI318_19,
            materials=MaterialPropertiesInput(),
            geometry=BeamSectionInput(),
            stirrup_diameter_mm=9,
            factored_moment_kgm=6000.0,
            positive_compression_reinforcement=_positive_compression(),
            positive_tension_reinforcement=_positive_tension(),
            negative_compression_reinforcement=_negative_compression(),
            negative_tension_reinforcement=_negative_tension(),
            design_case=MomentDesignCase.NEGATIVE_LEGACY,
        )
    )

    assert results.review_note
    assert results.as_required_cm2 > 0
    assert results.phi_mn_kgm > 0

