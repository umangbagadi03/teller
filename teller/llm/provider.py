import os

from teller import config

PROVIDER_NAMES = ["gemini", "anthropic", "openai", "ollama", "offline"]

# Providers a visitor can pick with their own key in the web app
KEY_PROVIDERS = ["gemini", "anthropic", "openai"]

# The offline model is a script, not an LLM. See teller/llm/offline.py.
OFFLINE_MODEL = "offline/scripted"

LIVE_RETRIES = 2


def pick_provider():
    # An explicit choice in .env always wins
    if config.LLM_PROVIDER:
        if config.LLM_PROVIDER not in PROVIDER_NAMES:
            raise ValueError(
                "Unknown LLM_PROVIDER '" + config.LLM_PROVIDER + "'. "
                "Use one of: gemini, anthropic, openai, ollama, offline."
            )
        return config.LLM_PROVIDER

    # Otherwise use the first provider that has an API key
    if config.GEMINI_API_KEY:
        return "gemini"
    if config.ANTHROPIC_API_KEY:
        return "anthropic"
    if config.OPENAI_API_KEY:
        return "openai"

    # A local model only when one is named, otherwise the offline demo
    if config.OLLAMA_MODEL:
        return "ollama"
    return "offline"


def get_default_model(provider):
    if provider == "gemini":
        return config.GEMINI_MODEL
    if provider == "anthropic":
        return config.ANTHROPIC_MODEL
    if provider == "openai":
        return config.OPENAI_MODEL
    if provider == "ollama":
        if config.OLLAMA_MODEL:
            return config.OLLAMA_MODEL
        return config.DEFAULT_OLLAMA_MODEL
    return "scripted"


def make_model_name(provider, model):
    # The benchmark and the agent both call LLMs through LiteLLM,
    # which picks the provider from the prefix of the model name.
    if provider == "offline":
        return OFFLINE_MODEL

    if model == "":
        model = get_default_model(provider)

    if provider == "ollama":
        os.environ["OLLAMA_API_BASE"] = config.OLLAMA_URL
        return "ollama_chat/" + model

    return provider + "/" + model


def get_model_name():
    provider = pick_provider()
    return make_model_name(provider, "")


def get_llm_settings():
    settings = {
        "temperature": 0.0,
        "num_retries": config.LLM_RETRIES,
    }

    # Ollama's default context is too small for the policy, tools and documents
    if pick_provider() == "ollama":
        settings["num_ctx"] = config.OLLAMA_CONTEXT_SIZE

    return settings


def make_key_settings(api_key):
    # Settings for a visitor's own key. Few retries, so a wrong key fails fast.
    return {
        "temperature": 0.0,
        "num_retries": LIVE_RETRIES,
        "api_key": api_key,
    }


def is_offline(model_name):
    return model_name == OFFLINE_MODEL
