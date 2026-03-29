"""Formula helpers for the reusable beam shear design engine."""

from __future__ import annotations

import math

from engines.common import DesignCode
from engines.common.units import safe_divide


def calculate_shear_phi(design_code: DesignCode) -> float:
    """Return the shear phi factor for the selected code family."""
    if design_code == DesignCode.ACI318_99:
        return 0.85
    return 0.75


def calculate_aci318_19_size_effect_factor(d_cm: float) -> float:
    """Return the ACI 318-19 lambda_s size-effect factor."""
    d_in = d_cm / 2.54
    return min(math.sqrt(2 / (1 + (d_in / 10))), 1.0)


def calculate_aci318_19_vc_max_kg(
    sqrt_fc: float,
    width_cm: float,
    d_cm: float,
    size_effect_factor: float,
    lambda_concrete: float = 1.0,
) -> float:
    """Return the ACI 318-19 Vc max cap."""
    return 1.33 * lambda_concrete * size_effect_factor * sqrt_fc * width_cm * d_cm


def calculate_av_min_per_spacing_cm(sqrt_fc: float, width_cm: float, fy_ksc: float) -> float:
    """Return Av,min per unit spacing."""
    return max(
        safe_divide(0.2 * sqrt_fc * width_cm, fy_ksc),
        safe_divide(3.5 * width_cm, fy_ksc),
    )

