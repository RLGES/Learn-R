"""
Configuration loader for Learn-R project.

Loads environment variables from .env file and provides typed access
to configuration values for LLM APIs and other settings.
"""
import os
from pathlib import Path
from typing import Optional

# Try to load python-dotenv, but work without it if not installed
try:
    from dotenv import load_dotenv
    DOTENV_AVAILABLE = True
except ImportError:
    DOTENV_AVAILABLE = False


class Config:
    """
    Configuration class that loads settings from environment variables.
    
    Usage:
        from config import config
        
        # Access LLM settings
        api_key = config.get_api_key("openai")
        model = config.openai_model
        
        # Check provider
        if config.llm_provider == "openai":
            ...
    """
    
    def __init__(self):
        """Initialize configuration by loading .env file."""
        self._load_env()
        self._validate()
    
    def _load_env(self):
        """Load environment variables from .env file."""
        if DOTENV_AVAILABLE:
            # Find the project root (where .env should be located)
            project_root = Path(__file__).parent
            env_path = project_root / ".env"
            
            if env_path.exists():
                load_dotenv(env_path)
                print(f"✓ Loaded configuration from {env_path}")
            else:
                env_example = project_root / ".env.example"
                if env_example.exists():
                    print(f"⚠ No .env file found. Copy .env.example to .env and add your API keys:")
                    print(f"  cp {env_example} {env_path}")
        else:
            print("⚠ python-dotenv not installed. Using system environment variables.")
            print("  Install with: pip install python-dotenv")
    
    def _validate(self):
        """Validate required configuration."""
        provider = self.llm_provider
        if provider:
            key = self.get_api_key(provider)
            if not key or key.startswith("your_"):
                print(f"⚠ No valid API key found for provider '{provider}'")
                print(f"  Set {provider.upper()}_API_KEY in your .env file")
    
    # ============================================
    # LLM Provider Settings
    # ============================================
    
    @property
    def llm_provider(self) -> str:
        """Get the default LLM provider (openai, anthropic, google, lmstudio, huggingface)."""
        return os.getenv("LLM_PROVIDER", "openai").lower()
    
    @property
    def openai_api_key(self) -> Optional[str]:
        """Get OpenAI API key."""
        return os.getenv("OPENAI_API_KEY")
    
    @property
    def anthropic_api_key(self) -> Optional[str]:
        """Get Anthropic API key."""
        return os.getenv("ANTHROPIC_API_KEY")
    
    @property
    def google_api_key(self) -> Optional[str]:
        """Get Google API key."""
        return os.getenv("GOOGLE_API_KEY")
    
    @property
    def lmstudio_base_url(self) -> str:
        """Get LM Studio server URL (local inference)."""
        return os.getenv("LMSTUDIO_BASE_URL", "http://localhost:1234/v1")
    
    @property
    def huggingface_api_key(self) -> Optional[str]:
        """Get Hugging Face API token."""
        return os.getenv("HUGGINGFACE_API_KEY") or os.getenv("HF_TOKEN")
    
    def get_api_key(self, provider: str = None) -> Optional[str]:
        """
        Get API key for the specified provider.
        
        Args:
            provider: Provider name (openai, anthropic, google). 
                     Defaults to LLM_PROVIDER env var.
        
        Returns:
            API key string or None if not set.
        """
        provider = (provider or self.llm_provider).lower()
        
        key_map = {
            "openai": self.openai_api_key,
            "anthropic": self.anthropic_api_key,
            "google": self.google_api_key,
            "huggingface": self.huggingface_api_key,
            "lmstudio": "local",  # LM Studio doesn't need API key
        }
        
        return key_map.get(provider)
    
    # ============================================
    # Model Names
    # ============================================
    
    @property
    def openai_model(self) -> str:
        """Get OpenAI model name."""
        return os.getenv("OPENAI_MODEL", "gpt-4o")
    
    @property
    def anthropic_model(self) -> str:
        """Get Anthropic model name."""
        return os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-latest")
    
    @property
    def google_model(self) -> str:
        """Get Google model name."""
        return os.getenv("GOOGLE_MODEL", "gemini-2.0-flash")
    
    @property
    def lmstudio_model(self) -> str:
        """Get LM Studio model name (depends on what model is loaded)."""
        return os.getenv("LMSTUDIO_MODEL", "local-model")
    
    @property
    def huggingface_model(self) -> str:
        """Get Hugging Face model ID."""
        return os.getenv("HUGGINGFACE_MODEL", "mistralai/Mistral-7B-Instruct-v0.3")
    
    def get_model(self, provider: str = None) -> str:
        """
        Get model name for the specified provider.
        
        Args:
            provider: Provider name. Defaults to LLM_PROVIDER env var.
        
        Returns:
            Model name string.
        """
        provider = (provider or self.llm_provider).lower()
        
        model_map = {
            "openai": self.openai_model,
            "anthropic": self.anthropic_model,
            "google": self.google_model,
            "lmstudio": self.lmstudio_model,
            "huggingface": self.huggingface_model,
        }
        
        return model_map.get(provider, "gpt-4o")
    
    # ============================================
    # Advanced Settings
    # ============================================
    
    @property
    def llm_max_tokens(self) -> int:
        """Get max tokens for LLM responses."""
        return int(os.getenv("LLM_MAX_TOKENS", "2048"))
    
    @property
    def llm_temperature(self) -> float:
        """Get temperature for LLM generation."""
        return float(os.getenv("LLM_TEMPERATURE", "0.3"))
    
    @property
    def llm_timeout(self) -> int:
        """Get request timeout in seconds."""
        return int(os.getenv("LLM_TIMEOUT", "60"))
    
    @property
    def llm_debug(self) -> bool:
        """Check if debug logging is enabled."""
        return os.getenv("LLM_DEBUG", "false").lower() in ("true", "1", "yes")
    
    # ============================================
    # Utility Methods
    # ============================================
    
    def is_configured(self, provider: str = None) -> bool:
        """
        Check if the specified provider is properly configured.
        
        Args:
            provider: Provider name. Defaults to LLM_PROVIDER env var.
        
        Returns:
            True if API key is set and valid.
        """
        key = self.get_api_key(provider)
        return key is not None and not key.startswith("your_")
    
    def get_available_providers(self) -> list:
        """
        Get list of configured providers.
        
        Returns:
            List of provider names that have valid API keys.
        """
        providers = []
        for provider in ["openai", "anthropic", "google", "lmstudio", "huggingface"]:
            if self.is_configured(provider):
                providers.append(provider)
        return providers
    
    def __str__(self) -> str:
        """Get string representation of config state."""
        lines = ["Configuration:"]
        lines.append(f"  Default provider: {self.llm_provider}")
        lines.append(f"  Available providers: {self.get_available_providers() or 'None configured'}")
        lines.append(f"  Max tokens: {self.llm_max_tokens}")
        lines.append(f"  Temperature: {self.llm_temperature}")
        lines.append(f"  Debug mode: {self.llm_debug}")
        return "\n".join(lines)


# Global config instance
config = Config()


# Convenience functions
def get_api_key(provider: str = None) -> Optional[str]:
    """Get API key for provider."""
    return config.get_api_key(provider)


def get_model(provider: str = None) -> str:
    """Get model name for provider."""
    return config.get_model(provider)


def is_configured(provider: str = None) -> bool:
    """Check if provider is configured."""
    return config.is_configured(provider)
