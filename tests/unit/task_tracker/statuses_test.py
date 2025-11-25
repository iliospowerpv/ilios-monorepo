class TestBoardStatuses:

    @staticmethod
    def _generate_list_endpoint(board_id_):
        """api/task-tracker/boards/BOARD_ID/statuses"""
        return f"api/task-tracker/boards/{board_id_}/statuses"

    @staticmethod
    def _generate_status_name_endpoint(board_id_, board_status_id_):
        """api/task-tracker/boards/BOARD_ID/statuses/STATUS_ID/name"""
        return f"api/task-tracker/boards/{board_id_}/statuses/{board_status_id_}/name"

    @staticmethod
    def _generate_status_individual_endpoint(board_id_, board_status_id_):
        """api/task-tracker/boards/BOARD_ID/statuses/STATUS_ID"""
        return f"api/task-tracker/boards/{board_id_}/statuses/{board_status_id_}"

    def test_get_boards_statuses_404(self, client, site, site_default_board, company_member_user_auth_header, mocker):
        """Test error 404 through if there is no board with requested ID"""
        logger_mock = mocker.patch("app.helpers.authorization.project_access.logger")
        request_board_id = site_default_board.id + 1

        response = client.get(self._generate_list_endpoint(request_board_id), headers=company_member_user_auth_header)

        assert response.status_code == 404
        logger_mock.warning.assert_called_with(f"There is no board with id {request_board_id}")

    def test_get_boards_statuses_403(self, client, site_default_board, non_system_user_auth_header):
        """Test error 403 through if user doesn't have access to the site"""

        response = client.get(self._generate_list_endpoint(site_default_board.id), headers=non_system_user_auth_header)

        assert response.status_code == 403

    def test_get_boards_statuses_success(self, client, site_id, site_default_board, company_member_user_auth_header):
        """Test user can receive default created board statues"""

        response = client.get(
            self._generate_list_endpoint(site_default_board.id), headers=company_member_user_auth_header
        )

        assert response.status_code == 200
        # we're good to check that exactly 7 statuses returned, since this is default for the MVP
        assert len(response.json()["items"]) == 7

    def test_get_company_board_statuses_success(
        self, client, company_id, company_default_board, company_member_user_auth_header
    ):
        """Test user can receive default created board statues"""

        response = client.get(
            self._generate_list_endpoint(company_default_board.id), headers=company_member_user_auth_header
        )

        assert response.status_code == 200
        # we're good to check that exactly 5 statuses returned, since this is default for the MVP
        assert len(response.json()["items"]) == 7

    def test_add_board_status_success(self, client, site_default_board, company_member_user_auth_header):
        """Test board status can be created"""
        response = client.post(
            self._generate_list_endpoint(site_default_board.id),
            headers=company_member_user_auth_header,
            json={"name": "new status"},
        )

        assert response.status_code == 201
        assert response.json()["message"] == "Status has been successfully created"

    def test_add_board_status_duplication_error(
        self, client, site_default_board, company_member_user_auth_header, mocker
    ):
        """Test board status name should be unique"""
        logger_mock = mocker.patch("app.routers.task_tracker.statuses.logger")
        test_status_name = "non unique status"
        success_response = client.post(
            self._generate_list_endpoint(site_default_board.id),
            headers=company_member_user_auth_header,
            json={"name": test_status_name},
        )
        failure_response = client.post(
            self._generate_list_endpoint(site_default_board.id),
            headers=company_member_user_auth_header,
            json={"name": test_status_name},
        )

        assert success_response.status_code == 201
        assert success_response.json()["message"] == "Status has been successfully created"
        assert failure_response.status_code == 409
        assert failure_response.json()["message"] == "Status name should be unique across the board"
        logger_mock.error.assert_called_with(
            f"Status with name '{test_status_name}' already exists on the board with id {site_default_board.id}"
        )

    def test_add_board_status_403(self, client, site_default_board, non_system_user_auth_header):
        """Test error 403 through if user doesn't have access to the site"""

        response = client.get(self._generate_list_endpoint(site_default_board.id), headers=non_system_user_auth_header)

        assert response.status_code == 403

    def test_update_board_status_success(self, client, site_default_board, company_member_user_auth_header):
        response = client.put(
            self._generate_status_name_endpoint(site_default_board.id, site_default_board.get_statuses_ids()[0]),
            headers=company_member_user_auth_header,
            json={"name": "new status 2"},
        )

        assert response.status_code == 202
        assert response.json()["message"] == "Status name has been successfully updated"

    def test_update_board_status_duplication_error(self, client, site_default_board, company_member_user_auth_header):
        response = client.put(
            self._generate_status_name_endpoint(site_default_board.id, site_default_board.statuses[0].id),
            headers=company_member_user_auth_header,
            json={"name": site_default_board.statuses[1].name},
        )

        assert response.status_code == 409
        assert response.json()["message"] == "Status name should be unique across the board"

    def test_update_board_status_404(self, client, site_default_board, company_member_user_auth_header, mocker):
        logger_mock = mocker.patch("app.helpers.authorization.project_access.logger")
        response = client.put(
            self._generate_status_name_endpoint(site_default_board.id, 1234567),
            headers=company_member_user_auth_header,
            json={"name": "test"},
        )

        assert response.status_code == 404
        logger_mock.warning.assert_called_with("There is no status with id 1234567")

    def test_update_board_status_403(
        self, client, site_default_board, company_member_user_auth_header, company_member_user, mocker, db_session
    ):
        company_member_user.sites = []
        db_session.commit()
        # drop site access
        logger_mock = mocker.patch("app.helpers.authorization.project_access.logger")
        response = client.put(
            self._generate_status_name_endpoint(site_default_board.id, site_default_board.get_statuses_ids()[0]),
            headers=company_member_user_auth_header,
            json={"name": "test"},
        )

        assert response.status_code == 403
        logger_mock.warning.assert_called_with(
            f"User {company_member_user.id} tried to access site {site_default_board.related_entity.entity_id} "
            "without site access."
        )

    def test_delete_board_status_403(
        self, client, site_default_board, company_member_user_auth_header, company_member_user, mocker, db_session
    ):
        company_member_user.sites = []
        db_session.commit()
        logger_mock = mocker.patch("app.helpers.authorization.project_access.logger")
        response = client.delete(
            self._generate_status_individual_endpoint(site_default_board.id, site_default_board.get_statuses_ids()[0]),
            headers=company_member_user_auth_header,
        )

        assert response.status_code == 403
        logger_mock.warning.assert_called_with(
            f"User {company_member_user.id} tried to access site {site_default_board.related_entity.entity_id} "
            "without site access."
        )

    def test_delete_board_status_404(self, client, site_default_board, company_member_user_auth_header, mocker):
        logger_mock = mocker.patch("app.helpers.authorization.project_access.logger")
        response = client.delete(
            self._generate_status_individual_endpoint(site_default_board.id, 1234567),
            headers=company_member_user_auth_header,
        )

        assert response.status_code == 404
        logger_mock.warning.assert_called_with("There is no status with id 1234567")

    def test_delete_board_status_in_use(
        self, client, site_default_board, site_task, company_member_user_auth_header, mocker
    ):
        """Validate status cannot be deleted if it's used in the tasks"""
        logger_mock = mocker.patch("app.routers.task_tracker.statuses.logger")
        response = client.delete(
            self._generate_status_individual_endpoint(site_default_board.id, site_task.status_id),
            headers=company_member_user_auth_header,
        )

        assert response.status_code == 400
        assert response.json()["message"] == "Status is in use, please, remove it from the tasks"
        logger_mock.warning.assert_called_with(f"Cannot remove status with id {site_task.status_id}: 1 tasks attached")

    def test_delete_board_status_success(self, client, site_default_board, company_member_user_auth_header):
        response = client.delete(
            self._generate_status_individual_endpoint(site_default_board.id, site_default_board.get_statuses_ids()[0]),
            headers=company_member_user_auth_header,
        )

        assert response.status_code == 202
        assert response.json()["message"] == "Status has been successfully deleted"
