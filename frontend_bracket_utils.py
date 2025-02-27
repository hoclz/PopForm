import pandas as pd

def parse_implicit_bracket(df: pd.DataFrame, bracket_expr: str) -> pd.Series:
    """
    For an implicit bracket like "0-4", "5-9", "10-14", "80+", "20-64", etc.,
    return a boolean mask for df["Age"] that matches the bracket.

    In our data, df["Age"] contains integer codes 1..18 corresponding to:
      1 -> 0-4, 2 -> 5-9, 3 -> 10-14, 4 -> 15-19, 5 -> 20-24,
      6 -> 25-29, 7 -> 30-34, 8 -> 35-39, 9 -> 40-44, 10 -> 45-49,
      11 -> 50-54, 12 -> 55-59, 13 -> 60-64, 14 -> 65-69, 15 -> 70-74,
      16 -> 75-79, 17 -> 80-84, 18 -> 80+

    Some implicit brackets (e.g., "20-64" or "65+") group several codes.
    """
    bracket_expr = bracket_expr.strip()

    # Mapping from implicit bracket expression to either a single Age code or a range (min, max)
    BRACKET_MAP = {
        "0-4": 1,
        "5-9": 2,
        "10-14": 3,
        "15-19": 4,
        "20-24": 5,
        "25-29": 6,
        "30-34": 7,
        "35-39": 8,
        "40-44": 9,
        "45-49": 10,
        "50-54": 11,
        "55-59": 12,
        "60-64": 13,
        "65-69": 14,
        "70-74": 15,
        "75-79": 16,
        "80-84": 17,
        "80+": 18,

        "20-64": (5, 13),   # codes 5 through 13 (20-24 up to 60-64)
        "65+":   (14, 18),  # codes 14 through 18 (65-69 up to 80+)

        # New two-bracket definitions:
        "0-19": (1, 4),     # codes 1..4 => 0-4, 5-9, 10-14, 15-19
        "20+":  (5, 18)     # codes 5..18 => 20-24, ..., 80+
    }

    # 1) If bracket_expr is in the dictionary, return a mask accordingly
    if bracket_expr in BRACKET_MAP:
        val = BRACKET_MAP[bracket_expr]
        if isinstance(val, int):
            # single code
            return df["Age"] == val
        elif isinstance(val, tuple):
            mn, mx = val
            return (df["Age"] >= mn) & (df["Age"] <= mx)

    # 2) Fallback: try to interpret a generic "X-Y" or "X+" format
    if bracket_expr.endswith("+"):
        try:
            start = int(bracket_expr[:-1])
            return df["Age"] >= start
        except Exception:
            return pd.Series(False, index=df.index)

    elif "-" in bracket_expr:
        parts = bracket_expr.split("-")
        try:
            mn = int(parts[0])
            mx = int(parts[1])
            return (df["Age"] >= mn) & (df["Age"] <= mx)
        except Exception:
            return pd.Series(False, index=df.index)

    # 3) If all else fails, return a False mask
    return pd.Series(False, index=df.index)
