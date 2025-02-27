import os
import pandas as pd
from backend_filter_apply import apply_filters
from backend_filter_age import filter_by_custom_age_ranges, filter_by_predefined_agegroup

def process_population_data(
    data_folder: str,
    agegroup_map_explicit: dict[str, list[str]],  # explicit brackets for filtering
    counties_map: dict[str, int],
    selected_years: list[str],
    selected_counties: list[str],
    selected_race: str,
    selected_ethnicity: str,
    selected_sex: str,
    selected_region: str,
    selected_agegroup: str,
    custom_age_ranges: list[tuple[int, int]]
) -> pd.DataFrame:
    """
    1) For each year, load CSV, apply filters, and apply custom or explicit age brackets.
    2) Concatenate all results and return the final DataFrame.
    """
    frames = []

    for year_str in selected_years:
        if year_str.lower() == "all":
            # If user literally selected "All" year, skip or handle differently
            continue

        filename = f"{year_str} population.csv"
        full_path = os.path.join(data_folder, filename)
        if not os.path.exists(full_path):
            # Skip if no file exists for the year
            continue

        df_year = pd.read_csv(full_path, encoding="utf-8")

        # Optionally add the Year column if it doesn't exist
        if "Year" not in df_year.columns:
            df_year["Year"] = year_str

        # Convert numeric columns
        if "Count" in df_year.columns:
            df_year["Count"] = pd.to_numeric(df_year["Count"], errors="coerce").fillna(0).astype(int)
        if "Age" in df_year.columns:
            df_year["Age"] = pd.to_numeric(df_year["Age"], errors="coerce").fillna(0).astype(int)

        # Apply basic filters
        df_year = apply_filters(
            df_year,
            selected_counties=selected_counties,
            selected_race=selected_race,
            selected_ethnicity=selected_ethnicity,
            selected_sex=selected_sex,
            selected_region=selected_region,
            counties_map=counties_map
        )

        # Apply age filtering: either custom ranges or predefined agegroup brackets
        if custom_age_ranges:
            df_year = filter_by_custom_age_ranges(df_year, custom_age_ranges)
        else:
            if selected_agegroup and selected_agegroup in agegroup_map_explicit:
                bracket_expressions = agegroup_map_explicit[selected_agegroup]
                df_year = filter_by_predefined_agegroup(df_year, bracket_expressions)

        frames.append(df_year)

    if frames:
        final_df = pd.concat(frames, ignore_index=True)
    else:
        final_df = pd.DataFrame(columns=["County", "Race", "Sex", "Ethnicity", "Count", "Age", "Year"])

    return final_df
