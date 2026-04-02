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
from engines.moment.formulas import calculate_flexural_phi, calculate_rho_max


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
    assert results.as_max_cm2 == pytest.approx(11.272067733990145)
    assert results.mn_kgm == pytest.approx(4456.506032607666)
    assert results.phi_mn_kgm == pytest.approx(4010.8554293468997)
    assert results.design_status == "PASS"


def test_design_moment_beam_supports_negative_case_with_audited_d_minus_path() -> None:
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

    assert results.as_required_cm2 == pytest.approx(5.253522874809101)
    assert results.as_min_cm2 == pytest.approx(2.4010000000000002)
    assert results.as_max_cm2 == pytest.approx(11.2067224137931)
    assert results.phi_mn_kgm == pytest.approx(6806.079722774743)
    assert results.review_note == ""


def test_aci318_14_flexural_phi_uses_0p65_to_0p90_transition() -> None:
    phi = calculate_flexural_phi(DesignCode.ACI318_14, et=0.0035, ety=4000.0 / (2.04 * 10**6))

    assert phi == pytest.approx(0.7766129032258065)


def test_aci318_08_flexural_phi_matches_2011_transition_branch() -> None:
    ety = 4000.0 / (2.04 * 10**6)

    assert calculate_flexural_phi(DesignCode.ACI318_08, et=0.0035, ety=ety) == pytest.approx(
        calculate_flexural_phi(DesignCode.ACI318_11, et=0.0035, ety=ety)
    )


def test_aci318_19_rho_max_depends_on_actual_fy() -> None:
    rho_max_grade_4000 = calculate_rho_max(
        DesignCode.ACI318_19,
        fc_prime_ksc=240.0,
        fy_ksc=4000.0,
        beta_1=0.85,
        es_ksc=2.04 * 10**6,
    )
    rho_max_grade_5000 = calculate_rho_max(
        DesignCode.ACI318_19,
        fc_prime_ksc=240.0,
        fy_ksc=5000.0,
        beta_1=0.85,
        es_ksc=2.04 * 10**6,
    )

    assert rho_max_grade_4000 == pytest.approx(0.01633633004926108)
    assert rho_max_grade_5000 < rho_max_grade_4000


def test_aci318_25_rho_max_matches_2019_branch_for_same_materials() -> None:
    rho_max_19 = calculate_rho_max(
        DesignCode.ACI318_19,
        fc_prime_ksc=240.0,
        fy_ksc=4000.0,
        beta_1=0.85,
        es_ksc=2.04 * 10**6,
    )
    rho_max_25 = calculate_rho_max(
        DesignCode.ACI318_25,
        fc_prime_ksc=240.0,
        fy_ksc=4000.0,
        beta_1=0.85,
        es_ksc=2.04 * 10**6,
    )

    assert rho_max_25 == pytest.approx(rho_max_19)
