"""Unit and numeric helpers shared by engine packages."""

from __future__ import annotations

import math


AUTO_SHEAR_SPACING_INCREMENT_CM = 2.5


def diameter_cm(diameter_mm: int | None) -> float:
    """Convert a bar diameter from mm to cm."""
    if diameter_mm is None:
        return 0.0
    return diameter_mm / 10.0


def bar_area_cm2(diameter_mm: int | None) -> float:
    """Return the bar area in cm2 for a round bar."""
    diameter = diameter_cm(diameter_mm)
    return math.pi * (diameter**2) / 4.0


def safe_divide(numerator: float, denominator: float) -> float:
    """Divide safely and return NaN for a zero denominator."""
    if denominator == 0:
        return math.nan
    return numerator / denominator


def auto_select_spacing_cm(
    required_spacing_cm: float,
    increment_cm: float = AUTO_SHEAR_SPACING_INCREMENT_CM,
) -> float:
    """Round a required spacing down to the supported increment."""
    if not math.isfinite(required_spacing_cm):
        return increment_cm
    snapped_spacing_cm = math.floor(required_spacing_cm / increment_cm) * increment_cm
    if snapped_spacing_cm > 0:
        return snapped_spacing_cm
    return required_spacing_cm
