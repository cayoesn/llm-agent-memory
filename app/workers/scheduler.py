from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.telemetry.logger import logger

scheduler = AsyncIOScheduler()


async def run_memory_decay() -> None:
    """Periodic task to apply decay to memory importance scores."""
    logger.info("scheduler_running_decay")
    # Logic to fetch all memories and apply DecayManager


async def run_reflection_generation() -> None:
    """Periodic task to analyze recent memories and generate insights."""
    logger.info("scheduler_running_reflection")
    # Logic to fetch recent episodic memories and generate ReflectionMemory


def start_scheduler() -> None:
    scheduler.add_job(run_memory_decay, "interval", hours=1)
    scheduler.add_job(run_reflection_generation, "interval", hours=4)
    scheduler.start()
    logger.info("scheduler_started")
