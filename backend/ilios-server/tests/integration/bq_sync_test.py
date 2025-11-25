from unittest.mock import ANY

import pytest
from google.cloud import bigquery

from app.settings import settings
from app.static.default_site_documents_enum import SiteDocumentsEnum
from app.static.due_diligence_bq_keys import DD_BQ_ESTIMATED_GENERATION_FIELD_NAME, DueDiligenceBQKeys
from tests.unit import samples
from tests.utils import get_document_by_name


class TestBQSyncProcess:
    """Validates the flow then some platform data should be synced into the Big Query for further calculation.

    There are several scenarios when we need to pass data to the BQ.
    1. Module/Inverter devices technical details has been updated.
    2. Asset Overview/Key Dates cards of the site details has been updated
    3. Module/Inverter keys of the As-build PV Syst doc has been updated
    4. Year 1 expected generation keys of the As-build PV Syst doc has been updated

    For the case 1, updates goes to the device characteristics table. Valuable fields are described in the
    BQDeviceCharacteristicsUpdateSchema/BQDeviceCharacteristicsCreateSchema models.
    For the cases 2, 3 and 4, updates goes to the site characteristics table. Valuable fields are described in the
    BQSiteCharacteristicsUpdateSchema/BQSiteCharacteristicsCreateSchema models.
    For the case 4, monthly metrics should be aggregated into the array,
    where each element represents month starting from january
    """

    DEVICE_TABLE_NAME = f"platform_{settings.environment_name}.{settings.bq_device_characteristics_table}"
    SITE_TABLE_NAME = f"platform_{settings.environment_name}.{settings.bq_site_characteristics_table}"

    @staticmethod
    def _generate_device_technical_details_endpoint(_site_id, _device_id):
        return f"/api/sites/{_site_id}/devices/{_device_id}/technical-details"

    @staticmethod
    def _generate_site_details_endpoint(_site_id):
        return f"/api/sites/{_site_id}/details"

    @staticmethod
    def _generate_key_endpoint(_site_id_, _document_id):
        return f"/api/due-diligence/{_site_id_}/documents/{_document_id}/keys"

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

    @pytest.mark.parametrize(
        "key_name,is_update,upsert_template",
        (
            # insert cases
            (DueDiligenceBQKeys.module_wattage, False, samples.BQ_INSERT_DD_KEY_DETAILS_STATEMENT_TEMPLATE),
            (DueDiligenceBQKeys.module_quantity, False, samples.BQ_INSERT_DD_KEY_DETAILS_STATEMENT_TEMPLATE),
            (DueDiligenceBQKeys.inverter_wattage, False, samples.BQ_INSERT_DD_KEY_DETAILS_STATEMENT_TEMPLATE),
            (DueDiligenceBQKeys.inverter_quantity, False, samples.BQ_INSERT_DD_KEY_DETAILS_STATEMENT_TEMPLATE),
            # update cases
            (DueDiligenceBQKeys.module_wattage, True, samples.BQ_UPDATE_DD_KEY_DETAILS_STATEMENT_TEMPLATE),
            (DueDiligenceBQKeys.module_quantity, True, samples.BQ_UPDATE_DD_KEY_DETAILS_STATEMENT_TEMPLATE),
            (DueDiligenceBQKeys.inverter_wattage, True, samples.BQ_UPDATE_DD_KEY_DETAILS_STATEMENT_TEMPLATE),
            (DueDiligenceBQKeys.inverter_quantity, True, samples.BQ_UPDATE_DD_KEY_DETAILS_STATEMENT_TEMPLATE),
        ),
    )
    def test_dd_key_sync(
        self,
        client,
        company_member_user_auth_header,
        site,
        all_site_documents,
        key_name,
        is_update,
        upsert_template,
        mocker,
        bq_client_mock,
    ):
        # build using keys enum
        expected_insert_statement_key_name = DueDiligenceBQKeys(key_name).name
        template_substitution_params = {
            "table_name": self.SITE_TABLE_NAME,
            "key_name": expected_insert_statement_key_name,
        }
        if is_update:
            bq_client_mock().query.side_effect = samples.conditional_bq_side_effect
            template_substitution_params = template_substitution_params | {"site_id": site.id}
        # to bypass check of the keys by document, mock tested key to the config
        mocker.patch(
            "app.routers.due_diligence.documents.AIParsingHandler.get_keys_by_document_type",
            return_value=[key_name.value],
        )
        as_build_pv_syst_document = get_document_by_name(
            site.documents, SiteDocumentsEnum.as_built_pv_syst_with_full_data_package
        )
        payload = {"name": key_name.value, "value": "42 Units"}

        response = client.put(
            self._generate_key_endpoint(site.id, as_build_pv_syst_document.id),
            headers=company_member_user_auth_header,
            json=payload,
        )

        assert response.status_code == 202
        bq_client_mock().query.assert_any_call(
            samples.fill_string_template(
                samples.BQ_SELECT_SITE_STATEMENT_TEMPLATE, site_id=site.id, table_name=self.SITE_TABLE_NAME
            ),
            job_id_prefix=ANY,
        )
        bq_client_mock().query.assert_any_call(
            samples.fill_string_template(upsert_template, **template_substitution_params), job_config=ANY
        )

    @pytest.mark.parametrize(
        "key_name,key_value,is_update,upsert_template,upsert_value",
        (
            # insert cases
            # first, ensure kw are synced as is, without any transformation
            (
                DueDiligenceBQKeys.jan,
                "1kwh",
                False,
                samples.BQ_INSERT_DD_KEY_DETAILS_STATEMENT_TEMPLATE,
                samples.generate_estimated_generation_payload(0, 1.0),
            ),
            (
                DueDiligenceBQKeys.feb,
                "2 kwh",
                False,
                samples.BQ_INSERT_DD_KEY_DETAILS_STATEMENT_TEMPLATE,
                samples.generate_estimated_generation_payload(1, 2.0),
            ),
            (
                DueDiligenceBQKeys.mar,
                "3KWh",
                False,
                samples.BQ_INSERT_DD_KEY_DETAILS_STATEMENT_TEMPLATE,
                samples.generate_estimated_generation_payload(2, 3.0),
            ),
            (
                DueDiligenceBQKeys.apr,
                "4.4 KWh in april",
                False,
                samples.BQ_INSERT_DD_KEY_DETAILS_STATEMENT_TEMPLATE,
                samples.generate_estimated_generation_payload(3, 4.4),
            ),
            # then check mw are transformed to kw
            (
                DueDiligenceBQKeys.may,
                "1.1mwh",
                False,
                samples.BQ_INSERT_DD_KEY_DETAILS_STATEMENT_TEMPLATE,
                samples.generate_estimated_generation_payload(4, 1100.0),
            ),
            # then check w are transformed to kw
            (
                DueDiligenceBQKeys.jun,
                "900 wh in june",
                False,
                samples.BQ_INSERT_DD_KEY_DETAILS_STATEMENT_TEMPLATE,
                samples.generate_estimated_generation_payload(5, 0.9),
            ),
            # for rest of month, simply validate they're tracked
            (
                DueDiligenceBQKeys.jul,
                "7kwh",
                False,
                samples.BQ_INSERT_DD_KEY_DETAILS_STATEMENT_TEMPLATE,
                samples.generate_estimated_generation_payload(6, 7.0),
            ),
            (
                DueDiligenceBQKeys.aug,
                "8kwh",
                False,
                samples.BQ_INSERT_DD_KEY_DETAILS_STATEMENT_TEMPLATE,
                samples.generate_estimated_generation_payload(7, 8.0),
            ),
            (
                DueDiligenceBQKeys.sep,
                "9kwh",
                False,
                samples.BQ_INSERT_DD_KEY_DETAILS_STATEMENT_TEMPLATE,
                samples.generate_estimated_generation_payload(8, 9.0),
            ),
            (
                DueDiligenceBQKeys.oct,
                "10kwh",
                False,
                samples.BQ_INSERT_DD_KEY_DETAILS_STATEMENT_TEMPLATE,
                samples.generate_estimated_generation_payload(9, 10.0),
            ),
            (
                DueDiligenceBQKeys.nov,
                "11kwh",
                False,
                samples.BQ_INSERT_DD_KEY_DETAILS_STATEMENT_TEMPLATE,
                samples.generate_estimated_generation_payload(10, 11.0),
            ),
            (
                DueDiligenceBQKeys.dec,
                "12kwh",
                False,
                samples.BQ_INSERT_DD_KEY_DETAILS_STATEMENT_TEMPLATE,
                samples.generate_estimated_generation_payload(11, 12.0),
            ),
            # update cases - process only for one month as an example
            (
                DueDiligenceBQKeys.apr,
                "4.4 Mwh in april",
                True,
                samples.BQ_UPDATE_DD_KEY_DETAILS_STATEMENT_TEMPLATE,
                samples.generate_estimated_generation_payload(3, 4400.0),
            ),
        ),
    )
    def test_dd_yearly_metrics_key_sync_success(
        self,
        client,
        company_member_user_auth_header,
        site,
        all_site_documents,
        key_name,
        key_value,
        is_update,
        upsert_template,
        upsert_value,
        mocker,
        bq_client_mock,
    ):
        # build using keys enum
        template_substitution_params = {
            "table_name": self.SITE_TABLE_NAME,
            "key_name": DD_BQ_ESTIMATED_GENERATION_FIELD_NAME,
        }
        query_param_key_name = DD_BQ_ESTIMATED_GENERATION_FIELD_NAME
        if is_update:
            bq_client_mock().query.side_effect = samples.conditional_bq_side_effect
            template_substitution_params = template_substitution_params | {"site_id": site.id}
            query_param_key_name = f"update_{DD_BQ_ESTIMATED_GENERATION_FIELD_NAME}"
        # to bypass check of the keys by document, mock tested key to the config
        mocker.patch(
            "app.routers.due_diligence.documents.AIParsingHandler.get_keys_by_document_type",
            return_value=[key_name.value],
        )
        as_build_pv_syst_document = get_document_by_name(
            site.documents, SiteDocumentsEnum.as_built_pv_syst_with_full_data_package
        )
        payload = {"name": key_name.value, "value": key_value}

        response = client.put(
            self._generate_key_endpoint(site.id, as_build_pv_syst_document.id),
            headers=company_member_user_auth_header,
            json=payload,
        )
        # Extract the job_config argument to validate data normalization
        query_call_args = bq_client_mock().query.call_args
        _, kwargs = query_call_args
        actual_job_config = kwargs["job_config"]
        upsert_query_parameter_value = bigquery.ArrayQueryParameter(query_param_key_name, "FLOAT64", upsert_value)

        assert response.status_code == 202
        bq_client_mock().query.assert_any_call(
            samples.fill_string_template(
                samples.BQ_SELECT_SITE_STATEMENT_TEMPLATE, site_id=site.id, table_name=self.SITE_TABLE_NAME
            ),
            job_id_prefix=ANY,
        )
        bq_client_mock().query.assert_any_call(
            samples.fill_string_template(upsert_template, **template_substitution_params), job_config=ANY
        )
        assert upsert_query_parameter_value in actual_job_config.query_parameters

    def test_dd_yearly_metrics_key_sync_error(
        self,
        client,
        company_member_user_auth_header,
        site,
        all_site_documents,
        mocker,
        bq_client_mock,
    ):
        """Validate if we cannot parse valid numbers and transform them into kwh it's substituted with 0"""
        logger_mock = mocker.patch("app.helpers.due_diligence.document_key_sync_helper.logger")
        key_name = DueDiligenceBQKeys.apr
        key_value = "Not valid measurement"

        mocker.patch(
            "app.routers.due_diligence.documents.AIParsingHandler.get_keys_by_document_type",
            return_value=[key_name.value],
        )
        as_build_pv_syst_document = get_document_by_name(
            site.documents, SiteDocumentsEnum.as_built_pv_syst_with_full_data_package
        )
        payload = {"name": key_name.value, "value": key_value}

        response = client.put(
            self._generate_key_endpoint(site.id, as_build_pv_syst_document.id),
            headers=company_member_user_auth_header,
            json=payload,
        )

        # Extract the job_config argument to validate data normalization
        query_call_args = bq_client_mock().query.call_args
        _, kwargs = query_call_args
        actual_job_config = kwargs["job_config"]
        upsert_query_parameter_value = bigquery.ArrayQueryParameter(
            DD_BQ_ESTIMATED_GENERATION_FIELD_NAME, "FLOAT64", samples.ESTIMATED_GENERATION_PAYLOAD
        )

        assert response.status_code == 202
        logger_mock.warning.assert_any_call(f"Cannot transform to KWh: input_value='{key_value}'")
        bq_client_mock().query.assert_called()
        assert upsert_query_parameter_value in actual_job_config.query_parameters
