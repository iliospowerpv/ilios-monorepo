from app.models.board import BoardModuleEnum

TEST_BOARD_BODY = {"name": "Test board", "description": "Just a test board", "is_active": False}
TEST_BOARD_BODY_REQUEST = TEST_BOARD_BODY | {"module": BoardModuleEnum.asset}
