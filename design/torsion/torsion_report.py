from __future__ import annotations

from core.utils import format_number

from .torsion_base import TorsionDesignResults
from .torsion_units import mm2_to_cm2


def build_torsion_report_rows(results: TorsionDesignResults) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for step in results.steps:
        rows.append(
            {
                "variable": step.variable,
                "equation": step.equation,
                "substitution": step.substitution,
                "result": step.result,
                "units": step.units,
                "clause": step.clause,
                "status": step.status,
                "note": step.note,
            }
        )
    return rows


def torsion_workspace_summary_lines(results: TorsionDesignResults) -> list[str]:
    if not results.enabled:
        return []
    if results.can_neglect_torsion:
        return [
            f"Tu = {format_number(results.tu_kgfm)} kgf-m | Threshold = {format_number(results.threshold_torsion_kgfm)} kgf-m",
            "Neglect check = torsion may be neglected.",
            f"Status = {results.status}",
        ]
    return [
        f"Tu = {format_number(results.tu_kgfm)} kgf-m | Threshold = {format_number(results.threshold_torsion_kgfm)} kgf-m | {results.status}",
        f"At/s req. = {results.transverse_reinf_required_mm2_per_mm:.6f} mm2/mm | Al req. = {format_number(mm2_to_cm2(results.longitudinal_reinf_required_mm2))} cm2",
    ]


def build_torsion_report_html(results: TorsionDesignResults) -> str:
    rows = build_torsion_report_rows(results)
    body = "".join(
        "<tr>"
        f"<td>{row['variable']}</td>"
        f"<td>{row['equation']}</td>"
        f"<td>{row['substitution']}</td>"
        f"<td>{row['result']}</td>"
        f"<td>{row['units']}</td>"
        f"<td>{row['clause']}</td>"
        "</tr>"
        for row in rows
    )
    return (
        "<table class='torsion-report-table'>"
        "<thead><tr>"
        "<th>Variable</th><th>Equation</th><th>Substitution</th><th>Result</th><th>Units</th><th>Clause</th>"
        "</tr></thead>"
        f"<tbody>{body}</tbody>"
        "</table>"
    )
