import streamlit as st
import pandas as pd
import numpy as np
import re
import io
import zipfile
from datetime import datetime
from typing import List, Tuple, Dict, Optional

# ---------------- Page setup
st.set_page_config(page_title="Illinois Population Data", layout="wide", page_icon="🏛️")

# ---------------- External modules (robust import + fallbacks)
try:
    import backend_main_processing
    import frontend_data_loader
    import frontend_bracket_utils
    import frontend_sidebar as fs
except Exception as e:
    st.error(f"Import error: {e}")
    st.stop()

# Bind functions from sidebar module
render_sidebar_controls = fs.render_sidebar_controls
display_census_links = fs.display_census_links

# Safe fallbacks for constants (prevents hard import failures)
DATASET_URLS_FOR_VINTAGE = getattr(fs, "DATASET_URLS_FOR_VINTAGE", {})
RELEASE_STRIP_ITEMS = getattr(
    fs,
    "RELEASE_STRIP_ITEMS",
    [(y, "County Population by Characteristics — release") for y in range(2000, 2025)]
)

# ---------------- Paths
DATA_FOLDER = "./data"
FORM_CONTROL_PATH = "./form_control_UI_data.csv"

# ---- Region definitions (unique assignment with precedence: Cook > Collar > Urban > Rural)
COOK_SET   = {31}
COLLAR_SET = {43, 89, 97, 125, 197}
URBAN_SET  = {
    201, 125, 97, 39, 89, 43, 31, 93, 197, 91, 143, 179, 127, 19, 183, 165, 109, 113, 173
}
RURAL_SET  = {
    1,3,5,7,9,11,13,15,17,21,23,25,27,29,33,35,37,41,45,47,49,51,53,55,57,59,61,63,65,67,
    69,71,73,75,77,79,81,83,85,87,95,99,101,103,105,107,111,115,117,119,121,123,129,131,
    133,135,137,139,141,145,147,149,151,153,155,157,159,161,163,167,169,171,175,177,181,
    185,187,189,191,193,195,199,203
}
REGION_LABELS = ("Cook County", "Collar Counties", "Urban Counties", "Rural Counties")

RACE_DISPLAY_TO_CODE = {
    "Two or More Races": "TOM",
    "American Indian and Alaska Native": "AIAN",
    "Black or African American": "Black",
    "White": "White",
    "Native Hawaiian and Other Pacific Islander": "NHOPI",
    "Asian": "Asian",
}
RACE_CODE_TO_DISPLAY = {v: k for k, v in RACE_DISPLAY_TO_CODE.items()}

CODE_TO_BRACKET = {
    1:"0-4",2:"5-9",3:"10-14",4:"15-19",5:"20-24",6:"25-29",7:"30-34",8:"35-39",9:"40-44",
    10:"45-49",11:"50-54",12:"55-59",13:"60-64",14:"65-69",15:"70-74",16:"75-79",17:"80-84",18:"80+",
}

# =========================================================
# ---------------------- Styling --------------------------
# =========================================================
st.markdown("""
<style>
:root {
  --deep-blue: #0d47a1;
  --blue: #1976d2;
  --ink: #1a365d;
}

/* ---------------- Eye header ---------------- */
.hero-wrap { position: relative; text-align: center; padding-top: 8px; margin: 0 0 8px 0; }
.eye-svg  { width: min(1200px,96%); display:block; margin:0 auto; }
.eye-title {
  font-size: 3rem; font-weight: 800; line-height: 1.1;
  background: linear-gradient(135deg, var(--deep-blue), var(--blue));
  -webkit-background-clip: text; -webkit-text-fill-color: transparent;
  margin: .15rem 0 .15rem;
}
.eye-sub { font-size:1.05rem; color:#5b6b7d; font-style: italic; margin:.1rem 0 .25rem 0; }

/* eyebrows + glow */
.eye-glow {
  position:absolute; inset:0; pointer-events:none;
  background:
    radial-gradient(40rem 9rem at 12% 8%, rgba(255,243,205,0.28), transparent 60%),
    radial-gradient(40rem 9rem at 88% 8%, rgba(255,243,205,0.28), transparent 60%);
  mix-blend-mode:multiply;
}
.brow {
  position:absolute; left:50%; transform:translateX(-50%);
  top: -14px; width:min(1200px,96%); height:30px; pointer-events:none;
  background:
    radial-gradient(110% 140% at 15% 80%, rgba(140,110,60,.25), transparent 70%),
    radial-gradient(110% 140% at 85% 80%, rgba(140,110,60,.25), transparent 70%);
  filter: blur(0.5px);
}
/* blink */
.blink-lid {
  position:absolute; left:50%; transform:translateX(-50%);
  top: 22px; width:min(1200px,96%); height:0px; background: rgba(255,255,255,0.85);
  border-radius: 999px/40px; pointer-events: none; opacity: 0;
  animation: blink 7s infinite;
}
@keyframes blink {
  0%, 96%, 100% { height:0; opacity:0; }
  97% { height: 14px; opacity:.85; }
  98% { height: 0px; opacity: 0; }
}

/* KPI */
.metric-card {
  background: linear-gradient(135deg,#e3f2fd,#bbdefb);
  padding:1rem;border-radius: 15px;
  box-shadow: 0 4px 6px rgba(13,71,161,.1);
  margin-bottom:1rem;text-align:center;border:1px solid #90caf9;
  height:120px;display:flex;flex-direction:column;justify-content:center;
}
.metric-value { font-size: 2.2rem; font-weight: 700; color:#1a365d; margin-bottom:.3rem; line-height:1; }
.metric-label { font-size: .85rem; color:#4a5568; font-weight: 500; line-height:1.2; }
.kpi-brick {
  width: 15px; min-width: 15px; height: 120px;
  background: #bfbfbf; border-radius: 4px;
  box-shadow: inset 0 0 0 1px #9e9e9e, 0 1px 2px rgba(0,0,0,.08);
  margin: 0 auto; position: relative;
}
.kpi-brick::before, .kpi-brick::after {
  content: ""; position: absolute; left: 3px; right: 3px; height: 4px;
  background: rgba(0,0,0,0.08); border-radius: 2px;
}
.kpi-brick::before { top: 32px; }
.kpi-brick::after  { bottom: 32px; }

/* Release strip */
.release-strip {
  --speed: 28s;
  position:relative; overflow:hidden; width:min(1100px,94%); white-space:nowrap;
  border-radius: 10px; border:1px solid #e5e7eb; background:#fffdf7;
  box-shadow: 0 2px 5px rgba(0,0,0,.05) inset; margin:.25rem auto .25rem;
}
.strip-track { display:inline-flex; align-items:center; gap:2rem; padding:.35rem .75rem; animation: scroll var(--speed) linear infinite; }
.strip-item { color:#374151; font-size:.92rem; }
.strip-item b { color:#0d47a1; }
@keyframes scroll { 0% { transform: translateX(0); } 100% { transform: translateX(-50%); } }

/* Lamps + dark */
.dark-overlay { position:fixed; inset:0; pointer-events:none; background: rgba(0,0,0,var(--darkness, 0.35)); transition: background .25s ease; z-index: 2; }
.lamp { position: fixed; width: 12px; height: 12px; z-index: 3; pointer-events:none; border-radius: 50%; background: #444; box-shadow: 0 0 0 2px rgba(0,0,0,.15); }
.lamp.on { background: #fffde7; box-shadow: 0 0 10px rgba(255,240,170,.9), 0 0 28px rgba(255,240,170,.8), 0 0 60px rgba(255,230,120,.75); }
.lamp-glow { position:fixed; pointer-events:none; z-index:2; width: 55vw; height: 55vh; border-radius: 50%; filter: blur(18px); opacity: .0;
  background: radial-gradient(circle, rgba(255,243,205,.85) 0%, rgba(255,230,130,.55) 28%, rgba(255,230,130,.28) 52%, rgba(255,230,130,.05) 80%, transparent 90%); animation: pulse 8s ease-in-out infinite; }
.lamp-glow.on { opacity: .9; }
@keyframes pulse { 0%,100% { transform: scale(1); filter: blur(15px); } 50% { transform: scale(1.05); filter: blur(21px); } }
.lamp-left { top: 6px; left: 12px; } .lamp-right { top: 6px; right: 12px; }
.glow-left { top: -8vh; left: -10vw; } .glow-right { top: -8vh; right: -10vw; }

/* Sidebar sizing/locking */
:root { --sb-width: 280px; }
[data-testid="stSidebar"] > div:first-child { width: var(--sb-width) !important; min-width: var(--sb-width) !important; max-width: var(--sb-width) !important; }
.sb-resizable [data-testid="stSidebar"] > div:first-child { resize: horizontal; overflow: auto; box-shadow: inset 0 0 0 1px rgba(25,118,210,.25); }
.sb-locked  [data-testid="stSidebar"] > div:first-child { resize: none !important; overflow: hidden !important; }
</style>
""", unsafe_allow_html=True)

# =========================================================
# -------- Header + strip + lamps helper functions --------
# =========================================================
def render_header_with_eye(show_strip: bool, speed_seconds: float) -> None:
    st.markdown(
        """
        <div class="hero-wrap">
          <div class="eye-glow"></div>
          <div class="brow"></div>
          <svg class="eye-svg" viewBox="0 0 1200 200" preserveAspectRatio="none" aria-hidden="true">
            <path d="M10,20 Q600,-170 1190,20" stroke="#cbd5e1" stroke-width="4" fill="none" stroke-linecap="round"/>
          </svg>
          <div class="eye-title">Illinois Population Data</div>
          <div class="eye-sub">Analyze demographic trends across Illinois counties from 2000–2024</div>
          <svg class="eye-svg" viewBox="0 0 1200 200" preserveAspectRatio="none" aria-hidden="true">
            <path d="M10,190 Q600,370 1190,190" stroke="#cbd5e1" stroke-width="4" fill="none" stroke-linecap="round"/>
          </svg>
          <div class="blink-lid"></div>
        </div>
        """,
        unsafe_allow_html=True
    )
    if show_strip:
        items = " • ".join([f"<span class='strip-item'><b>{y}</b>: {txt}</span>" for (y, txt) in RELEASE_STRIP_ITEMS])
        st.markdown(
            f"""<div class="release-strip" style="--speed: {float(speed_seconds)}s">
                   <div class="strip-track">{items} • {items}</div>
                </div>""",
            unsafe_allow_html=True
        )

def render_lighting(lamp_left_on: bool, lamp_right_on: bool, intensity: float, pulse_speed: int, dark_enabled: bool):
    darkness = 0.55 if dark_enabled else 0.0
    darkness = min(max(darkness * (0.65 + 0.35 * (1.0 - intensity)), 0.0), 0.85)
    st.markdown(
        f"""
        <div class="dark-overlay" style="--darkness:{darkness};"></div>
        <div class="lamp lamp-left {'on' if lamp_left_on else ''}"></div>
        <div class="lamp lamp-right {'on' if lamp_right_on else ''}"></div>
        <div class="lamp-glow glow-left {'on' if lamp_left_on else ''}" style="animation-duration:{pulse_speed}s; opacity:{0.85*intensity if lamp_left_on else 0};"></div>
        <div class="lamp-glow glow-right {'on' if lamp_right_on else ''}" style="animation-duration:{pulse_speed}s; opacity:{0.85*intensity if lamp_right_on else 0};"></div>
        """,
        unsafe_allow_html=True
    )

# =========================================================
# --------------- Utility: county/age helpers -------------
# =========================================================
def combine_codes_to_label(codes: List[int]) -> str:
    codes = sorted(set(int(c) for c in codes))
    if not codes:
        return ""
    lows, highs = [], []
    for c in codes:
        s = CODE_TO_BRACKET.get(c, "")
        if "-" in s:
            a, b = s.split("-"); lows.append(int(a)); highs.append(int(b))
        elif s.endswith("+"):
            lows.append(int(s[:-1])); highs.append(999)
    if not lows:
        return "-".join(str(c) for c in codes)
    lo, hi = min(lows), max(highs)
    return f"{lo}+" if hi >= 999 else f"{lo}-{hi}"

def ensure_county_names(df: pd.DataFrame, counties_map: Dict[str,int]) -> pd.DataFrame:
    if df is None or df.empty:
        return df
    id_to_name = {v:k for k,v in counties_map.items()}
    if 'County Code' in df.columns and 'County Name' not in df.columns:
        df['County Name'] = df['County Code'].map(id_to_name).fillna(df['County Code'])
    if 'County' in df.columns:
        def _map(v):
            try:
                if isinstance(v, (int, np.integer)) and v in id_to_name: return id_to_name[v]
                if isinstance(v, str) and v.isdigit() and int(v) in id_to_name: return id_to_name[int(v)]
            except Exception:
                pass
            return v
        df['County'] = df['County'].apply(_map)
    return df

def _county_code_from_row(row, counties_map: Dict[str, int]) -> Optional[int]:
    if 'County Code' in row and pd.notna(row['County Code']):
        try:
            return int(row['County Code'])
        except Exception:
            pass
    if 'County' in row and pd.notna(row['County']):
        try:
            return int(row['County'])
        except Exception:
            pass
    if 'County Name' in row and pd.notna(row['County Name']):
        return int(counties_map.get(str(row['County Name']), np.nan)) if str(row['County Name']) in counties_map else None
    return None

def _code_to_region(code: Optional[int]) -> Optional[str]:
    if code is None: return None
    try:
        c = int(code)
    except Exception:
        return None
    if c in COOK_SET:   return "Cook County"
    if c in COLLAR_SET: return "Collar Counties"
    if c in URBAN_SET:  return "Urban Counties"
    if c in RURAL_SET:  return "Rural Counties"
    return "Unknown Region"

def attach_region_column(df: pd.DataFrame, counties_map: Dict[str,int]) -> pd.DataFrame:
    if df is None or df.empty:
        return df
    df = df.copy()
    if 'Region' in df.columns:
        df['Region'] = df['Region'].apply(lambda x: _code_to_region(_county_code_from_row({'County Code': None, 'County': None, 'County Name': x}, counties_map))
                                          if x not in REGION_LABELS else x)
        return df
    df['Region'] = df.apply(lambda r: _code_to_region(_county_code_from_row(r, counties_map)), axis=1)
    return df

def attach_agegroup_column(df: pd.DataFrame, include_age: bool, agegroup_for_backend: Optional[str],
                           custom_ranges: List[Tuple[int,int]], agegroup_map_implicit: Dict[str, list]) -> pd.DataFrame:
    if not include_age:
        return df
    df = df.copy()
    if custom_ranges:
        df['AgeGroup'] = np.nan
        covered = np.zeros(len(df), dtype=bool)
        for (mn,mx) in custom_ranges:
            mn_i, mx_i = max(1,int(mn)), min(18,int(mx))
            if mn_i > mx_i:
                continue
            mask = df['Age'].between(mn_i, mx_i)
            df.loc[mask, 'AgeGroup'] = combine_codes_to_label(list(range(mn_i, mx_i+1)))
            covered |= mask.to_numpy()
        if (~covered).any():
            df.loc[~covered, 'AgeGroup'] = "Other Ages"
        return df
    if agegroup_for_backend:
        df['AgeGroup'] = np.nan
        for expr in agegroup_map_implicit.get(agegroup_for_backend, []):
            try:
                mask = frontend_bracket_utils.parse_implicit_bracket(df, str(expr))
                df.loc[mask, 'AgeGroup'] = str(expr)
            except Exception:
                bexpr = str(expr).strip()
                m = None
                if "-" in bexpr:
                    a,b = bexpr.split("-"); m = df['Age'].between(int(a), int(b))
                elif bexpr.endswith("+") and bexpr[:-1].isdigit():
                    m = df['Age'] >= int(bexpr[:-1])
                if m is not None:
                    df.loc[m, 'AgeGroup'] = bexpr
        if df['AgeGroup'].isna().any():
            df['AgeGroup'] = df['AgeGroup'].fillna("Other Ages")
        return df
    df['AgeGroup'] = "All Ages"
    return df

def aggregate_multi(df_source: pd.DataFrame, grouping_vars: List[str], year_str: str,
                    county_label: str, counties_map: Dict[str,int], agegroup_for_backend: Optional[str],
                    custom_ranges: List[Tuple[int,int]], agegroup_map_implicit: Dict[str, list]) -> pd.DataFrame:
    grouping_vars_clean = [g for g in grouping_vars if g != "All"]

    def _empty():
        base = (["County"] if "County" not in grouping_vars_clean else [])
        cols = [("AgeGroup" if g == "Age" else g) for g in grouping_vars_clean]
        return pd.DataFrame(columns=base + cols + ["Count", "Percent", "Year"])

    if df_source is None or df_source.empty:
        return _empty()

    total_population = df_source["Count"].sum()
    if total_population == 0:
        return _empty()

    if len(grouping_vars_clean) == 0:
        out = pd.DataFrame({"Count":[int(total_population)], "Percent":[100.0], "Year":[str(year_str)]})
        out.insert(0, "County", county_label)
        return ensure_county_names(out, counties_map)

    include_age = "Age" in grouping_vars_clean
    df = attach_agegroup_column(df_source, include_age, agegroup_for_backend, custom_ranges, agegroup_map_implicit)
    df = attach_region_column(df, counties_map)

    group_fields = []
    for gv in grouping_vars_clean:
        if gv == "Age": group_fields.append("AgeGroup")
        elif gv == "County": group_fields.append("County")
        elif gv == "Region": group_fields.append("Region")
        else: group_fields.append(gv)

    grouped = df.groupby(group_fields, dropna=False)["Count"].sum().reset_index()
    if "Race" in grouped.columns:
        grouped["Race"] = grouped["Race"].map({v:k for k,v in RACE_DISPLAY_TO_CODE.items()}).fillna(grouped["Race"])
    grouped["Year"] = str(year_str)

    if "County" in grouped.columns:
        grouped.rename(columns={"County":"County Code"}, inplace=True)
        grouped = ensure_county_names(grouped, counties_map)

    denom_keys = ["Year"]
    if "County Code" in grouped.columns and "County" in grouping_vars_clean: denom_keys.append("County Code")
    if "Region" in grouped.columns and "Region" in grouping_vars_clean: denom_keys.append("Region")
    if "AgeGroup" in grouped.columns and "Age" in grouping_vars_clean: denom_keys.append("AgeGroup")

    if denom_keys:
        den = grouped.groupby(denom_keys, dropna=False)["Count"].transform("sum")
        grouped["Percent"] = np.where(den > 0, (grouped["Count"]/den*100).round(1), 0.0)
    else:
        grouped["Percent"] = (grouped["Count"]/total_population*100.0).round(1)

    if "County" not in grouping_vars_clean:
        grouped.insert(0, "County", county_label)
        grouped = ensure_county_names(grouped, counties_map)

    existing = list(grouped.columns)
    col_order = []
    if "County" in existing: col_order.append("County")
    if "County Code" in existing:
        col_order += ["County Code"]
        if "County Name" in existing: col_order += ["County Name"]
    for c in ["Region", "AgeGroup", "Race", "Ethnicity", "Sex"]:
        if c in existing and c not in col_order and c in group_fields:
            col_order.append(c)
    for c in ["Count", "Percent", "Year"]:
        if c in existing: col_order.append(c)
    for c in group_fields:
        if c in existing and c not in col_order:
            col_order.append(c)
    return grouped[col_order]

# ──────────────────────────────────────────────────────────────
# ConcatenatedKey
# ──────────────────────────────────────────────────────────────
def _normalize_token(x: object) -> str:
    import re as _re
    s = str(x).strip()
    s = s.replace("–", "-").replace("—", "-")
    s = _re.sub(r"\s+", "_", s)
    s = _re.sub(r"[^0-9A-Za-z_\-]+", "", s)
    return s

def add_concatenated_key_dynamic(df: pd.DataFrame, selected_filters: Dict[str, object], delimiter: str = "_") -> pd.DataFrame:
    if df is None or df.empty: return df
    group_by = selected_filters.get("group_by", []) or []
    cols_present = set(df.columns)
    key_cols: List[str] = []
    if {"County Code", "County Name"}.issubset(cols_present): key_cols += ["County Code", "County Name"]
    elif "County" in cols_present: key_cols += ["County"]
    map_ui_to_col = {"Age": "AgeGroup", "Race": "Race", "Ethnicity": "Ethnicity", "Sex": "Sex", "County": "County Code", "Region": "Region"}
    for g in group_by:
        col = map_ui_to_col.get(g, g)
        if col in cols_present and col not in key_cols and col not in {"County Code","County Name","County"}:
            key_cols.append(col)
    if "Year" in cols_present: key_cols.append("Year")
    out = df.copy()
    for c in key_cols:
        if c in out.columns:
            if pd.api.types.is_numeric_dtype(out[c]):
                try: out[c] = pd.to_numeric(out[c], errors="coerce").astype("Int64").astype(str)
                except Exception: out[c] = out[c].astype(str)
            else: out[c] = out[c].astype(str)
    if key_cols:
        out["ConcatenatedKey"] = out[key_cols].apply(lambda r: delimiter.join(_normalize_token(v) for v in r), axis=1)
    else:
        out["ConcatenatedKey"] = ""
    prefix_tokens: List[str] = []
    for sel_key, col_name, label_prefix in [("race", "Race", ""), ("ethnicity", "Ethnicity", ""), ("sex", "Sex", ""), ("region", "Region", "Region_")]:
        if col_name not in cols_present:
            val = selected_filters.get(sel_key)
            if val and str(val).strip().lower() not in {"all", "none"}:
                token = (label_prefix + _normalize_token(val)) if label_prefix else _normalize_token(val)
                prefix_tokens.append(token)
    if prefix_tokens:
        prefix = delimiter.join(prefix_tokens)
        out["ConcatenatedKey"] = prefix + (delimiter if out["ConcatenatedKey"].ne("").any() else "") + out["ConcatenatedKey"]
    return out

# =========================================================
# --------------- Download: source ZIP --------------------
# =========================================================
def build_source_zip_for_years(years: List[int]) -> Optional[bytes]:
    try:
        import requests
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
            for y in years:
                url = DATASET_URLS_FOR_VINTAGE.get(int(y))
                if not url: continue
                r = requests.get(url, timeout=30); r.raise_for_status()
                fname = url.split("/")[-1]
                zf.writestr(fname, r.content)
        buf.seek(0)
        return buf.read()
    except Exception:
        return None

# =========================================================
# ---------------- Pivot (Preview & export) ---------------
# =========================================================
def make_pivot_preview(df: pd.DataFrame, cfg: Dict[str, object]) -> pd.DataFrame:
    if df.empty or not cfg.get("enable_pivot"): return pd.DataFrame()
    value_col = cfg.get("pivot_values", "Count")
    cols = cfg.get("pivot_cols")
    rows = [r for r in (cfg.get("pivot_rows", []) or []) if r in df.columns]
    append_rows = bool(cfg.get("pivot_append_rows"))

    out_frames: List[pd.DataFrame] = []
    row_sets = [[r] for r in rows] if append_rows and len(rows) > 1 else [rows]

    for row_list in row_sets:
        if not row_list: continue
        pv = pd.pivot_table(
            df, index=row_list, columns=[cols] if cols in df.columns else None,
            values=value_col, aggfunc=np.sum, fill_value=0, dropna=False
        ).reset_index()
        pv.columns = [str(c) if not isinstance(c, tuple) else "_".join([str(x) for x in c if x]) for c in pv.columns]
        temp = add_concatenated_key_dynamic(pv.copy(), {"group_by": row_list + ([cols] if cols else []) + (["Year"] if "Year" in pv.columns else [])}, delimiter="_")
        out_frames.append(temp)

    return pd.concat(out_frames, ignore_index=True) if out_frames else pd.DataFrame()

# =========================================================
# ------------------------------ MAIN ---------------------
# =========================================================
def main():
    (years_list, agegroups_list_raw, races_list_raw, counties_map,
     agegroup_map_explicit, agegroup_map_implicit) = frontend_data_loader.load_form_control_data(FORM_CONTROL_PATH)

    choices = render_sidebar_controls(years_list, races_list_raw, counties_map, agegroup_map_implicit, agegroups_list_raw)

    # Sidebar width / lock CSS
    sb_width = int(choices["sidebar_width_px"])
    sb_resize_on = choices["sidebar_resize_enabled"]
    sb_lock = choices["sidebar_lock_width"]
    st.markdown(f"<style>:root {{ --sb-width: {sb_width}px; }}</style>", unsafe_allow_html=True)
    body_class = "sb-resizable" if sb_resize_on else ""
    if sb_lock: body_class += " sb-locked"
    st.markdown(f"<script>document.body.className = '{body_class.strip()}';</script>", unsafe_allow_html=True)

    # Top-center controls (interactive): override sidebar values for this run
    ctr1, ctr2, ctr3 = st.columns([1.2, 2.2, 1.2])
    with ctr2:
        a, b = st.columns([1, 1.4])
        with a:
            top_show = st.toggle("Show release strip", value=choices["show_release_strip"])
        with b:
            top_speed = st.slider("Speed (seconds per loop)", 14, 60, int(choices["release_speed"]))
    choices["show_release_strip"] = top_show
    choices["release_speed"] = top_speed

    # Header + strip
    render_header_with_eye(choices["show_release_strip"], choices["release_speed"])

    # Lamps & dark overlay
    render_lighting(
        lamp_left_on=choices["lamp_left_on"],
        lamp_right_on=choices["lamp_right_on"],
        intensity=float(choices["lamp_intensity"]),
        pulse_speed=int(choices["lamp_pulse_speed"]),
        dark_enabled=choices["dark_enabled"]
    )

    # KPI row
    st.markdown("## 📊 Data Overview")
    c1, b1, c2, b2, c3, b3, c4 = st.columns([1, 0.07, 1, 0.07, 1, 0.07, 1])
    with c1:
        st.markdown(f"""<div class="metric-card"><div class="metric-value">{len(years_list)}</div><div class="metric-label">Years Available</div></div>""", unsafe_allow_html=True)
    with b1: st.markdown('<div class="kpi-brick"></div>', unsafe_allow_html=True)
    with c2:
        st.markdown(f"""<div class="metric-card"><div class="metric-value">{len(counties_map)}</div><div class="metric-label">Illinois Counties</div></div>""", unsafe_allow_html=True)
    with b2: st.markdown('<div class="kpi-brick"></div>', unsafe_allow_html=True)
    with c3:
        st.markdown(f"""<div class="metric-card"><div class="metric-value">{len(races_list_raw)}</div><div class="metric-label">Race Categories</div></div>""", unsafe_allow_html=True)
    with b3: st.markdown('<div class="kpi-brick"></div>', unsafe_allow_html=True)
    with c4:
        st.markdown(f"""<div class="metric-card"><div class="metric-value">{len(agegroups_list_raw)}</div><div class="metric-label">Age Groups</div></div>""", unsafe_allow_html=True)

    # Controls row
    st.markdown("---")
    left_col, right_col = st.columns([3, 2])
    with left_col:
        try:
            go = st.button("🚀 Generate Report", use_container_width=True, type="primary")
        except TypeError:
            go = st.button("🚀 Generate Report", use_container_width=True)
        clear_clicked = st.button("🗑️ Clear Results", use_container_width=True)
        if clear_clicked:
            st.session_state.report_df = pd.DataFrame()
            st.session_state.selected_filters = {}
            st.rerun()
    with right_col:
        display_census_links()

    # State
    st.session_state.setdefault("report_df", pd.DataFrame())
    st.session_state.setdefault("selected_filters", {})

    # Optional: source files ZIP
    if choices.get("download_years"):
        src_bytes = build_source_zip_for_years(choices["download_years"])
        if src_bytes:
            st.download_button(
                "📥 Download selected source files (ZIP)",
                data=src_bytes,
                file_name=f"census_county_asrh_vintages_{min(choices['download_years'])}-{max(choices['download_years'])}.zip",
                mime="application/zip",
                use_container_width=True
            )
        else:
            st.info("Source-file download not available in this environment. On a machine with internet, this will produce a ZIP of the selected vintages.")

    # Generate
    if go:
        if not choices["selected_years"]:
            st.warning("⚠️ Please select at least one year."); st.stop()
        if not choices["selected_counties"]:
            st.warning("⚠️ Please select at least one county."); st.stop()

        st.session_state.selected_filters = {
            "years": [str(y) for y in choices["selected_years"]],
            "counties": choices["selected_counties"],
            "race": choices["selected_race_display"],
            "ethnicity": choices["selected_ethnicity"],
            "sex": choices["selected_sex"],
            "region": choices["selected_region"],
            "age_group": "Custom Ranges" if choices["enable_custom_ranges"] else choices["selected_agegroup_display"],
            "group_by": choices["grouping_vars"],
        }

        def _county_label_for_all():
            if "All" in choices["selected_counties"]:
                return choices["selected_region"] or "All Counties"
            return "Selected Counties"

        with st.spinner("🔄 Processing data…"):
            def build_block(county_list: List[str], county_label: str) -> pd.DataFrame:
                frames = []
                for year in choices["selected_years"]:
                    df_src = backend_main_processing.process_population_data(
                        data_folder=DATA_FOLDER,
                        agegroup_map_explicit=None,  # not used here
                        counties_map=counties_map,
                        selected_years=[year],
                        selected_counties=county_list,
                        selected_race=choices["selected_race_code"],
                        selected_ethnicity=choices["selected_ethnicity"],
                        selected_sex=choices["selected_sex"],
                        selected_region=choices["selected_region"],
                        selected_agegroup=choices["agegroup_for_backend"],
                        custom_age_ranges=choices["custom_ranges"] if choices["enable_custom_ranges"] else [],
                    )
                    block = aggregate_multi(
                        df_source=df_src,
                        grouping_vars=choices["grouping_vars"],
                        year_str=str(year),
                        county_label=county_label,
                        counties_map=counties_map,
                        agegroup_for_backend=choices["agegroup_for_backend"],
                        custom_ranges=choices["custom_ranges"] if choices["enable_custom_ranges"] else [],
                        agegroup_map_implicit=agegroup_map_implicit,
                    )
                    if not block.empty:
                        frames.append(block)
                return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

            all_frames: List[pd.DataFrame] = []
            if "All" in choices["selected_counties"]:
                combined = build_block(["All"], _county_label_for_all())
            else:
                combined = build_block(choices["selected_counties"], "Selected Counties")
            if not combined.empty:
                all_frames.append(combined)

            if choices["include_breakdown"] and "All" not in choices["selected_counties"]:
                for cty in choices["selected_counties"]:
                    cdf = build_block([cty], cty)
                    if not cdf.empty:
                        all_frames.append(cdf)

            st.session_state.report_df = pd.concat(all_frames, ignore_index=True) if all_frames else pd.DataFrame()
            st.session_state.report_df = ensure_county_names(st.session_state.report_df, counties_map)

            if not st.session_state.report_df.empty:
                st.session_state.report_df = add_concatenated_key_dynamic(
                    st.session_state.report_df, st.session_state.selected_filters, delimiter="_"
                )
                cols = st.session_state.report_df.columns.tolist()
                if "ConcatenatedKey" in cols:
                    cols = ["ConcatenatedKey"] + [c for c in cols if c != "ConcatenatedKey"]
                    st.session_state.report_df = st.session_state.report_df[cols]

    # Results / download
    if not st.session_state.report_df.empty:
        st.success("✅ Report generated successfully!")
        st.markdown("### 📋 Results")
        st.dataframe(st.session_state.report_df, use_container_width=True)

        # Pivot preview
        pivot_df = make_pivot_preview(st.session_state.report_df, choices)
        if not pivot_df.empty:
            st.markdown("### 🔁 Pivot Preview")
            st.dataframe(pivot_df, use_container_width=True)

        meta = [
            "# Illinois Population Data Explorer - Export",
            f"# Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "# Data Source: U.S. Census Bureau Population Estimates",
            f"# Years: {', '.join(st.session_state.selected_filters.get('years', []))}",
            f"# Counties: {', '.join(st.session_state.selected_filters.get('counties', []))}",
            f"# Region Filter: {st.session_state.selected_filters.get('region', 'None')}",
            f"# Race Filter: {st.session_state.selected_filters.get('race', 'All')}",
            f"# Ethnicity: {st.session_state.selected_filters.get('ethnicity', 'All')}",
            f"# Sex: {st.session_state.selected_filters.get('sex', 'All')}",
            f"# Age Group: {st.session_state.selected_filters.get('age_group', 'All')}",
            f"# Group By: {', '.join(st.session_state.selected_filters.get('group_by', [])) or 'None'}",
            f"# Total Records: {len(st.session_state.report_df)}",
            f"# Total Population: {st.session_state.report_df['Count'].sum():,}" if 'Count' in st.session_state.report_df.columns else "# Total Population: N/A",
            "#",
            "# Note: Data are official U.S. Census Bureau estimates and may be subject to error.",
            "#"
        ]
        csv_text = "\n".join(meta) + "\n" + st.session_state.report_df.to_csv(index=False)
        st.download_button("📥 Download CSV", data=csv_text, file_name="illinois_population_data.csv", mime="text/csv")

    st.markdown("---")
    st.markdown("<div style='text-align:center;color:#666;'>Illinois Population Data Explorer • U.S. Census Bureau Data • 2000–2024</div>", unsafe_allow_html=True)

if __name__ == "__main__":
    main()
