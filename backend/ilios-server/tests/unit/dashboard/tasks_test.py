import copy

from app.crud.task import TaskCRUD
from app.models.board import BoardModuleEnum
from tests.unit import samples


class TestDashboardTasks:
    @staticmethod
    def _generate_list_endpoint():
        return "/api/account/dashboard/tasks"

    def test_get_tasks_list_200(
        self,
        client,
        site_default_board,
        site_task,
        non_system_user_auth_header,
        create_non_system_user,
        site_id,
        company_id,
        company_task,
        site_lease_document_task,
        site_om_task,
        company_om_task,
    ):
        """Test get list of user tasks, validate tasks on each module"""

        response = client.get(
            self._generate_list_endpoint(),
            headers=non_system_user_auth_header,
        )

        # build response object, for the site level Asset task validate the full object
        expected_item = copy.deepcopy(samples.TEST_TASK_PAYLOAD)
        user_info = {
            "id": create_non_system_user.id,
            "first_name": create_non_system_user.first_name,
            "last_name": create_non_system_user.last_name,
        }
        expected_item.update(
            {
                "id": site_task.id,
                "creator": user_info,
                "assignee": user_info,
                "external_id": site_task.external_id,
                "status": {
                    "id": site_default_board.statuses[0].id,
                    "name": site_default_board.statuses[0].name,
                },
                "module": BoardModuleEnum.asset.value,
                "site": {"id": site_id, "company_id": company_id},
                "company": None,
                "document": None,
            }
        )

        expected_tasks_by_modules = [
            {"id": site_task.id, "module": BoardModuleEnum.asset},
            {"id": company_task.id, "module": BoardModuleEnum.asset},
            {"id": site_lease_document_task.id, "module": BoardModuleEnum.diligence},
            {"id": site_om_task.id, "module": BoardModuleEnum.om},
            {"id": company_om_task.id, "module": BoardModuleEnum.om},
        ]
        response_tasks_by_modules = [{"id": task["id"], "module": task["module"]} for task in response.json()["items"]]

        assert response.status_code == 200
        assert response.json()["items"][0].items() <= expected_item.items()
        assert response_tasks_by_modules == expected_tasks_by_modules

    def test_get_tasks_list_ordered_by_due_date(
        self, client, db_session, site_default_board, site_task, non_system_user_auth_header, non_system_user_id
    ):
        """Test get list of user tasks is ordered by due date"""
        task_later_due_date = copy.deepcopy(samples.TEST_TASK_PAYLOAD)
        task_later_due_date.update(
            {
                "due_date": "2050-1-1",
                "external_id": "12342A",
                "assignee_id": non_system_user_id,
                "creator_id": non_system_user_id,
                "status_id": site_default_board.get_statuses_ids()[0],
                "board_id": site_default_board.id,
            }
        )
        task_crud = TaskCRUD(db_session)
        newer_task = task_crud.create_item(task_later_due_date)

        response = client.get(
            self._generate_list_endpoint(),
            headers=non_system_user_auth_header,
        )
        response_json = response.json()["items"]
        assert response.status_code == 200
        assert response_json[0]["id"] == site_task.id
        assert response_json[1]["id"] == newer_task.id
        assert response_json[0]["due_date"] < response_json[1]["due_date"]
        task_crud.delete_by_id(newer_task.id)

    def test_get_tasks_list_ordered_by_due_date_and_priority(
        self, client, db_session, site_default_board, site_task, non_system_user_auth_header, non_system_user_id
    ):
        """Test get list of user tasks is ordered by due date and high priority is on top when due date is same"""
        high_priority_task = copy.deepcopy(samples.TEST_TASK_PAYLOAD)
        high_priority_task.update(
            {
                "priority": "high",
                "external_id": "12342A",
                "assignee_id": non_system_user_id,
                "creator_id": non_system_user_id,
                "status_id": site_default_board.get_statuses_ids()[0],
                "board_id": site_default_board.id,
            }
        )
        task_crud = TaskCRUD(db_session)
        new_task = task_crud.create_item(high_priority_task)

        response = client.get(
            self._generate_list_endpoint(),
            headers=non_system_user_auth_header,
        )
        response_json = response.json()["items"]
        assert response.status_code == 200
        assert response_json[0]["id"] == new_task.id
        assert response_json[0]["priority"] == "High"
        assert response_json[1]["id"] == site_task.id
        assert response_json[1]["priority"] == "Medium"
        # ensure tasks have same due date
        assert response_json[0]["due_date"] == response_json[1]["due_date"]
        task_crud.delete_by_id(new_task.id)
