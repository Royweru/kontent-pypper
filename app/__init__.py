# KontentPyper - Autonomous Social Media Content Agent
import sys
import logging

logger = logging.getLogger(__name__)

def _patch_openai_pydantic_bug():
    """
    Monkey-patches the `openai` python package at runtime to fix an incompatibility
    between Pydantic v2.9+ and the OpenAI SDK where `by_alias=None` crashes the C-engine.
    """
    try:
        import openai._compat
        original_model_dump = openai._compat.model_dump

        def patched_model_dump(
            model,
            *,
            exclude=None,
            exclude_unset=False,
            exclude_defaults=False,
            warnings=True,
            mode="python",
            by_alias=None,
        ):
            # Force None to False to avoid PyBool crashes in Pydantic's C-compiled core.
            if by_alias is None:
                by_alias = False
                
            return original_model_dump(
                model,
                exclude=exclude,
                exclude_unset=exclude_unset,
                exclude_defaults=exclude_defaults,
                warnings=warnings,
                mode=mode,
                by_alias=by_alias,
            )
            
        openai._compat.model_dump = patched_model_dump
        logger.info("Successfully patched openai._compat.model_dump bug.")
    except ImportError:
        pass
    except Exception as e:
        logger.warning(f"Failed to patch openai package: {e}")

_patch_openai_pydantic_bug()
