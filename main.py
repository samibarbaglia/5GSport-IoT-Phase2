import uasyncio as asyncio
from movesense.movesense_controller import movesense_task, blink_task
from gnss.gnss_sensor import GNSSSensor

async def main():
    try:
        await asyncio.gather(
            movesense_task(),
            blink_task()
        )
    except Exception as e:
        print(f"Error: {e}")
    finally:
        print("Shutting down event loop...")
        loop = asyncio.get_event_loop()
        loop.stop()  # Stops event loop gracefully


# Run the event loop manually
loop = asyncio.get_event_loop()
loop.create_task(main())

try:
    loop.run_forever()
except KeyboardInterrupt:
    print("Stopped by user")
finally:
    loop.close()
