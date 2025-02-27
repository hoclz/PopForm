import csv

def load_form_control_data(csv_path: str):
    """
    Reads form_control_UI_data.csv which has 7 columns in the following order:
      CountyName, CountyCode, YearValue, Race, AgeGroup, ExplicitBrackets, ImplicitBrackets
    Returns:
      years_list, agegroups_list, races_list, counties_map,
      agegroup_map_explicit, agegroup_map_implicit
    """
    years_set = set()
    agegroups_set = set()
    races_set = set()
    counties_map = {}

    agegroup_map_explicit = {}
    agegroup_map_implicit = {}

    with open(csv_path, mode="r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            county_name = row.get("CountyName", "").strip()
            county_code_str = row.get("CountyCode", "").strip()
            year_val = row.get("YearValue", "").strip()
            race_val = row.get("Race", "").strip()
            age_group = row.get("AgeGroup", "").strip()
            explicit_str = row.get("ExplicitBrackets", "").strip()
            implicit_str = row.get("ImplicitBrackets", "").strip()

            if year_val:
                years_set.add(year_val)
            if age_group:
                agegroups_set.add(age_group)
            if race_val:
                races_set.add(race_val)

            # Parse county code
            county_code = None
            if county_code_str.isdigit():
                county_code = int(county_code_str)
            if county_name and county_code is not None:
                counties_map[county_name] = county_code

            # Parse explicit brackets
            explicit_list = []
            if explicit_str:
                for bracket in explicit_str.split(","):
                    bracket = bracket.strip()
                    if bracket:
                        explicit_list.append(bracket)
            # Parse implicit brackets
            implicit_list = []
            if implicit_str:
                for bracket in implicit_str.split(","):
                    bracket = bracket.strip()
                    if bracket:
                        implicit_list.append(bracket)

            if age_group:
                # Add to explicit map
                if age_group not in agegroup_map_explicit:
                    agegroup_map_explicit[age_group] = []
                agegroup_map_explicit[age_group].extend(explicit_list)

                # Add to implicit map
                if age_group not in agegroup_map_implicit:
                    agegroup_map_implicit[age_group] = []
                agegroup_map_implicit[age_group].extend(implicit_list)

    years_list = sorted(years_set)
    agegroups_list = sorted(agegroups_set)
    races_list = sorted(races_set)

    return (
        years_list,
        agegroups_list,
        races_list,
        counties_map,
        agegroup_map_explicit,
        agegroup_map_implicit
    )
