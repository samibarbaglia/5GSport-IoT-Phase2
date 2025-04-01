import time
import machine
import uasyncio as asyncio
# import json
import sys
sys.path.append('/')
from data_queue import gnss_queue, state

class GNSSDevice:
    def __init__(self, device_id=1, i2c_id=0, scl_pin=5, sda_pin=4, freq=115200, address=0x20):
        self.i2c = machine.I2C(i2c_id, scl=machine.Pin(scl_pin), sda=machine.Pin(sda_pin), freq=freq)
        self.address = address
        self.device_id = device_id

    def _calculate_checksum(self, sentence):
        """Calculate NMEA-style checksum."""
        checksum = 0     
        for char in sentence:
            checksum ^= ord(char)
        return checksum

    def _create_command(self):
        """Generate the GNSS command with checksum."""
        command = "$PCAS02,1000*"
        checksum = self._calculate_checksum(command[1:])  # Skip '$'
        return f"{command}{checksum:02X}\r\n"

    def send_command(self):
        """Send the configuration command to the GNSS module."""
        command = self._create_command().encode('utf-8')
        self.i2c.writeto(self.address, command)

    def _parse_data(self, data):
        """Parse raw GNSS data into human-readable format."""
        try:
            date = f"{(data[0] << 8 | data[1])}-{data[2]:02}-{data[3]:02} {data[4]+2:02}:{data[5]:02}:{data[6]:02}"
            lat = f"{data[7]}.{(data[8] + (data[9] << 16 | data[10] << 8 | data[11])) / 60:.6f} {chr(data[18])}"
            lon = f"{data[13]}.{(data[14] + (data[15] << 16 | data[16] << 8 | data[17])) / 60:.6f} {chr(data[12])}"
            return {"GNSS sensor ID": self.device_id, "Date": date, "Latitude": lat, "Longitude": lon}
        except Exception as e:
            print(f"Error parsing GNSS data: {e}")
            return None

    def read_data(self):
        """Read GNSS data over I2C."""
        self.i2c.writeto(self.address, bytearray([0]))  # Request data
        raw_data = self.i2c.readfrom(self.address, 50)  # Read 50 bytes
        self._parse_data(raw_data)
        
gnss_device = GNSSDevice()

async def gnss_task():
    while state.running_state:
        gnss_device.send_command()
        data = gnss_device.read_data()
        if data:
            gnss_queue.enqueue(data)
        await asyncio.sleep_ms(500)