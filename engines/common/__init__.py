"""Shared data models and helpers for reusable calculation engines."""

from .geometry import BeamGeometryInputData, calculate_beam_geometry, calculate_reinforcement_spacing
from .materials import (
    DEFAULT_EC_LOGIC,
    DEFAULT_ES_LOGIC,
    DEFAULT_FR_LOGIC,
    MaterialPropertiesInput,
    MaterialPropertyMode,
    MaterialPropertySetting,
    MaterialPropertySettings,
    MaterialResults,
    calculate_default_ec_ksc,
    calculate_default_es_ksc,
    calculate_default_fr_ksc,
    calculate_material_properties,
)
from .result_objects import (
    BeamGeometryResults,
    BeamSectionInput,
    DesignCode,
    LayerSpacingResult,
    RebarGroupInput,
    RebarLayerInput,
    ReinforcementArrangementInput,
    ReinforcementSpacingResults,
    ShearSpacingMode,
)

__all__ = [
    "BeamGeometryInputData",
    "BeamGeometryResults",
    "BeamSectionInput",
    "DEFAULT_EC_LOGIC",
    "DEFAULT_ES_LOGIC",
    "DEFAULT_FR_LOGIC",
    "DesignCode",
    "LayerSpacingResult",
    "MaterialPropertiesInput",
    "MaterialPropertyMode",
    "MaterialPropertySetting",
    "MaterialPropertySettings",
    "MaterialResults",
    "RebarGroupInput",
    "RebarLayerInput",
    "ReinforcementArrangementInput",
    "ReinforcementSpacingResults",
    "ShearSpacingMode",
    "calculate_beam_geometry",
    "calculate_default_ec_ksc",
    "calculate_default_es_ksc",
    "calculate_default_fr_ksc",
    "calculate_material_properties",
    "calculate_reinforcement_spacing",
]

