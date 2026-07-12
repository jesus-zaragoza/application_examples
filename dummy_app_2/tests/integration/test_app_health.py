import os
import time

import pytest
import requests


@pytest.mark.integration
def test_deployed_app_responds_with_expected_marker() -> None:
    app_url = os.getenv("APP_URL")
    expected_text = os.getenv("EXPECT_TEXT", "Dummy App Ready")

    if not app_url:
        pytest.skip("APP_URL is not configured for integration testing")

    last_status = None
    last_error = None

    for _ in range(12):
        try:
            response = requests.get(app_url, timeout=20)
            last_status = response.status_code
            if response.status_code == 200 and expected_text in response.text:
                return
        except requests.RequestException as exc:  # pragma: no cover - exercised only in CI.
            last_error = str(exc)

        time.sleep(10)

    pytest.fail(
        f"App health check failed for {app_url}. last_status={last_status}, last_error={last_error}"
    )
