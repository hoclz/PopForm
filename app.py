import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt  # (kept if you add charts later)
import io
import base64
import os
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
# Custom CSS for Illinois-themed design with improved title styling
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
    .census-links {
        background: #e3f2fd;
        padding: 20px;
        border-radius: 10px;
        border: 2px solid #90caf9;
        margin: 20px 0;
    }
</style>
""", unsafe_allow_html=True)

# ------------------------------------------------------------------------
# Import your existing backend code
try:
    import backend_main_processing
    import frontend_data_loader
    import frontend_bracket_utils
except ImportError as e:
    st.error(f"Error importing backend modules: {e}")
    st.info("Please ensure all backend modules are available")

# ------------------------------------------------------------------------
# Path configurations
DATA_FOLDER = "./data"
FORM_CONTROL_PATH = "./form_control_UI_data.csv"

# ------------------------------------------------------------------------
# Race and bracket definitions for Illinois
RACE_DISPLAY_TO_CODE = {
    "Two or More Races": "TOM",
    "American Indian and Alaska Native": "AIAN",
    "Black or African American": "Black",
    "White": "White",
    "Native Hawaiian and Other Pacific Islander": "NHOPI",
    "Asian": "Asian"
}
RACE_CODE_TO_DISPLAY = {v: k for k, v in RACE_DISPLAY_TO_CODE.items()}

# Age code → label lookup (codes are 1..18 in the data)
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
    """Combine age codes into a human-friendly bracket label (e.g., 1..5 → '0-24')."""
    codes = sorted(set(codes))
    if not codes:
        return ""
    low_vals, high_vals = [], []
    for c in codes:
        bracket_str = CODE_TO_BRACKET.get(c, "")
        if "-" in bracket_str:
            parts = bracket_str.split("-")
            try:
                start = int(parts[0])
                end = int(parts[1].replace("+", "")) if parts[1].endswith("+") else int(parts[1])
                low_vals.append(start)
                high_vals.append(end)
            except:
                pass
        elif bracket_str.endswith("+"):
            try:
                start = int(bracket_str.replace("+", ""))
                low_vals.append(start)
                high_vals.append(999)
            except:
                pass
    if not low_vals or not high_vals:
        return "-".join(str(c) for c in codes)
    overall_low = min(low_vals)
    overall_high = max(high_vals)
    return f"{overall_low}+" if overall_high >= 999 else f"{overall_low}-{overall_high}"

# ------------------------------------------------------------------------
# Utility: ensure county names are properly displayed
def ensure_county_names(df: pd.DataFrame, counties_map: Dict[str, int]) -> pd.DataFrame:
    """Ensure county codes are converted to county names in the output."""
    if df is None or df.empty:
        return df

    COUNTY_ID_TO_NAME = {v: k for k, v in counties_map.items()}

    # Handle grouped "County" column if it's codes
    if 'County' in df.columns:
        # Try to map int codes to names
        def _map_county(v):
            try:
                if pd.isna(v):
                    return v
                if isinstance(v, (int, np.integer)) and v in COUNTY_ID_TO_NAME:
                    return COUNTY_ID_TO_NAME[v]
                if isinstance(v, str) and v.isdigit() and int(v) in COUNTY_ID_TO_NAME:
                    return COUNTY_ID_TO_NAME[int(v)]
                # If already a name that exists in map keys, leave as-is
                return v
            except:
                return v
        df['County'] = df['County'].apply(_map_county)

    # Handle "County Code" -> "County Name"
    if 'County Code' in df.columns and 'County Name' not in df.columns:
        df['County Name'] = df['County Code'].map(COUNTY_ID_TO_NAME).fillna(df['County Code'])

    return df

# ------------------------------------------------------------------------
# Debug helper
def debug_data_processing(df_source: pd.DataFrame, tag: str):
    if df_source is None or df_source.empty:
        st.warning(f"No data after filtering ({tag})")
        return
    st.write(f"**Debug Info — {tag}**")
    st.write(f"Rows: {len(df_source)} | Total population: {df_source['Count'].sum():,}")
    for col in ['Age', 'Race', 'County', 'Ethnicity', 'Sex']:
        if col in df_source.columns:
            nunique = df_source[col].nunique(dropna=True)
            st.write(f"• {col}: {nunique} unique")

# ------------------------------------------------------------------------
# Census Data Links
def display_census_links():
    census_docs = [
        {"year": 2024, "period": "April 1, 2020 to July 1, 2024", "link": "https://www2.census.gov/programs-surveys/popest/technical-documentation/file-layouts/2020-2024/CC-EST2024-ALLDATA.pdf"},
        {"year": 2023, "period": "April 1, 2020 to July 1, 2023", "link": "https://www2.census.gov/programs-surveys/popest/technical-documentation/file-layouts/2020-2023/CC-EST2023-ALLDATA.pdf"},
        {"year": 2022, "period": "April 1, 2020 to July 1, 2022", "link": "https://www2.census.gov/programs-surveys/popest/technical-documentation/file-layouts/2020-2022/cc-est2022-alldata.pdf"},
        {"year": 2021, "period": "April 1, 2020 to July 1, 2021", "link": "https://www2.census.gov/programs-surveys/popest/technical-documentation/file-layouts/2020-2021/cc-est2021-alldata.pdf"},
        {"year": 2020, "period": "April 1, 2010 to July 1, 2020", "link": "https://www2.census.gov/programs-surveys/popest/technical-documentation/file-layouts/2010-2020/cc-est2020-alldata.pdf"},
        {"year": 2019, "period": "April 1, 2010 to July 1, 2019", "link": "https://www2.census.gov/programs-surveys/popest/technical-documentation/file-layouts/2010-2019/cc-est2019-alldata.pdf"},
        {"year": 2018, "period": "April 1, 2010 to July 1, 2018", "link": "https://www2.census.gov/programs-surveys/popest/technical-documentation/file-layouts/2010-2018/cc-est2018-alldata.pdf"},
        {"year": 2017, "period": "April 1, 2010 to July 1, 2017", "link": "https://www2.census.gov/programs-surveys/popest/technical-documentation/file-layouts/2010-2017/cc-est2017-alldata.pdf"},
        {"year": 2016, "period": "April 1, 2010 to July 1, 2016", "link": "https://www2.census.gov/programs-surveys/popest/technical-documentation/file-layouts/2010-2016/cc-est2016-alldata.pdf"},
        {"year": 2015, "period": "April 1, 2010 to July 1, 2015", "link": "https://www2.census.gov/programs-surveys/popest/technical-documentation/file-layouts/2010-2015/cc-est2015-alldata.pdf"},
        {"year": 2014, "period": "April 1, 2010 to July 1, 2014", "link": "https://www2.census.gov/programs-surveys/popest/technical-documentation/file-layouts/2010-2014/cc-est2014-alldata.pdf"},
        {"year": 2013, "period": "April 1, 2010 to July 1, 2013", "link": "https://www2.census.gov/programs-surveys/popest/technical-documentation/file-layouts/2010-2013/cc-est2013-alldata.pdf"},
        {"year": 2012, "period": "April 1, 2010 to July 1, 2012", "link": "https://www2.census.gov/programs-surveys/popest/technical-documentation/file-layouts/2010-2012/cc-est2012-alldata.pdf"},
        {"year": 2011, "period": "April 1, 2010 to July 1, 2011", "link": "https://www2.census.gov/programs-surveys/popest/technical-documentation/file-layouts/2010-2011/cc-est2011-alldata.pdf"},
        {"year": 2010, "period": "April 1, 2000 to July 1, 2010", "link": "https://www2.census.gov/programs-surveys/popest/technical-documentation/file-layouts/2000-2010/cc-est2010-alldata.pdf"},
    ]

    codebooks_md = "**Documentation Codebooks**:\n"
    codebooks_md += "- [File Layouts Main Page](https://www2.census.gov/programs-surveys/popest/technical-documentation/file-layouts/)\n"
    for doc in census_docs:
        codebooks_md += f"- [Vintage {doc['year']} ({doc['period']})]({doc['link']})\n"
    codebooks_md += "- [Methodology Overview](https://www.census.gov/programs-surveys/popest/technical-documentation/methodology.html)\n"
    codebooks_md += "- [Modified Race Data](https://www.census.gov/programs-surveys/popest/technical-documentation/research/modified-race-data.html)\n"

    with st.expander("Census Data Links", expanded=False):
        st.markdown("""
        **Important Links**:
        - [Census Datasets](https://www2.census.gov/programs-surveys/popest/datasets/)
        - [2000-2010 Intercensal County](https://www2.census.gov/programs-surveys/popest/datasets/2000-2010/intercensal/county/)
        - [2010-2020 County ASRH](https://www2.census.gov/programs-surveys/popest/datasets/2010-2020/counties/asrh/)
        - [2020-2023 County ASRH](https://www2.census.gov/programs-surveys/popest/datasets/2020-2023/counties/asrh/)
        - [2020-2024 County ASRH](https://www2.census.gov/programs-surveys/popest/datasets/2020-2024/counties/asrh/)
        - [RELEASE SCHEDULE](https://www.census.gov/programs-surveys/popest/about/schedule.html)
        """)
        st.markdown("---")
        st.markdown(codebooks_md)

# ------------------------------------------------------------------------
# CSV download helper with metadata
def add_metadata_to_csv(df: pd.DataFrame, selected_filters: Dict) -> str:
    metadata_lines = [
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
    metadata = "\n".join(metadata_lines) + "\n"
    csv_data = df.to_csv(index=False)
    return metadata + csv_data

# ------------------------------------------------------------------------
# AGEGROUP column builder for multi-dim groupby
def attach_agegroup_column(
    df: pd.DataFrame,
    include_age: bool,
    agegroup_for_backend: Optional[str],
    custom_ranges: List[Tuple[int, int]],
    agegroup_map_implicit: Dict[str, List[str]]
) -> pd.DataFrame:
    """
    Adds an 'AgeGroup' column to df when include_age is True.
    - If custom_ranges are provided, creates brackets from those ranges and adds an
      'Other Ages' bucket for uncovered ages so percentages can sum to 100%.
    - Else if agegroup_for_backend is defined, uses the implicit brackets list.
    - Else sets AgeGroup = 'All Ages'.
    """
    if not include_age:
        return df

    df = df.copy()

    # Custom ranges → explicit labels
    if custom_ranges:
        df['AgeGroup'] = np.nan
        covered = np.zeros(len(df), dtype=bool)

        for (mn, mx) in custom_ranges:
            mn_i = max(1, int(mn))
            mx_i = min(18, int(mx))
            if mn_i > mx_i:
                continue
            codes = list(range(mn_i, mx_i + 1))
            label = combine_codes_to_label(codes)
            mask = df['Age'].between(mn_i, mx_i)
            df.loc[mask, 'AgeGroup'] = label
            covered = covered | mask.to_numpy()

        # Add "Other Ages" so totals sum to 100 when partial coverage
        if (~covered).any():
            df.loc[~covered, 'AgeGroup'] = "Other Ages"

        return df

    # Implicit bracket set from map (e.g., 18-bracket, 6-bracket, etc.)
    if agegroup_for_backend:
        df['AgeGroup'] = np.nan
        bracket_exprs = agegroup_map_implicit.get(agegroup_for_backend, [])
        for bexpr in bracket_exprs:
            try:
                mask = frontend_bracket_utils.parse_implicit_bracket(df, bexpr)
                df.loc[mask, 'AgeGroup'] = bexpr  # Use the expression text as the label
            except Exception:
                # Fallback: try to parse simple forms like "1-4" or "80+"
                bexpr = str(bexpr).strip()
                m = None
                if "-" in bexpr:
                    a, b = bexpr.split("-")
                    a, b = int(a), int(b)
                    m = df['Age'].between(a, b)
                elif bexpr.endswith("+") and bexpr[:-1].isdigit():
                    a = int(bexpr[:-1])
                    m = df['Age'] >= a
                if m is not None:
                    df.loc[m, 'AgeGroup'] = bexpr

        # In most official bracket sets, coverage is complete; any NaNs → "Other Ages"
        if df['AgeGroup'].isna().any():
            df['AgeGroup'] = df['AgeGroup'].fillna("Other Ages")
        return df

    # No specific brackets selected → single bucket
    df['AgeGroup'] = "All Ages"
    return df

# ------------------------------------------------------------------------
# Multi-dimension aggregator (supports multi-select grouping)
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
    """
    Aggregates by any combination of columns in grouping_vars.
    - If 'Age' is included, uses AgeGroup computed from selected brackets/ranges.
    - Percent is computed against the total population of df_source for that year
      (ensures math adds up to ~100% across the full set of groups).
    - Inserts a constant 'County' label column unless 'County' itself is part of grouping_vars.
    """
    if df_source is None or df_source.empty:
        base_cols = (['County'] if 'County' not in grouping_vars else [])
        return pd.DataFrame(columns=base_cols + grouping_vars + ["Count", "Percent", "Year"])

    total_population = df_source["Count"].sum()
    if total_population == 0:
        base_cols = (['County'] if 'County' not in grouping_vars else [])
        return pd.DataFrame(columns=base_cols + grouping_vars + ["Count", "Percent", "Year"])

    include_age = "Age" in grouping_vars
    df = attach_agegroup_column(
        df_source, include_age, agegroup_for_backend, custom_ranges, agegroup_map_implicit
    )

    # Replace "Age" with "AgeGroup" for grouping
    group_fields = []
    for g in grouping_vars:
        if g == "Age":
            group_fields.append("AgeGroup")
        else:
            group_fields.append(g)

    # Group and sum
    grouped = df.groupby(group_fields, dropna=False)["Count"].sum().reset_index()

    # Map Race codes → labels
    if "Race" in grouped.columns:
        grouped["Race"] = grouped["Race"].map(RACE_CODE_TO_DISPLAY).fillna(grouped["Race"])

    # Add Year and Percent (denominator = all records in df_source for that year & county list)
    grouped["Year"] = str(year_str)
    grouped["Percent"] = (grouped["Count"] / total_population * 100.0).round(1)

    # When County NOT in grouping, add a County label column (like original behavior)
    if "County" not in grouping_vars:
        grouped.insert(0, "County", county_label)
        # Ensure name formatting for label column, too
        grouped = ensure_county_names(grouped, counties_map)
    else:
        # Add "County Name" when user groups by County (nice UX)
        grouped = grouped.rename(columns={"County": "County Code"})
        grouped["County Name"] = None
        grouped = ensure_county_names(grouped, counties_map)

    # Order columns consistently (County first if present, then groups, then Count/Percent/Year)
    col_order = []
    if "County" in grouped.columns:
        col_order.append("County")
    if "County Code" in grouped.columns:
        col_order.extend(["County Code", "County Name"])
    col_order.extend([c for c in group_fields if c not in col_order])
    col_order.extend(["Count", "Percent", "Year"])
    grouped = grouped[col_order]

    return grouped

# ------------------------------------------------------------------------
# Main Application
def main():
    # Header
    st.markdown('<div class="main-header">🏛️ Illinois Population Data Explorer</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-title">Analyze demographic trends across Illinois counties from 2000–2024</div>', unsafe_allow_html=True)

    # State
    if 'report_df' not in st.session_state:
        st.session_state.report_df = pd.DataFrame()
    if 'selected_filters' not in st.session_state:
        st.session_state.selected_filters = {}

    debug_mode = st.sidebar.checkbox("Debug Mode", value=False)

    # Load form control data
    try:
        (years_list,
         agegroups_list_raw,
         races_list_raw,
         counties_map,
         agegroup_map_explicit,
         agegroup_map_implicit) = frontend_data_loader.load_form_control_data(FORM_CONTROL_PATH)

        if years_list:
            st.sidebar.success("✅ Data loaded successfully!")
        else:
            st.sidebar.warning("⚠️ No data found in form control file.")
    except Exception as e:
        st.sidebar.error(f"❌ Error loading data: {e}")
        return

    COUNTY_NAME_TO_ID = counties_map
    COUNTY_ID_TO_NAME = {v: k for k, v in COUNTY_NAME_TO_ID.items()}

    # Quick Stats
    st.markdown("## 📊 Data Overview")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{len(years_list)}</div>
            <div class="metric-label">Years Available</div>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{len(counties_map)}</div>
            <div class="metric-label">Illinois Counties</div>
        </div>
        """, unsafe_allow_html=True)
    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{len(races_list_raw)}</div>
            <div class="metric-label">Race Categories</div>
        </div>
        """, unsafe_allow_html=True)
    with col4:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{len(agegroups_list_raw)}</div>
            <div class="metric-label">Age Groups</div>
        </div>
        """, unsafe_allow_html=True)

    # Query Builder
    st.markdown('<div class="section-header">🔍 Query Builder</div>', unsafe_allow_html=True)
    config_tab1, config_tab2, config_tab3 = st.tabs(["📍 Geography & Time", "👥 Demographics", "📋 Age Settings"])

    # ---------------- Geography & Time
    with config_tab1:
        c1, c2 = st.columns(2)
        with c1:
            selected_years = st.multiselect(
                "Select Year(s):",
                options=years_list,
                default=years_list[-1:] if years_list else [],
                help="Choose one or more years to analyze."
            )
        with c2:
            all_counties = ["All"] + sorted(counties_map.keys())
            selected_counties = st.multiselect(
                "Select Counties:",
                options=all_counties,
                default=["All"],
                help="Choose counties to include. 'All' includes all Illinois counties."
            )
            # Normalize "All" selection (don't mix with specific counties)
            if "All" in selected_counties and len(selected_counties) > 1:
                st.info("Using 'All' counties (specific selections ignored).")
                selected_counties = ["All"]

    # ---------------- Demographics
    with config_tab2:
        c1, c2 = st.columns(2)
        with c1:
            # Build race filter list
            race_filter_list = ["All"]
            for rcode in sorted(races_list_raw):
                if rcode == "All":
                    continue
                friendly_name = RACE_CODE_TO_DISPLAY.get(rcode, rcode)
                if friendly_name not in race_filter_list:
                    race_filter_list.append(friendly_name)

            selected_race_display = st.selectbox(
                "Race Filter:",
                race_filter_list,
                index=0,
                help="Filter data by race category (applies before grouping)."
            )

            selected_sex = st.radio(
                "Sex:",
                ["All", "Male", "Female"],
                horizontal=True
            )
        with c2:
            selected_ethnicity = st.radio(
                "Ethnicity:",
                ["All", "Hispanic", "Not Hispanic"],
                horizontal=True
            )
            region_options = ["None", "Collar Counties", "Urban Counties", "Rural Counties"]
            selected_region = st.selectbox("Region:", region_options, index=0)

    # ---------------- Age Settings
    with config_tab3:
        c1, c2 = st.columns(2)
        with c1:
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
                agegroup_code = AGEGROUP_DISPLAY_TO_CODE.get(selected_agegroup_display)
                brackets_implicit = agegroup_map_implicit.get(agegroup_code, [])
                if brackets_implicit:
                    st.write("**Age Brackets:** ", ", ".join(brackets_implicit))
        with c2:
            enable_custom_ranges = st.checkbox(
                "Enable custom age ranges",
                value=False,
                help="Age codes: 1=0–4, 2=5–9, 3=10–14, 4=15–19, 5=20–24, 6=25–29, "
                     "7=30–34, 8=35–39, 9=40–44, 10=45–49, 11=50–54, 12=55–59, "
                     "13=60–64, 14=65–69, 15=70–74, 16=75–79, 17=80–84, 18=80+. "
                     "See Documentation Codebooks under 'Census Data Links' for details."
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

    # ---------------- Grouping (multi-select)
    st.markdown('<div class="section-header">📈 Output Configuration</div>', unsafe_allow_html=True)
    oc1, oc2 = st.columns(2)
    with oc1:
        grouping_vars = st.multiselect(
            "Group Results By:",
            ["Age", "Race", "Ethnicity", "Sex", "County"],
            default=[],  # empty = totals only
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

    # ---------------- Buttons
    st.markdown("---")
    go = st.button("🚀 Generate Report", use_container_width=True, type="primary")
    clear = st.button("🗑️ Clear Results", use_container_width=True)

    if clear:
        st.session_state.report_df = pd.DataFrame()
        st.session_state.selected_filters = {}
        st.rerun()

    # ---------------- Generate
    if go:
        if not selected_years:
            st.warning("⚠️ Please select at least one year.")
            st.stop()
        if not selected_counties:
            st.warning("⚠️ Please select at least one county.")
            st.stop()

        # Convert Race to code for backend filter
        selected_race_code = "All" if selected_race_display == "All" else RACE_DISPLAY_TO_CODE.get(selected_race_display, selected_race_display)
        # Age bracket selection for backend
        agegroup_for_backend = None if selected_agegroup_display == "All" else AGEGROUP_DISPLAY_TO_CODE[selected_agegroup_display]

        st.session_state.selected_filters = {
            "years": [str(y) for y in selected_years],
            "counties": selected_counties,
            "race": selected_race_display,
            "ethnicity": selected_ethnicity,
            "sex": selected_sex,
            "region": selected_region,
            "age_group": selected_agegroup_display if not enable_custom_ranges else "Custom Ranges",
            "group_by": grouping_vars
        }

        with st.spinner("🔄 Processing data..."):
            try:
                def build_block_for(county_list: List[str], county_label: str) -> pd.DataFrame:
                    frames = []
                    for year in selected_years:
                        df_src = backend_main_processing.process_population_data(
                            data_folder=DATA_FOLDER,
                            agegroup_map_explicit=agegroup_map_explicit,
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
                            agegroup_map_implicit=agegroup_map_implicit
                        )
                        if not block.empty:
                            frames.append(block)
                    if frames:
                        return pd.concat(frames, ignore_index=True)
                    return pd.DataFrame()

                all_frames = []

                # Combined selection (All or Selected Counties block)
                if "All" in selected_counties:
                    combined = build_block_for(["All"], "All Counties")
                else:
                    combined = build_block_for(selected_counties, "Selected Counties")
                if not combined.empty:
                    all_frames.append(combined)

                # Individual county breakdowns (if requested and meaningful)
                if include_breakdown and "All" not in selected_counties:
                    for cty in selected_counties:
                        cdf = build_block_for([cty], cty)
                        if not cdf.empty:
                            all_frames.append(cdf)

                # Final results
                if all_frames:
                    final_df = pd.concat(all_frames, ignore_index=True)
                    final_df = ensure_county_names(final_df, counties_map)
                    st.session_state.report_df = final_df
                else:
                    st.session_state.report_df = pd.DataFrame()

            except Exception as e:
                st.error(f"❌ Error generating report: {e}")

        # ---------------- Display Results
        if st.session_state.report_df.empty:
            st.info("📭 No data found for the selected filters.")
        else:
            st.success("✅ Report generated successfully!")
            total_population = int(
                round(st.session_state.report_df.groupby("Year")["Count"].sum().mean())
            ) if "Year" in st.session_state.report_df.columns and not st.session_state.report_df.empty else st.session_state.report_df["Count"].sum()
            st.metric("Total Population in Report (approx. per year)", f"{total_population:,}")

            st.markdown("### 📋 Results")
            st.dataframe(st.session_state.report_df, use_container_width=True)

            csv_with_metadata = add_metadata_to_csv(st.session_state.report_df, st.session_state.selected_filters)
            st.download_button(
                label="📥 Download CSV",
                data=csv_with_metadata,
                file_name="illinois_population_data.csv",
                mime="text/csv",
            )

    # Existing results area
    elif not st.session_state.report_df.empty:
        st.markdown("### 📋 Existing Results")
        st.dataframe(st.session_state.report_df, use_container_width=True)
        csv_with_metadata = add_metadata_to_csv(st.session_state.report_df, st.session_state.selected_filters)
        st.download_button(
            label="📥 Download CSV",
            data=csv_with_metadata,
            file_name="illinois_population_data.csv",
            mime="text/csv",
        )

    # Display Census Links (closed by default)
    display_census_links()

    # Footer
    st.markdown("---")
    st.markdown(
        "<div style='text-align: center; color: #666;'>"
        "Illinois Population Data Explorer • U.S. Census Bureau Data • 2000–2024"
        "</div>",
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()
