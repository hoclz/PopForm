# ============================================================================
# HEADER SECTION - Includes and Configuration
# ============================================================================
import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
from typing import List, Tuple, Dict, Optional

# Application metadata
APP_TITLE = "Illinois Population Data Explorer"
APP_LAYOUT = "wide"
APP_ICON = "🏛️"
DATA_FOLDER = "./data"
FORM_CONTROL_PATH = "./form_control_UI_data.csv"

# ============================================================================
# CONSTANTS - Mappings and Configuration
# ============================================================================
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
    1: "0-4", 2: "5-9", 3: "10-14", 4: "15-19", 5: "20-24", 6: "25-29",
    7: "30-34", 8: "35-39", 9: "40-44", 10: "45-49", 11: "50-54",
    12: "55-59", 13: "60-64", 14: "65-69", 15: "70-74", 16: "75-79",
    17: "80-84", 18: "80+",
}

# ============================================================================
# STYLE CONFIGURATION - CSS Stylesheet
# ============================================================================
APP_STYLES = """
<style>
    /* Main container styling */
    .main-container {
        font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
        background: linear-gradient(135deg, #f8f9fa, #e9ecef);
    }
    
    .main-header {
        font-size: 2.5rem;
        background: linear-gradient(135deg, #0d47a1, #1976d2);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        margin-bottom: 0.5rem;
        font-weight: 800;
        font-family: 'Courier New', monospace;
        border-bottom: 2px solid #0d47a1;
        padding-bottom: 0.5rem;
    }
    
    .sub-title {
        font-size: 1.1rem;
        color: #495057;
        text-align: center;
        margin-bottom: 2rem;
        font-weight: 400;
        font-style: italic;
        font-family: 'Courier New', monospace;
    }
    
    /* Metric cards - struct-like appearance */
    /* Style adjusted slightly for sidebar */
    .st-emotion-cache-1jicfl2 .metric-card { 
        margin-bottom: 1rem;
    }
    
    .metric-card {
        background: linear-gradient(135deg, #ffffff, #f8f9fa);
        padding: 1.2rem;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        text-align: center;
        border: 1px solid #dee2e6;
        border-left: 4px solid #0d47a1;
        font-family: 'Courier New', monospace;
        margin-bottom: 1rem; /* Added for sidebar stacking */
    }
    
    .metric-value {
        font-size: 1.8rem;
        font-weight: 700;
        color: #1a365d;
        margin-bottom: 0.3rem;
        line-height: 1;
    }
    
    .metric-label {
        font-size: 0.8rem;
        color: #6c757d;
        font-weight: 500;
        line-height: 1.2;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    /* Button styling - function call appearance */
    .function-button {
        font-family: 'Courier New', monospace;
        font-weight: 600;
        border: 1px solid #0d47a1;
    }
    
    /* Data table styling - array-like appearance */
    .data-table {
        font-family: 'Courier New', monospace;
        font-size: 0.9rem;
    }
    
    /* Code block styling for sections */
    .code-section {
        background: #f8f9fa;
        border: 1px solid #e9ecef;
        border-radius: 5px;
        padding: 1rem;
        margin: 1rem 0;
        font-family: 'Courier New', monospace;
    }
</style>
"""

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

# ... (All utility functions like combine_codes_to_label, ensure_county_names, 
#      attach_agegroup_column, and aggregate_multi remain unchanged) ...

def combine_codes_to_label(codes: List[int]) -> str:
    """
    FUNCTION: combine_codes_to_label
    PURPOSE: Convert age codes to human-readable labels
    PARAMETERS: List of integer age codes
    RETURNS: String representation of age range
    """
    
    codes = sorted(set(int(c) for c in codes))
    if not codes:
        return ""
    
    lows, highs = [], []
    for c in codes:
        s = CODE_TO_BRACKET.get(c, "")
        if "-" in s:
            a, b = s.split("-")
            lows.append(int(a))
            highs.append(int(b))
        elif s.endswith("+"):
            lows.append(int(s[:-1]))
            highs.append(999)
    
    if not lows:
        return "-".join(str(c) for c in codes)
    
    lo, hi = min(lows), max(highs)
    return f"{lo}+" if hi >= 999 else f"{lo}-{hi}"

def ensure_county_names(df: pd.DataFrame, counties_map: Dict[str, int]) -> pd.DataFrame:
    """
    FUNCTION: ensure_county_names
    PURPOSE: Ensure county names are properly mapped in dataframe
    PARAMETERS: DataFrame, counties mapping dictionary
    RETURNS: DataFrame with county names
    """
    
    if df is None or df.empty:
        return df
    
    id_to_name = {v: k for k, v in counties_map.items()}
    
    # Handle county code to name mapping
    if 'County Code' in df.columns and 'County Name' not in df.columns:
        df['County Name'] = df['County Code'].map(id_to_name).fillna(df['County Code'])
    
    return df

def attach_agegroup_column(df: pd.DataFrame, include_age: bool,
                            agegroup_for_backend: Optional[str],
                            custom_ranges: List[Tuple[int, int]],
                            agegroup_map_implicit: Dict[str, list]) -> pd.DataFrame:
    """
    FUNCTION: attach_agegroup_column
    PURPOSE: Add age group column to dataframe based on configuration
    PARAMETERS: DataFrame, age inclusion flag, backend age group, custom ranges, implicit mapping
    RETURNS: DataFrame with age group column
    """
    
    if not include_age:
        return df
    
    df_copy = df.copy()
    
    # Handle custom age ranges
    if custom_ranges:
        df_copy['AgeGroup'] = np.nan
        covered = np.zeros(len(df_copy), dtype=bool)
        
        for mn, mx in custom_ranges:
            mn_i, mx_i = max(1, int(mn)), min(18, int(mx))
            if mn_i > mx_i:
                continue
            
            codes = list(range(mn_i, mx_i + 1))
            label = combine_codes_to_label(codes)
            mask = df_copy['Age'].between(mn_i, mx_i)
            
            df_copy.loc[mask, 'AgeGroup'] = label
            covered |= mask.to_numpy()
        
        if (~covered).any():
            df_copy.loc[~covered, 'AgeGroup'] = "Other Ages"
        
        return df_copy
    
    # Handle backend age groups
    if agegroup_for_backend:
        df_copy['AgeGroup'] = np.nan
        
        for expr in agegroup_map_implicit.get(agegroup_for_backend, []):
            try:
                mask = frontend_bracket_utils.parse_implicit_bracket(df_copy, str(expr))
                df_copy.loc[mask, 'AgeGroup'] = str(expr)
            except Exception:
                # Fallback parsing logic
                bexpr = str(expr).strip()
                m = None
                
                if "-" in bexpr:
                    a, b = bexpr.split("-")
                    m = df_copy['Age'].between(int(a), int(b))
                elif bexpr.endswith("+") and bexpr[:-1].isdigit():
                    m = df_copy['Age'] >= int(bexpr[:-1])
                
                if m is not None:
                    df_copy.loc[m, 'AgeGroup'] = bexpr
        
        if df_copy['AgeGroup'].isna().any():
            df_copy['AgeGroup'] = df_copy['AgeGroup'].fillna("Other Ages")
        
        return df_copy
    
    # Default case
    df_copy['AgeGroup'] = "All Ages"
    return df_copy

def aggregate_multi(df_source: pd.DataFrame, grouping_vars: List[str],
                    year_str: str, county_label: str,
                    counties_map: Dict[str, int],
                    agegroup_for_backend: Optional[str],
                    custom_ranges: List[Tuple[int, int]],
                    agegroup_map_implicit: Dict[str, list]) -> pd.DataFrame:
    """
    FUNCTION: aggregate_multi
    PURPOSE: Aggregate data with multiple grouping variables
    PARAMETERS: Source DataFrame, grouping variables, year, county info, age configurations
    RETURNS: Aggregated DataFrame
    """
    
    grouping_vars_clean = [g for g in grouping_vars if g != "All"]
    
    # Early return for empty data
    if df_source is None or df_source.empty:
        base = ["County"] if "County" not in grouping_vars_clean else []
        cols = [("AgeGroup" if g == "Age" else g) for g in grouping_vars_clean]
        return pd.DataFrame(columns=base + cols + ["Count", "Percent", "Year"])
    
    total_population = df_source["Count"].sum()
    if total_population == 0:
        return pd.DataFrame()
    
    # Single aggregate case
    if len(grouping_vars_clean) == 0:
        out = pd.DataFrame({
            "Count": [int(total_population)],
            "Percent": [100.0],
            "Year": [str(year_str)]
        })
        out.insert(0, "County", county_label)
        return ensure_county_names(out, counties_map)
    
    # Multi-group aggregation
    include_age = "Age" in grouping_vars_clean
    df = attach_agegroup_column(df_source, include_age, agegroup_for_backend,
                                custom_ranges, agegroup_map_implicit)
    
    group_fields = [("AgeGroup" if g == "Age" else g) for g in grouping_vars_clean]
    grouped = df.groupby(group_fields, dropna=False)["Count"].sum().reset_index()
    
    # Post-processing
    if "Race" in grouped.columns:
        grouped["Race"] = grouped["Race"].map(RACE_CODE_TO_DISPLAY).fillna(grouped["Race"])
    
    grouped["Year"] = str(year_str)
    grouped = ensure_county_names(grouped, counties_map)
    
    # Calculate percentages
    denom_keys = ["Year"]
    if "Age" in grouping_vars_clean and "AgeGroup" in grouped.columns:
        denom_keys.append("AgeGroup")
    
    if denom_keys:
        den = grouped.groupby(denom_keys, dropna=False)["Count"].transform("sum")
        grouped["Percent"] = np.where(den > 0, (grouped["Count"] / den * 100).round(1), 0.0)
    else:
        grouped["Percent"] = (grouped["Count"] / total_population * 100.0).round(1)
    
    # Ensure county column exists
    if "County" not in grouping_vars_clean:
        grouped.insert(0, "County", county_label)
    
    return grouped

# ============================================================================
# MAIN APPLICATION FUNCTION
# ============================================================================
def main():
    """
    FUNCTION: main
    PURPOSE: Application entry point and main control flow
    RETURNS: void
    """
    
    # Initialize application
    st.set_page_config(
        page_title=APP_TITLE,
        layout=APP_LAYOUT,
        page_icon=APP_ICON
    )
    
    # Apply styles
    st.markdown(APP_STYLES, unsafe_allow_html=True)
    
    # Import external modules
    try:
        import backend_main_processing
        import frontend_data_loader
        import frontend_bracket_utils
        from frontend_sidebar import render_sidebar_controls, display_census_links
    except Exception as e:
        st.error(f"Module import error: {e}")
        return
    
    # ========================================================================
    # HEADER SECTION
    # ========================================================================
    
    st.markdown('<div class="main-header">🏛️ Illinois Population Data Explorer</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-title">Analyze demographic trends across Illinois counties (2000–2024)</div>', unsafe_allow_html=True)
    
    # ========================================================================
    # DATA INITIALIZATION
    # ========================================================================
    
    # Load form control data
    (years_list, agegroups_list_raw, races_list_raw, counties_map,
     agegroup_map_explicit, agegroup_map_implicit) = frontend_data_loader.load_form_control_data(FORM_CONTROL_PATH)
    
    # ========================================================================
    # SIDEBAR - Metrics and Links (MOVED FROM MAIN PAGE)
    # ========================================================================
    
    with st.sidebar:
        st.markdown("## 📊 System Metrics")
        
        st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value">{len(years_list)}</div>
                <div class="metric-label">Years Available</div>
            </div>
        """, unsafe_allow_html=True)
        
        st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value">{len(counties_map)}</div>
                <div class="metric-label">Illinois Counties</div>
            </div>
        """, unsafe_allow_html=True)
        
        st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value">{len(races_list_raw)}</div>
                <div class="metric-label">Race Categories</div>
            </div>
        """, unsafe_allow_html=True)
        
        st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value">{len(agegroups_list_raw)}</div>
                <div class="metric-label">Age Groups</div>
            </div>
        """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Moved from main page action_cols[1]
        display_census_links()

    # ========================================================================
    # CONTROL PANEL SECTION (REORGANIZED)
    # ========================================================================
    
    st.markdown("## 🎮 Control Panel")
    
    with st.expander("Configure Data Query", expanded=True):
        
        # --- IMPORTANT ---
        # The function 'render_sidebar_controls' (from frontend_sidebar.py)
        # MUST BE MODIFIED to render its widgets in the main container 
        # (e.g., using st.multiselect) instead of st.sidebar.multiselect.
        choices = render_sidebar_controls(
            years_list, races_list_raw, counties_map,
            agegroup_map_implicit, agegroups_list_raw
        )
        
        st.markdown("---") # Separator before buttons

        # Action buttons (Moved inside expander)
        action_cols = st.columns(2) # Simplified from [3, 2]
        
        with action_cols[0]:
            try:
                go = st.button("🚀 Execute Data Processing", use_container_width=True, type="primary")
            except TypeError:
                go = st.button("🚀 Execute Data Processing", use_container_width=True)
        
        with action_cols[1]:
            clear_clicked = st.button("🗑️ Clear Results", use_container_width=True)

    st.markdown("---") # Separator after control panel
    
    # Initialize session state
    if "report_df" not in st.session_state:
        st.session_state["report_df"] = pd.DataFrame()
    if "selected_filters" not in st.session_state:
        st.session_state["selected_filters"] = {}
    
    # Handle clear action
    if clear_clicked:
        st.session_state["report_df"] = pd.DataFrame()
        st.session_state["selected_filters"] = {}
        st.rerun()
    
    # ========================================================================
    # DATA PROCESSING EXECUTION
    # ========================================================================
    
    if go:
        # Input validation
        if not choices["selected_years"]:
            st.warning("⚠️ Please select at least one year.")
            return
        if not choices["selected_counties"]:
            st.warning("⚠️ Please select at least one county.")
            return
        
        # Store filter configuration
        st.session_state["selected_filters"] = {
            "years": [str(y) for y in choices["selected_years"]],
            "counties": choices["selected_counties"],
            "race": choices["selected_race_display"],
            "ethnicity": choices["selected_ethnicity"],
            "sex": choices["selected_sex"],
            "region": choices["selected_region"],
            "age_group": "Custom Ranges" if choices["enable_custom_ranges"] else choices["selected_agegroup_display"],
            "group_by": choices["grouping_vars"],
        }
        
        # Execute data processing
        with st.spinner("🔄 Processing census data..."):
            all_frames = []
            
            def build_block(county_list: List[str], county_label: str) -> pd.DataFrame:
                frames = []
                
                for year in choices["selected_years"]:
                    # Process data for current year and county
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
                    
                    # Aggregate results
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
            
            # Build main data blocks
            if "All" in choices["selected_counties"]:
                combined = build_block(["All"], "All Counties")
                if not combined.empty:
                    all_frames.append(combined)
            else:
                combined = build_block(choices["selected_counties"], "Selected Counties")
                if not combined.empty:
                    all_frames.append(combined)
                
                # Include individual county breakdowns if requested
                if choices["include_breakdown"]:
                    for cty in choices["selected_counties"]:
                        cdf = build_block([cty], cty)
                        if not cdf.empty:
                            all_frames.append(cdf)
            
            # Store final results
            st.session_state["report_df"] = pd.concat(all_frames, ignore_index=True) if all_frames else pd.DataFrame()
            st.session_state["report_df"] = ensure_county_names(
                st.session_state["report_df"], counties_map
            )
    
    # ========================================================================
    # RESULTS DISPLAY SECTION
    # ========================================================================
    
    if not st.session_state["report_df"].empty:
        st.success("✅ Data processing completed successfully!")
        
        st.markdown("## 📋 Processing Results")
        
        # Display results dataframe
        st.dataframe(st.session_state["report_df"], use_container_width=True)
        
        # Export functionality
        st.markdown("## 💾 Data Export")
        
        meta = [
            "# Illinois Population Data Explorer - Export",
            f"# Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "# Data Source: U.S. Census Bureau Population Estimates",
            f"# Years: {', '.join(st.session_state['selected_filters'].get('years', []))}",
            f"# Counties: {', '.join(st.session_state['selected_filters'].get('counties', []))}",
            f"# Race Filter: {st.session_state['selected_filters'].get('race', 'All')}",
            f"# Ethnicity: {st.session_state['selected_filters'].get('ethnicity', 'All')}",
            f"# Sex: {st.session_state['selected_filters'].get('sex', 'All')}",
            f"# Region: {st.session_state['selected_filters'].get('region', 'None')}",
            f"# Age Group: {st.session_state['selected_filters'].get('age_group', 'All')}",
            f"# Group By: {', '.join(st.session_state['selected_filters'].get('group_by', [])) or 'None'}",
            f"# Total Records: {len(st.session_state['report_df'])}",
            f"# Total Population: {st.session_state['report_df']['Count'].sum():,}" if 'Count' in st.session_state['report_df'].columns else "# Total Population: N/A",
            "#",
            "# Note: Data are official U.S. Census Bureau estimates",
            "#"
        ]
        
        csv_text = "\n".join(meta) + "\n" + st.session_state["report_df"].to_csv(index=False)
        
        st.download_button(
            "📥 Download CSV Report",
            data=csv_text,
            file_name="illinois_population_data.csv",
            mime="text/csv"
        )
    
    # ========================================================================
    # FOOTER SECTION
    # ========================================================================
    
    st.markdown("---")
# ============================================================================
# APPLICATION ENTRY POINT
# ============================================================================
if __name__ == "__main__":
    main()
