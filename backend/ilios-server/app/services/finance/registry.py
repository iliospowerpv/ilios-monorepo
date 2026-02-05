"""Finance provider registry.

Manages registration and instantiation of finance providers.
"""

from typing import Optional, Type
import logging

from .provider import FinanceProvider, FinanceProviderError

logger = logging.getLogger(__name__)


class FinanceProviderRegistry:
    """Registry for finance providers.
    
    Manages the available provider types and creates instances
    when needed for a specific company configuration.
    """
    
    _instance: Optional["FinanceProviderRegistry"] = None
    
    def __init__(self):
        self._providers: dict[str, Type[FinanceProvider]] = {}
        self._register_default_providers()
    
    def _register_default_providers(self):
        """Register the default set of providers."""
        from .gravity_provider import GravityFinanceProvider
        
        self.register("gravity", GravityFinanceProvider)
    
    def register(self, provider_key: str, provider_class: Type[FinanceProvider]):
        """Register a provider class.
        
        Args:
            provider_key: Unique identifier for the provider.
            provider_class: The provider class to register.
        """
        if provider_key in self._providers:
            logger.warning(f"Overwriting existing provider: {provider_key}")
        
        self._providers[provider_key] = provider_class
        logger.info(f"Registered finance provider: {provider_key}")
    
    def get_provider_class(self, provider_key: str) -> Optional[Type[FinanceProvider]]:
        """Get a provider class by key.
        
        Args:
            provider_key: The provider key.
            
        Returns:
            The provider class or None if not found.
        """
        return self._providers.get(provider_key)
    
    def create_provider(
        self,
        provider_key: str,
        credentials: dict,
        config: Optional[dict] = None,
    ) -> FinanceProvider:
        """Create a provider instance.
        
        Args:
            provider_key: The provider key.
            credentials: The credentials dictionary.
            config: Optional configuration dictionary.
            
        Returns:
            An instance of the provider.
            
        Raises:
            FinanceProviderError: If the provider is not registered.
        """
        provider_class = self.get_provider_class(provider_key)
        
        if not provider_class:
            raise FinanceProviderError(
                message=f"Unknown finance provider: {provider_key}",
                provider_key=provider_key,
                error_code="UNKNOWN_PROVIDER",
            )
        
        return provider_class(credentials=credentials, config=config)
    
    def list_providers(self) -> list[dict]:
        """List all registered providers.
        
        Returns:
            List of provider info dictionaries.
        """
        result = []
        for key, cls in self._providers.items():
            instance = cls(credentials={}, config={})
            result.append({
                "key": key,
                "display_name": instance.display_name,
                "supports_budgets": instance.supports_budgets,
            })
        return result
    
    @classmethod
    def get_instance(cls) -> "FinanceProviderRegistry":
        """Get the singleton registry instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance


def get_provider_registry() -> FinanceProviderRegistry:
    """Get the global provider registry instance."""
    return FinanceProviderRegistry.get_instance()
