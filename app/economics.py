from __future__ import annotations

# Explicit working assumptions shown in the UI. They are studio parameters,
# not a claimed market study.
SECONDS_PER_FRAME = 6.5
GROUPING_MINUTES = 70
REVIEW_MINUTES = 18
HOURLY_RON = 150
EVENTS_PER_MONTH = 6
PACKAGE_RON = 6500


def analyze(photo_count: int, process_seconds: float) -> dict:
    manual_hours = (photo_count * SECONDS_PER_FRAME) / 3600 + GROUPING_MINUTES / 60
    lumina_hours = process_seconds / 3600 + REVIEW_MINUTES / 60
    saved_hours = max(0.0, manual_hours - lumina_hours)
    labor_saved = saved_hours * HOURLY_RON
    month_hours = saved_hours * EVENTS_PER_MONTH
    # How many full culls fit in the freed time, if the shoot day is not the constraint.
    selection_capacity = month_hours / manual_hours if manual_hours else 0.0
    return {
        "manual_hours": round(manual_hours, 2),
        "lumina_hours": round(lumina_hours, 2),
        "saved_hours": round(saved_hours, 2),
        "labor_saved_ron": round(labor_saved),
        "month_hours": round(month_hours, 1),
        "month_labor_ron": round(month_hours * HOURLY_RON),
        "selection_capacity": round(selection_capacity, 1),
        "package_ron": PACKAGE_RON,
        "assumptions": [
            {
                "label": "Decision per frame, manual culling",
                "value": f"{SECONDS_PER_FRAME:.1f} seconds",
            },
            {
                "label": "Grouping people and sequencing the album",
                "value": f"{GROUPING_MINUTES} minutes",
            },
            {
                "label": "Reviewing the Lumina proposal",
                "value": f"{REVIEW_MINUTES} minutes",
            },
            {
                "label": "Post-production rate",
                "value": f"{HOURLY_RON} RON / hour",
            },
            {
                "label": "Events per month",
                "value": str(EVENTS_PER_MONTH),
            },
            {
                "label": "Average wedding package",
                "value": f"{PACKAGE_RON:,} RON",
            },
        ],
    }
