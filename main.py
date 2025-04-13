import uasyncio as asyncio
import machine
import time
from wifi_connection import connect_wifi
from data_queue import state
from movesense_controller import movesense_task, blink_task
from led import Led
from gnss_device import GNSSDevice, gnss_task

SW_0_PIN = 9
SW_1_PIN = 8
SW_2_PIN = 7
LED1 = 22
LED2 = 21
LED3 = 20

# led1 = machine.Pin(LED1, machine.Pin.OUT)
led1 = Led(LED1)
button = machine.Pin(SW_1_PIN, machine.Pin.IN, machine.Pin.PULL_UP)
button_pressed = False
last_pressed_btn = 0
DEBOUNCE_MS = 500

def button_handler(pin):
    global last_pressed_btn
    current_time = time.ticks_ms()
    if time.ticks_diff(current_time, last_pressed_btn) > DEBOUNCE_MS:
        state.running_state = not state.running_state
        # print(f"Button pressed. Running state {state.running_state}")
        last_pressed_btn = current_time

async def running_state_on_led():
    while True:
        led1.led_on() if state.running_state else led1.led_off()
        await asyncio.sleep_ms(500)

async def main():
    try:
        # await connect_wifi()
        await asyncio.gather(
            movesense_task(),
            # gnss_task,
            blink_task(),
            running_state_on_led()
        )
    except Exception as e:
        print(f"Error: {e}")
    finally:
        print("Shutting down event loop...")
        loop = asyncio.get_event_loop()
        loop.stop()  # Stops event loop gracefully

button.irq(trigger=machine.Pin.IRQ_FALLING, handler=button_handler)

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
