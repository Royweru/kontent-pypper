import pytest

from app.services.ai.enhancer import EnhancerService
from app.services.ai.schemas import EnhancedDraftResponse, PlatformDraft


class _FakeLLM:
    def __init__(self, response=None, error=None):
        self.response = response
        self.error = error
        self.calls = []

    async def generate_structured(self, **kwargs):
        self.calls.append(kwargs)
        if self.error:
            raise self.error
        return self.response


@pytest.mark.anyio
async def test_enhancer_maps_structured_response_to_platform_dict():
    fake = _FakeLLM(
        response=EnhancedDraftResponse(
            drafts=[
                PlatformDraft(platform="Twitter", content="x copy"),
                PlatformDraft(platform="LinkedIn", content="li copy"),
            ],
            suggested_hashtags=["ai", "growth", "creator"],
        )
    )
    svc = EnhancerService()
    svc.llm = fake

    out = await svc.enhance_draft("raw idea", ["twitter", "linkedin"])
    assert out.platforms == {"twitter": "x copy", "linkedin": "li copy"}
    assert out.suggested_hashtags == ["ai", "growth", "creator"]


@pytest.mark.anyio
async def test_enhancer_includes_user_context_in_prompt():
    fake = _FakeLLM(
        response=EnhancedDraftResponse(
            drafts=[PlatformDraft(platform="twitter", content="x")],
            suggested_hashtags=[],
        )
    )
    svc = EnhancerService()
    svc.llm = fake

    await svc.enhance_draft("raw", ["twitter"], user_context="Founder voice; no hype.")
    assert len(fake.calls) == 1
    prompt = fake.calls[0]["user_prompt"]
    assert "ADDITIONAL CONTEXT FROM USER" in prompt
    assert "Founder voice; no hype." in prompt


@pytest.mark.anyio
async def test_enhancer_propagates_llm_failure():
    fake = _FakeLLM(error=ValueError("model timeout"))
    svc = EnhancerService()
    svc.llm = fake

    with pytest.raises(ValueError):
        await svc.enhance_draft("raw", ["twitter"])
