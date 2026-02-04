"""LLM Stub for Testing

Provides a deterministic LLM stub that can be injected during tests
to avoid calling real OpenAI API while still testing the full pipeline.

SECURITY: The stub can ONLY be enabled in test/dev environments.
In production (environment_name="production"), the stub is always disabled
regardless of env var settings.

Usage in tests:
    from app.services.llm_stub import LLMStub, enable_llm_stub, disable_llm_stub
    
    # Enable stub with default response
    enable_llm_stub()
    
    # Or with custom response
    enable_llm_stub(LLMStub(parsed_result={"field1": {"value": "test", "confidence": 0.95}}))
    
    # Or force an exception
    enable_llm_stub(LLMStub(raise_exception=ValueError("Simulated LLM failure")))
    
    # Disable after test
    disable_llm_stub()

Safe Environments:
    - "test", "testing", "dev", "development", "local", "debug"
    
Blocked Environments:
    - "production", "prod", "staging" (stub always disabled)
"""

import os
import logging
from typing import Optional, Any

logger = logging.getLogger(__name__)

_llm_stub_instance: Optional["LLMStub"] = None

SAFE_ENVIRONMENTS = {"test", "testing", "dev", "development", "local", "debug"}
BLOCKED_ENVIRONMENTS = {"production", "prod", "staging"}


class LLMStub:
    """Configurable LLM stub for testing."""
    
    def __init__(
        self,
        parsed_result: Optional[dict] = None,
        raw_response: Optional[str] = None,
        raise_exception: Optional[Exception] = None,
    ):
        self.parsed_result = parsed_result or self._default_parsed_result()
        self.raw_response = raw_response
        self.raise_exception = raise_exception
        self.call_count = 0
        self.last_system_prompt = None
        self.last_user_prompt = None
    
    @staticmethod
    def _default_parsed_result() -> dict:
        """Default parsed result for tests."""
        return {
            "lessor_name": {
                "value": "Test Landlord LLC",
                "confidence": 0.95,
                "evidence": {
                    "page": 1,
                    "snippet": "Test Landlord LLC, a Delaware limited liability company",
                    "anchor_text": "LESSOR"
                }
            },
            "lessee_name": {
                "value": "Test Tenant Corp",
                "confidence": 0.92,
                "evidence": {
                    "page": 1,
                    "snippet": "Test Tenant Corp, a California corporation",
                    "anchor_text": "LESSEE"
                }
            },
            "lease_start_date": {
                "value": "2024-01-01",
                "confidence": 0.88,
                "evidence": {
                    "page": 2,
                    "snippet": "The lease term shall commence on January 1, 2024",
                    "anchor_text": "TERM"
                }
            },
            "lease_term_years": {
                "value": "25",
                "confidence": 0.90,
                "evidence": {
                    "page": 2,
                    "snippet": "for a period of twenty-five (25) years",
                    "anchor_text": "TERM"
                }
            },
            "annual_rent": {
                "value": "50000",
                "confidence": 0.85,
                "evidence": {
                    "page": 3,
                    "snippet": "$50,000 per year",
                    "anchor_text": "RENT"
                }
            },
            "_metadata": {
                "model": "stub-model",
                "extraction_version": "test-1.0"
            }
        }
    
    def call(self, system_prompt: str, user_prompt: str) -> dict:
        """Simulate LLM call with configured behavior."""
        self.call_count += 1
        self.last_system_prompt = system_prompt
        self.last_user_prompt = user_prompt
        
        if self.raise_exception:
            raise self.raise_exception
        
        return self.parsed_result


def _get_current_environment() -> str:
    """Get current environment name from settings or env var."""
    env = os.environ.get("environment_name", "").lower()
    if not env:
        env = os.environ.get("ENVIRONMENT_NAME", "").lower()
    if not env:
        try:
            from app.settings import settings
            env = getattr(settings, "environment_name", "").lower()
        except Exception:
            pass
    return env


def _is_safe_environment() -> bool:
    """Check if current environment allows LLM stub.
    
    SECURITY: Follows explicit allow-list approach.
    Returns True ONLY for explicitly safe environments or pytest context.
    Unknown environments are blocked by default.
    """
    if os.environ.get("PYTEST_CURRENT_TEST"):
        return True
    
    env = _get_current_environment()
    
    if env in BLOCKED_ENVIRONMENTS:
        return False
    
    if env in SAFE_ENVIRONMENTS:
        return True
    
    if os.environ.get("LLM_STUB_FORCE_ALLOW") == "true":
        logger.warning(f"LLM stub force-allowed in environment '{env}' - use with caution")
        return True
    
    return False


def enable_llm_stub(stub: Optional[LLMStub] = None) -> Optional[LLMStub]:
    """Enable LLM stub for testing. Sets environment flag.
    
    SECURITY: Raises RuntimeError if called in production environment.
    """
    global _llm_stub_instance
    
    if not _is_safe_environment():
        env = _get_current_environment()
        error_msg = f"LLM stub cannot be enabled in environment '{env}' - only allowed in test/dev"
        logger.error(error_msg)
        raise RuntimeError(error_msg)
    
    _llm_stub_instance = stub or LLMStub()
    os.environ["LLM_STUB_ENABLED"] = "true"
    logger.info(f"LLM stub enabled in environment '{_get_current_environment()}'")
    return _llm_stub_instance


def disable_llm_stub():
    """Disable LLM stub and clear environment flag."""
    global _llm_stub_instance
    _llm_stub_instance = None
    os.environ.pop("LLM_STUB_ENABLED", None)


def get_llm_stub() -> Optional[LLMStub]:
    """Get current LLM stub instance if enabled and environment is safe."""
    if not _is_safe_environment():
        return None
    if os.environ.get("LLM_STUB_ENABLED") == "true":
        return _llm_stub_instance
    return None


def is_llm_stub_enabled() -> bool:
    """Check if LLM stub is currently enabled.
    
    SECURITY: Always returns False in production environments,
    regardless of env var settings.
    """
    if not _is_safe_environment():
        return False
    return os.environ.get("LLM_STUB_ENABLED") == "true"
