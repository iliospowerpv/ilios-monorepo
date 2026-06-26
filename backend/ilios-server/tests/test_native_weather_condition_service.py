"""Unit tests for the native observed-weather condition service (query-free).

These pin the honesty invariants from the implementation plan: null != 0, a
measured 0 is classified by geometry/time (never "sunny"), "rain"/"rainy" is never
emitted, and POA/cell wording is gated on a governed plane.
"""
from datetime import datetime

import pytest

from app.services.telemetry.native_weather_condition_service import (
    IRR_MODERATE,
    IRR_STRONG,
    derive_site_condition,
)

LAT, LON = 42.60545, -72.04823
COORDS = (LAT, LON)
# Local solar noon / midnight at lon -72 (see solar_position tests).
NOON_UTC = datetime(2025, 6, 21, 16, 48)
MIDNIGHT_UTC = datetime(2025, 6, 21, 4, 48)


class TestAvailabilityGate:
    def test_none_irradiance_is_unavailable_not_zero(self):
        cond = derive_site_condition(
            latest_irradiance_wm2=None,
            latest_irradiance_at_utc=NOON_UTC,
            freshness_state="fresh",
            coordinates=COORDS,
        )
        assert cond.state == "unavailable"
        assert cond.confidence == "unavailable"
        # null must never be coerced to a 0 reading.
        assert cond.observed_irradiance_wm2 is None

    def test_no_data_freshness_is_unavailable(self):
        cond = derive_site_condition(
            latest_irradiance_wm2=900.0,
            latest_irradiance_at_utc=NOON_UTC,
            freshness_state="no_data",
            coordinates=COORDS,
        )
        assert cond.state == "unavailable"
        assert cond.data_quality == "no_data"

    def test_tier_recorded_even_when_unavailable(self):
        assert (
            derive_site_condition(
                latest_irradiance_wm2=None,
                latest_irradiance_at_utc=None,
                freshness_state="no_data",
                coordinates=COORDS,
            ).tier
            == "A"
        )
        assert (
            derive_site_condition(
                latest_irradiance_wm2=None,
                latest_irradiance_at_utc=None,
                freshness_state="no_data",
                coordinates=None,
            ).tier
            == "B"
        )


class TestTierAClassification:
    def test_sunny_when_clear(self):
        cond = derive_site_condition(
            latest_irradiance_wm2=900.0,
            latest_irradiance_at_utc=NOON_UTC,
            freshness_state="fresh",
            coordinates=COORDS,
        )
        assert cond.state == "sunny"
        assert cond.tier == "A"
        assert cond.confidence == "observed_uncalibrated"

    def test_partly_cloudy(self):
        cond = derive_site_condition(
            latest_irradiance_wm2=480.0,
            latest_irradiance_at_utc=NOON_UTC,
            freshness_state="fresh",
            coordinates=COORDS,
        )
        assert cond.state == "partly_cloudy"

    def test_cloudy(self):
        cond = derive_site_condition(
            latest_irradiance_wm2=240.0,
            latest_irradiance_at_utc=NOON_UTC,
            freshness_state="fresh",
            coordinates=COORDS,
        )
        assert cond.state == "cloudy"

    def test_overcast_unknown_never_says_rain(self):
        cond = derive_site_condition(
            latest_irradiance_wm2=40.0,
            latest_irradiance_at_utc=NOON_UTC,
            freshness_state="fresh",
            coordinates=COORDS,
        )
        assert cond.state == "overcast_unknown"
        assert "undetermined" in cond.label.lower()
        assert "rain" not in cond.label.lower()

    def test_measured_zero_at_night_is_nighttime_not_sunny(self):
        # A genuine measured 0 must be classified by geometry, never dropped and
        # never "sunny".
        cond = derive_site_condition(
            latest_irradiance_wm2=0.0,
            latest_irradiance_at_utc=MIDNIGHT_UTC,
            freshness_state="fresh",
            coordinates=COORDS,
        )
        assert cond.state == "nighttime"
        assert cond.observed_irradiance_wm2 == 0.0

    def test_plane_governed_flips_confidence_to_calibrated(self):
        cond = derive_site_condition(
            latest_irradiance_wm2=900.0,
            latest_irradiance_at_utc=NOON_UTC,
            freshness_state="fresh",
            coordinates=COORDS,
            plane_governed=True,
        )
        assert cond.confidence == "observed_calibrated"
        assert cond.plane_governed is True


class TestTierBClassification:
    def test_strong_sunlight(self):
        cond = derive_site_condition(
            latest_irradiance_wm2=700.0,
            latest_irradiance_at_utc=datetime(2025, 6, 21, 12, 0),
            freshness_state="fresh",
            coordinates=None,
        )
        assert cond.state == "sunny"
        assert cond.tier == "B"
        assert cond.confidence == "coarse"

    def test_moderate_light(self):
        cond = derive_site_condition(
            latest_irradiance_wm2=300.0,
            latest_irradiance_at_utc=datetime(2025, 6, 21, 12, 0),
            freshness_state="fresh",
            coordinates=None,
        )
        assert cond.state == "partly_cloudy"

    def test_low_overcast_daytime(self):
        cond = derive_site_condition(
            latest_irradiance_wm2=100.0,
            latest_irradiance_at_utc=datetime(2025, 6, 21, 12, 0),
            freshness_state="fresh",
            coordinates=None,
            timezone_name="UTC",
        )
        assert cond.state == "cloudy"

    def test_dark_at_night(self):
        cond = derive_site_condition(
            latest_irradiance_wm2=0.0,
            latest_irradiance_at_utc=datetime(2025, 6, 21, 23, 0),
            freshness_state="fresh",
            coordinates=None,
            timezone_name="UTC",
        )
        assert cond.state == "nighttime"

    def test_dark_daytime_is_low_light_not_night(self):
        cond = derive_site_condition(
            latest_irradiance_wm2=0.0,
            latest_irradiance_at_utc=datetime(2025, 6, 21, 12, 0),
            freshness_state="fresh",
            coordinates=None,
            timezone_name="UTC",
        )
        assert cond.state == "low_light"
        assert "rain" not in cond.label.lower()


class TestStalenessOverlay:
    def test_stale_keeps_state_but_degrades_confidence(self):
        cond = derive_site_condition(
            latest_irradiance_wm2=900.0,
            latest_irradiance_at_utc=NOON_UTC,
            freshness_state="stale",
            coordinates=COORDS,
        )
        assert cond.state == "sunny"  # state preserved
        assert cond.confidence == "coarse"
        assert cond.data_quality == "stale"
        assert "last seen" in cond.label.lower()


class TestLightLevelAndTemperature:
    @pytest.mark.parametrize(
        "irr, expected",
        [(900.0, "strong"), (300.0, "moderate"), (100.0, "low"), (0.0, "dark")],
    )
    def test_light_level_bands(self, irr, expected):
        cond = derive_site_condition(
            latest_irradiance_wm2=irr,
            latest_irradiance_at_utc=NOON_UTC,
            freshness_state="fresh",
            coordinates=COORDS,
        )
        assert cond.light_level == expected

    def test_temperature_converted_to_celsius_and_type_none_when_ungoverned(self):
        cond = derive_site_condition(
            latest_irradiance_wm2=900.0,
            latest_irradiance_at_utc=NOON_UTC,
            freshness_state="fresh",
            coordinates=COORDS,
            latest_temperature_f=68.0,
            temperature_unit="C",
        )
        assert cond.temperature is not None
        assert cond.temperature.unit == "C"
        assert cond.temperature.value == pytest.approx(20.0)
        assert cond.temperature.type is None

    def test_temperature_type_only_when_governed(self):
        cond = derive_site_condition(
            latest_irradiance_wm2=900.0,
            latest_irradiance_at_utc=NOON_UTC,
            freshness_state="fresh",
            coordinates=COORDS,
            latest_temperature_f=77.0,
            temperature_unit="F",
            temperature_type="cell",
        )
        assert cond.temperature.unit == "F"
        assert cond.temperature.value == pytest.approx(77.0)
        assert cond.temperature.type == "cell"

    def test_no_temperature_when_not_provided(self):
        cond = derive_site_condition(
            latest_irradiance_wm2=900.0,
            latest_irradiance_at_utc=NOON_UTC,
            freshness_state="fresh",
            coordinates=COORDS,
        )
        assert cond.temperature is None


class TestHonestyInvariants:
    def test_no_label_ever_says_rain(self):
        # Walk a representative set of inputs across both tiers and assert the
        # forbidden meteorological claim never appears.
        samples = [
            dict(latest_irradiance_wm2=v, coordinates=c, timezone_name="UTC")
            for v in (0.0, 40.0, 100.0, 240.0, 300.0, 480.0, 700.0, 900.0)
            for c in (COORDS, None)
        ]
        for kwargs in samples:
            for ts in (NOON_UTC, datetime(2025, 6, 21, 12, 0), datetime(2025, 6, 21, 23, 0)):
                cond = derive_site_condition(
                    latest_irradiance_at_utc=ts, freshness_state="fresh", **kwargs
                )
                assert "rain" not in cond.label.lower()

    def test_irradiance_band_constants_are_sane(self):
        assert IRR_MODERATE < IRR_STRONG
