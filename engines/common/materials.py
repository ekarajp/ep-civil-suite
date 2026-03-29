"""Shared material input and derived material-property calculations."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import math

from .validation import validate_positive


DEFAULT_EC_LOGIC = "Ec = 15100 * sqrt(fc')"
DEFAULT_ES_LOGIC = "Es = 2.04 * 10^6"
DEFAULT_FR_LOGIC = "fr = 2 * sqrt(fc')"
ES_KSC = 2.04 * (10**6)


class MaterialPropertyMode(str, Enum):
    """How an optional material property is sourced."""

    DEFAULT = "Default"
    MANUAL = "Manual"


@dataclass(slots=True)
class MaterialPropertiesInput:
    """Concrete and reinforcing steel strengths for beam engines."""

    concrete_strength_ksc: float = 240.0
    main_steel_yield_ksc: float = 4000.0
    shear_steel_yield_ksc: float = 2400.0

    def __post_init__(self) -> None:
        validate_positive(self.concrete_strength_ksc, "concrete_strength_ksc")
        validate_positive(self.main_steel_yield_ksc, "main_steel_yield_ksc")
        validate_positive(self.shear_steel_yield_ksc, "shear_steel_yield_ksc")


@dataclass(slots=True)
class MaterialPropertySetting:
    """Optional override for a derived material property."""

    mode: MaterialPropertyMode = MaterialPropertyMode.DEFAULT
    manual_value: float | None = None

    def __post_init__(self) -> None:
        if self.mode == MaterialPropertyMode.MANUAL:
            if self.manual_value is None:
                raise ValueError("manual_value must be provided when mode is Manual.")
            validate_positive(self.manual_value, "manual_value")
        elif self.manual_value is not None:
            validate_positive(self.manual_value, "manual_value")


@dataclass(slots=True)
class MaterialPropertySettings:
    """Optional override settings for Ec, Es, and fr."""

    ec: MaterialPropertySetting = field(default_factory=MaterialPropertySetting)
    es: MaterialPropertySetting = field(default_factory=MaterialPropertySetting)
    fr: MaterialPropertySetting = field(default_factory=MaterialPropertySetting)


@dataclass(slots=True)
class MaterialResults:
    """Derived material properties reused by beam engines."""

    fc_prime_ksc: float
    fy_ksc: float
    fvy_ksc: float
    ec_ksc: float
    es_ksc: float
    modular_ratio_n: float
    modulus_of_rupture_fr_ksc: float
    beta_1: float
    ec_mode: MaterialPropertyMode
    es_mode: MaterialPropertyMode
    fr_mode: MaterialPropertyMode
    ec_default_ksc: float
    es_default_ksc: float
    fr_default_ksc: float
    ec_default_logic: str
    es_default_logic: str
    fr_default_logic: str


def calculate_default_ec_ksc(fc_prime_ksc: float) -> float:
    """ACI-style default concrete elastic modulus in ksc."""
    return 15100 * math.sqrt(fc_prime_ksc)


def calculate_default_es_ksc() -> float:
    """Default reinforcing-steel elastic modulus in ksc."""
    return ES_KSC


def calculate_default_fr_ksc(fc_prime_ksc: float) -> float:
    """Default modulus of rupture in ksc."""
    return 2 * math.sqrt(fc_prime_ksc)


def calculate_beta_1(fc_prime_ksc: float) -> float:
    """Beta1 block factor used by flexural calculations."""
    if 0 < fc_prime_ksc <= 280:
        return 0.85
    return max(0.65, 0.85 - (0.05 * (fc_prime_ksc - 280) / 70))


def calculate_material_properties(
    materials: MaterialPropertiesInput,
    material_settings: MaterialPropertySettings | None = None,
) -> MaterialResults:
    """Build the full set of derived material properties."""
    settings = material_settings or MaterialPropertySettings()
    ec_default_ksc = calculate_default_ec_ksc(materials.concrete_strength_ksc)
    es_default_ksc = calculate_default_es_ksc()
    fr_default_ksc = calculate_default_fr_ksc(materials.concrete_strength_ksc)
    ec_ksc = ec_default_ksc if settings.ec.mode == MaterialPropertyMode.DEFAULT else _manual_property_value(settings.ec.manual_value)
    es_ksc = es_default_ksc if settings.es.mode == MaterialPropertyMode.DEFAULT else _manual_property_value(settings.es.manual_value)
    fr_ksc = fr_default_ksc if settings.fr.mode == MaterialPropertyMode.DEFAULT else _manual_property_value(settings.fr.manual_value)
    return MaterialResults(
        fc_prime_ksc=materials.concrete_strength_ksc,
        fy_ksc=materials.main_steel_yield_ksc,
        fvy_ksc=materials.shear_steel_yield_ksc,
        ec_ksc=ec_ksc,
        es_ksc=es_ksc,
        modular_ratio_n=es_ksc / ec_ksc,
        modulus_of_rupture_fr_ksc=fr_ksc,
        beta_1=calculate_beta_1(materials.concrete_strength_ksc),
        ec_mode=settings.ec.mode,
        es_mode=settings.es.mode,
        fr_mode=settings.fr.mode,
        ec_default_ksc=ec_default_ksc,
        es_default_ksc=es_default_ksc,
        fr_default_ksc=fr_default_ksc,
        ec_default_logic=DEFAULT_EC_LOGIC,
        es_default_logic=DEFAULT_ES_LOGIC,
        fr_default_logic=DEFAULT_FR_LOGIC,
    )


def _manual_property_value(value: float | None) -> float:
    if value is None:
        raise ValueError("Manual material property value is missing.")
    return value
