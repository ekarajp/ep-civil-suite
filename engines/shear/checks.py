"""Design status checks for the reusable beam shear design engine."""


def build_shear_review_note(
    *,
    av_cm2: float,
    av_min_cm2: float,
    design_code_label: str,
    provided_spacing_cm: float,
    required_spacing_cm: float,
    section_change_required: bool,
    section_change_note: str,
    strength_limit_ok: bool,
    vc_capped_by_max: bool,
    vc_max_kg: float | None,
    size_effect_factor: float,
    vs_provided_kg: float,
    vs_max_kg: float,
) -> str:
    """Build the same review-note phrasing currently used by the app."""
    review_notes: list[str] = []
    if section_change_required:
        review_notes.append(section_change_note)
    if not strength_limit_ok:
        review_notes.append("Required shear reinforcement exceeds the current section limit. Increase section size or revise detailing.")
    if provided_spacing_cm > required_spacing_cm + 1e-9:
        review_notes.append(
            f"Provided spacing {provided_spacing_cm:.2f} cm exceeds required spacing {required_spacing_cm:.2f} cm."
        )
    if av_cm2 < av_min_cm2 - 1e-9:
        review_notes.append(
            f"Av = {av_cm2:.3f} cm2 is less than Av,min = {av_min_cm2:.3f} cm2."
        )
        if design_code_label == "ACI318-19":
            review_notes.append(
                f"ACI 318-19 size effect factor lambda_s = {size_effect_factor:.3f} was applied to Vc."
            )
    if vc_capped_by_max and vc_max_kg is not None:
        review_notes.append(
            f"ACI 318-19 Vc was limited to Vc,max = {vc_max_kg:.3f} kg."
        )
    if vs_provided_kg > vs_max_kg + 1e-9:
        review_notes.append("Provided stirrup spacing gives Vs above Vs,max; PhiVn is capped at the section shear limit.")
    return " ".join(review_notes)

