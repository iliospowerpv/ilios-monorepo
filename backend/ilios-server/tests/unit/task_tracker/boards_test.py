import pytest

import tests.unit.samples as samples
from app.crud.user import UserCRUD
from app.crud.user_project import UserProjectCRUD
from app.models.board import BoardModuleEnum


class TestBoards:

    @staticmethod
    def _generate_individual_board_endpoint(board_id_):
        """api/task-tracker/boards/BOARD_ID"""
        return f"api/task-tracker/boards/{board_id_}"

    def test_get_board_403(self, client, site_default_board, non_system_user_auth_header):
        """Test 403 error through if user doesn't have access to the site"""

        response = client.get(
            self._generate_individual_board_endpoint(site_default_board.id), headers=non_system_user_auth_header
        )

        assert response.status_code == 403

    def test_get_board_404(self, client, site_default_board, company_member_user_auth_header):
        """Test 404 error through if board doesn't exist"""

        response = client.get(
            self._generate_individual_board_endpoint(site_default_board.id + 100),
            headers=company_member_user_auth_header,
        )

        assert response.status_code == 404

    def test_get_board_success(self, client, site_id, site_default_board, company_member_user_auth_header):

        response = client.get(
            self._generate_individual_board_endpoint(site_default_board.id), headers=company_member_user_auth_header
        )

        assert response.status_code == 200
        assert response.json() == {
            "name": "Default board",
            "description": f"Default Asset board for site #{site_id}",
            "is_active": True,
            "id": site_default_board.id,
        }

    def test_update_board_403(self, client, site_default_board, non_system_user_auth_header):
        """Test 403 error through if user doesn't have access to the site"""

        response = client.put(
            self._generate_individual_board_endpoint(site_default_board.id), headers=non_system_user_auth_header
        )

        assert response.status_code == 403

    def test_update_board_404(self, client, site_default_board, company_member_user_auth_header):
        """Test 404 error through if board doesn't exist"""

        response = client.put(
            self._generate_individual_board_endpoint(site_default_board.id + 100),
            headers=company_member_user_auth_header,
        )

        assert response.status_code == 404

    @pytest.mark.parametrize(
        "board_payload,expected_board_body",
        (
            # No fields provided, active board is created by default
            ({}, {"name": None, "description": None, "is_active": True}),
            # All option fields provided
            (samples.TEST_BOARD_BODY, samples.TEST_BOARD_BODY),
        ),
    )
    def test_update_board_success(
        self,
        db_session,
        client,
        site_default_board,
        company_member_user_auth_header,
        board_payload,
        expected_board_body,
    ):
        """Test 404 error through if board doesn't exist"""

        response = client.put(
            self._generate_individual_board_endpoint(site_default_board.id),
            headers=company_member_user_auth_header,
            json=board_payload,
        )
        db_session.refresh(site_default_board)

        assert response.status_code == 200
        assert response.json()["message"] == "Board has been successfully updated"
        assert {
            "name": site_default_board.name,
            "description": site_default_board.description,
            "is_active": site_default_board.is_active,
        } == expected_board_body

    def test_delete_board_403(self, client, site_default_board, non_system_user_auth_header):
        """Test 403 error through if user doesn't have access to the site"""

        response = client.delete(
            self._generate_individual_board_endpoint(site_default_board.id), headers=non_system_user_auth_header
        )

        assert response.status_code == 403

    def test_delete_board_404(self, client, site_default_board, company_member_user_auth_header):
        """Test 404 error through if board doesn't exist"""

        response = client.delete(
            self._generate_individual_board_endpoint(site_default_board.id + 100),
            headers=company_member_user_auth_header,
        )

        assert response.status_code == 404

    def test_delete_board_success(self, db_session, client, site, site_default_board, company_member_user_auth_header):

        response = client.delete(
            self._generate_individual_board_endpoint(site_default_board.id), headers=company_member_user_auth_header
        )
        db_session.refresh(site)
        site_boards_ids = [related_entity.board.id for related_entity in site.related_boards]

        assert response.status_code == 202
        assert response.json()["message"] == "Board has been successfully deleted"
        assert site_default_board.id not in site_boards_ids

    def test_get_potential_company_task_assignees(
        self,
        client,
        non_system_user_id,
        company_member_user_auth_header,
        company_id,
        site_id,
        db_session,
        company_default_board_id,
        role_id,
    ):
        """Test that get potential company task assignees return list of company users."""
        user_crud = UserCRUD(db_session)
        user_project_crud = UserProjectCRUD(db_session)
        user_crud.update_by_id(
            non_system_user_id, {"parent_company_id": company_id, "is_registered": True, "role_id": role_id}
        )
        user_project = user_project_crud.create_item(
            {"company_id": company_id, "site_id": site_id, "user_id": non_system_user_id}
        )
        response = client.get(
            f"{self._generate_individual_board_endpoint(company_default_board_id)}/assignees",
            headers=company_member_user_auth_header,
        )
        response_json = response.json()["items"][0]

        assert response.status_code == 200
        assert response_json["id"] == non_system_user_id
        assert response_json["first_name"] == samples.NON_SYSTEM_USER_NAME
        assert response_json["last_name"] == samples.NON_SYSTEM_USER_LAST_NAME
        user_crud.update_by_id(non_system_user_id, {"parent_company_id": None, "role_id": None})
        user_project_crud.delete_by_id(user_project.id)

    def test_get_potential_site_task_assignees(
        self,
        client,
        non_system_user_id,
        company_member_user_auth_header,
        company_id,
        site_id,
        db_session,
        site_default_board_id,
        role_id,
    ):
        """Test that get potential site task assignees return list of company users."""
        user_crud = UserCRUD(db_session)
        user_project_crud = UserProjectCRUD(db_session)
        user_crud.update_by_id(
            non_system_user_id, {"parent_company_id": company_id, "is_registered": True, "role_id": role_id}
        )
        user_project = user_project_crud.create_item(
            {"company_id": company_id, "site_id": site_id, "user_id": non_system_user_id}
        )
        response = client.get(
            f"{self._generate_individual_board_endpoint(site_default_board_id)}/assignees",
            headers=company_member_user_auth_header,
        )
        response_json = response.json()["items"][0]

        assert response.status_code == 200
        assert response_json["id"] == non_system_user_id
        assert response_json["first_name"] == samples.NON_SYSTEM_USER_NAME
        assert response_json["last_name"] == samples.NON_SYSTEM_USER_LAST_NAME
        user_crud.update_by_id(non_system_user_id, {"parent_company_id": None, "role_id": None})
        user_project_crud.delete_by_id(user_project.id)

    def test_get_potential_document_task_assignees(
        self,
        client,
        non_system_user_id,
        company_member_user_auth_header,
        company_id,
        site_id,
        db_session,
        site_lease_document_default_board,
        role_id,
    ):
        """Test that get potential document task assignees return list of site users."""
        user_crud = UserCRUD(db_session)
        user_project_crud = UserProjectCRUD(db_session)
        user_crud.update_by_id(
            non_system_user_id, {"parent_company_id": company_id, "is_registered": True, "role_id": role_id}
        )
        user_project = user_project_crud.create_item(
            {"company_id": company_id, "site_id": site_id, "user_id": non_system_user_id}
        )
        response = client.get(
            f"{self._generate_individual_board_endpoint(site_lease_document_default_board.id)}/assignees",
            headers=company_member_user_auth_header,
        )
        response_json = response.json()["items"][0]

        assert response.status_code == 200
        assert response_json["id"] == non_system_user_id
        assert response_json["first_name"] == samples.NON_SYSTEM_USER_NAME
        assert response_json["last_name"] == samples.NON_SYSTEM_USER_LAST_NAME
        user_crud.update_by_id(non_system_user_id, {"parent_company_id": None, "role_id": None})
        user_project_crud.delete_by_id(user_project.id)

    def test_get_potential_task_assignees_403(
        self, client, non_system_user_auth_header, site_default_board_id, company_default_board_id
    ):
        """Test that get potential company task assignees receives 403."""
        for board_id in [site_default_board_id, company_default_board_id]:
            response = client.get(
                f"{self._generate_individual_board_endpoint(board_id)}/assignees", headers=non_system_user_auth_header
            )
            assert response.status_code == 403
            assert response.json()["message"] == "Forbidden"

    def test_get_potential_task_assignees_404(self, client, system_user_auth_header):
        """Test that get potential task assignees receives 404."""
        response = client.get(
            f"{self._generate_individual_board_endpoint(999)}/assignees", headers=system_user_auth_header
        )
        assert response.status_code == 404
        assert response.json()["message"] == "Not Found"

    @pytest.mark.parametrize(
        "scenario_number",
        (
            # unusual way to parametrize, here is just cases numbers, values described in the test case itself
            1,
            2,
            3,
        ),
    )
    def test_get_potential_document_task_assignees_validation_errors(
        self,
        client,
        company_member_user_auth_header,
        site_lease_document_default_board,
        site_task,
        site_lease_document_task,
        mocker,
        scenario_number,
    ):
        """Test task_id param is validated for the document assignees getting"""
        logger_mock = mocker.patch("app.helpers.task_tracker.handlers.document_handler.logger")
        # task_id and log message are fixture-based, and we cannot know them in the parametrize construction
        testing_cases = {
            # case 1 - queried task doesn't exist
            1: {"task_id": "18122024", "expected_log_message": "There is no task with id <18122024>"},
            # case 2 - task is related to the different board
            2: {
                "task_id": site_task.id,
                "expected_log_message": f"Invalid task_id provided, task with id <{site_task.id}> doesn't belong "
                f"to the board with id <{site_lease_document_default_board.id}>",
            },
            # case 3 - task doesn't have attached document, low probable case
            3: {
                "task_id": site_lease_document_task.id,
                "expected_log_message": f"Invalid task_id provided, task with id <{site_lease_document_task.id}> "
                "doesn't have linked DD document",
            },
        }
        task_id, expected_log_message = (
            testing_cases[scenario_number]["task_id"],
            testing_cases[scenario_number]["expected_log_message"],
        )

        response = client.get(
            f"{self._generate_individual_board_endpoint(site_lease_document_default_board.id)}/assignees"
            f"?task_id={task_id}",
            headers=company_member_user_auth_header,
        )

        assert response.status_code == 200
        assert response.json() == {"items": []}
        logger_mock.warning.assert_called_with(expected_log_message)


class TestSiteBoards:

    @staticmethod
    def _generate_list_endpoint(entity_id, entity_type="site"):
        """api/task-tracker/boards/?entity_type=ENTITY_TYPE&entity_id=ENTITY_ID"""
        return f"api/task-tracker/boards/?entity_type={entity_type}&entity_id={entity_id}"

    def test_get_site_boards_403(self, client, site, site_default_board, non_system_user_auth_header):
        """Test 403 error through if user doesn't have access to the site"""

        response = client.get(self._generate_list_endpoint(site.id), headers=non_system_user_auth_header)

        assert response.status_code == 403

    def test_get_site_boards_success(self, client, site, site_default_board, company_member_user_auth_header):
        """Test user can receive default created board"""

        response = client.get(self._generate_list_endpoint(site.id), headers=company_member_user_auth_header)

        assert response.status_code == 200
        assert len(response.json()["items"]) == 1
        assert response.json()["items"][0]["id"] == site.related_boards[0].board.id

    def test_create_site_boards_403(self, client, site, non_system_user_auth_header):
        """Test 403 error through if user doesn't have access to the site"""

        response = client.post(self._generate_list_endpoint(site.id), headers=non_system_user_auth_header)

        assert response.status_code == 403

    def test_create_site_boards_404(self, client, site, non_system_user_auth_header):
        """Test 404 error through if site doesn't exist"""

        response = client.post(self._generate_list_endpoint(site.id + 1), headers=non_system_user_auth_header)

        assert response.status_code == 404

    @pytest.mark.parametrize(
        "board_payload,expected_site_board",
        (
            # No fields provided, active board is created by default
            ({"module": BoardModuleEnum.asset}, {"name": None, "description": None, "is_active": True}),
            # All option fields provided
            (samples.TEST_BOARD_BODY_REQUEST, samples.TEST_BOARD_BODY),
        ),
    )
    def test_create_site_boards_success(
        self,
        db_session,
        client,
        site,
        company_member_user_auth_header,
        board_payload,
        expected_site_board,
    ):
        """Test board can be created with/without input data"""

        response = client.post(
            self._generate_list_endpoint(site.id), headers=company_member_user_auth_header, json=board_payload
        )

        # validate board is attached to the site
        # update state of fixture instance
        db_session.refresh(site)
        site_boards = [
            {
                "is_active": related_entity.board.is_active,
                "name": related_entity.board.name,
                "description": related_entity.board.description,
            }
            for related_entity in site.related_boards
        ]

        assert response.status_code == 201
        assert response.json()["message"] == "Board has been successfully created"
        assert expected_site_board in site_boards


class TestCompanyBoards:

    @staticmethod
    def _generate_list_endpoint(entity_id, entity_type="company"):
        """api/task-tracker/boards/?entity_type=ENTITY_TYPE&entity_id=ENTITY_ID"""
        return f"api/task-tracker/boards/?entity_type={entity_type}&entity_id={entity_id}"

    def test_get_company_boards_403(self, client, company_id, non_system_user_auth_header):
        response = client.get(self._generate_list_endpoint(company_id), headers=non_system_user_auth_header)
        assert response.status_code == 403

    def test_get_company_boards_success(self, client, company, company_default_board, company_member_user_auth_header):
        response = client.get(self._generate_list_endpoint(company.id), headers=company_member_user_auth_header)

        assert response.status_code == 200
        assert len(response.json()["items"]) == 1
        assert response.json()["items"][0]["id"] == company.related_boards[0].board.id

    def test_create_company_boards_403(self, client, company_id, non_system_user_auth_header):
        response = client.post(self._generate_list_endpoint(company_id), headers=non_system_user_auth_header)
        assert response.status_code == 403

    def test_create_company_boards_404(self, client, company_id, non_system_user_auth_header):
        response = client.post(self._generate_list_endpoint(company_id + 1), headers=non_system_user_auth_header)
        assert response.status_code == 404

    @pytest.mark.parametrize(
        "board_payload,expected_company_board",
        (
            # No fields provided, active board is created by default
            ({"module": BoardModuleEnum.asset}, {"name": None, "description": None, "is_active": True}),
            # All option fields provided
            (samples.TEST_BOARD_BODY_REQUEST, samples.TEST_BOARD_BODY),
        ),
    )
    def test_create_company_boards_success(
        self,
        db_session,
        client,
        company,
        company_member_user_auth_header,
        board_payload,
        expected_company_board,
    ):
        """Test board can be created with/without input data"""
        response = client.post(
            self._generate_list_endpoint(company.id), headers=company_member_user_auth_header, json=board_payload
        )

        # validate board is attached to the company
        # update state of fixture instance
        db_session.refresh(company)
        company_boards = [
            {
                "is_active": related_entity.board.is_active,
                "name": related_entity.board.name,
                "description": related_entity.board.description,
            }
            for related_entity in company.related_boards
        ]

        assert response.status_code == 201
        assert response.json()["message"] == "Board has been successfully created"
        assert expected_company_board in company_boards
