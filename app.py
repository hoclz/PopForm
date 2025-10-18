import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt  # kept for future charts
from datetime import datetime
from typing import List, Tuple, Dict, Optional

# ------------------------------------------------------------------------
# Streamlit Page Config
st.set_page_config(
    page_title="Illinois Population Data Explorer",
    layout="wide",
    page_icon="🏛️"
)

# ------------------------------------------------------------------------
# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        background: linear-gradient(135deg, #0d47a1, #1976d2);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        margin-bottom: 0.5rem;
        font-weight: 800;
        line-height: 1.1;
    }
    .sub-title {
        font-size: 1.2rem;
        color: #4a5568;
        text-align: center;
        margin-bottom: 2rem;
        font-weight: 400;
        font-style: italic;
    }
    .section-header {
        font-size: 1.6rem;
        color: #0d47a1;
        border-left: 5px solid #1976d2;
        padding-left: 1rem;
        margin: 2rem 0 1rem 0;
        font-weight: 600;
    }
    .metric-card {
        background: linear-gradient(135deg, #e3f2fd, #bbdefb);
        padding: 1rem;
        border-radius: 15px;
        box-shadow: 0 4px 6px rgba(13, 71, 161, 0.1);
        margin-bottom: 1rem;
        text-align: center;
        border: 1px solid #90caf9;
        height: 120px;
        display: flex;
        flex-direction: column;
        justify-content: center;
    }
    .metric-value {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1a365d;
        margin-bottom: 0.3rem;
        line-height: 1;
    }
    .metric-label {
        font-size: 0.85rem;
        color: #4a5568;
        font-weight: 500;
        line-height: 1.2;
    }
</style>
""", unsafe_allow_html=True)

# ------------------------------------------------------------------------
# Backend modules
try:
    import backend_main_processing
    import frontend_data_loader
    import frontend_bracket_utils
except ImportError as e:
    st.error(f"Error importing backend modules: {e}")
    st.stop()

# ------------------------------------------------------------------------
# Paths
DATA_FOLDER = "./data"
FORM_CONTROL_PATH = "./form_control_UI_data.csv"

# ------------------------------------------------------------------------
# Race code ↔ display
RACE_DISPLAY_TO_CODE = {
    "Two or More Races": "TOM",
    "American Indian and Alaska Native": "AIAN",
    "Black or African American": "Black",
    "White": "White",
    "Native Hawaiian and Other Pacific Islander": "NHOPI",
    "Asian": "Asian"
}
RACE_CODE_TO_DISPLAY = {v: k for k, v in RACE_DISPLAY_TO_CODE.items()}

# Age code → label lookup (1..18)
CODE_TO_BRACKET = {
    1:  "0-4",
    2:  "5-9",
    3:  "10-14",
    4:  "15-19",
    5:  "20-24",
    6:  "25-29",
    7:  "30-34",
    8:  "35-39",
    9:  "40-44",
    10: "45-49",
    11: "50-54",
    12: "55-59",
    13: "60-64",
    14: "65-69",
    15: "70-74",
    16: "75-79",
    17: "80-84",
    18: "80+"
}

def combine_codes_to_label(codes: List[int]) -> str:
    """Combine age codes into a single label (e.g., 1..5 → '0-24')."""
    codes = sorted(set(int(c) for c in codes))
    if not codes:
        return ""
    lows, highs = [], []
    for c in codes:
        s = CODE_TO_BRACKET.get(c, "")
        if "-" in s:
            a, b = s.split("-")
            try:
                lows.append(int(a))
                highs.append(int(b.replace("+", "")))
            except Exception:
                pass
        elif s.endswith("+"):
            try:
                lows.append(int(s[:-1]))
                highs.append(999)
            except Exception:
                pass
    if not lows or not highs:
        return "-".join(str(c) for c in codes)
    lo, hi = min(lows), max(highs)
    return f"{lo}+" if hi >= 999 else f"{lo}-{hi}"

# ------------------------------------------------------------------------
# County name helper
def ensure_county_names(df: pd.DataFrame, counties_map: Dict[str, int]) -> pd.DataFrame:
    """Add/normalize county name columns."""
    if df is None or df.empty:
        return df
    id_to_name = {v: k for k, v in counties_map.items()}

    # If we have County (code) column and we're not labeling by County (free-text),
    # map it where appropriate.
    if 'County Code' in df.columns:
        if 'County Name' not in df.columns:
            df['County Name'] = df['County Code'].map(id_to_name).fillna(df['County Code'])
    if 'County' in df.columns:
        # Might be label (e.g., "All Counties") or a code; keep labels as-is
        def _map_val(v):
            try:
                if isinstance(v, (int, np.integer)) and v in id_to_name:
                    return id_to_name[v]
                if isinstance(v, str) and v.isdigit() and int(v) in id_to_name:
                    return id_to_name[int(v)]
            except Exception:
                pass
            return v
        df['County'] = df['County'].apply(_map_val)
    return df

# ------------------------------------------------------------------------
# Debug
def debug_data_processing(df_source: pd.DataFrame, tag: str):
    if df_source is None or df_source.empty:
        st.warning(f"No data after filtering ({tag})")
        return
    st.write(f"**Debug — {tag}** rows={len(df_source)} total_pop={df_source['Count'].sum():,}")
    for c in ["Age", "Race", "Ethnicity", "Sex", "County"]:
        if c in df_source.columns:
            st.write(f"• {c}: {df_source[c].nunique()} unique")

# ------------------------------------------------------------------------
# Census Links
def display_census_links():
    docs = [
        (2024, "April 1, 2020 to July 1, 2024", "https://www2.census.gov/programs-surveys/popest/technical-documentation/file-layouts/2020-2024/CC-EST2024-ALLDATA.pdf"),
        (2023, "April 1, 2020 to July 1, 2023", "https://www2.census.gov/programs-surveys/popest/technical-documentation/file-layouts/2020-2023/CC-EST2023-ALLDATA.pdf"),
        (2022, "April 1, 2020 to July 1, 2022", "https://www2.census.gov/programs-surveys/popest/technical-documentation/file-layouts/2020-2022/cc-est2022-alldata.pdf"),
        (2021, "April 1, 2020 to July 1, 2021", "https://www2.census.gov/programs-surveys/popest/technical-documentation/file-layouts/2020-2021/cc-est2021-alldata.pdf"),
        (2020, "April 1, 2010 to July 1, 2020", "https://www2.census.gov/programs-surveys/popest/technical-documentation/file-layouts/2010-2020/cc-est2020-alldata.pdf"),
    ]
    with st.expander("Census Data Links", expanded=False):
        st.markdown("""
**Important Links**:
- [Census Datasets](https://www2.census.gov/programs-surveys/popest/datasets/)
- [2000–2010 Intercensal County](https://www2.census.gov/programs-surveys/popest/datasets/2000-2010/intercensal/county/)
- [2010–2020 County ASRH](https://www2.census.gov/programs-surveys/popest/datasets/2010-2020/counties/asrh/)
- [2020–2023 County ASRH](https://www2.census.gov/programs-surveys/popest/datasets/2020-2023/counties/asrh/)
- [2020–2024 County ASRH](https://www2.census.gov/programs-surveys/popest/datasets/2020-2024/counties/asrh/)
- [Release Schedule](https://www.census.gov/programs-surveys/popest/about/schedule.html)
""")
        st.markdown("---")
        md = "**Documentation Codebooks**:\n- [File Layouts Main Page](https://www2.census.gov/programs-surveys/popest/technical-documentation/file-layouts/)\n"
        for y, p, u in docs:
            md += f"- [Vintage {y} ({p})]({u})\n"
        md += "- [Methodology Overview](https://www.census.gov/programs-surveys/popest/technical-documentation/methodology.html)\n"
        md += "- [Modified Race Data](https://www.census.gov/programs-surveys/popest/technical-documentation/research/modified-race-data.html)\n"
        st.markdown(md)

# ------------------------------------------------------------------------
# CSV with metadata
def add_metadata_to_csv(df: pd.DataFrame, selected_filters: Dict) -> str:
    meta = [
        "# Illinois Population Data Explorer - Export",
        f"# Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "# Data Source: U.S. Census Bureau Population Estimates",
        f"# Years: {', '.join(selected_filters.get('years', []))}",
        f"# Counties: {', '.join(selected_filters.get('counties', []))}",
        f"# Race Filter: {selected_filters.get('race', 'All')}",
        f"# Ethnicity: {selected_filters.get('ethnicity', 'All')}",
        f"# Sex: {selected_filters.get('sex', 'All')}",
        f"# Region: {selected_filters.get('region', 'None')}",
        f"# Age Group: {selected_filters.get('age_group', 'All')}",
        f"# Group By: {', '.join(selected_filters.get('group_by', [])) or 'None'}",
        f"# Total Records: {len(df)}",
        f"# Total Population: {df['Count'].sum():,}" if 'Count' in df.columns else "# Total Population: N/A",
        "#",
        "# Note: Data are official U.S. Census Bureau estimates",
        "# and may be subject to sampling error",
        "#"
    ]
    return "\n".join(meta) + "\n" + df.to_csv(index=False)

# ------------------------------------------------------------------------
# AgeGroup attachment (for multi-dim groupby)
def attach_agegroup_column(
    df: pd.DataFrame,
    include_age: bool,
    agegroup_for_backend: Optional[str],
    custom_ranges: List[Tuple[int, int]],
    agegroup_map_implicit: Dict[str, List[str]]
) -> pd.DataFrame:
    if not include_age:
        return df
    df = df.copy()

    # Custom ranges: explicit labels (+ "Other Ages" to close the 100% gap)
    if custom_ranges:
        df['AgeGroup'] = np.nan
        covered = np.zeros(len(df), dtype=bool)
        for (mn, mx) in custom_ranges:
            mn_i = max(1, int(mn)); mx_i = min(18, int(mx))
            if mn_i > mx_i: 
                continue
            codes = list(range(mn_i, mx_i + 1))
            label = combine_codes_to_label(codes)
            mask = df['Age'].between(mn_i, mx_i)
            df.loc[mask, 'AgeGroup'] = label
            covered |= mask.to_numpy()
        if (~covered).any():
            df.loc[~covered, 'AgeGroup'] = "Other Ages"
        return df

    # Implicit sets (e.g., 18/6/2-bracket)
    if agegroup_for_backend:
        df['AgeGroup'] = np.nan
        for bexpr in agegroup_map_implicit.get(agegroup_for_backend, []):
            try:
                mask = frontend_bracket_utils.parse_implicit_bracket(df, str(bexpr))
                df.loc[mask, 'AgeGroup'] = str(bexpr)
            except Exception:
                bexpr = str(bexpr).strip()
                m = None
                if "-" in bexpr:
                    a, b = bexpr.split("-")
                    m = df['Age'].between(int(a), int(b))
                elif bexpr.endswith("+") and bexpr[:-1].isdigit():
                    m = df['Age'] >= int(bexpr[:-1])
                if m is not None:
                    df.loc[m, 'AgeGroup'] = bexpr
        if df['AgeGroup'].isna().any():
            df['AgeGroup'] = df['AgeGroup'].fillna("Other Ages")
        return df

    df['AgeGroup'] = "All Ages"
    return df

# ------------------------------------------------------------------------
# Multi-dimension aggregator (Age/Race/Ethnicity/Sex/County any combo)
def aggregate_multi(
    df_source: pd.DataFrame,
    grouping_vars: List[str],
    year_str: str,
    county_label: str,
    counties_map: Dict[str, int],
    agegroup_for_backend: Optional[str],
    custom_ranges: List[Tuple[int, int]],
    agegroup_map_implicit: Dict[str, List[str]]
) -> pd.DataFrame:

    # Empty base frame
    def _empty():
        base = (["County"] if "County" not in grouping_vars else [])
        return pd.DataFrame(columns=base + grouping_vars + ["Count", "Percent", "Year"])

    if df_source is None or df_source.empty:
        return _empty()

    total_population = df_source["Count"].sum()
    if total_population == 0:
        return _empty()

    include_age = "Age" in grouping_vars
    df = attach_agegroup_column(
        df_source, include_age, agegroup_for_backend, custom_ranges, agegroup_map_implicit
    )

    # Build real group fields (replace Age→AgeGroup; keep County as 'County' for grouping)
    group_fields: List[str] = []
    for g in grouping_vars:
        group_fields.append("AgeGroup" if g == "Age" else g)

    # Group and sum
    grouped = df.groupby(group_fields, dropna=False)["Count"].sum().reset_index()

    # Map race codes → labels
    if "Race" in grouped.columns:
        grouped["Race"] = grouped["Race"].map(RACE_CODE_TO_DISPLAY).fillna(grouped["Race"])

    # Percent vs total filtered pop for that block (year × county_list)
    grouped["Year"] = str(year_str)
    grouped["Percent"] = (grouped["Count"] / total_population * 100.0).round(1)

    # If NOT grouping by County → add friendly label column
    if "County" not in grouping_vars:
        grouped.insert(0, "County", county_label)
        grouped = ensure_county_names(grouped, counties_map)
    else:
        # If grouping by County, rename code column and add name
        if "County" in grouped.columns:
            grouped.rename(columns={"County": "County Code"}, inplace=True)
        grouped = ensure_county_names(grouped, counties_map)

        # Also update group_fields to reflect the rename for downstream column ordering
        group_fields = ["County Code" if g == "County" else g for g in group_fields]

    # Reorder columns ONLY by existing ones to avoid KeyErrors
    existing = list(grouped.columns)
    col_order: List[str] = []

    # Label column (present only when not grouped by County)
    if "County" in existing:
        col_order.append("County")

    # Code + Name (present only when grouped by County)
    if "County Code" in existing:
        col_order += ["County Code"]
        if "County Name" in existing:
            col_order += ["County Name"]

    # Add group fields in a stable order if they exist
    for c in group_fields:
        if c in existing and c not in col_order:
            col_order.append(c)

    # Metrics at the end
    for c in ["Count", "Percent", "Year"]:
        if c in existing:
            col_order.append(c)

    grouped = grouped[col_order]
    return grouped

# ------------------------------------------------------------------------
# Main
def main():
    st.markdown('<div class="main-header">🏛️ Illinois Population Data Explorer</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-title">Analyze demographic trends across Illinois counties from 2000–2024</div>', unsafe_allow_html=True)

    # State
    if "report_df" not in st.session_state:
        st.session_state.report_df = pd.DataFrame()
    if "selected_filters" not in st.session_state:
        st.session_state.selected_filters = {}

    debug_mode = st.sidebar.checkbox("Debug Mode", value=False)

    # Load form control data
    (years_list,
     agegroups_list_raw,
     races_list_raw,
     counties_map,
     agegroup_map_explicit,
     agegroup_map_implicit) = frontend_data_loader.load_form_control_data(FORM_CONTROL_PATH)

    st.markdown("## 📊 Data Overview")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f"""<div class="metric-card"><div class="metric-value">{len(years_list)}</div><div class="metric-label">Years Available</div></div>""", unsafe_allow_html=True)
    with c2:
        st.markdown(f"""<div class="metric-card"><div class="metric-value">{len(counties_map)}</div><div class="metric-label">Illinois Counties</div></div>""", unsafe_allow_html=True)
    with c3:
        st.markdown(f"""<div class="metric-card"><div class="metric-value">{len(races_list_raw)}</div><div class="metric-label">Race Categories</div></div>""", unsafe_allow_html=True)
    with c4:
        st.markdown(f"""<div class="metric-card"><div class="metric-value">{len(agegroups_list_raw)}</div><div class="metric-label">Age Groups</div></div>""", unsafe_allow_html=True)

    # Tabs
    st.markdown('<div class="section-header">🔍 Query Builder</div>', unsafe_allow_html=True)
    t_geo, t_demo, t_age = st.tabs(["📍 Geography & Time", "👥 Demographics", "📋 Age Settings"])

    with t_geo:
        g1, g2 = st.columns(2)
        with g1:
            selected_years = st.multiselect(
                "Select Year(s):",
                options=years_list,
                default=years_list[-1:] if years_list else [],
                help="Choose one or more years to analyze."
            )
        with g2:
            all_counties = ["All"] + sorted(counties_map.keys())
            selected_counties = st.multiselect(
                "Select Counties:",
                options=all_counties,
                default=["All"],
                help="Choose counties to include. 'All' includes all Illinois counties."
            )
            if "All" in selected_counties and len(selected_counties) > 1:
                st.info("Using 'All' counties (specific selections ignored).")
                selected_counties = ["All"]

    with t_demo:
        d1, d2 = st.columns(2)
        with d1:
            race_opts = ["All"]
            for rcode in sorted(races_list_raw):
                if rcode == "All":
                    continue
                race_opts.append(RACE_CODE_TO_DISPLAY.get(rcode, rcode))
            selected_race_display = st.selectbox(
                "Race Filter:",
                race_opts,
                index=0,
                help="Filter data by race category (applies before grouping)."
            )
            selected_sex = st.radio("Sex:", ["All", "Male", "Female"], horizontal=True)
        with d2:
            selected_ethnicity = st.radio("Ethnicity:", ["All", "Hispanic", "Not Hispanic"], horizontal=True)
            region_options = ["None", "Collar Counties", "Urban Counties", "Rural Counties"]
            selected_region = st.selectbox("Region:", region_options, index=0)

    with t_age:
        a1, a2 = st.columns(2)
        with a1:
            AGEGROUP_DISPLAY_TO_CODE = {
                "All": "All",
                "18-Bracket": "agegroup13",
                "6-Bracket": "agegroup14",
                "2-Bracket": "agegroup15"
            }
            selected_agegroup_display = st.selectbox(
                "Age Group:",
                list(AGEGROUP_DISPLAY_TO_CODE.keys()),
                index=0,
                help="Choose predefined age bracket grouping."
            )
            if selected_agegroup_display != "All":
                code = AGEGROUP_DISPLAY_TO_CODE[selected_agegroup_display]
                br = agegroup_map_implicit.get(code, [])
                if br:
                    st.write("**Age Brackets:** ", ", ".join(br))
        with a2:
            enable_custom_ranges = st.checkbox(
                "Enable custom age ranges",
                value=False,
                help=("Age codes: 1=0–4, 2=5–9, 3=10–14, 4=15–19, 5=20–24, 6=25–29, "
                      "7=30–34, 8=35–39, 9=40–44, 10=45–49, 11=50–54, 12=55–59, "
                      "13=60–64, 14=65–69, 15=70–74, 16=75–79, 17=80–84, 18=80+. "
                      "See Documentation Codebooks under 'Census Data Links' for details.")
            )
            st.caption("When enabled, these custom ranges override the Age Group selection.")
            custom_ranges: List[Tuple[int, int]] = []
            if enable_custom_ranges:
                rc = st.columns(3)
                with rc[0]:
                    if st.checkbox("Range 1", key="r1"):
                        mn1 = st.number_input("Min 1 (1–18)", 1, 18, 1, key="mn1")
                        mx1 = st.number_input("Max 1 (1–18)", 1, 18, 5, key="mx1")
                        if mn1 <= mx1:
                            custom_ranges.append((int(mn1), int(mx1)))
                with rc[1]:
                    if st.checkbox("Range 2", key="r2"):
                        mn2 = st.number_input("Min 2 (1–18)", 1, 18, 6, key="mn2")
                        mx2 = st.number_input("Max 2 (1–18)", 1, 18, 10, key="mx2")
                        if mn2 <= mx2:
                            custom_ranges.append((int(mn2), int(mx2)))
                with rc[2]:
                    if st.checkbox("Range 3", key="r3"):
                        mn3 = st.number_input("Min 3 (1–18)", 1, 18, 11, key="mn3")
                        mx3 = st.number_input("Max 3 (1–18)", 1, 18, 15, key="mx3")
                        if mn3 <= mx3:
                            custom_ranges.append((int(mn3), int(mx3)))

    # Output config
    st.markdown('<div class="section-header">📈 Output Configuration</div>', unsafe_allow_html=True)
    oc1, oc2 = st.columns(2)
    with oc1:
        grouping_vars = st.multiselect(
            "Group Results By:",
            ["Age", "Race", "Ethnicity", "Sex", "County"],
            default=[],
            help="Select one or more columns (e.g., Race + Sex)."
        )
    with oc2:
        include_breakdown = st.checkbox(
            "Include Individual County Breakdowns",
            value=True,
            help="Show a separate table for each selected county in addition to the combined results."
        )
        if "County" in grouping_vars and include_breakdown:
            st.info("When grouping by County, individual county breakdowns are redundant and will be skipped.")
            include_breakdown = False

    # Buttons
    st.markdown("---")
    go = st.button("🚀 Generate Report", use_container_width=True, type="primary")
    if st.button("🗑️ Clear Results", use_container_width=True):
        st.session_state.report_df = pd.DataFrame()
        st.session_state.selected_filters = {}
        st.rerun()

    # Generate
    if go:
        if not selected_years:
            st.warning("⚠️ Please select at least one year.")
            st.stop()
        if not selected_counties:
            st.warning("⚠️ Please select at least one county.")
            st.stop()

        selected_race_code = "All" if selected_race_display == "All" else RACE_DISPLAY_TO_CODE.get(selected_race_display, selected_race_display)
        agegroup_for_backend = None if selected_agegroup_display == "All" else {"All": None, "18-Bracket": "agegroup13", "6-Bracket": "agegroup14", "2-Bracket": "agegroup15"}[selected_agegroup_display]

        st.session_state.selected_filters = {
            "years": [str(y) for y in selected_years],
            "counties": selected_counties,
            "race": selected_race_display,
            "ethnicity": selected_ethnicity,
            "sex": selected_sex,
            "region": selected_region,
            "age_group": "Custom Ranges" if enable_custom_ranges else selected_agegroup_display,
            "group_by": grouping_vars
        }

        with st.spinner("🔄 Processing data..."):
            def build_block(county_list: List[str], county_label: str) -> pd.DataFrame:
                frames = []
                for year in selected_years:
                    df_src = backend_main_processing.process_population_data(
                        data_folder=DATA_FOLDER,
                        agegroup_map_explicit=frontend_data_loader.load_form_control_data(FORM_CONTROL_PATH)[4],  # not used here but kept for API parity
                        counties_map=counties_map,
                        selected_years=[year],
                        selected_counties=county_list,
                        selected_race=selected_race_code,
                        selected_ethnicity=selected_ethnicity,
                        selected_sex=selected_sex,
                        selected_region=selected_region,
                        selected_agegroup=agegroup_for_backend,
                        custom_age_ranges=custom_ranges if enable_custom_ranges else []
                    )
                    if debug_mode:
                        debug_data_processing(df_src, f"{county_label} · {year}")
                    block = aggregate_multi(
                        df_source=df_src,
                        grouping_vars=grouping_vars,
                        year_str=str(year),
                        county_label=county_label,
                        counties_map=counties_map,
                        agegroup_for_backend=agegroup_for_backend,
                        custom_ranges=custom_ranges if enable_custom_ranges else [],
                        agegroup_map_implicit=frontend_data_loader.load_form_control_data(FORM_CONTROL_PATH)[5]
                    )
                    if not block.empty:
                        frames.append(block)
                return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

            all_frames: List[pd.DataFrame] = []

            if "All" in selected_counties:
                combined = build_block(["All"], "All Counties")
            else:
                combined = build_block(selected_counties, "Selected Counties")
            if not combined.empty:
                all_frames.append(combined)

            if include_breakdown and "All" not in selected_counties:
                for cty in selected_counties:
                    cdf = build_block([cty], cty)
                    if not cdf.empty:
                        all_frames.append(cdf)

            st.session_state.report_df = pd.concat(all_frames, ignore_index=True) if all_frames else pd.DataFrame()
            st.session_state.report_df = ensure_county_names(st.session_state.report_df, counties_map)

        # Display
        if st.session_state.report_df.empty:
            st.info("📭 No data found for the selected filters.")
        else:
            st.success("✅ Report generated successfully!")
            st.markdown("### 📋 Results")
            st.dataframe(st.session_state.report_df, use_container_width=True)

            csv_with_meta = add_metadata_to_csv(st.session_state.report_df, st.session_state.selected_filters)
            st.download_button("📥 Download CSV", data=csv_with_meta, file_name="illinois_population_data.csv", mime="text/csv")

    # Existing results
    elif not st.session_state.report_df.empty:
        st.markdown("### 📋 Existing Results")
        st.dataframe(st.session_state.report_df, use_container_width=True)
        csv_with_meta = add_metadata_to_csv(st.session_state.report_df, st.session_state.selected_filters)
        st.download_button("📥 Download CSV", data=csv_with_meta, file_name="illinois_population_data.csv", mime="text/csv")

    display_census_links()

    st.markdown("---")
    st.markdown(
        "<div style='text-align: center; color: #666;'>"
        "Illinois Population Data Explorer • U.S. Census Bureau Data • 2000–2024"
        "</div>",
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()
