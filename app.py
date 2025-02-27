import streamlit as st
import pandas as pd
import tempfile
import os
from datetime import datetime

# Import backend modules
import backend_main_processing
import frontend_data_loader
import frontend_bracket_utils

# Constants
DATA_FOLDER = "data"
FORM_CONTROL_PATH = "form_control_UI_data.csv"

# Race Mapping
RACE_DISPLAY_TO_CODE = {
    "Two or More Races": "TOM",
    "American Indian and Alaska Native": "AIAN",
    "Black or African American": "Black",
    "White": "White",
    "Native Hawaiian and Other Pacific Islander": "NHOPI",
    "Asian": "Asian"
}

# AgeGroup Mapping
AGEGROUP_DISPLAY_TO_CODE = {
    "All": "All",
    "18-Bracket": "agegroup13",
    "6-Bracket":  "agegroup14",
    "2-Bracket":  "agegroup15"
}

# Initialize session state
if 'filtered_data_for_download' not in st.session_state:
    st.session_state.filtered_data_for_download = pd.DataFrame()
if 'results_for_display' not in st.session_state:
    st.session_state.results_for_display = []

def main():
    # Page Config
    st.set_page_config(
        page_title="Illinois Census Data Form",
        page_icon="📊",
        layout="wide"
    )
    
    # Title
    st.title("Illinois Census Data Form")
    
    # Load form control data
    (years_list,
     agegroups_list_raw,
     races_list_raw,
     counties_map,
     agegroup_map_explicit,
     agegroup_map_implicit) = frontend_data_loader.load_form_control_data(FORM_CONTROL_PATH)
    
    # Create columns for layout
    col1, col2, col3 = st.columns(3)
    
    # Left Column (Years & Counties)
    with col1:
        st.subheader("Selection Controls")
        
        # Year Selection (multiselect instead of listbox)
        selected_years = st.multiselect(
            "Year Selection:",
            options=years_list,
            default=[years_list[0]] if years_list else None
        )
        
        # Counties Selection
        county_options = ["All"] + sorted(counties_map.keys())
        selected_counties = st.multiselect(
            "Select Counties:",
            options=county_options
        )
    
    # Middle Column (Age Group, Race, Ethnicity, Sex, Region)
    with col2:
        st.subheader("Demographic Filters")
        
        # Age Group Selection
        agegroup_display_list = list(AGEGROUP_DISPLAY_TO_CODE.keys())
        selected_agegroup = st.selectbox(
            "Age Group:",
            options=agegroup_display_list,
            index=0
        )
        
        # Show selected age brackets
        if selected_agegroup != "All":
            agegroup_code = AGEGROUP_DISPLAY_TO_CODE.get(selected_agegroup, "All")
            brackets_implicit = agegroup_map_implicit.get(agegroup_code, [])
            if brackets_implicit:
                st.write("Selected Age Brackets (Implicit):")
                for expr in brackets_implicit:
                    st.write(f"- {expr}")
        
        # Race Selection
        race_display_list = ["All"] + [k for k in RACE_DISPLAY_TO_CODE.keys()]
        selected_race = st.selectbox(
            "Race:",
            options=race_display_list,
            index=0
        )
        
        # Ethnicity Selection
        selected_ethnicity = st.radio(
            "Ethnicity:",
            options=["All", "Hispanic", "Not Hispanic"],
            horizontal=True
        )
        
        # Sex Selection
        selected_sex = st.radio(
            "Sex:",
            options=["All", "Male", "Female"],
            horizontal=True
        )
        
        # Region Selection
        selected_region = st.radio(
            "Regional Counties:",
            options=["None", "Collar Counties", "Urban Counties", "Rural Counties"],
            horizontal=True
        )
    
    # Right Column (Custom Age Ranges)
    with col3:
        st.subheader("Custom Age Ranges")
        st.write("Enter min and max values (1-18)")
        
        custom_ranges = []
        for i in range(1, 6):
            col_min, col_max = st.columns(2)
            with col_min:
                min_val = st.number_input(f"Min {i}", min_value=1, max_value=18, value=1, key=f"min_{i}")
            with col_max:
                max_val = st.number_input(f"Max {i}", min_value=1, max_value=18, value=1, key=f"max_{i}")
            if min_val <= max_val:
                custom_ranges.append((min_val, max_val))
        
        st.info("Note: Custom Age Ranges override the Age Group selection above.")
    
    # Generate Report Button
    if st.button("Generate Report", type="primary"):
        if not selected_years:
            st.warning("Please select at least one year.")
            return
        
        # Convert Race display to code
        selected_race_code = "All" if selected_race == "All" else RACE_DISPLAY_TO_CODE.get(selected_race, selected_race)
        
        # Convert AgeGroup display to code
        selected_agegroup_code = AGEGROUP_DISPLAY_TO_CODE.get(selected_agegroup, None)
        agegroup_for_backend = None if selected_agegroup_code == "All" else selected_agegroup_code
        
        counties_str = ", ".join(selected_counties) if selected_counties else "No counties selected."
        
        combined_frames = []
        st.session_state.results_for_display = []
        
        years_title = f"({selected_years[0]})" if len(selected_years) == 1 else f"({', '.join(selected_years)})"
        
        with st.spinner("Generating report..."):
            for year_str in selected_years:
                df = backend_main_processing.process_population_data(
                    data_folder=DATA_FOLDER,
                    agegroup_map_explicit=agegroup_map_explicit,
                    counties_map=counties_map,
                    selected_years=[year_str],
                    selected_counties=selected_counties,
                    selected_race=selected_race_code,
                    selected_ethnicity=selected_ethnicity,
                    selected_sex=selected_sex,
                    selected_region=selected_region,
                    selected_agegroup=agegroup_for_backend,
                    custom_age_ranges=custom_ranges
                )
                
                # Process results similar to Tkinter version
                # ... [Result processing logic remains the same]
                
                if df is not None and not df.empty:
                    st.write(f"Results for {year_str}:")
                    st.dataframe(df)
                    combined_frames.append(df)
        
        if combined_frames:
            st.session_state.filtered_data_for_download = pd.concat(combined_frames, ignore_index=True)
            
            # Download buttons
            col1, col2 = st.columns(2)
            with col1:
                csv = st.session_state.filtered_data_for_download.to_csv(index=False)
                st.download_button(
                    "Download CSV",
                    csv,
                    "census_data.csv",
                    "text/csv",
                    key='download-csv'
                )
            
            with col2:
                excel_buffer = tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx')
                with pd.ExcelWriter(excel_buffer.name) as writer:
                    for year_str, df in zip(selected_years, combined_frames):
                        df.to_excel(writer, sheet_name=str(year_str), index=False)
                st.download_button(
                    "Download Excel",
                    open(excel_buffer.name, 'rb').read(),
                    "census_data.xlsx",
                    key='download-excel'
                )
                
        else:
            st.warning("No data found for the selected filters.")
    
    # Census Links
    with st.expander("Census Data Links"):
        st.write("""
        - [Census Datasets](https://www2.census.gov/programs-surveys/popest/datasets/)
        - [2000-2010 Intercensal County Data](https://www2.census.gov/programs-surveys/popest/datasets/2000-2010/intercensal/county/)
        - [2010-2020 County Data](https://www2.census.gov/programs-surveys/popest/datasets/2010-2020/counties/asrh/)
        - [2020-2023 County Data](https://www2.census.gov/programs-surveys/popest/datasets/2020-2023/counties/asrh/)
        - [Release Schedule](https://www.census.gov/programs-surveys/popest/about/schedule.html)
        """)

if __name__ == "__main__":
    main()
