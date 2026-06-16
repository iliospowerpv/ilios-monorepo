from unittest.mock import ANY

import pytest

from app.settings import settings
from tests.unit import samples


class TestBQSyncProcess:
    """Validates the flow when some platform data should be synced into BigQuery for further calculation.

    There is now a single scenario where platform data is still pushed to BQ (device profile edits):
    1. Module/Inverter devices technical details has been updated. Updates go to the device
       characteristics table. Valuable fields are described in the
       BQDeviceCharacteristicsUpdateSchema/BQDeviceCharacteristicsCreateSchema models.

    Project Hub Overview Phase 1+2 note: editing the site Asset Overview / Key Dates cards no longer
    syncs to BigQuery. The baseline-driving fields those cards used to push (DC/AC/MV losses,
    permission_to_operate) are now read-only and stripped from the update payload before persistence,
    so the site-characteristics diff is empty and no BigQuery query is issued. See
    test_site_cards_no_longer_sync_to_bq below.

    DD V2 Phase 5B note: the Due Diligence (As-built PV Syst) key -> BigQuery sync was removed; those
    scenarios (former cases 3 & 4) no longer exist and reviewed DD values flow into project_facts instead.
    """

    DEVICE_TABLE_NAME = f"platform_{settings.environment_name}.{settings.bq_device_characteristics_table}"
    SITE_TABLE_NAME = f"platform_{settings.environment_name}.{settings.bq_site_characteristics_table}"

    @staticmethod
    def _generate_device_technical_details_endpoint(_site_id, _device_id):
        return f"/api/sites/{_site_id}/devices/{_device_id}/technical-details"

    @staticmethod
    def _generate_site_details_endpoint(_site_id):
        return f"/api/sites/{_site_id}/details"

    @pytest.mark.parametrize(
        "device,category,payload,is_update,upsert_template",
        (
            # insert cases
            (
                samples.TEST_INVERTER_DEVICE_BODY,
                "Inverter",
                samples.INVERTER_TECHNICAL_DETAILS_BQ_REQUIRED_FIELDS_PAYLOAD,
                False,
                samples.BQ_INSERT_INVERTER_DEVICE_DETAILS_STATEMENT_TEMPLATE,
            ),
            (
                samples.TEST_MODULE_DEVICE_BODY,
                "Module",
                samples.MODULE_TECHNICAL_DETAILS_BQ_REQUIRED_FIELDS_PAYLOAD,
                False,
                samples.BQ_INSERT_MODULE_DEVICE_DETAILS_STATEMENT_TEMPLATE,
            ),
            # update cases
            (
                samples.TEST_INVERTER_DEVICE_BODY,
                "Inverter",
                samples.INVERTER_TECHNICAL_DETAILS_BQ_REQUIRED_FIELDS_PAYLOAD,
                True,
                samples.BQ_UPDATE_INVERTER_DEVICE_DETAILS_STATEMENT_TEMPLATE,
            ),
            (
                samples.TEST_MODULE_DEVICE_BODY,
                "Module",
                samples.MODULE_TECHNICAL_DETAILS_BQ_REQUIRED_FIELDS_PAYLOAD,
                True,
                samples.BQ_UPDATE_MODULE_DEVICE_DETAILS_STATEMENT_TEMPLATE,
            ),
        ),
        indirect=["device"],
    )
    def test_device_technical_details_sync(
        self,
        client,
        site_id,
        device,
        category,
        payload,
        is_update,
        upsert_template,
        company_member_user_auth_header,
        bq_client_mock,
    ):
        template_substitution_params = {"table_name": self.DEVICE_TABLE_NAME}
        if is_update:
            bq_client_mock().query.side_effect = samples.conditional_bq_side_effect
            template_substitution_params = template_substitution_params | {"site_id": site_id, "device_id": device.id}

        response = client.put(
            self._generate_device_technical_details_endpoint(site_id, device.id),
            json={"category": category, "technical_details": payload},
            headers=company_member_user_auth_header,
        )

        assert response.status_code == 202
        bq_client_mock().query.assert_any_call(
            samples.fill_string_template(
                samples.BQ_SELECT_DEVICE_STATEMENT_TEMPLATE,
                site_id=site_id,
                device_id=device.id,
                table_name=self.DEVICE_TABLE_NAME,
            ),
            job_id_prefix=ANY,
        )
        bq_client_mock().query.assert_any_call(
            samples.fill_string_template(upsert_template, **template_substitution_params), job_config=ANY
        )

    @pytest.mark.parametrize(
        "section_name,section_payload",
        (
            ("asset_overview", samples.SITE_ASSET_OVERVIEW_CARD_BQ_REQUIRED_FIELDS_PAYLOAD),
            ("key_dates", samples.SITE_KEY_DATES_CARD_BQ_REQUIRED_FIELDS_PAYLOAD),
        ),
    )
    def test_site_cards_no_longer_sync_to_bq(
        self,
        client,
        site_id,
        company_member_user_auth_header,
        bq_client_mock,
        section_name,
        section_payload,
    ):
        """Project Hub Overview Phase 1+2 guard.

        Editing the Asset Overview / Key Dates cards must NOT sync to BigQuery anymore. Even when the
        request still carries the (now read-only) baseline-driving fields, they are stripped from the
        update payload before persistence, so the site-characteristics diff is empty and no BigQuery
        query (neither the existence SELECT nor an upsert) is ever issued.
        """
        bq_client_mock().query.side_effect = samples.conditional_bq_side_effect

        response = client.put(
            self._generate_site_details_endpoint(site_id),
            params={"section_name": section_name},
            json=section_payload,
            headers=company_member_user_auth_header,
        )

        assert response.status_code == 202
        bq_client_mock().query.assert_not_called()
