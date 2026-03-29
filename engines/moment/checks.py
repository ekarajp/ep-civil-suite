"""Design status checks for the reusable beam moment design engine."""


def calculate_as_status(rho_provided: float, rho_min: float, rho_max: float) -> str:
    """Return the steel-area status label used by the legacy UI."""
    if rho_min <= rho_provided <= rho_max:
        return "OK"
    if rho_provided <= rho_min:
        return "NOT OK As < As min"
    return "NOT OK As > As max"

