"""Regression tests for the telemetry site readiness gate.

These guard the V2-aware fallback in ``get_site_telemetry_readiness``: a site
whose telemetry is natively ingested (V2) writes readings/rollups straight to
PostgreSQL and therefore has *no* BigQuery "last report" signal. Without the
fallback, such a live site would report ``is_data_flowing=false`` and the
Project Hub O&M "Performance Dashboard" would silently disappear even though
the charts have V2 data to render.

The fallback must:
* flip a BigQuery-empty result to ``True`` when V2 rollups exist,
* leave it ``False`` when there is neither BigQuery data nor V2 rollups (no
  false positives), and
* never override a BigQuery-true result.
"""
from datetime import datetime
from unittest.mock import MagicMock

import pytest

import app.routers.telemetry.telemetry as telemetry_router_module

from app.crud.company_das_provider import CompanyDASProviderCRUD
from app.crud.das_connection import DASConnectionCRUD
from app.crud.telemetry_mapping import TelemetryDeviceMappingCRUD, TelemetrySiteMappingCRUD
from app.crud.telemetry_native import TelemetrySiteRollupCRUD
from app.models.telemetry import DASProvidersEnum, TelemetrySiteIntervalRollup


def _readiness_endpoint(site_id):
    return f"/api/telemetry/sites/{site_id}/readiness"


@pytest.fixture(scope="function")
def mapped_telemetry_site(db_session, company_id, site_id, device_id):
    """A fully telemetry-configured site: connected + site-mapped + one mapped
    (telemetry-eligible) device.

    This is self-contained rather than reusing the shared ``das_connection`` /
    ``telemetry_site_mapping`` fixtures because DAS connection creation now
    requires the provider to be licensed to the company; we assign it here
    first so the fixture works regardless of predefined test data.
    """
    CompanyDASProviderCRUD(db_session).assign_provider(company_id, DASProvidersEnum.kmc)

    connection_crud = DASConnectionCRUD(db_session)
    connection = connection_crud.create_item(
        {
            "company_id": company_id,
            "name": "Readiness Test Connection",
            "provider": DASProvidersEnum.kmc,
            "secret_token_name": "test_token",
        }
    )

    site_mapping_crud = TelemetrySiteMappingCRUD(db_session)
    site_mapping = site_mapping_crud.create_item(
        {
            "site_id": site_id,
            "connection_id": connection.id,
            "telemetry_site_id": "123",
            "telemetry_site_name": "Readiness Test Site",
        }
    )

    device_mapping_crud = TelemetryDeviceMappingCRUD(db_session)
    device_mapping = device_mapping_crud.create_item(
        {
            "device_id": device_id,
            "telemetry_device_id": "456",
            "telemetry_device_name": "Readiness Test Device",
        }
    )

    yield

    device_mapping_crud.delete_by_id(device_mapping.id)
    site_mapping_crud.delete_by_id(site_mapping.id)
    connection_crud.delete_by_id(connection.id)
    CompanyDASProviderCRUD(db_session).remove_provider(company_id, DASProvidersEnum.kmc)


@pytest.fixture(scope="function")
def site_v2_rollups(db_session, site_id, company_id):
    """Insert (and clean up) a single V2 site rollup for the test site.

    Presence of *any* rollup is the V2-vs-BigQuery precedence switch
    (``site_has_v2_rollups`` / ``TelemetrySiteRollupCRUD.has_rollups``), so one
    row is enough to mark the site as V2-backed.
    """
    crud = TelemetrySiteRollupCRUD(db_session)
    crud.upsert_rollups(
        [
            {
                "site_id": site_id,
                "company_id": company_id,
                "bucket_start": datetime.utcnow().replace(minute=0, second=0, microsecond=0),
                "bucket_size": "1h",
                "normalized_metric": "site_power_ac_kw",
                "agg": "avg",
                "value": 42.0,
                "unit": "kW",
                "sample_count": 4,
            }
        ]
    )
    db_session.commit()

    yield

    db_session.query(TelemetrySiteIntervalRollup).filter(
        TelemetrySiteIntervalRollup.site_id == site_id
    ).delete()
    db_session.commit()


def _mock_bigquery_last_reported(monkeypatch, last_reported):
    """Patch the readiness endpoint's BigQuery client to return ``last_reported``."""
    fake_bq = MagicMock()
    fake_bq.return_value.get_device_last_reported.return_value = last_reported
    monkeypatch.setattr(telemetry_router_module, "TelemetryDeviceBigQuery", fake_bq)
    return fake_bq


class TestTelemetryReadinessV2Fallback:
    def test_v2_rollups_make_data_flowing_when_bigquery_empty(
        self,
        client,
        system_user_auth_header,
        site_id,
        mapped_telemetry_site,
        site_v2_rollups,
        monkeypatch,
    ):
        """Connected + site-mapped + device-mapped site with V2 rollups but no
        BigQuery last-report must report ``is_data_flowing=true`` so the
        Performance Dashboard stays visible for live V2 sites."""
        _mock_bigquery_last_reported(monkeypatch, [])

        response = client.get(
            _readiness_endpoint(site_id),
            headers=system_user_auth_header,
        )

        assert response.status_code == 200
        body = response.json()
        assert body["is_connected"] is True
        assert body["is_site_mapped"] is True
        assert body["is_devices_mapped"] is True
        assert body["is_data_flowing"] is True

    def test_no_bigquery_and_no_v2_rollups_is_not_flowing(
        self,
        client,
        system_user_auth_header,
        site_id,
        mapped_telemetry_site,
        monkeypatch,
    ):
        """With neither BigQuery data nor V2 rollups the gate must stay
        ``false`` — the fallback must not produce false positives."""
        _mock_bigquery_last_reported(monkeypatch, [])

        response = client.get(
            _readiness_endpoint(site_id),
            headers=system_user_auth_header,
        )

        assert response.status_code == 200
        body = response.json()
        assert body["is_connected"] is True
        assert body["is_site_mapped"] is True
        assert body["is_devices_mapped"] is True
        assert body["is_data_flowing"] is False

    def test_bigquery_true_result_is_preserved_without_v2(
        self,
        client,
        system_user_auth_header,
        site_id,
        mapped_telemetry_site,
        monkeypatch,
    ):
        """A BigQuery-true result stands on its own (no V2 rollups present); the
        V2 fallback only ever flips false -> true and never overrides a
        BigQuery-true result."""
        _mock_bigquery_last_reported(
            monkeypatch, [{"last_report_ts": "2026-06-10T12:00:00Z"}]
        )

        response = client.get(
            _readiness_endpoint(site_id),
            headers=system_user_auth_header,
        )

        assert response.status_code == 200
        assert response.json()["is_data_flowing"] is True
