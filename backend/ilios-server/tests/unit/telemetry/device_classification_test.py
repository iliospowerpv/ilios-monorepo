"""Tests for the shared device telemetry classification predicate.

Contract guarded here:

* The original ``{inverter, module, weather_station}`` set stays mappable AND
  expected-driving (zero regression to the existing flow).
* Eligibility EXPANDS: meters, gateways/DAS loggers, power loggers, and
  weather-source sensors become mappable for inspection — but ``can_drive_expected``
  stays frozen to the original three so expected/O&M math is never auto-widened.
* Capability metadata and ``device_role`` refine intent; explicit operator columns
  override the derived verdict; weather *semantics* are never guessed here.
"""
import types

import pytest

from app.models.device import DeviceCategories, DeviceTypes
from app.services.telemetry.device_classification import (
    EXPECTED_DRIVING_CATEGORIES,
    TELEMETRY_ELIGIBLE_CATEGORIES,
    DeviceRole,
    classify_device,
    drives_expected,
    is_mappable,
    is_telemetry_capable,
)


def _device(category=None, **kwargs):
    """Lightweight device-like stub (the classifier only reads attributes)."""
    return types.SimpleNamespace(category=category, **kwargs)


class TestExpectedDrivingStability:
    """The original three categories must stay fully eligible AND drive expected."""

    def test_backward_compatible_constant_unchanged(self):
        assert TELEMETRY_ELIGIBLE_CATEGORIES == [
            DeviceCategories.inverter,
            DeviceCategories.module,
            DeviceCategories.weather_station,
        ]
        assert tuple(TELEMETRY_ELIGIBLE_CATEGORIES) == EXPECTED_DRIVING_CATEGORIES

    @pytest.mark.parametrize(
        "category",
        [DeviceCategories.inverter, DeviceCategories.module, DeviceCategories.weather_station],
    )
    def test_original_categories_are_mappable_and_drive_expected(self, category):
        device = _device(category=category)
        classification = classify_device(device)
        assert classification.mappable is True
        assert classification.telemetry_capable is True
        assert classification.can_drive_expected is True
        assert is_mappable(device) is True
        assert drives_expected(device) is True
        assert classification.eligibility_reason is not None
        assert classification.ineligibility_reason is None


class TestEligibilityExpansion:
    """Meters / gateways / loggers / weather sensors become mappable, but never
    auto-drive expected."""

    def test_meter_is_mappable_but_not_expected_driving(self):
        device = _device(category=DeviceCategories.meter)
        classification = classify_device(device)
        assert classification.mappable is True
        assert classification.production_meter_capable is True
        assert classification.can_drive_expected is False
        assert drives_expected(device) is False
        assert classification.device_role == DeviceRole.meter.value
        assert "does not drive expected" in classification.eligibility_reason

    @pytest.mark.parametrize(
        "category", [DeviceCategories.network_gateway, DeviceCategories.mbod_gateway]
    )
    def test_gateways_are_mappable_but_not_expected_driving(self, category):
        device = _device(category=category)
        classification = classify_device(device)
        assert classification.mappable is True
        assert classification.gateway_capable is True
        assert classification.can_drive_expected is False
        assert classification.device_role == DeviceRole.gateway.value

    @pytest.mark.parametrize(
        "category",
        [
            DeviceCategories.battery,
            DeviceCategories.camera,
            DeviceCategories.combiner_box,
            DeviceCategories.transformer,
            DeviceCategories.rack_mount,
            DeviceCategories.network_connection,
            DeviceCategories.modem,
        ],
    )
    def test_non_eligible_categories_stay_unmappable(self, category):
        device = _device(category=category)
        classification = classify_device(device)
        assert classification.mappable is False
        assert classification.can_drive_expected is False
        assert is_mappable(device) is False
        assert classification.mapped_status == "ineligible"
        assert classification.ineligibility_reason is not None
        assert classification.eligibility_reason is None

    def test_none_category_not_mappable(self):
        device = _device(category=None)
        classification = classify_device(device)
        assert classification.mappable is False
        assert classification.category is None
        assert classification.ineligibility_reason == "Device has no category."


class TestWeatherSourceClassification:
    def test_weather_station_is_weather_source_capable(self):
        classification = classify_device(_device(category=DeviceCategories.weather_station))
        assert classification.weather_source_capable is True
        assert classification.device_role == DeviceRole.weather_station.value

    def test_irradiance_sensor_role_from_type(self):
        device = _device(category=DeviceCategories.weather_station, type=DeviceTypes.irradiance)
        classification = classify_device(device)
        assert classification.device_role == DeviceRole.irradiance_sensor.value
        assert classification.weather_source_capable is True

    def test_temperature_sensor_role_from_type(self):
        device = _device(category=DeviceCategories.weather_station, type=DeviceTypes.temperature)
        classification = classify_device(device)
        assert classification.device_role == DeviceRole.temperature_sensor.value
        assert classification.weather_source_capable is True

    def test_inverter_is_not_weather_source(self):
        assert classify_device(_device(category=DeviceCategories.inverter)).weather_source_capable is False


class TestOperatorOverrides:
    def test_device_role_promotes_otherwise_ineligible_category(self):
        # An operator tags a network_connection device as a power logger.
        device = _device(
            category=DeviceCategories.network_connection,
            device_role=DeviceRole.power_logger.value,
        )
        classification = classify_device(device)
        assert classification.mappable is True
        assert classification.production_meter_capable is True
        assert classification.can_drive_expected is False

    def test_explicit_capability_column_forces_mappable(self):
        device = _device(category=DeviceCategories.battery, weather_source_capable=True)
        classification = classify_device(device)
        assert classification.weather_source_capable is True
        assert classification.mappable is True
        # ...but a battery still never drives expected.
        assert classification.can_drive_expected is False

    def test_virtual_site_performance_device(self):
        device = _device(category=None, device_role=DeviceRole.site_performance_virtual.value)
        classification = classify_device(device)
        assert classification.virtual_device is True
        assert classification.mappable is True
        assert classification.telemetry_capable is False  # virtual = aggregation target
        assert classification.can_drive_expected is False

    def test_role_override_never_widens_expected(self):
        # Even mislabeling a meter with an expected-driving role must NOT let it
        # drive expected — category stays canonical for expected math.
        device = _device(category=DeviceCategories.meter, device_role=DeviceRole.inverter.value)
        assert classify_device(device).can_drive_expected is False

    def test_explicit_reason_overrides_derived(self):
        device = _device(
            category=DeviceCategories.meter, eligibility_reason="Revenue meter for billing."
        )
        assert classify_device(device).eligibility_reason == "Revenue meter for billing."


class TestMappedStatusAndHelpers:
    def test_mapped_status_reflects_mapping(self):
        unmapped = classify_device(_device(category=DeviceCategories.inverter))
        assert unmapped.mapped_status == "unmapped_eligible"
        mapped = classify_device(
            _device(category=DeviceCategories.inverter, telemetry_mapping=object())
        )
        assert mapped.mapped_status == "mapped"

    def test_is_telemetry_capable_is_descriptive_and_broad(self):
        # Descriptive flag is broad (meter emits telemetry) even though it does not
        # drive expected — proving the two concepts are decoupled.
        assert is_telemetry_capable(_device(category=DeviceCategories.meter)) is True
        assert drives_expected(_device(category=DeviceCategories.meter)) is False

    def test_classifier_tolerates_missing_columns(self):
        classification = classify_device(_device(category=DeviceCategories.inverter))
        assert classification.source_provider is None
        assert classification.external_device_type is None
