"""Release-readiness checker for phased rollout and go-live gates."""

from __future__ import annotations

import argparse
import os
import sys


def _truthy(v: str | None) -> bool:
    return str(v or "").strip().lower() in {"1", "true", "yes", "on"}


def _int_env(name: str, default: int) -> int:
    try:
        return int(str(os.getenv(name, str(default))).strip())
    except Exception:
        return default


def _print_group(title: str, items: dict[str, str | bool]) -> None:
    print(title)
    for key, value in items.items():
        print(f"{key}: {value}")


def check(mode: str = "preflight") -> int:
    required = {
        "PAYSTACK_SECRET_KEY": os.getenv("PAYSTACK_SECRET_KEY"),
        "PAYSTACK_PUBLIC_KEY": os.getenv("PAYSTACK_PUBLIC_KEY"),
        "PAYSTACK_PLAN_PRO": os.getenv("PAYSTACK_PLAN_PRO"),
        "PAYSTACK_PLAN_MAX": os.getenv("PAYSTACK_PLAN_MAX"),
        "PEXELS_API_KEY": os.getenv("PEXELS_API_KEY"),
        "R2_ACCOUNT_ID": os.getenv("R2_ACCOUNT_ID"),
        "R2_ACCESS_KEY_ID": os.getenv("R2_ACCESS_KEY_ID"),
        "R2_SECRET_ACCESS_KEY": os.getenv("R2_SECRET_ACCESS_KEY"),
        "R2_PUBLIC_DEV_URL": os.getenv("R2_PUBLIC_DEV_URL"),
    }
    optional = {
        "PAYSTACK_CALLBACK_URL": os.getenv("PAYSTACK_CALLBACK_URL"),
        "PAYSTACK_CANCEL_URL": os.getenv("PAYSTACK_CANCEL_URL"),
        "PAYSTACK_MANAGE_URL": os.getenv("PAYSTACK_MANAGE_URL"),
    }

    print("=== Release Readiness Check ===")
    for key, value in required.items():
        state = "OK" if str(value or "").strip() else "MISSING"
        print(f"{key}: {state}")

    print("--- Optional URL Overrides ---")
    for key, value in optional.items():
        state = "SET" if str(value or "").strip() else "DEFAULTED"
        print(f"{key}: {state}")

    canary = _int_env("ROLLOUT_CANARY_PERCENT", 100)
    flags = {
        "FEATURE_REAL_VIDEO_PIPELINE": _truthy(os.getenv("FEATURE_REAL_VIDEO_PIPELINE")),
        "FEATURE_PAYSTACK_BILLING": _truthy(os.getenv("FEATURE_PAYSTACK_BILLING")),
        "FEATURE_AI_ENHANCER_GUARDRAILS": _truthy(os.getenv("FEATURE_AI_ENHANCER_GUARDRAILS")),
        "ROLLOUT_CANARY_PERCENT": canary,
        "MODE": mode,
    }
    _print_group("--- Flags ---", flags)

    errors: list[str] = []
    warnings: list[str] = []

    missing = [k for k, v in required.items() if not str(v or "").strip()]
    if missing:
        errors.append(f"Missing {len(missing)} required environment variables: {', '.join(missing)}")

    if not (0 <= canary <= 100):
        errors.append("ROLLOUT_CANARY_PERCENT must be between 0 and 100.")

    if mode == "go-live":
        if not flags["FEATURE_REAL_VIDEO_PIPELINE"]:
            errors.append("FEATURE_REAL_VIDEO_PIPELINE must be enabled for go-live.")
        if not flags["FEATURE_PAYSTACK_BILLING"]:
            errors.append("FEATURE_PAYSTACK_BILLING must be enabled for go-live.")
        if canary == 0:
            errors.append("ROLLOUT_CANARY_PERCENT cannot be 0 in go-live mode.")
    else:
        if not flags["FEATURE_REAL_VIDEO_PIPELINE"]:
            warnings.append("FEATURE_REAL_VIDEO_PIPELINE is disabled; rollout will not generate real videos.")
        if not flags["FEATURE_PAYSTACK_BILLING"]:
            warnings.append("FEATURE_PAYSTACK_BILLING is disabled; checkout and webhook processing are paused.")

    if warnings:
        print("--- Warnings ---")
        for item in warnings:
            print(f"- {item}")

    if errors:
        print("--- Errors ---")
        for item in errors:
            print(f"- {item}")
        print("FAILED: Release readiness checks did not pass.")
        return 1

    print("PASSED: Release readiness checks passed.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Check rollout and go-live readiness.")
    parser.add_argument(
        "--mode",
        choices=["preflight", "go-live"],
        default="preflight",
        help="Use go-live to enforce strict production gates.",
    )
    args = parser.parse_args()
    return check(mode=args.mode)


if __name__ == "__main__":
    sys.exit(main())
