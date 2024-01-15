import concurrent.futures 
import asyncio
from asyncio import coroutines, futures

main_event_loop = None

def set_main_event_loop(loop):
    global main_event_loop
    main_event_loop = loop

def run_in_main_event_loop(coro):
    return run_coroutine_threadsafe(coro, main_event_loop)

def run_until_complete(coro):
    global main_event_loop
    main_event_loop.run_until_complete(coro)

def run_coroutine_threadsafe(coro, loop):
    """Submit a coroutine object to a given event loop.
        Return a concurrent.futures.Future to access the result.
    """
    if not coroutines.iscoroutine(coro):
        raise TypeError('A coroutine object is required')
    future = concurrent.futures.Future()

    def callback():
        try:
            futures._chain_future(asyncio.ensure_future(coro, loop=loop), future)
        except Exception as exc:
            if future.set_running_or_notify_cancel():
                future.set_exception(exc)
            raise

    main_event_loop.call_soon_threadsafe(callback)
    return future