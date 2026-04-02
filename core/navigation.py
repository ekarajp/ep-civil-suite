from __future__ import annotations

from dataclasses import dataclass

import streamlit as st


HOME_VIEW = "landing"
ACTIVE_VIEW_KEY = "_engineering_suite_active_view"


@dataclass(frozen=True, slots=True)
class ToolDefinition:
    key: str
    title: str
    description: str
    status: str
    available: bool


TOOLS: tuple[ToolDefinition, ...] = (
    ToolDefinition(
        key="reference_library",
        title="Reference Library",
        description="Import local PDF references into an offline searchable code library.",
        status="Available",
        available=True,
    ),
    ToolDefinition(
        key="rc_beam",
        title="RC Beam Analysis",
        description="Reinforced concrete beam analysis and design.",
        status="Available",
        available=True,
    ),
    ToolDefinition(
        key="beam_fiber_model",
        title="Beam Fiber Model",
        description="Section fiber analysis and nonlinear response modeling.",
        status="Coming Soon",
        available=False,
    ),
)


def get_tools() -> tuple[ToolDefinition, ...]:
    return TOOLS


def current_view() -> str:
    return str(st.session_state.get(ACTIVE_VIEW_KEY, HOME_VIEW))


def open_tool(tool_key: str) -> None:
    st.session_state[ACTIVE_VIEW_KEY] = tool_key


def go_home() -> None:
    st.session_state[ACTIVE_VIEW_KEY] = HOME_VIEW
