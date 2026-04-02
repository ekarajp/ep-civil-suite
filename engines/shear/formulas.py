"""Formula helpers for the reusable beam shear design engine.

Scope of this audit:
- rectangular nonprestressed beam sections
- normalweight concrete only
- member shear design only

Clause basis used in this module:
- ACI 318-99 Chapter 11 and Table 9.3.2
- ACI 318-08 Chapter 11 and Chapter 9 strength-reduction factors
- ACI 318-11 Chapter 11 and Chapter 9 strength-reduction factors
- ACI 318-14 Chapter 22 beam shear strength with Chapter 21 phi factors
- ACI 318-19 Table 22.5.5.1, Section 9.6.3, Section 9.7.6.2, and Chapter 21 phi factors
- ACI 318-25 Table 22.5.5.1, Section 9.6.3, Section 9.7.6.2, and Chapter 21 phi factors
"""

from __future__ import annotations

import math

from engines.common import DesignCode
from engines.common.units import safe_divide


def calculate_shear_phi(design_code: DesignCode) -> float:
    """Return phi for member shear and torsion strength checks."""
    if design_code == DesignCode.ACI318_99:
        return 0.85
    return 0.75


def calculate_aci318_19_size_effect_factor(d_cm: float) -> float:
    """Return ACI 318-19 lambda_s for Table 22.5.5.1 equation (c)."""
    d_in = d_cm / 2.54
    return min(math.sqrt(2 / (1 + (d_in / 10))), 1.0)


def calculate_aci318_19_vc_max_kg(
    sqrt_fc: float,
    width_cm: float,
    d_cm: float,
    size_effect_factor: float,
    lambda_concrete: float = 1.0,
) -> float:
    """Return the ACI 318-19 upper bound on Vc for Table 22.5.5.1."""
    return 1.33 * lambda_concrete * size_effect_factor * sqrt_fc * width_cm * d_cm


def calculate_av_min_per_spacing_cm(sqrt_fc: float, width_cm: float, fy_ksc: float) -> float:
    """Return Av,min/s for beam shear reinforcement."""
    return max(
        safe_divide(0.2 * sqrt_fc * width_cm, fy_ksc),
        safe_divide(3.5 * width_cm, fy_ksc),
    )
