import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import io
import base64

# Page configuration
st.set_page_config(
    page_title="California Population Explorer",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for modern styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.8rem;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        margin-bottom: 2rem;
        font-weight: 800;
    }
    .section-header {
        font-size: 1.6rem;
        color: #2c3e50;
        border-left: 5px solid #3498db;
        padding-left: 1rem;
        margin: 2rem 0 1rem 0;
        font-weight: 600;
    }
    .metric-card {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
        padding: 1.5rem;
        border-radius: 15px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        margin-bottom: 1rem;
        text-align: center;
    }
    .metric-value {
        font-size: 2rem;
        font-weight: bold;
        color: #2c3e50;
        margin: 0.5rem 0;
    }
    .metric-label {
        font-size: 1rem;
        color: #7f8c8d;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 2rem;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: #f8f9fa;
        border-radius: 10px 10px 0px 0px;
        gap: 1rem;
        padding: 10px 20px;
        font-weight: 600;
    }
    .feature-card {
        background: white;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        margin: 1rem 0;
        border-left: 4px solid #3498db;
    }
</style>
""", unsafe_allow_html=True)

def load_sample_data():
    """Load sample data for demonstration"""
    # Sample counties data for California
    counties = {
        'Los Angeles': 37, 'San Diego': 73, 'Orange': 59, 'Riverside': 65,
        'San Bernardino': 71, 'Santa Clara': 85, 'Alameda': 1, 'Sacramento': 67,
        'Contra Costa': 13, 'Fresno': 19, 'Ventura': 111, 'San Francisco': 75,
        'Kern': 29, 'San Mateo': 81, 'San Joaquin': 77, 'Sonoma': 97,
        'Stanislaus': 99, 'Tulare': 107, 'Santa Barbara': 83, 'Solano': 95
    }
    
    years = [str(year) for year in range(2000, 2024)]
    
    races = ['White', 'Hispanic', 'Asian', 'Black', 'Native American', 'Pacific Islander', 'Multiracial']
    
    age_groups = {
        'Under 18': ['0-4', '5-9', '10-14', '15-17'],
        '18-64': ['18-24', '25-34', '35-44', '45-54', '55-64'],
        '65+': ['65-74', '75-84', '85+'],
        'All Ages': ['All']
    }
    
    return counties, years, races, age_groups

def create_sample_chart(chart_type, data):
    """Create sample charts based on type"""
    if chart_type == "population_trend":
        years = list(range(2000, 2024))
        population = [10000000 + i * 50000 + np.random.randint(-100000, 100000) for i in range(len(years))]
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=years, y=population, mode='lines+markers', 
                               line=dict(color='#3498db', width=3),
                               marker=dict(size=8)))
        fig.update_layout(
            title="Population Trend 2000-2023",
            xaxis_title="Year",
            yaxis_title="Population",
            template="plotly_white",
            height=400
        )
        return fig
    
    elif chart_type == "age_distribution":
        age_groups = ['0-17', '18-24', '25-34', '35-44', '45-54', '55-64', '65+']
        percentages = [18, 12, 15, 14, 13, 11, 17]
        
        fig = px.pie(values=percentages, names=age_groups, 
                    title="Age Distribution",
                    color_discrete_sequence=px.colors.sequential.Blues_r)
        fig.update_traces(textposition='inside', textinfo='percent+label')
        fig.update_layout(height=400, showlegend=False)
        return fig
    
    elif chart_type == "race_composition":
        races = ['White', 'Hispanic', 'Asian', 'Black', 'Other']
        percentages = [36, 39, 15, 6, 4]
        
        fig = px.bar(x=races, y=percentages, 
                    title="Racial Composition",
                    color=races,
                    color_discrete_sequence=px.colors.qualitative.Set3)
        fig.update_layout(
            xaxis_title="Race/Ethnicity",
            yaxis_title="Percentage (%)",
            height=400,
            showlegend=False
        )
        return fig

def main():
    # Header Section
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown('<div class="main-header">🏛️ California Population Data Explorer</div>', unsafe_allow_html=True)
        st.markdown("### Analyze demographic trends across counties, age groups, and racial categories")
    
    # Load sample data
    counties, years, races, age_groups = load_sample_data()
    
    # Quick Stats Overview
    st.markdown("## 📈 Data Overview")
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.markdown("""
        <div class="metric-card">
            <div class="metric-value">24</div>
            <div class="metric-label">Years</div>
        </div>
        """, unsafe_allow_html=True)
        
    with col2:
        st.markdown("""
        <div class="metric-card">
            <div class="metric-value">58</div>
            <div class="metric-label">Counties</div>
        </div>
        """, unsafe_allow_html=True)
        
    with col3:
        st.markdown("""
        <div class="metric-card">
            <div class="metric-value">7</div>
            <div class="metric-label">Race Groups</div>
        </div>
        """, unsafe_allow_html=True)
        
    with col4:
        st.markdown("""
        <div class="metric-card">
            <div class="metric-value">4</div>
            <div class="metric-label">Age Categories</div>
        </div>
        """, unsafe_allow_html=True)
        
    with col5:
        st.markdown("""
        <div class="metric-card">
            <div class="metric-value">39.5M</div>
            <div class="metric-label">Total Population</div>
        </div>
        """, unsafe_allow_html=True)
    
    # Main Analysis Section
    st.markdown('<div class="section-header">🔍 Analysis Configuration</div>', unsafe_allow_html=True)
    
    # Create tabs for different analysis types
    tab1, tab2, tab3, tab4 = st.tabs(["📍 Geographic Selection", "📅 Time Period", "👥 Demographics", "📊 Visualization"])
    
    with tab1:
        col1, col2 = st.columns([2, 1])
        
        with col1:
            selected_counties = st.multiselect(
                "Select Counties:",
                options=list(counties.keys()),
                default=["Los Angeles", "San Diego", "Orange"],
                help="Choose counties to analyze"
            )
            
            # Region selection
            regions = st.multiselect(
                "Select Regions:",
                ["Southern California", "Northern California", "Central Valley", "Bay Area", "Central Coast"],
                default=["Southern California"]
            )
            
        with col2:
            st.markdown("**Selected County Codes:**")
            if selected_counties:
                county_codes = [counties[county] for county in selected_counties]
                for county, code in zip(selected_counties, county_codes):
                    st.write(f"• {county}: {code}")
            else:
                st.info("No counties selected")
    
    with tab2:
        col1, col2, col3 = st.columns([1, 1, 2])
        
        with col1:
            start_year = st.selectbox("Start Year:", years, index=0)
        with col2:
            end_year = st.selectbox("End Year:", years, index=len(years)-1)
        with col3:
            analysis_type = st.radio(
                "Analysis Type:",
                ["Single Year", "Year Range", "Decadal Comparison"],
                horizontal=True
            )
    
    with tab3:
        col1, col2 = st.columns(2)
        
        with col1:
            selected_races = st.multiselect(
                "Race/Ethnicity Groups:",
                races,
                default=races[:3]
            )
            
            sex_filter = st.radio(
                "Sex:",
                ["All", "Male", "Female"],
                horizontal=True
            )
            
        with col2:
            selected_age_categories = st.multiselect(
                "Age Categories:",
                list(age_groups.keys()),
                default=list(age_groups.keys())[:2]
            )
            
            ethnicity_filter = st.radio(
                "Ethnicity:",
                ["All", "Hispanic", "Non-Hispanic"],
                horizontal=True
            )
    
    with tab4:
        col1, col2 = st.columns(2)
        
        with col1:
            chart_type = st.selectbox(
                "Primary Chart Type:",
                ["Population Trend", "Age Distribution", "Race Composition", "Geographic Map", "Comparison Chart"]
            )
            
            color_scheme = st.selectbox(
                "Color Scheme:",
                ["Blue Scale", "Multi Color", "Pastel", "Dark", "Light"]
            )
            
        with col2:
            secondary_chart = st.selectbox(
                "Secondary Chart:",
                ["None", "Population Pyramid", "Trend Comparison", "Percentage Change"]
            )
            
            export_format = st.multiselect(
                "Export Formats:",
                ["PNG", "PDF", "CSV", "Excel"]
            )
    
    # Visualization Section
    st.markdown('<div class="section-header">📊 Interactive Visualizations</div>', unsafe_allow_html=True)
    
    if selected_counties:
        # Create visualization tabs
        viz_tab1, viz_tab2, viz_tab3, viz_tab4 = st.tabs(["📈 Trends", "👥 Demographics", "🗺️ Geography", "📋 Data Table"])
        
        with viz_tab1:
            col1, col2 = st.columns(2)
            
            with col1:
                st.plotly_chart(create_sample_chart("population_trend", None), use_container_width=True)
                
            with col2:
                st.plotly_chart(create_sample_chart("race_composition", None), use_container_width=True)
            
            # Additional trend analysis
            st.subheader("Comparative Analysis")
            col1, col2 = st.columns(2)
            
            with col1:
                # Sample comparative data
                comparison_data = pd.DataFrame({
                    'Year': [2020, 2021, 2022, 2023],
                    'Los Angeles': [10056835, 10071235, 10084567, 10102345],
                    'San Diego': [3323974, 3339876, 3354678, 3378945],
                    'Orange': [3175698, 3187654, 3201456, 3216789]
                })
                
                st.dataframe(comparison_data, use_container_width=True)
            
            with col2:
                st.plotly_chart(create_sample_chart("age_distribution", None), use_container_width=True)
        
        with viz_tab2:
            st.subheader("Demographic Breakdown")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Total Population", "39,538,223", "1.2%")
                st.metric("Median Age", "36.5", "0.3")
                
            with col2:
                st.metric("Population Density", "251/sq mi", "2.1%")
                st.metric("Growth Rate", "0.85%", "-0.1%")
                
            with col3:
                st.metric("Household Size", "2.9", "0.0")
                st.metric("Urban Population", "94.2%", "0.4%")
            
            # Demographic details
            st.subheader("Detailed Demographics")
            demo_data = pd.DataFrame({
                'Category': ['White', 'Hispanic', 'Asian', 'Black', 'Native American'],
                'Population': [13456789, 15543210, 5923456, 2134567, 156789],
                'Percentage': [34.0, 39.3, 15.0, 5.4, 0.4],
                'Growth Rate': [0.2, 1.8, 2.1, 0.5, 0.3]
            })
            
            st.dataframe(demo_data, use_container_width=True)
        
        with viz_tab3:
            st.subheader("Geographic Distribution")
            
            # Sample map data
            map_data = pd.DataFrame({
                'County': selected_counties,
                'Latitude': [34.0522, 32.7157, 33.7175, 38.5816, 37.7749],
                'Longitude': [-118.2437, -117.1611, -117.8311, -121.4944, -122.4194],
                'Population': [10056835, 3323974, 3175698, 1570583, 874784],
                'Growth_Rate': [0.8, 1.2, 0.9, 1.5, 1.1]
            })[:len(selected_counties)]
            
            # Create a simple map visualization
            fig = px.scatter_mapbox(map_data, 
                                  lat="Latitude", 
                                  lon="Longitude", 
                                  size="Population",
                                  color="Growth_Rate",
                                  hover_name="County",
                                  hover_data={"Population": True, "Growth_Rate": True},
                                  color_continuous_scale=px.colors.sequential.Blues,
                                  size_max=50,
                                  zoom=5)
            
            fig.update_layout(mapbox_style="open-street-map")
            fig.update_layout(margin={"r":0,"t":0,"l":0,"b":0}, height=500)
            
            st.plotly_chart(fig, use_container_width=True)
        
        with viz_tab4:
            st.subheader("Raw Data Export")
            
            # Generate sample detailed data
            detailed_data = []
            for county in selected_counties:
                for year in [2020, 2021, 2022, 2023]:
                    for race in selected_races[:2]:
                        detailed_data.append({
                            'County': county,
                            'Year': year,
                            'Race': race,
                            'Population': np.random.randint(100000, 5000000),
                            'Growth_Rate': round(np.random.uniform(0.1, 2.0), 2)
                        })
            
            detailed_df = pd.DataFrame(detailed_data)
            st.dataframe(detailed_df, use_container_width=True)
            
            # Export options
            st.download_button(
                "📥 Download as CSV",
                detailed_df.to_csv(index=False),
                "population_data.csv",
                "text/csv"
            )
    
    else:
        # Welcome/Instruction section when no counties selected
        st.markdown("""
        <div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 2rem; border-radius: 15px; color: white;'>
            <h2 style='color: white; margin-bottom: 1rem;'>🚀 Ready to Explore California Population Data?</h2>
            <p style='font-size: 1.2rem; margin-bottom: 1.5rem;'>
                Select counties in the <strong>Geographic Selection</strong> tab to unlock powerful demographic insights and visualizations.
            </p>
            <div style='display: grid; grid-template-columns: repeat(2, 1fr); gap: 1rem;'>
                <div class='feature-card' style='background: rgba(255,255,255,0.9); color: #2c3e50;'>
                    <h4>📈 Trend Analysis</h4>
                    <p>Track population changes over 20+ years</p>
                </div>
                <div class='feature-card' style='background: rgba(255,255,255,0.9); color: #2c3e50;'>
                    <h4>👥 Demographic Insights</h4>
                    <p>Break down by age, race, and ethnicity</p>
                </div>
                <div class='feature-card' style='background: rgba(255,255,255,0.9); color: #2c3e50;'>
                    <h4>🗺️ Geographic Mapping</h4>
                    <p>Visualize data across California counties</p>
                </div>
                <div class='feature-card' style='background: rgba(255,255,255,0.9); color: #2c3e50;'>
                    <h4>📊 Interactive Charts</h4>
                    <p>Create custom visualizations</p>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    # Footer
    st.markdown("---")
    st.markdown(
        "<div style='text-align: center; color: #7f8c8d;'>"
        "California Population Data Explorer • Built with Streamlit • Data Source: U.S. Census Bureau"
        "</div>",
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()
