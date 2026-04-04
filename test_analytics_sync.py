import asyncio
import logging
from app.services.scheduler.jobs import sync_platform_analytics

logging.basicConfig(level=logging.DEBUG)

if __name__ == "__main__":
    asyncio.run(sync_platform_analytics())
