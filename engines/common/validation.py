"""Validation helpers shared by engine packages."""


def validate_positive(value: float, field_name: str) -> None:
    """Raise when a positive-only numeric field is invalid."""
    if value <= 0:
        raise ValueError(f"{field_name} must be greater than zero.")


def validate_non_negative(value: float, field_name: str) -> None:
    """Raise when a non-negative numeric field is invalid."""
    if value < 0:
        raise ValueError(f"{field_name} must be zero or greater.")


def require_value(value: float | None, field_name: str) -> float:
    """Return a required value or raise a validation error."""
    if value is None:
        raise ValueError(f"{field_name} is required.")
    return value

