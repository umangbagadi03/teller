import os

from teller import config

PROVIDER_NAMES = ["gemini", "anthropic", "openai", "ollama"]


def pick_provider():
    # An explicit choice in .env always wins
    if config.LLM_PROVIDER:
        if config.LLM_PROVIDER not in PROVIDER_NAMES:
            raise ValueError(
                "Unknown LLM_PROVIDER '" + config.LLM_PROVIDER + "'. "
                "Use one of: gemini, anthropic, openai, ollama."
            )
        return config.LLM_PROVIDER

    # Otherwise use the first provider that has an API key.
    # Ollama runs locally and needs no key, so it is the fallback.
    if config.GEMINI_API_KEY:
        return "gemini"
    if config.ANTHROPIC_API_KEY:
        return "anthropic"
    if config.OPENAI_API_KEY:
        return "openai"
    return "ollama"


def get_model_name():
    # The benchmark and the agent both call LLMs through LiteLLM,
    # which picks the provider from the prefix of the model name.
    provider = pick_provider()

    if provider == "gemini":
        return "gemini/" + config.GEMINI_MODEL
    if provider == "anthropic":
        return "anthropic/" + config.ANTHROPIC_MODEL
    if provider == "openai":
        return "openai/" + config.OPENAI_MODEL

    os.environ["OLLAMA_API_BASE"] = config.OLLAMA_URL
    return "ollama_chat/" + config.OLLAMA_MODEL


def get_llm_settings():
    settings = {
        "temperature": 0.0,
        "num_retries": config.LLM_RETRIES,
    }

    # Ollama's default context is too small for the policy, tools and documents
    if pick_provider() == "ollama":
        settings["num_ctx"] = config.OLLAMA_CONTEXT_SIZE

    return settings
