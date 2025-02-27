#  backend_filter_age.py

import pandas as pd
import re  # For regex

def filter_by_custom_age_ranges(df: pd.DataFrame, custom_age_ranges: list[tuple[int,int]]) -> pd.DataFrame:
    """
    Applies a union (OR) of custom age range conditions.
    Example: [(0,4), (5,9)] => keep rows where Age is in [0..4] OR [5..9].
    """
    if df.empty:
        return df

    combined_mask = False
    for (mn, mx) in custom_age_ranges:
        combined_mask = combined_mask | ((df["Age"] >= mn) & (df["Age"] <= mx))
    return df[combined_mask]


def filter_by_predefined_agegroup(df: pd.DataFrame, bracket_expressions: list[str]) -> pd.DataFrame:
    """
    Applies a union (OR) of bracket expressions.
    E.g. "Age=1", "Age=2", "Age>=5 AND Age<=9", "0-4", etc.
    """
    if df.empty or not bracket_expressions:
        return df

    combined_mask = False
    for expr in bracket_expressions:
        expr = expr.strip()
        mask = parse_age_expression(df, expr)
        combined_mask = combined_mask | mask

    return df[combined_mask]


def parse_age_expression(df: pd.DataFrame, expr: str):
    """
    A naive parser for expressions like:
      - "Age=1"
      - "0-4"
      - "Age>=10 AND Age<=14"
    Expects df["Age"] to be numeric.
    """
    expr = expr.replace(" ", "")

    # e.g. "0-4"
    dash_match = re.match(r"^(\d+)-(\d+)$", expr)
    if dash_match:
        mn = int(dash_match.group(1))
        mx = int(dash_match.group(2))
        return (df["Age"] >= mn) & (df["Age"] <= mx)

    # e.g. "Age=5"
    eq_match = re.match(r"^Age=(\d+)$", expr)
    if eq_match:
        val = int(eq_match.group(1))
        return (df["Age"] == val)

    # e.g. "Age>=10 AND Age<=14"
    if "AND" in expr.upper():
        parts = expr.upper().split("AND")
        mask = True
        for part in parts:
            part = part.strip()
            ge_match = re.match(r"^AGE>=(\d+)$", part)
            le_match = re.match(r"^AGE<=(\d+)$", part)
            if ge_match:
                val = int(ge_match.group(1))
                mask = mask & (df["Age"] >= val)
            elif le_match:
                val = int(le_match.group(1))
                mask = mask & (df["Age"] <= val)
        return mask

    # e.g. "Age>=10"
    ge_alone = re.match(r"^AGE>=(\d+)$", expr.upper())
    if ge_alone:
        val = int(ge_alone.group(1))
        return (df["Age"] >= val)

    # e.g. "Age<=14"
    le_alone = re.match(r"^AGE<=(\d+)$", expr.upper())
    if le_alone:
        val = int(le_alone.group(1))
        return (df["Age"] <= val)

    # fallback => exclude all
    return False
