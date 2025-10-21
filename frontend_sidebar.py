import streamlit as st
from typing import List, Tuple, Dict

# ──────────────────────────────────────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────────────────────────────────────
RACE_DISPLAY_TO_CODE = {
    "Two or More Races": "TOM",
    "American Indian and Alaska Native": "AIAN",
    "Black or African American": "Black",
    "White": "White",
    "Native Hawaiian and Other Pacific Islander": "NHOPI",
    "Asian": "Asian",
}
RACE_CODE_TO_DISPLAY = {v: k for k, v in RACE_DISPLAY_TO_CODE.items()}

# Stable patterns for CPC/ASRH “ALLDATA”—URLs follow a consistent scheme.
# These are used for the “Download source data for selected years” control.
DATASET_URLS_FOR_VINTAGE: Dict[int, str] = {}
for v in [2010] + list(range(2011, 2020)):  # 2000–2010, then 2011…2019
    period = "2000-2010" if v == 2010 else f"2010-{v}"
    DATASET_URLS_FOR_VINTAGE[v] = f"https://www2.census.gov/programs-surveys/popest/datasets/{period}/counties/asrh/cc-est{v}-alldata.csv"
for v in range(2020, 2025):  # 2020…2024
    period = f"2020-{v}"
    DATASET_URLS_FOR_VINTAGE[v] = f"https://www2.census.gov/programs-surveys/popest/datasets/{period}/counties/asrh/cc-est{v}-alldata.csv"

def _nearest_vintage_for_year(y: int) -> int:
    """Map a calendar year to the CPC 'vintage' file that contains it."""
    if y <= 2010: return 2010
    if 2011 <= y <= 2019: return y
    if 2020 <= y <= 2024: return y
    return 2024

def get_dataset_links_for_years(years: List[int]) -> List[Tuple[int, str]]:
    """Return a de-duplicated (vintage, url) list for the selected years."""
    vintages = sorted({ _nearest_vintage_for_year(int(y)) for y in years })
    return [(v, DATASET_URLS_FOR_VINTAGE.get(v, "")) for v in vintages]

# ──────────────────────────────────────────────────────────────────────────────
# Sidebar Builder
# ──────────────────────────────────────────────────────────────────────────────
def render_sidebar_controls(
    years_list: List[int],
    races_list_raw: List[str],
    counties_map: Dict[str, int],
    agegroup_map_implicit: Dict[str, list],
    agegroups_list_raw: List[str] = None,
):
    """Render all sidebar controls (grouped into expanders)."""

    sb = st.sidebar
    sb.markdown("## 🔍 Query Builder")

    # — Geography & Time —
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

    # — Demographics —
    with sb.expander("👥 Demographics", expanded=False):
        race_opts = ["All"]
        for rcode in sorted(races_list_raw):
            if rcode != "All":
                race_opts.append(RACE_CODE_TO_DISPLAY.get(rcode, rcode))
        selected_race_display = st.selectbox("Race Filter:", race_opts, index=0)
        selected_sex = st.radio("Sex:", ["All", "Male", "Female"], horizontal=True)
        selected_ethnicity = st.radio("Ethnicity:", ["All", "Hispanic", "Not Hispanic"], horizontal=True)
        region_options = ["None", "Cook County", "Collar Counties", "Urban Counties", "Rural Counties"]
        selected_region = st.selectbox("Region:", region_options, index=0)

    # — Age Settings —
    with sb.expander("📋 Age Settings", expanded=False):
        AGEGROUP_DISPLAY_TO_CODE = {
            "All": "All",
            "18-Bracket": "agegroup13",
            "6-Bracket": "agegroup14",
            "2-Bracket": "agegroup15",
        }
        selected_agegroup_display = st.selectbox("Age Group:", list(AGEGROUP_DISPLAY_TO_CODE.keys()), index=0)
        if selected_agegroup_display != "All":
            code = AGEGROUP_DISPLAY_TO_CODE[selected_agegroup_display]
            br = agegroup_map_implicit.get(code, [])
            if br:
                st.caption("**Age Brackets:** " + ", ".join(map(str, br)))
        enable_custom_ranges = st.checkbox("Enable custom age ranges", value=False)
        st.caption("When enabled, these custom ranges override the Age Group selection.")
        custom_ranges = []
        if enable_custom_ranges:
            # up to 3 quick ranges
            for i, (d_min, d_max) in enumerate([(1,5),(6,10),(11,15)], start=1):
                if st.checkbox(f"Range {i}", key=f"r{i}"):
                    mn = st.number_input(f"Min {i} (1–18)", 1, 18, d_min, key=f"mn{i}")
                    mx = st.number_input(f"Max {i} (1–18)", 1, 18, d_max, key=f"mx{i}")
                    if mn <= mx:
                        custom_ranges.append((int(mn), int(mx)))

    # — Group Results By —
    with sb.expander("📈 Group Results By", expanded=False):
        grouping_vars = st.multiselect(
            "Group by any combination (or choose 'All' for totals):",
            ["All", "Age", "Race", "Ethnicity", "Sex", "Region", "County"],
            default=["All"],
        )
        if "All" in grouping_vars and len(grouping_vars) > 1:
            st.info("Using 'All' (totals only). Other selections ignored.")
            grouping_vars = ["All"]

    # — Pivot (optional) —
    with sb.expander("🔁 Pivot Table (optional)", expanded=False):
        st.session_state.setdefault("pivot_enable", False)
        st.session_state.setdefault("pivot_rows", [])
        st.session_state.setdefault("pivot_cols", [])
        st.session_state.setdefault("pivot_vals", ["Count"])
        st.session_state.setdefault("pivot_agg", "sum")
        st.session_state.setdefault("pivot_pct_mode", "Weighted by Count (rows)")
        st.session_state.setdefault("pivot_totals", True)
        st.session_state.setdefault("pivot_flatten", True)
        st.session_state.setdefault("pivot_sort_rows", False)
        st.session_state.setdefault("pivot_export_mode", "Both")
        st.session_state.setdefault("pivot_append_mode", False)

        st.session_state.pivot_enable = st.checkbox("Enable pivot", value=st.session_state.pivot_enable)

        dim_options = ["County Name","County Code","Region","AgeGroup","Race","Ethnicity","Sex","Year"]
        default_rows = ["AgeGroup"] if "AgeGroup" in dim_options else []
        default_cols = ["Race"]

        st.session_state.pivot_rows = st.multiselect("Rows", dim_options, default=st.session_state.pivot_rows or default_rows, help="Choose one or more row variables.")
        st.session_state.pivot_cols = st.multiselect("Columns", dim_options, default=st.session_state.pivot_cols or default_cols)
        st.session_state.pivot_vals = st.multiselect("Values", ["Count","Percent"], default=st.session_state.pivot_vals)
        st.session_state.pivot_agg = st.selectbox("Aggregation for Count", ["sum","mean","median","max","min"], index=["sum","mean","median","max","min"].index(st.session_state.pivot_agg))
        st.session_state.pivot_pct_mode = st.selectbox("Percent aggregation", ["Weighted by Count (rows)","Mean (unweighted)"], index=0 if st.session_state.pivot_pct_mode.startswith("Weighted") else 1)
        st.session_state.pivot_totals = st.checkbox("Show totals (margins)", value=st.session_state.pivot_totals)
        st.session_state.pivot_flatten = st.checkbox("Flatten headers for CSV", value=st.session_state.pivot_flatten)
        st.session_state.pivot_sort_rows = st.checkbox("Sort rows by grand total (desc)", value=st.session_state.pivot_sort_rows)

        # NEW: Append mode
        st.session_state.pivot_append_mode = st.checkbox(
            "Append when multiple row variables are selected (one pivot per row var, stacked)",
            value=st.session_state.pivot_append_mode,
            help="If checked and you choose multiple row variables, the app builds one pivot per row variable and appends them in a single table with a 'PivotRowDim' column."
        )

        st.session_state.pivot_export_mode = st.radio("CSV download includes", ["Raw","Pivot","Both"], index=["Raw","Pivot","Both"].index(st.session_state.pivot_export_mode))

    # — Output Options —
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

    # — UI Preferences —
    with sb.expander("🧰 UI Preferences", expanded=False):
        ui_sidebar_resizable = st.checkbox("Enable sidebar resizing", value=False, help="When enabled, you can set a custom sidebar width.")
        ui_sidebar_width = st.slider("Sidebar width (px)", 260, 520, 340, 10, disabled=not ui_sidebar_resizable)
        ui_sidebar_locked = st.checkbox("Lock sidebar width", value=False, disabled=not ui_sidebar_resizable)

    return {
        "debug_mode": debug_mode,
        "selected_years": selected_years,
        "selected_counties": selected_counties,
        "selected_race_display": selected_race_display,
        "selected_race_code": "All" if selected_race_display == "All" else RACE_DISPLAY_TO_CODE.get(selected_race_display, selected_race_display),
        "selected_sex": selected_sex,
        "selected_ethnicity": selected_ethnicity,
        "selected_region": selected_region,
        "selected_agegroup_display": selected_agegroup_display,
        "agegroup_for_backend": {"All": None, "18-Bracket": "agegroup13", "6-Bracket": "agegroup14", "2-Bracket": "agegroup15"}[selected_agegroup_display],
        "enable_custom_ranges": enable_custom_ranges,
        "custom_ranges": custom_ranges,
        "grouping_vars": grouping_vars,
        "include_breakdown": include_breakdown,

        # Pivot selections back to app
        "pivot_enable": st.session_state.pivot_enable,
        "pivot_rows": st.session_state.pivot_rows,
        "pivot_cols": st.session_state.pivot_cols,
        "pivot_vals": st.session_state.pivot_vals,
        "pivot_agg": st.session_state.pivot_agg,
        "pivot_pct_mode": st.session_state.pivot_pct_mode,
        "pivot_totals": st.session_state.pivot_totals,
        "pivot_flatten": st.session_state.pivot_flatten,
        "pivot_sort_rows": st.session_state.pivot_sort_rows,
        "pivot_export_mode": st.session_state.pivot_export_mode,
        "pivot_append_mode": st.session_state.pivot_append_mode,

        # UI prefs
        "ui_sidebar_resizable": ui_sidebar_resizable,
        "ui_sidebar_width": ui_sidebar_width,
        "ui_sidebar_locked": ui_sidebar_locked,
    }


# ──────────────────────────────────────────────────────────────────────────────
# Right-side links & documentation
# ──────────────────────────────────────────────────────────────────────────────
def display_census_links(selected_years: List[int] = None):
    """Right-side expander for Census links, source downloads, and documentation."""
    selected_years = selected_years or []

    docs = [
        (2024, "Apr 1, 2020 – Jul 1, 2024", "https://www2.census.gov/programs-surveys/popest/technical-documentation/file-layouts/2020-2024/CC-EST2024-ALLDATA.pdf"),
        (2023, "Apr 1, 2020 – Jul 1, 2023", "https://www2.census.gov/programs-surveys/popest/technical-documentation/file-layouts/2020-2023/CC-EST2023-ALLDATA.pdf"),
        (2022, "Apr 1, 2020 – Jul 1, 2022", "https://www2.census.gov/programs-surveys/popest/technical-documentation/file-layouts/2020-2022/cc-est2022-alldata.pdf"),
        (2021, "Apr 1, 2020 – Jul 1, 2021", "https://www2.census.gov/programs-surveys/popest/technical-documentation/file-layouts/2020-2021/cc-est2021-alldata.pdf"),
        (2020, "Apr 1, 2010 – Jul 1, 2020", "https://www2.census.gov/programs-surveys/popest/technical-documentation/file-layouts/2010-2020/cc-est2020-alldata.pdf"),
        (2019, "Apr 1, 2010 – Jul 1, 2019", "https://www2.census.gov/programs-surveys/popest/technical-documentation/file-layouts/2010-2019/cc-est2019-alldata.pdf"),
        (2018, "Apr 1, 2010 – Jul 1, 2018", "https://www2.census.gov/programs-surveys/popest/technical-documentation/file-layouts/2010-2018/cc-est2018-alldata.pdf"),
        (2017, "Apr 1, 2010 – Jul 1, 2017", "https://www2.census.gov/programs-surveys/popest/technical-documentation/file-layouts/2010-2017/cc-est2017-alldata.pdf"),
        (2016, "Apr 1, 2010 – Jul 1, 2016", "https://www2.census.gov/programs-surveys/popest/technical-documentation/file-layouts/2010-2016/cc-est2016-alldata.pdf"),
        (2015, "Apr 1, 2010 – Jul 1, 2015", "https://www2.census.gov/programs-surveys/popest/technical-documentation/file-layouts/2010-2015/cc-est2015-alldata.pdf"),
        (2014, "Apr 1, 2010 – Jul 1, 2014", "https://www2.census.gov/programs-surveys/popest/technical-documentation/file-layouts/2010-2014/cc-est2014-alldata.pdf"),
        (2013, "Apr 1, 2010 – Jul 1, 2013", "https://www2.census.gov/programs-surveys/popest/technical-documentation/file-layouts/2010-2013/cc-est2013-alldata.pdf"),
        (2012, "Apr 1, 2010 – Jul 1, 2012", "https://www2.census.gov/programs-surveys/popest/technical-documentation/file-layouts/2010-2012/cc-est2012-alldata.pdf"),
        (2011, "Apr 1, 2010 – Jul 1, 2011", "https://www2.census.gov/programs-surveys/popest/technical-documentation/file-layouts/2010-2011/cc-est2011-alldata.pdf"),
        (2010, "Apr 1, 2000 – Jul 1, 2010", "https://www2.census.gov/programs-surveys/popest/technical-documentation/file-layouts/2000-2010/cc-est2010-alldata.pdf"),
    ]

    with st.expander("Census Data Links", expanded=False):
        st.markdown("""
**Important Links**  
- Datasets index: https://www2.census.gov/programs-surveys/popest/datasets/  
- 2000–2010 Intercensal County (ASRH): https://www2.census.gov/programs-surveys/popest/datasets/2000-2010/intercensal/county/  
- 2010–2020 County ASRH: https://www2.census.gov/programs-surveys/popest/datasets/2010-2020/counties/asrh/  
- 2020–2024 County ASRH: https://www2.census.gov/programs-surveys/popest/datasets/2020-2024/counties/asrh/  
- Release Schedule: https://www.census.gov/programs-surveys/popest/about/schedule.html
""")

        st.markdown("---")
        md = "**Documentation Codebooks**\n\n"
        for y, p, u in docs:
            md += f"- Vintage **{y}** ({p}): {u}\n"
        md += "\n- Methodology Overview: https://www.census.gov/programs-surveys/popest/technical-documentation/methodology.html\n"
        md += "- Modified Race Data: https://www.census.gov/programs-surveys/popest/technical-documentation/research/modified-race-data.html\n"
        st.markdown(md)

        # NEW: direct source data download links for the user's selected years
        if selected_years:
            st.markdown("---")
            st.subheader("Download Source Data (Selected Years)")
            for v, url in get_dataset_links_for_years(selected_years):
                if url:
                    st.link_button(f"⬇️ CC-EST{v}-ALLDATA (CSV)", url)

        # Rationale for the 18 CPC age groups
        st.markdown("---")
        st.subheader("About the 18 CPC Age Groups")
        st.markdown("""
The **County Population by Characteristics (CPC)** files publish 5-year age buckets for county-level estimates, aligned to
federal dissemination standards and disclosure avoidance. The **18 groups** used in this app are:  
**0–4, 5–9, 10–14, 15–19, 20–24, 25–29, 30–34, 35–39, 40–44, 45–49, 50–54, 55–59, 60–64, 65–69, 70–74, 75–79, 80–84, 80+**.  
They harmonize vintage-to-vintage files, keep cells large enough to protect privacy, and match common analytic use cases 
(e.g., dependency ratios, school-age/prime-age/older cohorts). When you pick **18-Bracket** in the app, we aggregate to this
canonical set for comparability across years and regions.
""")
