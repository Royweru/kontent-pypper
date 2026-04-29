"""
Utilities for enforcing server-side publish scope.
"""

from __future__ import annotations

from fastapi import HTTPException


def build_scoped_content_map(
    *,
    requested_platforms: list[str],
    platform_specific_content: dict[str, str],
    original_content: str,
) -> tuple[list[str], dict[str, str]]:
    """
    Normalize selected platforms and ensure payload content cannot target unselected platforms.
    """
    if not requested_platforms:
        raise HTTPException(status_code=400, detail="At least one platform must be selected.")

    normalized_platforms: list[str] = []
    for platform in requested_platforms:
        key = str(platform or "").strip().lower()
        if not key:
            raise HTTPException(status_code=400, detail="Platform names cannot be empty.")
        if key not in normalized_platforms:
            normalized_platforms.append(key)

    provided_map = {
        str(platform or "").strip().lower(): content
        for platform, content in (platform_specific_content or {}).items()
        if str(platform or "").strip()
    }
    unknown_payload_platforms = sorted(set(provided_map.keys()) - set(normalized_platforms))
    if unknown_payload_platforms:
        raise HTTPException(
            status_code=400,
            detail=(
                "platform_specific_content contains unselected platforms: "
                + ", ".join(unknown_payload_platforms)
            ),
        )

    content_map = {
        platform: provided_map.get(platform, original_content)
        for platform in normalized_platforms
    }
    return normalized_platforms, content_map
