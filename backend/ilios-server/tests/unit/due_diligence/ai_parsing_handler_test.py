from app.crud.internal_configuration import InternalConfigurationCRUD
from app.helpers.configs.ai_parsing_helper import AIParsingHandler
from app.models.internal_configuration import InternalConfigurationNameEnum


class TestAIParsingHandler:
    """Validate AI Parsing Handler works with/without the config"""

    def test_config_reading_no_file(self, unset_ai_parsing_config, mocker, db_session):
        logger_mock = mocker.patch("app.helpers.configs.base_config_helper.logger")
        ai_parsing_handler = AIParsingHandler(db_session)
        ai_parsing_handler.read()

        logger_mock.warning.assert_called_with(
            f"There is no config stored at path {ai_parsing_handler._gen_file_path()}"
        )

    def test_get_parsable_documents_list_ok(self, set_test_ai_parsing_config, db_session):
        ai_parsing_handler = AIParsingHandler(db_session)
        parsable_documents_list = ai_parsing_handler.get_parsable_documents_list()

        assert parsable_documents_list == ["Site Lease"]

    def test_get_parsable_documents_list_no_config_file(self, unset_ai_parsing_config, db_session):
        ai_parsing_handler = AIParsingHandler(db_session)
        parsable_documents_list = ai_parsing_handler.get_parsable_documents_list()

        assert parsable_documents_list == []

    def test_get_keys_by_document_type_ok(self, set_test_ai_parsing_config, db_session):
        ai_parsing_handler = AIParsingHandler(db_session)
        site_lease_document_keys = ai_parsing_handler.get_keys_by_document_type("Site Lease")

        assert site_lease_document_keys == [
            "Lessor (Landlord) Entity Name",
            "Lessee (Tenant) Entity Name",
            "Effective Date",
        ]

    def test_get_keys_by_document_type_unexpected_document_type(self, set_test_ai_parsing_config, db_session):
        ai_parsing_handler = AIParsingHandler(db_session)
        document_keys = ai_parsing_handler.get_keys_by_document_type("wrong")

        assert document_keys == []

    def test_get_keys_by_document_type_no_config_file(self, unset_ai_parsing_config, db_session):
        ai_parsing_handler = AIParsingHandler(db_session)
        site_lease_document_keys = ai_parsing_handler.get_keys_by_document_type("Site Lease")

        assert site_lease_document_keys == []

    def test_write_config_no_file(self, unset_ai_parsing_config, db_session):
        payload = {"something": "test"}
        ai_parsing_handler = AIParsingHandler(db_session)

        # capture result to ensure file doesn't exist
        read_result_no_file_exist = ai_parsing_handler.read()

        # set the file
        ai_parsing_handler.store(payload)

        # check file was created and we can read the content
        read_result_file_updated = ai_parsing_handler.read()

        assert read_result_no_file_exist is None
        assert read_result_file_updated == payload

        # remove test config from DB to ensure other tests are not affected
        internal_config_crud = InternalConfigurationCRUD(db_session)
        prev_db_config = internal_config_crud.get_by_name(InternalConfigurationNameEnum.ai_parsing)

        if prev_db_config:
            internal_config_crud.delete_by_id(prev_db_config.id)
