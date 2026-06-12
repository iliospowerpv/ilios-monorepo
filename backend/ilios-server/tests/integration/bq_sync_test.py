from unittest.mock import ANY

import pytest

from app.settings import settings
from tests.unit import samples


class TestBQSyncProcess:
    """Validates the flow when some platform data should be synced into BigQuery for further calculation.

    There are two scenarios when we still pass data to BQ (device/site profile edits):
    1. Module/Inverter devices technical details has been updated.
    2. Asset Overview/Key Dates cards of the site details has been updated.

    For the case 1, updates go to the device characteristics table. Valuable fields are described in the
    BQDeviceCharacteristicsUpdateSchema/BQDeviceCharacteristicsCreateSchema models.
    For the case 2, updates go to the site characteristics table. Valuable fields are described in the
    BQSiteCharacteristicsUpdateSchema/BQSiteCharacteristicsCreateSchema models.

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
        "section_name,section_payload,is_update,upsert_template",
        (
            # insert cases
            (
                "asset_overview",
                samples.SITE_ASSET_OVERVIEW_CARD_BQ_REQUIRED_FIELDS_PAYLOAD,
                False,
                samples.BQ_INSERT_SITE_ASSET_OVERVIEW_CARD_DETAILS_STATEMENT_TEMPLATE,
            ),
            (
                "key_dates",
                samples.SITE_KEY_DATES_CARD_BQ_REQUIRED_FIELDS_PAYLOAD,
                False,
                samples.BQ_INSERT_SITE_KEY_DATES_CARD_DETAILS_STATEMENT_TEMPLATE,
            ),
            # update cases
            (
                "asset_overview",
                samples.SITE_ASSET_OVERVIEW_CARD_BQ_REQUIRED_FIELDS_PAYLOAD,
                True,
                samples.BQ_UPDATE_SITE_ASSET_OVERVIEW_CARD_DETAILS_STATEMENT_TEMPLATE,
            ),
            (
                "key_dates",
                samples.SITE_KEY_DATES_CARD_BQ_REQUIRED_FIELDS_PAYLOAD,
                True,
                samples.BQ_UPDATE_SITE_KEY_DATES_CARD_DETAILS_STATEMENT_TEMPLATE,
            ),
        ),
    )
    def test_site_cards_sync(
        self,
        client,
        site_id,
        company_member_user_auth_header,
        bq_client_mock,
        section_name,
        section_payload,
        is_update,
        upsert_template,
    ):
        template_substitution_params = {"table_name": self.SITE_TABLE_NAME}
        if is_update:
            bq_client_mock().query.side_effect = samples.conditional_bq_side_effect
            template_substitution_params = template_substitution_params | {"site_id": site_id}

        response = client.put(
            self._generate_site_details_endpoint(site_id),
            params={"section_name": section_name},
            json=section_payload,
            headers=company_member_user_auth_header,
        )

        assert response.status_code == 202
        bq_client_mock().query.assert_any_call(
            samples.fill_string_template(
                samples.BQ_SELECT_SITE_STATEMENT_TEMPLATE, site_id=site_id, table_name=self.SITE_TABLE_NAME
            ),
            job_id_prefix=ANY,
        )
        bq_client_mock().query.assert_any_call(
            samples.fill_string_template(upsert_template, **template_substitution_params), job_config=ANY
        )
