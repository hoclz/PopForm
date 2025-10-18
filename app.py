import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import io
import base64
import os
from datetime import datetime

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

def combine_codes_to_label(codes: list[int]) -> str:
    """Combine age codes into bracket labels"""
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
                end = int(parts[1].replace("+","")) if parts[1].endswith("+") else int(parts[1])
                low_vals.append(start)
                high_vals.append(end)
            except:
                pass
        elif bracket_str.endswith("+"):
            try:
                start = int(bracket_str.replace("+",""))
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
# CORRECTED Data aggregation functions
def aggregate_age_with_brackets(
    df_source: pd.DataFrame,
    year_str: str,
    agegroup_for_backend: str | None,
    custom_ranges: list[tuple[int,int]],
    agegroup_display: str,
    agegroup_map_implicit: dict
) -> pd.DataFrame:
    """
    CORRECTED: Aggregates data by age brackets (or custom ranges)
    Fixed percentage calculation and total population handling
    """
    if df_source is None or df_source.empty:
        return pd.DataFrame(columns=["AgeGroup", "Count", "Percent", "Year"])
    
    # Calculate TOTAL population for percentage calculations
    # This should be the total of ALL filtered data, not just what's in brackets
    total_population = df_source["Count"].sum()
    
    # If no bracket selection & no custom ranges => entire population
    if agegroup_for_backend is None and not custom_ranges:
        return pd.DataFrame({
            "AgeGroup": ["All Ages"],
            "Count": [total_population],
            "Percent": [100.0],
            "Year": [year_str]
        })

    # If custom ranges
    if custom_ranges:
        rows = []
        for (mn, mx) in custom_ranges:
            code_list = list(range(mn, mx+1))
            bracket_label = combine_codes_to_label(code_list)
            mask = df_source["Age"].isin(code_list)
            sub_sum = df_source.loc[mask, "Count"].sum()
            rows.append((bracket_label, sub_sum))
        
        out_rows = []
        for (bexpr, cval) in rows:
            # Calculate percentage against TOTAL population, not sum of brackets
            pct = (cval / total_population * 100.0) if total_population > 0 else 0.0
            out_rows.append((bexpr, cval, round(pct, 1)))
        
        df_out = pd.DataFrame(out_rows, columns=["AgeGroup", "Count", "Percent"])
        df_out["Year"] = year_str
        return df_out

    # Otherwise, use the implicit bracket definitions from the map
    brackets_implicit = agegroup_map_implicit.get(agegroup_for_backend, [])
    if not brackets_implicit:
        return pd.DataFrame({
            "AgeGroup": [f"No bracket for {agegroup_display}"],
            "Count": [total_population],
            "Percent": [100.0],
            "Year": [year_str]
        })

    rows = []
    for bracket_expr in brackets_implicit:
        bracket_expr = bracket_expr.strip()
        mask = frontend_bracket_utils.parse_implicit_bracket(df_source, bracket_expr)
        sub_sum = df_source.loc[mask, "Count"].sum()
        rows.append((bracket_expr, sub_sum))

    out_rows = []
    for (bexpr, cval) in rows:
        # Calculate percentage against TOTAL population
        pct = (cval / total_population * 100.0) if total_population > 0 else 0.0
        out_rows.append((bexpr, cval, round(pct, 1)))

    df_out = pd.DataFrame(out_rows, columns=["AgeGroup", "Count", "Percent"])
    df_out["Year"] = year_str
    return df_out

def aggregate_by_field(
    df_source: pd.DataFrame,
    group_by: str,
    year_str: str,
    county_id_to_name: dict
) -> pd.DataFrame:
    """
    CORRECTED: Aggregates by Race, Ethnicity, Sex, or County
    Fixed percentage calculation to use total filtered population
    """
    if df_source is None or df_source.empty:
        if group_by == "County":
            return pd.DataFrame(columns=["County Code", "County Name", "Count", "Percent", "Year"])
        else:
            return pd.DataFrame(columns=[group_by, "Count", "Percent", "Year"])

    if group_by not in df_source.columns:
        if group_by == "County":
            return pd.DataFrame(columns=["County Code", "County Name", "Count", "Percent", "Year"])
        else:
            return pd.DataFrame(columns=[group_by, "Count", "Percent", "Year"])

    # Calculate total population for percentage base
    total_population = df_source["Count"].sum()
    
    grouped = df_source.groupby(group_by)["Count"].sum().reset_index()
    grouped["Percent"] = (grouped["Count"] / total_population * 100).round(1) if total_population > 0 else 0
    grouped["Year"] = year_str

    if group_by == "Race":
        grouped[group_by] = grouped[group_by].map(RACE_CODE_TO_DISPLAY).fillna(grouped[group_by])
        return grouped
    elif group_by == "County":
        grouped.rename(columns={group_by: "County Code"}, inplace=True)
        grouped["County Name"] = grouped["County Code"].map(county_id_to_name).fillna(grouped["County Code"])
        return grouped[["County Code", "County Name", "Count", "Percent", "Year"]]
    else:
        return grouped

# ------------------------------------------------------------------------
# Data validation and debugging function
def debug_data_processing(df_source, filters_applied):
    """Helper function to debug data processing"""
    if df_source is None or df_source.empty:
        st.warning("No data after filtering")
        return
    
    st.write(f"**Debug Info - {filters_applied}**")
    st.write(f"Total records: {len(df_source)}")
    st.write(f"Total population: {df_source['Count'].sum():,}")
    
    if "Age" in df_source.columns:
        st.write(f"Age range: {df_source['Age'].min()} to {df_source['Age'].max()}")
    
    if "Race" in df_source.columns:
        st.write(f"Races present: {df_source['Race'].unique()}")
    
    if "County" in df_source.columns:
        st.write(f"Counties present: {len(df_source['County'].unique())}")

# ------------------------------------------------------------------------
# Census Data Links Display Function with Documentation Codebooks
def display_census_links():
    """Display census data links in expander exactly like reference code, with added documentation codebooks."""
    # List of documentation codebooks (easy to update)
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

    # Build the codebooks markdown dynamically
    codebooks_md = "**Documentation Codebooks**:\n"
    codebooks_md += "- [File Layouts Main Page](https://www2.census.gov/programs-surveys/popest/technical-documentation/file-layouts/)\n"
    for doc in census_docs:
        codebooks_md += f"- [Vintage {doc['year']} ({doc['period']})]({doc['link']})\n"
    codebooks_md += "- [Methodology Overview](https://www.census.gov/programs-surveys/popest/technical-documentation/methodology.html)\n"
    codebooks_md += "- [Modified Race Data](https://www.census.gov/programs-surveys/popest/technical-documentation/research/modified-race-data.html)\n"

    with st.expander("Census Data Links", expanded=False):  # Changed to False to be closed by default
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
# Function to add metadata to CSV download
def add_metadata_to_csv(df, selected_filters):
    """Add metadata as comments at the beginning of the CSV file"""
    metadata_lines = [
        "# Illinois Population Data Explorer - Export",
        f"# Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"# Data Source: U.S. Census Bureau Population Estimates",
        f"# Years: {', '.join(selected_filters.get('years', []))}",
        f"# Counties: {', '.join(selected_filters.get('counties', []))}",
        f"# Race Filter: {selected_filters.get('race', 'All')}",
        f"# Ethnicity: {selected_filters.get('ethnicity', 'All')}",
        f"# Sex: {selected_filters.get('sex', 'All')}",
        f"# Region: {selected_filters.get('region', 'None')}",
        f"# Age Group: {selected_filters.get('age_group', 'All')}",
        f"# Group By: {selected_filters.get('group_by', 'None')}",
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
# Function to ensure county names are properly displayed - FIXED BASED ON OLD CODE
def ensure_county_names(df, counties_map):
    """Ensure county codes are converted to county names in the output"""
    if df is None or df.empty:
        return df
    
    # Create reverse mapping from code to name (EXACTLY like old code)
    COUNTY_ID_TO_NAME = {v: k for k, v in counties_map.items()}
    
    # Check if we have county code column that needs conversion
    if 'County Code' in df.columns and 'County Name' not in df.columns:
        df['County Name'] = df['County Code'].map(COUNTY_ID_TO_NAME).fillna(df['County Code'])
    
    # If we have a generic 'County' column with codes, convert to names
    if 'County' in df.columns:
        # Check if values are numeric codes or county names that need mapping
        for idx, county_val in df['County'].items():
            if county_val in COUNTY_ID_TO_NAME.values():  # Already a name
                continue
            elif str(county_val).isdigit() and int(county_val) in COUNTY_ID_TO_NAME:
                df.at[idx, 'County'] = COUNTY_ID_TO_NAME[int(county_val)]
            elif county_val in counties_map:  # It's a county name that maps to code
                # Keep the original name since it's already correct
                continue
    
    return df

# ------------------------------------------------------------------------
# Main Application
def main():
    # Header Section with Improved Title Styling
    st.markdown('<div class="main-header">🏛️ Illinois Population Data Explorer</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-title">Analyze demographic trends across Illinois counties from 2000-2024</div>', unsafe_allow_html=True)
    
    # Initialize session state
    if 'report_df' not in st.session_state:
        st.session_state.report_df = pd.DataFrame()
    if 'selected_filters' not in st.session_state:
        st.session_state.selected_filters = {}
    
    # Debug mode
    debug_mode = st.sidebar.checkbox("Debug Mode", value=False)
    
    # Census Links Button in Sidebar
    if st.sidebar.button("📊 Census Data Links"):
        display_census_links()
    
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
            st.sidebar.warning("⚠️ No data found in form control file")
            
    except Exception as e:
        st.sidebar.error(f"❌ Error loading data: {e}")
        return

    # County ID <-> Name maps (EXACTLY like old code)
    COUNTY_NAME_TO_ID = counties_map  
    COUNTY_ID_TO_NAME = {v: k for k, v in COUNTY_NAME_TO_ID.items()}

    # Quick Stats Overview
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

    # Main Analysis Section
    st.markdown('<div class="section-header">🔍 Query Builder</div>', unsafe_allow_html=True)
    
    # Create tabs for different configuration sections
    config_tab1, config_tab2, config_tab3 = st.tabs(["📍 Geography & Time", "👥 Demographics", "📋 Age Settings"])
    
    with config_tab1:
        col1, col2 = st.columns(2)
        
        with col1:
            selected_years = st.multiselect(
                "Select Year(s):",
                options=years_list,
                default=years_list[-1:] if years_list else [],
                help="Choose one or more years to analyze"
            )
            
        with col2:
            all_counties = ["All"] + sorted(counties_map.keys())
            selected_counties = st.multiselect(
                "Select Counties:",
                options=all_counties,
                default=["All"],
                help="Choose counties to include. 'All' includes all Illinois counties."
            )
    
    with config_tab2:
        col1, col2 = st.columns(2)
        
        with col1:
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
                help="Filter data by race category"
            )
            
            selected_sex = st.radio(
                "Sex:",
                ["All", "Male", "Female"],
                horizontal=True
            )
            
        with col2:
            selected_ethnicity = st.radio(
                "Ethnicity:",
                ["All", "Hispanic", "Not Hispanic"],
                horizontal=True
            )
            
            region_options = ["None", "Collar Counties", "Urban Counties", "Rural Counties"]
            selected_region = st.selectbox("Region:", region_options, index=0)
    
    with config_tab3:
        col1, col2 = st.columns(2)
        
        with col1:
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
                help="Choose predefined age bracket grouping"
            )
            
            # Show age brackets for selected group
            if selected_agegroup_display != "All":
                agegroup_code = AGEGROUP_DISPLAY_TO_CODE.get(selected_agegroup_display)
                brackets_implicit = agegroup_map_implicit.get(agegroup_code, [])
                if brackets_implicit:
                    st.write("**Age Brackets:**", ", ".join(brackets_implicit))
        
        with col2:
            st.write("**Custom Age Ranges:**")
            st.caption(
                "Optional: Define custom age ranges (overrides Age Group selection). "
                "Age codes: 1=0-4, 2=5-9, 3=10-14, 4=15-19, 5=20-24, 6=25-29, 7=30-34, 8=35-39, "
                "9=40-44, 10=45-49, 11=50-54, 12=55-59, 13=60-64, 14=65-69, 15=70-74, 16=75-79, "
                "17=80-84, 18=80+. See Documentation Codebooks under Census Data Links for details."
            )
            
            custom_ranges = []
            range_cols = st.columns(3)
            
            with range_cols[0]:
                if st.checkbox("Range 1", key="range1_check"):
                    min1 = st.number_input("Min 1", min_value=1, max_value=18, value=1, key="min1")
                    max1 = st.number_input("Max 1", min_value=1, max_value=18, value=5, key="max1")
                    if min1 <= max1:
                        custom_ranges.append((min1, max1))
            
            with range_cols[1]:
                if st.checkbox("Range 2", key="range2_check"):
                    min2 = st.number_input("Min 2", min_value=1, max_value=18, value=6, key="min2")
                    max2 = st.number_input("Max 2", min_value=1, max_value=18, value=10, key="max2")
                    if min2 <= max2:
                        custom_ranges.append((min2, max2))
            
            with range_cols[2]:
                if st.checkbox("Range 3", key="range3_check"):
                    min3 = st.number_input("Min 3", min_value=1, max_value=18, value=11, key="min3")
                    max3 = st.number_input("Max 3", min_value=1, max_value=18, value=15, key="max3")
                    if min3 <= max3:
                        custom_ranges.append((min3, max3))
    
    # Grouping Options
    st.markdown('<div class="section-header">📈 Output Configuration</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        grouping_var = st.selectbox(
            "Group Results By:",
            ["None", "Age", "Race", "Ethnicity", "Sex", "County"],
            index=0,
            help="Choose how to group the results"
        )
    
    with col2:
        include_breakdown = st.checkbox(
            "Include Individual County Breakdowns",
            value=True,
            help="Show data for each selected county individually in addition to totals"
        )
    
    # Action Buttons
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        generate_btn = st.button("🚀 Generate Report", use_container_width=True, type="primary")
    
    with col2:
        if st.button("🗑️ Clear Results", use_container_width=True):
            st.session_state.report_df = pd.DataFrame()
            st.session_state.selected_filters = {}
            st.rerun()
    
    with col3:
        download_disabled = st.session_state.report_df.empty
        if st.button("💾 Download Data", use_container_width=True, disabled=download_disabled):
            if not st.session_state.report_df.empty:
                # Add metadata to CSV
                csv_with_metadata = add_metadata_to_csv(st.session_state.report_df, st.session_state.selected_filters)
                st.download_button(
                    label="📥 Download CSV",
                    data=csv_with_metadata,
                    file_name="illinois_population_data.csv",
                    mime="text/csv",
                    key="download_btn"
                )

    # Generate Report Logic
    if generate_btn:
        if not selected_years:
            st.warning("⚠️ Please select at least one year.")
            st.stop()
        
        if not selected_counties:
            st.warning("⚠️ Please select at least one county.")
            st.stop()
        
        # Store selected filters for metadata
        st.session_state.selected_filters = {
            'years': selected_years,
            'counties': selected_counties,
            'race': selected_race_display,
            'ethnicity': selected_ethnicity,
            'sex': selected_sex,
            'region': selected_region,
            'age_group': selected_agegroup_display,
            'group_by': grouping_var
        }
        
        # Convert selections for backend processing
        if selected_race_display == "All":
            selected_race_code = "All"
        else:
            selected_race_code = RACE_DISPLAY_TO_CODE.get(selected_race_display, selected_race_display)
        
        if selected_agegroup_display == "All":
            agegroup_for_backend = None
        else:
            agegroup_for_backend = AGEGROUP_DISPLAY_TO_CODE[selected_agegroup_display]
        
        # Process data
        with st.spinner("🔄 Processing data..."):
            try:
                all_frames = []
                debug_info = []
                
                def get_aggregated_result(county_list, county_label):
                    frames_for_years = []
                    for year in selected_years:
                        try:
                            df_source = backend_main_processing.process_population_data(
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
                                custom_age_ranges=custom_ranges if custom_ranges else []
                            )
                            
                            if debug_mode:
                                debug_info.append(f"Year {year}, {county_label}: {len(df_source)} records, Total Pop: {df_source['Count'].sum():,}")
                            
                            if grouping_var == "None" or grouping_var == "Age":
                                age_df = aggregate_age_with_brackets(
                                    df_source=df_source,
                                    year_str=year,
                                    agegroup_for_backend=agegroup_for_backend,
                                    custom_ranges=custom_ranges if custom_ranges else [],
                                    agegroup_display=selected_agegroup_display,
                                    agegroup_map_implicit=agegroup_map_implicit
                                )
                                if not age_df.empty:
                                    age_df.insert(0, "County", county_label)
                                frames_for_years.append(age_df)
                            else:
                                # Use COUNTY_ID_TO_NAME mapping exactly like old code
                                group_df = aggregate_by_field(df_source, grouping_var, year, COUNTY_ID_TO_NAME)
                                if grouping_var != "County":
                                    if not group_df.empty:
                                        group_df.insert(0, "County", county_label)
                                frames_for_years.append(group_df)
                                
                        except Exception as e:
                            st.error(f"Error processing {year} for {county_label}: {e}")
                    
                    if frames_for_years:
                        return pd.concat(frames_for_years, ignore_index=True)
                    return pd.DataFrame()
                
                # Get combined results
                if "All" in selected_counties:
                    df_combined = get_aggregated_result(["All"], "All Counties")
                else:
                    df_combined = get_aggregated_result(selected_counties, "Selected Counties")
                
                all_frames.append(df_combined)
                
                # Individual county breakdowns if requested
                if include_breakdown and "All" not in selected_counties:
                    for county in selected_counties:
                        df_county = get_aggregated_result([county], county)
                        all_frames.append(df_county)
                
                # Combine all results
                if all_frames:
                    final_df = pd.concat(all_frames, ignore_index=True)
                    # Ensure county names are properly displayed using the fixed function
                    final_df = ensure_county_names(final_df, counties_map)
                    st.session_state.report_df = final_df
                else:
                    final_df = pd.DataFrame()
                    st.session_state.report_df = final_df
                    
                # Show debug info if enabled
                if debug_mode and debug_info:
                    with st.expander("Debug Information"):
                        for info in debug_info:
                            st.write(info)
                            
            except Exception as e:
                st.error(f"❌ Error generating report: {e}")
        
        # Display Results
        if st.session_state.report_df.empty:
            st.info("📭 No data found for the selected filters.")
        else:
            st.success("✅ Report generated successfully!")
            
            # Summary statistics
            total_population = st.session_state.report_df["Count"].sum()
            st.metric("Total Population in Report", f"{total_population:,}")
            
            # Display data
            st.markdown("### 📋 Results")
            st.dataframe(st.session_state.report_df, use_container_width=True)
            
            # Add download button
            csv_with_metadata = add_metadata_to_csv(st.session_state.report_df, st.session_state.selected_filters)
            st.download_button(
                label="📥 Download CSV",
                data=csv_with_metadata,
                file_name="illinois_population_data.csv",
                mime="text/csv",
            )

    # Show existing results if available
    elif not st.session_state.report_df.empty:
        st.markdown("### 📋 Existing Results")
        st.dataframe(st.session_state.report_df, use_container_width=True)
        
        # Download button for existing results
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
        "Illinois Population Data Explorer • U.S. Census Bureau Data • 2000-2024"
        "</div>",
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()
