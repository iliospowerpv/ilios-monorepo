import logging
from typing import Any, Optional

import boto3
from botocore.config import Config
from langchain_aws import ChatBedrock
from langchain_core.rate_limiters import InMemoryRateLimiter
from langchain_google_genai import ChatGoogleGenerativeAI
from vertexai.generative_models import HarmBlockThreshold, HarmCategory


logger = logging.getLogger(__name__)

gemini_safety_settings = {
    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_ONLY_HIGH,
    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
}


def get_llm(
    model_type: str,
    temperature: float = 0.00001,
    top_p: float = 0.85,
    max_output_tokens: int = 8092,
    system_prompt: Optional[str] = None,
) -> Any:
    """
    Set up the LLM for the term_extraction. If the Gemini model is not available,
    it will fall back to VertexAI.
    """

    if model_type == "GEMINI15":
        try:
            logger.info("WORKING WITH GEMINI 1.5 MODEL")
            llm = ChatGoogleGenerativeAI(
                model="gemini-1.5-pro",
                temperature=temperature,
                top_p=top_p,
                max_output_tokens=max_output_tokens,
                convert_system_message_to_human=True,
                safety_settings=gemini_safety_settings,
                rate_limiter=get_rate_limiter(1, 5, 10),
            )
            logger.info("GEMINI 1.5 SETUP COMPLETE")
            return llm
        except Exception as e:
            logger.info(f"Error: {e}")

    elif model_type == "CLAUDE":
        try:
            retry_config = Config(
                region_name="us-east-1",
                retries={"max_attempts": 25, "mode": "standard"},
                max_pool_connections=15,
            )
            session = boto3.session.Session()
            boto3_bedrock_runtime = session.client(
                "bedrock-runtime", config=retry_config
            )

            model_id = "anthropic.claude-3-sonnet-20240229-v1:0"
            model_kwargs = {
                "max_tokens": 8092,
                "temperature": 0.0,
                "top_k": 1,
                "top_p": 0.0,
                "stop_sequences": ["\n\nHuman"],
            }
            if system_prompt:
                llm = ChatBedrock(  # type: ignore
                    client=boto3_bedrock_runtime,
                    model_id=model_id,
                    model_kwargs=model_kwargs,
                    rate_limiter=get_rate_limiter(10, 1, 20),
                    system_prompt_with_tools=system_prompt,
                )
            else:
                llm = ChatBedrock(  # type: ignore
                    client=boto3_bedrock_runtime,
                    model_id=model_id,
                    model_kwargs=model_kwargs,
                    rate_limiter=get_rate_limiter(10, 1, 20),
                )
            logger.info("CLAUDE SETUP COMPLETE")
            return llm
        except Exception as e:
            logger.info(f"Error: {e}")
    else:
        raise ValueError("UNSUPPORTED MODEL TYPE, AVAILABLE OPTIONS: GEMINI15, CLAUDE")


def get_rate_limiter(
    requests_per_second: float, check_every_n_seconds: float, max_bucket_size: int
) -> InMemoryRateLimiter:
    """Get the rate limiter for the LLM."""
    return InMemoryRateLimiter(
        requests_per_second=requests_per_second,
        check_every_n_seconds=check_every_n_seconds,
        max_bucket_size=max_bucket_size,
    )
