import uasyncio as asyncio
import machine
import time

from config import (SW_0_PIN, SW_1_PIN, SW_2_PIN, LED1, LED2, LED3)

from wifi_connection import connect_wifi
from data_queue import state
from movesense_controller import movesense_task, blink_task
from led import Led
from mqtt import connect_mqtt, publish_to_mqtt
from GNSS_sensor import set_up_gnss_sensor, gnss_task

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

def read_picoW_unique_id():
    id_bytes = machine.unique_id()
    picoW_id = id_bytes.hex()
    return picoW_id

async def main():
    try:
        picoW_id = read_picoW_unique_id()
        await set_up_gnss_sensor()
        print(f"PicoW ID is {picoW_id}")
        await connect_wifi()
        mqtt_client = await connect_mqtt()
        await asyncio.gather(
            movesense_task(picoW_id),
            gnss_task(picoW_id),
            publish_to_mqtt(mqtt_client),
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
