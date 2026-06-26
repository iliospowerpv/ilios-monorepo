"""Unit tests for the pure-Python solar-geometry helpers (no DB, no network)."""
import math
from datetime import datetime

from app.helpers.solar_position import (
    clear_sky_ghi,
    parse_lon_lat,
    solar_elevation_deg,
    solar_zenith_cos,
)

# A real site coordinate (110 Shawmut style, western Massachusetts).
LAT, LON = 42.60545, -72.04823


class TestSolarZenithCos:
    def test_clamped_to_unit_range(self):
        # Sweep a day; the cosine must always stay within [-1, 1].
        for hour in range(0, 24):
            cz = solar_zenith_cos(LAT, LON, datetime(2025, 6, 21, hour, 0))
            assert -1.0 <= cz <= 1.0

    def test_noon_is_higher_than_midnight(self):
        # Local solar noon at lon -72 lands near 16:48 UTC; local midnight near 04:48.
        noon = solar_zenith_cos(LAT, LON, datetime(2025, 6, 21, 16, 48))
        midnight = solar_zenith_cos(LAT, LON, datetime(2025, 6, 21, 4, 48))
        assert noon > 0.85  # sun high
        assert midnight <= 0.0  # sun below horizon

    def test_summer_noon_sun_higher_than_winter_noon(self):
        summer = solar_zenith_cos(LAT, LON, datetime(2025, 6, 21, 16, 48))
        winter = solar_zenith_cos(LAT, LON, datetime(2025, 12, 21, 16, 48))
        assert summer > winter


class TestSolarElevation:
    def test_known_cosines(self):
        assert solar_elevation_deg(1.0) == 90.0
        assert abs(solar_elevation_deg(0.0)) < 1e-9
        assert solar_elevation_deg(-1.0) == -90.0

    def test_out_of_range_is_clamped(self):
        assert solar_elevation_deg(5.0) == 90.0
        assert solar_elevation_deg(-5.0) == -90.0


class TestClearSkyGhi:
    def test_zero_or_below_horizon(self):
        assert clear_sky_ghi(0.0) == 0.0
        assert clear_sky_ghi(-0.5) == 0.0

    def test_overhead_sun_reasonable_magnitude(self):
        # Haurwitz at cosZ=1: 1098 * exp(-0.057) ~= 1037 W/m^2.
        ghi = clear_sky_ghi(1.0)
        assert 1000.0 < ghi < 1098.0
        assert math.isclose(ghi, 1098.0 * math.exp(-0.057), rel_tol=1e-9)

    def test_monotonic_increasing_with_sun_height(self):
        assert clear_sky_ghi(0.25) < clear_sky_ghi(0.5) < clear_sky_ghi(1.0)

    def test_never_negative(self):
        for cz in (0.01, 0.1, 0.3, 0.6, 0.9, 1.0):
            assert clear_sky_ghi(cz) >= 0.0


class TestParseLonLat:
    def test_bare_lat_lon_pair(self):
        assert parse_lon_lat("42.60545, -72.04823") == (42.60545, -72.04823)

    def test_pair_without_space(self):
        assert parse_lon_lat("42.60545,-72.04823") == (42.60545, -72.04823)

    def test_embedded_in_url_like_string(self):
        assert parse_lon_lat("https://maps.example/?q=42.6,-72.0&z=5") == (42.6, -72.0)

    def test_swaps_when_first_is_out_of_latitude_range(self):
        # First value -172.5 is not a valid latitude but is a valid longitude;
        # second value 42.6 is a valid latitude -> treated as (lon, lat) and swapped.
        assert parse_lon_lat("-172.5, 42.6") == (42.6, -172.5)

    def test_positive_integers(self):
        assert parse_lon_lat("40, 70") == (40.0, 70.0)

    def test_none_and_empty(self):
        assert parse_lon_lat(None) is None
        assert parse_lon_lat("") is None

    def test_non_string(self):
        assert parse_lon_lat(12345) is None  # type: ignore[arg-type]

    def test_garbage_returns_none(self):
        assert parse_lon_lat("not coordinates at all") is None

    def test_single_number_returns_none(self):
        assert parse_lon_lat("42.6") is None

    def test_both_out_of_range_returns_none(self):
        assert parse_lon_lat("999, 999") is None
