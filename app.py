import streamlit as st
import pandas as pd
import tempfile
import os
from datetime import datetime
import logging

# Import backend modules
import backend_main_processing
import frontend_data_loader
import frontend_bracket_utils
from backend_filter_apply import REVERSE_RACE_MAP

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Constants
DATA_FOLDER = "data"
FORM_CONTROL_PATH = "form_control_UI_data.csv"

# Use the REVERSE_RACE_MAP from backend for consistency
RACE_DISPLAY_TO_CODE = REVERSE_RACE_MAP

# AgeGroup Mapping
AGEGROUP_DISPLAY_TO_CODE = {
    "All": "All",
    "18-Bracket": "agegroup13",
    "6-Bracket":  "agegroup14",
    "2-Bracket":  "agegroup15"
}

def validate_data_folder(data_folder: str, selected_years: list[str]) -> bool:
    """Validate that required data files exist."""
    if not os.path.exists(data_folder):
        st.error(f"Data folder '{data_folder}' not found!")
        logger.error(f"Data folder '{data_folder}' not found")
        return False
        
    missing_files = []
    for year in selected_years:
        filename = f"{year} population.csv"
        if not os.path.exists(os.path.join(data_folder, filename)):
            missing_files.append(filename)
    
    if missing_files:
        st.error(f"Missing data files: {', '.join(missing_files)}")
        logger.error(f"Missing data files: {', '.join(missing_files)}")
        return False
    return True

def check_data_consistency(df: pd.DataFrame) -> tuple[bool, str]:
    """Check if the data meets our requirements."""
    if df is None:
        return False, "No data returned from processing"
        
    if df.empty:
        return False, "No data matches the selected criteria"
        
    required_columns = ["County", "Race", "Sex", "Ethnicity", "Count", "Age", "Year"]
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        return False, f"Missing required columns: {', '.join(missing_columns)}"
        
    try:
        # Verify numeric columns
        pd.to_numeric(df["Count"])
        pd.to_numeric(df["Age"])
    except Exception as e:
        return False, f"Invalid numeric data: {str(e)}"
        
    return True, ""

@st.cache_data
def load_form_control_data():
    """Cache the form control data loading."""
    try:
        return frontend_data_loader.load_form_control_data(FORM_CONTROL_PATH)
    except Exception as e:
        st.error(f"Error loading form control data: {str(e)}")
        logger.error(f"Error loading form control data: {str(e)}")
        return None

def process_results(df: pd.DataFrame, year_str: str, agegroup_for_backend: str, 
                   custom_ranges: list, selected_agegroup: str, 
                   agegroup_map_implicit: dict) -> pd.DataFrame:
    """Process the results dataframe according to the selected filters."""
    if df is None or df.empty:
        return None

    try:
        total_pop = df["Count"].sum()
        
        # If "All" => single row "IL Population" if no custom ranges
        if agegroup_for_backend is None and not custom_ranges:
            return pd.DataFrame({
                "AgeGroup": ["IL Population"],
                "Count": [total_pop],
                "Percent": [100.0 if total_pop > 0 else 0.0],
                "Year": [year_str]
            })
            
        # Process custom ranges
        if custom_ranges:
            rows = []
            total_sum = 0
            for (mn, mx) in custom_ranges:
                code_list = range(mn, mx + 1)
                bracket_label = f"{mn}-{mx}"
                mask = df["Age"].isin(code_list)
                sub_sum = df.loc[mask, "Count"].sum()
                rows.append((bracket_label, sub_sum))
                total_sum += sub_sum

            out_rows = [
                (bexpr, cval, (cval / total_sum * 100.0) if total_sum > 0 else 0.0)
                for bexpr, cval in rows
            ]
            
            result_df = pd.DataFrame(out_rows, columns=["AgeGroup", "Count", "Percent"])
            result_df["Year"] = year_str
            result_df["Percent"] = result_df["Percent"].round(1)
            return result_df
            
        # Process implicit brackets
        brackets_implicit = agegroup_map_implicit.get(agegroup_for_backend, [])
        if not brackets_implicit:
            return pd.DataFrame({
                "AgeGroup": [f"No bracket for {selected_agegroup}"],
                "Count": [total_pop],
                "Percent": [100.0 if total_pop > 0 else 0.0],
                "Year": [year_str]
            })
            
        if "Age" in df.columns:
            rows = []
            total_sum = 0
            for bracket_expr in brackets_implicit:
                bracket_expr = bracket_expr.strip()
                mask = frontend_bracket_utils.parse_implicit_bracket(df, bracket_expr)
                sub_sum = df.loc[mask, "Count"].sum()
                rows.append((bracket_expr, sub_sum))
                total_sum += sub_sum
                
            out_rows = [
                (bexpr, cval, (cval / total_sum * 100.0) if total_sum > 0 else 0.0)
                for bexpr, cval in rows
            ]
            
            result_df = pd.DataFrame(out_rows, columns=["AgeGroup", "Count", "Percent"])
            result_df["Year"] = year_str
            result_df["Percent"] = result_df["Percent"].round(1)
            return result_df
            
    except Exception as e:
        logger.error(f"Error processing results: {str(e)}")
        st.error(f"Error processing results: {str(e)}")
        return None

def main():
    # Initialize session state
    if 'filtered_data_for_download' not in st.session_state:
        st.session_state.filtered_data_for_download = pd.DataFrame()
    if 'results_for_display' not in st.session_state:
        st.session_state.results_for_display = []

    # Page Config
    st.set_page_config(
        page_title="Illinois Census Data Form",
        page_icon="📊",
        layout="wide"
    )
    
    # Title
    st.title("Illinois Census Data Form")
    
    # Load form control data with caching
    form_data = load_form_control_data()
    if form_data is None:
        st.error("Failed to load form control data. Please check the logs.")
        return
        
    (years_list,
     agegroups_list_raw,
     races_list_raw,
     counties_map,
     agegroup_map_explicit,
     agegroup_map_implicit) = form_data
    
    # Create columns for layout
    col1, col2, col3 = st.columns(3)
    
    # Left Column (Years & Counties)
    with col1:
        st.subheader("Selection Controls")
        
        selected_years = st.multiselect(
            "Year Selection:",
            options=years_list,
            default=[years_list[0]] if years_list else None
        )
        
        county_options = ["All"] + sorted(counties_map.keys())
        selected_counties = st.multiselect(
            "Select Counties:",
            options=county_options
        )
    
    # Middle Column (Age Group, Race, Ethnicity, Sex, Region)
    with col2:
        st.subheader("Demographic Filters")
        
        agegroup_display_list = list(AGEGROUP_DISPLAY_TO_CODE.keys())
        selected_agegroup = st.selectbox(
            "Age Group:",
            options=agegroup_display_list,
            index=0
        )
        
        if selected_agegroup != "All":
            agegroup_code = AGEGROUP_DISPLAY_TO_CODE.get(selected_agegroup, "All")
            brackets_implicit = agegroup_map_implicit.get(agegroup_code, [])
            if brackets_implicit:
                st.write("Selected Age Brackets (Implicit):")
                for expr in brackets_implicit:
                    st.write(f"- {expr}")
        
        race_display_list = ["All"] + [k for k in RACE_DISPLAY_TO_CODE.keys()]
        selected_race = st.selectbox(
            "Race:",
            options=race_display_list,
            index=0
        )
        
        selected_ethnicity = st.radio(
            "Ethnicity:",
            options=["All", "Hispanic", "Not Hispanic"],
            horizontal=True
        )
        
        selected_sex = st.radio(
            "Sex:",
            options=["All", "Male", "Female"],
            horizontal=True
        )
        
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
            
        if not validate_data_folder(DATA_FOLDER, selected_years):
            return
        
        selected_race_code = "All" if selected_race == "All" else RACE_DISPLAY_TO_CODE.get(selected_race, selected_race)
        selected_agegroup_code = AGEGROUP_DISPLAY_TO_CODE.get(selected_agegroup, None)
        agegroup_for_backend = None if selected_agegroup_code == "All" else selected_agegroup_code
        
        combined_frames = []
        st.session_state.results_for_display = []
        
        with st.spinner("Generating report..."):
            try:
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
                    
                    # Validate data consistency
                    is_valid, error_msg = check_data_consistency(df)
                    if not is_valid:
                        st.error(f"Data validation failed for {year_str}: {error_msg}")
                        continue
                    
                    # Process results
                    processed_df = process_results(
                        df, year_str, agegroup_for_backend, custom_ranges,
                        selected_agegroup, agegroup_map_implicit
                    )
                    
                    if processed_df is not None and not processed_df.empty:
                        st.write(f"Results for {year_str}:")
                        st.dataframe(processed_df)
                        combined_frames.append(processed_df)
                        
            except Exception as e:
                st.error(f"Error processing data: {str(e)}")
                logger.error(f"Error processing data: {str(e)}")
                return
        
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
                try:
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
                except Exception as e:
                    st.error(f"Error creating Excel file: {str(e)}")
                    logger.error(f"Error creating Excel file: {str(e)}")
                finally:
                    if 'excel_buffer' in locals():
                        try:
                            os.unlink(excel_buffer.name)
                        except:
                            pass
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
