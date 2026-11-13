
import asyncio
import threading
import time

import pytest


def blocking_processing():
    time.sleep(0.2)
    return threading.get_ident()


@pytest.mark.asyncio
async def test_to_thread_keeps_event_loop_responsive():
    event_loop_thread = threading.get_ident()

    processing_task = asyncio.create_task(
        asyncio.to_thread(blocking_processing)
    )

    # This coroutine should execute while processing is running.
    await asyncio.sleep(0.02)

    assert not processing_task.done()

    processing_thread = await processing_task

    assert processing_thread != event_loop_thread


@pytest.mark.asyncio
async def test_processing_semaphore_limits_concurrency():
    semaphore = asyncio.Semaphore(2)

    active_tasks = 0
    max_active_tasks = 0

    async def process():
        nonlocal active_tasks, max_active_tasks

        async with semaphore:
            active_tasks += 1
            max_active_tasks = max(max_active_tasks, active_tasks)

            await asyncio.sleep(0.05)

            active_tasks -= 1

    await asyncio.gather(
        *(process() for _ in range(6))
    )

    assert max_active_tasks == 2
