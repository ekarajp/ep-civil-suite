"""Formula helpers for the reusable beam moment design engine."""

from __future__ import annotations

import math

from engines.common import DesignCode


ECU = 0.003


def calculate_flexural_phi(design_code: DesignCode, et: float, ety: float) -> float:
    """Return the flexural phi factor for the selected code family."""
    if math.isnan(et):
        return math.nan
    if design_code == DesignCode.ACI318_99:
        return 0.9
    if design_code == DesignCode.ACI318_11:
        if et < 0.002:
            return 0.75
        if et <= 0.005:
            return 0.75 + ((et - 0.002) * 0.5)
        return 0.9
    if design_code == DesignCode.ACI318_14:
        if et < ety:
            return 0.75
        if et <= 0.005:
            return 0.75 + ((0.15 / (0.005 - ety)) * (et - ety))
        return 0.9
    if et < ety:
        return 0.75
    if et <= ety + 0.003:
        return 0.75 + ((0.15 / ((ety + 0.003) - ety)) * (et - ety))
    return 0.9


def calculate_rho_required(fc_prime_ksc: float, fy_ksc: float, ru_kg_per_cm2: float) -> float:
    """Return the required steel ratio from the current rectangular-section solver."""
    discriminant = 1 - ((2 * ru_kg_per_cm2) / (0.85 * fc_prime_ksc))
    if discriminant < 0:
        return math.nan
    return 0.85 * (fc_prime_ksc / fy_ksc) * (1 - math.sqrt(discriminant))


def calculate_rho_min(design_code: DesignCode, fc_prime_ksc: float, fy_ksc: float) -> float:
    """Return the minimum steel ratio used by the current app logic."""
    if design_code == DesignCode.ACI318_99:
        return 14 / fy_ksc
    return max((14 / fy_ksc), (0.8 * math.sqrt(fc_prime_ksc) / fy_ksc))


def calculate_rho_max(
    design_code: DesignCode,
    fc_prime_ksc: float,
    fy_ksc: float,
    beta_1: float,
) -> float:
    """Return the maximum steel ratio used by the current app logic."""
    if design_code == DesignCode.ACI318_99:
        return 0.75 * 0.85 * (fc_prime_ksc / fy_ksc) * beta_1 * (6120 / (6120 + fy_ksc))
    if design_code in {DesignCode.ACI318_11, DesignCode.ACI318_14}:
        return 0.36 * beta_1 * (fc_prime_ksc / fy_ksc)
    return 0.32 * beta_1 * (fc_prime_ksc / fy_ksc)

