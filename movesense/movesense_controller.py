import aioble
import uasyncio as asyncio
import machine
from movesense.movesense_device import MovesenseDevice

# Movesense series ID
_MOVESENSE_SERIES = "174630000197"

# Sensor Data Rate
IMU_RATE = 52
ECG_RATE = 125

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


async def movesense_task():
    device = await find_movesense(_MOVESENSE_SERIES)
    if not device:
        return

    ms = MovesenseDevice(_MOVESENSE_SERIES)
    await ms.connect_ble(device)
    await ms.subscribe_sensor("IMU", IMU_RATE)
    await ms.subscribe_sensor("HR")
    await ms.subscribe_sensor("ECG", ECG_RATE)

    await ms.process_notification()


async def blink_task():
    while True:
        led.value(not led.value())
        await asyncio.sleep_ms(500)
