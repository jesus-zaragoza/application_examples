"""Chart-building utilities kept separate from Streamlit for easier unit testing."""

from __future__ import annotations

import pandas as pd


def build_chart_data(apps: int) -> pd.DataFrame:
    """Return chart data for the requested number of app bars.

    Parameters
    ----------
    apps:
        Number of rows to generate. Must be greater than zero.
    """
    if apps < 1:
        raise ValueError("apps must be greater than zero")

    return pd.DataFrame(
        {
            "app_index": list(range(apps)),
            "y": [2**value for value in range(apps)],
        }
    )
