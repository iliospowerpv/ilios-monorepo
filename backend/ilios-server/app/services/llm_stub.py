"""LLM Stub for Testing

Provides a deterministic LLM stub that can be injected during tests
to avoid calling real OpenAI API while still testing the full pipeline.

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
"""

import os
from typing import Optional, Any

_llm_stub_instance: Optional["LLMStub"] = None


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


def enable_llm_stub(stub: Optional[LLMStub] = None):
    """Enable LLM stub for testing. Sets environment flag."""
    global _llm_stub_instance
    _llm_stub_instance = stub or LLMStub()
    os.environ["LLM_STUB_ENABLED"] = "true"
    return _llm_stub_instance


def disable_llm_stub():
    """Disable LLM stub and clear environment flag."""
    global _llm_stub_instance
    _llm_stub_instance = None
    os.environ.pop("LLM_STUB_ENABLED", None)


def get_llm_stub() -> Optional[LLMStub]:
    """Get current LLM stub instance if enabled."""
    if os.environ.get("LLM_STUB_ENABLED") == "true":
        return _llm_stub_instance
    return None


def is_llm_stub_enabled() -> bool:
    """Check if LLM stub is currently enabled."""
    return os.environ.get("LLM_STUB_ENABLED") == "true"
