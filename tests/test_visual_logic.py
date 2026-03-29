import pytest

from apps.singly_beam.models import (
    BeamDesignInputSet,
    BeamGeometryInput,
    PositiveBendingInput,
    RebarGroupInput,
    RebarLayerInput,
    ReinforcementArrangementInput,
)
from apps.singly_beam.visualization import (
    STIRRUP_DRAWING_COLOR,
    build_beam_section_svg,
    build_section_rebar_details,
    compute_bar_points,
    compute_torsion_side_bar_points,
    torsion_bar_drawable_capacity,
    torsion_bar_spacing_warning,
    ordered_layer_bars,
)
from design.torsion import TorsionDesignInput
from core.theme import LIGHT_THEME


def test_positive_bottom_bars_stay_inside_cover_zone() -> None:
    inputs = BeamDesignInputSet()
    bars = compute_bar_points(inputs, inputs.positive_bending.tension_reinforcement, face="bottom")

    assert bars
    clear_face = inputs.geometry.cover_cm + inputs.shear.stirrup_diameter_mm / 10
    assert all(bar.x_cm >= clear_face for bar in bars)
    assert all(bar.x_cm <= inputs.geometry.width_cm - clear_face for bar in bars)
    assert all(bar.y_cm <= inputs.geometry.depth_cm - clear_face for bar in bars)


def test_negative_top_bars_are_ordered_left_to_right() -> None:
    inputs = BeamDesignInputSet()
    bars = compute_bar_points(inputs, inputs.negative_bending.tension_reinforcement, face="top")

    assert bars == sorted(bars, key=lambda bar: bar.x_cm)


def test_three_layer_capacity_is_supported() -> None:
    inputs = BeamDesignInputSet()
    inputs.positive_bending.tension_reinforcement.layer_2.group_a.diameter_mm = 16
    inputs.positive_bending.tension_reinforcement.layer_2.group_a.count = 2
    inputs.positive_bending.tension_reinforcement.layer_3.group_a.diameter_mm = 12
    inputs.positive_bending.tension_reinforcement.layer_3.group_a.count = 2

    bars = compute_bar_points(inputs, inputs.positive_bending.tension_reinforcement, face="bottom")

    assert max(bar.layer_index for bar in bars) == 3


def test_layer_bar_order_places_corner_bars_outside_and_middle_bar_at_center() -> None:
    layer = RebarLayerInput(
        group_a=RebarGroupInput(diameter_mm=20, count=2),
        group_b=RebarGroupInput(diameter_mm=16, count=1),
    )

    ordered = ordered_layer_bars(layer)

    assert [diameter for diameter, _ in ordered] == [20, 16, 20]
    assert [group for _, group in ordered] == ["Corner", "Middle", "Corner"]


def test_layer_bar_order_places_middle_bars_between_corners() -> None:
    layer = RebarLayerInput(
        group_a=RebarGroupInput(diameter_mm=20, count=2),
        group_b=RebarGroupInput(diameter_mm=16, count=2),
    )

    ordered = ordered_layer_bars(layer)

    assert [diameter for diameter, _ in ordered] == [20, 16, 16, 20]
    assert [group for _, group in ordered] == ["Corner", "Middle", "Middle", "Corner"]


def test_section_rebar_details_show_multiple_layers() -> None:
    inputs = BeamDesignInputSet()
    inputs.positive_bending.tension_reinforcement.layer_2.group_a = RebarGroupInput(diameter_mm=16, count=2)
    inputs.positive_bending.tension_reinforcement.layer_3.group_a = RebarGroupInput(diameter_mm=12, count=2)

    details = build_section_rebar_details(inputs, "positive", stirrup_spacing_cm=16.7)

    assert details.top_lines == ["2DB12"]
    assert details.bottom_lines == ["Layer 1: 2DB12 + 1DB12", "Layer 2: 2DB16", "Layer 3: 2DB12"]
    assert details.stirrup_line == "RB9, 2 legs @ 167 mm"


def test_section_rebar_details_switch_to_rb_for_2400_grade() -> None:
    inputs = BeamDesignInputSet()
    inputs.materials.main_steel_yield_ksc = 2400.0
    inputs.materials.shear_steel_yield_ksc = 2400.0

    details = build_section_rebar_details(inputs, "positive", stirrup_spacing_cm=16.7)

    assert details.top_lines == ["2RB12"]
    assert details.bottom_lines == ["2RB12 + 1RB12"]
    assert details.stirrup_line.startswith("RB9")


def test_section_svg_uses_blue_stirrup_line() -> None:
    inputs = BeamDesignInputSet()

    svg = build_beam_section_svg(inputs, LIGHT_THEME, "positive")

    assert f'stroke="{STIRRUP_DRAWING_COLOR}"' in svg


def test_torsion_surface_bars_use_side_faces_first_then_top_bottom_if_needed() -> None:
    inputs = BeamDesignInputSet(
        torsion=TorsionDesignInput(
            enabled=True,
            provided_longitudinal_bar_diameter_mm=16,
            provided_longitudinal_bar_count=5,
            provided_longitudinal_bar_fy_ksc=4000.0,
        )
    )

    bars = compute_torsion_side_bar_points(inputs)
    details = build_section_rebar_details(inputs, "positive", stirrup_spacing_cm=15.0)

    left_bars = [bar for bar in bars if bar.group_name == "left"]
    right_bars = [bar for bar in bars if bar.group_name == "right"]
    top_bottom_bars = [bar for bar in bars if bar.group_name in {"top", "bottom"}]

    assert abs(len(left_bars) - len(right_bars)) <= 1
    assert len(bars) == 5
    assert len(left_bars) + len(right_bars) >= 4
    assert len(top_bottom_bars) <= 1
    left_spacings = [left_bars[index + 1].y_cm - left_bars[index].y_cm for index in range(len(left_bars) - 1)]
    right_spacings = [right_bars[index + 1].y_cm - right_bars[index].y_cm for index in range(len(right_bars) - 1)]
    if left_spacings:
        assert max(left_spacings) - min(left_spacings) <= 1e-6
    if right_spacings:
        assert max(right_spacings) - min(right_spacings) <= 1e-6
    assert details.torsion_side_lines[0].startswith("Left face:")
    assert details.torsion_side_lines[1].startswith("Right face:")


def test_torsion_spacing_warning_reports_when_section_bars_are_too_close() -> None:
    crowded_arrangement = ReinforcementArrangementInput(
        layer_1=RebarLayerInput(
            group_a=RebarGroupInput(diameter_mm=20, count=2),
            group_b=RebarGroupInput(diameter_mm=20, count=3),
        )
    )
    inputs = BeamDesignInputSet(
        geometry=BeamGeometryInput(width_cm=20.0, depth_cm=40.0, cover_cm=4.0, minimum_clear_spacing_cm=2.5),
        positive_bending=PositiveBendingInput(
            factored_moment_kgm=4000.0,
            compression_reinforcement=crowded_arrangement,
            tension_reinforcement=crowded_arrangement,
        ),
        torsion=TorsionDesignInput(
            enabled=True,
            provided_longitudinal_bar_diameter_mm=16,
            provided_longitudinal_bar_count=5,
            provided_longitudinal_bar_fy_ksc=4000.0,
        ),
    )

    warning = torsion_bar_spacing_warning(inputs)

    assert "minimum clear spacing requirement" in warning


def test_torsion_layout_stops_at_maximum_drawable_al_bar_count() -> None:
    inputs = BeamDesignInputSet(
        torsion=TorsionDesignInput(
            enabled=True,
            provided_longitudinal_bar_diameter_mm=16,
            provided_longitudinal_bar_count=14,
            provided_longitudinal_bar_fy_ksc=4000.0,
        )
    )

    bars = compute_torsion_side_bar_points(inputs)
    details = build_section_rebar_details(inputs, "positive", stirrup_spacing_cm=15.0)

    assert len(bars) < 14
    assert "Reached maximum Al bar count" in details.torsion_warning


def test_torsion_drawable_capacity_reduces_when_upper_and_lower_layers_are_added() -> None:
    base_inputs = BeamDesignInputSet(
        torsion=TorsionDesignInput(
            enabled=True,
            provided_longitudinal_bar_diameter_mm=16,
            provided_longitudinal_bar_count=1,
            provided_longitudinal_bar_fy_ksc=4000.0,
        )
    )
    layered_inputs = BeamDesignInputSet(
        torsion=TorsionDesignInput(
            enabled=True,
            provided_longitudinal_bar_diameter_mm=16,
            provided_longitudinal_bar_count=1,
            provided_longitudinal_bar_fy_ksc=4000.0,
        )
    )
    layered_inputs.positive_bending.compression_reinforcement.layer_2.group_a = RebarGroupInput(diameter_mm=16, count=2)
    layered_inputs.positive_bending.compression_reinforcement.layer_3.group_a = RebarGroupInput(diameter_mm=16, count=2)
    layered_inputs.positive_bending.tension_reinforcement.layer_2.group_a = RebarGroupInput(diameter_mm=16, count=2)
    layered_inputs.positive_bending.tension_reinforcement.layer_3.group_a = RebarGroupInput(diameter_mm=16, count=2)

    assert torsion_bar_drawable_capacity(layered_inputs) < torsion_bar_drawable_capacity(base_inputs)


def test_torsion_side_bar_spacing_stays_equal_with_multiple_longitudinal_layers() -> None:
    inputs = BeamDesignInputSet(
        geometry=BeamGeometryInput(width_cm=20.0, depth_cm=50.0, cover_cm=4.0, minimum_clear_spacing_cm=2.5),
        torsion=TorsionDesignInput(
            enabled=True,
            provided_longitudinal_bar_diameter_mm=16,
            provided_longitudinal_bar_count=4,
            provided_longitudinal_bar_fy_ksc=4000.0,
        )
    )
    inputs.positive_bending.tension_reinforcement.layer_2.group_a = RebarGroupInput(diameter_mm=16, count=2)
    inputs.positive_bending.tension_reinforcement.layer_3.group_a = RebarGroupInput(diameter_mm=16, count=2)

    bars = compute_torsion_side_bar_points(inputs)

    left_bars = sorted((bar for bar in bars if bar.group_name == "left"), key=lambda bar: bar.y_cm)
    right_bars = sorted((bar for bar in bars if bar.group_name == "right"), key=lambda bar: bar.y_cm)
    left_spacings = [left_bars[index + 1].y_cm - left_bars[index].y_cm for index in range(len(left_bars) - 1)]
    right_spacings = [right_bars[index + 1].y_cm - right_bars[index].y_cm for index in range(len(right_bars) - 1)]

    assert left_spacings
    assert right_spacings
    assert max(left_spacings) - min(left_spacings) <= 1e-6
    assert max(right_spacings) - min(right_spacings) <= 1e-6
