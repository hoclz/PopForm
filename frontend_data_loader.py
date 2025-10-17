import streamlit as st
import pandas as pd
import numpy as np
import geopandas as gpd
import matplotlib.pyplot as plt
import ttkbootstrap as tb
from frontend_data_loader import load_form_control_data
import os

# Page configuration
st.set_page_config(
    page_title="Population Data Explorer",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
        font-weight: bold;
    }
    .section-header {
        font-size: 1.5rem;
        color: #2e86ab;
        border-bottom: 2px solid #2e86ab;
        padding-bottom: 0.5rem;
        margin-top: 2rem;
        margin-bottom: 1rem;
    }
    .metric-card {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #2e86ab;
        margin-bottom: 1rem;
    }
    .stButton button {
        width: 100%;
        border-radius: 0.5rem;
    }
    .sidebar .sidebar-content {
        background-color: #f8f9fa;
    }
</style>
""", unsafe_allow_html=True)

def main():
    # Header Section
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown('<div class="main-header">🏛️ California Population Data Explorer</div>', unsafe_allow_html=True)
        st.markdown("### Analyze demographic trends across counties, age groups, and racial categories")

    # Initialize session state for data
    if 'data_loaded' not in st.session_state:
        st.session_state.data_loaded = False
        st.session_state.form_data = None

    # Sidebar - Data Management
    with st.sidebar:
        st.markdown("## 📁 Data Management")
        
        uploaded_file = st.file_uploader("Upload Form Control Data", type=['csv'], 
                                        help="Upload form_control_UI_data.csv file")
        
        if uploaded_file is not None:
            try:
                # Save uploaded file temporarily
                with open("temp_form_data.csv", "wb") as f:
                    f.write(uploaded_file.getbuffer())
                
                # Load data
                (years_list, agegroups_list, races_list, 
                 counties_map, agegroup_map_explicit, agegroup_map_implicit) = load_form_control_data("temp_form_data.csv")
                
                st.session_state.form_data = {
                    'years': years_list,
                    'agegroups': agegroups_list,
                    'races': races_list,
                    'counties': counties_map,
                    'explicit_brackets': agegroup_map_explicit,
                    'implicit_brackets': agegroup_map_implicit
                }
                st.session_state.data_loaded = True
                
                # Clean up
                os.remove("temp_form_data.csv")
                
                st.success("✅ Data loaded successfully!")
                
            except Exception as e:
                st.error(f"Error loading data: {str(e)}")
        else:
            st.info("👆 Please upload a CSV file to begin analysis")

    # Main content area
    if st.session_state.data_loaded and st.session_state.form_data:
        data = st.session_state.form_data
        
        # Quick Stats Overview
        st.markdown("## 📈 Data Overview")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.markdown(f"""
            <div class="metric-card">
                <h3>🗓️ Years</h3>
                <h2>{len(data['years'])}</h2>
                <p>Available periods</p>
            </div>
            """, unsafe_allow_html=True)
            
        with col2:
            st.markdown(f"""
            <div class="metric-card">
                <h3>🏛️ Counties</h3>
                <h2>{len(data['counties'])}</h2>
                <p>California counties</p>
            </div>
            """, unsafe_allow_html=True)
            
        with col3:
            st.markdown(f"""
            <div class="metric-card">
                <h3>👥 Race Groups</h3>
                <h2>{len(data['races'])}</h2>
                <p>Demographic categories</p>
            </div>
            """, unsafe_allow_html=True)
            
        with col4:
            st.markdown(f"""
            <div class="metric-card">
                <h3>📊 Age Groups</h3>
                <h2>{len(data['agegroups'])}</h2>
                <p>Age brackets</p>
            </div>
            """, unsafe_allow_html=True)

        # Analysis Controls Section
        st.markdown('<div class="section-header">🔍 Analysis Configuration</div>', unsafe_allow_html=True)
        
        tab1, tab2, tab3 = st.tabs(["📍 Geographic Selection", "📅 Temporal Analysis", "📋 Demographic Filters"])
        
        with tab1:
            st.subheader("County Selection")
            selected_counties = st.multiselect(
                "Choose counties to analyze:",
                options=list(data['counties'].keys()),
                default=list(data['counties'].keys())[:3] if data['counties'] else [],
                help="Select one or more counties for analysis"
            )
            
            # County codes display
            if selected_counties:
                st.info("Selected County Codes:")
                county_codes = [data['counties'][county] for county in selected_counties]
                st.write(", ".join(map(str, county_codes)))
        
        with tab2:
            col1, col2 = st.columns(2)
            with col1:
                start_year = st.selectbox(
                    "Start Year:",
                    options=data['years'],
                    index=0
                )
            with col2:
                end_year = st.selectbox(
                    "End Year:",
                    options=data['years'],
                    index=len(data['years'])-1
                )
            
            # Year range validation
            if start_year > end_year:
                st.warning("⚠️ Start year should be before end year")
        
        with tab3:
            col1, col2 = st.columns(2)
            with col1:
                selected_races = st.multiselect(
                    "Race/Ethnicity Groups:",
                    options=data['races'],
                    default=data['races'][:3] if data['races'] else []
                )
            with col2:
                selected_age_groups = st.multiselect(
                    "Age Groups:",
                    options=data['agegroups'],
                    default=data['agegroups'][:3] if data['agegroups'] else []
                )
            
            # Age bracket type selection
            bracket_type = st.radio(
                "Age Bracket Display:",
                ["Explicit Brackets", "Implicit Brackets"],
                horizontal=True
            )

        # Visualization Section
        st.markdown('<div class="section-header">📊 Data Visualization</div>', unsafe_allow_html=True)
        
        viz_tab1, viz_tab2, viz_tab3 = st.tabs(["📈 Summary Charts", "🗺️ Geographic View", "📋 Detailed Data"])
        
        with viz_tab1:
            st.subheader("Data Distribution")
            
            if selected_counties and selected_races and selected_age_groups:
                col1, col2 = st.columns(2)
                
                with col1:
                    # Sample chart - Age group distribution
                    st.markdown("**Age Group Coverage**")
                    age_data = {age: len(data['explicit_brackets'].get(age, [])) for age in selected_age_groups}
                    fig, ax = plt.subplots(figsize=(10, 6))
                    ax.bar(age_data.keys(), age_data.values(), color='skyblue', alpha=0.7)
                    ax.set_title('Age Groups and Their Brackets')
                    ax.set_ylabel('Number of Brackets')
                    plt.xticks(rotation=45)
                    st.pyplot(fig)
                
                with col2:
                    # Sample chart - Race distribution
                    st.markdown("**Available Race Groups**")
                    race_data = {race: 1 for race in selected_races}  # Placeholder
                    fig, ax = plt.subplots(figsize=(10, 6))
                    ax.pie(race_data.values(), labels=race_data.keys(), autopct='%1.1f%%', startangle=90)
                    ax.set_title('Selected Race Distribution')
                    st.pyplot(fig)
            else:
                st.info("Please select counties, races, and age groups to generate visualizations")
        
        with viz_tab2:
            st.subheader("Geographic Analysis")
            st.info("🗺️ Geographic visualization would be displayed here with the selected counties highlighted on a California map.")
            # Placeholder for map visualization
            st.write("Map integration would show selected counties:", selected_counties)
        
        with viz_tab3:
            st.subheader("Raw Data Preview")
            
            # Display available data structures
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**Available Counties**")
                counties_df = pd.DataFrame(list(data['counties'].items()), columns=['County', 'Code'])
                st.dataframe(counties_df, use_container_width=True)
            
            with col2:
                st.markdown("**Age Group Brackets**")
                bracket_type_data = data['explicit_brackets'] if bracket_type == "Explicit Brackets" else data['implicit_brackets']
                brackets_list = []
                for age_group, brackets in bracket_type_data.items():
                    if age_group in selected_age_groups:
                        brackets_list.append({
                            'Age Group': age_group,
                            'Brackets': ', '.join(brackets[:3]) + ('...' if len(brackets) > 3 else '')
                        })
                brackets_df = pd.DataFrame(brackets_list)
                st.dataframe(brackets_df, use_container_width=True)

        # Export Section
        st.markdown('<div class="section-header">📤 Export Results</div>', unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("📊 Generate Report", use_container_width=True):
                st.success("Report generation started! This would create a comprehensive PDF report.")
        
        with col2:
            if st.button("📁 Export to Excel", use_container_width=True):
                st.success("Excel export initiated! This would download the filtered data as Excel.")
        
        with col3:
            if st.button("🖼️ Save Visualizations", use_container_width=True):
                st.success("Visualizations saved! This would download charts as PNG files.")

    else:
        # Welcome screen when no data is loaded
        st.markdown("""
        ## 🚀 Welcome to the Population Data Explorer
        
        This application helps you analyze and visualize population demographic data across California counties.
        
        ### Getting Started:
        1. **Upload your data** using the sidebar on the left
        2. **Configure your analysis** using the interactive filters
        3. **Explore visualizations** across different tabs
        4. **Export results** for further analysis
        
        ### Features:
        - 📍 **Multi-county analysis** - Compare across multiple geographic regions
        - 📅 **Temporal trends** - Analyze changes over time
        - 👥 **Demographic breakdowns** - Explore by race and age groups
        - 📊 **Interactive visualizations** - Charts, maps, and data tables
        - 📤 **Export capabilities** - Reports, Excel files, and images
        
        ### Sample Data Structure:
        The application expects a CSV file with the following columns:
        - CountyName, CountyCode, YearValue, Race, AgeGroup, ExplicitBrackets, ImplicitBrackets
        
        **👈 Start by uploading your data in the sidebar!**
        """)
        
        # Sample data preview
        st.markdown("### 📋 Expected Data Format")
        sample_data = pd.DataFrame({
            'CountyName': ['Alameda', 'Alameda', 'Los Angeles'],
            'CountyCode': [1, 1, 37],
            'YearValue': ['2020', '2020', '2020'],
            'Race': ['White', 'Hispanic', 'Asian'],
            'AgeGroup': ['0-17', '18-64', '65+'],
            'ExplicitBrackets': ['0-4,5-9,10-14,15-17', '18-24,25-34,35-44,45-54,55-64', '65-74,75-84,85+'],
            'ImplicitBrackets': ['Child', 'Adult', 'Senior']
        })
        st.dataframe(sample_data, use_container_width=True)

if __name__ == "__main__":
    main()
