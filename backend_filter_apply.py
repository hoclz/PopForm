# back end code | filter_apply.py

import pandas as pd
from backend_region_definitions import COLLAR_COUNTIES, URBAN_COUNTIES, RURAL_COUNTIES

# Reverse race mapping
REVERSE_RACE_MAP = {
    "Two or More Races": "TOM",
    "American Indian and Alaska Native": "AIAN",
    "Black or African American": "Black",
    "White": "White",
    "Native Hawaiian and Other Pacific Islander": "NHOPI",
    "Asian": "Asian"
}

def apply_filters(
    df: pd.DataFrame,
    selected_counties: list[str],
    selected_race: str,
    selected_ethnicity: str,
    selected_sex: str,
    selected_region: str,
    counties_map: dict[str,int]
) -> pd.DataFrame:
    """
    Applies filters on the DataFrame.
    e.g. if selected_race != "All", we filter by that race code, etc.
    """
    # Race filter
    if selected_race not in ["All", None, ""]:
        race_code = REVERSE_RACE_MAP.get(selected_race, selected_race)
        df = df[df["Race"] == race_code]

    # Ethnicity filter
    if selected_ethnicity == "Hispanic":
        df = df[df["Ethnicity"] == "Hispanic"]
    elif selected_ethnicity == "Not Hispanic":
        df = df[df["Ethnicity"] == "Not Hispanic"]

    # Sex filter
    if selected_sex == "Male":
        df = df[df["Sex"] == "Male"]
    elif selected_sex == "Female":
        df = df[df["Sex"] == "Female"]

    # Region filter
    if selected_region == "Collar Counties":
        df = df[df["County"].isin(COLLAR_COUNTIES)]
    elif selected_region == "Urban Counties":
        df = df[df["County"].isin(URBAN_COUNTIES)]
    elif selected_region == "Rural Counties":
        df = df[df["County"].isin(RURAL_COUNTIES)]

    # Counties filter
    if selected_counties and "All" not in selected_counties:
        codes = []
        for name in selected_counties:
            if name in counties_map:
                codes.append(counties_map[name])
        if codes:
            df = df[df["County"].isin(codes)]

    return df
