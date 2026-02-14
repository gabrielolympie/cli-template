#!/usr/bin/env python3
"""Minimalist script to load an LLM model from config.yaml"""

from mirascope import llm
import os
import yaml
from dotenv import load_dotenv

load_dotenv()


def load_config(config_path: str = "config.yaml") -> dict:
    """Load configuration from config.yaml"""
    default_config = {
        "llm": {
            "api_base": None,
            "provider": "openai",
            "model_name": "gpt-4",
            "max_completion_tokens": 8192,
            "context_size": 128000,
            "support_image": False,
            "support_audio_input": False,
            "support_audio_output": False,
            "thinking": {"level": None, "include_thoughts": False}
        },
        "debug": False
    }

    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            loaded_config = yaml.safe_load(f)
            if loaded_config:
                default_config.update(loaded_config)

    return default_config


def setup_provider(config: dict) -> None:
    """Register provider if needed (for OpenAI-compatible APIs)"""
    llm_config = config.get("llm", {})
    provider = llm_config.get("provider", "openai")
    api_base = llm_config.get("api_base")
    api_key_env = llm_config.get("api_key_env")

    # Native providers - no registration needed
    native_providers = ["anthropic", "google", "openai", "ollama", "mlx"]
    if provider in native_providers and not api_base:
        return

    # Get API key
    if api_key_env:
        api_key = os.environ.get(api_key_env)
    else:
        provider_env_map = {
            "vllm": "VLLM_API_KEY",
            "zai": "ZAI_API_KEY",
            "together": "TOGETHER_API_KEY",
            "xai": "XAI_API_KEY",
        }
        env_var = provider_env_map.get(provider, "OPENAI_API_KEY")
        api_key = os.environ.get(env_var)

        # Fallback for local servers
        if not api_key and provider in ["vllm", "ollama"]:
            api_key = "unused"

    if api_base and api_key:
        llm.register_provider(
            "openai:completions",
            scope=f"{provider}/",
            base_url=api_base,
            api_key=api_key,
        )


def load_model(config: dict) -> llm.Model:
    """Create LLM model instance from config"""
    llm_config = config.get("llm", {})

    model_name = llm_config.get("model_name", "gpt-4")
    max_tokens = llm_config.get("max_completion_tokens", 8192)
    thinking_config = llm_config.get("thinking", {"level": None, "include_thoughts": False})

    thinking = None
    if thinking_config.get("level") and thinking_config.get("level") != "None":
        thinking = {
            "level": thinking_config.get("level"),
            "include_thoughts": thinking_config.get("include_thoughts", True)
        }

    return llm.Model(
        model_name,
        max_tokens=max_tokens,
        thinking=thinking
    )


def get_model(config_path: str = "config.yaml") -> tuple[llm.Model, dict]:
    """Convenience function: load config, setup provider, and return model"""
    config = load_config(config_path)
    setup_provider(config)
    model = load_model(config)
    return model, config


if __name__ == "__main__":
    model, config = get_model()
    llm_config = config["llm"]

    print("Model loaded successfully:")
    print(f"  Provider: {llm_config['provider']}")
    print(f"  Model: {llm_config['model_name']}")
    print(f"  Max tokens: {llm_config['max_completion_tokens']}")
    print(f"  Context size: {llm_config['context_size']}")
