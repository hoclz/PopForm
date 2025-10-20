
import streamlit as st

# Sidebar builder (all sections closed by default)

RACE_DISPLAY_TO_CODE = {
    "Two or More Races": "TOM",
    "American Indian and Alaska Native": "AIAN",
    "Black or African American": "Black",
    "White": "White",
    "Native Hawaiian and Other Pacific Islander": "NHOPI",
    "Asian": "Asian",
}
RACE_CODE_TO_DISPLAY = {v: k for k, v in RACE_DISPLAY_TO_CODE.items()}


def render_sidebar_controls(
    years_list,
    races_list_raw,
    counties_map,
    agegroup_map_implicit,
    agegroups_list_raw=None,
):
    """Render Query Builder + Grouping in the sidebar (all closed by default)."""
    sb = st.sidebar
    sb.markdown("## 🔍 Query Builder")

    # Geography & Time
    with sb.expander("📍 Geography & Time", expanded=False):
        selected_years = st.multiselect(
            "Select Year(s):",
            options=years_list,
            default=years_list[-1:] if years_list else [],
        )
        all_counties = ["All"] + sorted(counties_map.keys())
        selected_counties = st.multiselect(
            "Select Counties:", options=all_counties, default=["All"]
        )
        if "All" in selected_counties and len(selected_counties) > 1:
            st.info("Using 'All' counties (specific selections ignored).")
            selected_counties = ["All"]

    # Demographics
    with sb.expander("👥 Demographics", expanded=False):
        race_opts = ["All"]
        for rcode in sorted(races_list_raw):
            if rcode != "All":
                race_opts.append(RACE_CODE_TO_DISPLAY.get(rcode, rcode))
        selected_race_display = st.selectbox("Race Filter:", race_opts, index=0)
        selected_sex = st.radio("Sex:", ["All", "Male", "Female"], horizontal=True)
        selected_ethnicity = st.radio("Ethnicity:", ["All", "Hispanic", "Not Hispanic"], horizontal=True)
        region_options = ["None", "Collar Counties", "Urban Counties", "Rural Counties"]
        selected_region = st.selectbox("Region:", region_options, index=0)

    # Age Settings
    with sb.expander("📋 Age Settings", expanded=False):
        AGEGROUP_DISPLAY_TO_CODE = {
            "All": "All",
            "18-Bracket": "agegroup13",
            "6-Bracket": "agegroup14",
            "2-Bracket": "agegroup15",
        }
        selected_agegroup_display = st.selectbox(
            "Age Group:", list(AGEGROUP_DISPLAY_TO_CODE.keys()), index=0
        )
        if selected_agegroup_display != "All":
            code = AGEGROUP_DISPLAY_TO_CODE[selected_agegroup_display]
            br = agegroup_map_implicit.get(code, [])
            if br:
                st.caption("**Age Brackets:** " + ", ".join(map(str, br)))

        enable_custom_ranges = st.checkbox("Enable custom age ranges", value=False)
        st.caption("When enabled, these custom ranges override the Age Group selection.")
        custom_ranges = []
        if enable_custom_ranges:
            for i, (d_min, d_max) in enumerate([(1,5),(6,10),(11,15)], start=1):
                if st.checkbox(f"Range {i}", key=f"r{i}"):
                    mn = st.number_input(f"Min {i} (1–18)", 1, 18, d_min, key=f"mn{i}")
                    mx = st.number_input(f"Max {i} (1–18)", 1, 18, d_max, key=f"mx{i}")
                    if mn <= mx:
                        custom_ranges.append((int(mn), int(mx)))

    # Group Results By
    with sb.expander("📈 Group Results By", expanded=False):
        grouping_vars = st.multiselect(
            "Group by any combination (or choose 'All' for totals):",
            ["All", "Age", "Race", "Ethnicity", "Sex", "County"],
            default=["All"],
        )
        if "All" in grouping_vars and len(grouping_vars) > 1:
            st.info("Using 'All' (totals only). Other selections ignored.")
            grouping_vars = ["All"]

    # Output Options
    with sb.expander("⚙️ Output Options", expanded=False):
        include_breakdown = st.checkbox(
            "Include Individual County Breakdowns",
            value=True,
            help="Show a separate table for each selected county (in addition to combined results)."
        )
        if "County" in grouping_vars and include_breakdown:
            st.info("Grouping by County already provides county rows. Turning off extra breakdowns.")
            include_breakdown = False
        debug_mode = st.checkbox("Debug Mode", value=False)

    return {
        "debug_mode": debug_mode,
        "selected_years": selected_years,
        "selected_counties": selected_counties,
        "selected_race_display": selected_race_display,
        "selected_race_code": "All" if selected_race_display == "All"
                               else RACE_DISPLAY_TO_CODE.get(selected_race_display, selected_race_display),
        "selected_sex": selected_sex,
        "selected_ethnicity": selected_ethnicity,
        "selected_region": selected_region,
        "selected_agegroup_display": selected_agegroup_display,
        "agegroup_for_backend": {"All": None, "18-Bracket": "agegroup13",
                                 "6-Bracket": "agegroup14", "2-Bracket": "agegroup15"}[selected_agegroup_display],
        "enable_custom_ranges": enable_custom_ranges,
        "custom_ranges": custom_ranges,
        "grouping_vars": grouping_vars,
        "include_breakdown": include_breakdown,
    }


def display_census_links():
    """Right-side expander for Census links (default closed)."""
    docs = [
        (2024, "April 1, 2020 to July 1, 2024", "https://www2.census.gov/programs-surveys/popest/technical-documentation/file-layouts/2020-2024/CC-EST2024-ALLDATA.pdf"),
        (2023, "April 1, 2020 to July 1, 2023", "https://www2.census.gov/programs-surveys/popest/technical-documentation/file-layouts/2020-2023/CC-EST2023-ALLDATA.pdf"),
        (2022, "April 1, 2020 to July 1, 2022", "https://www2.census.gov/programs-surveys/popest/technical-documentation/file-layouts/2020-2022/cc-est2022-alldata.pdf"),
        (2021, "April 1, 2020 to July 1, 2021", "https://www2.census.gov/programs-surveys/popest/technical-documentation/file-layouts/2020-2021/cc-est2021-alldata.pdf"),
        (2020, "April 1, 2010 to July 1, 2020", "https://www2.census.gov/programs-surveys/popest/technical-documentation/file-layouts/2010-2020/cc-est2020-alldata.pdf"),
        (2019, "April 1, 2010 to July 1, 2019", "https://www2.census.gov/programs-surveys/popest/technical-documentation/file-layouts/2010-2019/cc-est2019-alldata.pdf"),
        (2018, "April 1, 2010 to July 1, 2018", "https://www2.census.gov/programs-surveys/popest/technical-documentation/file-layouts/2010-2018/cc-est2018-alldata.pdf"),
        (2017, "April 1, 2010 to July 1, 2017", "https://www2.census.gov/programs-surveys/popest/technical-documentation/file-layouts/2010-2017/cc-est2017-alldata.pdf"),
        (2016, "April 1, 2010 to July 1, 2016", "https://www2.census.gov/programs-surveys/popest/technical-documentation/file-layouts/2010-2016/cc-est2016-alldata.pdf"),
        (2015, "April 1, 2010 to July 1, 2015", "https://www2.census.gov/programs-surveys/popest/technical-documentation/file-layouts/2010-2015/cc-est2015-alldata.pdf"),
        (2014, "April 1, 2010 to July 1, 2014", "https://www2.census.gov/programs-surveys/popest/technical-documentation/file-layouts/2010-2014/cc-est2014-alldata.pdf"),
        (2013, "April 1, 2010 to July 1, 2013", "https://www2.census.gov/programs-surveys/popest/technical-documentation/file-layouts/2010-2013/cc-est2013-alldata.pdf"),
        (2012, "April 1, 2010 to July 1, 2012", "https://www2.census.gov/programs-surveys/popest/technical-documentation/file-layouts/2010-2012/cc-est2012-alldata.pdf"),
        (2011, "April 1, 2010 to July 1, 2011", "https://www2.census.gov/programs-surveys/popest/technical-documentation/file-layouts/2010-2011/cc-est2011-alldata.pdf"),
        (2010, "April 1, 2000 to July 1, 2010", "https://www2.census.gov/programs-surveys/popest/technical-documentation/file-layouts/2000-2010/cc-est2010-alldata.pdf"),
    ]

    with st.expander("Census Data Links", expanded=False):
        st.markdown("""
**Important Links**:
- [Census Datasets](https://www2.census.gov/programs-surveys/popest/datasets/)
- [2000–2010 Intercensal County](https://www2.census.gov/programs-surveys/popest/datasets/2000-2010/intercensal/county/)
- [2010–2020 County ASRH](https://www2.census.gov/programs-surveys/popest/datasets/2010-2020/counties/asrh/)
- [2020–2023 County ASRH](https://www2.census.gov/programs-surveys/popest/datasets/2020-2023/counties/asrh/)
- [2020–2024 County ASRH](https://www2.census.gov/programs-surveys/popest/datasets/2020-2024/counties/asrh/)
- [Release Schedule](https://www.census.gov/programs-surveys/popest/about/schedule.html)
""")
        st.markdown("---")
        md = "**Documentation Codebooks**\n- [File Layouts Main Page](https://www2.census.gov/programs-surveys/popest/technical-documentation/file-layouts/)\n"
        for y, p, u in docs:
            md += f"- [Vintage {y} ({p})]({u})\n"
        md += "- [Methodology Overview](https://www.census.gov/programs-surveys/popest/technical-documentation/methodology.html)\n"
        md += "- [Modified Race Data](https://www.census.gov/programs-surveys/popest/technical-documentation/research/modified-race-data.html)\n"
        st.markdown(md)
