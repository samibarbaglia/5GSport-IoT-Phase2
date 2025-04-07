import uasyncio as asyncio
import machine
from wifi_connection import connect_wifi
from data_queue import running_state
from movesense.movesense_controller import movesense_task, blink_task
from gnss.gnss_device import GNSSDevice, gnss_task

SW_0_PIN = 9
SW_1_PIN = 8
SW_2_PIN = 7

button = machine.Pin(SW_1_PIN, machine.Pin.IN, machine.Pin.PULL_UP)
button_pressed = False

async def main():
    # button.irq(trigger=machine.Pin.IRQ_RISING, handler=button_handler)
    try:
        # await connect_wifi()
        await asyncio.gather(
            movesense_task(),
            # gnss_task,
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
    print("Start running...")
    loop.run_forever()
except KeyboardInterrupt:
    print("Stopped by user")
finally:
    loop.close()
