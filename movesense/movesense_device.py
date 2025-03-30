import time
import bluetooth
import uasyncio as asyncio
from micropython import const
from struct import unpack
from movesense.data_queue import ecg_queue, imu_queue, hr_queue
import machine  

rtc = machine.RTC()

# GSP Service and Characteristic UUIDs
_GSP_SERVICE_UUID = bluetooth.UUID("34802252-7185-4d5d-b431-630e7050e8f0")
_GSP_WRITE_UUID = bluetooth.UUID("34800001-7185-4d5d-b431-630e7050e8f0")
_GSP_NOTIFY_UUID = bluetooth.UUID("34800002-7185-4d5d-b431-630e7050e8f0")

# Command IDs
_CMD_HELLO = const(0)
_CMD_SUBSCRIBE = const(1)
_CMD_UNSUBSCRIBE = const(2)


class MovesenseDevice:
    BYTES_PER_ELEMENT = 4

    def __init__(self, movesense_series, imu_ref=99, hr_ref=98, ecg_ref=97):
        self.ms_series = str(movesense_series)
        self.imu_ref = imu_ref
        self.hr_ref = hr_ref
        self.ecg_ref = ecg_ref
        self.connection = None
        self.sensor_service = None
        self.write_char = None
        self.notify_char = None

    def log(self, msg):
        print(f"[Movesense {self.ms_series}]: {msg}")

    async def connect_ble(self, device):
        try:
            self.log(f"Connecting to BLE device {device}...")
            self.connection = await device.connect(timeout_ms=10000)
        except asyncio.TimeoutError:
            self.log("Connection timeout")
            return
        self.log("Connected")

        try:
            self.sensor_service = await self.connection.service(_GSP_SERVICE_UUID)
            self.notify_char = await self.sensor_service.characteristic(_GSP_NOTIFY_UUID)
            self.write_char = await self.sensor_service.characteristic(_GSP_WRITE_UUID)
        except asyncio.TimeoutError:
            self.log("Timeout discovering services/characteristics")
            return

        if not (self.sensor_service and self.write_char and self.notify_char):
            self.log("Required service/characteristics not found")
            return

        await self.notify_char.subscribe(notify=True)

    async def subscribe_sensor(self, sensor_type, sensor_rate=None):
        if sensor_type == "IMU":
            cmd = bytearray([_CMD_SUBSCRIBE, self.imu_ref]) + bytearray(f"Meas/IMU9/{sensor_rate}", "utf-8")
        elif sensor_type == "HR":
            cmd = bytearray([_CMD_SUBSCRIBE, self.hr_ref]) + bytearray("Meas/HR", "utf-8")
        elif sensor_type == "ECG":
            cmd = bytearray([_CMD_SUBSCRIBE, self.ecg_ref]) + bytearray(f"Meas/ECG/{sensor_rate}", "utf-8")
        else:
            self.log("Invalid sensor type")
            return
        
        self.log(f"Subscribing to {sensor_type} with command: {cmd.hex()}")
        await self.write_char.write(cmd)

    async def process_notification(self):
        self.log("Waiting for notifications...")
        start_time = time.time()
        duration = 30  # Stop after 30 seconds

        while self.connection.is_connected():
            if time.time() - start_time >= duration:
                self.log("Stopping after 30 seconds...")
                await self.disconnect_ble()
                break

            try:
                data = await self.notify_char.notified(timeout_ms=300)
                if data:
                    ref_code = data[1]
                    if ref_code == self.imu_ref:
                        self.log("IMU data received")
                        self._process_imu_data(data)
                    elif ref_code == self.ecg_ref:
                        self.log("ECG data received")
                        self._process_ecg_data(data)
                    elif ref_code == self.hr_ref:
                        self.log("HR data received")
                        self._process_hr_data(data)
                    else:
                        self.log("Unknown data received")
            except asyncio.TimeoutError:
                continue

    def _process_imu_data(self, data):
        sample_count = len(data[6:]) // self.BYTES_PER_ELEMENT
        unpacked_data = list(unpack(f'<BBI{sample_count}f', data))
        timestamp = unpacked_data[2]
        sensordata = [round(v, 3) for v in unpacked_data[3:]]
        self.log(f"IMU Timestamp: {timestamp}, Data: {sensordata}")
        imu_queue.enqueue({"timestamp": timestamp, "data": sensordata})

    def _process_hr_data(self, data):
        unpacked_data = list(unpack('<BBfH', data))
        avg_hr = unpacked_data[2]
        rr_interval = unpacked_data[3]
        self.log(f"HR: Avg {avg_hr}, RR Interval {rr_interval}")
        hr_queue.enqueue({"timestamp": time.time(), "avg_hr": avg_hr, "rr_interval": rr_interval})

    def _process_ecg_data(self, data):
        sample_count = len(data[6:]) // self.BYTES_PER_ELEMENT
        unpacked_data = list(unpack(f'<BBI{sample_count}i', data))
        ts = unpacked_data[2]
        sensordata = unpacked_data[3:]
        self.log(f"ECG Timestamp: {ts}, Samples: {sensordata}")
        ecg_queue.enqueue({"timestamp": ts, "samples": sensordata})

    async def disconnect_ble(self):
        unsub_cmds = [
            bytearray([_CMD_UNSUBSCRIBE, self.imu_ref]),
            bytearray([_CMD_UNSUBSCRIBE, self.hr_ref]),
            bytearray([_CMD_UNSUBSCRIBE, self.ecg_ref]),
        ]
        if self.connection and self.connection.is_connected():
            self.log("Unsubscribing from sensors...")
            for cmd in unsub_cmds:
                await self.write_char.write(cmd)
                await asyncio.sleep_ms(100)
            await self.connection.disconnect()
            self.log("Disconnected")

