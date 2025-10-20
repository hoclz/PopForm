
import streamlit as st

# ─────────────────────────────────────────────────────────────────────────────
# Race display ↔ internal code mapping
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
    \"\"\"Render the entire Query Builder + Output Configuration in the *sidebar*.

    Returns a dict of all chosen filters/settings. This keeps app.py clean.
    \"\"\"
    sb = st.sidebar
    debug_mode = sb.checkbox("Debug Mode", value=False)

    sb.markdown("## 🔍 Query Builder")

    # Geography & Time
    with sb.expander("📍 Geography & Time", expanded=True):
        selected_years = st.multiselect(
            "Select Year(s):",
            options=years_list,
            default=years_list[-1:] if years_list else [],
            help="Choose one or more years to analyze."
        )
        all_counties = ["All"] + sorted(counties_map.keys())
        selected_counties = st.multiselect(
            "Select Counties:",
            options=all_counties,
            default=["All"],
            help="Choose counties to include. 'All' includes all Illinois counties."
        )
        if "All" in selected_counties and len(selected_counties) > 1:
            st.info("Using 'All' counties (specific selections ignored).")
            selected_counties = ["All"]

    # Demographics
    with sb.expander("👥 Demographics", expanded=True):
        race_opts = ["All"]
        for rcode in sorted(races_list_raw):
            if rcode == "All":
                continue
            race_opts.append(RACE_CODE_TO_DISPLAY.get(rcode, rcode))
        selected_race_display = st.selectbox(
            "Race Filter:",
            race_opts,
            index=0,
            help="Filter data by race category (applies before grouping)."
        )
        selected_sex = st.radio("Sex:", ["All", "Male", "Female"], horizontal=True)
        selected_ethnicity = st.radio("Ethnicity:", ["All", "Hispanic", "Not Hispanic"], horizontal=True)
        region_options = ["None", "Collar Counties", "Urban Counties", "Rural Counties"]
        selected_region = st.selectbox("Region:", region_options, index=0)

    # Age Settings
    with sb.expander("📋 Age Settings", expanded=True):
        AGEGROUP_DISPLAY_TO_CODE = {
            "All": "All",
            "18-Bracket": "agegroup13",
            "6-Bracket":  "agegroup14",
            "2-Bracket":  "agegroup15",
        }
        selected_agegroup_display = st.selectbox(
            "Age Group:",
            list(AGEGROUP_DISPLAY_TO_CODE.keys()),
            index=0,
            help="Choose predefined age bracket grouping."
        )
        if selected_agegroup_display != "All":
            code = AGEGROUP_DISPLAY_TO_CODE[selected_agegroup_display]
            br = agegroup_map_implicit.get(code, [])
            if br:
                st.caption("**Age Brackets:** " + ", ".join(map(str, br)))

        enable_custom_ranges = st.checkbox(
            "Enable custom age ranges",
            value=False,
            help=("Age codes: 1=0–4, 2=5–9, 3=10–14, 4=15–19, 5=20–24, 6=25–29, "
                  "7=30–34, 8=35–39, 9=40–44, 10=45–49, 11=50–54, 12=55–59, "
                  "13=60–64, 14=65–69, 15=70–74, 16=75–79, 17=80–84, 18=80+.")
        )
        st.caption("When enabled, these custom ranges override the Age Group selection.")
        custom_ranges = []
        if enable_custom_ranges:
            # Keep it simple and compact
            for i, (d_min, d_max) in enumerate([(1,5),(6,10),(11,15)], start=1):
                if st.checkbox(f"Range {i}", key=f"r{i}"):
                    mn = st.number_input(f"Min {i} (1–18)", 1, 18, d_min, key=f"mn{i}")
                    mx = st.number_input(f"Max {i} (1–18)", 1, 18, d_max, key=f"mx{i}")
                    if mn <= mx:
                        custom_ranges.append((int(mn), int(mx)))

    # Output Configuration
    sb.markdown("## 📈 Output Configuration")
    grouping_vars = st.multiselect(
        "Group Results By:",
        ["All", "Age", "Race", "Ethnicity", "Sex", "County"],
        default=["All"],
        help="Choose 'All' for totals only, or select columns (e.g., Race + Sex)."
    )
    if "All" in grouping_vars and len(grouping_vars) > 1:
        st.info("Using 'All' (totals only). Other selections ignored.")
        grouping_vars = ["All"]

    include_breakdown = st.checkbox(
        "Include Individual County Breakdowns",
        value=True,
        help="Show a separate table for each selected county (in addition to combined results)."
    )
    if "County" in grouping_vars and include_breakdown:
        st.info("When grouping by County, individual county breakdowns are redundant and will be skipped.")
        include_breakdown = False

    age_map = {"All": None, "18-Bracket": "agegroup13", "6-Bracket": "agegroup14", "2-Bracket": "agegroup15"}

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
        "agegroup_for_backend": age_map[selected_agegroup_display],
        "enable_custom_ranges": enable_custom_ranges,
        "custom_ranges": custom_ranges,
        "grouping_vars": grouping_vars,
        "include_breakdown": include_breakdown,
    }
