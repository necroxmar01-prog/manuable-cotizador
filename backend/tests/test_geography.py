
import pytest

from app.services.geography import (
    calculate_distance_km,
    determine_zone,
)


@pytest.mark.parametrize(
    ("distance", "expected_zone"),
    [
        (0, 1),
        (50, 1),
        (100, 1),
        (100.01, 2),
        (250, 2),
        (500, 2),
        (500.01, 3),
        (750, 3),
        (1000, 3),
        (1000.01, 4),
        (1500, 4),
    ],
)
def test_determine_zone(distance, expected_zone):
    assert determine_zone(distance) == expected_zone


def test_same_coordinates_return_zero_distance():
    distance = calculate_distance_km(
        19.4326,
        -99.1332,
        19.4326,
        -99.1332,
    )

    assert distance == pytest.approx(0)


def test_distance_is_symmetric():
    distance_forward = calculate_distance_km(
        19.4326,
        -99.1332,
        25.6866,
        -100.3161,
    )

    distance_backward = calculate_distance_km(
        25.6866,
        -100.3161,
        19.4326,
        -99.1332,
    )

    assert distance_forward == pytest.approx(distance_backward)


@pytest.mark.parametrize(
    ("coordinates"),
    [
        (91, 0, 0, 0),
        (0, 181, 0, 0),
        (0, 0, -91, 0),
        (0, 0, 0, -181),
        (float("nan"), 0, 0, 0),
        (float("inf"), 0, 0, 0),
    ],
)
def test_invalid_coordinates_raise_error(coordinates):
    with pytest.raises(ValueError):
        calculate_distance_km(*coordinates)


@pytest.mark.parametrize("distance", [-1, float("nan"), float("inf")])
def test_invalid_distance_raises_error(distance):
    with pytest.raises(ValueError):
        determine_zone(distance)
