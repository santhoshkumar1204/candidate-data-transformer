"""Streamlit application for Candidate Data Transformer."""

from __future__ import annotations

import json
import math
import sys
from collections import Counter
from dataclasses import asdict
from html import escape
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

try:
    import plotly.express as px
except ImportError:  # pragma: no cover - lets the app render a helpful fallback before deps are installed.
    px = None

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from candidate_data_transformer.pipeline import CandidatePipeline, PipelineResult, configure_logging
from generate_dataset import generate_dataset

st.set_page_config(
    page_title="Candidate Data Transformer",
    layout="wide",
    initial_sidebar_state="expanded",
)

DATASET_DIR = ROOT / "datasets"
OUTPUT_PATH = ROOT / "outputs" / "merged_candidates.json"
CONFIG_DIR = ROOT / "config"

PAGE_ITEMS = [
    ("Home", ":material/home:"),
    ("Upload Dataset", ":material/upload_file:"),
    ("Pipeline Execution", ":material/play_circle:"),
    ("Merged Candidate Viewer", ":material/table_view:"),
    ("Before vs After Comparison", ":material/compare_arrows:"),
    ("Confidence Viewer", ":material/verified:"),
    ("Provenance Viewer", ":material/account_tree:"),
    ("Configuration Viewer", ":material/settings:"),
    ("Pipeline Statistics", ":material/monitoring:"),
    ("Data Quality Dashboard", ":material/fact_check:"),
]

PIPELINE_STAGES = [
    ("Parse", "Source-specific parsers read recruiter CSV, ATS JSON, LinkedIn text, and resume Markdown."),
    ("Normalize", "Canonical candidates are standardized for whitespace, identifiers, aliases, and date metadata."),
    ("Block", "Deterministic blocking reduces the candidate pair search space."),
    ("Similarity", "Weighted identity signals score blocked candidate pairs."),
    ("Merge", "Confirmed matches are merged into deterministic canonical profiles."),
    ("Validate", "Merged canonical profiles are checked for schema and semantic issues."),
    ("Project", "Output projection flattens, renames, and shapes runtime JSON."),
    ("Output", "Projected results are saved to JSON and surfaced in Streamlit."),
]

BASE_COMPARE_FIELDS = [
    "candidate_id",
    "full_name",
    "emails",
    "phones",
    "current_company",
    "current_title",
    "experience.years",
    "experience.summary",
    "experience.entries",
    "education.highest_degree",
    "education.university",
    "education.graduation_year",
    "skills",
    "certifications",
    "projects",
    "location.current",
    "location.preferred",
    "linkedin_url",
    "github_url",
    "source",
]

CARD_TONES = {
    "blue": "tone-blue",
    "green": "tone-green",
    "orange": "tone-orange",
    "red": "tone-red",
    "slate": "tone-slate",
}


def inject_styles() -> None:
    """Inject a restrained internal-dashboard style layer."""

    st.markdown(
        """
        <style>
        :root {
            --cdt-border: color-mix(in srgb, var(--text-color) 18%, transparent);
            --cdt-border-soft: color-mix(in srgb, var(--text-color) 10%, transparent);
            --cdt-muted: color-mix(in srgb, var(--text-color) 68%, transparent);
            --cdt-faint: color-mix(in srgb, var(--text-color) 48%, transparent);
            --cdt-surface: var(--background-color);
            --cdt-surface-muted: var(--secondary-background-color);
            --cdt-primary-soft: color-mix(in srgb, var(--primary-color) 14%, transparent);
            --cdt-primary-border: color-mix(in srgb, var(--primary-color) 42%, var(--cdt-border));
            --cdt-shadow: 0 8px 24px color-mix(in srgb, var(--text-color) 10%, transparent);
        }
        .stApp {
            background: var(--background-color);
            color: var(--text-color);
        }
        .block-container {
            padding-top: 1rem;
            padding-right: 1.5rem;
            padding-left: 1.5rem;
            padding-bottom: 2.25rem;
            max-width: 100%;
        }
        section[data-testid="stSidebar"] {
            background: var(--secondary-background-color);
            border-right: 1px solid var(--cdt-border);
        }
        section[data-testid="stSidebar"] .block-container {
            padding-top: 1rem;
            padding-left: 1rem;
            padding-right: 1rem;
        }
        .ui-shell,
        .ui-card,
        .sidebar-brand,
        .sidebar-stat,
        .stage-card,
        .compare-shell,
        .provenance-block,
        .diagram-card,
        .filter-shell,
        .table-shell,
        .toolbar-shell,
        .stage-flow-card,
        .compare-field,
        .band-pill {
            background: var(--cdt-surface);
            border: 1px solid var(--cdt-border);
            border-radius: 8px;
            box-shadow: var(--cdt-shadow);
        }
        .ui-shell {
            padding: 1.25rem 1.25rem 1.1rem 1.25rem;
        }
        .ui-card {
            padding: 1rem 1rem 0.9rem 1rem;
            margin-bottom: 0.75rem;
        }
        .eyebrow,
        .ui-card .eyebrow,
        .sidebar-stat .eyebrow,
        .stage-flow-card .meta-label,
        .compare-field .field-name {
            font-size: 0.75rem;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            color: var(--cdt-faint);
            margin-bottom: 0.35rem;
        }
        .ui-card .value,
        .sidebar-stat .value {
            font-weight: 700;
            color: var(--text-color);
            line-height: 1.1;
        }
        .ui-card .value {
            font-size: 1.7rem;
            margin-bottom: 0.35rem;
        }
        .ui-card .support,
        .support,
        .ui-subtitle,
        .ui-section-note,
        .muted,
        .stage-card p,
        .stage-flow-card .stage-body {
            color: var(--cdt-muted);
        }
        .ui-title {
            font-size: 2rem;
            font-weight: 700;
            color: var(--text-color);
            margin-bottom: 0.25rem;
        }
        .ui-subtitle {
            font-size: 1rem;
            line-height: 1.6;
        }
        .ui-section {
            font-size: 1.15rem;
            font-weight: 700;
            color: var(--text-color);
            margin: 0.2rem 0 0.15rem 0;
        }
        .ui-section-note {
            margin-bottom: 0.75rem;
        }
        .status-chip {
            display: inline-block;
            border-radius: 999px;
            padding: 0.22rem 0.65rem;
            font-size: 0.78rem;
            font-weight: 600;
            margin-right: 0.35rem;
            border: 1px solid var(--cdt-primary-border);
            background: var(--cdt-primary-soft);
            color: var(--text-color);
        }
        .tone-slate {
            border-color: var(--cdt-border);
            background: var(--cdt-surface-muted);
        }
        .tone-blue,
        .tone-green,
        .tone-orange,
        .tone-red {
            border-color: var(--cdt-primary-border);
            background: var(--cdt-primary-soft);
        }
        .stage-track {
            display: flex;
            flex-wrap: wrap;
            gap: 0.55rem;
            margin-top: 0.65rem;
        }
        .stage-node,
        .stage-flow-card .stage-index,
        .brand-mark {
            background: var(--cdt-primary-soft);
            border: 1px solid var(--cdt-primary-border);
            color: var(--text-color);
            font-weight: 700;
        }
        .stage-node {
            border-radius: 999px;
            padding: 0.42rem 0.8rem;
            font-size: 0.84rem;
        }
        .sidebar-brand {
            padding: 1rem;
            margin-bottom: 1rem;
        }
        .brand-mark {
            width: 2.6rem;
            height: 2.6rem;
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1rem;
            margin-bottom: 0.7rem;
        }
        .sidebar-stat-grid {
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 0.55rem;
            margin-top: 0.85rem;
        }
        .sidebar-stat {
            padding: 0.7rem 0.75rem;
        }
        .sidebar-stat .value {
            font-size: 1.05rem;
        }
        section[data-testid="stSidebar"] .stButton {
            margin-bottom: 0.35rem;
        }
        section[data-testid="stSidebar"] .stButton > button {
            justify-content: flex-start;
            border-radius: 8px;
            min-height: 2.8rem;
            font-weight: 600;
        }
        .stage-card {
            padding: 1rem;
            min-height: 200px;
        }
        .stage-card h4,
        .keyline,
        .stage-flow-card .stage-name,
        .compare-field .field-value {
            color: var(--text-color);
        }
        .stage-card h4 {
            font-size: 1rem;
            margin: 0 0 0.35rem 0;
        }
        .stage-card p,
        .stage-flow-card .stage-body {
            font-size: 0.9rem;
            line-height: 1.45;
            margin-bottom: 0.65rem;
        }
        .keyline {
            font-weight: 600;
            margin-bottom: 0.18rem;
            font-size: 0.88rem;
        }
        .compare-shell,
        .provenance-block {
            padding: 1rem;
        }
        .provenance-block {
            padding: 0.9rem 1rem;
        }
        .diagram-card {
            padding: 1rem;
        }
        .diagram-flow {
            display: grid;
            grid-template-columns: repeat(8, minmax(0, 1fr));
            gap: 0.45rem;
            align-items: center;
        }
        .diagram-step {
            border: 1px solid var(--cdt-primary-border);
            background: var(--cdt-primary-soft);
            border-radius: 8px;
            padding: 0.65rem 0.55rem;
            text-align: center;
        }
        .diagram-step .eyebrow {
            margin-bottom: 0.2rem;
        }
        .diagram-arrow,
        .flow-arrow {
            color: var(--cdt-faint);
            font-weight: 700;
        }
        .diagram-arrow {
            text-align: center;
        }
        .stage-flow-scroll {
            overflow-x: auto;
            padding-bottom: 0.35rem;
        }
        .stage-flow {
            display: grid;
            grid-auto-flow: column;
            grid-auto-columns: minmax(220px, 1fr);
            gap: 0.7rem;
            align-items: stretch;
        }
        .stage-flow-card {
            padding: 1rem;
            min-height: 232px;
        }
        .stage-flow-card .stage-index {
            width: 1.65rem;
            height: 1.65rem;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            border-radius: 999px;
            font-size: 0.8rem;
            margin-bottom: 0.7rem;
        }
        .stage-flow-card .stage-name {
            font-size: 1rem;
            font-weight: 700;
            margin-bottom: 0.35rem;
        }
        .stage-flow-card .meta-label {
            font-weight: 700;
            margin-top: 0.65rem;
            margin-bottom: 0.15rem;
        }
        .flow-arrow {
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.15rem;
        }
        .filter-shell,
        .toolbar-shell {
            padding: 0.9rem 1rem 0.2rem 1rem;
            margin-bottom: 0.8rem;
        }
        .table-shell {
            padding: 0.85rem;
        }
        .compare-field {
            padding: 0.8rem 0.9rem;
            margin-bottom: 0.6rem;
            min-height: 96px;
        }
        .compare-field.changed {
            border-color: var(--cdt-primary-border);
            background: var(--cdt-primary-soft);
        }
        .compare-field .field-value {
            font-size: 0.95rem;
            line-height: 1.5;
            word-break: break-word;
        }
        .compare-field .field-note {
            margin-top: 0.45rem;
            font-size: 0.8rem;
            color: var(--text-color);
            font-weight: 600;
        }
        .band-legend {
            display: flex;
            flex-wrap: wrap;
            gap: 0.5rem;
            margin-top: 0.55rem;
        }
        .band-pill {
            display: inline-flex;
            align-items: center;
            gap: 0.35rem;
            border-radius: 999px;
            padding: 0.28rem 0.65rem;
            font-size: 0.82rem;
            font-weight: 600;
            color: var(--text-color);
        }
        div[data-testid="stDataFrame"] {
            border: 1px solid var(--cdt-border);
            border-radius: 8px;
            overflow: hidden;
            box-shadow: var(--cdt-shadow);
        }
        @media (max-width: 1200px) {
            .diagram-flow {
                grid-template-columns: repeat(4, minmax(0, 1fr));
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


inject_styles()


def run_pipeline() -> PipelineResult:
    """Run the pipeline and cache results in session state."""

    configure_logging()
    result = CandidatePipeline(dataset_dir=DATASET_DIR).run(output_path=OUTPUT_PATH)
    st.session_state["pipeline_result"] = result
    return result


def get_result() -> PipelineResult | None:
    """Return the latest pipeline result from session state."""

    return st.session_state.get("pipeline_result")


def as_dataframe(rows: list[dict[str, Any]]) -> pd.DataFrame:
    """Build a display dataframe from dictionaries."""

    return pd.DataFrame(rows) if rows else pd.DataFrame()


def load_json_file(path: Path, default: Any) -> Any:
    """Load JSON from disk with a safe fallback."""

    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def read_output_payload() -> dict[str, Any] | None:
    """Read the most recent projected output payload when available."""

    return load_json_file(OUTPUT_PATH, None)


def read_output_text() -> str | None:
    """Return the current saved output JSON text when present."""

    try:
        return OUTPUT_PATH.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None


def dataset_summary_payload() -> dict[str, Any] | None:
    """Return the current dataset summary file when available."""

    return load_json_file(DATASET_DIR / "dataset_summary.json", None)


def dataset_inventory() -> dict[str, int]:
    """Return current source inventory counts."""

    inventory = {
        "recruiter_rows": 0,
        "ats_records": 0,
        "linkedin_profiles": len(list((DATASET_DIR / "linkedin").glob("*.txt"))),
        "resume_files": len(list((DATASET_DIR / "resume").glob("*.md"))),
    }
    recruiter_path = DATASET_DIR / "recruiter.csv"
    if recruiter_path.exists():
        try:
            inventory["recruiter_rows"] = len(pd.read_csv(recruiter_path))
        except Exception:
            pass
    ats_path = DATASET_DIR / "ats.json"
    if ats_path.exists():
        payload = load_json_file(ats_path, [])
        if isinstance(payload, list):
            inventory["ats_records"] = len(payload)
    return inventory


def recruiter_preview(limit: int = 10) -> pd.DataFrame:
    """Return a small recruiter dataset preview."""

    recruiter_path = DATASET_DIR / "recruiter.csv"
    if not recruiter_path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(recruiter_path).head(limit)
    except Exception:
        return pd.DataFrame()


def test_suite_count() -> int:
    """Count repository test suites."""

    return len(list((ROOT / "tests").glob("test_*.py")))


def output_config_payload() -> dict[str, Any]:
    """Return the active output configuration."""

    return load_json_file(CONFIG_DIR / "output_config.json", {})


def safe_stat_dict() -> dict[str, Any]:
    """Return the best available stats payload."""

    result = get_result()
    if result:
        return asdict(result.stats)
    payload = read_output_payload()
    if isinstance(payload, dict):
        stats = payload.get("stats")
        if isinstance(stats, dict):
            return stats
    return {}


def projected_snapshot() -> list[dict[str, Any]]:
    """Return projected candidates from the active session or latest output."""

    result = get_result()
    if result:
        return result.projected_candidates
    payload = read_output_payload()
    if isinstance(payload, dict) and isinstance(payload.get("candidates"), list):
        return payload["candidates"]
    return []


def format_value(value: Any) -> str:
    """Return a compact display string for a value."""

    if value is None:
        return "-"
    if isinstance(value, float):
        return f"{value:.4f}".rstrip("0").rstrip(".")
    if isinstance(value, list):
        return ", ".join(format_value(item) for item in value) if value else "-"
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=True)
    return str(value)


def status_tone_from_errors(error_count: int | None) -> str:
    """Return a tone key from validation error counts."""

    if error_count is None:
        return "slate"
    if error_count == 0:
        return "green"
    return "red"


def confidence_tone(score: float | None) -> str:
    """Return a tone bucket for a confidence score."""

    if score is None:
        return "slate"
    if score >= 0.90:
        return "green"
    if score >= 0.70:
        return "blue"
    return "orange"


def render_status_chip(label: str, tone: str = "blue") -> str:
    """Build a compact theme-aware status chip."""

    tone_class = CARD_TONES.get(tone, CARD_TONES["blue"])
    return f"<span class='status-chip {tone_class}'>{escape(label)}</span>"


def render_metric_cards(cards: list[dict[str, Any]], columns: int = 4) -> None:
    """Render KPI cards with Streamlit metric primitives."""

    for start in range(0, len(cards), columns):
        row = cards[start : start + columns]
        cols = st.columns(len(row))
        for column, card in zip(cols, row):
            with column:
                with st.container(border=True):
                    icon = str(card.get("icon", ":material/analytics:"))
                    st.caption(f"{icon} {card['title']}")
                    st.metric(label=" ", value=card["value"], delta=card.get("delta"), label_visibility="collapsed")
                    support = card.get("support")
                    if support:
                        st.caption(str(support))


def render_page_header(title: str, subtitle: str) -> None:
    """Render a consistent page header."""

    stats = safe_stat_dict()
    validation_errors = stats.get("validation_errors")
    ready_tone = "green" if validation_errors in (0, None) else "orange"
    st.markdown(
        f"""
        <div class="ui-shell">
          <div style="display:flex;justify-content:space-between;gap:1rem;align-items:flex-start;flex-wrap:wrap;">
            <div>
              <div class="ui-title">{escape(title)}</div>
              <div class="ui-subtitle">{escape(subtitle)}</div>
            </div>
            <div style="text-align:right;min-width:260px;">
              {render_status_chip('Ready', ready_tone)}
              {render_status_chip('output_config.json', 'blue')}
              {render_status_chip('Pipeline: Operational', 'green')}
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

def render_section(title: str, note: str | None = None) -> None:
    """Render a section title and optional note."""

    st.markdown(f"<div class='ui-section'>{escape(title)}</div>", unsafe_allow_html=True)
    if note:
        st.markdown(f"<div class='ui-section-note'>{escape(note)}</div>", unsafe_allow_html=True)


def render_pipeline_track() -> None:
    """Render the pipeline overview track."""

    flow = [
        "Recruiter CSV",
        "ATS JSON",
        "LinkedIn",
        "Resume",
        "Parse",
        "Normalize",
        "Identity Resolution",
        "Merge",
        "Confidence",
        "Projection",
        "Validation",
        "Merged JSON",
    ]
    nodes = "".join(f"<span class='stage-node'>{escape(name)}</span>" for name in flow)
    st.markdown(f"<div class='stage-track'>{nodes}</div>", unsafe_allow_html=True)

def render_pipeline_diagram_card() -> None:
    """Render a compact engineering-style pipeline diagram."""

    diagram_parts: list[str] = ["<div class='diagram-card'><div class='diagram-flow'>"]
    for index, (name, _) in enumerate(PIPELINE_STAGES, start=1):
        diagram_parts.append(
            f"""
            <div class="diagram-step">
              <div class="eyebrow">Stage {index}</div>
              <div style="font-size:0.92rem;font-weight:700;">{escape(name)}</div>
            </div>
            """
        )
        if index < len(PIPELINE_STAGES):
            diagram_parts.append("<div class='diagram-arrow'>&rarr;</div>")
    diagram_parts.append("</div></div>")
    st.markdown("".join(diagram_parts), unsafe_allow_html=True)


def source_distribution(result: PipelineResult) -> pd.DataFrame:
    """Build parsed source distribution dataframe."""

    counts = Counter(candidate.source for candidate in result.parsed_candidates)
    return pd.DataFrame(
        [{"source": source, "count": count} for source, count in sorted(counts.items())]
    )


def confidence_distribution_df(stats: dict[str, Any]) -> pd.DataFrame:
    """Build confidence distribution dataframe."""

    distribution = stats.get("confidence_distribution", {})
    return pd.DataFrame(
        [{"bucket": bucket.title(), "count": count} for bucket, count in distribution.items()]
    )


def donut_chart(dataframe: pd.DataFrame, category: str, value: str, title: str) -> None:
    """Render a Plotly donut chart."""

    if dataframe.empty:
        st.info("No chart data available.")
        return
    if px is None:
        st.warning("Install Plotly to enable polished interactive charts: python -m pip install plotly")
        st.bar_chart(dataframe.set_index(category), width="stretch", height=320)
        return
    fig = px.pie(
        dataframe,
        names=category,
        values=value,
        hole=0.55,
    )
    fig.update_traces(textposition="inside", textinfo="percent+label", hovertemplate="%{label}<br>%{value}<extra></extra>")
    fig.update_layout(
        title={"text": title, "font": {"size": 16}},
        height=320,
        margin={"l": 12, "r": 12, "t": 56, "b": 12},
        legend_title_text="",
    )
    st.plotly_chart(fig, width="stretch", theme="streamlit")


def bar_chart(dataframe: pd.DataFrame, x: str, y: str, title: str) -> None:
    """Render a Plotly bar chart."""

    if dataframe.empty:
        st.info("No chart data available.")
        return
    if px is None:
        st.warning("Install Plotly to enable polished interactive charts: python -m pip install plotly")
        st.bar_chart(dataframe.set_index(x), width="stretch", height=320)
        return
    fig = px.bar(dataframe, x=x, y=y, text=y)
    fig.update_traces(textposition="outside", hovertemplate=f"%{{x}}<br>%{{y}}<extra></extra>")
    fig.update_layout(
        title={"text": title, "font": {"size": 16}},
        height=320,
        margin={"l": 12, "r": 12, "t": 56, "b": 24},
        xaxis_title="",
        yaxis_title="",
    )
    st.plotly_chart(fig, width="stretch", theme="streamlit")

def flatten_dict(value: Any, prefix: str = "") -> dict[str, Any]:
    """Flatten nested dict-like values for comparison or display."""

    flattened: dict[str, Any] = {}
    if isinstance(value, dict):
        for key, child in value.items():
            next_prefix = f"{prefix}.{key}" if prefix else key
            flattened.update(flatten_dict(child, next_prefix))
        return flattened
    flattened[prefix] = value
    return flattened


def candidate_option_label(candidate: Any) -> str:
    """Build a readable candidate label."""

    identifier = candidate.candidate_id or "UNKNOWN"
    name = candidate.full_name or "Unnamed Candidate"
    return f"{identifier} | {name}"


def candidate_summary_card(title: str, candidate: Any, tone: str = "blue") -> None:
    """Render a compact candidate summary card."""

    overall = candidate.confidence.get("overall") if hasattr(candidate, "confidence") else None
    status = render_status_chip(
        f"Overall {format_value(overall)}" if overall is not None else "Canonical View",
        confidence_tone(overall) if overall is not None else tone,
    )
    tone_class = CARD_TONES.get(tone, CARD_TONES["blue"])
    st.markdown(
        f"""
        <div class="compare-shell {tone_class}">
          <div class="eyebrow">{escape(title)}</div>
          <div class="value" style="font-size:1.35rem;">{escape(candidate.full_name or 'Unnamed Candidate')}</div>
          <div class="support">{status}</div>
          <div class="support" style="margin-top:0.5rem;">
            <strong>ID</strong> {escape(candidate.candidate_id or '-')}<br/>
            <strong>Company</strong> {escape(candidate.current_company or '-')}<br/>
            <strong>Title</strong> {escape(candidate.current_title or '-')}
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def build_compare_rows(source_candidate: Any, merged_candidate: Any, show_extended: bool) -> pd.DataFrame:
    """Build before/after comparison rows."""

    source_flat = flatten_dict(source_candidate.model_dump(mode="json"))
    merged_flat = flatten_dict(merged_candidate.model_dump(mode="json"))
    if show_extended:
        fields = sorted(
            key
            for key in set(source_flat) | set(merged_flat)
            if not key.startswith("raw_record")
            and not key.startswith("confidence")
            and not key.startswith("provenance")
            and not key.startswith("merge_metadata")
        )
    else:
        fields = [field for field in BASE_COMPARE_FIELDS if field in source_flat or field in merged_flat]

    rows = []
    for field in fields:
        source_value = source_flat.get(field)
        merged_value = merged_flat.get(field)
        changed = format_value(source_value) != format_value(merged_value)
        rows.append(
            {
                "field": field,
                "source_value": format_value(source_value),
                "merged_value": format_value(merged_value),
                "status": "Changed" if changed else "Same",
            }
        )
    return pd.DataFrame(rows)


def style_comparison_table(dataframe: pd.DataFrame) -> Any:
    """Apply subtle highlighting to changed values."""

    def style_row(row: pd.Series) -> list[str]:
        if row["status"] == "Changed":
            return ["background-color: var(--secondary-background-color)"] * len(row)
        return [""] * len(row)

    return dataframe.style.apply(style_row, axis=1)


def build_confidence_rows(result: PipelineResult) -> pd.DataFrame:
    """Build a tabular confidence summary across merged candidates."""

    rows = []
    for candidate in result.merged_candidates:
        overall = candidate.confidence.get("overall")
        rows.append(
            {
                "candidate_id": candidate.candidate_id,
                "full_name": candidate.full_name,
                "company": candidate.current_company,
                "overall_confidence": overall,
                "band": "High" if overall is not None and overall >= 0.90 else "Medium" if overall is not None and overall >= 0.70 else "Low",
            }
        )
    return pd.DataFrame(rows)


def missing_field_summary(candidates: list[Any]) -> pd.DataFrame:
    """Summarize missingness across merged candidates."""

    checks = {
        "emails": lambda candidate: not candidate.emails,
        "phones": lambda candidate: not candidate.phones,
        "current_company": lambda candidate: not candidate.current_company,
        "current_title": lambda candidate: not candidate.current_title,
        "skills": lambda candidate: not candidate.skills,
        "location.current": lambda candidate: not candidate.location or not candidate.location.current,
        "linkedin_url": lambda candidate: not candidate.linkedin_url,
        "github_url": lambda candidate: not candidate.github_url,
    }
    rows = []
    for field_name, predicate in checks.items():
        rows.append({"field": field_name, "missing_count": sum(1 for candidate in candidates if predicate(candidate))})
    return pd.DataFrame(rows)

def source_contribution_df(candidates: list[dict[str, Any]]) -> pd.DataFrame:
    """Summarize merged candidate source contribution from projected output."""

    counts: Counter[str] = Counter()
    for candidate in candidates:
        sources = candidate.get("metadata.merged_from_sources") or candidate.get("source") or []
        if isinstance(sources, str):
            sources = [sources]
        for source in sources:
            counts[str(source)] += 1
    return pd.DataFrame([{"source": source.title(), "count": count} for source, count in counts.items()])


def top_values_df(candidates: list[dict[str, Any]], field: str, label: str, limit: int = 10) -> pd.DataFrame:
    """Return top values for scalar or list-valued projected fields."""

    counts: Counter[str] = Counter()
    for candidate in candidates:
        value = candidate.get(field)
        values = value if isinstance(value, list) else [value]
        for item in values:
            if item not in (None, ""):
                counts[str(item)] += 1
    return pd.DataFrame([{label: key, "count": value} for key, value in counts.most_common(limit)])


def validation_summary_df(stats: dict[str, Any]) -> pd.DataFrame:
    """Build valid/invalid profile counts for charting."""

    output_profiles = int(stats.get("output_profiles", 0) or 0)
    validation_errors = int(stats.get("validation_errors", 0) or 0)
    valid_profiles = max(output_profiles - validation_errors, 0)
    return pd.DataFrame(
        [
            {"status": "Valid", "count": valid_profiles},
            {"status": "Invalid", "count": validation_errors},
        ]
    )


def candidate_detail_rows(candidate: dict[str, Any]) -> dict[str, pd.DataFrame]:
    """Build grouped detail tables for a projected candidate row."""

    def as_rows(values: Any, key: str) -> pd.DataFrame:
        if values is None:
            items: list[Any] = []
        elif isinstance(values, list):
            items = values
        else:
            items = [values]
        return pd.DataFrame([{key: format_value(item)} for item in items]) if items else pd.DataFrame([{key: "-"}])

    confidence_rows = [
        {"field": key.replace("confidence.", ""), "confidence": value}
        for key, value in candidate.items()
        if key.startswith("confidence.") and isinstance(value, (int, float))
    ]
    provenance_rows = []
    provenance_prefixes = sorted(
        {
            key.removeprefix("provenance.").rsplit(".", 1)[0]
            for key in candidate
            if key.startswith("provenance.") and key.endswith(".merge_reason")
        }
    )
    for prefix in provenance_prefixes:
        provenance_rows.append(
            {
                "field": prefix,
                "value": format_value(candidate.get(f"provenance.{prefix}.value")),
                "sources": format_value(candidate.get(f"provenance.{prefix}.sources")),
                "reason": format_value(candidate.get(f"provenance.{prefix}.merge_reason")),
                "confidence": candidate.get(f"provenance.{prefix}.confidence"),
            }
        )
    return {
        "Contact": pd.concat([as_rows(candidate.get("emails"), "emails"), as_rows(candidate.get("phones"), "phones")], axis=1),
        "Skills": as_rows(candidate.get("skills"), "skills"),
        "Experience": pd.DataFrame(
            [
                {"field": "years", "value": format_value(candidate.get("experience.years"))},
                {"field": "summary", "value": format_value(candidate.get("experience.summary"))},
                {"field": "entries", "value": format_value(candidate.get("experience.entries"))},
            ]
        ),
        "Education": pd.DataFrame(
            [
                {"field": "degree", "value": format_value(candidate.get("education.highest_degree"))},
                {"field": "university", "value": format_value(candidate.get("education.university"))},
                {"field": "graduation_year", "value": format_value(candidate.get("education.graduation_year"))},
            ]
        ),
        "Confidence": pd.DataFrame(confidence_rows),
        "Provenance": pd.DataFrame(provenance_rows),
    }

def current_page() -> str:
    """Return the active page name."""

    if "page" not in st.session_state:
        st.session_state["page"] = PAGE_ITEMS[0][0]
    return st.session_state["page"]


def navigate(page_name: str) -> None:
    """Set the active page."""

    st.session_state["page"] = page_name


def render_sidebar() -> None:
    """Render the engineering-dashboard sidebar."""

    stats = safe_stat_dict()
    inventory = dataset_inventory()
    output_exists = OUTPUT_PATH.exists()
    validation_errors = stats.get("validation_errors")
    validation_label = "Passed" if stats and validation_errors == 0 else "Not run" if not stats else "Review"
    validation_tone = "green" if validation_label == "Passed" else "slate" if validation_label == "Not run" else "orange"

    with st.sidebar:
        st.markdown(
            f"""
            <div class="sidebar-brand">
              <div class="brand-mark">CDT</div>
              <div style="font-size:1.05rem;font-weight:700;">Candidate Data Transformer</div>
              <div class="support" style="margin-top:0.25rem;">Version 1.0</div>
              <div style="margin-top:0.7rem;">{render_status_chip('Ready', 'green')}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.caption("Navigation")
        for page_name, icon in PAGE_ITEMS:
            button_type = "primary" if current_page() == page_name else "secondary"
            if st.button(page_name, key=f"nav_{page_name}", icon=icon, type=button_type, width="stretch"):
                navigate(page_name)

        st.markdown("---")
        with st.container(border=True):
            st.caption("Current Dataset")
            st.write(f"{sum(inventory.values())} source records/files")
            st.caption("Current Output")
            st.write("merged_candidates.json" if output_exists else "Not generated")
            st.caption("Validation Status")
            st.markdown(render_status_chip(validation_label, validation_tone), unsafe_allow_html=True)
        with st.container(border=True):
            st.caption("Configuration")
            st.write("output_config.json")
            st.caption("Projection")
            st.write(f"{stats.get('output_profiles', 0)} profiles")

def page_home() -> None:
    """Render the home dashboard."""

    stats = safe_stat_dict()
    inventory = dataset_inventory()
    dataset_summary = dataset_summary_payload() or {}
    config = output_config_payload()
    validation_errors = stats.get("validation_errors")
    output_text = read_output_text()

    render_page_header(
        "Candidate Data Transformer",
        "Deterministic multi-source candidate profile transformation engine",
    )

    render_section("Operational Snapshot")
    render_metric_cards(
        [
            {"icon": ":material/input:", "title": "Input Sources", "value": 4, "support": "Recruiter CSV, ATS JSON, LinkedIn text, resume Markdown"},
            {"icon": ":material/database:", "title": "Parsed Records", "value": stats.get("candidates_parsed", 0), "support": "Source records parsed by the pipeline"},
            {"icon": ":material/merge:", "title": "Merged Profiles", "value": stats.get("merged_profiles", 0), "support": "Duplicate groups resolved deterministically"},
            {
                "icon": ":material/fact_check:",
                "title": "Validation",
                "value": "Passed" if stats and validation_errors == 0 else "Awaiting Run" if not stats else "Review",
                "support": f"{stats.get('validation_errors', 0)} validation errors",
            },
        ],
        columns=4,
    )

    render_section("Pipeline Overview", "Large connected stages from source ingestion to projected JSON output.")
    with st.container(border=True):
        render_pipeline_track()
        progress_value = 1.0 if stats else 0.0
        st.progress(progress_value, text="Pipeline operational" if stats else "Ready to execute")

    render_section("System Architecture")
    with st.container(border=True):
        architecture_path = ROOT / "docs" / "OverallArchitecture_diagram.png"
        if architecture_path.exists():
            st.image(str(architecture_path), width="stretch")
        else:
            st.info("Architecture diagram not found.")

    render_section("Quick Actions")
    action_cols = st.columns(4)
    with action_cols[0]:
        if st.button("Run Pipeline", icon=":material/play_circle:", type="primary", width="stretch", key="home_run_pipeline"):
            with st.status("Running deterministic pipeline...", expanded=True) as status:
                st.write("Parsing, normalizing, matching, merging, validating, and projecting records.")
                result = run_pipeline()
                status.update(label=f"Pipeline completed in {result.stats.execution_time_seconds}s", state="complete")
    with action_cols[1]:
        if st.button("Open Viewer", icon=":material/table_view:", width="stretch", key="home_open_viewer"):
            navigate("Merged Candidate Viewer")
    with action_cols[2]:
        if st.button("Validate", icon=":material/fact_check:", width="stretch", key="home_validate"):
            navigate("Data Quality Dashboard")
    with action_cols[3]:
        st.download_button(
            "Download JSON",
            data=output_text or "{}",
            file_name="merged_candidates.json",
            mime="application/json",
            icon=":material/download:",
            width="stretch",
            disabled=output_text is None,
        )

    render_section("Project Information")
    info_tabs = st.tabs(["Sources", "Runtime", "Dataset Notes"])
    with info_tabs[0]:
        render_metric_cards(
            [
                {"icon": ":material/table:", "title": "Recruiter Rows", "value": inventory["recruiter_rows"], "support": "datasets/recruiter.csv"},
                {"icon": ":material/data_object:", "title": "ATS Records", "value": inventory["ats_records"], "support": "datasets/ats.json"},
                {"icon": ":material/article:", "title": "LinkedIn Profiles", "value": inventory["linkedin_profiles"], "support": "datasets/linkedin/*.txt"},
                {"icon": ":material/description:", "title": "Resume Files", "value": inventory["resume_files"], "support": "datasets/resume/*.md"},
            ],
            columns=4,
        )
    with info_tabs[1]:
        render_metric_cards(
            [
                {"icon": ":material/settings:", "title": "Configuration", "value": "output_config.json", "support": f"Flatten={config.get('flatten_nested', True)}"},
                {"icon": ":material/verified:", "title": "Confidence", "value": config.get("include_confidence", True), "support": "Projection toggle"},
                {"icon": ":material/account_tree:", "title": "Provenance", "value": config.get("include_provenance", True), "support": "Projection toggle"},
                {"icon": ":material/science:", "title": "Test Suites", "value": test_suite_count(), "support": "Pytest suites present"},
            ],
            columns=4,
        )
    with info_tabs[2]:
        if dataset_summary:
            render_metric_cards(
                [
                    {"icon": ":material/groups:", "title": "Generated Candidates", "value": dataset_summary.get("number_of_candidates", 0), "support": "Base recruiter records"},
                    {"icon": ":material/merge:", "title": "Duplicate Cases", "value": dataset_summary.get("duplicates", {}).get("count", 0), "support": "Synthetic duplicate records"},
                    {"icon": ":material/alternate_email:", "title": "Invalid Emails", "value": dataset_summary.get("invalid_emails", {}).get("count", 0), "support": "Normalization scenarios"},
                    {"icon": ":material/person_search:", "title": "Incomplete LinkedIn", "value": dataset_summary.get("other_edge_cases", {}).get("incomplete_linkedin_profiles", 0), "support": "Partial text profiles"},
                ],
                columns=4,
            )
        else:
            st.info("No dataset summary found. Generate a dataset to populate notes.")

def page_upload_dataset() -> None:
    """Render the dataset console."""

    render_page_header(
        "Upload Dataset",
        "Local dataset console for generating, validating, and previewing the source files expected by the existing pipeline.",
    )
    render_section("Supported Sources", "The current pipeline reads these local source formats without changing backend behavior.")
    render_metric_cards(
        [
            {"title": "Recruiter CSV", "value": "recruiter.csv", "support": "Structured recruiter export with core candidate fields"},
            {"title": "ATS JSON", "value": "ats.json", "support": "Structured ATS export array with profileLinks and metadata"},
            {"title": "LinkedIn Text", "value": "linkedin/*.txt", "support": "Section-based plain text profiles"},
            {"title": "Resume Markdown", "value": "resume/*.md", "support": "Markdown resumes for sampled candidates"},
        ],
        columns=4,
    )

    left, right = st.columns([1.2, 1.0])
    with left:
        st.markdown('<div class="ui-card">', unsafe_allow_html=True)
        st.markdown("##### Dataset Generation Console")
        st.caption("Preserves the current behavior: this page generates a synthetic local dataset instead of uploading remote files.")
        count = st.number_input("Synthetic candidate count", min_value=1, max_value=10000, value=100, step=10)
        if st.button("Generate Dataset", type="primary", icon=":material/auto_awesome:", width="stretch"):
            generate_dataset(count=int(count), output_dir=DATASET_DIR, seed=42)
            st.success(f"Generated dataset at {DATASET_DIR}")
        st.code("datasets/recruiter.csv\ndatasets/ats.json\ndatasets/linkedin/*.txt\ndatasets/resume/*.md")
        st.markdown("</div>", unsafe_allow_html=True)
    with right:
        summary = dataset_summary_payload()
        st.markdown('<div class="ui-card">', unsafe_allow_html=True)
        st.markdown("##### Current Dataset Summary")
        if summary:
            st.caption(f"Generated at {summary.get('generated_at', '-')}")
            render_metric_cards(
                [
                    {"title": "Candidates", "value": summary.get("number_of_candidates", 0), "support": "Recruiter base records"},
                    {"title": "Duplicates", "value": summary.get("duplicates", {}).get("count", 0), "support": "Duplicate recruiter cases"},
                    {"title": "Missing Emails", "value": summary.get("missing_emails", {}).get("count", 0), "support": "Rows with blank primary_email"},
                    {"title": "Missing Phones", "value": summary.get("missing_phones", {}).get("count", 0), "support": "Rows with blank phone_number"},
                ],
                columns=2,
            )
        else:
            st.info("No dataset summary found. Generate a dataset to populate this console.")
        st.markdown("</div>", unsafe_allow_html=True)

    render_section("Preview Table", "A recruiter.csv sample preview to confirm the generated dataset shape.")
    preview = recruiter_preview()
    if preview.empty:
        st.info("No recruiter.csv preview available yet.")
    else:
        st.markdown('<div class="table-shell">', unsafe_allow_html=True)
        st.dataframe(preview, width="stretch", height=360, hide_index=True)
        st.markdown("</div>", unsafe_allow_html=True)


def stage_result_text(stage_name: str, stats: dict[str, Any]) -> tuple[str, str]:
    """Return record count and result summary for one pipeline stage."""

    if not stats:
        return "Pending", "Run the pipeline to populate this stage."
    if stage_name == "Parse":
        return f"{stats.get('candidates_parsed', 0)} records", "Parsed recruiter CSV, ATS JSON, LinkedIn text, and resumes."
    if stage_name == "Normalize":
        return f"{stats.get('candidates_normalized', 0)} records", "Standardized canonical candidates with reusable normalizers."
    if stage_name == "Block":
        return f"{stats.get('compared_pairs', 0)} pairs", "Generated blocked comparison pairs from deterministic keys."
    if stage_name == "Similarity":
        return f"{stats.get('compared_pairs', 0)} pairs", "Scored blocked pairs with exact and fuzzy identity signals."
    if stage_name == "Merge":
        return f"{stats.get('merged_profiles', 0)} groups", "Merged confirmed components and preserved singleton outputs."
    if stage_name == "Validate":
        return f"{stats.get('output_profiles', 0)} profiles", f"{stats.get('validation_errors', 0)} invalid profiles reported."
    if stage_name == "Project":
        return f"{stats.get('output_profiles', 0)} profiles", "Projected merged candidates using runtime output_config.json."
    return f"{stats.get('output_profiles', 0)} profiles", f"Saved JSON to {OUTPUT_PATH.name}."


def render_stage_flow(stats: dict[str, Any]) -> None:
    """Render the pipeline as a horizontal engineering flow."""

    parts = ["<div class='stage-flow-scroll'><div class='stage-flow'>"]
    for index, (stage_name, description) in enumerate(PIPELINE_STAGES, start=1):
        record_text, result_text = stage_result_text(stage_name, stats)
        if not stats:
            status = "Idle"
            tone = "slate"
            timing = "Awaiting run"
        elif stage_name == "Validate" and stats.get("validation_errors", 0) > 0:
            status = "Review"
            tone = "orange"
            timing = "Captured at run level"
        else:
            status = "Completed"
            tone = "green"
            timing = (
                f"{stats.get('execution_time_seconds', 0)}s total"
                if stage_name == "Output"
                else "Captured at run level"
            )
        parts.append(
            f"""
            <div class="stage-flow-card">
              <div class="stage-index">{index}</div>
              <div>{render_status_chip(status, tone)}</div>
              <div class="stage-name">{escape(stage_name)}</div>
              <div class="stage-body">{escape(description)}</div>
              <div class="meta-label">Records Processed</div>
              <div class="stage-body">{escape(record_text)}</div>
              <div class="meta-label">Execution Result</div>
              <div class="stage-body">{escape(result_text)}</div>
              <div class="meta-label">Execution Time</div>
              <div class="stage-body">{escape(timing)}</div>
            </div>
            """
        )
        if index < len(PIPELINE_STAGES):
            parts.append("<div class='flow-arrow'>&rarr;</div>")
    parts.append("</div></div>")
    st.markdown("".join(parts), unsafe_allow_html=True)


def render_compare_detail_grid(comparison: pd.DataFrame) -> None:
    """Render synchronized source and merged field cards."""

    left_column, right_column = st.columns(2)
    with left_column:
        st.markdown("##### Source Candidate")
        for row in comparison.itertuples(index=False):
            changed_class = " changed" if row.status == "Changed" else ""
            note = "Normalized or merged value differs" if row.status == "Changed" else "No merged change"
            st.markdown(
                f"""
                <div class="compare-field{changed_class}">
                  <div class="field-name">{escape(str(row.field))}</div>
                  <div class="field-value">{escape(str(row.source_value))}</div>
                  <div class="field-note">{escape(note) if row.status == 'Changed' else ''}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
    with right_column:
        st.markdown("##### Merged Candidate")
        for row in comparison.itertuples(index=False):
            changed_class = " changed" if row.status == "Changed" else ""
            note = "Selected canonical value" if row.status == "Changed" else "Same as source"
            st.markdown(
                f"""
                <div class="compare-field{changed_class}">
                  <div class="field-name">{escape(str(row.field))}</div>
                  <div class="field-value">{escape(str(row.merged_value))}</div>
                  <div class="field-note">{escape(note) if row.status == 'Changed' else ''}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def page_pipeline_execution() -> None:
    """Render the pipeline execution dashboard."""

    render_page_header(
        "Pipeline Execution",
        "Operational run console with progress, current stage, execution summary, logs, and generated output.",
    )

    stats = safe_stat_dict()
    progress_value = 1.0 if stats else 0.0
    render_section("Pipeline Progress")
    progress_text = "All stages completed" if stats else "Ready to run"
    st.progress(progress_value, text=progress_text)

    run_col, stage_col = st.columns([1.0, 1.2])
    with run_col:
        with st.container(border=True):
            st.subheader("Run Pipeline")
            st.caption("Executes the existing end-to-end backend pipeline and writes the projected JSON output.")
            if st.button("Run Complete Pipeline", type="primary", icon=":material/play_circle:", width="stretch"):
                with st.status("Running pipeline...", expanded=True) as status:
                    for stage_name, description in PIPELINE_STAGES:
                        st.write(f"{stage_name}: {description}")
                    result = run_pipeline()
                    status.update(label=f"Pipeline completed in {result.stats.execution_time_seconds}s", state="complete")
                st.success("Generated merged_candidates.json")
    with stage_col:
        with st.container(border=True):
            st.subheader("Current Stage")
            if stats:
                st.metric("Stage", "Output", delta="Completed")
                st.caption(f"Projected {stats.get('output_profiles', 0)} profiles to {OUTPUT_PATH.name}")
            else:
                st.metric("Stage", "Idle")
                st.caption("No session run yet. Latest saved output may still be available on other pages.")

    stats = safe_stat_dict()
    render_section("Execution Summary")
    render_metric_cards(
        [
            {"icon": ":material/database:", "title": "Parsed", "value": stats.get("candidates_parsed", 0), "support": "Total source records parsed"},
            {"icon": ":material/hub:", "title": "Compared Pairs", "value": stats.get("compared_pairs", 0), "support": "Blocked identity comparisons"},
            {"icon": ":material/merge:", "title": "Merged Groups", "value": stats.get("merged_profiles", 0), "support": "Confirmed duplicate groups"},
            {"icon": ":material/timer:", "title": "Duration", "value": f"{stats.get('execution_time_seconds', 0)}s" if stats else "-", "support": "Total pipeline execution time"},
        ],
        columns=4,
    )

    render_section("Execution Timeline", "Each stage reflects the existing pipeline instrumentation and run-level timing.")
    render_stage_flow(stats)

    log_col, output_col = st.columns([1.1, 1.0])
    with log_col:
        render_section("Execution Log")
        log_path = ROOT / "logs" / "pipeline.log"
        with st.container(border=True):
            if log_path.exists():
                log_lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()[-80:]
                st.code("\n".join(log_lines) if log_lines else "No log entries yet.", language="text")
            else:
                st.info("No pipeline log file found yet.")
    with output_col:
        render_section("Generated Output")
        with st.container(border=True):
            output_text = read_output_text()
            if output_text:
                st.metric("Output File", OUTPUT_PATH.name)
                st.caption(str(OUTPUT_PATH))
                st.download_button(
                    "Download JSON",
                    data=output_text,
                    file_name="merged_candidates.json",
                    mime="application/json",
                    icon=":material/download:",
                    width="stretch",
                )
                if stats:
                    st.json(stats, expanded=False)
            else:
                st.info("Run the pipeline to generate merged_candidates.json.")

def page_merged_viewer() -> None:
    """Render the merged candidate viewer."""

    render_page_header(
        "Merged Candidate Viewer",
        "Search, filter, page, download, and inspect merged candidate profiles without changing projected output fields.",
    )
    candidates = projected_snapshot()
    if not candidates:
        st.info("Run the pipeline first or load an existing output JSON snapshot.")
        return

    dataframe = as_dataframe(candidates)
    candidate_column = "profile_id" if "profile_id" in dataframe.columns else "candidate_id"
    company_column = "company" if "company" in dataframe.columns else "current_company"
    title_column = "title" if "title" in dataframe.columns else "current_title"
    confidence_column = "confidence.overall" if "confidence.overall" in dataframe.columns else None

    render_section("Statistics")
    average_confidence_all = "-"
    if confidence_column and confidence_column in dataframe.columns and not dataframe.empty:
        average_confidence_all = f"{dataframe[confidence_column].fillna(0).mean():.2f}"
    render_metric_cards(
        [
            {"icon": ":material/badge:", "title": "Profiles", "value": len(dataframe), "support": "Projected candidate rows"},
            {"icon": ":material/business:", "title": "Companies", "value": dataframe[company_column].nunique() if company_column in dataframe else 0, "support": "Distinct current companies"},
            {"icon": ":material/work:", "title": "Titles", "value": dataframe[title_column].nunique() if title_column in dataframe else 0, "support": "Distinct current titles"},
            {"icon": ":material/verified:", "title": "Avg Confidence", "value": average_confidence_all, "support": "Mean overall confidence"},
        ],
        columns=4,
    )

    st.markdown('<div class="filter-shell">', unsafe_allow_html=True)
    filter_cols = st.columns([1.8, 1.1, 1.1, 0.9, 0.7])
    search_text = filter_cols[0].text_input("Search", placeholder="Search across candidate fields")
    company_filter = filter_cols[1].selectbox(
        "Company",
        ["All"] + sorted(str(value) for value in dataframe[company_column].dropna().unique()) if company_column in dataframe else ["All"],
    )
    title_filter = filter_cols[2].selectbox(
        "Title",
        ["All"] + sorted(str(value) for value in dataframe[title_column].dropna().unique()) if title_column in dataframe else ["All"],
    )
    confidence_filter = filter_cols[3].selectbox("Confidence", ["All", "High", "Medium", "Low"])
    rows_per_page = filter_cols[4].selectbox("Rows", [10, 25, 50, 100], index=1)
    st.markdown("</div>", unsafe_allow_html=True)

    filtered = dataframe.copy()
    if search_text:
        lowered = search_text.casefold()
        mask = filtered.astype(str).apply(lambda row: row.str.casefold().str.contains(lowered, na=False)).any(axis=1)
        filtered = filtered[mask]
    if company_filter != "All" and company_column in filtered:
        filtered = filtered[filtered[company_column].astype(str) == company_filter]
    if title_filter != "All" and title_column in filtered:
        filtered = filtered[filtered[title_column].astype(str) == title_filter]
    if confidence_filter != "All" and confidence_column and confidence_column in filtered:
        scores = filtered[confidence_column].fillna(0)
        if confidence_filter == "High":
            filtered = filtered[scores >= 0.90]
        elif confidence_filter == "Medium":
            filtered = filtered[(scores >= 0.70) & (scores < 0.90)]
        else:
            filtered = filtered[scores < 0.70]

    total_rows = len(filtered)
    total_pages = max(1, math.ceil(total_rows / rows_per_page)) if total_rows else 1
    page_number = st.number_input("Page", min_value=1, max_value=total_pages, value=1, step=1)
    start = (page_number - 1) * rows_per_page
    end = start + rows_per_page
    paged = filtered.iloc[start:end]

    average_confidence = "-"
    if confidence_column and confidence_column in filtered.columns and not filtered.empty:
        average_confidence = f"{filtered[confidence_column].fillna(0).mean():.2f}"
    render_metric_cards(
        [
            {"icon": ":material/filter_alt:", "title": "Filtered Profiles", "value": total_rows, "support": "Rows after search and filters"},
            {"icon": ":material/business:", "title": "Visible Companies", "value": filtered[company_column].nunique() if company_column in filtered else 0, "support": "Distinct employers in result set"},
            {"icon": ":material/verified:", "title": "Average Confidence", "value": average_confidence, "support": "Mean confidence for filtered profiles"},
        ],
        columns=3,
    )

    toolbar_left, toolbar_right = st.columns([1.2, 0.8])
    with toolbar_left:
        st.caption(f"Showing {0 if total_rows == 0 else start + 1}-{min(end, total_rows)} of {total_rows} projected profiles.")
    with toolbar_right:
        output_text = read_output_text()
        if output_text:
            st.download_button(
                "Download Merged JSON",
                data=output_text,
                file_name="merged_candidates.json",
                mime="application/json",
                icon=":material/download:",
                width="stretch",
            )

    column_config: dict[str, Any] = {candidate_column: st.column_config.TextColumn("Candidate", width="medium")}
    if company_column in paged.columns:
        column_config[company_column] = st.column_config.TextColumn("Company", width="medium")
    if title_column in paged.columns:
        column_config[title_column] = st.column_config.TextColumn("Title", width="medium")
    if confidence_column and confidence_column in paged.columns:
        column_config[confidence_column] = st.column_config.ProgressColumn("Overall Confidence", min_value=0.0, max_value=1.0, format="%.2f")
    st.markdown('<div class="table-shell">', unsafe_allow_html=True)
    st.dataframe(paged, width="stretch", height=500, hide_index=True, column_config=column_config)
    st.markdown("</div>", unsafe_allow_html=True)

    render_section("Candidate Details", "Expand a candidate to inspect contact data, skills, experience, education, confidence, and provenance.")
    for _, candidate in paged.iterrows():
        row = candidate.to_dict()
        label = f"{format_value(row.get(candidate_column))} | {format_value(row.get('full_name'))} | {format_value(row.get(company_column))}"
        with st.expander(label, expanded=False):
            detail_tabs = st.tabs(["Contact", "Skills", "Experience", "Education", "Confidence", "Provenance"])
            detail_tables = candidate_detail_rows(row)
            for tab, name in zip(detail_tabs, ["Contact", "Skills", "Experience", "Education", "Confidence", "Provenance"]):
                with tab:
                    detail_df = detail_tables[name]
                    config: dict[str, Any] = {}
                    if "confidence" in detail_df.columns:
                        config["confidence"] = st.column_config.ProgressColumn("Confidence", min_value=0.0, max_value=1.0, format="%.2f")
                    st.dataframe(detail_df, width="stretch", hide_index=True, column_config=config)

def page_before_after() -> None:
    """Render before-vs-after candidate comparison."""

    render_page_header(
        "Before vs After Comparison",
        "Side-by-side comparison between a normalized source record and its merged canonical profile with subtle change highlighting.",
    )
    result = get_result()
    if not result:
        st.info("Run the pipeline first to compare normalized source candidates with merged outputs.")
        return

    merged_candidates = result.merged_candidates
    merged_choice = st.selectbox(
        "Merged Candidate",
        merged_candidates,
        format_func=candidate_option_label,
    )
    source_records = merged_choice.raw_record.get("source_records", []) if isinstance(merged_choice.raw_record, dict) else []
    source_ids = [record.get("candidate_id") for record in source_records if record.get("candidate_id")]
    if not source_ids:
        st.info("The selected merged candidate does not have associated source records.")
        return
    source_id = st.selectbox("Source Candidate", source_ids)
    source_candidate = next((candidate for candidate in result.normalized_candidates if candidate.candidate_id == source_id), None)
    if source_candidate is None:
        st.warning("Could not find the selected source candidate in normalized candidates.")
        return

    summary_left, summary_right = st.columns(2)
    with summary_left:
        candidate_summary_card("Normalized Source Candidate", source_candidate, "blue")
    with summary_right:
        candidate_summary_card("Merged Candidate", merged_choice, "green")

    show_extended = st.toggle("Show extended comparison fields", value=False)
    comparison = build_compare_rows(source_candidate, merged_choice, show_extended)
    render_section("Synchronized Comparison", "Side-by-side candidate cards highlight normalized or changed values in subtle green.")
    render_compare_detail_grid(comparison)
    render_section("Field Comparison Table", "Changed values are highlighted to make merged selections and normalized differences easy to inspect.")
    st.dataframe(
        style_comparison_table(comparison),
        width="stretch",
        height=520,
        hide_index=True,
        column_config={
            "field": st.column_config.TextColumn("Field", width="medium"),
            "source_value": st.column_config.TextColumn("Source Candidate", width="large"),
            "merged_value": st.column_config.TextColumn("Merged Candidate", width="large"),
            "status": st.column_config.TextColumn("Status", width="small"),
        },
    )


def page_confidence() -> None:
    """Render the confidence dashboard."""

    render_page_header(
        "Confidence Viewer",
        "Field and profile confidence surfaced as operational review aids without changing the underlying scoring model.",
    )
    result = get_result()
    if not result:
        st.info("Run the pipeline first to inspect field and profile confidence.")
        return

    stats = asdict(result.stats)
    distribution = confidence_distribution_df(stats)
    render_metric_cards(
        [
            {"title": "High", "value": stats.get("confidence_distribution", {}).get("high", 0), "support": "Overall confidence >= 0.90"},
            {"title": "Medium", "value": stats.get("confidence_distribution", {}).get("medium", 0), "support": "Overall confidence >= 0.75 and < 0.90"},
            {"title": "Low", "value": stats.get("confidence_distribution", {}).get("low", 0), "support": "Overall confidence < 0.75"},
            {"title": "Missing", "value": stats.get("confidence_distribution", {}).get("missing", 0), "support": "Profiles without overall confidence"},
        ],
        columns=4,
    )
    st.markdown(
        """
        <div class="band-legend">
          <span class="band-pill">High: 0.90 - 1.00</span>
          <span class="band-pill">Medium: 0.70 - 0.89</span>
          <span class="band-pill">Low: below 0.70</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    chart_col, detail_col = st.columns([1.1, 1.2])
    with chart_col:
        donut_chart(distribution, "bucket", "count", "Confidence Distribution")
    with detail_col:
        confidence_rows = build_confidence_rows(result)
        st.dataframe(
            confidence_rows,
            width="stretch",
            height=300,
            hide_index=True,
            column_config={
                "overall_confidence": st.column_config.ProgressColumn(
                    "Overall Confidence",
                    min_value=0.0,
                    max_value=1.0,
                    format="%.2f",
                )
            },
        )

    selected = st.selectbox("Candidate Detail", result.merged_candidates, format_func=candidate_option_label)
    render_metric_cards(
        [
            {
                "title": "Selected Profile",
                "value": selected.candidate_id or "-",
                "support": selected.full_name or "Unnamed Candidate",
            },
            {
                "title": "Overall Confidence",
                "value": format_value(selected.confidence.get("overall")),
                "support": selected.current_company or "No current company",
            },
            {
                "title": "Scored Fields",
                "value": len(selected.confidence),
                "support": "Field and overall confidence entries on this merged profile",
            },
        ],
        columns=3,
    )
    render_section("Field Confidence Detail", "Progress bars reflect the current field-level scores computed by the merge policy.")
    confidence_items = sorted(selected.confidence.items(), key=lambda item: (-item[1], item[0]))
    for field_name, score in confidence_items:
        tone = confidence_tone(score)
        tone_class = CARD_TONES.get(tone, CARD_TONES["blue"])
        st.markdown(
            f"""
            <div class="provenance-block {tone_class}" style="margin-bottom:0.55rem;">
              <div style="display:flex; justify-content:space-between; gap:1rem;">
                <div><strong>{escape(field_name)}</strong></div>
                <div>{render_status_chip(format_value(score), tone)}</div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.progress(min(max(score, 0.0), 1.0))


def page_provenance() -> None:
    """Render the provenance viewer."""

    render_page_header(
        "Provenance Viewer",
        "Field-level provenance for merged candidates showing selected values, contributing sources, confidence, and merge rationale.",
    )
    result = get_result()
    if not result:
        st.info("Run the pipeline first to inspect provenance.")
        return

    selected = st.selectbox("Candidate", result.merged_candidates, format_func=candidate_option_label)
    candidate_summary_card("Merged Candidate", selected, "blue")
    source_records = []
    if isinstance(selected.raw_record, dict):
        raw_sources = selected.raw_record.get("source_records", [])
        if isinstance(raw_sources, list):
            source_records = raw_sources
    if source_records:
        render_section("Source Records", "Contributing records attached to the merged candidate payload.")
        st.markdown('<div class="table-shell">', unsafe_allow_html=True)
        st.dataframe(pd.DataFrame(source_records), width="stretch", hide_index=True, height=220)
        st.markdown("</div>", unsafe_allow_html=True)
    render_section("Field Provenance", "Each field below is rendered from the current merged candidate provenance payload.")
    for field_name in sorted(selected.provenance):
        record = selected.provenance[field_name]
        score = record.get("confidence")
        tone = confidence_tone(score)
        with st.expander(f"{field_name} | confidence {format_value(score)}", expanded=False):
            left, right = st.columns([1.1, 1.0])
            with left:
                st.markdown(
                    f"""
                    <div class="provenance-block">
                      <div class="eyebrow">Current Value</div>
                      <div class="support">{escape(format_value(record.get('value')))}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                st.markdown(
                    f"""
                    <div class="provenance-block" style="margin-top:0.65rem;">
                      <div class="eyebrow">Merge Reason</div>
                      <div class="support">{escape(str(record.get('merge_reason', '-')))}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            with right:
                st.markdown(
                    f"""
                    <div class="provenance-block">
                      <div class="eyebrow">Sources</div>
                      <div class="support">{escape(format_value(record.get('sources')))}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                st.markdown(
                    f"""
                    <div class="provenance-block" style="margin-top:0.65rem;">
                      <div class="eyebrow">Source Candidate IDs</div>
                      <div class="support">{escape(format_value(record.get('source_candidate_ids')))}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                st.markdown(
                    f"""
                    <div class="provenance-block" style="margin-top:0.65rem;">
                      <div class="eyebrow">Confidence</div>
                      <div class="support">{render_status_chip(format_value(score), tone)}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )


def page_configuration() -> None:
    """Render the configuration viewer."""

    render_page_header(
        "Configuration Viewer",
        "Runtime configuration rendered as an engineering control surface while preserving the existing JSON-driven behavior.",
    )
    output_config = output_config_payload()
    matching_config = load_json_file(CONFIG_DIR / "matching_config.json", {})
    confidence_config = load_json_file(CONFIG_DIR / "confidence_config.json", {})
    company_aliases = load_json_file(CONFIG_DIR / "company_aliases.json", {})
    skill_aliases = load_json_file(CONFIG_DIR / "skill_aliases.json", {})

    render_metric_cards(
        [
            {"title": "Flatten Nested", "value": output_config.get("flatten_nested", True), "support": f"Separator: {output_config.get('flatten_separator', '.')}"},
            {"title": "Include Confidence", "value": output_config.get("include_confidence", True), "support": "Projection toggle from output_config.json"},
            {"title": "Include Provenance", "value": output_config.get("include_provenance", True), "support": "Projection toggle from output_config.json"},
            {"title": "Missing Strategy", "value": output_config.get("missing_value_strategy", "null"), "support": "Runtime handling for missing values"},
        ],
        columns=4,
    )

    tabs = st.tabs(["Projection", "Matching", "Confidence", "Aliases", "Raw JSON"])
    with tabs[0]:
        rename_fields = output_config.get("rename_fields", {})
        render_section("Field Mapping", "Current output field renames applied by the projection engine.")
        if rename_fields:
            st.markdown('<div class="table-shell">', unsafe_allow_html=True)
            st.dataframe(
                pd.DataFrame([{"source_field": key, "projected_field": value} for key, value in rename_fields.items()]),
                width="stretch",
                hide_index=True,
            )
            st.markdown("</div>", unsafe_allow_html=True)
        else:
            st.info("No field renames configured.")
        render_section("Projection Controls")
        render_metric_cards(
            [
                {"title": "Include Fields", "value": len(output_config.get("include_fields", [])), "support": "Explicit allow-list entries"},
                {"title": "Exclude Fields", "value": len(output_config.get("exclude_fields", [])), "support": "Explicit deny-list entries"},
                {"title": "Missing Value", "value": format_value(output_config.get("missing_value")), "support": "Custom replacement when strategy is custom"},
            ],
            columns=3,
        )
    with tabs[1]:
        weights = matching_config.get("similarity_weights", {})
        render_metric_cards(
            [
                {"title": "Match Threshold", "value": matching_config.get("match_threshold", "-"), "support": "Automatic merge threshold"},
                {
                    "title": "Possible Match Threshold",
                    "value": matching_config.get("possible_match_threshold", "-"),
                    "support": "Non-merge review threshold",
                },
            ],
            columns=2,
        )
        st.dataframe(
            pd.DataFrame([{"signal": key, "weight": value} for key, value in weights.items()]),
            width="stretch",
            hide_index=True,
        )
    with tabs[2]:
        source_confidence = confidence_config.get("source_confidence", {})
        st.dataframe(
            pd.DataFrame([{"source": key, "confidence": value} for key, value in source_confidence.items()]),
            width="stretch",
            hide_index=True,
            column_config={
                "confidence": st.column_config.ProgressColumn("Confidence", min_value=0.0, max_value=1.0, format="%.2f")
            },
        )
    with tabs[3]:
        left, right = st.columns(2)
        with left:
            st.markdown("##### Company Aliases")
            st.dataframe(
                pd.DataFrame([{"alias": key, "canonical": value} for key, value in company_aliases.items()]),
                width="stretch",
                hide_index=True,
                height=280,
            )
        with right:
            st.markdown("##### Skill Aliases")
            st.dataframe(
                pd.DataFrame([{"alias": key, "canonical": value} for key, value in skill_aliases.items()]),
                width="stretch",
                hide_index=True,
                height=280,
            )
    with tabs[4]:
        for path in sorted(CONFIG_DIR.glob("*.json")):
            with st.expander(path.name, expanded=path.name == "output_config.json"):
                st.json(load_json_file(path, {}), expanded=False)


def page_statistics() -> None:
    """Render pipeline statistics."""

    render_page_header(
        "Pipeline Statistics",
        "Plotly-based operational charts for source distribution, merge rate, contribution, confidence, validation, companies, and skills.",
    )
    stats = safe_stat_dict()
    if not stats:
        st.info("Run the pipeline first to populate pipeline statistics.")
        return

    candidates = projected_snapshot()
    parsed = stats.get("candidates_parsed", 0)
    merged_groups = stats.get("merged_profiles", 0)
    merge_rate = round((merged_groups / parsed) * 100, 2) if parsed else 0.0
    render_metric_cards(
        [
            {"icon": ":material/database:", "title": "Parsed Records", "value": parsed, "support": "Total source candidates parsed"},
            {"icon": ":material/hub:", "title": "Compared Pairs", "value": stats.get("compared_pairs", 0), "support": "Pairs generated by blocking"},
            {"icon": ":material/output:", "title": "Output Profiles", "value": stats.get("output_profiles", 0), "support": "Projected merged profiles"},
            {"icon": ":material/merge:", "title": "Merge Rate", "value": f"{merge_rate}%", "support": "Merged groups divided by parsed records"},
            {"icon": ":material/error:", "title": "Validation Errors", "value": stats.get("validation_errors", 0), "support": "Invalid merged profiles"},
            {"icon": ":material/timer:", "title": "Execution Time", "value": f"{stats.get('execution_time_seconds', 0)}s", "support": "End-to-end runtime"},
        ],
        columns=3,
    )

    tabs = st.tabs(["Distribution", "Quality", "Companies", "Skills", "Raw Stats"])
    with tabs[0]:
        left, right = st.columns(2)
        with left:
            result = get_result()
            if result:
                donut_chart(source_distribution(result), "source", "count", "Input Distribution")
            else:
                inventory = dataset_inventory()
                inventory_df = pd.DataFrame(
                    [
                        {"source": "Recruiter CSV", "count": inventory["recruiter_rows"]},
                        {"source": "ATS JSON", "count": inventory["ats_records"]},
                        {"source": "LinkedIn", "count": inventory["linkedin_profiles"]},
                        {"source": "Resume", "count": inventory["resume_files"]},
                    ]
                )
                donut_chart(inventory_df, "source", "count", "Input Distribution")
        with right:
            donut_chart(confidence_distribution_df(stats), "bucket", "count", "Confidence Distribution")
        left, right = st.columns(2)
        with left:
            contribution = source_contribution_df(candidates)
            donut_chart(contribution, "source", "count", "Source Contribution")
        with right:
            merge_df = pd.DataFrame(
                [
                    {"metric": "Merged Groups", "count": stats.get("merged_profiles", 0)},
                    {"metric": "Singleton Outputs", "count": max(stats.get("output_profiles", 0) - stats.get("merged_profiles", 0), 0)},
                ]
            )
            bar_chart(merge_df, "metric", "count", "Merge Rate")
    with tabs[1]:
        left, right = st.columns(2)
        with left:
            donut_chart(validation_summary_df(stats), "status", "count", "Validation Summary")
        with right:
            result = get_result()
            if result:
                bar_chart(missing_field_summary(result.merged_candidates), "field", "missing_count", "Missing Field Counts")
            else:
                st.info("Run the pipeline in this session to view object-level missingness.")
    with tabs[2]:
        company_field = "company" if candidates and "company" in candidates[0] else "current_company"
        bar_chart(top_values_df(candidates, company_field, "company"), "company", "count", "Top Companies")
    with tabs[3]:
        bar_chart(top_values_df(candidates, "skills", "skill"), "skill", "count", "Top Skills")
    with tabs[4]:
        st.json(stats, expanded=False)

def page_quality() -> None:
    """Render data quality dashboard."""

    render_page_header(
        "Data Quality Dashboard",
        "Validation health, missing field patterns, duplicate merge metrics, and confidence distribution for the current merged output.",
    )
    result = get_result()
    if not result:
        st.info("Run the pipeline first to inspect data quality metrics.")
        return

    report = result.validation_report
    stats = asdict(result.stats)
    render_metric_cards(
        [
            {"title": "Valid Profiles", "value": report.valid_count if report else 0, "support": "Merged profiles passing validation"},
            {"title": "Invalid Profiles", "value": report.invalid_count if report else 0, "support": "Profiles with schema or semantic issues"},
            {"title": "Duplicate Groups", "value": stats.get("duplicates_found", 0), "support": "Merged groups identified by identity resolution"},
            {"title": "Possible Matches", "value": stats.get("possible_matches", 0), "support": "Pairs retained for manual review"},
        ],
        columns=4,
    )

    left, right = st.columns(2)
    with left:
        bar_chart(missing_field_summary(result.merged_candidates), "field", "missing_count", "Missing Field Counts")
    with right:
        donut_chart(confidence_distribution_df(stats), "bucket", "count", "Confidence Distribution")

    render_section("Validation Details", "Validation remains non-fatal: invalid profiles are reported without stopping the pipeline.")
    if report and report.errors:
        st.markdown('<div class="table-shell">', unsafe_allow_html=True)
        st.dataframe(
            pd.DataFrame([asdict(error) for error in report.errors]),
            width="stretch",
            height=320,
            hide_index=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.success("No validation errors in the latest run.")


PAGES = {
    "Home": page_home,
    "Upload Dataset": page_upload_dataset,
    "Pipeline Execution": page_pipeline_execution,
    "Merged Candidate Viewer": page_merged_viewer,
    "Before vs After Comparison": page_before_after,
    "Confidence Viewer": page_confidence,
    "Provenance Viewer": page_provenance,
    "Configuration Viewer": page_configuration,
    "Pipeline Statistics": page_statistics,
    "Data Quality Dashboard": page_quality,
}

render_sidebar()
PAGES[current_page()]()

















