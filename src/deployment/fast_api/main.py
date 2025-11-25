import json
import logging.config
import os
from time import sleep
from typing import Any, Dict, List

import uvicorn
from fastapi import BackgroundTasks, Depends, FastAPI
from fastapi.responses import HTMLResponse
from requests import patch

from src.deployment.cloud_run_job.key_value_extraction.env_enum import Env
from src.deployment.cloud_run_job.key_value_extraction.response_status import Status
from src.deployment.fast_api.auth import api_key_check
from src.deployment.fast_api.chatbot import chatbot_router
from src.deployment.fast_api.file_processing import file_processing_router
from src.deployment.fast_api.models.input import (
    CoterminousInputItem,
    CoterminousInputPayload,
)
from src.deployment.fast_api.models.output import (
    ComparisonStatus,
    CoterminousOutputItem,
    CoterminousOutputPayload,
)
from src.pipelines.co_terminus_check.base import CoTerminusCheck


logging.config.fileConfig("logging.conf", disable_existing_loggers=False)
logger = logging.getLogger(__name__)


app = FastAPI()
app.include_router(file_processing_router)
app.include_router(chatbot_router)


@app.get("/", dependencies=[Depends(api_key_check)])
def read_root() -> Dict[str, str]:
    return {"FastAPI": "iliOS_AI_App"}


def compare_key_value_pairs(
    key_value_pairs: List[CoterminousInputItem],
) -> CoterminousOutputPayload:
    assert key_value_pairs, "Empty input, no key items to compare"
    for item in key_value_pairs:
        for source in item.sources:
            assert (
                source.key_item
            ), f"Empty key for item {item.name}. Key item cannot be empty"
            assert (
                source.value
            ), f"Empty value for item {item.name}. Value cannot be empty"
    co_terminus_check = CoTerminusCheck()
    result = co_terminus_check.run_batch_validate(key_value_pairs)
    return CoterminousOutputPayload(
        items=result, status=Status.COMPLETED, message="Successful comparison"
    )


def co_terminus_background_task(
    input_payload: CoterminousInputPayload, backend_output_path: str
) -> None:
    try:
        result = compare_key_value_pairs(input_payload.items)
    except AssertionError as e:
        result = CoterminousOutputPayload(
            items=[], status=Status.PROCESSING_FAILED, message=str(e)
        )
    backend_response = send_data(backend_output_path, Status.COMPLETED, result)
    logger.info(
        f"Backend connection success for QA/PROD environment: {backend_response.json()}"
    )


def mock_coterminous_background_task(
    endpoint_path: str,
    result: CoterminousOutputPayload,
) -> None:
    logger.info("Starting mock function; waiting for 6 seconds")
    sleep(7)
    logger.info("Sending data to backend")
    backend_response = send_data(endpoint_path, Status.COMPLETED, result)
    logger.info(
        f"Backend connection success for QA/PROD environment: {backend_response.json()}"
    )
    logger.info("Mock function completed")


def send_data(
    endpoint_path: str,
    status: Status,
    result: CoterminousOutputPayload,
) -> Any:
    dump_data = [item.model_dump() for item in result.items]
    try:

        put_request_result = patch(
            endpoint_path,
            params={"api_key": os.environ["BACKEND_API_KEY"]},
            json={"status": str(status.value), "items": dump_data},
        )
        logger.info(json.dumps({"status": str(status.value), "items": dump_data}))
    except Exception as e:
        logger.error(f"Backend patch connection error: {str(e)}")
        return None
    try:
        logger.info(f"Backend connection success: {put_request_result.json()}")
    except Exception as e:
        logger.error(f"Backend connection output parse error: {str(e)}")
    return put_request_result


@app.post("/coterminous-check", dependencies=[Depends(api_key_check)])
async def evaluate(
    input_payload: CoterminousInputPayload, background_task: BackgroundTasks
) -> str:
    """Endpoint to perform the co-terminus check"""
    logger.info(f"Env: {os.environ.get('ENV')}")
    logger.info(f"Received items: {[item.name for item in input_payload.items]}")
    backend_output_path = str(os.environ.get("BACKEND_URL")).format(
        record_id=input_payload.id
    )
    logger.info(f"Backend output path: {backend_output_path}")
    if os.environ.get("ENV") == Env.TEST:
        return f"Test environment connection success for payload id: {input_payload.id}"
    elif os.environ.get("ENV") == Env.DEV:
        items = [
            CoterminousOutputItem(name=item.name, status=ComparisonStatus.EQUAL)
            for item in input_payload.items
        ]
        logger.info("Adding background task")
        background_task.add_task(
            mock_coterminous_background_task,
            backend_output_path,
            CoterminousOutputPayload(items=items, status=Status.COMPLETED),
        )
        logger.info("Finishing the job and responding to the client")
        return f"Job scheduled for payload id: {input_payload.id}"
    elif os.environ.get("ENV") in [Env.QA, Env.UAT, Env.PROD]:
        background_task.add_task(
            co_terminus_background_task, input_payload, backend_output_path
        )
        logger.info(f"Job scheduled for payload id: {input_payload.id}")
        return f"Job scheduled for payload id: {input_payload.id}"
    else:
        return f"Invalid environment: {os.environ.get('ENV')}"


# flake8: noqa

html = """
<!DOCTYPE html>
<html>
    <head>
        <title>WebSocket Test</title>
    </head>
    <body>
        <h1>WebSocket Test</h1>
        <form action="" onsubmit="sendMessage(event)">
            <label>Token: <input type="text" id="token" autocomplete="off" value=""/></label>
            <button onclick="connect(event)">Connect</button>
            <hr>
            <label>Message: <input type="text" id="messageText" autocomplete="off"/></label>
            <button>Send</button>
        </form>
        <ul id='messages'>
        </ul>
        <script>
        var ws = null;
            function connect(event) {
                var token = document.getElementById("token").value;
                ws = new WebSocket("ws://0.0.0.0:8080/chatbot/chat?token=" + token);
                ws.onmessage = function(event) {
                    var messages = document.getElementById('messages');
                    var message = document.createElement('li');
                    var content = document.createTextNode(event.data);
                    message.appendChild(content);
                    messages.appendChild(message);
                };
                event.preventDefault();
            }
            function sendMessage(event) {
                var input = document.getElementById("messageText");
                ws.send(input.value);
                input.value = '';
                event.preventDefault();
            }
        </script>
    </body>
</html>
"""


@app.get("/chatbot_test", dependencies=[Depends(api_key_check)])
async def get() -> HTMLResponse:
    return HTMLResponse(html)


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8080)
