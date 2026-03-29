"""Validation helpers for the torsion engine scaffold."""

from design.torsion import TorsionDesignResults


def validate_torsion_results(results: TorsionDesignResults) -> list[str]:
    """Normalize torsion warnings into sentence-style messages."""
    return [message if message.endswith(".") else f"{message}." for message in results.warnings]

