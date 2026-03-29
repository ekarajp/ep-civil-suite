from __future__ import annotations

KGF_TO_NEWTON = 9.80665
CM_TO_MM = 10.0
KSC_TO_MPA = KGF_TO_NEWTON / 100.0


def kgf_to_newton(force_kgf: float) -> float:
    return force_kgf * KGF_TO_NEWTON


def newton_to_kgf(force_n: float) -> float:
    return force_n / KGF_TO_NEWTON


def kgf_m_to_n_mm(moment_kgfm: float) -> float:
    return kgf_to_newton(moment_kgfm) * 1000.0


def n_mm_to_kgf_m(moment_nmm: float) -> float:
    return newton_to_kgf(moment_nmm) / 1000.0


def cm_to_mm(length_cm: float) -> float:
    return length_cm * CM_TO_MM


def mm_to_cm(length_mm: float) -> float:
    return length_mm / CM_TO_MM


def cm2_to_mm2(area_cm2: float) -> float:
    return area_cm2 * (CM_TO_MM**2)


def mm2_to_cm2(area_mm2: float) -> float:
    return area_mm2 / (CM_TO_MM**2)


def ksc_to_mpa(stress_ksc: float) -> float:
    return stress_ksc * KSC_TO_MPA
