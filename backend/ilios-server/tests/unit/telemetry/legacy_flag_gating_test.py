"""Unit tests for the legacy-telemetry feature-flag gating.

These tests are intentionally self-contained: they drive the gated helpers
directly with mocks (no DB fixtures, no DAS-connection seeding) so they exercise
ONLY the ``legacy_telemetry_enabled`` gating added in the Telemetry V2
legacy-removal sprint. The flag is OFF by default; when off, legacy Firestore and
BigQuery side effects must be skipped entirely and callers must surface honest
N/A (None / empty) instead of querying decommissioned infrastructure.
"""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import app.helpers.company_helper as company_helper
import app.helpers.device_helper as device_helper
import app.helpers.telemetry.telemetry_helper as telemetry_helper
from app.helpers.telemetry.legacy_flag import legacy_telemetry_enabled
from app.helpers.telemetry.v2_company_data import SiteExpectedToday, SiteTodayPower
from app.services.telemetry.expected_service import ExpectedState
from app.settings import settings


class TestLegacyTelemetryFlagPredicate:
    def test_off_by_default(self):
        """The Settings field defaults to False regardless of the environment."""
        assert type(settings).model_fields["legacy_telemetry_enabled"].default is False

    def test_reads_setting(self, monkeypatch):
        monkeypatch.setattr(settings, "legacy_telemetry_enabled", True, raising=False)
        assert legacy_telemetry_enabled() is True
        monkeypatch.setattr(settings, "legacy_telemetry_enabled", False, raising=False)
        assert legacy_telemetry_enabled() is False


def _telemetry_device():
    device = MagicMock()
    device.category = next(iter(device_helper.TELEMETRY_DEVICES_CATEGORIES))
    device.telemetry_mapping = MagicMock()
    device.id = 1
    return device


class TestGetDevicesLastReportedGating:
    def test_returns_empty_and_skips_bq_when_flag_off(self):
        with patch.object(device_helper, "legacy_telemetry_enabled", return_value=False), patch.object(
            device_helper, "TelemetryDeviceBigQuery"
        ) as bq:
            result = device_helper.get_devices_last_reported([_telemetry_device()])
        assert result == []
        bq.assert_not_called()

    def test_calls_bq_when_flag_on(self):
        bq_instance = MagicMock()
        bq_instance.get_device_last_reported.return_value = [{"device_id": 1}]
        with patch.object(device_helper, "legacy_telemetry_enabled", return_value=True), patch.object(
            device_helper, "TelemetryDeviceBigQuery", return_value=bq_instance
        ):
            result = device_helper.get_devices_last_reported([_telemetry_device()])
        bq_instance.get_device_last_reported.assert_called_once()
        assert result == [{"device_id": 1}]


class TestGetAvailabilityMetricsGating:
    def test_returns_none_and_skips_bq_when_flag_off(self):
        with patch.object(device_helper, "legacy_telemetry_enabled", return_value=False), patch.object(
            device_helper, "TelemetryDeviceBigQuery"
        ) as bq:
            result = device_helper.get_availability_metrics(_telemetry_device())
        assert result == {"mtbf": None, "mttr": None}
        bq.assert_not_called()

    def test_calls_bq_when_flag_on(self):
        bq_instance = MagicMock()
        bq_instance.get_device_availability_metrics.return_value = [{"mtbf": 48, "mttr": 24}]
        with patch.object(device_helper, "legacy_telemetry_enabled", return_value=True), patch.object(
            device_helper, "TelemetryDeviceBigQuery", return_value=bq_instance
        ), patch.object(device_helper, "get_availability_metrics_start_time", return_value=None):
            result = device_helper.get_availability_metrics(_telemetry_device())
        bq_instance.get_device_availability_metrics.assert_called_once()
        # transform_availability_metric == ceil(hours / 24): 48h -> 2d, 24h -> 1d
        assert result == {"mtbf": 2, "mttr": 1}


def _energy_site():
    return SimpleNamespace(
        id=1,
        actual_kw="sentinel",
        expected_kw="sentinel",
        cumulative_vs_expected="sentinel",
        cumulative_7_days_vs_expected="sentinel",
        cumulative_30_days_vs_expected="sentinel",
    )


class TestExtendCompanySitesEnergyGating:
    """Flag OFF (default) now fills the 5 energy attrs from V2 PostgreSQL rollups +
    baselines (honest-or-null, never a fabricated zero). Flag ON keeps the legacy
    BigQuery path and never touches V2. Each test patches the batched V2 helpers /
    the BigQuery client so no real DB or BigQuery is needed.
    """

    @staticmethod
    def _run_v2(*, today_power, baselines, expected):
        """Drive the helper on the flag-off (V2) path with mocked batched helpers.

        Returns the (single) site after the helper has populated its energy attrs,
        plus the patched BigQuery mock so callers can assert it was never used.
        """
        site = _energy_site()
        with patch.object(company_helper, "legacy_telemetry_enabled", return_value=False), patch.object(
            company_helper, "TelemetrySiteBigQuery"
        ) as bq, patch.object(
            company_helper, "get_sites_today_power", return_value=today_power
        ), patch.object(
            company_helper, "get_active_baselines", return_value=baselines
        ), patch.object(
            company_helper, "compute_sites_expected_today", return_value=expected
        ):
            company_helper.extend_company_sites_with_energy_attributes(MagicMock(), [site])
        return site, bq

    def test_flag_off_no_today_power_is_na(self):
        """No today readings -> every energy attr is honest None, no BigQuery."""
        site, bq = self._run_v2(
            today_power={1: SiteTodayPower(energy_kwh=0.0, bucket_count=0, latest_power_kw=None)},
            baselines={},
            expected={},
        )
        assert site.actual_kw is None
        assert site.expected_kw is None
        assert site.cumulative_vs_expected is None
        assert site.cumulative_7_days_vs_expected is None
        assert site.cumulative_30_days_vs_expected is None
        bq.assert_not_called()

    def test_flag_off_actual_only_when_no_baseline(self):
        """Today power but no active baseline -> actual_kw shown, expected/% are None."""
        site, bq = self._run_v2(
            today_power={1: SiteTodayPower(energy_kwh=4.0, bucket_count=5, latest_power_kw=5.0)},
            baselines={},
            expected={},
        )
        assert site.actual_kw == 5.0
        assert site.expected_kw is None
        assert site.cumulative_vs_expected is None
        assert site.cumulative_7_days_vs_expected is None
        assert site.cumulative_30_days_vs_expected is None
        bq.assert_not_called()

    def test_flag_off_real_numbers_with_baseline(self):
        """Today power + computable baseline -> real actual/expected/today-%; 7d/30d None.

        The table reads the ACTUAL-aligned fields (``expected_power_at_latest_actual_kw``
        + the ``comparable_*`` energies), NOT the union-latest ``expected_power_latest_kw``,
        so actual_kw/expected_kw and the today % always compare the same intervals.
        """
        site, bq = self._run_v2(
            today_power={1: SiteTodayPower(energy_kwh=4.0, bucket_count=5, latest_power_kw=5.0)},
            baselines={1: object()},
            expected={
                1: SiteExpectedToday(
                    state=ExpectedState.available,
                    expected_energy_kwh=8.0,
                    expected_power_latest_kw=10.0,
                    expected_power_at_latest_actual_kw=10.0,
                    comparable_actual_energy_kwh=4.0,
                    comparable_expected_energy_kwh=8.0,
                )
            },
        )
        assert site.actual_kw == 5.0
        assert site.expected_kw == 10.0
        assert site.cumulative_vs_expected == 50  # comparable 4 / 8 * 100
        assert site.cumulative_7_days_vs_expected is None
        assert site.cumulative_30_days_vs_expected is None
        bq.assert_not_called()

    def test_flag_off_genuine_zero_is_zero_not_none(self):
        """Real today coverage with 0 production -> a distinguishable 0% (not None/N/A)."""
        site, bq = self._run_v2(
            today_power={1: SiteTodayPower(energy_kwh=0.0, bucket_count=3, latest_power_kw=0.0)},
            baselines={1: object()},
            expected={
                1: SiteExpectedToday(
                    state=ExpectedState.partial,
                    expected_energy_kwh=10.0,
                    expected_power_latest_kw=8.0,
                    expected_power_at_latest_actual_kw=8.0,
                    comparable_actual_energy_kwh=0.0,
                    comparable_expected_energy_kwh=10.0,
                )
            },
        )
        assert site.actual_kw == 0.0
        assert site.expected_kw == 8.0
        assert site.cumulative_vs_expected == 0
        assert site.cumulative_7_days_vs_expected is None
        assert site.cumulative_30_days_vs_expected is None
        bq.assert_not_called()

    def test_flag_off_unaligned_latest_bucket_expected_kw_is_none(self):
        """Latest ACTUAL power bucket is not ``ok`` -> expected_kw is honest None
        (no cross-bucket borrowing from a later weather-only bucket), even though a
        union-latest ``expected_power_latest_kw`` exists. The comparable today %
        still computes from the aligned comparable buckets."""
        site, bq = self._run_v2(
            today_power={1: SiteTodayPower(energy_kwh=4.0, bucket_count=5, latest_power_kw=5.0)},
            baselines={1: object()},
            expected={
                1: SiteExpectedToday(
                    state=ExpectedState.partial,
                    expected_energy_kwh=8.0,
                    expected_power_latest_kw=10.0,  # union-latest; MUST NOT be used here
                    expected_power_at_latest_actual_kw=None,  # latest actual bucket not ok
                    comparable_actual_energy_kwh=4.0,
                    comparable_expected_energy_kwh=8.0,
                )
            },
        )
        assert site.actual_kw == 5.0
        assert site.expected_kw is None
        assert site.cumulative_vs_expected == 50  # comparable 4 / 8 * 100
        bq.assert_not_called()

    def test_flag_off_no_comparable_buckets_today_pct_is_none(self):
        """Today power exists but no bucket is both ``ok`` AND has actual power
        (e.g. power buckets lack weather) -> today % is honest None, never a
        fabricated 0%."""
        site, bq = self._run_v2(
            today_power={1: SiteTodayPower(energy_kwh=4.0, bucket_count=5, latest_power_kw=5.0)},
            baselines={1: object()},
            expected={
                1: SiteExpectedToday(
                    state=ExpectedState.missing_inputs,
                    expected_energy_kwh=None,
                    expected_power_latest_kw=None,
                    expected_power_at_latest_actual_kw=None,
                    comparable_actual_energy_kwh=None,
                    comparable_expected_energy_kwh=None,
                )
            },
        )
        assert site.actual_kw == 5.0
        assert site.expected_kw is None
        assert site.cumulative_vs_expected is None
        bq.assert_not_called()

    def test_flag_on_uses_bigquery_and_skips_v2(self):
        site = _energy_site()
        bq_instance = MagicMock()
        bq_instance.get_site_actual_expected_performance.return_value = {1: (10.0, 20.0)}
        bq_instance.get_site_cumulative_energy.return_value = {1: (1, 2, 3)}
        with patch.object(company_helper, "legacy_telemetry_enabled", return_value=True), patch.object(
            company_helper, "TelemetrySiteBigQuery", return_value=bq_instance
        ), patch.object(company_helper, "get_sites_today_power") as v2_power, patch.object(
            company_helper, "get_active_baselines"
        ) as v2_baselines, patch.object(
            company_helper, "compute_sites_expected_today"
        ) as v2_expected:
            company_helper.extend_company_sites_with_energy_attributes(MagicMock(), [site])
        assert site.actual_kw == 10.0
        assert site.expected_kw == 20.0
        assert (
            site.cumulative_vs_expected,
            site.cumulative_7_days_vs_expected,
            site.cumulative_30_days_vs_expected,
        ) == (1, 2, 3)
        # Flag ON must never reach the V2 PostgreSQL path.
        v2_power.assert_not_called()
        v2_baselines.assert_not_called()
        v2_expected.assert_not_called()


class TestFirestoreMappingGating:
    """The landmine: a Firestore failure used to DELETE the just-created DB row.
    With the flag off, Firestore must not be touched and the DB row must persist.
    """

    def test_create_site_mapping_skips_firestore_when_flag_off(self):
        site = SimpleNamespace(id=1, company_id=2)
        crud_instance = MagicMock()
        crud_instance.create_item.return_value = MagicMock(id=99, connection_id=3, telemetry_site_id="ext")
        with patch.object(telemetry_helper, "legacy_telemetry_enabled", return_value=False), patch.object(
            telemetry_helper, "TelemetrySiteMappingCRUD", return_value=crud_instance
        ), patch.object(telemetry_helper, "FirestoreClient") as fs:
            telemetry_helper.create_site_mapping_for_telemetry(site, {"connection_id": 3}, MagicMock())
        crud_instance.create_item.assert_called_once()
        fs.assert_not_called()
        crud_instance.delete_by_id.assert_not_called()

    def test_create_device_mapping_skips_firestore_when_flag_off(self):
        site = SimpleNamespace(id=1, company_id=2)
        crud_instance = MagicMock()
        crud_instance.create_item.return_value = MagicMock(id=99, device_id=7, telemetry_device_id="ext")
        with patch.object(telemetry_helper, "legacy_telemetry_enabled", return_value=False), patch.object(
            telemetry_helper, "TelemetryDeviceMappingCRUD", return_value=crud_instance
        ), patch.object(telemetry_helper, "FirestoreClient") as fs:
            telemetry_helper.create_device_mapping_for_telemetry(site, {"device_id": 7}, MagicMock())
        crud_instance.create_item.assert_called_once()
        fs.assert_not_called()
        crud_instance.delete_by_id.assert_not_called()

    def test_create_device_mapping_calls_firestore_when_flag_on(self):
        site = SimpleNamespace(id=1, company_id=2)
        crud_instance = MagicMock()
        crud_instance.create_item.return_value = MagicMock(id=99, device_id=7, telemetry_device_id="ext")
        fs_instance = MagicMock()
        with patch.object(telemetry_helper, "legacy_telemetry_enabled", return_value=True), patch.object(
            telemetry_helper, "TelemetryDeviceMappingCRUD", return_value=crud_instance
        ), patch.object(telemetry_helper, "FirestoreClient", return_value=fs_instance) as fs, patch.object(
            telemetry_helper, "FSDevice"
        ):
            telemetry_helper.create_device_mapping_for_telemetry(site, {"device_id": 7}, MagicMock())
        fs.assert_called_once()
        fs_instance.update_company_config.assert_called_once()
