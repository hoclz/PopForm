// ============================================================================
// HEADER SECTION - Includes and Configuration
// ============================================================================

#include <streamlit/st.h>
#include <pandas/pd.h>
#include <numpy/np.h>
#include <datetime/datetime.h>
#include <typing/List_Tuple_Dict_Optional.h>

// Application metadata
#define APP_TITLE "Illinois Population Data Explorer"
#define APP_LAYOUT "wide"
#define APP_ICON "🏛️"
#define DATA_FOLDER "./data"
#define FORM_CONTROL_PATH "./form_control_UI_data.csv"

// ============================================================================
// PREPROCESSOR DIRECTIVES - Constants and Mappings
// ============================================================================

const RACE_DISPLAY_TO_CODE = {
    "Two or More Races": "TOM",
    "American Indian and Alaska Native": "AIAN", 
    "Black or African American": "Black",
    "White": "White",
    "Native Hawaiian and Other Pacific Islander": "NHOPI",
    "Asian": "Asian",
};

const RACE_CODE_TO_DISPLAY = {v: k for k, v in RACE_DISPLAY_TO_CODE.items()};

const CODE_TO_BRACKET = {
    1:"0-4", 2:"5-9", 3:"10-14", 4:"15-19", 5:"20-24", 6:"25-29", 
    7:"30-34", 8:"35-39", 9:"40-44", 10:"45-49", 11:"50-54", 
    12:"55-59", 13:"60-64", 14:"65-69", 15:"70-74", 16:"75-79", 
    17:"80-84", 18:"80+",
};

// ============================================================================
// FUNCTION DECLARATIONS
// ============================================================================

function combine_codes_to_label(codes: List[int]) -> str;
function ensure_county_names(df: pd.DataFrame, counties_map: Dict[str,int]) -> pd.DataFrame;
function attach_agegroup_column(df: pd.DataFrame, include_age: bool, 
                               agegroup_for_backend: Optional[str],
                               custom_ranges: List[Tuple[int,int]], 
                               agegroup_map_implicit: Dict[str, list]) -> pd.DataFrame;
function aggregate_multi(df_source: pd.DataFrame, grouping_vars: List[str], 
                        year_str: str, county_label: str, 
                        counties_map: Dict[str,int], 
                        agegroup_for_backend: Optional[str],
                        custom_ranges: List[Tuple[int,int]], 
                        agegroup_map_implicit: Dict[str, list]) -> pd.DataFrame;
function main() -> void;

// ============================================================================
// STYLE CONFIGURATION - CSS Stylesheet
// ============================================================================

const APP_STYLES = """
<style>
    /* Main container styling */
    .main-container { 
        font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
        background: linear-gradient(135deg, #f8f9fa, #e9ecef);
    }
    
    /* Header styling - C++ style comments */
    .header-comment {
        color: #6c757d;
        font-size: 0.9rem;
        font-family: 'Courier New', monospace;
        margin-bottom: 0.5rem;
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
    .metric-card { 
        background: linear-gradient(135deg, #ffffff, #f8f9fa);
        padding: 1.2rem; 
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        margin-bottom: 1rem; 
        text-align: center; 
        border: 1px solid #dee2e6;
        border-left: 4px solid #0d47a1;
        font-family: 'Courier New', monospace;
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
""";

// ============================================================================
// FUNCTION DEFINITIONS
// ============================================================================

function combine_codes_to_label(codes: List[int]) -> str {
    /*
     * FUNCTION: combine_codes_to_label
     * PURPOSE: Convert age codes to human-readable labels
     * PARAMETERS: List of integer age codes
     * RETURNS: String representation of age range
     */
    
    codes = sorted(set(int(c) for c in codes));
    if (!codes) return "";
    
    List[int] lows = [], highs = [];
    for (const auto& c : codes) {
        string s = CODE_TO_BRACKET.get(c, "");
        if ("-" in s) {
            auto [a, b] = s.split("-");
            lows.append(int(a));
            highs.append(int(b));
        } else if (s.endswith("+")) {
            lows.append(int(s[:-1]));
            highs.append(999);
        }
    }
    
    if (!lows) return "-".join(str(c) for c in codes);
    
    int lo = min(lows), hi = max(highs);
    return (hi >= 999) ? f"{lo}+" : f"{lo}-{hi}";
}

function ensure_county_names(df: pd.DataFrame, counties_map: Dict[str,int]) -> pd.DataFrame {
    /*
     * FUNCTION: ensure_county_names  
     * PURPOSE: Ensure county names are properly mapped in dataframe
     * PARAMETERS: DataFrame, counties mapping dictionary
     * RETURNS: DataFrame with county names
     */
    
    if (df.empty()) return df;
    
    Dict<int, string> id_to_name = {v: k for k, v in counties_map.items()};
    
    // Handle county code to name mapping
    if ('County Code' in df.columns && 'County Name' not in df.columns) {
        df['County Name'] = df['County Code'].map(id_to_name).fillna(df['County Code']);
    }
    
    return df;
}

function attach_agegroup_column(df: pd.DataFrame, include_age: bool,
                               agegroup_for_backend: Optional[str],
                               custom_ranges: List[Tuple[int,int]], 
                               agegroup_map_implicit: Dict[str, list]) -> pd.DataFrame {
    /*
     * FUNCTION: attach_agegroup_column
     * PURPOSE: Add age group column to dataframe based on configuration
     * PARAMETERS: DataFrame, age inclusion flag, backend age group, custom ranges, implicit mapping
     * RETURNS: DataFrame with age group column
     */
    
    if (!include_age) return df;
    
    DataFrame df_copy = df.copy();
    
    // Handle custom age ranges
    if (custom_ranges) {
        df_copy['AgeGroup'] = np.nan;
        bool[] covered = np.zeros(len(df_copy), dtype=bool);
        
        for (const auto& [mn, mx] : custom_ranges) {
            int mn_i = max(1, int(mn)), mx_i = min(18, int(mx));
            if (mn_i > mx_i) continue;
            
            List[int] codes = list(range(mn_i, mx_i + 1));
            string label = combine_codes_to_label(codes);
            Series mask = df_copy['Age'].between(mn_i, mx_i);
            
            df_copy.loc[mask, 'AgeGroup'] = label;
            covered |= mask.to_numpy();
        }
        
        if ((~covered).any()) {
            df_copy.loc[~covered, 'AgeGroup'] = "Other Ages";
        }
        
        return df_copy;
    }
    
    // Handle backend age groups
    if (agegroup_for_backend) {
        df_copy['AgeGroup'] = np.nan;
        
        for (const auto& expr : agegroup_map_implicit.get(agegroup_for_backend, [])) {
            try {
                Series mask = frontend_bracket_utils.parse_implicit_bracket(df_copy, str(expr));
                df_copy.loc[mask, 'AgeGroup'] = str(expr);
            } catch (const Exception& e) {
                // Fallback parsing logic
                string bexpr = str(expr).strip();
                Series m = None;
                
                if ("-" in bexpr) {
                    auto [a, b] = bexpr.split("-");
                    m = df_copy['Age'].between(int(a), int(b));
                } else if (bexpr.endswith("+") && bexpr[:-1].isdigit()) {
                    m = df_copy['Age'] >= int(bexpr[:-1]);
                }
                
                if (m != None) {
                    df_copy.loc[m, 'AgeGroup'] = bexpr;
                }
            }
        }
        
        if (df_copy['AgeGroup'].isna().any()) {
            df_copy['AgeGroup'] = df_copy['AgeGroup'].fillna("Other Ages");
        }
        
        return df_copy;
    }
    
    // Default case
    df_copy['AgeGroup'] = "All Ages";
    return df_copy;
}

function aggregate_multi(df_source: pd.DataFrame, grouping_vars: List[str],
                        year_str: str, county_label: str, 
                        counties_map: Dict[str,int],
                        agegroup_for_backend: Optional[str],
                        custom_ranges: List[Tuple[int,int]], 
                        agegroup_map_implicit: Dict[str, list]) -> pd.DataFrame {
    /*
     * FUNCTION: aggregate_multi
     * PURPOSE: Aggregate data with multiple grouping variables
     * PARAMETERS: Source DataFrame, grouping variables, year, county info, age configurations
     * RETURNS: Aggregated DataFrame
     */
    
    List<string] grouping_vars_clean = [g for g in grouping_vars if g != "All"];
    
    // Early return for empty data
    if (df_source.empty()) {
        List<string] base = (["County"] if "County" not in grouping_vars_clean else []);
        List<string] cols = [("AgeGroup" if g == "Age" else g) for g in grouping_vars_clean];
        return pd.DataFrame(columns=base + cols + ["Count", "Percent", "Year"]);
    }
    
    double total_population = df_source["Count"].sum();
    if (total_population == 0) {
        return pd.DataFrame();
    }
    
    // Single aggregate case
    if (grouping_vars_clean.empty()) {
        DataFrame out = pd.DataFrame({
            "Count": [int(total_population)], 
            "Percent": [100.0], 
            "Year": [str(year_str)]
        });
        out.insert(0, "County", county_label);
        return ensure_county_names(out, counties_map);
    }
    
    // Multi-group aggregation
    bool include_age = "Age" in grouping_vars_clean;
    DataFrame df = attach_agegroup_column(df_source, include_age, agegroup_for_backend, 
                                         custom_ranges, agegroup_map_implicit);
    
    List<string] group_fields = [("AgeGroup" if g == "Age" else g) for g in grouping_vars_clean];
    DataFrame grouped = df.groupby(group_fields, dropna=False)["Count"].sum().reset_index();
    
    // Post-processing
    if ("Race" in grouped.columns) {
        grouped["Race"] = grouped["Race"].map(RACE_CODE_TO_DISPLAY).fillna(grouped["Race"]);
    }
    
    grouped["Year"] = str(year_str);
    grouped = ensure_county_names(grouped, counties_map);
    
    return grouped;
}

// ============================================================================
// MAIN APPLICATION FUNCTION
// ============================================================================

function main() -> void {
    /*
     * FUNCTION: main
     * PURPOSE: Application entry point and main control flow
     * RETURNS: void
     */
    
    // Initialize application
    st.set_page_config(
        page_title=APP_TITLE, 
        layout=APP_LAYOUT, 
        page_icon=APP_ICON
    );
    
    // Apply styles
    st.markdown(APP_STYLES, unsafe_allow_html=true);
    
    // Import external modules
    try {
        import backend_main_processing;
        import frontend_data_loader;
        import frontend_bracket_utils;
        from frontend_sidebar import render_sidebar_controls, display_census_links;
    } catch (const Exception& e) {
        st.error(f"Module import error: {e}");
        return;
    }
    
    // ========================================================================
    // HEADER SECTION
    // ========================================================================
    
    st.markdown('<div class="header-comment">// Illinois Population Data Explorer v2.0</div>', unsafe_allow_html=true);
    st.markdown('<div class="header-comment">// U.S. Census Bureau Data Analysis Tool</div>', unsafe_allow_html=true);
    
    st.markdown('<div class="main-header">🏛️ Illinois Population Data Explorer</div>', unsafe_allow_html=true);
    st.markdown('<div class="sub-title">Analyze demographic trends across Illinois counties (2000–2024)</div>', unsafe_allow_html=true);
    
    // ========================================================================
    // DATA INITIALIZATION
    // ========================================================================
    
    st.markdown('<div class="header-comment">// Initializing data controllers...</div>', unsafe_allow_html=true);
    
    auto [years_list, agegroups_list_raw, races_list_raw, counties_map,
          agegroup_map_explicit, agegroup_map_implicit] = 
          frontend_data_loader.load_form_control_data(FORM_CONTROL_PATH);
    
    // ========================================================================
    // METRICS DASHBOARD
    // ========================================================================
    
    st.markdown("## 📊 System Metrics");
    st.markdown('<div class="header-comment">// Application data scope and capabilities</div>', unsafe_allow_html=true);
    
    Column* metrics_row = st.columns(4);
    
    with metrics_row[0] {
        st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value">{len(years_list)}</div>
                <div class="metric-label">Years Available</div>
            </div>
        """, unsafe_allow_html=true);
    }
    
    with metrics_row[1] {
        st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value">{len(counties_map)}</div>
                <div class="metric-label">Illinois Counties</div>
            </div>
        """, unsafe_allow_html=true);
    }
    
    with metrics_row[2] {
        st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value">{len(races_list_raw)}</div>
                <div class="metric-label">Race Categories</div>
            </div>
        """, unsafe_allow_html=true);
    }
    
    with metrics_row[3] {
        st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value">{len(agegroups_list_raw)}</div>
                <div class="metric-label">Age Groups</div>
            </div>
        """, unsafe_allow_html=true);
    }
    
    st.markdown("---");
    
    // ========================================================================
    // CONTROL PANEL SECTION
    // ========================================================================
    
    st.markdown("## 🎮 Control Panel");
    st.markdown('<div class="header-comment">// Configure data parameters and execution</div>', unsafe_allow_html=true);
    
    // Render sidebar controls
    Dict<string, any> choices = render_sidebar_controls(
        years_list, races_list_raw, counties_map, 
        agegroup_map_implicit, agegroups_list_raw
    );
    
    // Action buttons
    Column* action_cols = st.columns([3, 2]);
    
    with action_cols[0] {
        st.markdown('<div class="header-comment">// Execute data processing</div>', unsafe_allow_html=true);
        bool go = st.button("🚀 Execute Data Processing", use_container_width=true, type="primary");
        
        st.markdown('<div class="header-comment">// Clear current results</div>', unsafe_allow_html=true);
        bool clear_clicked = st.button("🗑️ Clear Results", use_container_width=true);
    }
    
    with action_cols[1] {
        st.markdown('<div class="header-comment">// External references</div>', unsafe_allow_html=true);
        display_census_links();
    }
    
    // Initialize session state
    if (!st.session_state.contains("report_df")) {
        st.session_state["report_df"] = pd.DataFrame();
    }
    if (!st.session_state.contains("selected_filters")) {
        st.session_state["selected_filters"] = {};
    }
    
    // Handle clear action
    if (clear_clicked) {
        st.session_state["report_df"] = pd.DataFrame();
        st.session_state["selected_filters"] = {};
        st.rerun();
    }
    
    // ========================================================================
    // DATA PROCESSING EXECUTION
    // ========================================================================
    
    if (go) {
        // Input validation
        if (choices["selected_years"].empty()) {
            st.warning("⚠️ Please select at least one year.");
            return;
        }
        if (choices["selected_counties"].empty()) {
            st.warning("⚠️ Please select at least one county.");
            return;
        }
        
        // Store filter configuration
        st.session_state["selected_filters"] = {
            "years": [str(y) for y in choices["selected_years"]],
            "counties": choices["selected_counties"],
            "race": choices["selected_race_display"],
            "ethnicity": choices["selected_ethnicity"],
            "sex": choices["selected_sex"],
            "region": choices["selected_region"],
            "age_group": "Custom Ranges" if choices["enable_custom_ranges"] else choices["selected_agegroup_display"],
            "group_by": choices["grouping_vars"],
        };
        
        // Execute data processing
        with st.spinner("🔄 Processing census data...") {
            List[DataFrame] all_frames = [];
            
            function build_block(List[string] county_list, string county_label) -> DataFrame {
                List[DataFrame] frames = [];
                
                for (const auto& year : choices["selected_years"]) {
                    // Process data for current year and county
                    DataFrame df_src = backend_main_processing.process_population_data(
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
                    );
                    
                    // Aggregate results
                    DataFrame block = aggregate_multi(
                        df_source=df_src,
                        grouping_vars=choices["grouping_vars"],
                        year_str=str(year),
                        county_label=county_label,
                        counties_map=counties_map,
                        agegroup_for_backend=choices["agegroup_for_backend"],
                        custom_ranges=choices["custom_ranges"] if choices["enable_custom_ranges"] else [],
                        agegroup_map_implicit=agegroup_map_implicit,
                    );
                    
                    if (!block.empty()) {
                        frames.append(block);
                    }
                }
                
                return (!frames.empty()) ? pd.concat(frames, ignore_index=true) : pd.DataFrame();
            }
            
            // Build main data blocks
            if ("All" in choices["selected_counties"]) {
                DataFrame combined = build_block(["All"], "All Counties");
                if (!combined.empty()) all_frames.append(combined);
            } else {
                DataFrame combined = build_block(choices["selected_counties"], "Selected Counties");
                if (!combined.empty()) all_frames.append(combined);
                
                // Include individual county breakdowns if requested
                if (choices["include_breakdown"]) {
                    for (const auto& cty : choices["selected_counties"]) {
                        DataFrame cdf = build_block([cty], cty);
                        if (!cdf.empty()) all_frames.append(cdf);
                    }
                }
            }
            
            // Store final results
            st.session_state["report_df"] = (!all_frames.empty()) ? 
                pd.concat(all_frames, ignore_index=true) : pd.DataFrame();
            st.session_state["report_df"] = ensure_county_names(
                st.session_state["report_df"], counties_map
            );
        }
    }
    
    // ========================================================================
    // RESULTS DISPLAY SECTION
    // ========================================================================
    
    if (!st.session_state["report_df"].empty()) {
        st.success("✅ Data processing completed successfully!");
        
        st.markdown("## 📋 Processing Results");
        st.markdown('<div class="header-comment">// Generated data output</div>', unsafe_allow_html=true);
        
        // Display results dataframe
        st.dataframe(st.session_state["report_df"], use_container_width=true);
        
        // Export functionality
        st.markdown("## 💾 Data Export");
        st.markdown('<div class="header-comment">// Export processed data with metadata</div>', unsafe_allow_html=true);
        
        List[string] meta = [
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
        ];
        
        string csv_text = "\n".join(meta) + "\n" + st.session_state["report_df"].to_csv(index=false);
        
        st.download_button(
            "📥 Download CSV Report",
            data=csv_text,
            file_name="illinois_population_data.csv",
            mime="text/csv"
        );
    }
    
    // ========================================================================
    // FOOTER SECTION
    // ========================================================================
    
    st.markdown("---");
    st.markdown(
        "<div style='text-align:center;color:#666;font-family:Consolas;'>"
        "// Illinois Population Data Explorer • U.S. Census Bureau Data • 2000–2024"
        "</div>", 
        unsafe_allow_html=true
    );
}

// ============================================================================
// APPLICATION ENTRY POINT
// ============================================================================

if (__name__ == "__main__") {
    main();
}
