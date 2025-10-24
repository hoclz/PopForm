
import streamlit as st
from typing import List, Tuple, Dict

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
    years_list: List[int],
    races_list_raw: List[str],
    counties_map: Dict[str, int],
    agegroup_map_implicit: Dict[str, list],
    agegroups_list_raw: List[str] = None,
):
    """Render Query Builder + Grouping in the sidebar (all closed by default)."""
    sb = st.sidebar
    sb.markdown("## 🔍 Query Builder")

    # 📍 Geography & Time
    with sb.expander("📍 Geography & Time", expanded=False):
        selected_years = st.multiselect(
            "Select Year(s):",
            options=years_list,
            default=years_list[-1:] if years_list else [],
            key="ui_selected_years",
        )
        all_counties = ["All"] + sorted(counties_map.keys())
        selected_counties = st.multiselect(
            "Select Counties:", options=all_counties, default=["All"], key="ui_selected_counties"
        )
        if "All" in selected_counties and len(selected_counties) > 1:
            st.info("Using 'All' counties (specific selections ignored).")
            selected_counties = ["All"]

    # 👥 Demographics & Region filters
    with sb.expander("👥 Demographics", expanded=False):
        race_opts = ["All"]
        for rcode in sorted(races_list_raw):
            if rcode != "All":
                race_opts.append(RACE_CODE_TO_DISPLAY.get(rcode, rcode))
        selected_race_display = st.selectbox("Race Filter:", race_opts, index=0, key="ui_selected_race_display")
        selected_sex = st.radio("Sex:", ["All", "Male", "Female"], horizontal=True, key="ui_selected_sex")
        selected_ethnicity = st.radio(
            "Ethnicity:", ["All", "Hispanic", "Not Hispanic"], horizontal=True, key="ui_selected_ethnicity"
        )

        # include Cook County so labels match backend region mapping
        region_options = ["None", "Cook County", "Collar Counties", "Urban Counties", "Rural Counties"]
        selected_region = st.selectbox("Region:", region_options, index=0, key="ui_selected_region")

    # 📋 Age Settings
    with sb.expander("📋 Age Settings", expanded=False):
        AGEGROUP_DISPLAY_TO_CODE = {
            "All": "All",
            "18-Bracket": "agegroup13",
            "6-Bracket": "agegroup14",
            "2-Bracket": "agegroup15",
        }
        selected_agegroup_display = st.selectbox(
            "Age Group:", list(AGEGROUP_DISPLAY_TO_CODE.keys()), index=0, key="ui_selected_agegroup_display"
        )
        if selected_agegroup_display != "All":
            code = AGEGROUP_DISPLAY_TO_CODE[selected_agegroup_display]
            br = agegroup_map_implicit.get(code, [])
            if br:
                st.caption("**Age Brackets:** " + ", ".join(map(str, br)))

        enable_custom_ranges = st.checkbox("Enable custom age ranges", value=False, key="ui_enable_custom_ranges")
        st.caption("When enabled, these custom ranges override the Age Group selection.")
        custom_ranges = []
        if enable_custom_ranges:
            for i, (d_min, d_max) in enumerate([(1, 5), (6, 10), (11, 15)], start=1):
                if st.checkbox(f"Range {i}", key=f"ui_r{i}"):
                    mn = st.number_input(f"Min {i} (1–18)", 1, 18, d_min, key=f"ui_mn{i}")
                    mx = st.number_input(f"Max {i} (1–18)", 1, 18, d_max, key=f"ui_mx{i}")
                    if mn <= mx:
                        custom_ranges.append((int(mn), int(mx)))

    # 📈 Group Results By
    with sb.expander("📈 Group Results By", expanded=False):
        grouping_vars = st.multiselect(
            "Group by any combination (or choose 'All' for totals):",
            ["All", "Age", "Race", "Ethnicity", "Sex", "Region", "County"],
            default=["All"],
            key="ui_grouping_vars",
        )
        if "All" in grouping_vars and len(grouping_vars) > 1:
            st.info("Using 'All' (totals only). Other selections ignored.")
            grouping_vars = ["All"]

    # 🧩 Tokenization (POP_LONG_Q)
    with sb.expander("🧩 Tokenized Output • POP_LONG_Q", expanded=False):
        enable_tokenization = st.checkbox(
            "Enable POP_LONG tokenization (build q1–q8 fields)",
            value=False, key="ui_enable_tokenization",
            help="Creates a SAS-style tokenized extract like POP_LONG_Q for use in downstream pipelines."
        )
        token_schema = st.selectbox(
            "Token schema",
            ["SAS/POP_LONG_Q (S/E tokens)", "Custom (minimal)"],
            index=0, key="ui_token_schema",
            help="SAS/POP_LONG_Q uses S1/S2 for Sex, E1/E2 for Ethnicity, constant 'R' for Race indicator, "
                 "Age=1–18 for CPC 5-year groups, q7=1 and q8=population count."
        )
        apply_pop_long_rules = st.checkbox(
            "Apply POP_LONG standard rules (age≠0 for 2020+, only White/Black/AIAN/Asian+NHOPI)",
            value=True, key="ui_apply_pop_long_rules"
        )
        token_age_scheme = st.selectbox(
            "Age code scheme for q5",
            ["CPC 18 buckets (1–18)", "Raw AGEGRP (0–18)"],
            index=0, key="ui_token_age_scheme"
        )
        include_county_cols = st.checkbox(
            "Include County Name/Code columns in tokenized output",
            value=True, key="ui_token_include_county"
        )
        st.caption(
            "When tokenization is enabled, the app builds a long-form table per **Year × County × Sex × Ethnicity × Race × Age**. "
            "The constant `q7=1` and `q8` equals the population count. You can still use the normal report and pivot features."
        )

    # ⚙️ Output Options
    with sb.expander("⚙️ Output Options", expanded=False):
        include_breakdown = st.checkbox(
            "Include Individual County Breakdowns",
            value=True,
            key="ui_include_breakdown",
            help="Show a separate table for each selected county (in addition to combined results).",
        )
        # Keep existing behavior: if grouping by County, per-county breakdown is redundant
        if "County" in grouping_vars and include_breakdown:
            st.info("Grouping by County already provides county rows. Turning off extra breakdowns.")
            include_breakdown = False
        debug_mode = st.checkbox("Debug Mode", value=False, key="ui_debug_mode")

    return {
        "debug_mode": debug_mode,
        "selected_years": selected_years,
        "selected_counties": selected_counties,
        "selected_race_display": selected_race_display,
        "selected_race_code": "All"
        if selected_race_display == "All"
        else RACE_DISPLAY_TO_CODE.get(selected_race_display, selected_race_display),
        "selected_sex": selected_sex,
        "selected_ethnicity": selected_ethnicity,
        "selected_region": selected_region,
        "selected_agegroup_display": selected_agegroup_display,
        "agegroup_for_backend": {
            "All": None,
            "18-Bracket": "agegroup13",
            "6-Bracket": "agegroup14",
            "2-Bracket": "agegroup15",
        }[selected_agegroup_display],
        "enable_custom_ranges": enable_custom_ranges,
        "custom_ranges": custom_ranges,
        "grouping_vars": grouping_vars,
        "include_breakdown": include_breakdown,
        # --- tokenization selections ---
        "tokenization": {
            "enabled": enable_tokenization,
            "schema": token_schema,
            "apply_pop_long_rules": apply_pop_long_rules,
            "age_scheme": token_age_scheme,
            "include_county_cols": include_county_cols,
        }
    }


def display_census_links():
    """Right-side expander for Census links (default closed), including 'About the 18 CPC Age Groups'."""
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
        st.markdown(
            """
**Important Links**:
- [Census Datasets](https://www2.census.gov/programs-surveys/popest/datasets/)
- [2000–2010 Intercensal County](https://www2.census.gov/programs-surveys/popest/datasets/2000-2010/intercensal/county/)
- [2010–2020 County ASRH](https://www2.census.gov/programs-surveys/popest/datasets/2010-2020/counties/asrh/)
- [2020–2023 County ASRH](https://www2.census.gov/programs-surveys/popest/datasets/2020-2023/counties/asrh/)
- [2020–2024 County ASRH](https://www2.census.gov/programs-surveys/popest/datasets/2020-2024/counties/asrh/)
- [Release Schedule](https://www.census.gov/programs-surveys/popest/about/schedule.html)
"""
        )
        st.markdown("---")
        md = "**Documentation Codebooks**\n- [File Layouts Main Page](https://www2.census.gov/programs-surveys/popest/technical-documentation/file-layouts/)\n"
        for y, p, u in docs:
            md += f"- [Vintage {y} ({p})]({u})\n"
        md += "- [Methodology Overview](https://www.census.gov/programs-surveys/popest/technical-documentation/methodology.html)\n"
        md += "- [Modified Race Data](https://www.census.gov/programs-surveys/popest/technical-documentation/research/modified-race-data.html)\n"
        st.markdown(md)

        # --- About the 18 CPC Age Groups ---
        st.markdown("---")
        st.subheader("About the 18 CPC Age Groups")
        st.markdown(
            """
The **County Population by Characteristics (CPC)** files publish 5-year age buckets for county-level estimates, aligned to
federal dissemination standards and disclosure avoidance. The **18 groups** commonly used are:  
**0–4, 5–9, 10–14, 15–19, 20–24, 25–29, 30–34, 35–39, 40–44, 45–49, 50–54, 55–59, 60–64, 65–69, 70–74, 75–79, 80–84, 80+**.

These brackets harmonize vintage-to-vintage files, keep cells large enough to protect privacy, and match common analytic
use cases (e.g., dependency ratios, school-age/prime-age/older cohorts). When **18-Bracket** is selected, results are aggregated
to this canonical set for comparability across years and regions.
"""
        )
