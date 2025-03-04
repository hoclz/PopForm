import streamlit as st
import pandas as pd
import openpyxl  # For Excel operations
import os
import geopandas as gpd
import matplotlib.pyplot as plt
import io, base64

# ------------------------------------------------------------------------
# Setup for Illinois Outline
LINE_COLOR = "#ADD8E6"  # choose a color for the outline
ILLINOIS_GEOJSON_URL = "https://raw.githubusercontent.com/codeforamerica/click_that_hood/master/public/data/illinois-counties.geojson"

# Load the Illinois counties GeoJSON and compute the state boundary
illinois = gpd.read_file(ILLINOIS_GEOJSON_URL).to_crs(epsg=26971)
state_boundary = illinois.dissolve()

def add_illinois_outline(ax, boundary_gdf, position, zoom, zoom_factor=1.1):
    """
    Adds a zoomed inset of the Illinois outline to the given axis.
    
    Parameters:
    - ax: The parent axes.
    - boundary_gdf: A GeoDataFrame with the Illinois boundary.
    - position: [x, y] coordinates (as fractions of the parent axes) for the inset.
    - zoom: The width and height of the inset axes (as fractions of the parent axes).
    - zoom_factor: A multiplier (0 < zoom_factor <= 1) to determine the extent of the geometry to show.
                   Lower values zoom in more.
    """
    # Create an inset axis within ax
    inset_ax = ax.inset_axes([position[0], position[1], zoom, zoom])
    
    # Plot the boundary with increased linewidth and a custom color
    boundary_gdf.boundary.plot(ax=inset_ax, linewidth=10, edgecolor=LINE_COLOR)
    
    # Get the total bounds of the geometry (xmin, ymin, xmax, ymax)
    xmin, ymin, xmax, ymax = boundary_gdf.total_bounds
    # Compute the center of the geometry
    x_center = (xmin + xmax) / 2
    y_center = (ymin + ymax) / 2
    # Compute width and height based on the zoom_factor
    width = (xmax - xmin) * zoom_factor
    height = (ymax - ymin) * zoom_factor
    # Set the limits of the inset axis to "zoom in" on the center
    inset_ax.set_xlim(x_center - width/2, x_center + width/2)
    inset_ax.set_ylim(y_center - height/2, y_center + height/2)
    inset_ax.axis('off')


def get_illinois_outline_image():
    """
    Generates a small matplotlib figure containing the Illinois outline,
    saves it to a PNG in memory, and returns a base64-encoded string.
    """
    fig, ax = plt.subplots(figsize=(4, 4))
    # Draw the outline on the entire figure (using almost full inset space)
    add_illinois_outline(ax, state_boundary, (0.2, 0.1), 0.8)
    ax.axis('off')
    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight', transparent=True)
    plt.close(fig)
    buf.seek(0)
    img_base64 = base64.b64encode(buf.read()).decode('utf-8')
    return img_base64

# Generate the base64 image string for the Illinois outline
outline_img_base64 = get_illinois_outline_image()

# ------------------------------------------------------------------------
# Streamlit Page Config
st.set_page_config(
    page_title="Illinois Census Query Builder",
    layout="wide",  
    page_icon=":rocket:"
)

############################################################################
# 1) Custom CSS – includes .outer-frame and left/right column fill
############################################################################
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Roboto:wght@400;500;700&display=swap');

/* Global styling */
html, body, [data-testid="stAppViewContainer"], [data-testid="stAppView"] {
    font-family: 'Roboto', sans-serif;
    background-color: #f0f2f6;
    margin: 0;
    padding: 0;
}
.main .block-container {
    max-width: 100%;
    margin: 0;
    padding: 0;
    background-color: transparent;
    box-shadow: none;
}

/* The outer frame around everything in the middle column */
.outer-frame {
    border: 2px solid #ccc;
    border-radius: 8px;
    padding: 2rem;
    margin: 1rem;
    background-color: #fff;
}

/* LEFT & RIGHT columns fill color.
   You can change "rgb(240, 240, 240)" to any other color. */
.fill-column {
    background-color: rgb(180, 220, 220);
    /* Adjust min-height so the fill is visible behind the center content. */
    min-height: 2200px;
}

/* "Hero" banner styling */
.hero-banner {
    background: linear-gradient(135deg, #262626, #333333);
    color: #ffffff;
    padding: 3rem 2rem;
    border-radius: 0.5rem;
    margin-bottom: 1.5rem;
    text-align: center;
}
.hero-banner h1 {
    font-weight: 700;
    font-size: 2.2rem;
    margin-bottom: 0.2rem;
}
.hero-banner p {
    font-size: 1.1rem;
    margin-top: 0.5rem;
}

/* Button row at the top */
.button-row {
    text-align: center;
    margin-bottom: 1rem;
}
.button-row .stButton button {
    background-color: #444444 !important;
    color: #ffffff !important;
    border: none !important;
    border-radius: 20px !important;
    padding: 0.6rem 1.4rem !important;
    margin: 0 0.3rem;
    font-weight: 500;
    font-size: 0.9rem;
    transition: background-color 0.3s ease;
}
.button-row .stButton button:hover {
    background-color: #5c5c5c !important;
}

/* Query builder container */
.query-builder-container {
    background-color: #ffffff;
    border-radius: 0.5rem;
    padding: 1.5rem;
    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    margin-bottom: 1.5rem;
}

/* Table container (report) */
.report-container {
    background-color: #ffffff;
    padding: 1.5rem;
    border-radius: 0.5rem;
    margin-top: 1.5rem;
    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
}

/* Make table header bold & styled */
[data-testid="stDataFrame"] thead tr th, [data-testid="stDataEditor"] thead tr th {
    font-weight: 600 !important;
    background-color: #e9ecef !important;
    padding: 0.75rem !important;
}
[data-testid="stDataFrame"] table,
[data-testid="stDataEditor"] table {
    border: 1px solid #dee2e6;
    border-collapse: collapse;
    margin-top: 0.5rem;
}
[data-testid="stDataFrame"] th, [data-testid="stDataFrame"] td,
[data-testid="stDataEditor"] th, [data-testid="stDataEditor"] td {
    border: 1px solid #dee2e6;
    padding: 0.6rem;
    font-size: 0.9rem;
}

/* Minor separation lines */
.query-separator {
    margin: 1rem 0;
    border: none;
    height: 1px;
    background: #e0e0e0;
}

/* ----------------------- */
/* Added outline for all dropdown lists */
div[data-baseweb="select"] {
    border: 2px solid #ccc;
    border-radius: 4px;
    padding: 2px;
}
</style>
""", unsafe_allow_html=True)

# ------------------------------------------------------------------------
# Try to load secrets; if not found, fall back to defaults
try:
    paths = st.secrets.get("paths", {})
except FileNotFoundError:
    paths = {}
DATA_FOLDER = paths.get("data_folder", "./data")
FORM_CONTROL_PATH = paths.get("form_control_path", "./form_control_UI_data.csv")

# ------------------------------------------------------------------------
# Import your existing backend code
import backend_main_processing
import frontend_data_loader
import frontend_bracket_utils

# ------------------------------------------------------------------------
# Race and bracket definitions:
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
    """Same bracket logic as before."""
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
# AGGREGATOR 1: Age-based brackets
# ------------------------------------------------------------------------
def aggregate_age_with_brackets(
    df_source: pd.DataFrame,
    year_str: str,
    agegroup_for_backend: str | None,
    custom_ranges: list[tuple[int,int]],
    agegroup_display: str,
    agegroup_map_implicit: dict
) -> pd.DataFrame:
    """
    Aggregates data by age brackets (or custom ranges).
    Always returns a valid DataFrame, never None.
    """
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

# ------------------------------------------------------------------------
# AGGREGATOR 2: Generic Group By
# ------------------------------------------------------------------------
def aggregate_by_field(
    df_source: pd.DataFrame,
    group_by: str,
    year_str: str,
    county_id_to_name: dict
) -> pd.DataFrame:
    """
    Aggregates by Race, Ethnicity, Sex, or County.
    Returns columns based on group_by:
        - If County => [County Code, County Name, Count, Percent, Year]
        - Else => [group_by, Count, Percent, Year]
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
# Handling rerun for older Streamlit
try:
    from streamlit.runtime.scriptrunner import RerunException, RerunData
except ImportError:
    from streamlit.script_runner import RerunException
    from streamlit.script_runner import ScriptRequestQueue
    RerunData = ScriptRequestQueue.RerunData

def rerun():
    raise RerunException(RerunData(None))

# ------------------------------------------------------------------------
# HERO BANNER with Illinois Outline
# Here we insert the outline image (as a base64-encoded PNG) before the word "Illinois" in the title.
hero_html = f"""
<div class='hero-banner'>
    <h1 style="width: 100%; text-align: center; font-size: 3rem; color: #87CEFA;">
        <img src="data:image/png;base64,{outline_img_base64}" style="vertical-align: middle; margin-right: 5px; height: 80px;" />
        Illinois Population | U.S. Census Data | 2000 - 2023
    </h1>
    <p style="font-size: 1.2rem; color: #ADD8E6;">
        Users can utilize this tool to query CC-EST2000-2023-ALLDATA-[ST-FIPS] annual county-level population estimates broken down by age, sex, race, and hispanic origin.<br>
    </p>
</div>
"""

# ------------------------------------------------------------------------
def main():
    # Create three columns with [1,4,1] ratio
    col_left, col_center, col_right = st.columns([2, 3, 2])

    # Fill color on the left column
    with col_left:
        st.markdown("<div class='fill-column'></div>", unsafe_allow_html=True)

    # Fill color on the right column
    with col_right:
        st.markdown("<div class='fill-column'></div>", unsafe_allow_html=True)

    # Place the entire UI in the center column
    with col_center:
        # Outer frame start
        st.markdown("<div class='outer-frame'>", unsafe_allow_html=True)

        # Insert the Hero Banner with the Illinois outline image
        st.markdown(hero_html, unsafe_allow_html=True)

        # Buttons row
        st.markdown("<div class='button-row'>", unsafe_allow_html=True)
        colA, colB, colC, colD = st.columns([1,1,1,1])
        with colA:
            generate_button = st.button("Generate Report")
        with colB:
            clear_report_button = st.button("Clear Report")
        with colC:
            census_links_button = st.button("Census Links")
        with colD:
            download_button = st.button("Download Output")
        st.markdown("</div>", unsafe_allow_html=True)

        # An expander for "Currently Selected Filters"
        filters_container = st.expander("Currently Selected Filters", expanded=False)

        # If user wants census links
        if census_links_button:
            with st.expander("Census Data Links", expanded=True):
                st.write("""
                **Important Links**:
                - [Census Datasets](https://www2.census.gov/programs-surveys/popest/datasets/)
                - [2000-2010 Intercensal County](https://www2.census.gov/programs-surveys/popest/datasets/2000-2010/intercensal/county/)
                - [2010-2020 County ASRH](https://www2.census.gov/programs-surveys/popest/datasets/2010-2020/counties/asrh/)
                - [2020-2023 County ASRH](https://www2.census.gov/programs-surveys/popest/datasets/2020-2023/counties/asrh/)
                - [RELEASE SCHEDULE](https://www.census.gov/programs-surveys/popest/about/schedule.html)
                """)

        # If user wants to download
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

        # If user wants to clear
        if clear_report_button:
            if "report_df" in st.session_state:
                del st.session_state["report_df"]
            st.info("Report cleared.")
            st.stop()

        # Query builder container
        st.markdown("<div class='query-builder-container'>", unsafe_allow_html=True)
        st.markdown("### Step 1: Load form data & Basic Filters")

        # Load your form-control data
        (years_list,
         agegroups_list_raw,
         races_list_raw,
         counties_map,
         agegroup_map_explicit,
         agegroup_map_implicit) = frontend_data_loader.load_form_control_data(FORM_CONTROL_PATH)

        # Build race filter list
        race_filter_list = ["All"]
        sorted_codes = sorted(RACE_DISPLAY_TO_CODE.values())
        for code in sorted_codes:
            friendly = RACE_CODE_TO_DISPLAY.get(code, code)
            race_filter_list.append(friendly)

        AGEGROUP_DISPLAY_TO_CODE = {
            "All": "All",
            "18-Bracket": "agegroup13",
            "6-Bracket":  "agegroup14",
            "2-Bracket":  "agegroup15"
        }

        # County ID <-> Name maps
        COUNTY_NAME_TO_ID = counties_map  
        COUNTY_ID_TO_NAME = {v: k for k, v in COUNTY_NAME_TO_ID.items()}

        # Basic filters in 2 columns
        cA, cB = st.columns(2)
        with cA:
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
                help="Choose which counties to include. 'All' = every county."
            )

        with cB:
            selected_agegroup_display = st.selectbox(
                "Age Group",
                list(AGEGROUP_DISPLAY_TO_CODE.keys()),
                index=0,
                help="Choose a preset age bracket grouping, or use Custom Age Ranges."
            )
            if selected_agegroup_display != "All":
                agegroup_code = AGEGROUP_DISPLAY_TO_CODE.get(selected_agegroup_display)
                brackets_implicit = agegroup_map_implicit.get(agegroup_code, [])
                if brackets_implicit:
                    st.markdown(f"**Selected Age Brackets:** {', '.join(brackets_implicit)}")
                else:
                    st.markdown("*No bracket expressions found.*")

            selected_race_display = st.selectbox(
                "Race Filter",
                race_filter_list,
                index=0,
                help="Restrict data by race. 'All' includes all races."
            )

        st.markdown("<hr class='query-separator'>", unsafe_allow_html=True)
        st.markdown("### Step 2: Advanced Demographics (Optional)")

        region_options = ["None", "Collar Counties", "Urban Counties", "Rural Counties"]
        selected_region = st.radio("Region", options=region_options, index=0)

        ethnicity_options = ["All", "Hispanic", "Not Hispanic"]
        selected_ethnicity = st.radio("Ethnicity", options=ethnicity_options, index=0)

        sex_options = ["All", "Male", "Female"]
        selected_sex = st.radio("Sex", options=sex_options, index=0)

        st.markdown("<hr class='query-separator'>", unsafe_allow_html=True)
        st.markdown("### Step 3: Custom Age Ranges (Optional)")
        st.caption("Valid Age codes: 1..18. These override the Age Group selection.")
        custom_age_ranges_inputs = []
        age_opts = [""] + [str(i) for i in range(1,19)]
        for i in range(1,6):
            cc1, cc2, cc3, cc4 = st.columns([0.5,1,0.5,1])
            with cc1:
                st.markdown(f"**Min{i}**")
            with cc2:
                min_val = st.selectbox("", age_opts, index=0, key=f"min_{i}", label_visibility="collapsed")
            with cc3:
                st.markdown(f"**Max{i}**")
            with cc4:
                max_val = st.selectbox("", age_opts, index=0, key=f"max_{i}", label_visibility="collapsed")
            custom_age_ranges_inputs.append((min_val, max_val))

        st.markdown("<hr class='query-separator'>", unsafe_allow_html=True)
        st.markdown("### Step 4: Grouping Variable (Optional)")
        group_options = ["", "Age", "Race", "Ethnicity", "Sex", "County"]
        grouping_var = st.selectbox("Group By", group_options, index=0)

        st.markdown("</div>", unsafe_allow_html=True)  # end query-builder-container

        # Fill the "Currently Selected Filters" container
        with filters_container:
            st.write(f"**Years:** {', '.join(selected_years) if selected_years else 'None'}")
            st.write(f"**Counties:** {', '.join(selected_counties) if selected_counties else 'All'}")
            st.write(f"**Age Group:** {selected_agegroup_display}")
            st.write(f"**Race Filter:** {selected_race_display}")
            st.write(f"**Region:** {selected_region}")
            st.write(f"**Ethnicity:** {selected_ethnicity}")
            st.write(f"**Group By:** {grouping_var if grouping_var else '(None)'}")

        # -- Generate report logic --
        if generate_button:
            if not selected_years:
                st.warning("Please select at least one year.")
                st.stop()

            # Race filter display -> code
            if selected_race_display == "All":
                selected_race_code = "All"
            else:
                selected_race_code = RACE_CODE_TO_DISPLAY.get(selected_race_display, selected_race_display)

            # Age group code
            if selected_agegroup_display == "All":
                agegroup_for_backend = None
            else:
                agegroup_for_backend = AGEGROUP_DISPLAY_TO_CODE[selected_agegroup_display]

            # Parse custom ranges
            parsed_custom_ranges = []
            for (mn_val, mx_val) in custom_age_ranges_inputs:
                mn_val, mx_val = mn_val.strip(), mx_val.strip()
                if mn_val.isdigit() and mx_val.isdigit():
                    mn, mx = int(mn_val), int(mx_val)
                    if 1 <= mn <= 18 and 1 <= mx <= 18:
                        if mn <= mx:
                            parsed_custom_ranges.append((mn, mx))
                        else:
                            st.warning(f"Invalid range: Min({mn}) > Max({mx}). Ignored.")
                    else:
                        st.warning(f"Age codes must be 1..18. Range {mn}-{mx} ignored.")
                elif mn_val or mx_val:
                    st.warning(f"Invalid custom age range '{mn_val}' - '{mx_val}'. Ignored.")

            all_frames = []

            def get_aggregated_result(county_list, county_label):
                frames_for_years = []
                for year in selected_years:
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
                        custom_age_ranges=parsed_custom_ranges
                    )

                    if grouping_var == "":
                        age_df = aggregate_age_with_brackets(
                            df_source=df_source,
                            year_str=year,
                            agegroup_for_backend=agegroup_for_backend,
                            custom_ranges=parsed_custom_ranges,
                            agegroup_display=selected_agegroup_display,
                            agegroup_map_implicit=agegroup_map_implicit
                        )
                        # Insert County column if the DataFrame is valid
                        if not age_df.empty:
                            age_df.insert(0, "County", county_label)
                        else:
                            age_df["County"] = county_label
                        frames_for_years.append(age_df)

                    elif grouping_var == "Age":
                        age_df = aggregate_age_with_brackets(
                            df_source=df_source,
                            year_str=year,
                            agegroup_for_backend=agegroup_for_backend,
                            custom_ranges=parsed_custom_ranges,
                            agegroup_display=selected_agegroup_display,
                            agegroup_map_implicit=agegroup_map_implicit
                        )
                        if not age_df.empty:
                            age_df.insert(0, "County", county_label)
                        else:
                            age_df["County"] = county_label
                        frames_for_years.append(age_df)

                    else:
                        group_df = aggregate_by_field(df_source, grouping_var, year, COUNTY_ID_TO_NAME)
                        if grouping_var != "County":
                            if not group_df.empty:
                                group_df.insert(0, "County", county_label)
                            else:
                                group_df["County"] = county_label
                        frames_for_years.append(group_df)

                if frames_for_years:
                    return pd.concat(frames_for_years, ignore_index=True)
                return pd.DataFrame()

            if not selected_counties:
                # If user didn't pick counties => treat as "All"
                df_combined = get_aggregated_result(["All"], "All-Counties")
                all_frames.append(df_combined)
            else:
                # Summation across all selected
                sum_label = "All-Selected-Counties"
                df_combined = get_aggregated_result(selected_counties, sum_label)
                all_frames.append(df_combined)

                # Individual county breakdown
                for c in selected_counties:
                    if c == "All":
                        label = "ALL-COUNTIES-STATEWIDE"
                        if grouping_var == "County":
                            county_keys = sorted(counties_map.keys())
                            df_single = get_aggregated_result(county_keys, label)
                        else:
                            df_single = get_aggregated_result(["All"], label)
                    else:
                        label = c
                        df_single = get_aggregated_result([c], label)
                    all_frames.append(df_single)

            if all_frames:
                final_df = pd.concat(all_frames, ignore_index=True)
            else:
                final_df = pd.DataFrame()

            if final_df.empty:
                st.info("No data found for the selected filters.")
            else:
                st.session_state["report_df"] = final_df
                total_count = final_df["Count"].sum() if "Count" in final_df.columns else 0
                st.success("Report Generated Successfully!")
                st.write(f"**Summary**: **Total Count** = {total_count:,}")
                with st.container():
                    st.markdown('<div class="report-container">', unsafe_allow_html=True)
                    st.dataframe(final_df, use_container_width=True)
                    st.markdown('</div>', unsafe_allow_html=True)

        # -- Close the outer-frame --
        st.markdown("</div>", unsafe_allow_html=True)

def parse_implicit_bracket(df_source, bracket_expr):
    """
    Placeholder or pass-through logic for bracket expressions if your real code is in:
    frontend_bracket_utils.parse_implicit_bracket(...).
    """
    return frontend_bracket_utils.parse_implicit_bracket(df_source, bracket_expr)

if __name__ == "__main__":
    main()
