import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Literal

class Settings(BaseSettings):
    # LLM Provider: "anthropic" or "openai"
    llm_provider: Literal["anthropic", "openai"] = "anthropic"
    
    # Anthropic Settings
    anthropic_api_key: str = ""
    claude_model_generation: str = "claude-3-5-sonnet-20241022"
    claude_model_analysis: str = "claude-3-haiku-20240307"
    
    # OpenAI Settings
    openai_api_key: str = ""
    openai_model_generation: str = "gpt-4o"
    openai_model_analysis: str = "gpt-4o-mini"
    
    # Shared LLM Settings
    llm_temperature_generation: float = 0.5
    llm_temperature_analysis: float = 0.2
    llm_max_tokens_generation: int = 16384
    llm_max_tokens_analysis: int = 4096
    max_retry_count: int = 2
    
    # Embedding Settings
    embedding_provider: Literal["local", "openai"] = "local"
    embedding_model: str = "all-MiniLM-L6-v2"
    openai_api_key: str = ""
    
    # RAG Settings
    chroma_persist_dir: str = "./chroma_data"
    retrieval_top_k_spec: int = 5
    retrieval_top_k_code: int = 10
    retrieval_top_k_test: int = 5
    retrieval_top_k_reference: int = 5
    retrieval_top_k_schema: int = 3
    relevance_threshold: float = 0.3
    
    # Project Settings
    karate_project_path: str = "./karate_project"
    karate_config_path: str = "./config/karate_project.yaml"
    generated_features_dir: str = "./karate_project/src/test/java/karate/generated"
    
    # Execution Settings
    java_home: str = "/Library/Java/JavaVirtualMachines/amazon-corretto-17.jdk/Contents/Home"
    maven_execution_timeout: int = 120
    karate_env: str = "dev"
    karate_report_dir: str = "./karate_project/target/karate-reports"
    
    # Mock Server Settings
    wiremock_jar_path: str = "./karate_project/wiremock/wiremock-standalone.jar"
    wiremock_port: int = 8080
    wiremock_auto_start: bool = True
    
    # Database Schema Ingestion
    db_connection_string: str = ""
    db_schema: str = "public"
    db_table_filter: str = ""  # comma-separated table names, empty = all
    
    log_level: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8",
        extra="ignore"
    )

_settings_instance = None

def get_settings() -> Settings:
    global _settings_instance
    if _settings_instance is None:
        _settings_instance = Settings()
    return _settings_instance


def get_llm(role: Literal["generation", "analysis"] = "generation"):
    """
    Factory function that returns the configured LLM for the given role.
    
    Supports Anthropic (Claude) and OpenAI (GPT) backends. The provider
    is selected via the LLM_PROVIDER setting (defaults to 'anthropic').
    
    Args:
        role: Either 'generation' (creative, higher token limit) or
              'analysis' (fast, cheaper, classification tasks).
    
    Returns:
        A LangChain chat model instance (ChatAnthropic or ChatOpenAI).
    """
    settings = get_settings()
    
    if role == "generation":
        temperature = settings.llm_temperature_generation
        max_tokens = settings.llm_max_tokens_generation
    else:
        temperature = settings.llm_temperature_analysis
        max_tokens = settings.llm_max_tokens_analysis
    
    if settings.llm_provider == "openai":
        from langchain_openai import ChatOpenAI
        model = settings.openai_model_generation if role == "generation" else settings.openai_model_analysis
        return ChatOpenAI(
            model=model,
            api_key=settings.openai_api_key,
            temperature=temperature,
            max_tokens=max_tokens,
        )
    else:  # anthropic (default)
        from langchain_anthropic import ChatAnthropic
        model = settings.claude_model_generation if role == "generation" else settings.claude_model_analysis
        return ChatAnthropic(
            model=model,
            api_key=settings.anthropic_api_key,
            temperature=temperature,
            max_tokens=max_tokens,
        )
