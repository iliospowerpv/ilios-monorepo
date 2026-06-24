"""Tests for the read-only batch inventory-reconciliation summaries endpoint.

The endpoint (``GET /api/telemetry/v2/inventory-reconciliation/summaries``) is the
list/card counterpart to the per-site reconciliation endpoint. It must:

* require authentication;
* reuse the SAME ``build_inventory_reconciliation_summary`` builder (no new logic);
* return ONE response covering many sites (so lists make a single request);
* tolerate empty / malformed / unknown ids (omit, never fail the batch);
* never fabricate a "matched" headline for an unavailable site.
"""

from app.schema.inventory_reconciliation import InventoryReconciliationStatus

ENDPOINT = "/api/telemetry/v2/inventory-reconciliation/summaries"


class TestInventoryReconciliationSummariesEndpoint:
    def test_endpoint_requires_authentication(self, client):
        response = client.get(f"{ENDPOINT}?site_ids=1")
        assert response.status_code == 401

    def test_empty_site_ids_returns_empty_summaries(self, client, system_user_auth_header):
        response = client.get(ENDPOINT, headers=system_user_auth_header)
        assert response.status_code == 200
        assert response.json() == {"summaries": []}

    def test_malformed_site_ids_are_ignored(self, client, system_user_auth_header):
        response = client.get(f"{ENDPOINT}?site_ids=abc,,-3,0", headers=system_user_auth_header)
        assert response.status_code == 200
        assert response.json() == {"summaries": []}

    def test_unknown_site_id_is_omitted(self, client, system_user_auth_header):
        response = client.get(f"{ENDPOINT}?site_ids=99999999", headers=system_user_auth_header)
        assert response.status_code == 200
        assert response.json() == {"summaries": []}

    def test_returns_summary_for_a_real_site(self, client, site, system_user_auth_header):
        response = client.get(f"{ENDPOINT}?site_ids={site.id}", headers=system_user_auth_header)
        assert response.status_code == 200
        data = response.json()
        assert len(data["summaries"]) == 1
        item = data["summaries"][0]
        assert item["site_id"] == site.id

        summary = item["summary"]
        # Shape must match InventoryReconciliationSummary (chip relies on these).
        for key in (
            "status",
            "status_label",
            "status_explanation",
            "has_blocking_mismatch",
            "weather_dependency_unsatisfied",
            "open_actionable_mismatch_count",
            "informational_mismatch_count",
        ):
            assert key in summary
        assert summary["status"] in {s.value for s in InventoryReconciliationStatus}

    def test_batch_matches_per_site_endpoint(self, client, site, system_user_auth_header):
        """No new logic: the batch summary equals the per-site response's headline."""
        per_site = client.get(
            f"/api/telemetry/v2/sites/{site.id}/inventory-reconciliation",
            headers=system_user_auth_header,
        )
        assert per_site.status_code == 200
        per_site_body = per_site.json()

        batch = client.get(f"{ENDPOINT}?site_ids={site.id}", headers=system_user_auth_header)
        assert batch.status_code == 200
        summary = batch.json()["summaries"][0]["summary"]

        assert summary["status"] == per_site_body["status"]
        assert summary["status_label"] == per_site_body["status_label"]
        assert summary["status_explanation"] == per_site_body["status_explanation"]
        assert summary["has_blocking_mismatch"] == per_site_body["has_blocking_mismatch"]
        assert summary["weather_dependency_unsatisfied"] == per_site_body["weather_dependency_unsatisfied"]

    def test_duplicate_ids_are_deduped_in_single_response(self, client, site, system_user_auth_header):
        """One request covering repeated ids yields exactly one item (no fan-out)."""
        response = client.get(
            f"{ENDPOINT}?site_ids={site.id},{site.id},{site.id}",
            headers=system_user_auth_header,
        )
        assert response.status_code == 200
        summaries = response.json()["summaries"]
        assert len(summaries) == 1
        assert summaries[0]["site_id"] == site.id

    def test_too_many_ids_is_rejected(self, client, system_user_auth_header):
        too_many = ",".join(str(i) for i in range(1, 202))
        response = client.get(f"{ENDPOINT}?site_ids={too_many}", headers=system_user_auth_header)
        assert response.status_code == 400
