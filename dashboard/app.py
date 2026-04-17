import json
import re
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from html import escape


import altair as alt
import pandas as pd
import streamlit as st
import base64

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from auth.auth import authenticate
from data.csv_loader import load_csv_data
from data.ingestion import MACHINE_PROFILES, get_live_snapshot
from data.preprocessing import FEATURE_COLUMNS, preprocess
from database.db import init_db, load_alerts, save_alert, save_data
from models.isolation_forest import AnomalyModel

st.markdown("""
<style>
button[kind="header"] {display: none;}
</style>
""", unsafe_allow_html=True)


st.set_page_config(page_title="AI Predictive Maintenance", layout="wide")

MACHINE_IDS = list(MACHINE_PROFILES)
BUFFER_SIZE = 60
TREND_WINDOW = 5
STALE_AFTER_SECONDS = 3
ALERT_STREAK_THRESHOLD = 2
SENSOR_LABELS = {
    "temperature_C": "Temperature",
    "vibration_mm_s": "Vibration",
    "rpm": "RPM",
    "current_A": "Current",
}
SENSOR_UNITS = {
    "temperature_C": "C",
    "vibration_mm_s": "mm/s",
    "rpm": "rpm",
    "current_A": "A",
}
SENSOR_THRESHOLDS = {
    "temperature_C": {"warning_high": 85.0, "critical_high": 95.0},
    "vibration_mm_s": {"warning_high": 2.0, "critical_high": 3.0},
    "current_A": {"warning_high": 16.0, "critical_high": 18.0},
    "rpm": {
        "warning_high": 1600.0,
        "critical_high": 1700.0,
        "warning_low": 1350.0,
        "critical_low": 1250.0,
    },
}
SENSOR_TREND_THRESHOLDS = {
    "temperature_C": 3.0,
    "vibration_mm_s": 0.25,
    "current_A": 1.0,
    "rpm": 60.0,
}


def utc_now():
    return datetime.now(timezone.utc)


def local_now():
    return datetime.now().astimezone()


def sync_theme_mode():
    st.session_state.theme_mode = "dark" if st.session_state.get("theme_toggle", True) else "light"


def get_theme_palette():
    use_dark_theme = st.session_state.get("theme_mode", "dark") == "dark"
    return {
        "bg_top": "#050916" if use_dark_theme else "#f4f6fb",
        "bg_bottom": "#102042" if use_dark_theme else "#edf1fa",
        "surface": "rgba(15, 19, 30, 0.82)" if use_dark_theme else "rgba(255, 255, 255, 0.92)",
        "surface_strong": "rgba(18, 23, 36, 0.95)" if use_dark_theme else "rgba(255, 255, 255, 0.98)",
        "surface_soft": "rgba(11, 16, 26, 0.72)" if use_dark_theme else "rgba(246, 248, 252, 0.92)",
        "border": "rgba(128, 150, 255, 0.18)" if use_dark_theme else "rgba(30, 64, 175, 0.10)",
        "border_soft": "rgba(128, 150, 255, 0.10)" if use_dark_theme else "rgba(15, 23, 42, 0.06)",
        "sidebar_bg": "linear-gradient(180deg, rgba(8, 10, 18, 0.98) 0%, rgba(14, 23, 46, 0.98) 100%)" if use_dark_theme else "linear-gradient(180deg, rgba(255, 255, 255, 0.98) 0%, rgba(242, 246, 252, 0.98) 100%)",
        "sidebar_border": "rgba(128, 150, 255, 0.12)" if use_dark_theme else "rgba(15, 23, 42, 0.08)",
        "ink": "#f5f7fb" if use_dark_theme else "#132437",
        "muted": "#97a6c5" if use_dark_theme else "#64748b",
        "accent": "#8ca2ff" if use_dark_theme else "#4458ea",
        "accent_secondary": "#66dbff" if use_dark_theme else "#0f766e",
        "watch": "#f4c152" if use_dark_theme else "#b7791f",
        "danger": "#ff8c7b" if use_dark_theme else "#b54708",
        "success": "#4fdb96" if use_dark_theme else "#1d6f42",
        "shadow": "0 28px 80px rgba(2, 6, 23, 0.45)" if use_dark_theme else "0 22px 46px rgba(15, 23, 42, 0.10)",
        "glow_a": "rgba(92, 110, 255, 0.22)" if use_dark_theme else "rgba(67, 97, 238, 0.12)",
        "glow_b": "rgba(34, 211, 238, 0.16)" if use_dark_theme else "rgba(15, 118, 110, 0.08)",
        "button_bg": "linear-gradient(135deg, rgba(124, 140, 255, 0.96) 0%, rgba(98, 218, 255, 0.92) 100%)" if use_dark_theme else "linear-gradient(135deg, rgba(68, 88, 234, 0.96) 0%, rgba(15, 118, 110, 0.92) 100%)",
        "button_text": "#f8fbff" if use_dark_theme else "#ffffff",
        "input_bg": "rgba(8, 13, 24, 0.92)" if use_dark_theme else "rgba(250, 251, 255, 0.98)",
        "observed_line": "#90a4ff" if use_dark_theme else "#4058ea",
        "forecast_line": "#f7c96a" if use_dark_theme else "#d97706",
        "warning_line": "#f4c152" if use_dark_theme else "#c97a1a",
        "critical_line": "#ff8c7b" if use_dark_theme else "#b54708",
    }


def parse_timestamp(value):
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def inject_styles():
    palette = get_theme_palette()
    st.markdown(
        f"""
        <style>
        :root {{
            --bg-top: {palette["bg_top"]};
            --bg-bottom: {palette["bg_bottom"]};
            --surface: {palette["surface"]};
            --surface-strong: {palette["surface_strong"]};
            --surface-soft: {palette["surface_soft"]};
            --border: {palette["border"]};
            --border-soft: {palette["border_soft"]};
            --ink: {palette["ink"]};
            --muted: {palette["muted"]};
            --accent: {palette["accent"]};
            --accent-secondary: {palette["accent_secondary"]};
            --watch: {palette["watch"]};
            --danger: {palette["danger"]};
            --success: {palette["success"]};
            --shadow: {palette["shadow"]};
            --input-bg: {palette["input_bg"]};
            --button-bg: {palette["button_bg"]};
            --button-text: {palette["button_text"]};
        }}

        .stApp {{
            background:
                radial-gradient(circle at top left, {palette["glow_a"]}, transparent 30%),
                radial-gradient(circle at top right, {palette["glow_b"]}, transparent 24%),
                linear-gradient(180deg, var(--bg-top) 0%, var(--bg-bottom) 100%);
            color: var(--ink);
        }}

        [data-testid="stAppViewContainer"] {{
            background: transparent;
        }}

        header[data-testid="stHeader"] {{
            background: transparent;
        }}

        html, body, [class*="css"] {{
            font-family: "Trebuchet MS", "Segoe UI", sans-serif;
        }}

        .block-container {{
            max-width: 1380px;
            padding-top: 1.25rem;
            padding-bottom: 2.2rem;
        }}

        h1, h2, h3, .hero-title, .shell-title, .login-title {{
            font-family: Georgia, "Times New Roman", serif;
            letter-spacing: 0.02em;
        }}

        div[data-testid="stMetric"] {{
            background: linear-gradient(180deg, var(--surface-strong) 0%, var(--surface) 100%);
            border: 1px solid var(--border);
            border-radius: 20px;
            padding: 0.95rem 1rem;
            box-shadow: var(--shadow);
        }}

        div[data-testid="stMetricLabel"] {{
            color: var(--muted);
            font-weight: 700;
            letter-spacing: 0.08em;
            text-transform: uppercase;
        }}

        div[data-testid="stMetricValue"] {{
            color: var(--ink);
        }}

        div[data-testid="stSidebar"] {{
            background: {palette["sidebar_bg"]};
            border-right: 1px solid {palette["sidebar_border"]};
        }}

        div[data-testid="stSidebar"] > div:first-child {{
            background: transparent;
        }}

        div[data-testid="stSidebar"] * {{
            color: var(--ink);
        }}

        .hero-card,
        .topbar-card,
        .clock-card,
        .sidebar-brand,
        .login-copy-card,
        .summary-card,
        .machine-card,
        .reason-card {{
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 24px;
            box-shadow: var(--shadow);
            backdrop-filter: blur(18px);
        }}

        .topbar-card {{
            padding: 1.35rem 1.5rem;
            margin-bottom: 1rem;
            background:
                radial-gradient(circle at top right, {palette["glow_b"]}, transparent 24%),
                linear-gradient(135deg, var(--surface-strong) 0%, var(--surface) 100%);
        }}

        .shell-chip,
        .hero-kicker,
        .summary-eyebrow,
        .clock-label,
        .sidebar-brand-kicker,
        .login-kicker {{
            color: var(--muted);
            font-size: 0.76rem;
            font-weight: 700;
            letter-spacing: 0.18em;
            text-transform: uppercase;
        }}

        .shell-title {{
            color: var(--ink);
            font-size: 2.15rem;
            font-weight: 700;
            margin: 0.45rem 0 0.35rem;
        }}

        .shell-subtitle {{
            color: var(--muted);
            line-height: 1.65;
            max-width: 58rem;
        }}

        .clock-card {{
            padding: 1.15rem 1.2rem;
            min-height: 172px;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            background:
                radial-gradient(circle at top left, {palette["glow_a"]}, transparent 22%),
                linear-gradient(180deg, var(--surface-strong) 0%, var(--surface-soft) 100%);
        }}

        .clock-time {{
            color: var(--ink);
            font-family: Georgia, "Times New Roman", serif;
            font-size: 2rem;
            font-weight: 700;
            margin-top: 0.45rem;
        }}

        .clock-date {{
            color: var(--muted);
            line-height: 1.55;
        }}

        .clock-status {{
            display: inline-flex;
            align-items: center;
            gap: 0.45rem;
            width: fit-content;
            border-radius: 999px;
            padding: 0.35rem 0.75rem;
            font-size: 0.78rem;
            font-weight: 700;
            color: var(--ink);
            background: var(--border-soft);
            border: 1px solid var(--border);
        }}

        .sidebar-brand {{
            padding: 1.15rem 1.15rem 1rem;
            margin-bottom: 1rem;
            background:
                radial-gradient(circle at top right, {palette["glow_a"]}, transparent 26%),
                linear-gradient(180deg, var(--surface-strong) 0%, var(--surface) 100%);
        }}

        .sidebar-brand-title {{
            color: var(--ink);
            font-size: 1.45rem;
            font-family: Georgia, "Times New Roman", serif;
            font-weight: 700;
            margin: 0.35rem 0;
        }}

        .sidebar-brand-copy {{
            color: var(--muted);
            line-height: 1.55;
            margin-bottom: 0;
        }}

        .hero-card {{
            padding: 1.55rem 1.7rem;
            background:
                radial-gradient(circle at top right, {palette["glow_b"]}, transparent 28%),
                linear-gradient(135deg, rgba(18, 24, 39, 0.95) 0%, rgba(17, 44, 88, 0.92) 55%, rgba(17, 72, 110, 0.92) 100%);
            color: #f8fbfc;
            margin-bottom: 1rem;
        }}

        .hero-kicker {{
            opacity: 0.86;
            margin-bottom: 0.45rem;
        }}

        .hero-title {{
            font-size: 2.2rem;
            font-weight: 700;
            margin-bottom: 0.45rem;
        }}

        .hero-copy {{
            font-size: 1rem;
            max-width: 62rem;
            opacity: 0.92;
            line-height: 1.6;
        }}

        .summary-card {{
            padding: 1.2rem 1.3rem;
            margin-bottom: 1rem;
        }}

        .summary-title {{
            font-size: 1.35rem;
            font-weight: 700;
            color: var(--ink);
            margin-bottom: 0.35rem;
        }}

        .summary-copy {{
            color: var(--muted);
            line-height: 1.55;
        }}

        .machine-card {{
            padding: 1.15rem 1.2rem;
            margin-bottom: 1rem;
        }}

        .machine-card.normal {{
            border-left: 6px solid var(--success);
        }}

        .machine-card.watch {{
            border-left: 6px solid var(--watch);
        }}

        .machine-card.warning {{
            border-left: 6px solid var(--watch);
        }}

        .machine-card.critical {{
            border-left: 6px solid var(--danger);
        }}

        .machine-top {{
            display: flex;
            justify-content: space-between;
            gap: 1rem;
            align-items: flex-start;
            margin-bottom: 0.8rem;
        }}

        .machine-id {{
            font-size: 1.15rem;
            font-weight: 700;
            color: var(--ink);
        }}

        .machine-meta {{
            color: var(--muted);
            margin-top: 0.2rem;
            line-height: 1.5;
        }}

        .risk-pill {{
            padding: 0.35rem 0.7rem;
            border-radius: 999px;
            font-weight: 700;
            font-size: 0.9rem;
            white-space: nowrap;
        }}

        .risk-pill.normal {{
            color: var(--success);
            background: rgba(29, 111, 66, 0.14);
        }}

        .risk-pill.watch {{
            color: var(--watch);
            background: rgba(183, 121, 31, 0.15);
        }}

        .risk-pill.warning {{
            color: var(--watch);
            background: rgba(217, 119, 6, 0.15);
        }}

        .risk-pill.critical {{
            color: var(--danger);
            background: rgba(181, 71, 8, 0.15);
        }}

        .machine-grid {{
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 0.7rem 1rem;
            margin-bottom: 0.8rem;
        }}

        .machine-stat-label {{
            color: var(--muted);
            font-size: 0.78rem;
            text-transform: uppercase;
            letter-spacing: 0.1em;
            font-weight: 700;
            margin-bottom: 0.15rem;
        }}

        .machine-stat-value {{
            color: var(--ink);
            font-size: 1rem;
            font-weight: 700;
        }}

        .machine-copy {{
            color: var(--muted);
            line-height: 1.55;
            margin-bottom: 0.75rem;
        }}

        .machine-reasons {{
            margin: 0;
            padding-left: 1.1rem;
            color: var(--muted);
            line-height: 1.5;
        }}

        .reason-card {{
            padding: 1rem 1.1rem;
            margin-bottom: 1rem;
        }}

        .reason-title {{
            color: var(--ink);
            font-size: 1.02rem;
            font-weight: 700;
            margin-bottom: 0.65rem;
        }}

        .reason-empty {{
            color: var(--muted);
            line-height: 1.5;
        }}

        .login-copy-card {{
            padding: 1.55rem 1.65rem;
            margin-bottom: 1rem;
            text-align: center;
            background:
                radial-gradient(circle at top center, {palette["glow_a"]}, transparent 24%),
                linear-gradient(180deg, var(--surface-strong) 0%, rgba(14, 18, 28, 0.96) 100%);
        }}

        .login-shell-card {{
            padding: 1.45rem 1.55rem;
            margin-bottom: 1rem;
        }}

        .login-title {{
            color: var(--ink);
            font-size: 3rem;
            font-weight: 700;
            margin: 0.45rem 0 0.55rem;
        }}

        .login-copy {{
            color: var(--muted);
            font-size: 1rem;
            line-height: 1.65;
            max-width: 34rem;
            margin: 0 auto;
        }}

        .login-footnote,
        .auth-note {{
            color: var(--muted);
            text-align: center;
            line-height: 1.55;
        }}

        .auth-note {{
            margin-top: 0.9rem;
        }}

        div[data-testid="stDataFrame"] {{
            background: var(--surface-strong);
            border: 1px solid var(--border);
            border-radius: 18px;
            overflow: hidden;
        }}

        div[data-testid="stForm"] {{
            background: var(--surface-strong);
            border: 1px solid var(--border);
            border-radius: 22px;
            padding: 1.25rem 1.35rem;
            box-shadow: var(--shadow);
        }}

        div[data-testid="stForm"] label,
        .stSelectbox label,
        .stMultiSelect label,
        .stSlider label,
        .stTextInput label,
        .stTextArea label,
        .stFileUploader label,
        .stRadio label,
        .stToggle label {{
            color: var(--ink) !important;
            font-weight: 600;
        }}

        div[data-baseweb="input"] > div,
        div[data-baseweb="select"] > div,
        .stTextArea textarea,
        .stDateInput input,
        .stTimeInput input {{
            background: var(--input-bg) !important;
            border: 1px solid var(--border) !important;
            color: var(--ink) !important;
            border-radius: 16px !important;
        }}

        .stTextArea textarea::placeholder,
        input::placeholder {{
            color: var(--muted) !important;
            opacity: 0.9;
        }}

        div[data-baseweb="tag"] {{
            background: var(--border-soft) !important;
            border-radius: 999px !important;
            color: var(--ink) !important;
        }}

        .stButton > button,
        .stDownloadButton > button,
        div[data-testid="stFormSubmitButton"] button {{
            width: 100%;
            border: none;
            border-radius: 18px;
            background: var(--button-bg);
            color: var(--button-text);
            font-weight: 700;
            box-shadow: var(--shadow);
            min-height: 3rem;
        }}

        .stButton > button:hover,
        .stDownloadButton > button:hover,
        div[data-testid="stFormSubmitButton"] button:hover {{
            filter: brightness(1.04);
        }}

        div[data-testid="stToggle"] {{
            background: var(--surface-strong);
            border: 1px solid var(--border);
            border-radius: 20px;
            padding: 0.95rem 1rem 0.8rem;
            box-shadow: var(--shadow);
            margin-bottom: 1rem;
        }}

        div[data-testid="stToggle"] p {{
            color: var(--ink);
            font-weight: 700;
            margin-bottom: 0.25rem;
        }}

        div[data-testid="stFileUploader"] section {{
            background: var(--surface-strong);
            border: 1px dashed var(--border);
            border-radius: 18px;
        }}

        div[data-testid="stAlert"] {{
            border-radius: 18px;
            border: 1px solid var(--border-soft);
        }}

        .stTabs [data-baseweb="tab-list"] {{
            gap: 0.45rem;
        }}

        .stTabs [data-baseweb="tab"] {{
            border-radius: 999px;
            background: var(--surface-soft);
            color: var(--muted);
            border: 1px solid var(--border-soft);
        }}

        .stTabs [aria-selected="true"] {{
            background: var(--surface-strong);
            color: var(--ink);
            border-color: var(--border);
        }}

        @media (max-width: 960px) {{
            .shell-title,
            .hero-title,
            .login-title {{
                font-size: 1.85rem;
            }}

            .clock-time {{
                font-size: 1.45rem;
            }}
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


@st.cache_data(show_spinner=False)
def load_historical_frame(path):
    historical = pd.DataFrame(load_csv_data(path))
    rename_map = {
        "temp_1": "temperature_C",
        "vibration_1": "vibration_mm_s",
        "rpm_1": "rpm",
        "current_1": "current_A",
    }
    historical = historical.rename(columns=rename_map)

    if "machine_id" not in historical.columns:
        historical["machine_id"] = MACHINE_IDS[0]

    for column in FEATURE_COLUMNS:
        if column not in historical.columns:
            historical[column] = 0.0
        historical[column] = pd.to_numeric(historical[column], errors="coerce").fillna(0.0)

    return historical


@st.cache_data(show_spinner=False)
def build_baselines(path):
    historical = load_historical_frame(path)
    global_std = {
        "temperature_C": max(float(historical["temperature_C"].std(ddof=0) or 0.0), 3.0),
        "vibration_mm_s": max(float(historical["vibration_mm_s"].std(ddof=0) or 0.0), 0.25),
        "rpm": max(float(historical["rpm"].std(ddof=0) or 0.0), 70.0),
        "current_A": max(float(historical["current_A"].std(ddof=0) or 0.0), 0.8),
    }
    baselines = {}

    for machine_id in MACHINE_IDS:
        machine_df = historical[historical["machine_id"] == machine_id]
        profile = MACHINE_PROFILES[machine_id]
        baselines[machine_id] = {}

        for column in FEATURE_COLUMNS:
            if machine_df.empty:
                mean_value = float(profile[column])
                std_value = global_std[column]
            else:
                mean_value = float(machine_df[column].mean())
                std_value = max(float(machine_df[column].std(ddof=0) or 0.0), global_std[column] * 0.45)

            baselines[machine_id][column] = {
                "mean": mean_value,
                "std": std_value,
            }

    return baselines


@st.cache_resource(show_spinner=False)
def load_model(path):
    historical = load_historical_frame(path)
    model = AnomalyModel()
    model.train(historical.to_dict(orient="records"))
    return model


@st.cache_data(show_spinner=False)
def load_recorded_sensor_frame(path, modified_at):
    del modified_at

    if not os.path.exists(path):
        return pd.DataFrame(columns=["machine_id", "timestamp", "status"])

    with open(path, "r", encoding="utf-8") as file:
        raw_records = extract_records_from_payload(json.load(file))

    return normalize_sensor_records(raw_records)


def extract_records_from_payload(payload):
    if isinstance(payload, list):
        return payload

    if isinstance(payload, dict):
        for key in ("records", "data", "history", "sensor_data", "items"):
            candidate = payload.get(key)
            if isinstance(candidate, list):
                return candidate

        nested_lists = [value for value in payload.values() if isinstance(value, list)]
        if len(nested_lists) == 1:
            return nested_lists[0]

        return [payload]

    raise ValueError("JSON data must be a list of records or an object containing a record list.")


def normalize_sensor_records(raw_records):
    if not isinstance(raw_records, list):
        raise ValueError("Sensor data must be a list of JSON records.")

    rows = []
    for entry in raw_records:
        if not isinstance(entry, dict):
            continue

        normalized = preprocess(entry)
        row = {
            "machine_id": entry.get("machine_id", "Unknown"),
            "timestamp": entry.get("timestamp") or normalized.get("timestamp"),
            "status": entry.get("status") or normalized.get("status", "unknown"),
        }

        for key, value in normalized.items():
            if key in {"timestamp", "status"}:
                continue
            row[key] = value

        rows.append(row)

    frame = pd.DataFrame(rows)
    if frame.empty:
        return pd.DataFrame(columns=["machine_id", "timestamp", "status"])

    frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=True, errors="coerce").dt.tz_convert(None)
    frame = frame.dropna(subset=["timestamp"]).sort_values("timestamp").reset_index(drop=True)

    sensor_columns = [
        column
        for column in frame.columns
        if column not in {"machine_id", "timestamp", "status"}
    ]
    for column in sensor_columns:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")

    return frame


@st.cache_data(show_spinner=False)
def load_external_sensor_frame(json_text):
    if not json_text or not json_text.strip():
        raise ValueError("Please provide JSON data to analyze.")

    try:
        payload = json.loads(json_text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON: {exc.msg} at line {exc.lineno}, column {exc.colno}.") from exc

    raw_records = extract_records_from_payload(payload)
    return normalize_sensor_records(raw_records)


def sensor_label(sensor_name):
    return SENSOR_LABELS.get(sensor_name, sensor_name.replace("_", " ").title())


def sensor_unit(sensor_name):
    return SENSOR_UNITS.get(sensor_name, "")


def sensor_status(sensor_name, value):
    thresholds = SENSOR_THRESHOLDS.get(sensor_name)
    if thresholds is None or pd.isna(value):
        return "Normal", "normal"

    if (
        ("critical_high" in thresholds and value >= thresholds["critical_high"])
        or ("critical_low" in thresholds and value <= thresholds["critical_low"])
    ):
        return "Critical", "critical"

    if (
        ("warning_high" in thresholds and value >= thresholds["warning_high"])
        or ("warning_low" in thresholds and value <= thresholds["warning_low"])
    ):
        return "Warning", "warning"

    return "Normal", "normal"


def sensor_trend_threshold(sensor_name, series):
    base_threshold = SENSOR_TREND_THRESHOLDS.get(sensor_name)
    if base_threshold is not None:
        return base_threshold

    variation = float(series.std(ddof=0) or 0.0)
    return max(variation * 0.9, 0.5)


def detect_sensor_trend(df, sensor_name, window=TREND_WINDOW):
    if sensor_name not in df.columns:
        return "collecting", None, None

    series = pd.to_numeric(df[sensor_name], errors="coerce").dropna()
    if len(series) < max(2, window):
        return "collecting", None, None

    recent = series.tail(window)
    change = float(recent.iloc[-1] - recent.iloc[0])
    slope = change / max(len(recent) - 1, 1)
    threshold = sensor_trend_threshold(sensor_name, recent)

    if change > threshold:
        trend = "increasing"
    elif change < -threshold:
        trend = "decreasing"
    else:
        trend = "stable"

    return trend, change, slope


def infer_sample_interval(df):
    if "timestamp" not in df.columns or len(df) < 2:
        return timedelta(seconds=1)

    intervals = df["timestamp"].sort_values().diff().dropna()
    if intervals.empty:
        return timedelta(seconds=1)

    median_interval = intervals.median()
    if pd.isna(median_interval) or median_interval <= pd.Timedelta(0):
        return timedelta(seconds=1)

    return median_interval.to_pytimedelta()


def predict_sensor_values(df, sensor_name, horizon):
    if sensor_name not in df.columns or df.empty:
        return pd.DataFrame(columns=["timestamp", "value"]), "Not enough data"

    sensor_df = df[["timestamp", sensor_name]].dropna().copy()
    if len(sensor_df) < 2:
        return pd.DataFrame(columns=["timestamp", "value"]), "Not enough data"

    trend, change, slope = detect_sensor_trend(sensor_df, sensor_name)
    if slope is None:
        return pd.DataFrame(columns=["timestamp", "value"]), "Not enough data"

    latest_timestamp = sensor_df["timestamp"].iloc[-1]
    latest_value = float(sensor_df[sensor_name].iloc[-1])
    interval = infer_sample_interval(sensor_df)

    future_rows = []
    for step in range(1, horizon + 1):
        future_rows.append(
            {
                "timestamp": latest_timestamp + interval * step,
                "value": latest_value + slope * step,
            }
        )

    prediction_df = pd.DataFrame(future_rows)
    final_value = float(prediction_df["value"].iloc[-1])
    direction = "increase" if slope > 0 else "decrease" if slope < 0 else "remain steady"
    unit = sensor_unit(sensor_name)
    unit_suffix = f" {unit}" if unit else ""

    if direction == "remain steady":
        message = f"{sensor_label(sensor_name)} likely to remain around {final_value:.2f}{unit_suffix}."
    else:
        message = f"{sensor_label(sensor_name)} likely to {direction} to {final_value:.2f}{unit_suffix}."

    return prediction_df, message


def build_sensor_chart(filtered_df, sensor_name, prediction_df):
    palette = get_theme_palette()
    actual_df = filtered_df[["timestamp", sensor_name]].dropna().copy()
    actual_df["series"] = "Observed"
    actual_df["severity"] = actual_df[sensor_name].apply(lambda value: sensor_status(sensor_name, value)[1])
    unit = sensor_unit(sensor_name)
    axis_title = sensor_label(sensor_name) if not unit else f"{sensor_label(sensor_name)} ({unit})"

    base = alt.Chart(actual_df).encode(x=alt.X("timestamp:T", title="Timestamp"))
    actual_line = base.mark_line(color=palette["observed_line"], strokeWidth=2.5).encode(
        y=alt.Y(f"{sensor_name}:Q", title=axis_title),
        tooltip=[
            alt.Tooltip("timestamp:T", title="Timestamp"),
            alt.Tooltip(f"{sensor_name}:Q", title=sensor_label(sensor_name), format=".2f"),
        ],
    )

    anomaly_points = (
        base.transform_filter(alt.datum.severity != "normal")
        .mark_circle(size=80)
        .encode(
            y=alt.Y(f"{sensor_name}:Q"),
            color=alt.Color(
                "severity:N",
                scale=alt.Scale(
                    domain=["warning", "critical"],
                    range=[palette["warning_line"], palette["critical_line"]],
                ),
                legend=alt.Legend(title="Anomaly"),
            ),
            tooltip=[
                alt.Tooltip("timestamp:T", title="Timestamp"),
                alt.Tooltip(f"{sensor_name}:Q", title=sensor_label(sensor_name), format=".2f"),
                alt.Tooltip("severity:N", title="Status"),
            ],
        )
    )

    layers = [actual_line, anomaly_points]

    if not prediction_df.empty:
        future_df = prediction_df.copy()
        future_df["series"] = "Forecast"
        forecast_line = alt.Chart(future_df).mark_line(
            color=palette["forecast_line"],
            strokeDash=[6, 4],
            strokeWidth=2,
        ).encode(
            x=alt.X("timestamp:T"),
            y=alt.Y("value:Q"),
            tooltip=[
                alt.Tooltip("timestamp:T", title="Forecast time"),
                alt.Tooltip("value:Q", title="Forecast", format=".2f"),
            ],
        )
        forecast_points = alt.Chart(future_df).mark_circle(color=palette["forecast_line"], size=50).encode(
            x=alt.X("timestamp:T"),
            y=alt.Y("value:Q"),
        )
        layers.extend([forecast_line, forecast_points])

    return (
        alt.layer(*layers)
        .properties(height=260)
        .configure_view(strokeOpacity=0)
        .configure_axis(
            domainColor=palette["border"],
            gridColor=palette["border_soft"],
            labelColor=palette["muted"],
            titleColor=palette["ink"],
            tickColor=palette["border"],
        )
        .configure_legend(
            titleColor=palette["ink"],
            labelColor=palette["muted"],
            orient="bottom",
        )
        .interactive()
    )


def build_day_comparison(filtered_df, sensor_names):
    if filtered_df.empty:
        return pd.DataFrame(), "No data available for day comparison."

    by_day = (
        filtered_df.assign(day=filtered_df["timestamp"].dt.date)
        .groupby("day")[sensor_names]
        .mean(numeric_only=True)
        .sort_index()
    )

    if len(by_day) < 2:
        return pd.DataFrame(), "At least two days of data are needed for day-to-day comparison."

    latest_day = by_day.index[-1]
    previous_day = by_day.index[-2]
    latest_values = by_day.loc[latest_day]
    previous_values = by_day.loc[previous_day]

    rows = []
    for sensor_name in sensor_names:
        latest_value = float(latest_values.get(sensor_name, float("nan")))
        previous_value = float(previous_values.get(sensor_name, float("nan")))
        delta_value = latest_value - previous_value
        rows.append(
            {
                "Sensor": sensor_label(sensor_name),
                f"{previous_day} Avg": round(previous_value, 2),
                f"{latest_day} Avg": round(latest_value, 2),
                "Delta": round(delta_value, 2),
                "Direction": "Up" if delta_value > 0 else "Down" if delta_value < 0 else "Flat",
            }
        )

    summary = f"Comparing average sensor values on {latest_day} versus {previous_day}."
    return pd.DataFrame(rows), summary


def init_session_state():
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
    if "theme_mode" not in st.session_state:
        st.session_state.theme_mode = "dark"
    if "theme_toggle" not in st.session_state:
        st.session_state.theme_toggle = True
    if "machine_buffers" not in st.session_state:
        st.session_state.machine_buffers = {machine_id: [] for machine_id in MACHINE_IDS}
    if "last_seen" not in st.session_state:
        st.session_state.last_seen = {}
    if "risk_streaks" not in st.session_state:
        st.session_state.risk_streaks = {machine_id: 0 for machine_id in MACHINE_IDS}
    if "last_alert_signature" not in st.session_state:
        st.session_state.last_alert_signature = {}
    if "alert_history" not in st.session_state:
        st.session_state.alert_history = load_alerts()


def reset_live_state():
    st.session_state.machine_buffers = {machine_id: [] for machine_id in MACHINE_IDS}
    st.session_state.last_seen = {}
    st.session_state.risk_streaks = {machine_id: 0 for machine_id in MACHINE_IDS}
    st.session_state.last_alert_signature = {}
    st.session_state.alert_history = load_alerts()


def get_trend_change(df, sensor="temperature_C", window=TREND_WINDOW):
    if sensor not in df.columns or len(df) < window:
        return None
    return float(df[sensor].iloc[-1] - df[sensor].iloc[-window])


def detect_trend(df, sensor="temperature_C"):
    change = get_trend_change(df, sensor)
    if change is None:
        return "collecting"
    if change > 3:
        return "increasing"
    if change < -3:
        return "decreasing"
    return "stable"


def forecast_temperature(df, sensor="temperature_C", window=TREND_WINDOW):
    if sensor not in df.columns or len(df) < window:
        return None
    slope = float(df[sensor].iloc[-1] - df[sensor].iloc[-window])
    return float(df[sensor].iloc[-1] + slope)


def format_trend(trend, change):
    if change is None:
        return "Collecting baseline"
    if trend == "increasing":
        return f"Increasing (+{change:.1f} C)"
    if trend == "decreasing":
        return f"Decreasing (-{abs(change):.1f} C)"
    return f"Stable ({change:+.1f} C)"


def z_score(value, mean, std):
    if std <= 0:
        return 0.0
    return float((value - mean) / std)


def severity_from_score(score, stale_seconds):
    if stale_seconds is not None and stale_seconds > 6:
        return "critical"
    if score >= 80:
        return "critical"
    if score >= 55:
        return "warning"
    if score >= 30:
        return "watch"
    return "normal"


def recommended_action(current, future_temperature, stale_seconds):
    if stale_seconds is not None and stale_seconds > STALE_AFTER_SECONDS:
        return "Check the stream connection and machine telemetry source."
    if future_temperature is not None and future_temperature > 90:
        return "Inspect the cooling path and schedule maintenance at the earliest slot."
    if current.get("vibration_mm_s", 0.0) > 2.0:
        return "Inspect bearings and rotating components for wear."
    if current.get("current_A", 0.0) > 16.0:
        return "Review motor load and electrical draw before the next production cycle."
    return "Continue monitoring and watch for repeated warning patterns."


def build_machine_state(machine_id, df, baseline, model):
    last_seen = st.session_state.last_seen.get(machine_id)
    current = df.iloc[-1].to_dict() if not df.empty else {}
    stale_seconds = None
    if last_seen is not None:
        stale_seconds = max(0.0, (utc_now() - last_seen).total_seconds())

    trend = detect_trend(df)
    trend_change = get_trend_change(df)
    future_temperature = forecast_temperature(df)

    risk_score = 0.0
    reasons = []
    z_scores = {}

    if df.empty:
        return {
            "machine_id": machine_id,
            "current": {column: 0.0 for column in FEATURE_COLUMNS},
            "status": "offline",
            "risk_score": 0,
            "severity": "watch",
            "summary": "No live data received yet for this machine.",
            "reasons": ["Waiting for the first sensor packet."],
            "trend": trend,
            "trend_change": trend_change,
            "future_temperature": future_temperature,
            "forecast_text": "Forecast available after five live samples.",
            "z_scores": {column: 0.0 for column in FEATURE_COLUMNS},
            "is_anomaly": False,
            "anomaly_score": 0.0,
            "stale_seconds": None,
            "last_seen_text": "No data yet",
            "action": "Verify the stream source for this machine.",
        }

    for column in FEATURE_COLUMNS:
        current_value = float(current.get(column, 0.0))
        baseline_mean = baseline[column]["mean"]
        baseline_std = baseline[column]["std"]
        z_scores[column] = z_score(current_value, baseline_mean, baseline_std)

    temperature_c = float(current.get("temperature_C", 0.0))
    vibration_mm_s = float(current.get("vibration_mm_s", 0.0))
    current_a = float(current.get("current_A", 0.0))
    machine_status = current.get("status", "running")

    is_anomaly = model.predict(current)
    anomaly_score = model.anomaly_score(current)

    if stale_seconds is not None and stale_seconds > STALE_AFTER_SECONDS:
        risk_score += min(40.0, 10.0 + (stale_seconds - STALE_AFTER_SECONDS) * 8.0)
        reasons.append(f"No fresh data received for {stale_seconds:.0f} seconds.")

    if temperature_c > max(88.0, baseline["temperature_C"]["mean"] + baseline["temperature_C"]["std"] * 2.2):
        risk_score += 28.0
        reasons.append(f"Temperature is elevated at {temperature_c:.1f} C versus the machine baseline.")
    elif temperature_c > max(80.0, baseline["temperature_C"]["mean"] + baseline["temperature_C"]["std"] * 1.4):
        risk_score += 16.0
        reasons.append(f"Temperature is drifting above the expected operating range at {temperature_c:.1f} C.")

    if vibration_mm_s > max(2.0, baseline["vibration_mm_s"]["mean"] + baseline["vibration_mm_s"]["std"] * 1.9):
        risk_score += 18.0
        reasons.append(f"Vibration reached {vibration_mm_s:.2f} mm/s, which may indicate bearing wear.")

    if current_a > max(16.0, baseline["current_A"]["mean"] + baseline["current_A"]["std"] * 1.8):
        risk_score += 14.0
        reasons.append(f"Current draw is elevated at {current_a:.2f} A.")

    if abs(z_scores["rpm"]) > 1.8:
        risk_score += 8.0
        reasons.append(f"RPM deviated from the baseline by {z_scores['rpm']:+.1f} standard deviations.")

    if trend == "increasing":
        risk_score += 12.0
        reasons.append(f"Temperature climbed {trend_change:.1f} C over the last {TREND_WINDOW} samples.")
    elif trend == "decreasing" and trend_change is not None:
        risk_score = max(0.0, risk_score - 4.0)

    if future_temperature is not None:
        if future_temperature > 90:
            risk_score += 20.0
            forecast_text = (
                f"Predicted to reach {future_temperature:.1f} C in the next 5-10 seconds. High overheating risk."
            )
        elif future_temperature > 80:
            risk_score += 10.0
            forecast_text = f"Predicted around {future_temperature:.1f} C in the next 5-10 seconds. Warning band."
        else:
            forecast_text = f"Predicted around {future_temperature:.1f} C in the next 5-10 seconds."
    else:
        forecast_text = "Forecast available after five live samples."

    if z_scores["temperature_C"] > 1.5 and z_scores["vibration_mm_s"] > 1.5:
        risk_score += 14.0
        reasons.append("Temperature and vibration are rising together, forming a compound risk pattern.")

    if z_scores["temperature_C"] > 1.2 and z_scores["current_A"] > 1.3:
        risk_score += 10.0
        reasons.append("Temperature and current draw are elevated together, which may point to overload.")

    if machine_status == "warning":
        risk_score += 8.0
    elif machine_status == "fault":
        risk_score += 18.0
        reasons.append("The machine-reported status is fault.")

    if is_anomaly:
        risk_score += min(18.0, 8.0 + anomaly_score * 12.0)
        reasons.append("The anomaly model flagged the current sensor pattern as unusual.")

    risk_score = min(100, int(round(risk_score)))
    severity = severity_from_score(risk_score, stale_seconds)

    if reasons:
        summary = reasons[0]
    else:
        summary = "Sensor behavior is close to the learned baseline."

    return {
        "machine_id": machine_id,
        "current": current,
        "status": machine_status if stale_seconds is None or stale_seconds <= STALE_AFTER_SECONDS else "stream_gap",
        "risk_score": risk_score,
        "severity": severity,
        "summary": summary,
        "reasons": reasons,
        "trend": trend,
        "trend_change": trend_change,
        "future_temperature": future_temperature,
        "forecast_text": forecast_text,
        "z_scores": z_scores,
        "is_anomaly": is_anomaly,
        "anomaly_score": anomaly_score,
        "stale_seconds": stale_seconds,
        "last_seen_text": current.get("timestamp", "Unknown"),
        "action": recommended_action(current, future_temperature, stale_seconds),
    }


def update_alert_tracking(states):
    for state in states:
        machine_id = state["machine_id"]
        current_streak = st.session_state.risk_streaks.get(machine_id, 0)

        if state["risk_score"] >= 55:
            current_streak += 1
        else:
            current_streak = 0

        st.session_state.risk_streaks[machine_id] = current_streak
        state["alert_streak"] = current_streak
        state["should_alert"] = state["severity"] == "critical" or current_streak >= ALERT_STREAK_THRESHOLD


def maybe_record_alert(state):
    if not state["should_alert"]:
        return

    signature = (
        f"{state['severity']}|{state['machine_id']}|{state['risk_score'] // 10}|"
        f"{state['summary'][:80]}"
    )
    previous = st.session_state.last_alert_signature.get(state["machine_id"])
    if signature == previous:
        return

    alert_payload = {
        "timestamp": utc_now().isoformat(timespec="seconds").replace("+00:00", "Z"),
        "machine_id": state["machine_id"],
        "severity": state["severity"],
        "risk_score": state["risk_score"],
        "summary": state["summary"],
        "action": state["action"],
    }
    save_alert(alert_payload)
    st.session_state.alert_history.insert(0, alert_payload)
    st.session_state.alert_history = st.session_state.alert_history[:50]
    st.session_state.last_alert_signature[state["machine_id"]] = signature


def priority_frame(states):
    rows = []
    for state in states:
        current = state["current"]
        rows.append(
            {
                "Machine": state["machine_id"],
                "Risk": state["risk_score"],
                "Severity": state["severity"].title(),
                "Status": str(state["status"]).replace("_", " ").title(),
                "Temperature (C)": round(float(current.get("temperature_C", 0.0)), 1),
                "Vibration (mm/s)": round(float(current.get("vibration_mm_s", 0.0)), 2),
                "Current (A)": round(float(current.get("current_A", 0.0)), 2),
                "Trend": format_trend(state["trend"], state["trend_change"]),
                "Forecast": state["forecast_text"],
            }
        )

    return pd.DataFrame(rows).sort_values(by=["Risk", "Machine"], ascending=[False, True]).reset_index(drop=True)


def baseline_frame(machine_id, state, baselines):
    rows = []
    for column in FEATURE_COLUMNS:
        current_value = float(state["current"].get(column, 0.0))
        rows.append(
            {
                "Sensor": SENSOR_LABELS[column],
                "Current": round(current_value, 2),
                "Baseline mean": round(baselines[machine_id][column]["mean"], 2),
                "Baseline std": round(baselines[machine_id][column]["std"], 2),
                "z-score": round(state["z_scores"][column], 2),
            }
        )
    return pd.DataFrame(rows)


def render_sidebar_brand():
    st.sidebar.markdown(
        """
        <div class="sidebar-brand">
            <div class="sidebar-brand-kicker">AI Factory Ops</div>
            <div class="sidebar-brand-title">Maintenance Studio</div>
            <div class="sidebar-brand-copy">
                Switch between live monitoring and recorded analysis from one premium workspace.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_workspace_header(view_label, title, subtitle, status_text=None, show_clock=True, show_theme_toggle=True):
    now = local_now()
    if show_clock or show_theme_toggle:
        left_col, right_col = st.columns([1.65, 1], gap="large")
    else:
        left_col, right_col = st.columns([1, 0.001], gap="large")

    with left_col:
        st.markdown(
            f"""
            <div class="topbar-card">
                <div class="shell-chip">{escape(view_label)}</div>
                <div class="shell-title">{escape(title)}</div>
                <div class="shell-subtitle">{escape(subtitle)}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with right_col:
        if show_theme_toggle:
            st.toggle("Dark theme", key="theme_toggle", help="Switch between dark and light workspace styles.")
        if show_clock:
            st.markdown(
                f"""
                <div class="clock-card">
                    <div>
                        <div class="clock-label">Daily control deck</div>
                        <div class="clock-time">{now.strftime("%I:%M %p")}</div>
                        <div class="clock-date">{now.strftime("%A, %d %B %Y")}<br>{escape(now.tzname() or "Local time")}</div>
                    </div>
                    <div class="clock-status">{escape(status_text or "")}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def render_hero():
    st.markdown(
        """
        <div class="hero-card">
            <div class="hero-kicker">AI Operations</div>
            <div class="hero-title">Predictive Maintenance Command Center</div>
            <div class="hero-copy">
                Multi-machine monitoring with per-machine baselines, short-horizon thermal forecasting,
                risk prioritization, transient spike suppression, and persistent alert history.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_summary_card(title, copy):
    st.markdown(
        f"""
        <div class="summary-card">
            <div class="summary-eyebrow">Situation</div>
            <div class="summary-title">{escape(title)}</div>
            <div class="summary-copy">{escape(copy)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_machine_card(state):
    current = state["current"]
    reasons = state["reasons"][:4]
    reason_items = "".join(f"<li>{escape(reason)}</li>" for reason in reasons) if reasons else ""
    if not reason_items:
        reason_items = "<li>Machine is operating near its learned baseline.</li>"

    st.markdown(
        f"""
        <div class="machine-card {escape(state['severity'])}">
            <div class="machine-top">
                <div>
                    <div class="machine-id">{escape(state['machine_id'])}</div>
                    <div class="machine-meta">
                        Status: {escape(str(state['status']).replace('_', ' ').title())}<br>
                        Last packet: {escape(state['last_seen_text'])}
                    </div>
                </div>
                <div class="risk-pill {escape(state['severity'])}">Risk {state['risk_score']}</div>
            </div>
            <div class="machine-grid">
                <div>
                    <div class="machine-stat-label">Temperature</div>
                    <div class="machine-stat-value">{float(current.get('temperature_C', 0.0)):.1f} C</div>
                </div>
                <div>
                    <div class="machine-stat-label">Vibration</div>
                    <div class="machine-stat-value">{float(current.get('vibration_mm_s', 0.0)):.2f} mm/s</div>
                </div>
                <div>
                    <div class="machine-stat-label">Current</div>
                    <div class="machine-stat-value">{float(current.get('current_A', 0.0)):.2f} A</div>
                </div>
                <div>
                    <div class="machine-stat-label">Trend</div>
                    <div class="machine-stat-value">{escape(format_trend(state['trend'], state['trend_change']))}</div>
                </div>
            </div>
            <div class="machine-copy">{escape(state['summary'])}</div>
            <ul class="machine-reasons">
                {reason_items}
            </ul>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_reason_card(title, items):
    if items:
        body = "<ul class='machine-reasons'>" + "".join(f"<li>{escape(item)}</li>" for item in items) + "</ul>"
    else:
        body = "<div class='reason-empty'>No active reasoning items for this section.</div>"

    st.markdown(
        f"""
        <div class="reason-card">
            <div class="reason-title">{escape(title)}</div>
            {body}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_analysis_hero():
    st.markdown(
        """
        <div class="hero-card">
            <div class="hero-kicker">Historical Intelligence</div>
            <div class="hero-title">📊 Historical Machine Analysis Dashboard</div>
            <div class="hero-copy">
                Explore recorded sensor data, compare day-to-day shifts, highlight anomalies,
                and forecast the next 5-10 values for each machine sensor.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_historical_status(message, tone):
    if tone == "critical":
        st.error(message)
    elif tone == "warning":
        st.warning(message)
    else:
        st.success(message)


def historical_analysis_dashboard():
    recorded_path = "database/sensor_data.json"
    render_workspace_header(
        "Historical analysis",
        "Recorded Sensor Intelligence",
        "Compare machine behavior across days, inspect anomalies, forecast the next readings, and export filtered evidence.",
        "Historical review mode",
    )
    render_analysis_hero()

    data_source = st.sidebar.radio(
        "Historical data source",
        options=["Recorded database", "Upload JSON file", "Paste JSON text"],
        key="historical_data_source",
    )

    source_note = ""
    if data_source == "Recorded database":
        modified_at = os.path.getmtime(recorded_path) if os.path.exists(recorded_path) else 0.0
        recorded_df = load_recorded_sensor_frame(recorded_path, modified_at)
        source_note = "Analyzing recorded telemetry from `database/sensor_data.json`."
    elif data_source == "Upload JSON file":
        uploaded_file = st.sidebar.file_uploader(
            "Upload JSON file",
            type=["json"],
            key="historical_json_upload",
            help="Upload external JSON such as 7 days of recorded machine telemetry.",
        )
        if uploaded_file is None:
            st.info("Upload a JSON file to analyze external historical data.")
            st.caption("Expected format: a list of records, or an object containing `records`, `data`, or `sensor_data`.")
            return

        try:
            json_text = uploaded_file.getvalue().decode("utf-8")
            recorded_df = load_external_sensor_frame(json_text)
            source_note = f"Analyzing uploaded file: `{uploaded_file.name}`."
        except UnicodeDecodeError:
            st.error("The uploaded file must be UTF-8 encoded JSON.")
            return
        except ValueError as exc:
            st.error(str(exc))
            return
    else:
        pasted_json = st.sidebar.text_area(
            "Paste JSON data",
            height=220,
            key="historical_json_text",
            help="Paste external JSON data such as 7 days of recorded telemetry.",
        )
        if not pasted_json.strip():
            st.info("Paste JSON data in the sidebar to analyze an external dataset.")
            st.caption("Expected format: a list of records, or an object containing `records`, `data`, or `sensor_data`.")
            return

        try:
            recorded_df = load_external_sensor_frame(pasted_json)
            source_note = "Analyzing pasted JSON data."
        except ValueError as exc:
            st.error(str(exc))
            return

    if recorded_df.empty:
        st.info("No historical sensor data is available for the selected source.")
        return

    st.caption(source_note)

    machine_options = sorted(recorded_df["machine_id"].dropna().unique().tolist())
    selected_machine = st.sidebar.selectbox("Recorded machine", machine_options, key="historical_machine")
    forecast_horizon = st.sidebar.slider("Prediction horizon", 5, 10, 5, key="historical_horizon")

    machine_df = recorded_df[recorded_df["machine_id"] == selected_machine].copy()
    available_sensors = [
        column
        for column in machine_df.columns
        if column not in {"machine_id", "timestamp", "status"} and machine_df[column].notna().any()
    ]

    if not available_sensors:
        st.warning("No sensor columns were found for the selected machine.")
        return

    min_timestamp = machine_df["timestamp"].min().to_pydatetime()
    max_timestamp = machine_df["timestamp"].max().to_pydatetime()

    if min_timestamp == max_timestamp:
        selected_range = (min_timestamp, max_timestamp)
        st.sidebar.caption(f"Recorded time range: {min_timestamp} to {max_timestamp}")
    else:
        selected_range = st.sidebar.slider(
            "Date / time range",
            min_value=min_timestamp,
            max_value=max_timestamp,
            value=(min_timestamp, max_timestamp),
            format="YYYY-MM-DD HH:mm:ss",
            key="historical_time_range",
        )

    selected_sensors = st.multiselect(
        "Available sensors",
        options=available_sensors,
        default=available_sensors,
        format_func=sensor_label,
    )

    if not selected_sensors:
        st.warning("Select at least one sensor to analyze.")
        return

    filtered_df = machine_df[
        machine_df["timestamp"].between(pd.Timestamp(selected_range[0]), pd.Timestamp(selected_range[1]))
    ].copy()

    if filtered_df.empty:
        st.info("No records match the selected machine and time filter.")
        return

    filtered_df = filtered_df.sort_values("timestamp").reset_index(drop=True)
    latest_row = filtered_df.iloc[-1]
    latest_sensor_statuses = [
        sensor_status(sensor_name, latest_row.get(sensor_name))[1]
        for sensor_name in selected_sensors
    ]
    severity_rank = {"normal": 0, "warning": 1, "critical": 2}
    overall_tone = max(latest_sensor_statuses, key=lambda item: severity_rank[item])

    records_count = len(filtered_df)
    day_count = filtered_df["timestamp"].dt.date.nunique()
    export_df = filtered_df[["machine_id", "timestamp", "status"] + selected_sensors].copy()
    export_df["timestamp"] = export_df["timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S")

    top_col1, top_col2, top_col3, top_col4 = st.columns(4)
    top_col1.metric("Machine", selected_machine)
    top_col2.metric("Records", records_count)
    top_col3.metric("Days in filter", day_count)
    top_col4.metric("Sensors selected", len(selected_sensors))

    render_historical_status(
        f"{selected_machine} historical status is {overall_tone.title()} for the latest filtered readings.",
        overall_tone,
    )

    st.download_button(
        "Download filtered data",
        export_df.to_csv(index=False).encode("utf-8"),
        file_name=f"{selected_machine}_historical_analysis.csv",
        mime="text/csv",
    )

    comparison_df, comparison_summary = build_day_comparison(filtered_df, selected_sensors)
    compare_col, records_col = st.columns([1.2, 1])

    with compare_col:
        st.subheader("Day-to-day comparison")
        st.caption(comparison_summary)
        if comparison_df.empty:
            st.info(comparison_summary)
        else:
            st.dataframe(comparison_df, use_container_width=True, hide_index=True)

    with records_col:
        st.subheader("Last 10 records")
        last_records = filtered_df[["timestamp", "status"] + selected_sensors].tail(10).iloc[::-1].copy()
        last_records["timestamp"] = last_records["timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S")
        st.dataframe(last_records, use_container_width=True, hide_index=True)

    for sensor_name in selected_sensors:
        sensor_series = filtered_df[["timestamp", sensor_name]].dropna().copy()
        if sensor_series.empty:
            continue

        trend, change, _ = detect_sensor_trend(sensor_series, sensor_name)
        prediction_df, prediction_message = predict_sensor_values(filtered_df, sensor_name, forecast_horizon)

        latest_value = float(sensor_series[sensor_name].iloc[-1])
        average_value = float(sensor_series[sensor_name].mean())
        max_value = float(sensor_series[sensor_name].max())
        min_value = float(sensor_series[sensor_name].min())
        status_label_text, status_tone = sensor_status(sensor_name, latest_value)
        anomaly_mask = sensor_series[sensor_name].apply(lambda value: sensor_status(sensor_name, value)[1] != "normal")
        anomaly_count = int(anomaly_mask.sum())
        unit = sensor_unit(sensor_name)
        unit_suffix = f" {unit}" if unit else ""
        trend_text = format_trend(trend, change)

        st.subheader(sensor_label(sensor_name))

        metric_col1, metric_col2, metric_col3, metric_col4, metric_col5 = st.columns(5)
        metric_col1.metric("Latest", f"{latest_value:.2f}{unit_suffix}")
        metric_col2.metric("Average", f"{average_value:.2f}{unit_suffix}")
        metric_col3.metric("Maximum", f"{max_value:.2f}{unit_suffix}")
        metric_col4.metric("Minimum", f"{min_value:.2f}{unit_suffix}")
        metric_col5.metric("Anomalies", anomaly_count)

        render_historical_status(
            f"{sensor_label(sensor_name)} is {status_label_text}. Trend: {trend_text}. Prediction: {prediction_message}",
            status_tone,
        )

        chart = build_sensor_chart(filtered_df, sensor_name, prediction_df)
        st.altair_chart(chart, use_container_width=True)



# ✅ MUST be the very first Streamlit call — never inside a function
st.set_page_config(layout="wide", page_title="Smart Site System")

# ---------- SESSION STATE DEFAULTS ----------
if "users" not in st.session_state:
    st.session_state.users = {}          # {email: {name, password}}

if "mode" not in st.session_state:
    st.session_state.mode = "signup"

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

# ---------- PASSWORD STRENGTH ----------
def password_strength(password: str) -> int:
    score = 0
    if len(password) >= 8:
        score += 1
    if re.search(r"[A-Z]", password):
        score += 1
    if re.search(r"[0-9]", password):
        score += 1
    if re.search(r"[@#$%^&+=]", password):
        score += 1
    return score


def show_strength(password: str) -> int:
    score = password_strength(password)
    if score <= 1:
        st.error("🔴 Weak password — needs uppercase, number & special char (@#$%^&+=)")
    elif score == 2:
        st.warning("🟡 Medium password — add more complexity")
    elif score == 3:
        st.info("🔵 Good password")
    else:
        st.success("🟢 Strong password")
    return score


# ---------- IMAGE LOADER ----------
def safe_get_base64(path: str) -> str:
    if os.path.exists(path):
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    return ""


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IMG_PATH = os.path.join(BASE_DIR, "assets", "loginn.jpg")
img_base64 = safe_get_base64(IMG_PATH)


# ---------- GLOBAL STYLES ----------
st.markdown("""
<style>



.block-container {
    padding: 0rem;
}



/* INPUT */
.stTextInput input {
    background-color: rgba(31,41,55,0.8) !important;
    color: white !important;
    border-radius: 8px;
    border: 1px solid rgba(255,255,255,0.1) !important;
    height: 45px;
}

/* LABEL */
.stTextInput label {
    color: #d1d5db !important;
}

/* BUTTON */
.stButton > button {
    background-color: #2563eb;
    color: white;
    border-radius: 8px;
    width: 100%;
    height: 45px;
    margin-top: 8px;
    border: none;
    font-weight: 600;
}

/* HOVER */
.stButton > button:hover {
    background-color: #1d4ed8;
}

/* CHECKBOX */
.stCheckbox label {
    color: #9ca3af !important;
}

/* SECONDARY BUTTON */
div[data-testid="stButton"]:last-of-type button {
    background-color: transparent;
    border: 1px solid rgba(255,255,255,0.2);
    color: #9ca3af;
}
div[data-testid="stButton"]:last-of-type button:hover {
    background-color: rgba(255,255,255,0.05);
    color: white;
}

</style>
""", unsafe_allow_html=True)


# ---------- MAIN ROUTER ----------
def main():
    if st.session_state.logged_in:
        show_dashboard()
    elif st.session_state.mode == "signup":
        show_signup()
    else:
        show_login()


# ---------- LAYOUT WRAPPER ----------
def page_layout(form_fn):
    """Renders the split left-image / right-form layout."""
    left, right = st.columns([1.6, 1])

    with left:
        bg = (
            f"url('data:image/jpeg;base64,{img_base64}')"
            if img_base64
            else "linear-gradient(135deg,#0f172a,#020617)"
        )
        st.markdown(
            f"""
            <div style="
                height: 100vh;
                background: {bg};
                background-size: cover;
                background-position: center;
            "></div>
            """,
            unsafe_allow_html=True,
        )

    with right:
        st.markdown('<div class="right-panel">', unsafe_allow_html=True)
        form_fn()
        st.markdown("</div>", unsafe_allow_html=True)


# ---------- SIGNUP PAGE ----------
def show_signup():
    def form():
        st.markdown("""
        <h1 style="color:white; margin-bottom:4px;">Create Account</h1>
        <p style="color:#9ca3af; margin-bottom:24px;">
            Welcome to the Smart Site System for Oil Depots.<br>
            Register as a member to get started.
        </p>
        """, unsafe_allow_html=True)

        username = st.text_input("User Name", key="signup_username")
        email    = st.text_input("E-mail", key="su_email")
        password = st.text_input("Password", type="password", key="su_password")

        # Always evaluate strength so confirm field is always present when needed
        strength = 0
        if password:
            strength = show_strength(password)

        # Show confirm field only when password is strong enough
        confirm = ""
        if password and strength >= 3:
            confirm = st.text_input("Re-enter Password", type="password", key="su_confirm")

        agree = st.checkbox("I agree to the terms of service", key="su_agree")

        if st.button("Create Account", key="btn_create"):
            # --- Validation ---
            if not username.strip() or not email.strip() or not password:
                st.warning("⚠️ Please fill in all fields.")
            elif not re.match(r"^[\w\.-]+@[\w\.-]+\.\w+$", email):
                st.error("❌ Enter a valid email address.")
            elif email in st.session_state.users:
                st.error("❌ An account with this email already exists.")
            elif strength < 3:
                st.error("❌ Password is too weak. Improve it before continuing.")
            elif confirm != password:
                st.error("❌ Passwords do not match.")
            elif not agree:
                st.warning("⚠️ You must accept the terms of service.")
            else:
                st.session_state.users[email] = {
                    "name": username.strip(),
                    "password": password,
                }
                st.success("🎉 Account created! Redirecting to login…")
                st.session_state.mode = "login"
                st.rerun()

        st.markdown("<p style='color:#9ca3af; margin-top:16px;'>Already have an account?</p>", unsafe_allow_html=True)
        if st.button("Go to Login", key="btn_go_login"):
            st.session_state.mode = "login"
            st.rerun()

    page_layout(form)


# ---------- LOGIN PAGE ----------
def show_login():
    def form():
        st.markdown("""
        <h1 style="color:white; margin-bottom:4px;">Welcome Back</h1>
        <p style="color:#9ca3af; margin-bottom:24px;">
            Sign in to access the Smart Site System.
        </p>
        """, unsafe_allow_html=True)

        email    = st.text_input("Email", key="li_email")
        password = st.text_input("Password", type="password", key="li_password")

        if st.button("Login", key="btn_login"):
            if not email.strip() or not password:
                st.warning("⚠️ Please enter both email and password.")
            else:
                user = st.session_state.users.get(email.strip())
                if user and user["password"] == password:
                    st.session_state.logged_in = True
                    st.session_state.current_user = user["name"]
                    st.success(f"✅ Welcome back, {user['name']}!")
                    st.rerun()
                else:
                    st.error("❌ Invalid email or password.")

        st.markdown("<p style='color:#9ca3af; margin-top:16px;'>Don't have an account?</p>", unsafe_allow_html=True)
        if st.button("Go to Signup", key="btn_go_signup"):
            st.session_state.mode = "signup"
            st.rerun()

    page_layout(form)





# ---------- ENTRY POINT ----------
def run_app():
    if not st.session_state.logged_in:
        main()



if __name__ == "__main__":
    run_app()



def advance_stream():
    snapshot = get_live_snapshot(MACHINE_IDS)
    for raw_reading in snapshot:
        machine_id = raw_reading["machine_id"]
        reading = preprocess(raw_reading)
        save_data(machine_id, reading)

        buffer = st.session_state.machine_buffers[machine_id]
        buffer.append(reading)
        if len(buffer) > BUFFER_SIZE:
            buffer.pop(0)

        reading_timestamp = parse_timestamp(reading.get("timestamp"))
        if reading_timestamp is not None:
            st.session_state.last_seen[machine_id] = reading_timestamp


def live_monitoring_dashboard():
    baselines = build_baselines("data/sample_data.csv")
    model = load_model("data/sample_data.csv")

    render_workspace_header(
        "Live monitoring",
        "Predictive Maintenance Command Center",
        "Track live machine telemetry, surface rising thermal risk early, and act on machine-level explanations before a fault escalates.",
        "Live stream connected",
    )
    render_hero()

    st.sidebar.header("Monitoring control")
    auto_refresh = st.sidebar.toggle("Auto refresh", value=True)
    refresh_interval = st.sidebar.slider("Refresh interval (seconds)", 1, 5, 1)
    focus_machine = st.sidebar.selectbox("Focus machine", MACHINE_IDS)
    st.sidebar.caption(
        "This dashboard now aligns more closely with the statement: 4 machines, per-machine baselines, "
        "risk prioritization, alert history, and stream-gap detection."
    )

    if st.sidebar.button("Reset live buffers"):
        reset_live_state()
        st.rerun()

    should_advance = auto_refresh or not any(st.session_state.machine_buffers.values()) or st.sidebar.button("Advance one cycle")
    if should_advance:
        advance_stream()

    states = []
    for machine_id in MACHINE_IDS:
        df = pd.DataFrame(st.session_state.machine_buffers[machine_id])
        states.append(build_machine_state(machine_id, df, baselines[machine_id], model))

    update_alert_tracking(states)
    for state in states:
        maybe_record_alert(state)

    states.sort(key=lambda item: item["risk_score"], reverse=True)
    highest = states[0]
    active_alerts = sum(1 for state in states if state["should_alert"])
    stream_gaps = sum(1 for state in states if state["stale_seconds"] is not None and state["stale_seconds"] > STALE_AFTER_SECONDS)

    top_metrics = st.columns(4)
    top_metrics[0].metric("Machines monitored", len(MACHINE_IDS))
    top_metrics[1].metric("Active alerts", active_alerts)
    top_metrics[2].metric("Highest risk", f"{highest['machine_id']} ({highest['risk_score']})")
    top_metrics[3].metric("Stream gaps", stream_gaps)

    render_summary_card(
        f"Priority target: {highest['machine_id']}",
        f"{highest['summary']} Recommended action: {highest['action']}",
    )

    board_col, focus_col = st.columns([1.35, 1])

    with board_col:
        st.subheader("Priority queue")
        st.dataframe(priority_frame(states), use_container_width=True, hide_index=True)

        st.subheader("Machine overview")
        card_columns = st.columns(2)
        for index, state in enumerate(states):
            with card_columns[index % 2]:
                render_machine_card(state)

    with focus_col:
        focus_state = next(state for state in states if state["machine_id"] == focus_machine)
        focus_df = pd.DataFrame(st.session_state.machine_buffers[focus_machine])

        st.subheader(f"Focus view: {focus_machine}")
        render_reason_card(
            "Decision explanation",
            focus_state["reasons"] or [focus_state["summary"]],
        )
        render_reason_card(
            "Recommended action",
            [focus_state["action"], focus_state["forecast_text"]],
        )

        if not focus_df.empty:
            chart_df = focus_df.rename(columns=SENSOR_LABELS)
            st.line_chart(
                chart_df[[SENSOR_LABELS[column] for column in FEATURE_COLUMNS]],
                height=320,
                use_container_width=True,
            )
            st.caption("Rolling window of the latest live samples for the selected machine.")
            st.dataframe(baseline_frame(focus_machine, focus_state, baselines), use_container_width=True, hide_index=True)
        else:
            st.info("Waiting for the first live packet for this machine.")

    st.subheader("Alert history")
    if st.session_state.alert_history:
        alert_df = pd.DataFrame(st.session_state.alert_history)
        st.dataframe(alert_df, use_container_width=True, hide_index=True)
    else:
        st.info("No alerts recorded yet.")

    if auto_refresh:
        time.sleep(refresh_interval)
        st.rerun()


def main_app():
    init_db()

    render_sidebar_brand()
    st.sidebar.caption(local_now().strftime("Today: %A, %d %B %Y"))
    st.sidebar.header("Navigation")
    dashboard_mode = st.sidebar.radio(
        "Dashboard mode",
        options=["Live Monitoring", "Historical Analysis"],
        key="dashboard_mode",
    )

    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.rerun()

    if dashboard_mode == "Historical Analysis":
        historical_analysis_dashboard()
    else:
        live_monitoring_dashboard()



init_session_state()
sync_theme_mode()
inject_styles()
 
# ---------- ENTRY POINT ----------
def run_app():
    if not st.session_state.logged_in:
        main()
    else:
        try:
            main_app()
        except Exception as e:
            st.error("Dashboard failed to load ⚠️")
            st.exception(e)


if __name__ == "__main__":
    run_app()

