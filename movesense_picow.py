import aioble
import bluetooth
import machine
import uasyncio as asyncio
import time
from micropython import const
from struct import unpack

from data_queue import ecg_queue, imu_queue, hr_queue

rtc = machine.RTC()

# Movesense series
_MOVESENSE_SERIES = "174630000192"

#Sensor data rate
IMU_RATE = 52 #Data rate for IMU: 13, 26, 52, 104, 208, 416, 833, 1666
ECG_RATE = 125 #Data rate for ECG: 125, 128, 200, 250, 256, 500, 512

# GSP Service and Characteristic UUIDs
_GSP_SERVICE_UUID = bluetooth.UUID("34802252-7185-4d5d-b431-630e7050e8f0")
_GSP_WRITE_UUID = bluetooth.UUID("34800001-7185-4d5d-b431-630e7050e8f0")
_GSP_NOTIFY_UUID = bluetooth.UUID("34800002-7185-4d5d-b431-630e7050e8f0")

# Command IDs from GSP specification
_CMD_HELLO = const(0)
_CMD_SUBSCRIBE = const(1)
_CMD_UNSUBSCRIBE = const(2)


# Onboard LED for status
led = machine.Pin("LED", machine.Pin.OUT)

class MovesenseDevice:
    BYTES_PER_ELEMENT = 4
    def __init__(self, movesense_series=_MOVESENSE_SERIES, name=None, imu_ref=99, hr_ref=98, ecg_ref=97):
        self.ms_series = str(movesense_series)
        self.name = name
        self.imu_ref = imu_ref
        self.hr_ref = hr_ref
        self.ecg_ref = ecg_ref
        self.connection = None
    
    def log(self, msg):
        print(f"[MS{self.ms_series}]: {msg}")
        
    def json_data_format(self):
        self.json_data = {"Movesense series": self.ms_series, 
                          "Movesense name": self.name}
        return self.json_data

    async def connect_ble(self, device):
        try:
            print(f"Connecting device {device} to BLE...")
            self.connection = await device.connect(timeout_ms = 10000)
        except asyncio.TimeoutError:
            print("Failed to connect to device due to timeout")
            return
        print(f"Connected to {device}")
        try:
            self.sensor_service = await self.connection.service(_GSP_SERVICE_UUID)
            self.notify_char = await self.sensor_service.characteristic(_GSP_NOTIFY_UUID)
            self.write_char = await self.sensor_service.characteristic(_GSP_WRITE_UUID)
        except asyncio.TimeoutError:
            print("Timeout discovering services/characteristics")
            return
        if not (self.sensor_service and self.write_char and self.notify_char):
            print("Required service/characteristics not found")
            return
        # Enable notifications
        await self.notify_char.subscribe(notify=True)
        
    async def subscribe_imu(self, sensor, sensor_rate):
        self.imu_sensor = sensor
        sub_cmd = bytearray([_CMD_SUBSCRIBE, self.imu_ref]) + bytearray(f"Meas/{sensor}/{sensor_rate}", "utf-8")        
        self.log(f"Sending {sensor} SUBSCRIBE command: {sub_cmd.hex()}")
        await self.write_char.write(sub_cmd)
    
    async def subscribe_hr(self):
        sub_cmd = bytearray([_CMD_SUBSCRIBE, self.hr_ref]) + bytearray("Meas/HR", "utf-8")
        self.log(f"Sending HR SUBSCRIBE command: {sub_cmd.hex()}")
        await self.write_char.write(sub_cmd)
    
    async def subscribe_ecg(self, sensor_rate):
        sub_cmd = bytearray([_CMD_SUBSCRIBE, self.ecg_ref]) + bytearray(f"Meas/ECG/{sensor_rate}", "utf-8")
        self.log(f"Sending ECG SUBSCRIBE command: {sub_cmd.hex()}")
        await self.write_char.write(sub_cmd)
    
    async def process_notification(self):
        # Subscribe to notifications and process incoming data
        print("Waiting for notifications...")
        duration = 30				# temporary stop the data reading for now
        self.start_time = time.time()
        while self.connection.is_connected():
            try:
                #TODO: temporary using time countdown to stop sensor and disconnect
                elapsed_time = time.time() - self.start_time
                if elapsed_time >= duration:
                    print(f"{duration} seconds elapsed, stopping...")
                    await self.disconnect_ble()
                    break
                data = await self.notify_char.notified(timeout_ms=300)
                if data:
                    ref_code = data[1]
                    if ref_code == self.imu_ref:
                        print("receive imu data!")
                        self._process_imu_data(data)
                    elif ref_code == self.ecg_ref:
                        print("receive ecg data")
                        self._process_ecg_data(data)
                    elif ref_code == self.hr_ref:
                        print("receive hr data")
                        self._process_hr_data(data)
                    else:
                        print("Unclassified data")
                    
            except asyncio.TimeoutError:
                continue
                
    def _process_imu_data(self, data):
        sensor_type = {
            "IMU6": 2,
            "IMU9": 3
            }
        json_data = {}
        json_data.update(self.json_data_format())
        sample_count = len(data[6:]) // MovesenseDevice.BYTES_PER_ELEMENT
        data = list(unpack(f'<BBI{sample_count}f', data))
        timestamp = data[2]
        sensordata = [round(v, 3) for v in data[3:]]
        sensordata = list(zip(sensordata[::3], sensordata[1::3], sensordata[2::3]))
        print(f"sensor {self.imu_sensor} data {sensordata}")
        sensor_count = sensor_type.get(self.imu_sensor, 3)
        samples_per_sensor = len(sensordata) // sensor_count
        imu_samples = []
        for i in range(samples_per_sensor):
            if self.imu_sensor == "IMU6":
                acc = sensordata[i]
                gyro = sensordata[i + samples_per_sensor]
                sample = [timestamp, acc[0], acc[1], acc[2], gyro[0], gyro[1], gyro[2]]
            elif self.imu_sensor == "IMU9":
                acc = sensordata[i]
                gyro = sensordata[i + samples_per_sensor]
                magn = sensordata[i + samples_per_sensor * 2]
                sample = [timestamp, acc[0], acc[1], acc[2], gyro[0], gyro[1], gyro[2], magn[0], magn[1], magn[2]]
            imu_samples.append(sample)
        self.log(f"{self.imu_sensor} - Timestamp: {timestamp}, samples {imu_samples}")
        #NEED TO PROCESS DATA TO PUT IN JSON 
        # imu_queue.enqueue(json_data)
        
    def _process_hr_data(self, data):
        # < = little endian
        # B = unsigned char (1 byte)
        # B = unsigned char (1 byte)
        # f = float (4 bytes)
        # H = uint16 (2 bytes)
        json_data = {}
        data_unpack = list(unpack(f'<BBfH', data))
        avg_hr = data_unpack[2]
        rr_interval = data_unpack[3]
        self.log(f"HR data: ts {time.time()} avg_hr {avg_hr}, rr_interval {rr_interval}")
        json_data.update(self.json_data_format())
        json_data["UTCTimestamp"] = rtc.datetime()
        json_data["average"] = avg_hr
        json_data["rrData"] = [rr_interval]
#         hr_queue.enqueue(json_data)
        
    def _process_ecg_data(self, data):
        sample_count = len(data[6:]) // MovesenseDevice.BYTES_PER_ELEMENT
        # < = little endian, B = unsigned char
        # I = unsigned int, i = signed int, f = float
        json_data = {}
        json_data.update(self.json_data_format())
        data = list(unpack(f'<BBI{sample_count}i', data))
        ts = data[2]
        sensordata = data[3:]
        json_data["UTCTimestamp"] = rtc.datetime()
        json_data["Samples"] = sensordata
        json_data["Timestamp"] = ts
        # self.log(f"ecg: ts {ts}, samples data {sensordata}")
        self.log(json_data)
        # ecg_queue.enqueue(json_data)
        
        # samples = len(sensordata)
        # ecg_samples = []
        # for i in range(samples):
        #     sample = [ts, sensordata[i]]
        #     ecg_samples.append(sample)
        # self.log(f"ECG - ts: {ts}, samples {ecg_samples}")
                
    async def disconnect_ble(self):
        unsub_cmd = [
            bytearray([_CMD_UNSUBSCRIBE, self.imu_ref]),
            bytearray([_CMD_UNSUBSCRIBE, self.hr_ref]),
            bytearray([_CMD_UNSUBSCRIBE, self.ecg_ref])
            ]
        if self.connection.is_connected():
            self.log("Unsubscribing data...")
            for cmd in unsub_cmd:
                await self.write_char.write(cmd)
                await asyncio.sleep_ms(100)
            await self.connection.disconnect()
            self.log("Disconnected")
        
async def find_movesense(ms_series):
    """Scan for Movesense sensor advertising the GSP service."""
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
    await ms.subscribe_imu("IMU9", IMU_RATE)
    await ms.subscribe_hr()
    await ms.subscribe_ecg(ECG_RATE)
    
    await ms.process_notification()

async def blink_task():
    """Blink LED to indicate connection status."""
    toggle = True
    while True:
        led.value(toggle)
        toggle = not toggle
        await asyncio.sleep_ms(500)


async def main():
    """Run peripheral and blink tasks concurrently."""
    tasks = [
        asyncio.create_task(movesense_task()),
        asyncio.create_task(blink_task())
    ]
    await asyncio.gather(*tasks)


# Run the main coroutine
asyncio.run(main())

