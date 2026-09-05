import os
from pydantic import BaseModel, Field
from typing import Any, Optional

from langchain_core.runnables import RunnableConfig


class Configuration(BaseModel):
    """The configuration for the agent."""

    query_generator_model: str = Field(
        default="gemini-3.6-flash",
        metadata={
            "description": "The name of the language model to use for the agent's query generation."
        },
    )

    web_search_model: str = Field(
        default="gemini-3.6-flash",
        metadata={
            "description": "The name of the language model to use for the agent's web search."
        },
    )

    reflection_model: str = Field(
        default="gemini-3.6-flash",
        metadata={
            "description": "The name of the language model to use for the agent's reflection."
        },
    )

    answer_model: str = Field(
        default="gemini-3.1-pro-preview",
        metadata={
            "description": "The name of the language model to use for the agent's answer."
        },
    )

    number_of_initial_queries: int = Field(
        default=3,
        metadata={"description": "The number of initial search queries to generate."},
    )

    max_research_loops: int = Field(
        default=2,
        metadata={"description": "The maximum number of research loops to perform."},
    )

    @classmethod
    def from_runnable_config(
        cls, config: Optional[RunnableConfig] = None
    ) -> "Configuration":
        """Create a Configuration instance from a RunnableConfig."""
        configurable = (
            config["configurable"] if config and "configurable" in config else {}
        )

        # Get raw values from environment or config
        raw_values: dict[str, Any] = {
            name: os.environ.get(name.upper(), configurable.get(name))
            for name in cls.model_fields.keys()
        }

        # Fallback to GEMINI_FLASH_MODEL and GEMINI_PRO_MODEL if set
        flash_model = os.environ.get("GEMINI_FLASH_MODEL")
        pro_model = os.environ.get("GEMINI_PRO_MODEL")
        if flash_model:
            if not raw_values.get("query_generator_model"):
                raw_values["query_generator_model"] = flash_model
            if not raw_values.get("web_search_model"):
                raw_values["web_search_model"] = flash_model
            if not raw_values.get("reflection_model"):
                raw_values["reflection_model"] = flash_model
        if pro_model and not raw_values.get("answer_model"):
            raw_values["answer_model"] = pro_model

        # Filter out None values
        values = {k: v for k, v in raw_values.items() if v is not None}

        return cls(**values)
