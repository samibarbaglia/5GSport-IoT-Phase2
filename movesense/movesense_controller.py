import aioble
import uasyncio as asyncio
import machine
from movesense.movesense_device import MovesenseDevice
import sys
sys.path.append('/')
from data_queue import running_state

# Movesense series ID
_MOVESENSE_SERIES = "174630000192"

# Sensor Data Rate
IMU_RATE = 52   #Sample rate can be 13, 26, 52, 104, 208, 416, 833, 1666
ECG_RATE = 125  #Sample rate can be 125, 128, 200, 250, 256, 500, 512

# Onboard LED
led = machine.Pin("LED", machine.Pin.OUT)


async def find_movesense(ms_series):
    async with aioble.scan(duration_ms=5000, interval_us=30000, window_us=30000, active=True) as scanner:
        async for result in scanner:
            if result.name() == f"Movesense {ms_series}":
                print("Found Movesense sensor:", result.device)
                return result.device
    print(f"Movesense series {ms_series} not found")
    return None


async def movesense_task(movesense_series=_MOVESENSE_SERIES):
    # while running_state:
    device = await find_movesense(movesense_series)
    if not device:
        return

    ms = MovesenseDevice(movesense_series)
    await ms.connect_ble(device)
    await ms.subscribe_sensor("IMU9", IMU_RATE)
    await ms.subscribe_sensor("HR")
    await ms.subscribe_sensor("ECG", ECG_RATE)

    await ms.process_notification()


async def blink_task():
    while True:
        led.value(not led.value())
        await asyncio.sleep_ms(500)
