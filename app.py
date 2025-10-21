import streamlit as st
import pandas as pd
import numpy as np
import re
from datetime import datetime
from typing import List, Tuple, Dict, Optional

# Page setup
st.set_page_config(page_title="Illinois Population Data", layout="wide", page_icon="🏛️")

# Styling (includes arched header + brick KPI dividers)
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        background: linear-gradient(135deg,#0d47a1,#1976d2);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align:center;
        margin-bottom: .25rem;
        font-weight: 800;
        line-height: 1.1;
    }
    .sub-title {
        font-size: 1.1rem;
        color:#4a5568;
        text-align:center;
        margin-bottom: .5rem;
        font-weight: 400;
        font-style: italic;
    }
    .hero-arch{
        position:relative;
        text-align:center;
        padding: 6px 0 2px;
        margin: 0 0 12px 0;
    }
    .arch-svg{
        width:min(1200px,96%);
        height:110px;
        display:block;
        margin:0 auto;
    }
    @media (max-width:700px){
        .arch-svg{ height:80px; }
    }

    .metric-card {
        background: linear-gradient(135deg,#e3f2fd,#bbdefb);
        padding:1rem;
        border-radius: 15px;
        box-shadow: 0 4px 6px rgba(13,71,161,.1);
        margin-bottom:1rem;
        text-align:center;
        border:1px solid #90caf9;
        height:120px;
        display:flex;
        flex-direction:column;
        justify-content:center;
    }
    .metric-value { font-size: 2.2rem; font-weight: 700; color:#1a365d; margin-bottom:.3rem; line-height:1; }
    .metric-label { font-size: .85rem; color:#4a5568; font-weight: 500; line-height:1.2; }

    /* Brick divider (15px wide) between KPI cards */
    .kpi-brick {
        width: 15px; min-width: 15px; height: 120px;
        background: #bfbfbf;
        border-radius: 4px;
        box-shadow: inset 0 0 0 1px #9e9e9e, 0 1px 2px rgba(0,0,0,.08);
        margin: 0 auto;
        position: relative;
    }
    .kpi-brick::before, .kpi-brick::after {
        content: ""; position: absolute; left: 3px; right: 3px; height: 4px;
        background: rgba(0,0,0,0.08); border-radius: 2px;
    }
    .kpi-brick::before { top: 32px; }
    .kpi-brick::after  { bottom: 32px; }
</style>
""", unsafe_allow_html=True)

# External modules
try:
    import backend_main_processing
    import frontend_data_loader
    import frontend_bracket_utils
    from frontend_sidebar import render_sidebar_controls, display_census_links
except Exception as e:
    st.error(f"Import error: {e}")
    st.stop()

DATA_FOLDER = "./data"
FORM_CONTROL_PATH = "./form_control_UI_data.csv"

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
            codes = list(range(mn_i, mx_i+1))
            label = combine_codes_to_label(codes)
            mask = df['Age'].between(mn_i, mx_i)
            df.loc[mask, 'AgeGroup'] = label; covered |= mask.to_numpy()
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
        out = ensure_county_names(out, counties_map)
        return out
    include_age = "Age" in grouping_vars_clean
    df = attach_agegroup_column(df_source, include_age, agegroup_for_backend, custom_ranges, agegroup_map_implicit)
    group_fields = [("AgeGroup" if g == "Age" else g) for g in grouping_vars_clean]
    grouped = df.groupby(group_fields, dropna=False)["Count"].sum().reset_index()
    if "Race" in grouped.columns:
        grouped["Race"] = grouped["Race"].map({v:k for k,v in RACE_DISPLAY_TO_CODE.items()}).fillna(grouped["Race"])
    grouped["Year"] = str(year_str)
    if "County" in grouping_vars_clean:
        if "County" in grouped.columns:
            grouped.rename(columns={"County":"County Code"}, inplace=True)
        grouped = ensure_county_names(grouped, counties_map)
        denom_keys = ["Year","County Code"]
        if "Age" in grouping_vars_clean and "AgeGroup" in grouped.columns:
            denom_keys.append("AgeGroup")
    else:
        denom_keys = ["Year"]
        if "Age" in grouping_vars_clean and "AgeGroup" in grouped.columns:
            denom_keys.append("AgeGroup")
    if denom_keys:
        den = grouped.groupby(denom_keys, dropna=False)["Count"].transform("sum")
        grouped["Percent"] = np.where(den > 0, (grouped["Count"]/den*100).round(1), 0.0)
    else:
        grouped["Percent"] = (grouped["Count"]/total_population*100.0).round(1)
    if "County" not in grouping_vars_clean:
        grouped.insert(0, "County", county_label)
        grouped = ensure_county_names(grouped, counties_map)
    else:
        group_fields = ["County Code" if g == "County" else g for g in group_fields]
    existing = list(grouped.columns); col_order = []
    if "County" in existing: col_order.append("County")
    if "County Code" in existing:
        col_order += ["County Code"]
        if "County Name" in existing: col_order += ["County Name"]
    for c in group_fields:
        if c in existing and c not in col_order: col_order.append(c)
    for c in ["Count","Percent","Year"]:
        if c in existing: col_order.append(c)
    return grouped[col_order]

# ──────────────────────────────────────────────────────────────
# NEW: dynamic ConcatenatedKey based on UI/group-by (uses "_" delimiter)
# ──────────────────────────────────────────────────────────────
def _normalize_token(x: object) -> str:
    s = str(x).strip()
    s = s.replace("–", "-").replace("—", "-")
    s = re.sub(r"\s+", "_", s)                 # spaces -> underscore
    s = re.sub(r"[^0-9A-Za-z_\-]+", "", s)     # keep letters/digits/_/-
    return s

def add_concatenated_key_dynamic(
    df: pd.DataFrame,
    selected_filters: Dict[str, object],
    delimiter: str = "_"
) -> pd.DataFrame:
    """
    Builds a 'ConcatenatedKey' using whatever columns are present based on the user's selections.
    Order:
      County Code, County Name (or County) → group_by-derived columns (AgeGroup, Race, Ethnicity, Sex, …) → Year
    If a dimension was filtered to a single value and NOT present as a column, the selected value is prefixed.
    """
    if df is None or df.empty:
        return df

    group_by = selected_filters.get("group_by", []) or []
    cols_present = set(df.columns)
    key_cols: List[str] = []

    # County first (prefer code+name when available)
    if {"County Code", "County Name"}.issubset(cols_present):
        key_cols += ["County Code", "County Name"]
    elif "County" in cols_present:
        key_cols += ["County"]

    # Map UI group names → data columns
    map_ui_to_col = {"Age": "AgeGroup", "Race": "Race", "Ethnicity": "Ethnicity", "Sex": "Sex", "County": "County Code"}
    for g in group_by:
        col = map_ui_to_col.get(g, g)
        if col in cols_present and col not in key_cols and col not in {"County Code","County Name","County"}:
            key_cols.append(col)

    # Year last if present
    if "Year" in cols_present:
        key_cols.append("Year")

    out = df.copy()

    # Cast columns to str safely
    for c in key_cols:
        if c in out.columns:
            if pd.api.types.is_numeric_dtype(out[c]):
                # keep integers as integers strings (avoid 1.0)
                try:
                    out[c] = pd.to_numeric(out[c], errors="coerce").astype("Int64").astype(str)
                except Exception:
                    out[c] = out[c].astype(str)
            else:
                out[c] = out[c].astype(str)

    # Base key from available columns
    if key_cols:
        out["ConcatenatedKey"] = out[key_cols].apply(lambda r: delimiter.join(_normalize_token(v) for v in r), axis=1)
    else:
        out["ConcatenatedKey"] = ""

    # If a dimension was filtered but not grouped (column missing), prefix that constant token
    prefix_tokens: List[str] = []
    for sel_key, col_name in [("race", "Race"), ("ethnicity", "Ethnicity"), ("sex", "Sex")]:
        if col_name not in cols_present:  # not grouped/shown
            val = selected_filters.get(sel_key)
            if val and str(val).strip().lower() not in {"all", "none"}:
                prefix_tokens.append(_normalize_token(val))

    if prefix_tokens:
        prefix = delimiter.join(prefix_tokens)
        out["ConcatenatedKey"] = prefix + (delimiter if out["ConcatenatedKey"].ne("").any() else "") + out["ConcatenatedKey"]

    return out

def main():
    # ===== Arched header (matches screenshot) =====
    st.markdown("""
<div class="hero-arch">
  <!-- top arc -->
  <svg class="arch-svg" viewBox="0 0 1200 200" preserveAspectRatio="none" aria-hidden="true">
    <path d="M10,190 Q600,-150 1190,190"
          stroke="#cbd5e1" stroke-width="4" fill="none" stroke-linecap="round"/>
  </svg>

  <div class="main-header">Illinois Population Data</div>
  <div class="sub-title">Analyze demographic trends across Illinois counties from 2000–2024</div>

  <!-- bottom arc -->
  <svg class="arch-svg" viewBox="0 0 1200 200" preserveAspectRatio="none" aria-hidden="true">
    <path d="M10,10 Q600,350 1190,10"
          stroke="#cbd5e1" stroke-width="4" fill="none" stroke-linecap="round"/>
  </svg>
</div>
""", unsafe_allow_html=True)

    # Load form controls
    (years_list, agegroups_list_raw, races_list_raw, counties_map,
     agegroup_map_explicit, agegroup_map_implicit) = frontend_data_loader.load_form_control_data(
        FORM_CONTROL_PATH
    )

    # Sidebar (all sections closed; includes "Group Results By")
    choices = render_sidebar_controls(
        years_list, races_list_raw, counties_map, agegroup_map_implicit, agegroups_list_raw
    )

    # KPI row with 15px bricks between cards
    st.markdown("## 📊 Data Overview")
    c1, b1, c2, b2, c3, b3, c4 = st.columns([1, 0.07, 1, 0.07, 1, 0.07, 1])

    with c1:
        st.markdown(
            f"""<div class="metric-card"><div class="metric-value">{len(years_list)}</div><div class="metric-label">Years Available</div></div>""",
            unsafe_allow_html=True,
        )
    with b1:
        st.markdown('<div class="kpi-brick"></div>', unsafe_allow_html=True)

    with c2:
        st.markdown(
            f"""<div class="metric-card"><div class="metric-value">{len(counties_map)}</div><div class="metric-label">Illinois Counties</div></div>""",
            unsafe_allow_html=True,
        )
    with b2:
        st.markdown('<div class="kpi-brick"></div>', unsafe_allow_html=True)

    with c3:
        st.markdown(
            f"""<div class="metric-card"><div class="metric-value">{len(races_list_raw)}</div><div class="metric-label">Race Categories</div></div>""",
            unsafe_allow_html=True,
        )
    with b3:
        st.markdown('<div class="kpi-brick"></div>', unsafe_allow_html=True)

    with c4:
        st.markdown(
            f"""<div class="metric-card"><div class="metric-value">{len(agegroups_list_raw)}</div><div class="metric-label">Age Groups</div></div>""",
            unsafe_allow_html=True,
        )

    # Buttons + Census links row (Census links on the RIGHT, default closed)
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

    # Generate flow
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
                combined = build_block(["All"], "All Counties")
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

            # >>> NEW: add dynamic ConcatenatedKey (underscore-delimited) <<<
            if not st.session_state.report_df.empty:
                st.session_state.report_df = add_concatenated_key_dynamic(
                    st.session_state.report_df, st.session_state.selected_filters, delimiter="_"
                )
                # Move the key to the first column for visibility
                cols = st.session_state.report_df.columns.tolist()
                if "ConcatenatedKey" in cols:
                    cols = ["ConcatenatedKey"] + [c for c in cols if c != "ConcatenatedKey"]
                    st.session_state.report_df = st.session_state.report_df[cols]

    # Results / download
    if not st.session_state.report_df.empty:
        st.success("✅ Report generated successfully!")
        st.markdown("### 📋 Results")
        st.dataframe(st.session_state.report_df, use_container_width=True)

        meta = [
            "# Illinois Population Data Explorer - Export",
            f"# Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "# Data Source: U.S. Census Bureau Population Estimates",
            f"# Years: {', '.join(st.session_state.selected_filters.get('years', []))}",
            f"# Counties: {', '.join(st.session_state.selected_filters.get('counties', []))}",
            f"# Race Filter: {st.session_state.selected_filters.get('race', 'All')}",
            f"# Ethnicity: {st.session_state.selected_filters.get('ethnicity', 'All')}",
            f"# Sex: {st.session_state.selected_filters.get('sex', 'All')}",
            f"# Region: {st.session_state.selected_filters.get('region', 'None')}",
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
