import pytest
from src.dummy_app.chart import build_chart_data


def test_build_chart_data_returns_expected_shape() -> None:
    frame = build_chart_data(4)

    assert list(frame.columns) == ["app_index", "y"]
    assert frame.shape == (4, 2)
    assert frame["y"].tolist() == [1, 2, 4, 8]


def test_build_chart_data_rejects_non_positive_values() -> None:
    with pytest.raises(ValueError, match="greater than zero"):
        build_chart_data(0)
