import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import io
import base64
import os

# ------------------------------------------------------------------------
# Streamlit Page Config
st.set_page_config(
    page_title="Illinois Census Query Builder",
    layout="wide",  
    page_icon="🏛️"
)

# ------------------------------------------------------------------------
# Custom CSS for Illinois-themed design
st.markdown("""
<style>
    .main-header {
        font-size: 2.8rem;
        background: linear-gradient(135deg, #0d47a1, #1976d2);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        margin-bottom: 1rem;
        font-weight: 800;
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
        padding: 1.5rem;
        border-radius: 15px;
        box-shadow: 0 4px 6px rgba(13, 71, 161, 0.1);
        margin-bottom: 1rem;
        text-align: center;
        border: 1px solid #90caf9;
    }
    .metric-value {
        font-size: 2rem;
        font-weight: bold;
        color: #0d47a1;
        margin: 0.5rem 0;
    }
    .metric-label {
        font-size: 1rem;
        color: #546e7a;
        text-transform: uppercase;
        letter-spacing: 1px;
        font-weight: 500;
    }
    .illinois-blue {
        color: #0d47a1;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 1rem;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: #e3f2fd;
        border-radius: 10px 10px 0px 0px;
        gap: 1rem;
        padding: 10px 20px;
        font-weight: 600;
        color: #0d47a1;
    }
    .stTabs [data-baseweb="tab"][aria-selected="true"] {
        background-color: #1976d2;
        color: white;
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
    # Create dummy functions for demonstration
    def dummy_load_data(*args):
        return [], [], [], {}, {}, {}
    frontend_data_loader.load_form_control_data = dummy_load_data

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
# Data aggregation functions
def aggregate_age_with_brackets(
    df_source: pd.DataFrame,
    year_str: str,
    agegroup_for_backend: str | None,
    custom_ranges: list[tuple[int,int]],
    agegroup_display: str,
    agegroup_map_implicit: dict
) -> pd.DataFrame:
    """Aggregates data by age brackets (or custom ranges)"""
    if df_source is None or df_source.empty:
        return pd.DataFrame(columns=["AgeGroup", "Count", "Percent", "Year"])
    
    # If no bracket selection & no custom ranges => entire population
    if agegroup_for_backend is None and not custom_ranges:
        total_pop = df_source["Count"].sum()
        return pd.DataFrame({
            "AgeGroup": ["IL Population"],
            "Count": [total_pop],
            "Percent": [100.0 if total_pop > 0 else 0.0],
            "Year": [year_str]
        })

    # If custom ranges
    if custom_ranges:
        rows, total_sum = [], 0
        for (mn, mx) in custom_ranges:
            code_list = range(mn, mx+1)
            bracket_label = combine_codes_to_label(list(code_list))
            mask = df_source["Age"].isin(code_list)
            sub_sum = df_source.loc[mask, "Count"].sum()
            rows.append((bracket_label, sub_sum))
            total_sum += sub_sum
        out_rows = []
        for (bexpr, cval) in rows:
            pct = (cval / total_sum * 100.0) if total_sum > 0 else 0.0
            out_rows.append((bexpr, cval, round(pct,1)))
        df_out = pd.DataFrame(out_rows, columns=["AgeGroup", "Count", "Percent"])
        df_out["Year"] = year_str
        return df_out

    # Otherwise, use the implicit bracket definitions from the map
    brackets_implicit = agegroup_map_implicit.get(agegroup_for_backend, [])
    if not brackets_implicit:
        total_pop = df_source["Count"].sum()
        return pd.DataFrame({
            "AgeGroup": [f"No bracket for {agegroup_display}"],
            "Count": [total_pop],
            "Percent": [100.0 if total_pop > 0 else 0.0],
            "Year": [year_str]
        })

    rows, total_sum = [], 0
    for bracket_expr in brackets_implicit:
        bracket_expr = bracket_expr.strip()
        mask = frontend_bracket_utils.parse_implicit_bracket(df_source, bracket_expr)
        sub_sum = df_source.loc[mask, "Count"].sum()
        rows.append((bracket_expr, sub_sum))
        total_sum += sub_sum

    out_rows = []
    for (bexpr, cval) in rows:
        pct = (cval / total_sum * 100.0) if total_sum > 0 else 0.0
        out_rows.append((bexpr, cval, round(pct,1)))

    df_out = pd.DataFrame(out_rows, columns=["AgeGroup", "Count", "Percent"])
    df_out["Year"] = year_str
    return df_out

def aggregate_by_field(
    df_source: pd.DataFrame,
    group_by: str,
    year_str: str,
    county_id_to_name: dict
) -> pd.DataFrame:
    """Aggregates by Race, Ethnicity, Sex, or County"""
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

    grouped = df_source.groupby(group_by)["Count"].sum().reset_index()
    total_sum = grouped["Count"].sum()
    grouped["Percent"] = grouped["Count"] / total_sum * 100 if total_sum > 0 else 0
    grouped["Percent"] = grouped["Percent"].round(1)
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
# Main Application
def main():
    # Header Section
    st.markdown('<div class="main-header">🏛️ Illinois Population Data Explorer</div>', unsafe_allow_html=True)
    st.markdown("### Analyze demographic trends across Illinois counties from 2000-2024")
    
    # Initialize session state
    if 'report_df' not in st.session_state:
        st.session_state.report_df = pd.DataFrame()
    
    # Load form control data
    try:
        (years_list,
         agegroups_list_raw,
         races_list_raw,
         counties_map,
         agegroup_map_explicit,
         agegroup_map_implicit) = frontend_data_loader.load_form_control_data(FORM_CONTROL_PATH)
        
        if years_list:
            st.success("✅ Data loaded successfully!")
        else:
            st.warning("⚠️ No data found. Using sample configuration.")
            # Provide sample data for demonstration
            years_list = ["2020", "2021", "2022", "2023"]
            counties_map = {"Cook": 31, "DuPage": 43, "Lake": 97, "Will": 197}
            races_list_raw = ["White", "Black", "Asian", "Hispanic"]
            agegroups_list_raw = ["Under 18", "18-64", "65+"]
        
    except Exception as e:
        st.error(f"❌ Error loading data: {e}")
        st.info("Using sample configuration for demonstration")
        # Provide sample data
        years_list = ["2020", "2021", "2022", "2023"]
        counties_map = {"Cook": 31, "DuPage": 43, "Lake": 97, "Will": 197}
        races_list_raw = ["White", "Black", "Asian", "Hispanic"]
        agegroups_list_raw = ["Under 18", "18-64", "65+"]

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
                default=years_list[-1:] if years_list else [],  # Default to most recent year
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
            st.caption("Optional: Define custom age ranges (overrides Age Group selection)")
            
            # Fixed custom ranges - no zero values
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
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        generate_btn = st.button("🚀 Generate Report", use_container_width=True, type="primary")
    
    with col2:
        if st.button("🗑️ Clear Results", use_container_width=True):
            st.session_state.report_df = pd.DataFrame()
            st.rerun()
    
    with col3:
        show_links = st.button("📊 Census Links", use_container_width=True)
    
    with col4:
        download_disabled = st.session_state.report_df.empty
        download_btn = st.button("💾 Download Data", use_container_width=True, disabled=download_disabled)

    # Census Links
    if show_links:
        with st.expander("U.S. Census Bureau Links", expanded=True):
            st.write("""
            **Data Sources:**
            - [Census Datasets](https://www2.census.gov/programs-surveys/popest/datasets/)
            - [2000-2010 Intercensal County Data](https://www2.census.gov/programs-surveys/popest/datasets/2000-2010/intercensal/county/)
            - [2010-2020 County ASRH](https://www2.census.gov/programs-surveys/popest/datasets/2010-2020/counties/asrh/)
            - [2020-2024 County ASRH](https://www2.census.gov/programs-surveys/popest/datasets/2020-2024/counties/asrh/)
            - [Release Schedule](https://www.census.gov/programs-surveys/popest/about/schedule.html)
            """)

    # Generate Report Logic
    if generate_btn:
        if not selected_years:
            st.warning("⚠️ Please select at least one year.")
            st.stop()
        
        if not selected_counties:
            st.warning("⚠️ Please select at least one county.")
            st.stop()
        
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
                                group_df = aggregate_by_field(df_source, grouping_var, year, counties_map)
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
                    st.session_state.report_df = final_df
                else:
                    final_df = pd.DataFrame()
                    st.session_state.report_df = final_df
                    
            except Exception as e:
                st.error(f"❌ Error generating report: {e}")
                st.info("This might be due to missing data files or backend processing issues")
        
        # Display Results
        if st.session_state.report_df.empty:
            st.info("📭 No data found for the selected filters.")
        else:
            st.success("✅ Report generated successfully!")
            
            # Summary statistics
            total_population = st.session_state.report_df["Count"].sum()
            st.metric("Total Population Count", f"{total_population:,}")
            
            # Display data
            st.markdown("### 📋 Results")
            st.dataframe(st.session_state.report_df, use_container_width=True)
    
    # Download functionality
    if download_btn and "report_df" in st.session_state and not st.session_state.report_df.empty:
        csv_data = st.session_state.report_df.to_csv(index=False)
        st.download_button(
            label="📥 Download CSV",
            data=csv_data,
            file_name="illinois_population_data.csv",
            mime="text/csv",
        )

    # Show existing results if available
    elif not st.session_state.report_df.empty:
        st.markdown("### 📋 Existing Results")
        st.dataframe(st.session_state.report_df, use_container_width=True)
        
        # Download button for existing results
        csv_data = st.session_state.report_df.to_csv(index=False)
        st.download_button(
            label="📥 Download CSV",
            data=csv_data,
            file_name="illinois_population_data.csv",
            mime="text/csv",
        )

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
