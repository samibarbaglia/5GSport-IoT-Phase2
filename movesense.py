"""This library contains functions for connecting to Movesense sensors using Bluetooth and subscribing to datastreams using GATT services."""

from bleak import BleakScanner, BleakClient
import asyncio
import numpy as np
import pandas as pd
from struct import unpack
from datetime import datetime
from time import time
from dataclasses import dataclass, field
import contextlib
from enum import Enum, StrEnum, auto
import os

# Defined in the GATT Sensordata app source code
WRITE_UUID = "34800001-7185-4d5d-b431-630e7050e8f0"
NOTIFY_UUID = "34800002-7185-4d5d-b431-630e7050e8f0"

class Command(Enum):
    """GATT Sensordata app commands."""
    HELLO = 0
    SUB = 1
    UNSUB = 2
    # Other commands can send via GATT https://movesense.com/docs/esw/gatt_sensordata_protocol/#commands

class Sensor(StrEnum):
    """All of the Movesense sensors."""
    ACC = auto()
    GYRO = auto()
    MAGN = auto()
    IMU6 = auto()
    IMU9 = auto()
    HR = auto()
    ECG = auto()
    TEMPERATURE = auto()

# CSV headers
COLUMNS = {
    Sensor.ACC: ['Timestamp','AccX','AccY','AccZ'],
    Sensor.GYRO: ['Timestamp','GyroX','GyroY','GyroZ'],
    Sensor.MAGN: ['Timestamp','MagnX','MagnY','MagnZ'],
    Sensor.IMU6: ['Timestamp','AccX','AccY','AccZ','GyroX','GyroY','GyroZ'],
    Sensor.IMU9: ['Timestamp','AccX','AccY','AccZ','GyroX','GyroY','GyroZ','MagnX','MagnY','MagnZ'],
    Sensor.HR: ['average','rrData'],
    Sensor.ECG: ['Timestamp','Sample'],
    Sensor.TEMPERATURE: ['Timestamp','Measurement']
}

@dataclass
class Record:
    """Object to store recorded data to.
    
    Args:
    -
        device_name (str):
            Name of the device used to record this data.
            Used in the CSV filename.
        sensor (Sensor):
            A :class:`Sensor` enumerator.
    """
    device_name: str
    sensor: Sensor
    timestamp: datetime = field(default=datetime.now(), init=False)
    # timestamp_float: float = field(default=time, init=False)
    data: list = field(default_factory=list, init=False)
    
    def __post_init__(self):
        self.columns = COLUMNS[self.sensor]
        if self.sensor == Sensor.IMU9:
            self.sensor_count = 3
        elif self.sensor == Sensor.IMU6:
            self.sensor_count = 2
        elif self.sensor == Sensor.HR:
            self.sensor_count = 2
        elif self.sensor == Sensor.ECG:
            self.sensor_count = 1
        else:
            self.sensor_count = 1
    
    def to_pandas(self):
        """Transforms record data to a pandas :class:`Dataframe`"""
        return pd.DataFrame(self.data, columns=self.columns)
    
    def to_numpy(self):
        """Transforms record to a numpy array"""
        return np.array(self.data)

    def log_data(self, latest_sample):
        print(f"[{self.device_name}|{self.sensor.value}][{time()}]: {latest_sample}")

    def to_csv(self, filepath):
        """Saves the data to a CSV file.
        
        Args:
        -
            filepath (str):
                Absolute or relative path to where the file will be saved to."""
        if not os.path.exists(filepath):
            print('The path doesn\'t Exist. Saving to root folder instead')
            filepath = './'
        
        if filepath[-1] != '/':
            filepath += '/'
        
        file = f'{filepath}{self.device_name}_{self.sensor.value}_{self.timestamp.strftime("%Y-%m-%d_%H-%M-%S")}.csv'
        
        df = self.to_pandas()
        df['Timestamp'] = (df['Timestamp'] - df['Timestamp'][0])
        df.to_csv(file, index=False)
        print(f'File created at: {file}')
    
class MovesenseClient:
    """Client for connecting to Movesense BLE GATT sensordata services.
    
    The client is used as an asynchronous context manager to connect and disconnect automatically.
    
    Args:
    -
        address (str):
            Movesense address
        client_ref (int):
            Client referense used when subscribing to sensordata. Cannot be zero.
            
    Example:
    -
        ```
        import movesense as ms
        import asyncio
        
        device = ms.MovesenseClient(address='0C:8C:DC:3E:57:6B')
        
        async def main():
            async with device as client:
                await client.subscribe(sensor=Sensor.IMU9, samplerate=52, rec_length=60)
                
                await asyncio.sleep(15)
                
                await client.subscribe(sensor=Sensor.IMU9, samplerate=52, rec_length=60)
                
        asyncio.run(main())
        ```
    """
    def __init__(self, address: str, client_ref = 99) -> None:
        self.address = address
        self.name = None
        self.client_ref = client_ref
        self.disconnect_event = asyncio.Event()
        self.bleakclient = BleakClient(self.address, self.disconnected_callback, timeout=60)
        self.recorded_data: list[Record] = []
        self.terminated = False
        
    def get_name(self) -> str:
        """Returns client name"""
        return self.name
    
    def get_address(self) -> str:
        """Returns client address"""
        return self.address
    
    def get_bleak_client(self) -> BleakClient:
        """Returns BleakClient"""
        return self.bleakclient
    
    def get_record(self, index: int = -1) -> Record:
        """Returns a record. If an index isn't given, the last record is returned.
        
        Args:
        -
            index (int):
                Index of the recording."""
        if self.recorded_data:
            return self.recorded_data[index]
        return None
    
    def set_name(self, name: str):
        """Set name manually.
        
        Args:
        -
            name (str):
                Name for the device"""
        self.name = name
        
    async def __aenter__(self):
        await self.bleakclient.connect()
        if self.name == None:
            name = await self.bleakclient.read_gatt_char(17)
            self.name = "ms" + "".join(map(chr, name))[-4:]
        self.log('Connected')
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.bleakclient.is_connected:
            await self.bleakclient.disconnect()
            self.log('Disconnected')
    
    def log(self, message: str):
        """Simple logger function.
        
        Args:
        -
            message (str):
                Message to log."""
        print(f'({self.name}) {message}')
            
    def disconnected_callback(self, client) -> None:
        """Disconnected callback function for BleakClient."""
        self.disconnect_event.set() 
    
    def trigger_unsubscribe(self):
        self.terminated = True
        
    async def subscribe(
        self,
        sensor = Sensor.IMU9, 
        samplerate = 52, 
        rec_length = None,
        start_delay = 5,
        filepath = './',
        save_to_csv = True) -> Record:
        """Subscribe to Movesense sensor data. This should be used with the context manager.
        
        Args:
        -
            sensor (Sensor):
                A :class:`Sensor` enumerator.
            samplerate (int):
                How often sensor data is measured. Value depends on the sensor.
                Movement sensor sample rates: 13, 26, 52, 104, 208, 516.
            rec_length (None|int):
                Recording length in seconds.
            start_delay (int):
                Starts the recording after set delay in seconds.
            filepath (str):
                Location where the CSV files are saved to.
            save_to_csv (bool):
                Option to disable saving data to a CSV file.
        
        Returns:
        - 
            record (Record):
                Recorded data.
        
        Example
        -
        ```
        import movesense as ms
        import asyncio
        
        device = ms.MovesenseClient(address='0C:8C:DC:3E:57:6B')
        
        async def main():
            async with device as client:
                await client.subscribe(sensor=Sensor.IMU9, samplerate=52, rec_length=60)
        asyncio.run(main())
        ```
        """
        
        if not self.bleakclient.is_connected:
            self.log('Error. Client not connected.')
            return
        bleak_client = self.get_bleak_client()
        self.log(f"Bleak client {bleak_client}")
        record = Record(self.name, sensor)
        if sensor in [Sensor.ACC, Sensor.GYRO, Sensor.MAGN, Sensor.IMU6, Sensor.IMU9, Sensor.ECG]:
            sub_data = bytearray([Command.SUB.value, self.client_ref]) + bytearray(f'Meas/{sensor.value}/{samplerate}', 'utf-8')
        elif sensor in Sensor.HR:
            sub_data = bytearray([Command.SUB.value, self.client_ref]) + bytearray(f'Meas/{sensor.value}', 'utf-8')
        unsub_data = bytearray([Command.UNSUB.value, self.client_ref])
        
        
        async def notification_handler(sender , data: bytearray):
            ''''
            Received notifications containing Movesense sensordata. The data
            is unpacked, parsed and saved to a :class:'Record'.
            
            Args:
            -
            sender:
                Required by bleak. Not used.
            data (bytearray):
                :class:`bytearray` received from Movesense in sbem format.
            '''
            
            # Parser
            # Meas API: https://bitbucket.org/movesense/movesense-device-lib/src/master/MovesenseCoreLib/resources/movesense-api/meas/
            # Refer to the API for data types and formatting
            # Bytearray (little endian):
            # - result type [1 byte]: (1 = response to command, 2 = data notification from subscription)
            # - client reference [1 byte]
            # - data: (2 byte "HTTP result" for commands, sbem formatted binary for subscriptions)
            if record.sensor in [Sensor.ACC, Sensor.GYRO, Sensor.MAGN, Sensor.IMU6, Sensor.IMU9]:
                bytes_per_element = 4
                sample_count = len(data[6:]) // bytes_per_element
                
                # Explain the format of the data
                # < = little endian (1 byte)
                # B = unsigned char (1 byte)
                # B = unsigned char (1 byte)
                # f = float (4 bytes) x sample_count
                data = list(unpack(f'<BBI{sample_count}f', data))
                
                ts0 = data[2]
                sensordata = [round(v, 3) for v in data[3:]]
                sensordata = list(zip(sensordata[::3], sensordata[1::3], sensordata[2::3]))
                
                samples_per_sensor = len(sensordata) // record.sensor_count

                
                for i in range(samples_per_sensor):
                    if i == 0:
                        sample = [ts0, *sensordata[i]] # add timestamp only to the first sample
                    else:
                        sample = [float('nan'), *sensordata[i]] 
                        #sample = [ts[i], *sensordata[i]] # ~ sample timestamp
                    if record.sensor in [Sensor.IMU6, Sensor.IMU9]:
                        offset = i + samples_per_sensor
                        sample += sensordata[offset]
                    if record.sensor == Sensor.IMU9:
                        offset = i + samples_per_sensor * 2
                        sample += sensordata[offset]
                    record.data += [sample]
                    record.log_data(sample) # Log the latest sample
            elif record.sensor == Sensor.HR:
                # < = little endian
                # B = unsigned char (1 byte)
                # B = unsigned char (1 byte)
                # f = float (4 bytes)
                # H = uint16 (2 bytes)
                data = list(unpack(f'<BBfH', data))
                row = [round(data[2],1), data[3]]
                record.data += [row]
                record.log_data(row)  # Log the latest row
                        
            elif record.sensor == Sensor.ECG:

                bytes_per_element = 4
                sample_count = len(data[6:]) // bytes_per_element
                
                # < = little endian, B = unsigned char
                # I = unsigned int, i = signed int, f = float
                #data = list(unpack(f'<BBI{sample_count}f', data))
                data = list(unpack(f'<BBI{sample_count}i', data))
                
                ts0 = data[2]
                sensordata = data[3:]
                
                samples = len(sensordata)
                
                for i in range(samples):
                    if i == 0:
                        sample = [ts0, sensordata[i]]
                    else:
                        sample = [float('nan'), sensordata[i]]
                    record.data += [sample]
                    record.log_data(sample)  # Log the latest sample
                        
            elif record.sensor == Sensor.TEMPERATURE:
                pass
            
            if (rec_length is not None and len(record.data) >= rec_length * samplerate) or self.terminated:
                self.disconnect_event.set()
    
                
        self.log(f"Recording starts in {start_delay} seconds")
        await asyncio.sleep(start_delay)
        
        self.log(f'Recording {sensor} @ {samplerate}Hz')
        await self.bleakclient.start_notify(NOTIFY_UUID, notification_handler)
        await self.bleakclient.write_gatt_char(WRITE_UUID, sub_data, response=True)
        
        await self.disconnect_event.wait()
        
        if self.bleakclient.is_connected:
            self.log('Recording complete')
            await self.bleakclient.write_gatt_char(WRITE_UUID, unsub_data, response=True)
            await self.bleakclient.stop_notify(NOTIFY_UUID)

        if save_to_csv:
            record.to_csv(filepath)
        
        self.recorded_data.append(record)
        
        return record

class MovesenseMultiClient:
    """Client for connecting to multiple Movesense devices simultaneously
    
    Args:
    -
        clients (list[MovesenseClient]):
            List of :class:`MovesenseClient` objects.
    """
    def __init__(self, clients: list[MovesenseClient]) -> None:
        self.clients: list[MovesenseClient] = clients
        self.connected_events = [asyncio.Event() for _ in range(len(clients))]
        self.failed_to_connect = asyncio.Event()
        
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass
        
    async def subscribe(
        self,
        sensor = Sensor.IMU9, 
        samplerate = 52, 
        rec_length = 60,
        start_delay = 5,
        filepath = './',
        save_to_csv = True):
        """Connects to multiple Movesense devices and synchronously subscribes to
        sensordata and records it.
        
        Args:
        -
            sensor (Sensor):
                A :class:`Sensor` enumerator.
            samplerate (int):
                How often sensordata is measured. Value depends on the sensor.
                Movement sensor samplerates: 13, 26, 52, 104, 208, 516.
            rec_length (int):
                Recording length in seconds.
            start_delay (int):
                Starts the recording after set delay in seconds.
            filepath (str):
                Location where the CSV files are saved to.
            save_to_csv (bool):
                Option to disable saving data to a CSV file.
                
        Returns:
        -
            records (list[Record]):
                List of records from all of the devices.
        """
        
        async def connect(
            lock: asyncio.Lock,
            connected_event: asyncio.Event,
            device: MovesenseClient,
            sensor: Sensor, 
            samplerate: int, 
            rec_length: int,
            start_delay: int,
            filepath: str,
            save_to_csv: bool):
            """Connects to a Movesense sensor and waits for other devices to connect before subscribing to data.
            
            Args:
            -
                sensor (Sensor):
                    A :class:`Sensor` enumerator.
                samplerate (int):
                    How often sensordata is measured. Value depends on the sensor.
                    Movement sensor samplerates: 13, 26, 52, 104, 208, 516.
                rec_length (int):
                    Recording length in seconds.
                start_delay (int):
                    Starts the recording after set delay in seconds.
                filepath (str):
                    Location where the CSV files are saved to.
                save_to_csv (bool):
                    Option to disable saving data to a CSV file.
            """
            
            try:
                async with contextlib.AsyncExitStack() as stack:
                    async with lock:
                        client = device.bleakclient
                        await stack.enter_async_context(client)
                        name = await client.read_gatt_char(17)
                        if device.name == None:
                            device.name = "ms" + "".join(map(chr, name))[-4:]
                        device.log('Connected')
                    
                    connected_event.set()
                    for event in self.connected_events:
                        await event.wait()
                        
                    if not self.failed_to_connect.is_set():
                        await device.subscribe(sensor, samplerate, rec_length, start_delay, filepath, save_to_csv)
                
                device.log('Disconnected')
            except:
                device.log('Failed to connect')
                connected_event.set()
                self.failed_to_connect.set()
        
        lock = asyncio.Lock()
        await asyncio.gather(
            *(
                connect(lock, connected_event, client, sensor, samplerate, rec_length, start_delay, filepath, save_to_csv)
                for client, connected_event in zip(self.clients, self.connected_events)
            )
        )
        
        records = None
        if not self.failed_to_connect.is_set():
            records = [client.get_record(-1) for client in self.clients]
            
        self.failed_to_connect.clear()
        for event in self.connected_events:
            event.clear()
        
        return records
        
        
        
async def scan(end_of_serial: str | int) -> MovesenseClient | None:
    '''
    Scans for a Movesense sensor with a specific serial number
    
    Args:
    -
        end_of_serial (str | int):
            End of a serial number.
        
    Returns:
        device (Movesense):
            Movesense sensor object
        None:
            Sensor was not found
    '''
    end_of_serial = str(end_of_serial)
    devices = await BleakScanner.discover()
    for d in devices:
        if d.name and d.name.endswith(end_of_serial):
            print("Device found: ", d.name)
            print("Address: ", d.address)
            name = 'MS' + d.name[-4:]
            movesense = MovesenseClient(d.address)
            movesense.set_name(name)
            return movesense
    
    print("Device not found. Make sure the device is in pairing mode.")
    return None
