# app.py
import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
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
    .feature-card {
        background: white;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        margin: 1rem 0;
        border-left: 4px solid #3498db;
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
</style>
""", unsafe_allow_html=True)

def create_population_trend_chart():
    """Create population trend chart using matplotlib"""
    years = list(range(2000, 2024))
    population = [10000000 + i * 50000 + np.random.randint(-100000, 100000) for i in range(len(years))]
    
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(years, population, marker='o', linewidth=2, markersize=6, color='#3498db')
    ax.set_title('California Population Trend 2000-2023', fontsize=16, fontweight='bold', pad=20)
    ax.set_xlabel('Year', fontsize=12)
    ax.set_ylabel('Population', fontsize=12)
    ax.grid(True, alpha=0.3)
    ax.ticklabel_format(style='plain', axis='y')
    plt.tight_layout()
    return fig

def create_age_distribution_chart():
    """Create age distribution chart"""
    age_groups = ['0-17', '18-24', '25-34', '35-44', '45-54', '55-64', '65+']
    percentages = [18, 12, 15, 14, 13, 11, 17]
    colors = plt.cm.Blues(np.linspace(0.4, 0.8, len(age_groups)))
    
    fig, ax = plt.subplots(figsize=(10, 6))
    bars = ax.bar(age_groups, percentages, color=colors, alpha=0.8)
    ax.set_title('Age Distribution in California', fontsize=16, fontweight='bold', pad=20)
    ax.set_xlabel('Age Groups', fontsize=12)
    ax.set_ylabel('Percentage (%)', fontsize=12)
    
    # Add value labels on bars
    for bar, percentage in zip(bars, percentages):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height + 0.5,
                f'{percentage}%', ha='center', va='bottom', fontweight='bold')
    
    plt.xticks(rotation=45)
    plt.tight_layout()
    return fig

def create_race_composition_chart():
    """Create race composition chart"""
    races = ['White', 'Hispanic', 'Asian', 'Black', 'Other']
    percentages = [36, 39, 15, 6, 4]
    colors = ['#ff9999', '#66b3ff', '#99ff99', '#ffcc99', '#c2c2f0']
    
    fig, ax = plt.subplots(figsize=(8, 8))
    wedges, texts, autotexts = ax.pie(percentages, labels=races, colors=colors, autopct='%1.1f%%', startangle=90)
    
    # Style the text
    for autotext in autotexts:
        autotext.set_color('white')
        autotext.set_fontweight('bold')
    
    ax.set_title('Racial Composition of California', fontsize=16, fontweight='bold', pad=20)
    plt.tight_layout()
    return fig

def create_county_comparison_chart(selected_counties):
    """Create county comparison chart"""
    counties = selected_counties[:5]  # Limit to 5 counties for clarity
    populations = [np.random.randint(1000000, 5000000) for _ in counties]
    
    fig, ax = plt.subplots(figsize=(12, 6))
    bars = ax.bar(counties, populations, color=plt.cm.viridis(np.linspace(0, 1, len(counties))), alpha=0.8)
    ax.set_title('Population Comparison by County', fontsize=16, fontweight='bold', pad=20)
    ax.set_xlabel('County', fontsize=12)
    ax.set_ylabel('Population', fontsize=12)
    
    # Add value labels on bars
    for bar, population in zip(bars, populations):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height + 10000,
                f'{population:,}', ha='center', va='bottom', fontweight='bold')
    
    plt.xticks(rotation=45)
    plt.tight_layout()
    return fig

def main():
    # Header Section
    st.markdown('<div class="main-header">🏛️ California Population Data Explorer</div>', unsafe_allow_html=True)
    st.markdown("### Analyze demographic trends across counties, age groups, and racial categories")
    
    # Load data
    try:
        from frontend_data_loader import load_form_control_data
        years_list, agegroups_list, races_list, counties_map, agegroup_map_explicit, agegroup_map_implicit = load_form_control_data("form_control_UI_data.csv")
    except:
        # Use sample data if loading fails
        from frontend_data_loader import get_sample_data
        years_list, agegroups_list, races_list, counties_map, agegroup_map_explicit, agegroup_map_implicit = get_sample_data()
    
    # Quick Stats Overview
    st.markdown("## 📈 Data Overview")
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{len(years_list)}</div>
            <div class="metric-label">Years</div>
        </div>
        """, unsafe_allow_html=True)
        
    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{len(counties_map)}</div>
            <div class="metric-label">Counties</div>
        </div>
        """, unsafe_allow_html=True)
        
    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{len(races_list)}</div>
            <div class="metric-label">Race Groups</div>
        </div>
        """, unsafe_allow_html=True)
        
    with col4:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{len(agegroups_list)}</div>
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
                options=list(counties_map.keys()),
                default=list(counties_map.keys())[:3] if counties_map else [],
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
                county_codes = [counties_map[county] for county in selected_counties]
                for county, code in zip(selected_counties, county_codes):
                    st.write(f"• {county}: {code}")
            else:
                st.info("No counties selected")
    
    with tab2:
        col1, col2, col3 = st.columns([1, 1, 2])
        
        with col1:
            start_year = st.selectbox("Start Year:", years_list, index=0)
        with col2:
            end_year = st.selectbox("End Year:", years_list, index=len(years_list)-1)
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
                races_list,
                default=races_list[:3] if races_list else []
            )
            
            sex_filter = st.radio(
                "Sex:",
                ["All", "Male", "Female"],
                horizontal=True
            )
            
        with col2:
            selected_age_categories = st.multiselect(
                "Age Categories:",
                agegroups_list,
                default=agegroups_list[:2] if agegroups_list else []
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
                ["Population Trend", "Age Distribution", "Race Composition", "County Comparison"]
            )
            
            color_scheme = st.selectbox(
                "Color Scheme:",
                ["Blue Scale", "Multi Color", "Pastel", "Dark", "Light"]
            )
            
        with col2:
            st.markdown("**Export Options:**")
            export_csv = st.checkbox("CSV Export")
            export_png = st.checkbox("PNG Export")
    
    # Visualization Section
    st.markdown('<div class="section-header">📊 Interactive Visualizations</div>', unsafe_allow_html=True)
    
    if selected_counties:
        # Create visualization tabs
        viz_tab1, viz_tab2, viz_tab3, viz_tab4 = st.tabs(["📈 Trends & Charts", "👥 Demographics", "🏛️ County Data", "📋 Export"])
        
        with viz_tab1:
            col1, col2 = st.columns(2)
            
            with col1:
                st.pyplot(create_population_trend_chart())
                if export_png:
                    buf = io.BytesIO()
                    create_population_trend_chart().savefig(buf, format='png', dpi=300, bbox_inches='tight')
                    buf.seek(0)
                    st.download_button(
                        "Download Trend Chart",
                        buf.getvalue(),
                        "population_trend.png",
                        "image/png"
                    )
                
            with col2:
                st.pyplot(create_race_composition_chart())
            
            col3, col4 = st.columns(2)
            
            with col3:
                st.pyplot(create_age_distribution_chart())
                
            with col4:
                st.pyplot(create_county_comparison_chart(selected_counties))
        
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
            st.subheader("County-Level Data")
            
            # Generate sample county data
            county_data = []
            for county in selected_counties:
                for year in [2020, 2021, 2022, 2023]:
                    county_data.append({
                        'County': county,
                        'Year': year,
                        'Population': np.random.randint(500000, 5000000),
                        'Growth_Rate': round(np.random.uniform(0.1, 2.0), 2),
                        'Density': np.random.randint(100, 2000)
                    })
            
            county_df = pd.DataFrame(county_data)
            st.dataframe(county_df, use_container_width=True)
            
            # County statistics
            st.subheader("County Statistics")
            stats_col1, stats_col2, stats_col3 = st.columns(3)
            
            with stats_col1:
                avg_population = county_df['Population'].mean()
                st.metric("Average County Population", f"{avg_population:,.0f}")
                
            with stats_col2:
                avg_growth = county_df['Growth_Rate'].mean()
                st.metric("Average Growth Rate", f"{avg_growth:.2f}%")
                
            with stats_col3:
                max_population = county_df['Population'].max()
                st.metric("Largest County Population", f"{max_population:,.0f}")
        
        with viz_tab4:
            st.subheader("Data Export")
            
            # Generate comprehensive export data
            export_data = []
            for county in selected_counties:
                for year in years_list[-5:]:  # Last 5 years
                    for race in selected_races[:3] if selected_races else ['All']:
                        for age_group in selected_age_categories[:2] if selected_age_categories else ['All']:
                            export_data.append({
                                'County': county,
                                'Year': year,
                                'Race': race,
                                'Age_Group': age_group,
                                'Population': np.random.randint(10000, 500000),
                                'County_Code': counties_map[county]
                            })
            
            export_df = pd.DataFrame(export_data)
            st.dataframe(export_df, use_container_width=True)
            
            # Export options
            col1, col2 = st.columns(2)
            
            with col1:
                if export_csv:
                    csv_data = export_df.to_csv(index=False)
                    st.download_button(
                        "📥 Download Full Dataset as CSV",
                        csv_data,
                        "california_population_data.csv",
                        "text/csv"
                    )
            
            with col2:
                st.info("💡 Select counties and configure filters above to generate customized data exports.")
    
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
                    <h4>🏛️ County Comparisons</h4>
                    <p>Compare data across multiple counties</p>
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
