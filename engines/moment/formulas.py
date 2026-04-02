"""Formula helpers for the reusable beam moment design engine.

Scope of this audit:
- rectangular nonprestressed beam sections
- flexure without axial-force design interaction
- ACI 318-99, 318-08, 318-11, 318-14, 318-19, and 318-25 code families

Clause basis used in this module:
- ACI 318-99 Table 9.3.2 for flexural phi and Chapter 10 strain-block assumptions
- ACI 318-08 Table 9.3.2.1 and Sections 10.2, 10.3, and 10.5
- ACI 318-11 Table 9.3.2.1 and Sections 10.2, 10.3, and 10.5
- ACI 318-14 Table 21.2.2 and Sections 22.2, 22.3, and 9.6.1.2
- ACI 318-19 Table 21.2.2 and Sections 22.2, 22.3, and 9.6.1.2
- ACI 318-25 Table 21.2.2 and Sections 22.2, 22.3, and 9.6.1.2
"""

from __future__ import annotations

import math

from engines.common import DesignCode


ECU = 0.003
PHI_FLEXURE_MIN = 0.65
PHI_FLEXURE_MAX = 0.9
ACI_318_11_14_TENSION_CONTROLLED_STRAIN = 0.005


def calculate_flexural_phi(design_code: DesignCode, et: float, ety: float) -> float:
    """Return flexural phi for rectangular nonprestressed beam sections.

    The beam app uses the nonprestressed flexure strain-transition rules from
    the selected ACI code family. ACI 318-99 keeps phi = 0.90 for this beam
    scope, while ACI 318-08/11/14 use the fixed tension-controlled strain
    limit of 0.005 and ACI 318-19/25 use ety + 0.003.
    """
    if math.isnan(et):
        return math.nan
    if design_code == DesignCode.ACI318_99:
        return PHI_FLEXURE_MAX
    if design_code in {DesignCode.ACI318_08, DesignCode.ACI318_11, DesignCode.ACI318_14}:
        return _interpolate_phi(et, ety, ACI_318_11_14_TENSION_CONTROLLED_STRAIN)
    return _interpolate_phi(et, ety, ety + 0.003)


def calculate_rho_required(fc_prime_ksc: float, fy_ksc: float, ru_kg_per_cm2: float) -> float:
    """Return required steel ratio from the rectangular stress-block solution.

    This is the direct rectangular beam solution used when flexure is evaluated
    without compression-steel contribution, based on the ACI rectangular
    compression block assumptions used in Chapter 10 (ACI 318-99/11) and
    Section 22.2 (ACI 318-14/19).
    """
    discriminant = 1 - ((2 * ru_kg_per_cm2) / (0.85 * fc_prime_ksc))
    if discriminant < 0:
        return math.nan
    return 0.85 * (fc_prime_ksc / fy_ksc) * (1 - math.sqrt(discriminant))


def calculate_rho_min(design_code: DesignCode, fc_prime_ksc: float, fy_ksc: float) -> float:
    """Return minimum tensile steel ratio for nonprestressed beams.

    ACI 318-99 uses Section 10.5.1.
    ACI 318-08 keeps the same beam minimum logic in Section 10.5.1.
    ACI 318-11 keeps the same beam minimum logic in Section 10.5.1.
    ACI 318-14/19/25 use Section 9.6.1.2.
    """
    if design_code == DesignCode.ACI318_99:
        return 14 / fy_ksc
    return max((14 / fy_ksc), (0.8 * math.sqrt(fc_prime_ksc) / fy_ksc))


def calculate_rho_max(
    design_code: DesignCode,
    fc_prime_ksc: float,
    fy_ksc: float,
    beta_1: float,
    es_ksc: float = 2.04 * (10**6),
) -> float:
    """Return the app's audited upper steel-ratio limit for beam flexure.

    ACI does not provide a single ``rho_max`` symbol for this beam workflow in
    the modern code editions, so this helper derives the limit from the
    governing flexural strain-limit clauses and the rectangular stress block.

    - ACI 318-99: legacy beam limit based on 0.75 rho_bal
    - ACI 318-08/11/14: tension-controlled limit at et = 0.005
    - ACI 318-19/25: tension-controlled limit at et = ety + 0.003
    """
    epsilon_y = fy_ksc / es_ksc
    if design_code == DesignCode.ACI318_99:
        rho_balanced = 0.85 * beta_1 * (fc_prime_ksc / fy_ksc) * (ECU / (ECU + epsilon_y))
        return 0.75 * rho_balanced
    tension_controlled_strain = (
        ACI_318_11_14_TENSION_CONTROLLED_STRAIN
        if design_code in {DesignCode.ACI318_08, DesignCode.ACI318_11, DesignCode.ACI318_14}
        else epsilon_y + 0.003
    )
    return 0.85 * beta_1 * (fc_prime_ksc / fy_ksc) * (ECU / (ECU + tension_controlled_strain))


def _interpolate_phi(et: float, compression_controlled_limit: float, tension_controlled_limit: float) -> float:
    if et <= compression_controlled_limit:
        return PHI_FLEXURE_MIN
    if et >= tension_controlled_limit:
        return PHI_FLEXURE_MAX
    transition = (et - compression_controlled_limit) / (tension_controlled_limit - compression_controlled_limit)
    return PHI_FLEXURE_MIN + (PHI_FLEXURE_MAX - PHI_FLEXURE_MIN) * transition
