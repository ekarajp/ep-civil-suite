from __future__ import annotations

import apps.singly_beam.workspace_page as workspace_page
from apps.singly_beam.models import BeamType, CombinedShearTorsionResults
from core.theme import LIGHT_THEME
from design.torsion import TorsionDesignCode
from design.torsion.torsion_base import TorsionDemandType, TorsionDesignResults


def test_initialize_session_state_restores_persisted_values(monkeypatch) -> None:
    default_inputs = workspace_page.load_default_inputs()
    session_state = {
        workspace_page.PERSISTED_WORKSPACE_STATE_KEY: {
            "beam_type": "Continuous Beam",
            "width_cm": 35.0,
            "project_date_auto_value": "2026-03-29 10:15",
        }
    }

    monkeypatch.setattr(workspace_page.st, "session_state", session_state)

    workspace_page.initialize_session_state(default_inputs)

    assert session_state["beam_type"] == "Continuous Beam"
    assert session_state["width_cm"] == 35.0
    assert session_state["project_date_auto_value"] == "2026-03-29 10:15"
    assert "depth_cm" in session_state


def test_initialize_session_state_force_restores_values_when_returning_from_other_page(monkeypatch) -> None:
    default_inputs = workspace_page.load_default_inputs()
    session_state = {
        "width_cm": 1.0,
        "min_clear_spacing_cm": 0.1,
        workspace_page.PERSISTED_WORKSPACE_STATE_KEY: {
            "width_cm": 30.0,
            "min_clear_spacing_cm": 3.5,
        },
    }

    monkeypatch.setattr(workspace_page.st, "session_state", session_state)

    workspace_page.initialize_session_state(default_inputs, force_restore=True)

    assert session_state["width_cm"] == 30.0
    assert session_state["min_clear_spacing_cm"] == 3.5


def test_initialize_session_state_does_not_override_existing_values_during_workspace_rerun(monkeypatch) -> None:
    default_inputs = workspace_page.load_default_inputs()
    session_state = {
        "width_cm": 28.0,
        workspace_page.PERSISTED_WORKSPACE_STATE_KEY: {
            "width_cm": 20.0,
        },
    }

    monkeypatch.setattr(workspace_page.st, "session_state", session_state)

    workspace_page.initialize_session_state(default_inputs, force_restore=False)

    assert session_state["width_cm"] == 28.0


def test_persist_session_state_snapshots_current_workspace_values(monkeypatch) -> None:
    default_inputs = workspace_page.load_default_inputs()
    session_state = {
        "beam_type": "Continuous Beam",
        "width_cm": 42.0,
        "project_date_auto_value": "2026-03-29 11:00",
    }

    monkeypatch.setattr(workspace_page.st, "session_state", session_state)

    workspace_page.persist_session_state(default_inputs)

    persisted_state = session_state[workspace_page.PERSISTED_WORKSPACE_STATE_KEY]
    assert persisted_state["beam_type"] == "Continuous Beam"
    assert persisted_state["width_cm"] == 42.0
    assert persisted_state["project_date_auto_value"] == "2026-03-29 11:00"


def test_build_inputs_from_state_uses_main_design_code_for_torsion(monkeypatch) -> None:
    default_inputs = workspace_page.load_default_inputs()
    session_state = type("SessionState", (dict,), {"__getattr__": dict.__getitem__, "__setattr__": dict.__setitem__})()
    session_state.update(workspace_page.build_default_state(default_inputs))
    session_state["include_torsion_design"] = True
    session_state["design_code"] = "ACI318-14"
    session_state["torsion_tu_kgfm"] = 500.0
    session_state["project_date_auto_value"] = "2026-03-29 12:00"

    monkeypatch.setattr(workspace_page.st, "session_state", session_state)

    inputs = workspace_page.build_inputs_from_state()

    assert inputs.torsion.design_code == TorsionDesignCode.ACI318_14
    assert inputs.torsion.provided_longitudinal_bar_fy_ksc == 4000.0


def test_build_inputs_from_state_uses_selected_fyl_for_torsion_longitudinal_steel(monkeypatch) -> None:
    default_inputs = workspace_page.load_default_inputs()
    session_state = type("SessionState", (dict,), {"__getattr__": dict.__getitem__, "__setattr__": dict.__setitem__})()
    session_state.update(workspace_page.build_default_state(default_inputs))
    session_state["include_torsion_design"] = True
    session_state["fy_grade_option"] = 5000
    session_state["fy_ksc"] = 5000.0
    session_state["torsion_longitudinal_fy_grade_option"] = 3000
    session_state["torsion_longitudinal_fy_ksc"] = 3000.0
    session_state["project_date_auto_value"] = "2026-03-29 12:30"

    monkeypatch.setattr(workspace_page.st, "session_state", session_state)

    inputs = workspace_page.build_inputs_from_state()

    assert inputs.materials.main_steel_yield_ksc == 5000.0
    assert inputs.torsion.provided_longitudinal_bar_fy_ksc == 3000.0


def test_build_inputs_for_torsion_capacity_preview_allows_selected_diameter_with_zero_count(monkeypatch) -> None:
    default_inputs = workspace_page.load_default_inputs()
    session_state = type("SessionState", (dict,), {"__getattr__": dict.__getitem__, "__setattr__": dict.__setitem__})()
    session_state.update(workspace_page.build_default_state(default_inputs))
    session_state["include_torsion_design"] = True
    session_state["torsion_longitudinal_diameter_option"] = 16
    session_state["torsion_longitudinal_diameter_mm"] = 16
    session_state["torsion_longitudinal_count"] = 0
    session_state["project_date_auto_value"] = "2026-03-29 13:00"

    monkeypatch.setattr(workspace_page.st, "session_state", session_state)

    inputs = workspace_page._build_inputs_for_torsion_capacity_preview()

    assert inputs.torsion.provided_longitudinal_bar_diameter_mm == 16
    assert inputs.torsion.provided_longitudinal_bar_count == 1
    assert session_state["torsion_longitudinal_count"] == 0


def test_include_torsion_toggle_restores_previous_torsion_inputs(monkeypatch) -> None:
    session_state = type("SessionState", (dict,), {"__getattr__": dict.__getitem__, "__setattr__": dict.__setitem__})()
    session_state.update(
        {
            "include_torsion_design": False,
            "torsion_tu_kgfm": 1250.0,
            "torsion_demand_type": "equilibrium torsion",
            "torsion_longitudinal_diameter_option": 16,
            "torsion_longitudinal_diameter_mm": 16,
            "torsion_longitudinal_fy_grade_option": 4000,
            "torsion_longitudinal_fy_ksc": 4000.0,
            "torsion_longitudinal_count": 6,
        }
    )

    monkeypatch.setattr(workspace_page.st, "session_state", session_state)

    workspace_page._handle_include_torsion_design_change()

    session_state.update(
        {
            "torsion_tu_kgfm": 0.0,
            "torsion_demand_type": "compatibility torsion",
            "torsion_longitudinal_diameter_option": "-",
            "torsion_longitudinal_diameter_mm": 0,
            "torsion_longitudinal_fy_grade_option": 2400,
            "torsion_longitudinal_fy_ksc": 2400.0,
            "torsion_longitudinal_count": 0,
        }
    )

    session_state["include_torsion_design"] = True
    workspace_page._handle_include_torsion_design_change()

    assert session_state["torsion_tu_kgfm"] == 1250.0
    assert session_state["torsion_demand_type"] == "equilibrium torsion"
    assert session_state["torsion_longitudinal_diameter_option"] == 16
    assert session_state["torsion_longitudinal_diameter_mm"] == 16
    assert session_state["torsion_longitudinal_fy_grade_option"] == 4000
    assert session_state["torsion_longitudinal_fy_ksc"] == 4000.0
    assert session_state["torsion_longitudinal_count"] == 6


def test_shear_torsion_interaction_diagram_html_shows_shared_stirrup_rule() -> None:
    html = workspace_page._build_shear_torsion_interaction_diagram_html(
        CombinedShearTorsionResults(
            active=True,
            torsion_ignored=False,
            ignore_message="",
            vu_kg=5000.0,
            tu_kgfm=1200.0,
            shear_required_transverse_mm2_per_mm=0.020,
            torsion_required_transverse_mm2_per_mm=0.030,
            combined_required_transverse_mm2_per_mm=0.050,
            provided_transverse_mm2_per_mm=0.080,
            governing_case="Shear + Torsion",
            capacity_ratio=0.625,
            design_status="PASS",
            stirrup_diameter_mm=9,
            stirrup_legs=2,
            stirrup_spacing_cm=15.0,
            summary_note="",
        ),
        LIGHT_THEME,
        TorsionDesignResults(
            enabled=True,
            code_version="ACI 318-19",
            demand_type=TorsionDemandType.EQUILIBRIUM,
            design_method="Standard thin-walled tube / space-truss method",
            status="PASS",
            pass_fail_summary="Provided torsion reinforcement satisfies the implemented standard torsion checks.",
            tu_kgfm=1200.0,
            threshold_torsion_kgfm=100.0,
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
            can_neglect_torsion=False,
            cross_section_ok=True,
            alternative_procedure_allowed=False,
        ),
    )

    assert "Shear&ndash;Torsion Interaction Diagram" in html
    assert "x + y &le; 1.00" in html
    assert "Demand point" in html


def test_torsion_warning_summary_prefers_specific_warning_text() -> None:
    torsion_results = TorsionDesignResults(
        enabled=True,
        code_version="ACI 318-19",
        demand_type=TorsionDemandType.EQUILIBRIUM,
        design_method="Standard thin-walled tube / space-truss method",
        status="DOES NOT MEET REQUIREMENTS",
        pass_fail_summary="Provided torsion reinforcement does not meet one or more torsion reinforcement requirements.",
        tu_kgfm=1200.0,
        threshold_torsion_kgfm=100.0,
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
        can_neglect_torsion=False,
        cross_section_ok=True,
        alternative_procedure_allowed=False,
        warnings=("Provided longitudinal torsion reinforcement does not meet the required Al.",),
    )

    assert workspace_page._torsion_warning_summary(torsion_results) == (
        "Provided longitudinal torsion reinforcement does not meet the required Al."
    )


def test_torsion_demand_type_info_text_keeps_conservative_guidance() -> None:
    info_text = workspace_page.TORSION_DEMAND_TYPE_INFO_TEXT

    assert "Use 'equilibrium torsion'" in info_text
    assert "Use 'compatibility torsion'" in info_text
    assert "safer and more conservative design assumption" in info_text


def test_shear_design_section_label_switches_to_combined_mode_when_torsion_is_enabled() -> None:
    assert workspace_page._shear_design_section_label(False, BeamType.SIMPLE) == "6. Shear Design"
    assert workspace_page._shear_design_section_label(True, BeamType.SIMPLE) == "6. Shear & Torsion Design"
    assert workspace_page._shear_design_section_label(True, BeamType.CONTINUOUS) == "7. Shear & Torsion Design"


def test_torsion_detail_inputs_are_hidden_when_torsion_can_be_ignored() -> None:
    preview_results = type(
        "PreviewResults",
        (),
        {
            "combined_shear_torsion": CombinedShearTorsionResults(
                active=False,
                torsion_ignored=True,
                ignore_message="Tu < Tth, ignore torsion",
                vu_kg=0.0,
                tu_kgfm=0.0,
                shear_required_transverse_mm2_per_mm=0.0,
                torsion_required_transverse_mm2_per_mm=0.0,
                combined_required_transverse_mm2_per_mm=0.0,
                provided_transverse_mm2_per_mm=0.0,
                governing_case="Torsion ignored",
                capacity_ratio=0.0,
                design_status="PASS",
                stirrup_diameter_mm=9,
                stirrup_legs=2,
                stirrup_spacing_cm=15.0,
                summary_note="",
            )
        },
    )()

    assert workspace_page._torsion_detail_inputs_required(None) is True
    assert workspace_page._torsion_detail_inputs_required(preview_results) is False
