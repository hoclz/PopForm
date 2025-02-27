import tkinter as tk
import pandas as pd

def show_multi_year_report_in_new_window(parent, results_list):
    """
    Displays multiple years' aggregated results in a scrollable Toplevel window.
    Each element in results_list is:
      (year, final_df, age_group_chosen, ethnicity, sex, region, race, counties_str, custom_age_str, years_title)
    final_df must have columns ["AgeGroup", "Count", "Percent", "Year"] (even if empty).
    """
    top = tk.Toplevel(parent)
    top.title("Population Distribution Report")

    canvas = tk.Canvas(top, width=800, height=600)
    scrollbar = tk.Scrollbar(top, orient="vertical", command=canvas.yview)
    scrollable_frame = tk.Frame(canvas)

    scrollable_frame.bind("<Configure>",
        lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
    )
    canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)

    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    row_idx = 0
    lbl_title = tk.Label(scrollable_frame, text="Population Distribution Report", font=("Arial", 14, "bold"))
    lbl_title.grid(row=row_idx, column=0, columnspan=3, sticky="w", padx=10, pady=10)
    row_idx += 1

    for (year, final_df, age_group_chosen, ethnicity, sex, region, race, counties_str, custom_age_str, years_title) in results_list:
        # Display year and the computed title (e.g. "(2000)" or "(2000, 2001)")
        lbl_section = tk.Label(scrollable_frame, text=f"Year: {year} {years_title}", font=("Arial", 12, "bold"))
        lbl_section.grid(row=row_idx, column=0, columnspan=3, sticky="w", padx=10, pady=5)
        row_idx += 1

        # Show the user-chosen filters
        details_list = [
            f"Age Group: {age_group_chosen}",
            f"Ethnicity: {ethnicity}",
            f"Sex: {sex}",
            f"Region: {region}",
            f"Race: {race}",
            f"Counties: {counties_str}",
            f"Custom Age: {custom_age_str}",
        ]
        for d in details_list:
            tk.Label(scrollable_frame, text=d, font=("Arial", 10)).grid(
                row=row_idx, column=0, columnspan=3, sticky="w", padx=30
            )
            row_idx += 1

        row_idx += 1  # blank line

        if final_df.empty:
            tk.Label(scrollable_frame, text="No data found.", font=("Arial", 10, "italic")
                     ).grid(row=row_idx, column=0, columnspan=3, sticky="w", padx=10)
            row_idx += 2
            continue

        # Table headers
        tk.Label(scrollable_frame, text="Age Group", font=("Arial", 10, "bold")
                 ).grid(row=row_idx, column=0, sticky="w", padx=10)
        tk.Label(scrollable_frame, text="Population Count", font=("Arial", 10, "bold")
                 ).grid(row=row_idx, column=1, sticky="w", padx=10)
        tk.Label(scrollable_frame, text="Percent", font=("Arial", 10, "bold")
                 ).grid(row=row_idx, column=2, sticky="w", padx=10)
        row_idx += 1

        for i, row_data in final_df.iterrows():
            ag = row_data["AgeGroup"]
            cnt = row_data["Count"]
            pct = row_data["Percent"]
            tk.Label(scrollable_frame, text=str(ag)).grid(row=row_idx, column=0, sticky="w", padx=10)
            tk.Label(scrollable_frame, text=f"{int(cnt):,d}").grid(row=row_idx, column=1, sticky="w", padx=10)
            tk.Label(scrollable_frame, text=f"{pct:.1f}%").grid(row=row_idx, column=2, sticky="w", padx=10)
            row_idx += 1

        total_pop = final_df["Count"].sum()
        tk.Label(scrollable_frame, text="Total", font=("Arial", 10, "bold")
                 ).grid(row=row_idx, column=0, sticky="w", padx=10)
        tk.Label(scrollable_frame, text=f"{int(total_pop):,d}", font=("Arial", 10, "bold")
                 ).grid(row=row_idx, column=1, sticky="w", padx=10)
        if total_pop > 0:
            tk.Label(scrollable_frame, text="100.0%", font=("Arial", 10, "bold")
                     ).grid(row=row_idx, column=2, sticky="w", padx=10)
        else:
            tk.Label(scrollable_frame, text="N/A", font=("Arial", 10, "bold")
                     ).grid(row=row_idx, column=2, sticky="w", padx=10)
        row_idx += 2

        # Notes
        tk.Label(scrollable_frame, text="Notes:", font=("Arial", 10, "bold")
                 ).grid(row=row_idx, column=0, sticky="w", padx=10)
        row_idx += 1
        notes_list = [
            "1. The population counts are derived from U.S. Census data and reflect the selected criteria.",
            "2. If no specific counties were selected, the data represent statewide aggregates.",
            "3. Age group categorization depends on the selected predefined group or custom age ranges."
        ]
        for note in notes_list:
            tk.Label(scrollable_frame, text=note, font=("Arial", 9)
                     ).grid(row=row_idx, column=0, columnspan=3, sticky="w", padx=30)
            row_idx += 1

        row_idx += 2  # spacing

    top.update_idletasks()
