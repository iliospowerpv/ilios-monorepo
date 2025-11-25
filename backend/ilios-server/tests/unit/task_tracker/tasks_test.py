import copy
import logging
from datetime import date, timedelta

import pytest

import tests.unit.samples as samples
from app.crud.task import TaskCRUD
from app.crud.user import UserCRUD
from app.models.task import TaskPriorityEnum
from app.static import BoardMessages, TaskMessages


class GeneralTasksValidationSuite:
    """General class for tasks testing, independent of the task level specific"""

    @staticmethod
    def _generate_list_endpoint(board_id_):
        """api/task-tracker/boards/{BOARD_ID}/tasks"""
        return f"api/task-tracker/boards/{board_id_}/tasks"

    def _generate_individual_endpoint(self, board_id_, task_id_):
        """api/task-tracker/boards/{BOARD_ID}/tasks/TASK_ID"""
        return f"{self._generate_list_endpoint(board_id_)}/{task_id_}"

    def _generate_task_description_endpoint(self, board_id_, task_id_):
        """api/task-tracker/boards/{BOARD_ID}/tasks/TASK_ID/description"""
        return f"{self._generate_list_endpoint(board_id_)}/{task_id_}/description"

    def _generate_task_details_endpoint(self, board_id_, task_id_):
        """api/task-tracker/boards/{BOARD_ID}/tasks/TASK_ID/details"""
        return f"{self._generate_list_endpoint(board_id_)}/{task_id_}/details"

    def _generate_task_summary_of_events_endpoint(self, board_id_, task_id_):
        """api/task-tracker/boards/{BOARD_ID}/tasks/TASK_ID/summary-of-events"""
        return f"{self._generate_list_endpoint(board_id_)}/{task_id_}/summary-of-events"

    def _generate_site_visits_endpoint(self, board_id_, task_id_):
        """api/task-tracker/boards/{BOARD_ID}/tasks/TASK_ID/site-visits"""
        return f"{self._generate_list_endpoint(board_id_)}/{task_id_}/site-visits"

    @pytest.fixture(scope="function")
    def default_board(self):
        """Should be specified on each entity of the class"""

    @pytest.fixture(scope="function")
    def default_task(self):
        """Should be specified on each entity of the class"""

    def test_create_task_403(self, client, default_board, non_system_user_auth_header):
        """Test 403 error through if user doesn't have access to the site"""

        response = client.post(self._generate_list_endpoint(default_board.id), headers=non_system_user_auth_header)

        assert response.status_code == 403

    @pytest.mark.parametrize(
        "payload_extra,set_assignee",
        (
            # No additional fields, create task with only required
            (None, False),
            # Add optional fields, such as due date, description and assignee
            ({"due_date": "2029-04-28", "description": "Test task description"}, True),
        ),
    )
    def test_create_task_success(
        self,
        client,
        site,
        default_board,
        company_member_user,
        company_member_user_auth_header,
        payload_extra,
        set_assignee,
        caplog,
        db_session,
    ):
        """Test task can be created without/with optional fields"""
        company_member_user.is_registered = True
        db_session.commit()
        db_session.refresh(company_member_user)
        caplog.set_level(logging.INFO)

        payload = copy.deepcopy(samples.TEST_TASK_BODY)
        # set status ID properly to the board
        payload["status_id"] = default_board.statuses[0].id
        # set assignee if it's set in the test data input
        if set_assignee:
            payload["assignee_id"] = company_member_user.id

        if payload_extra:
            payload.update(payload_extra)

        response = client.post(
            self._generate_list_endpoint(default_board.id), headers=company_member_user_auth_header, json=payload
        )
        # parse created ticket ID to ensure it's included to the response
        created_task_id = None
        created_task_message_part = "Created task with id "
        for log in caplog.records:
            log_msg = log.message
            if created_task_message_part in log_msg:
                msg_parts = log_msg.split(created_task_message_part)
                msg_parts = msg_parts[1].split(" ")
                created_task_id = int(msg_parts[0])
        assert response.status_code == 201
        assert response.json()["message"] == "Task has been successfully created"
        assert response.json()["entity_id"] == created_task_id

    @pytest.mark.parametrize(
        "payload_change,expected_status_code,expected_error",
        samples.TASK_CREATION_PAYLOAD_FOR_CUSTOM_ERRORS_DATA,
    )
    def test_create_task_wrong_payload(
        self,
        client,
        default_board,
        company_member_user,
        company_member_user_auth_header,
        payload_change,
        expected_status_code,
        expected_error,
        db_session,
    ):
        """Test task handle input payload errors"""
        user_crud = UserCRUD(db_session)
        user_crud.update_by_id(company_member_user.id, {"is_registered": True})
        payload = copy.deepcopy(samples.TEST_TASK_BODY)
        # set status ID properly to the board
        payload["status_id"] = default_board.statuses[0].id
        # set assignee to the current user
        payload["assignee_id"] = company_member_user.id

        # patch payload with broken data
        payload.update(payload_change)

        response = client.post(
            self._generate_list_endpoint(default_board.id), headers=company_member_user_auth_header, json=payload
        )
        assert response.status_code == expected_status_code
        assert response.json()["message"] == expected_error

    def test_create_task_for_alert_not_allowed(
        self,
        client,
        default_board,
        company_member_user,
        company_member_user_auth_header,
        caplog,
        db_session,
        alerts,
    ):
        """Test task creation for Alert is not allowed if board is not SIte O&M"""
        company_member_user.is_registered = True
        db_session.commit()
        db_session.refresh(company_member_user)
        caplog.set_level(logging.INFO)

        payload = copy.deepcopy(samples.TEST_TASK_BODY)
        # set status ID properly to the board
        payload["status_id"] = default_board.statuses[0].id
        payload["alert_id"] = alerts[0].id

        response = client.post(
            self._generate_list_endpoint(default_board.id), headers=company_member_user_auth_header, json=payload
        )
        assert response.status_code == 400
        assert response.json()["message"] == BoardMessages.invalid_alert_task_board.value

    def test_create_task_missing_payload(self, client, default_board, company_member_user_auth_header):
        response = client.post(
            self._generate_list_endpoint(default_board.id), headers=company_member_user_auth_header, json={}
        )

        assert response.status_code == 422
        assert response.json()["message"] == samples.MISSING_TASK_BODY_MSG

    def test_get_tasks_list_403(self, client, default_board, non_system_user_auth_header):
        """Test 403 error through if user doesn't have access to the site"""

        response = client.get(self._generate_list_endpoint(default_board.id), headers=non_system_user_auth_header)

        assert response.status_code == 403

    def test_get_tasks_list_success(
        self, client, default_board, default_task, company_member_user_auth_header, create_non_system_user
    ):
        """Test list getting with the search to validate response object returned correctly"""

        response = client.get(
            self._generate_list_endpoint(default_board.id),
            headers=company_member_user_auth_header,
            # use this search term to ensure it corresponds to the payload from the task fixture
            params={"search": "fix"},
        )

        # build response object
        expected_item = copy.deepcopy(samples.TEST_TASK_PAYLOAD)
        user_info = {
            "id": create_non_system_user.id,
            "first_name": create_non_system_user.first_name,
            "last_name": create_non_system_user.last_name,
        }
        expected_item.update(
            {
                "id": default_task.id,
                "creator": user_info,
                "assignee": user_info,
                "status": {
                    "id": default_task.status_id,
                    "name": default_task.status.name,
                },
                "external_id": default_task.external_id,
            }
        )

        assert response.status_code == 200
        assert response.json()["items"] == [expected_item]

    def test_get_task_by_id(
        self, client, default_board, default_task, company_member_user_auth_header, create_non_system_user
    ):
        """Test get task by id"""

        response = client.get(
            self._generate_individual_endpoint(default_board.id, default_task.id),
            headers=company_member_user_auth_header,
        )

        # build response object
        expected_item = copy.deepcopy(samples.TEST_TASK_EXPECTED_LIST_PAYLOAD)
        user_info = {
            "id": create_non_system_user.id,
            "first_name": create_non_system_user.first_name,
            "last_name": create_non_system_user.last_name,
        }
        expected_item.update(
            {
                "id": default_task.id,
                "creator": user_info,
                "assignee": user_info,
                "status": {
                    "id": default_task.status_id,
                    "name": default_task.status.name,
                },
                "external_id": default_task.external_id,
                "alert_id": None,
                "completed_at": None,
            }
        )
        assert response.status_code == 200
        assert response.json() == expected_item

    def test_get_task_by_id_403(self, client, default_board, default_task, non_system_user_auth_header):
        """Test get task by id with 403 error"""
        response = client.get(
            self._generate_individual_endpoint(default_board.id, default_task.id),
            headers=non_system_user_auth_header,
        )
        assert response.status_code == 403
        assert response.json()["message"] == "Forbidden"

    def test_get_task_by_id_404(self, client, default_board, company_member_user_auth_header):
        """Test get task by id with 404 error"""
        response = client.get(
            self._generate_individual_endpoint(default_board.id, 1234),
            headers=company_member_user_auth_header,
        )
        assert response.status_code == 404
        assert response.json()["message"] == "Not Found"

    @pytest.mark.parametrize(
        "updated_description",
        (
            "Test task description",
            None,
        ),
    )
    def test_update_task_description(
        self, client, default_board, default_task, company_member_user_auth_header, updated_description
    ):
        """Test update task description success"""
        response = client.put(
            f"{self._generate_task_description_endpoint(default_board.id, default_task.id)}",
            headers=company_member_user_auth_header,
            json={"description": updated_description},
        )
        assert response.status_code == 202
        assert response.json()["message"] == TaskMessages.task_update_success.value

    def test_update_task_description_validation_error(
        self, client, default_board, default_task, company_member_user_auth_header
    ):
        """Test update task description success"""
        response = client.put(
            f"{self._generate_task_description_endpoint(default_board.id, default_task.id)}",
            headers=company_member_user_auth_header,
            json={"description": samples.TEST_TEXT_2001_SYMBOLS_LEN},
        )
        assert response.status_code == 422
        assert response.json()["message"] == samples.TASK_DESCRIPTION_TOO_LONG_ERR

    def test_update_task_description_403(self, client, default_board, default_task, non_system_user_auth_header):
        """Test update task description 403"""
        response = client.put(
            f"{self._generate_task_description_endpoint(default_board.id, default_task.id)}",
            headers=non_system_user_auth_header,
            json={"description": "Test task description"},
        )
        assert response.status_code == 403
        assert response.json()["message"] == "Forbidden"

    def test_update_task_description_404(self, client, default_board, company_member_user_auth_header):
        """Test update task description 404"""
        response = client.put(
            f"{self._generate_task_description_endpoint(default_board.id, 1234)}",
            headers=company_member_user_auth_header,
            json={"description": "Test task description"},
        )
        assert response.status_code == 404
        assert response.json()["message"] == "Not Found"

    def test_update_task_details(
        self,
        client,
        default_board,
        default_task,
        company_member_user_auth_header,
        non_system_user_id,
    ):
        """Test update task details success"""
        response = client.put(
            f"{self._generate_task_details_endpoint(default_board.id, default_task.id)}",
            headers=company_member_user_auth_header,
            json=samples.make_task_details_payload(default_board, non_system_user_id),
        )

        assert response.status_code == 202
        assert response.json()["message"] == TaskMessages.task_update_success.value

    def test_update_details_ok_w_unauthz_but_the_same_assignee(
        self,
        client,
        default_board,
        default_task,
        system_user_auth_header,
        non_system_user_id,
        mocker,
    ):
        """Test update task details success in case of the same assignee_id even when the assignee is now out of
        project.

        Such requirement introduced by https://softserve-jirasw.atlassian.net/browse/IOSP1-1027 bug fix.
        """
        assert (
            default_task.assignee_id == non_system_user_id
        )  # ensure existing task is still assigned to the target user

        # to reproduce bug in the test setup the site should have no such assignee_id (non_system_user_id) from task
        mocker.patch(
            "app.helpers.task_tracker.handlers.base_handler.TaskTrackerBaseHandler.get_board_active_users_ids",
            return_value=[10099],
        )

        response = client.put(
            f"{self._generate_task_details_endpoint(default_board.id, default_task.id)}",
            headers=system_user_auth_header,
            json=samples.make_task_details_payload(default_board, non_system_user_id),
        )
        assert response.status_code == 202  # in case assignee_id is not changed - do not validate, do not throw 400
        assert response.json()["message"] == TaskMessages.task_update_success.value

    def test_update_task_details_w_past_due_date(
        self,
        client,
        default_board,
        default_task,
        company_member_user_auth_header,
        non_system_user_id,
    ):
        """Test update task details success when date is in past and not changed.

        Such requirement introduced by https://softserve-jirasw.atlassian.net/browse/IOSP1-1131 bug fix.
        """
        task_details = {
            "name": "New task details",
            "priority": TaskPriorityEnum.low,
            "due_date": str(default_task.due_date),  # make sure date is not validated if not changed
            "assignee_id": non_system_user_id,
            "status_id": default_board.statuses[1].id,
        }
        response = client.put(
            f"{self._generate_task_details_endpoint(default_board.id, default_task.id)}",
            headers=company_member_user_auth_header,
            json=task_details,
        )

        assert response.status_code == 202
        assert response.json()["message"] == TaskMessages.task_update_success.value

    @pytest.mark.parametrize(
        "payload_change,expected_status_code,expected_error",
        samples.TASK_UPDATE_PAYLOAD_FOR_CUSTOM_ERRORS_DATA,
    )
    def test_update_task_details_error_case(
        self,
        client,
        default_board,
        default_task,
        company_member_user_auth_header,
        payload_change,
        expected_status_code,
        expected_error,
    ):
        """Test update task details error cases"""
        task_details = {
            "name": "New task details",
            "priority": TaskPriorityEnum.low,
            "due_date": str(date.today() + timedelta(days=1)),  # make sure date is always in future
            "status_id": default_board.statuses[1].id,
        }
        task_details.update(payload_change)
        response = client.put(
            f"{self._generate_task_details_endpoint(default_board.id, default_task.id)}",
            headers=company_member_user_auth_header,
            json=task_details,
        )
        assert response.status_code == expected_status_code
        assert response.json()["message"] == expected_error

    def test_update_task_details_403(self, client, default_board, default_task, non_system_user_auth_header):
        """Test update task details 403"""
        response = client.put(
            f"{self._generate_task_details_endpoint(default_board.id, default_task.id)}",
            headers=non_system_user_auth_header,
            json={"task_details": "task_details"},
        )
        assert response.status_code == 403
        assert response.json()["message"] == "Forbidden"

    def test_update_task_details_404(self, client, default_board, company_member_user_auth_header):
        """Test update task details 404"""
        response = client.put(
            f"{self._generate_task_details_endpoint(default_board.id, 1234)}",
            headers=company_member_user_auth_header,
            json={"task_details": "task_details"},
        )
        assert response.status_code == 404
        assert response.json()["message"] == "Not Found"

    @pytest.mark.parametrize(
        "payload",
        (
            "Test summary of events",
            None,
        ),
    )
    def test_update_task_summary_of_events_success(
        self, client, default_board, default_task, company_member_user_auth_header, payload
    ):
        response = client.put(
            f"{self._generate_task_summary_of_events_endpoint(default_board.id, default_task.id)}",
            headers=company_member_user_auth_header,
            json={"summary_of_events": payload},
        )
        assert response.status_code == 202
        assert response.json()["message"] == TaskMessages.task_update_success.value

    def test_update_task_summary_of_events_validation_error(
        self, client, default_board, default_task, company_member_user_auth_header
    ):
        response = client.put(
            f"{self._generate_task_summary_of_events_endpoint(default_board.id, default_task.id)}",
            headers=company_member_user_auth_header,
            json={"summary_of_events": samples.TEST_TEXT_2001_SYMBOLS_LEN},
        )
        assert response.status_code == 422
        assert response.json()["message"] == samples.TASK_SUMMARY_OF_EVENTS_TOO_LONG_ERR

    def test_update_task_summary_of_events_403(self, client, default_board, default_task, non_system_user_auth_header):
        response = client.put(
            f"{self._generate_task_summary_of_events_endpoint(default_board.id, default_task.id)}",
            headers=non_system_user_auth_header,
            json={"summary_of_events": "Test"},
        )
        assert response.status_code == 403
        assert response.json()["message"] == "Forbidden"

    def test_update_task_summary_of_events_404(self, client, default_board, company_member_user_auth_header):
        response = client.put(
            f"{self._generate_task_summary_of_events_endpoint(default_board.id, 1234)}",
            headers=company_member_user_auth_header,
            json={"summary_of_events": "Test"},
        )
        assert response.status_code == 404
        assert response.json()["message"] == "Not Found"

    @pytest.mark.parametrize(
        "request_method",
        (
            "get",
            "post",
            "put",
        ),
    )
    def test_site_visit_not_allowed(
        self, client, default_board, default_task, company_member_user_auth_header, request_method
    ):
        """Since <site visits> feature is allowed only for the O&M site level tasks,
        ensure for all other tasks all interactions are blocked"""
        response = client.request(
            request_method,
            f"{self._generate_site_visits_endpoint(default_board.id, default_task.id)}",
            headers=company_member_user_auth_header,
        )
        assert response.status_code == 400
        assert response.json()["message"] == TaskMessages.site_visit_not_applicable.value

    def test_set_completion_date(
        self,
        client,
        default_board,
        default_task,
        company_member_user_auth_header,
        non_system_user_id,
        db_session,
        board_completion_status,
    ):
        # save task completion details before status was changed
        task_completion_before_update = default_task.completed_at

        # patch payload to set closing status
        payload = samples.make_task_details_payload(default_board, non_system_user_id)
        payload["status_id"] = [status for status in default_board.statuses if status.name == board_completion_status][
            0
        ].id

        client.put(
            f"{self._generate_task_details_endpoint(default_board.id, default_task.id)}",
            headers=company_member_user_auth_header,
            json=payload,
        )

        # reload task object to the current state
        db_session.refresh(default_task)

        assert task_completion_before_update is None
        assert default_task.completed_at is not None

    def test_unset_completion_date(
        self,
        client,
        default_board,
        default_task,
        company_member_user_auth_header,
        non_system_user_id,
        db_session,
        board_completion_status,
        board_processing_status,
    ):
        # step 1 - set task completion
        payload = samples.make_task_details_payload(default_board, non_system_user_id)
        payload["status_id"] = [status for status in default_board.statuses if status.name == board_completion_status][
            0
        ].id
        client.put(
            f"{self._generate_task_details_endpoint(default_board.id, default_task.id)}",
            headers=company_member_user_auth_header,
            json=payload,
        )
        db_session.refresh(default_task)
        task_completion_set = default_task.completed_at

        # step 2 - unset task completion
        payload = samples.make_task_details_payload(default_board, non_system_user_id)
        payload["status_id"] = [status for status in default_board.statuses if status.name == board_processing_status][
            0
        ].id
        client.put(
            f"{self._generate_task_details_endpoint(default_board.id, default_task.id)}",
            headers=company_member_user_auth_header,
            json=payload,
        )
        db_session.refresh(default_task)
        task_completion_unset = default_task.completed_at

        assert task_completion_set is not None
        assert task_completion_unset is None


class TestSiteAssetTasks(GeneralTasksValidationSuite):
    @pytest.fixture(scope="function")
    def default_board(self, site_default_board):
        yield site_default_board

    @pytest.fixture(scope="function")
    def default_task(self, site_task):
        yield site_task

    @pytest.fixture(scope="function")
    def board_completion_status(self):
        yield "Closed"

    @pytest.fixture(scope="function")
    def board_processing_status(self):
        yield "New"

    def test_update_task_affected_device_error(
        self,
        client,
        default_board,
        default_task,
        company_member_user_auth_header,
    ):
        """Special param for the site level tasks - affected device"""
        task_details = {
            "name": "New task details",
            "priority": TaskPriorityEnum.low,
            "due_date": str(date.today() + timedelta(days=1)),  # make sure date is always in future
            "status_id": default_board.statuses[1].id,
        }
        task_details.update({"affected_device_id": 99999})
        response = client.put(
            f"{self._generate_task_details_endpoint(default_board.id, default_task.id)}",
            headers=company_member_user_auth_header,
            json=task_details,
        )
        assert response.status_code == 400
        assert response.json()["message"] == samples.INVALID_TASK_AFFECTED_DEVICE_MSG


class TestSiteOnMTasks(GeneralTasksValidationSuite):
    @pytest.fixture(scope="function")
    def default_board(self, site_om_default_board):
        yield site_om_default_board

    @pytest.fixture(scope="function")
    def default_task(self, site_om_task):
        yield site_om_task

    @pytest.fixture(scope="function")
    def board_completion_status(self):
        yield "Closed"

    @pytest.fixture(scope="function")
    def board_processing_status(self):
        yield "New"

    def test_create_task_for_alert_not_allowed(self):
        """Ignore task creation not allowed for O&M board"""

    def test_site_visit_not_allowed(self):
        """Ignore since it's allowed for site level O&M tasks"""

    def test_create_task_for_alert(
        self,
        client,
        default_board,
        company_member_user,
        company_member_user_auth_header,
        caplog,
        db_session,
        alerts,
    ):
        """Test task can be created without/with optional fields"""
        company_member_user.is_registered = True
        db_session.commit()
        db_session.refresh(company_member_user)
        caplog.set_level(logging.INFO)

        payload = copy.deepcopy(samples.TEST_TASK_BODY)
        # set status ID properly to the board
        payload["status_id"] = default_board.statuses[0].id
        payload["alert_id"] = alerts[0].id

        response = client.post(
            self._generate_list_endpoint(default_board.id), headers=company_member_user_auth_header, json=payload
        )
        # parse created ticket ID to ensure it's included to the response
        created_task_id = None
        created_task_message_part = "Created task with id "
        for log in caplog.records:
            log_msg = log.message
            if created_task_message_part in log_msg:
                msg_parts = log_msg.split(created_task_message_part)
                msg_parts = msg_parts[1].split(" ")
                created_task_id = int(msg_parts[0])

        assert response.status_code == 201
        assert response.json()["message"] == "Task has been successfully created"
        assert response.json()["entity_id"] == created_task_id

    def test_create_task_for_alert_duplicated(
        self,
        client,
        default_board,
        company_member_user,
        company_member_user_auth_header,
        caplog,
        db_session,
        alerts,
    ):
        """Test duplicated tasks can not be created for alerts"""
        company_member_user.is_registered = True
        db_session.commit()
        db_session.refresh(company_member_user)
        caplog.set_level(logging.INFO)

        payload = copy.deepcopy(samples.TEST_TASK_BODY)
        # set status ID properly to the board
        payload["status_id"] = default_board.statuses[0].id
        payload["alert_id"] = alerts[0].id

        response = client.post(
            self._generate_list_endpoint(default_board.id), headers=company_member_user_auth_header, json=payload
        )
        assert response.status_code == 201
        assert response.json()["message"] == "Task has been successfully created"

        second_response = client.post(
            self._generate_list_endpoint(default_board.id), headers=company_member_user_auth_header, json=payload
        )
        assert second_response.status_code == 409
        assert second_response.json()["message"] == TaskMessages.alert_task_already_exists.value

    def test_site_visit_create_success(self, client, default_board, default_task, company_member_user_auth_header):
        response = client.post(
            f"{self._generate_site_visits_endpoint(default_board.id, default_task.id)}",
            headers=company_member_user_auth_header,
        )
        assert response.status_code == 201
        assert response.json()["message"] == TaskMessages.site_visit_create_success.value

    def test_site_visit_create_duplicated(
        self, client, default_board, default_task, company_member_user_auth_header, site_visit
    ):
        response = client.post(
            f"{self._generate_site_visits_endpoint(default_board.id, default_task.id)}",
            headers=company_member_user_auth_header,
        )
        assert response.status_code == 400
        assert response.json()["message"] == TaskMessages.multiple_site_visits_error.value

    def test_get_task_with_added_site_visit(
        self, client, default_board, default_task, company_member_user_auth_header, site_visit
    ):
        response = client.get(
            f"{self._generate_individual_endpoint(default_board.id, default_task.id)}",
            headers=company_member_user_auth_header,
        )
        assert response.status_code == 200
        assert response.json()["site_visit_added"] is True

    @pytest.mark.parametrize(
        "request_method",
        (
            "get",
            "put",
        ),
    )
    def test_get_put_site_visit_404(
        self, client, default_board, default_task, company_member_user_auth_header, request_method
    ):
        """Validate site visit API returns 404 if site visit wasn't added"""
        response = client.request(
            request_method,
            f"{self._generate_site_visits_endpoint(default_board.id, default_task.id)}",
            headers=company_member_user_auth_header,
            json={},
        )
        assert response.status_code == 404
        assert response.json()["message"] == TaskMessages.site_visit_not_found.value

    def test_get_site_visit_success(
        self, client, default_board, default_task, company_member_user_auth_header, site_visit
    ):
        response = client.get(
            f"{self._generate_site_visits_endpoint(default_board.id, default_task.id)}",
            headers=company_member_user_auth_header,
        )
        assert response.status_code == 200
        assert response.json() == samples.TEST_SITE_VISIT_PAYLOAD

    def test_update_site_visit_success(
        self, client, default_board, default_task, company_member_user_auth_header, site_visit
    ):
        response = client.put(
            f"{self._generate_site_visits_endpoint(default_board.id, default_task.id)}",
            headers=company_member_user_auth_header,
            json=samples.TEST_SITE_VISIT_PAYLOAD,
        )
        assert response.status_code == 200
        assert response.json()["message"] == TaskMessages.site_visit_update_success.value

    def test_update_site_visit_validation_error(
        self, client, default_board, default_task, company_member_user_auth_header, site_visit
    ):
        response = client.put(
            f"{self._generate_site_visits_endpoint(default_board.id, default_task.id)}",
            headers=company_member_user_auth_header,
            json=samples.TEST_SITE_VISIT_PAYLOAD_INVALID,
        )
        assert response.status_code == 422
        assert response.json()["message"] == samples.SITE_VISIT_VALIDATION_ERROR

    def test_create_task_with_description(
        self,
        client,
        default_board,
        company_member_user_auth_header,
        db_session,
    ):
        """Validates https://softserve-jirasw.atlassian.net/browse/IOSP1-3986"""

        description = "Validate IOSP1-3986"
        payload = copy.deepcopy(samples.TEST_TASK_BODY)
        payload.update({"description": description, "status_id": default_board.statuses[0].id})

        response = client.post(
            self._generate_list_endpoint(default_board.id), headers=company_member_user_auth_header, json=payload
        )

        created_task_id = response.json()["entity_id"]
        created_task = TaskCRUD(db_session).get_by_id(created_task_id)

        assert response.status_code == 201
        assert response.json()["message"] == "Task has been successfully created"
        assert created_task.description == description


class TestCompanyAssetTasks(GeneralTasksValidationSuite):
    @pytest.fixture(scope="function")
    def default_board(self, company_default_board):
        yield company_default_board

    @pytest.fixture(scope="function")
    def default_task(self, company_task):
        yield company_task

    @pytest.fixture(scope="function")
    def board_completion_status(self):
        yield "Closed"

    @pytest.fixture(scope="function")
    def board_processing_status(self):
        yield "New"


class TestCompanyOnMTasks(GeneralTasksValidationSuite):
    @pytest.fixture(scope="function")
    def default_board(self, company_om_default_board):
        yield company_om_default_board

    @pytest.fixture(scope="function")
    def default_task(self, company_om_task):
        yield company_om_task

    @pytest.fixture(scope="function")
    def board_completion_status(self):
        yield "Closed"

    @pytest.fixture(scope="function")
    def board_processing_status(self):
        yield "New"


class TestDocumentTasks(GeneralTasksValidationSuite):
    @pytest.fixture(scope="function")
    def default_board(self, site_lease_document_default_board):
        yield site_lease_document_default_board

    @pytest.fixture(scope="function")
    def default_task(self, site_lease_document_task):
        yield site_lease_document_task

    @pytest.fixture(scope="function")
    def board_completion_status(self):
        yield "Completed"

    @pytest.fixture(scope="function")
    def board_processing_status(self):
        yield "To Upload"

    def test_create_task_success(self):
        """ "Ignore task creation tests for document due to temporary limitation"""

    def test_create_task_wrong_payload(self):
        """Ignore task creation tests for document due to temporary limitation"""

    def test_create_task_for_alert_not_allowed(self):
        """Ignore task creation tests for document due to temporary limitation"""

    def test_update_task_summary_of_events_success(self):
        """Ignore since the field is not applicable for the diligence tasks"""

    def test_create_document_task_not_allowed(
        self,
        client,
        site_lease_document_default_board,
        site_lease_document_task,
        company_member_user,
        company_member_user_auth_header,
        db_session,
    ):
        """Temporary limitation - we are not allowed to add more than one task on the document board"""
        user_crud = UserCRUD(db_session)
        user_crud.update_by_id(company_member_user.id, {"is_registered": True})
        payload = copy.deepcopy(samples.TEST_TASK_BODY)
        payload["status_id"] = site_lease_document_default_board.statuses[0].id
        payload["assignee_id"] = company_member_user.id

        response = client.post(
            self._generate_list_endpoint(site_lease_document_default_board.id),
            headers=company_member_user_auth_header,
            json=payload,
        )
        assert len(site_lease_document_default_board.tasks) > 0
        assert response.status_code == 400
        assert response.json()["message"] == "Task adding to the Document level boards is prohibited"

    def test_update_task_summary_of_events_prohibited(
        self, client, default_board, default_task, company_member_user_auth_header
    ):
        """For the diligence module, summary of events field management is not applicable."""
        response = client.put(
            f"{self._generate_task_summary_of_events_endpoint(default_board.id, default_task.id)}",
            headers=company_member_user_auth_header,
            json={"summary_of_events": "Test"},
        )
        assert response.status_code == 400
        assert response.json()["message"] == TaskMessages.summary_of_event_not_applicable.value
