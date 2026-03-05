"""
KontentPyper - LLM Client (LangChain Abstraction)
Uses langchain_openai.ChatOpenAI for model-agnostic structured and text generation.
Swap provider by changing the import and model string - zero other code changes needed.
"""

import logging
from typing import Type, TypeVar

from pydantic import BaseModel
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class LLMClient:
    """
    Thin wrapper around LangChain's ChatOpenAI.
    Provides two clean methods:
      - generate_structured() -> returns a validated Pydantic model
      - generate_text()       -> returns a plain string
    
    To swap to Gemini later, change the import to `from langchain_google_genai import ChatGoogleGenerativeAI`
    and pass its model name. The rest of the codebase stays untouched.
    """

    def __init__(self, api_key: str, model: str = "gpt-5-nano"):
        self.model_name = model
        self.llm = ChatOpenAI(
            model=model,
            api_key=api_key,
            max_retries=2,
        )

    # ── Structured Output ─────────────────────────────────────────

    async def generate_structured(
        self,
        system_prompt: str,
        user_prompt: str,
        response_model: Type[T],
        temperature: float = 0.7,
    ) -> T:
        """
        Uses LangChain's with_structured_output to guarantee a Pydantic model.
        This enforces JSON schema at the API level so the LLM cannot hallucinate 
        random keys or formats.
        """
        structured_llm = self.llm.with_structured_output(
            response_model, method="json_schema"
        )
        # Override temperature per-call
        structured_llm = structured_llm.bind(temperature=temperature)

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ]

        try:
            result = await structured_llm.ainvoke(messages)
            return result
        except Exception as exc:
            logger.exception("Structured generation failed on model=%s", self.model_name)
            raise ValueError(f"LLM structured generation error: {exc}") from exc

    # ── Plain Text Output ─────────────────────────────────────────

    async def generate_text(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.7,
    ) -> str:
        """Standard text completion. Returns the raw content string."""
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ]

        try:
            response = await self.llm.ainvoke(
                messages, temperature=temperature
            )
            return response.content
        except Exception as exc:
            logger.exception("Text generation failed on model=%s", self.model_name)
            raise ValueError(f"LLM text generation error: {exc}") from exc
