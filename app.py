import streamlit as st
import pandas as pd
import numpy as np
import re
from datetime import datetime
from typing import List, Tuple, Dict, Optional

# ──────────────────────────────────────────────────────────────────────────────
# Page setup
# ──────────────────────────────────────────────────────────────────────────────
st.set_page_config(page_title="Illinois Population Data", layout="wide", page_icon="🏛️")

# External modules (your existing back-end pieces + our modular sidebar)
try:
    import backend_main_processing
    import frontend_data_loader
    import frontend_bracket_utils
    from frontend_sidebar import (
        render_sidebar_controls,
        display_census_links,
        DATASET_URLS_FOR_VINTAGE,
        get_dataset_links_for_years,
    )
except Exception as e:
    st.error(f"Import error: {e}")
    st.stop()

DATA_FOLDER = "./data"
FORM_CONTROL_PATH = "./form_control_UI_data.csv"

# ──────────────────────────────────────────────────────────────────────────────
# Region definitions (unique assignment precedence: Cook > Collar > Urban > Rural)
# ──────────────────────────────────────────────────────────────────────────────
COOK_SET   = {31}
COLLAR_SET = {43, 89, 97, 125, 197}
URBAN_SET  = {201,125,97,39,89,43,31,93,197,91,143,179,127,19,183,165,109,113,173}
RURAL_SET  = {
    1,3,5,7,9,11,13,15,17,21,23,25,27,29,33,35,37,41,45,47,49,51,53,55,57,59,61,63,65,67,
    69,71,73,75,77,79,81,83,85,87,95,99,101,103,105,107,111,115,117,119,121,123,129,131,
    133,135,137,139,141,145,147,149,151,153,155,157,159,161,163,167,169,171,175,177,181,
    185,187,189,191,193,195,199,203
}
REGION_LABELS = ("Cook County", "Collar Counties", "Urban Counties", "Rural Counties")

RACE_DISPLAY_TO_CODE = {
    "Two or More Races":"TOM","American Indian and Alaska Native":"AIAN",
    "Black or African American":"Black","White":"White",
    "Native Hawaiian and Other Pacific Islander":"NHOPI","Asian":"Asian",
}

CODE_TO_BRACKET = {
    1:"0-4",2:"5-9",3:"10-14",4:"15-19",5:"20-24",6:"25-29",7:"30-34",8:"35-39",9:"40-44",
    10:"45-49",11:"50-54",12:"55-59",13:"60-64",14:"65-69",15:"70-74",16:"75-79",17:"80-84",18:"80+",
}

# ──────────────────────────────────────────────────────────────────────────────
# Release ticker (2000–2024 CPC/ASRH releases; keep stable + editable)
# ──────────────────────────────────────────────────────────────────────────────
CPC_RELEASES: List[Tuple[int, str]] = [
    (2024, "Jun 23, 2025"),
    (2023, "Jun 27, 2024"),
    (2022, "Jun 22, 2023"),
    (2021, "Jun 2022"),
    (2020, "Jun 2021"),
    (2019, "Jun 2020"),
    (2018, "Jun 2019"),
    (2017, "Jun 2018"),
    (2016, "Jun 2017"),
    (2015, "Jun 2016"),
    (2014, "Jun 2015"),
    (2013, "Jun 2014"),
    (2012, "Jun 2013"),
    (2011, "Jun 2012"),
    (2010, "Mar 2012"),
    (2009, "Jun 2010"),
    (2008, "Jun 2009"),
    (2007, "Jun 2008"),
    (2006, "Jun 2007"),
    (2005, "Jun 2006"),
    (2004, "Jun 2005"),
    (2003, "Jun 2004"),
    (2002, "Jun 2003"),
    (2001, "Jun 2002"),
    (2000, "Jun 2001"),
]

# ──────────────────────────────────────────────────────────────────────────────
# Global CSS (ticker + eye header + lamps + sidebar width hook)
# ──────────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* ===== Toggleable dark overlay + lamps (top-left / top-right) ===== */
#global-lighting-overlay{
  position: fixed; inset: 0; pointer-events: none; z-index: 9999;
}
#global-lighting-overlay .dim{
  position:absolute; inset:0; background:rgba(0,0,0,0.45); transition:opacity .25s ease;
}
#global-lighting-overlay.light-off .dim{ opacity: 0; }
#global-lighting-overlay .lamp{
  position:absolute; top:-40px; width:48vw; height:48vh; filter: blur(1px);
  background: radial-gradient(ellipse at center,
              rgba(255,255,220,0.65) 0%,
              rgba(255,250,200,0.45) 30%,
              rgba(255,240,160,0.28) 55%,
              rgba(255,240,160,0.0) 80%);
  opacity:.0; transition: opacity .25s ease;
}
#global-lighting-overlay .lamp.on{ opacity: 1; }
#global-lighting-overlay .lamp.left { left:-10vw; }
#global-lighting-overlay .lamp.right{ right:-10vw; }

/* ===== Release ticker ===== */
.release-controls-row{display:flex;align-items:center;justify-content:center;gap:1rem;margin:.15rem 0 .4rem 0;}
.release-ticker-wrap{position:relative;width:100%;overflow:hidden;background:linear-gradient(90deg,#0d47a1,#1565c0);border-bottom:1px solid rgba(255,255,255,.25);box-shadow:0 2px 6px rgba(13,71,161,.15);}
.release-ticker-wrap::before,.release-ticker-wrap::after{content:"";position:absolute;top:0;bottom:0;width:80px;pointer-events:none;z-index:2;}
.release-ticker-wrap::before{left:0;background:linear-gradient(90deg,rgba(13,71,161,1),rgba(13,71,161,0));}
.release-ticker-wrap::after{right:0;background:linear-gradient(270deg,rgba(21,101,192,1),rgba(21,101,192,0));}
.release-ticker-inner{--marquee-speed:135s;display:flex;width:max-content;white-space:nowrap;will-change:transform;animation:ticker-marquee var(--marquee-speed) linear infinite;padding:8px 0;}
.release-ticker-inner:hover{animation-play-state:paused;}
.release-seq{display:flex;align-items:center;gap:1.25rem;padding:0 1.2rem;}
.release-item{color:#fff;font-weight:700;font-size:.98rem;letter-spacing:.1px;}
.release-bullet{color:#e3f2fd;opacity:.55;}
.release-title-chip{display:inline-flex;align-items:center;gap:.5rem;background:rgba(255,255,255,.12);color:#fff;border:1px solid rgba(255,255,255,.25);padding:.15rem .55rem;border-radius:999px;font-weight:700;font-size:.9rem;}
@keyframes ticker-marquee{0%{transform:translateX(0);}100%{transform:translateX(-50%);}}

/* ===== "Eye" title (with eyebrows + soft flash) ===== */
.eye-wrap{position:relative;text-align:center;padding: 6px 0 2px;margin: 0 0 8px 0;}
.eye-svg{width:min(1200px,96%);height:120px;display:block;margin:0 auto;}
.eye-title{
  font-size:3rem;font-weight:900;line-height:1.1;margin:.2rem 0 .1rem;
  background:linear-gradient(135deg,#0d47a1,#1976d2);
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;
  text-shadow:0 0 0 transparent;
}
.eye-sub{font-size:1.1rem;color:#4a5568;text-align:center;margin-bottom:.5rem;font-style:italic;}
/* eyelid flash (slow blink) */
.eye-flash{
  position:absolute; left:50%; transform:translateX(-50%);
  top:12px; width:min(900px,82%); height:8px; border-radius:999px;
  background:linear-gradient(90deg,transparent,rgba(255,255,255,0.85),transparent);
  filter:blur(1px); opacity:.0; animation:eyeFlash 5.8s ease-in-out infinite;
}
@keyframes eyeFlash{
  0%{opacity:0;} 42%{opacity:0;}
  45%{opacity:.9;} 55%{opacity:.0;}
  100%{opacity:0;}
}

/* KPI cards + bricks */
.metric-card{background:linear-gradient(135deg,#e3f2fd,#bbdefb);padding:1rem;border-radius:15px;box-shadow:0 4px 6px rgba(13,71,161,.1);margin-bottom:1rem;text-align:center;border:1px solid #90caf9;height:120px;display:flex;flex-direction:column;justify-content:center;}
.metric-value{font-size:2.2rem;font-weight:700;color:#1a365d;margin-bottom:.3rem;line-height:1;}
.metric-label{font-size:.85rem;color:#4a5568;font-weight:500;line-height:1.2;}
.kpi-brick{width:15px;min-width:15px;height:120px;background:#bfbfbf;border-radius:4px;box-shadow:inset 0 0 0 1px #9e9e9e,0 1px 2px rgba(0,0,0,.08);margin:0 auto;position:relative;}
.kpi-brick::before,.kpi-brick::after{content:"";position:absolute;left:3px;right:3px;height:4px;background:rgba(0,0,0,0.08);border-radius:2px;}
.kpi-brick::before{top:32px}.kpi-brick::after{bottom:32px}

/* Sidebar width hook (set via inline style we inject) */
section[data-testid="stSidebar"] { transition: width .2s ease; }
</style>
""", unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────────────────────
# Utils
# ──────────────────────────────────────────────────────────────────────────────
def combine_codes_to_label(codes: List[int]) -> str:
    codes = sorted(set(int(c) for c in codes))
    if not codes: return ""
    lows, highs = [], []
    for c in codes:
        s = CODE_TO_BRACKET.get(c, "")
        if "-" in s:
            a,b = s.split("-"); lows.append(int(a)); highs.append(int(b))
        elif s.endswith("+"):
            lows.append(int(s[:-1])); highs.append(999)
    lo, hi = (min(lows), max(highs)) if lows else (None, None)
    if lo is None: return "-".join(str(c) for c in codes)
    return f"{lo}+" if hi >= 999 else f"{lo}-{hi}"

def ensure_county_names(df: pd.DataFrame, counties_map: Dict[str,int]) -> pd.DataFrame:
    if df is None or df.empty: return df
    id_to_name = {v:k for k,v in counties_map.items()}
    if 'County Code' in df.columns and 'County Name' not in df.columns:
        df['County Name'] = df['County Code'].map(id_to_name).fillna(df['County Code'])
    if 'County' in df.columns:
        def _map(v):
            try:
                if isinstance(v, (int, np.integer)) and v in id_to_name: return id_to_name[v]
                if isinstance(v, str) and v.isdigit() and int(v) in id_to_name: return id_to_name[int(v)]
            except Exception: pass
            return v
        df['County'] = df['County'].apply(_map)
    return df

def _county_code_from_row(row, counties_map: Dict[str, int]) -> Optional[int]:
    if 'County Code' in row and pd.notna(row['County Code']):
        try: return int(row['County Code'])
        except Exception: pass
    if 'County' in row and pd.notna(row['County']):
        try: return int(row['County'])
        except Exception: pass
    if 'County Name' in row and pd.notna(row['County Name']):
        return int(counties_map.get(str(row['County Name']), np.nan)) if str(row['County Name']) in counties_map else None
    return None

def _code_to_region(code: Optional[int]) -> Optional[str]:
    if code is None: return None
    try: c = int(code)
    except Exception: return None
    if c in COOK_SET:   return "Cook County"
    if c in COLLAR_SET: return "Collar Counties"
    if c in URBAN_SET:  return "Urban Counties"
    if c in RURAL_SET:  return "Rural Counties"
    return "Unknown Region"

def attach_region_column(df: pd.DataFrame, counties_map: Dict[str,int]) -> pd.DataFrame:
    if df is None or df.empty: return df
    df = df.copy()
    if 'Region' in df.columns:
        df['Region'] = df['Region'].apply(
            lambda x: _code_to_region(_county_code_from_row({'County Code': None, 'County': None, 'County Name': x}, counties_map))
            if x not in REGION_LABELS else x
        )
        return df
    df['Region'] = df.apply(lambda r: _code_to_region(_county_code_from_row(r, counties_map)), axis=1)
    return df

def attach_agegroup_column(df: pd.DataFrame, include_age: bool, agegroup_for_backend: Optional[str],
                           custom_ranges: List[Tuple[int,int]], agegroup_map_implicit: Dict[str, list]) -> pd.DataFrame:
    if not include_age: return df
    df = df.copy()
    if custom_ranges:
        df['AgeGroup'] = np.nan
        covered = np.zeros(len(df), dtype=bool)
        for (mn,mx) in custom_ranges:
            mn_i, mx_i = max(1,int(mn)), min(18,int(mx))
            if mn_i > mx_i: continue
            codes = list(range(mn_i, mx_i+1))
            label = combine_codes_to_label(codes)
            mask = df['Age'].between(mn_i, mx_i)
            df.loc[mask, 'AgeGroup'] = label; covered |= mask.to_numpy()
        if (~covered).any(): df.loc[~covered, 'AgeGroup'] = "Other Ages"
        return df
    if agegroup_for_backend:
        df['AgeGroup'] = np.nan
        for expr in agegroup_map_implicit.get(agegroup_for_backend, []):
            try:
                mask = frontend_bracket_utils.parse_implicit_bracket(df, str(expr))
                df.loc[mask, 'AgeGroup'] = str(expr)
            except Exception:
                bexpr = str(expr).strip(); m = None
                if "-" in bexpr:
                    a,b = bexpr.split("-"); m = df['Age'].between(int(a), int(b))
                elif bexpr.endswith("+") and bexpr[:-1].isdigit():
                    m = df['Age'] >= int(bexpr[:-1])
                if m is not None: df.loc[m, 'AgeGroup'] = bexpr
        if df['AgeGroup'].isna().any(): df['AgeGroup'] = df['AgeGroup'].fillna("Other Ages")
        return df
    df['AgeGroup'] = "All Ages"; return df

# ──────────────────────────────────────────────────────────────────────────────
# Aggregation & keys
# ──────────────────────────────────────────────────────────────────────────────
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
        out = ensure_county_names(out, counties_map)
        return out

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

    # normalize race labels
    if "Race" in grouped.columns:
        inv = {v:k for k,v in RACE_DISPLAY_TO_CODE.items()}
        grouped["Race"] = grouped["Race"].map(inv).fillna(grouped["Race"])

    grouped["Year"] = str(year_str)

    if "County" in grouped.columns:
        grouped.rename(columns={"County":"County Code"}, inplace=True)
        grouped = ensure_county_names(grouped, counties_map)

    denom_keys = ["Year"]
    if "County Code" in grouped.columns and "County" in grouping_vars_clean: denom_keys.append("County Code")
    if "Region" in grouped.columns and "Region" in grouping_vars_clean:     denom_keys.append("Region")
    if "AgeGroup" in grouped.columns and "Age" in grouping_vars_clean:      denom_keys.append("AgeGroup")

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
    for c in ["Region","AgeGroup","Race","Ethnicity","Sex"]:
        if c in existing and c not in col_order and c in group_fields: col_order.append(c)
    for c in ["Count","Percent","Year"]:
        if c in existing: col_order.append(c)
    for c in group_fields:
        if c in existing and c not in col_order: col_order.append(c)
    return grouped[col_order]

def _normalize_token(x: object) -> str:
    s = str(x).strip()
    s = s.replace("–", "-").replace("—", "-")
    s = re.sub(r"\s+", "_", s)
    s = re.sub(r"[^0-9A-Za-z_\\-]+", "", s)
    return s

def add_concatenated_key_dynamic(df: pd.DataFrame, selected_filters: Dict[str, object], delimiter: str = "_") -> pd.DataFrame:
    if df is None or df.empty: return df
    group_by = selected_filters.get("group_by", []) or []
    cols_present = set(df.columns)
    key_cols: List[str] = []
    if {"County Code","County Name"}.issubset(cols_present): key_cols += ["County Code","County Name"]
    elif "County" in cols_present: key_cols += ["County"]
    map_ui_to_col = {"Age":"AgeGroup","Race":"Race","Ethnicity":"Ethnicity","Sex":"Sex","County":"County Code","Region":"Region"}
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
    out["ConcatenatedKey"] = out[key_cols].apply(lambda r: delimiter.join(_normalize_token(v) for v in r), axis=1) if key_cols else ""
    prefix_tokens: List[str] = []
    for sel_key, col_name, label_prefix in [("race","Race",""),("ethnicity","Ethnicity",""),("sex","Sex",""),("region","Region","Region_")]:
        if col_name not in cols_present:
            val = selected_filters.get(sel_key)
            if val and str(val).strip().lower() not in {"all","none"}:
                token = (label_prefix + _normalize_token(val)) if label_prefix else _normalize_token(val)
                prefix_tokens.append(token)
    if prefix_tokens:
        prefix = "_".join(prefix_tokens)
        out["ConcatenatedKey"] = prefix + ("_" if out["ConcatenatedKey"].ne("").any() else "") + out["ConcatenatedKey"]
    return out

# ──────────────────────────────────────────────────────────────────────────────
# Pivot helpers
# ──────────────────────────────────────────────────────────────────────────────
def build_pivot_table(df: pd.DataFrame,
                      rows: List[str], cols: List[str], values: List[str],
                      agg_count: str = "sum",
                      percent_mode: str = "Weighted by Count (rows)",
                      margins: bool = True, flatten: bool = True,
                      sort_rows: bool = False,
                      append_per_row_var: bool = False) -> pd.DataFrame:
    """
    Build a pivot preview. If append_per_row_var=True and more than one row var is chosen,
    this creates one pivot per row variable and appends them (long format) with a column
    'PivotRowDim' to identify which row variable produced the block.
    """
    if df is None or df.empty or not values: return pd.DataFrame()

    # Keep only dims that exist
    rows = [r for r in rows if r in df.columns]
    cols = [c for c in cols if c in df.columns]

    def _single_pivot(use_rows: List[str]) -> pd.DataFrame:
        pieces = []
        # Count
        if "Count" in values and "Count" in df.columns:
            p_cnt = pd.pivot_table(df, index=use_rows or None, columns=cols or None, values="Count",
                                   aggfunc=agg_count, margins=margins, margins_name="Total",
                                   dropna=False, fill_value=0)
            pieces.append(("Count", p_cnt))
        # Percent
        if "Percent" in values and "Percent" in df.columns:
            if percent_mode.startswith("Weighted"):
                df2 = df.copy()
                df2["__pct_num"] = df2["Percent"] * df2["Count"] / 100.0
                num = pd.pivot_table(df2, index=use_rows or None, columns=cols or None, values="__pct_num",
                                     aggfunc="sum", margins=margins, margins_name="Total",
                                     dropna=False, fill_value=0)
                den = pd.pivot_table(df2, index=use_rows or None, columns=cols or None, values="Count",
                                     aggfunc="sum", margins=margins, margins_name="Total",
                                     dropna=False, fill_value=0)
                with np.errstate(divide='ignore', invalid='ignore'):
                    p_pct = (num / den) * 100.0
                    p_pct = p_pct.fillna(0)
            else:
                p_pct = pd.pivot_table(df, index=use_rows or None, columns=cols or None, values="Percent",
                                       aggfunc="mean", margins=margins, margins_name="Total",
                                       dropna=False, fill_value=0)
            pieces.append(("Percent", p_pct))

        if not pieces:
            return pd.DataFrame()

        # combine
        if len(pieces) == 1:
            pivot = pieces[0][1]
        else:
            pivot = pd.concat({name: p for name, p in pieces}, axis=1)

        # Sort rows if requested
        if sort_rows and use_rows:
            try:
                if isinstance(pivot.columns, pd.MultiIndex) and ("Count" in pivot.columns.levels[0]):
                    sort_key = pivot["Count"]
                else:
                    sort_key = pivot
                pivot = pivot.sort_values(by=list(sort_key.columns), ascending=False)
            except Exception:
                pass

        if flatten and isinstance(pivot.columns, pd.MultiIndex):
            pivot.columns = [" | ".join([str(x) for x in tup if str(x) != ""]) for tup in pivot.columns.to_flat_index()]

        pivot = pivot.reset_index() if use_rows else pivot.reset_index(drop=False)

        # Round percents nicely
        for col in pivot.columns:
            if isinstance(col, str) and ("Percent" in col or col == "Percent"):
                try:
                    pivot[col] = pivot[col].astype(float).round(1)
                except Exception:
                    pass
        return pivot

    if append_per_row_var and len(rows) > 1:
        blocks = []
        for rv in rows:
            pv = _single_pivot([rv])
            if pv.empty: continue
            pv.insert(0, "PivotRowDim", rv)
            blocks.append(pv)
        return pd.concat(blocks, ignore_index=True) if blocks else pd.DataFrame()
    else:
        return _single_pivot(rows)

def add_concatenated_key_for_pivot(pivot_df: pd.DataFrame,
                                   selected_filters: Dict[str, object],
                                   rows_used: List[str]) -> pd.DataFrame:
    """
    Add a ConcatenatedKey to the pivot preview (row-level key).
    Uses the available row columns (and any County/Year if present).
    """
    if pivot_df is None or pivot_df.empty: return pivot_df
    df = pivot_df.copy()
    cols_present = set(df.columns)
    key_cols: List[str] = []

    # Prefer named county columns if present
    if {"County Code","County Name"}.issubset(cols_present): key_cols += ["County Code","County Name"]
    elif "County" in cols_present: key_cols += ["County"]

    for r in rows_used:
        if r in cols_present and r not in key_cols:
            key_cols.append(r)
    if "Year" in cols_present and "Year" not in key_cols:
        key_cols.append("Year")

    # Safe casting
    for c in key_cols:
        if c in df.columns:
            if pd.api.types.is_numeric_dtype(df[c]):
                try: df[c] = pd.to_numeric(df[c], errors="coerce").astype("Int64").astype(str)
                except Exception: df[c] = df[c].astype(str)
            else: df[c] = df[c].astype(str)
    if key_cols:
        df["ConcatenatedKey"] = df[key_cols].apply(lambda r: "_".join(_normalize_token(x) for x in r), axis=1)
    else:
        df["ConcatenatedKey"] = ""
    return df

# ──────────────────────────────────────────────────────────────────────────────
# Ticker + Eye + Lamps renderers
# ──────────────────────────────────────────────────────────────────────────────
def render_release_ticker(releases: List[Tuple[int, str]], speed_seconds: int = 135, show: bool = True):
    if not show: return
    rel_sorted = sorted(releases, key=lambda x: x[0], reverse=True)
    items_html = "".join(
        f"<span class='release-item'>Vintage {y}: {when}</span><span class='release-bullet'>•</span>"
        for (y, when) in rel_sorted
    )
    html = f"""
    <div class="release-ticker-wrap" role="marquee" aria-label="County Population by Characteristics release dates">
        <div class="release-ticker-inner" style="--marquee-speed:{int(speed_seconds)}s;">
            <div class="release-seq">
              <span class='release-title-chip'>📅 County Population by Characteristics — Release Dates</span>
              <span class='release-bullet'>•</span>{items_html}
            </div>
            <div class="release-seq" aria-hidden="true">
              <span class='release-title-chip'>📅 County Population by Characteristics — Release Dates</span>
              <span class='release-bullet'>•</span>{items_html}
            </div>
        </div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)

def render_eye_header():
    st.markdown("""
<div class="eye-wrap">
  <svg class="eye-svg" viewBox="0 0 1200 200" preserveAspectRatio="none" aria-hidden="true">
    <!-- Eyebrows (upper & lower arcs) -->
    <path d="M10,190 Q600,-150 1190,190" stroke="#cbd5e1" stroke-width="4" fill="none" stroke-linecap="round"/>
  </svg>
  <div class="eye-flash"></div>
  <div class="eye-title">Illinois Population Data</div>
  <div class="eye-sub">Analyze demographic trends across Illinois counties from 2000–2024</div>
  <svg class="eye-svg" viewBox="0 0 1200 200" preserveAspectRatio="none" aria-hidden="true">
    <path d="M10,10 Q600,350 1190,10" stroke="#cbd5e1" stroke-width="4" fill="none" stroke-linecap="round"/>
  </svg>
</div>
""", unsafe_allow_html=True)

def render_lighting_controls_and_overlay():
    st.session_state.setdefault("lamp_left", False)
    st.session_state.setdefault("lamp_right", False)
    st.session_state.setdefault("dark_enabled", True)

    # Controls row (top-center)
    _l, center, _r = st.columns([1, 3, 1])
    with center:
        c1, c2, c3 = st.columns([1, 1, 1])
        with c1:
            st.session_state.dark_enabled = st.toggle("🌙 Dark Screen", value=st.session_state.dark_enabled, help="Dim the screen to see lamp lighting better.")
        with c2:
            st.session_state.lamp_left = st.toggle("💡 Left Lamp", value=st.session_state.lamp_left)
        with c3:
            st.session_state.lamp_right = st.toggle("💡 Right Lamp", value=st.session_state.lamp_right)

    # Overlay HTML
    lamp_left_cls  = "lamp left on"  if st.session_state.lamp_left  else "lamp left"
    lamp_right_cls = "lamp right on" if st.session_state.lamp_right else "lamp right"
    wrapper_cls    = "" if st.session_state.dark_enabled else "light-off"
    overlay_html = f"""
<div id="global-lighting-overlay" class="{wrapper_cls}">
  <div class="dim"></div>
  <div class="{lamp_left_cls}"></div>
  <div class="{lamp_right_cls}"></div>
</div>
"""
    st.markdown(overlay_html, unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────────────────────
# App main
# ──────────────────────────────────────────────────────────────────────────────
def main():
    # Lighting controls + release ticker controls (top)
    render_lighting_controls_and_overlay()

    st.session_state.setdefault("show_release_ticker", True)
    st.session_state.setdefault("ticker_speed", 135)
    _l, center, _r = st.columns([1, 3, 1])
    with center:
        c1, c2 = st.columns([1, 2])
        with c1:
            st.session_state.show_release_ticker = st.toggle("Show Release Strip", value=st.session_state.show_release_ticker)
        with c2:
            st.session_state.ticker_speed = st.slider("Ticker speed (secs per loop)", 60, 200, int(st.session_state.ticker_speed), 5, help="Lower = faster • Higher = slower")
    render_release_ticker(CPC_RELEASES, speed_seconds=st.session_state.ticker_speed, show=st.session_state.show_release_ticker)

    # Eye header
    render_eye_header()

    # Load lists for UI
    (years_list, agegroups_list_raw, races_list_raw, counties_map,
     agegroup_map_explicit, agegroup_map_implicit) = frontend_data_loader.load_form_control_data(FORM_CONTROL_PATH)

    # Sidebar
    choices = render_sidebar_controls(
        years_list, races_list_raw, counties_map, agegroup_map_implicit, agegroups_list_raw
    )

    # Sidebar width CSS (if enabled)
    if choices["ui_sidebar_resizable"]:
        width_px = int(choices["ui_sidebar_width"])
        st.markdown(
            f"<style>section[data-testid='stSidebar']{{width:{width_px}px; min-width:{width_px}px;}}</style>",
            unsafe_allow_html=True,
        )
    if choices["ui_sidebar_resizable"] and choices["ui_sidebar_locked"]:
        st.markdown("<style>section[data-testid='stSidebar'] *{user-select:none;}</style>", unsafe_allow_html=True)

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

    # Buttons + Census links (right column also shows source downloads for selected years)
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
            st.session_state.pivot_df = pd.DataFrame()
            st.session_state.selected_filters = {}
            st.rerun()
    with right_col:
        display_census_links(selected_years=choices["selected_years"])

    # State
    st.session_state.setdefault("report_df", pd.DataFrame())
    st.session_state.setdefault("pivot_df", pd.DataFrame())
    st.session_state.setdefault("selected_filters", {})

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
            return choices["selected_region"] or "All Counties" if "All" in choices["selected_counties"] else "Selected Counties"

        with st.spinner("🔄 Processing data…"):
            def build_block(county_list: List[str], county_label: str) -> pd.DataFrame:
                frames = []
                for year in choices["selected_years"]:
                    df_src = backend_main_processing.process_population_data(
                        data_folder=DATA_FOLDER,
                        agegroup_map_explicit=agegroup_map_explicit,
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
                    # Exact Region filter so Cook ≠ others
                    if choices["selected_region"] and choices["selected_region"] != "None":
                        df_src = attach_region_column(df_src, counties_map)
                        df_src = df_src[df_src["Region"] == choices["selected_region"]]

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
                    if not block.empty: frames.append(block)
                return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

            all_frames: List[pd.DataFrame] = []
            combined = build_block(["All"], _county_label_for_all()) if "All" in choices["selected_counties"] else build_block(choices["selected_counties"], "Selected Counties")
            if not combined.empty: all_frames.append(combined)

            if choices["include_breakdown"] and "All" not in choices["selected_counties"]:
                for cty in choices["selected_counties"]:
                    cdf = build_block([cty], cty)
                    if not cdf.empty: all_frames.append(cdf)

            st.session_state.report_df = pd.concat(all_frames, ignore_index=True) if all_frames else pd.DataFrame()
            st.session_state.report_df = ensure_county_names(st.session_state.report_df, counties_map)

            if not st.session_state.report_df.empty:
                st.session_state.report_df = add_concatenated_key_dynamic(st.session_state.report_df, st.session_state.selected_filters, delimiter="_")
                cols = st.session_state.report_df.columns.tolist()
                if "ConcatenatedKey" in cols:
                    cols = ["ConcatenatedKey"] + [c for c in cols if c != "ConcatenatedKey"]
                    st.session_state.report_df = st.session_state.report_df[cols]

            # Build pivot (preview) if requested
            if choices["pivot_enable"] and not st.session_state.report_df.empty:
                st.session_state.pivot_df = build_pivot_table(
                    st.session_state.report_df,
                    rows=choices["pivot_rows"],
                    cols=choices["pivot_cols"],
                    values=choices["pivot_vals"],
                    agg_count=choices["pivot_agg"],
                    percent_mode=choices["pivot_pct_mode"],
                    margins=choices["pivot_totals"],
                    flatten=choices["pivot_flatten"],
                    sort_rows=choices["pivot_sort_rows"],
                    append_per_row_var=choices["pivot_append_mode"]
                )
                # add ConcatenatedKey to the preview too
                st.session_state.pivot_df = add_concatenated_key_for_pivot(
                    st.session_state.pivot_df, st.session_state.selected_filters, rows_used=choices["pivot_rows"]
                )
                # If appending, allow appending multiple row dims in one go => ConcatenatedKey remains stable by row content

            else:
                st.session_state.pivot_df = pd.DataFrame()

    # Results / download
    if not st.session_state.report_df.empty:
        st.success("✅ Report generated successfully!")
        st.markdown("### 📋 Results")
        st.dataframe(st.session_state.report_df, use_container_width=True)

        # CSV (Raw)
        meta = [
            "# Illinois Population Data Explorer - Export",
            f"# Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "# Data Source: U.S. Census Bureau Population Estimates (CPC/ASRH)",
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
            "#", "# Note: Data are official U.S. Census Bureau estimates and may be subject to error.", "#"
        ]
        raw_csv = "\n".join(meta) + "\n" + st.session_state.report_df.to_csv(index=False)

        # Download buttons depending on pivot export preference
        show_raw = (choices["pivot_export_mode"] in {"Raw","Both"}) or not choices["pivot_enable"]
        show_pvt = choices["pivot_enable"] and (choices["pivot_export_mode"] in {"Pivot","Both"})

        if show_raw:
            st.download_button("📥 Download CSV (Raw)", data=raw_csv, file_name="illinois_population_data.csv", mime="text/csv")

        # Pivot preview & download
        if show_pvt and not st.session_state.pivot_df.empty:
            st.markdown("### 🔁 Pivot Preview")
            st.dataframe(st.session_state.pivot_df, use_container_width=True)
            pmeta = [
                "# Illinois Population Data Explorer - Pivot Export",
                f"# Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                f"# Rows: {', '.join(choices['pivot_rows']) or '(none)'}",
                f"# Columns: {', '.join(choices['pivot_cols']) or '(none)'}",
                f"# Values: {', '.join(choices['pivot_vals'])}",
                f"# Count agg: {choices['pivot_agg']}",
                f"# Percent mode: {choices['pivot_pct_mode']}",
                f"# Totals: {'Yes' if choices['pivot_totals'] else 'No'}",
                f"# Flatten headers: {'Yes' if choices['pivot_flatten'] else 'No'}",
                f"# Append per row variable: {'Yes' if choices['pivot_append_mode'] else 'No'}",
                "#"
            ]
            p_csv = "\n".join(pmeta) + "\n" + st.session_state.pivot_df.to_csv(index=False)
            st.download_button("📥 Download CSV (Pivot)", data=p_csv, file_name="illinois_population_pivot.csv", mime="text/csv")

    st.markdown("---")
    st.markdown("<div style='text-align:center;color:#666;'>Illinois Population Data Explorer • U.S. Census Bureau Data • 2000–2024</div>", unsafe_allow_html=True)

if __name__ == "__main__":
    main()
