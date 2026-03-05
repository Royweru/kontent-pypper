"""
╔══════════════════════════════════════════════════════════════╗
║          CONTENT AUTOMATION PIPELINE — Entry Point           ║
║                                                              ║
║  Usage:                                                      ║
║    python run_pipeline.py              → Full live run        ║
║    python run_pipeline.py --dry-run    → Generate only        ║
║    python run_pipeline.py --dashboard  → Start dashboard      ║
║    python run_pipeline.py --check      → Validate API keys    ║
╚══════════════════════════════════════════════════════════════╝
"""

import asyncio
import sys
import os

# Ensure project root is in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.settings import settings


def main():
    args = sys.argv[1:]

    # ── Check API key configuration ──────────────────────────
    if "--check" in args:
        print("\n[CHECK] Checking API key configuration...\n")
        warnings = settings.validate()
        if warnings:
            for w in warnings:
                print(f"  [!] {w}")
            print(f"\n  {len(warnings)} key(s) not configured")
            print("  Edit .env file to add your API keys\n")
        else:
            print("  [OK] All API keys configured!\n")
        return

    # ── Start dashboard server ───────────────────────────────
    if "--dashboard" in args:
        print("\n[SYS] Starting Content Pipeline Dashboard...")
        print(f"   URL: http://localhost:{settings.DASHBOARD_PORT}\n")

        import uvicorn
        from dashboard.app import app

        uvicorn.run(
            app,
            host=settings.DASHBOARD_HOST,
            port=settings.DASHBOARD_PORT,
        )
        return

    # ── Run the pipeline ─────────────────────────────────────
    dry_run = "--dry-run" in args

    settings.ensure_dirs()

    from pipeline.orchestrator import run_pipeline
    asyncio.run(run_pipeline(dry_run=dry_run))


if __name__ == "__main__":
    main()
