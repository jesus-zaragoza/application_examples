import os
import sys
from pathlib import Path

# Ensure the app root (this file's directory) is importable regardless of the
# working directory the Databricks Apps runtime launches Streamlit from. This
# makes `from src.dummy_app...` resolve reliably in the container, locally, and in CI.
APP_ROOT = Path(__file__).resolve().parent
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

import streamlit as st  # noqa: E402

from src.dummy_app.chart import build_chart_data  # noqa: E402

# Streamlit page setup.
st.set_page_config(page_title="dummy-app", layout="wide")

# Deployment metadata injected from the Databricks Bundle.
app_env = os.getenv("APP_ENV", "local")
app_version = os.getenv("APP_VERSION", "local")
git_branch = os.getenv("GIT_BRANCH", "local")

st.title("Dummy App Ready")
st.caption(f"Environment: {app_env} | Version: {app_version[:7]} | Branch: {git_branch}")
st.success("CI/CD Deployment Test: Dummy App Ready")

# Simple visual payload so the app still has a meaningful interactive surface.
apps = st.slider("Number of apps", min_value=1, max_value=60, value=10)
chart_data = build_chart_data(apps)
st.bar_chart(
    chart_data.set_index("app_index"),
    height=500,
    width=min(100 + 50 * apps, 1000),
    use_container_width=False,
)

with st.expander("Deployment context"):
    st.json(
        {
            "app_env": app_env,
            "app_version": app_version,
            "git_branch": git_branch,
            "uc_catalog": os.getenv("UC_CATALOG", ""),
            "uc_schema": os.getenv("UC_SCHEMA", ""),
            "serving_endpoint_name": os.getenv("SERVING_ENDPOINT_NAME", ""),
            "vector_search_endpoint_name": os.getenv("VECTOR_SEARCH_ENDPOINT_NAME", ""),
            "ai_gateway_route": os.getenv("AI_GATEWAY_ROUTE", ""),
        }
    )
