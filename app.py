import streamlit as st
import pandas as pd
import openpyxl  # For Excel operations
import os

# ------------------------------------------------------------------------
# Streamlit Page Config
st.set_page_config(
    page_title="Illinois Census Data Form",
    layout="wide"  # Keep "wide" so our custom CSS isn't overridden
)

# ------------------------------------------------------------------------
# Revised CSS: narrower container + left/right borders
st.markdown("""
<style>
/* Optional: Give the entire page a light gray background */
html, body, [data-testid="stAppViewContainer"], [data-testid="stAppView"] {
    background-color: #f2f2f2; /* Adjust color as desired */
}

/* Narrow the main content, add left/right borders, etc. */
.main .block-container {
    /* Limit container width (e.g. 1000px). Adjust to your preference. */
    max-width: 1000px !important;
    margin: 2rem auto !important;

    /* Add left and right “divider” borders */
    border-left: 10px solid #ccc;
    border-right: 10px solid #ccc;
    background-color: #fff;

    /* Internal padding so content doesn't touch borders */
    padding: 2rem !important;

    /* Optional: Slight rounding or shadow for a card-like look */
    border-radius: 4px;
    box-shadow: 0 2px 6px rgba(0,0,0,0.1);
}

/* Title container styling */
.title-container {
    text-align: center;
    background-color: #2c3e50;
    padding: 20px;
    border-radius: 6px;
    margin-bottom: 1rem;
}
.title-container h1 {
    color: #fff;
    margin: 0;
    font-family: "Segoe UI", sans-serif;
    font-size: 2rem;
}
.title-container p {
    color: #ddd;
    margin: 0.5rem 0 0;
}

/* Subheaders styling */
.stMarkdown h2, .stMarkdown h3 {
    color: #2c3e50 !important;
    font-family: "Segoe UI", sans-serif;
    margin-bottom: 0.5rem;
}

/* Labels and text */
.stMarkdown label, .stRadio label, .stSelectbox label, .stMultiSelect label {
    font-weight: 600 !important;
    color: #444 !important;
}

/* Buttons */
.stButton button {
    background-color: #2c3e50 !important; /* primary color */
    color: white !important;
    border-radius: 5px !important;
    font-size: 15px !important;
    padding: 0.6rem 1rem !important;
    border: none !important;
    cursor: pointer;
    margin-top: 0.5rem;
}
.stButton button:hover {
    background-color: #34495e !important; /* secondary color */
    color: white !important;
}

/* Table styling */
[data-testid="stDataFrame"] table, [data-testid="stDataEditor"] table {
    border: 1px solid #ddd;
    border-collapse: collapse;
}
[data-testid="stDataFrame"] th, [data-testid="stDataEditor"] th,
[data-testid="stDataFrame"] td, [data-testid="stDataEditor"] td {
    border: 1px solid #ddd;
    padding: 8px;
}

/* Container for the final report */
.report-container {
    background-color: #f9fffa;
    padding: 1rem;
    border-radius: 5px;
    margin-top: 1rem;
    border: 1px solid #eee;
}

/* Extra spacing between sections */
.section-separator {
    margin-top: 1rem;
    margin-bottom: 1rem;
    border: none;
    height: 1px;
    background: #eee;
}
</style>
""", unsafe_allow_html=True)

# ------------------------------------------------------------------------
# Try to load secrets; if not found, fall back to defaults.
try:
    paths = st.secrets.get("paths", {})
except FileNotFoundError:
    paths = {}

DATA_FOLDER = paths.get("data_folder", "./data")
FORM_CONTROL_PATH = paths.get("form_control_path", "./form_control_UI_data.csv")

# ------------------------------------------------------------------------
# Import your custom modules (ensure they're accessible in your PYTHONPATH)
import backend_main_processing
import frontend_data_loader
import frontend_bracket_utils

# ------------------------------------------------------------------------
# Bracket definitions and aggregation logic
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
    """Convert bracket code numbers to a merged numeric label, e.g. 0-4, 5-9, etc."""
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
                if parts[1].endswith("+"):
                    end = int(parts[1].replace("+", ""))
                    end = 999
                else:
                    end = int(parts[1])
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
        # Fallback if parsing fails
        return "-".join(str(c) for c in codes)
    overall_low = min(low_vals)
    overall_high = max(high_vals)
    return f"{overall_low}+" if overall_high >= 999 else f"{overall_low}-{overall_high}"

def aggregate_population_data(
    df_source: pd.DataFrame,
    year_str: str,
    agegroup_for_backend: str | None,
    custom_ranges: list[tuple[int,int]],
    agegroup_display: str,
    agegroup_map_implicit: dict,
):
    """
    Returns a DataFrame with columns: [AgeGroup, Count, Percent, Year].
    """
    if agegroup_for_backend is None and not custom_ranges:
        total_pop = df_source["Count"].sum() if not df_source.empty else 0
        return pd.DataFrame({
            "AgeGroup": ["IL Population"],
            "Count": [total_pop],
            "Percent": [100.0 if total_pop > 0 else 0.0],
            "Year": [year_str]
        })

    if custom_ranges:
        rows, total_sum = [], 0
        for (mn, mx) in custom_ranges:
            code_list = range(mn, mx+1)
            bracket_label = combine_codes_to_label(code_list)
            mask = df_source["Age"].isin(code_list)
            sub_sum = df_source.loc[mask, "Count"].sum()
            rows.append((bracket_label, sub_sum))
            total_sum += sub_sum
        out_rows = []
        for (bexpr, cval) in rows:
            pct = (cval / total_sum * 100.0) if total_sum > 0 else 0.0
            out_rows.append((bexpr, cval, round(pct,1)))
        return pd.DataFrame(out_rows, columns=["AgeGroup", "Count", "Percent"]).assign(Year=year_str)

    brackets_implicit = agegroup_map_implicit.get(agegroup_for_backend, [])
    if not brackets_implicit:
        total_pop = df_source["Count"].sum() if not df_source.empty else 0
        return pd.DataFrame({
            "AgeGroup": [f"No bracket for {agegroup_display}"],
            "Count": [total_pop],
            "Percent": [100.0 if total_pop > 0 else 0.0],
            "Year": [year_str]
        })

    if "Age" not in df_source.columns or df_source.empty:
        rows = [(br.strip(), 0) for br in brackets_implicit]
        total_sum = 0
    else:
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
    return pd.DataFrame(out_rows, columns=["AgeGroup", "Count", "Percent"]).assign(Year=year_str)

# ------------------------------------------------------------------------
# Handling rerun for older versions of Streamlit
try:
    from streamlit.runtime.scriptrunner import RerunException, RerunData
except ImportError:
    from streamlit.script_runner import RerunException
    from streamlit.script_runner import ScriptRequestQueue
    RerunData = ScriptRequestQueue.RerunData

def rerun():
    """Force a rerun in older versions of Streamlit."""
    raise RerunException(RerunData(None))

# ------------------------------------------------------------------------
def main():
    # -- Custom title block (centered and styled)
    st.markdown("""
    <div class="title-container">
      <h1>Illinois Census Data Form</h1>
      <p>A Streamlit web interface for selecting census data filters, generating population reports, and downloading results.</p>
    </div>
    """, unsafe_allow_html=True)

    # 1) Load form-control data
    (years_list,
     agegroups_list_raw,
     races_list_raw,
     counties_map,
     agegroup_map_explicit,
     agegroup_map_implicit) = frontend_data_loader.load_form_control_data(FORM_CONTROL_PATH)

    # Race display mapping
    RACE_DISPLAY_TO_CODE = {
        "Two or More Races": "TOM",
        "American Indian and Alaska Native": "AIAN",
        "Black or African American": "Black",
        "White": "White",
        "Native Hawaiian and Other Pacific Islander": "NHOPI",
        "Asian": "Asian"
    }

    race_display_list = ["All"]
    for rcode in sorted(races_list_raw):
        if rcode == "All":
            continue
        friendly_name = None
        for k, v in RACE_DISPLAY_TO_CODE.items():
            if v == rcode:
                friendly_name = k
                break
        race_display_list.append(friendly_name if friendly_name else rcode)

    # Age group display mapping
    AGEGROUP_DISPLAY_TO_CODE = {
        "All": "All",
        "18-Bracket": "agegroup13",
        "6-Bracket":  "agegroup14",
        "2-Bracket":  "agegroup15"
    }
    agegroup_display_list = list(AGEGROUP_DISPLAY_TO_CODE.keys())

    # -- Intro note
    st.markdown("<hr class='section-separator'/>", unsafe_allow_html=True)
    st.markdown("""
    **Note**: Custom Age Ranges override the Age Group selection.
    """)

    # ---------- LAYOUT FOR SELECTION CONTROLS ----------
    with st.container():
        col1, col2, col3 = st.columns([1.2, 1.2, 1.6])

        # -- COL1: Year(s) & Counties
        with col1:
            st.subheader("Selection Controls")
            selected_years = st.multiselect(
                "Year(s)",
                options=years_list,
                default=[],
                help="Select one or more years to analyze"
            )
            all_counties = ["All"] + sorted(counties_map.keys())
            selected_counties = st.multiselect(
                "Select Counties",
                options=all_counties,
                default=[],
                help="Choose which counties to include. 'All' will include every county."
            )

        # -- COL2: AgeGroup, Race and Demographic Filters
        with col2:
            st.subheader("Demographic Filters")
            selected_agegroup_display = st.selectbox(
                "Age Group",
                agegroup_display_list,
                index=0,
                help="Choose a preset age bracket grouping, or use Custom Age Ranges instead."
            )

            if selected_agegroup_display != "All":
                agegroup_code = AGEGROUP_DISPLAY_TO_CODE.get(selected_agegroup_display, None)
                brackets_implicit = agegroup_map_implicit.get(agegroup_code, [])
                if brackets_implicit:
                    st.markdown("**Selected Age Brackets (Implicit):** " + ", ".join(brackets_implicit))
                else:
                    st.markdown("*No bracket expressions found for this Age Group.*")

            selected_race_display = st.selectbox(
                "Race",
                race_display_list,
                index=0,
                help="Select a race category. 'All' will include every race."
            )

            # Radio selections in one row
            with st.expander("Advanced Demographics", expanded=False):
                st.write("Use these filters to further refine the data:")
                c_reg, c_eth, c_sex = st.columns(3)
                with c_reg:
                    region_options = ["None", "Collar Counties", "Urban Counties", "Rural Counties"]
                    selected_region = st.radio(
                        "Region",
                        options=region_options,
                        index=0,
                        help="Filter by a predefined region grouping",
                        label_visibility="collapsed"
                    )
                with c_eth:
                    ethnicity_options = ["All", "Hispanic", "Not Hispanic"]
                    selected_ethnicity = st.radio(
                        "Ethnicity",
                        options=ethnicity_options,
                        index=0,
                        help="Filter by Hispanic or Not Hispanic",
                        label_visibility="collapsed"
                    )
                with c_sex:
                    sex_options = ["All", "Male", "Female"]
                    selected_sex = st.radio(
                        "Sex",
                        options=sex_options,
                        index=0,
                        help="Filter by sex",
                        label_visibility="collapsed"
                    )

        # -- COL3: Custom Age Ranges
        with col3:
            st.subheader("Custom Age Ranges")
            st.caption("Valid Age codes: 1..18. These override the Age Group selection.")
            custom_age_ranges_inputs = []
            age_options = [""] + [str(i) for i in range(1, 19)]
            for i in range(1, 6):
                c1, c2 = st.columns(2)
                min_val = c1.selectbox(
                    f"Min{i}",
                    age_options,
                    index=0,
                    help="Minimum age code",
                    key=f"min_{i}"
                )
                max_val = c2.selectbox(
                    f"Max{i}",
                    age_options,
                    index=0,
                    help="Maximum age code",
                    key=f"max_{i}"
                )
                custom_age_ranges_inputs.append((min_val, max_val))

    st.markdown("<hr class='section-separator'/>", unsafe_allow_html=True)

    # ---------- Display currently selected filters ----------
    with st.expander("Currently Selected Filters", expanded=False):
        st.write(f"**Years:** {', '.join(selected_years) if selected_years else 'None'}")
        st.write(f"**Counties:** {', '.join(selected_counties) if selected_counties else 'None'}")
        st.write(f"**Age Group:** {selected_agegroup_display}")
        st.write(f"**Race:** {selected_race_display}")
        st.write(f"**Region:** {selected_region if 'selected_region' in locals() else 'None'}")
        st.write(f"**Ethnicity:** {selected_ethnicity if 'selected_ethnicity' in locals() else 'All'}")
        st.write(f"**Sex:** {selected_sex if 'selected_sex' in locals() else 'All'}")

    # ---------- BUTTONS ROW ----------
    st.markdown("<hr class='section-separator'/>", unsafe_allow_html=True)
    btn_col1, btn_col2, btn_col3, btn_col4 = st.columns(4)
    generate_button = btn_col1.button("Generate Report")
    clear_report_button = btn_col2.button("Clear Report")
    census_links_button = btn_col3.button("Census Links")
    download_button = btn_col4.button("Download Output")

    # ---------- Clear Report Logic ----------
    if clear_report_button:
        if "report_df" in st.session_state:
            del st.session_state["report_df"]
        st.info("Report cleared.")
        st.stop()

    # ---------- Census Links ----------
    if census_links_button:
        with st.expander("Census Data Links", expanded=True):
            st.write("Below are important links to access the data information:")
            links_data = [
                "https://www2.census.gov/programs-surveys/popest/datasets/",
                "https://www2.census.gov/programs-surveys/popest/datasets/2000-2010/intercensal/county/",
                "https://www2.census.gov/programs-surveys/popest/datasets/2010-2020/counties/asrh/",
                "https://www2.census.gov/programs-surveys/popest/datasets/2020-2023/counties/asrh/",
                "RELEASE SCHEDULE: https://www.census.gov/programs-surveys/popest/about/schedule.html"
            ]
            for link in links_data:
                if link.startswith("RELEASE SCHEDULE: "):
                    label = link.split("RELEASE SCHEDULE: ")[1]
                    st.markdown(f"- [{label}]({label})")
                else:
                    st.markdown(f"- [{link}]({link})")

    # ---------- Generate Report ----------
    if generate_button:
        # Validate mandatory selection
        if not selected_years:
            st.warning("Please select at least one year.")
            st.stop()

        # Convert Race display -> code
        if selected_race_display == "All":
            selected_race_code = "All"
        else:
            found_code = False
            for k, v in RACE_DISPLAY_TO_CODE.items():
                if k == selected_race_display:
                    selected_race_code = v
                    found_code = True
                    break
            if not found_code:
                selected_race_code = selected_race_display

        # Convert AgeGroup display -> code
        if selected_agegroup_display == "All":
            agegroup_for_backend = None
        else:
            agegroup_for_backend = AGEGROUP_DISPLAY_TO_CODE[selected_agegroup_display]

        # Parse custom age ranges (with validation)
        parsed_custom_ranges = []
        for (min_val, max_val) in custom_age_ranges_inputs:
            min_val = min_val.strip()
            max_val = max_val.strip()
            if min_val.isdigit() and max_val.isdigit():
                mn = int(min_val)
                mx = int(max_val)
                if 1 <= mn <= 18 and 1 <= mx <= 18:
                    if mn <= mx:
                        parsed_custom_ranges.append((mn, mx))
                    else:
                        st.warning(f"Invalid range: Min({mn}) > Max({mx}). Range ignored.")
                else:
                    st.warning(f"Age codes must be between 1 and 18. Range {mn}-{mx} ignored.")
            elif min_val or max_val:
                st.warning(f"Invalid custom age range inputs '{min_val}' - '{max_val}'. Ignored.")

        # Process data with a spinner (progress indicator)
        with st.spinner("Generating report..."):
            combined_frames = []
            for year in selected_years:
                df_source = backend_main_processing.process_population_data(
                    data_folder=DATA_FOLDER,
                    agegroup_map_explicit=agegroup_map_explicit,
                    counties_map=counties_map,
                    selected_years=[year],
                    selected_counties=selected_counties,
                    selected_race=selected_race_code,
                    selected_ethnicity=selected_ethnicity,
                    selected_sex=selected_sex,
                    selected_region=selected_region,
                    selected_agegroup=agegroup_for_backend,
                    custom_age_ranges=parsed_custom_ranges
                )

                aggregated_df = aggregate_population_data(
                    df_source=df_source,
                    year_str=year,
                    agegroup_for_backend=agegroup_for_backend,
                    custom_ranges=parsed_custom_ranges,
                    agegroup_display=selected_agegroup_display,
                    agegroup_map_implicit=agegroup_map_implicit
                )
                combined_frames.append(aggregated_df)

            if combined_frames:
                final_df = pd.concat(combined_frames, ignore_index=True)
            else:
                final_df = pd.DataFrame()

        if final_df.empty:
            st.info("No data found for the selected filters.")
        else:
            # Store the result in session_state
            st.session_state["report_df"] = final_df

            # Summary statistics
            total_count = final_df["Count"].sum() if "Count" in final_df.columns else 0
            st.success("Report Generated Successfully!")
            st.write(f"**Summary**: Total Count = {total_count}")

            # Display Data
            with st.container():
                st.markdown('<div class="report-container">', unsafe_allow_html=True)
                st.dataframe(final_df, use_container_width=True)
                st.markdown('</div>', unsafe_allow_html=True)

    # ---------- Download Button ----------
    if download_button:
        if "report_df" not in st.session_state or st.session_state["report_df"].empty:
            st.warning("No report available. Please generate a report first.")
        else:
            final_df = st.session_state["report_df"]
            csv_data = final_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="Download CSV",
                data=csv_data,
                file_name="population_report.csv",
                mime="text/csv",
            )

if __name__ == "__main__":
    main()
