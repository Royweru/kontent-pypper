# app/services/ai/llm_client.py
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
    """

    def __init__(self, model: str = "gpt-4o-mini"):
        self.model_name = model
        self.llm = ChatOpenAI(
            model=model,
            max_retries=2,
        )

    # ── Structured Output ─────────────────────────────────────────

    async def generate_structured(
        self,
        system_prompt: str,
        user_prompt: str,
        response_model: Type[T],
        temperature: float = 1.0,
    ) -> T:
        """
        Uses LangChain's with_structured_output to guarantee a Pydantic model.
        This enforces JSON schema at the API level so the LLM cannot hallucinate 
        random keys or formats.
        """
        structured_llm = self.llm.with_structured_output(
            response_model, method="function_calling"
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
        temperature: float = 1.0,
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
