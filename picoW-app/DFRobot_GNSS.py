# -*- coding: utf-8 -*-
# MicroPython adaptation of DFRobot_GNSS.py from https://github.com/DFRobot/DFRobot_GNSS/blob/master/python/raspberrypi/DFRobot_GNSS.py

import time
from machine import I2C, UART

I2C_MODE  = 0x01
UART_MODE = 0x02

GNSS_DEVICE_ADDR = 0x20


# Register addresses
I2C_YEAR_H = 0
I2C_YEAR_L = 1
I2C_MONTH = 2
I2C_DATE = 3
I2C_HOUR = 4
I2C_MINUTE = 5
I2C_SECOND = 6
I2C_LAT_1 = 7
I2C_LAT_2 = 8
I2C_LAT_X_24 = 9
I2C_LAT_X_16 = 10
I2C_LAT_X_8 = 11
I2C_LAT_DIS = 12
I2C_LON_1 = 13
I2C_LON_2 = 14
I2C_LON_X_24 = 15
I2C_LON_X_16 = 16
I2C_LON_X_8 = 17
I2C_LON_DIS = 18
I2C_USE_STAR = 19
I2C_ALT_H = 20
I2C_ALT_L = 21
I2C_ALT_X = 22
I2C_SOG_H = 23
I2C_SOG_L = 24
I2C_SOG_X = 25
I2C_COG_H = 26
I2C_COG_L = 27
I2C_COG_X = 28
I2C_START_GET = 29
I2C_ID = 30
I2C_DATA_LEN_H = 31
I2C_DATA_LEN_L = 32
I2C_ALL_DATA = 33
I2C_GNSS_MODE = 34
I2C_SLEEP_MODE = 35
I2C_RGB_MODE = 36

# Constants
ENABLE_POWER = 0
DISABLE_POWER = 1
RGB_ON = 0x05
RGB_OFF = 0x02
GPS = 1
BeiDou = 2
GPS_BeiDou = 3
GLONASS = 4
GPS_GLONASS = 5
BeiDou_GLONASS = 6
GPS_BeiDou_GLONASS = 7


class struct_utc_tim:
    def __init__(self):
        self.year = 2000
        self.month = 1
        self.date = 1
        self.hour = 0
        self.minute = 0
        self.second = 0

class struct_lat_lon:
    def __init__(self):
        self.lat_dd = 0
        self.lat_mm = 0
        self.lat_mmmmm = 0
        self.lat_direction = "S"
        self.latitude_degree = 0.00
        self.latitude = 0.00
        self.lon_ddd = 0
        self.lon_mm = 0
        self.lon_mmmmm = 0
        self.lon_direction = "W"
        self.lonitude = 0.00
        self.lonitude_degree = 0.00

utc = struct_utc_tim()
lat_lon = struct_lat_lon()


class DFRobot_GNSS:
    def __init__(self, gnss_id=1, bus=0, baudrate=9600, i2c_addr=GNSS_DEVICE_ADDR, uart_port=1, i2c=None):
        self._mode = None
        self._i2c_addr = i2c_addr
        self._txbuf = bytearray(1)
        self.gnss_id = gnss_id

        if i2c is not None:
            self.i2c = i2c
            self._mode = I2C_MODE
        elif bus != 0:
            self.i2c = I2C(bus)
            self._mode = I2C_MODE
        else:
            self.uart = UART(uart_port, baudrate=baudrate, timeout=500)
            self._mode = UART_MODE


    def begin(self):
        rslt = self.read_reg(I2C_ID, 1)
        time.sleep(0.1)
        if rslt == -1:
            return False
        if rslt[0] != GNSS_DEVICE_ADDR:
            return False
        return True

    def get_gnss_id(self):
        return self.gnss_id

    def get_date(self):
        rslt = self.read_reg(I2C_YEAR_H, 4)
        if rslt != -1:
            utc.year = rslt[0]*256 + rslt[1]
            utc.month = rslt[2]
            utc.date = rslt[3]
        return utc

    def get_utc(self):
        rslt = self.read_reg(I2C_HOUR, 3)
        if rslt != -1:
            utc.hour = rslt[0]
            utc.minute = rslt[1]
            utc.second = rslt[2]
        return utc

    def get_lat(self):
        rslt = self.read_reg(I2C_LAT_1, 6)
        if rslt != -1:
            lat_lon.lat_dd = rslt[0]
            lat_lon.lat_mm = rslt[1]
            lat_lon.lat_mmmmm = rslt[2]*65536 + rslt[3]*256 + rslt[4]
            lat_lon.lat_direction = chr(rslt[5])
            lat_lon.latitude = lat_lon.lat_dd*100.0 + lat_lon.lat_mm + lat_lon.lat_mmmmm/100000.0
            lat_lon.latitude_degree = lat_lon.lat_dd + lat_lon.lat_mm/60.0 + lat_lon.lat_mmmmm/100000.0/60.0
        return lat_lon

    def get_lon(self):
        rslt = self.read_reg(I2C_LON_1, 6)
        if rslt != -1:
            lat_lon.lon_ddd = rslt[0]
            lat_lon.lon_mm = rslt[1]
            lat_lon.lon_mmmmm = rslt[2]*65536 + rslt[3]*256 + rslt[4]
            lat_lon.lon_direction = chr(rslt[5])
            lat_lon.lonitude = lat_lon.lon_ddd*100.0 + lat_lon.lon_mm + lat_lon.lon_mmmmm/100000.0
            lat_lon.lonitude_degree = lat_lon.lon_ddd + lat_lon.lon_mm/60.0 + lat_lon.lon_mmmmm/100000.0/60.0
        return lat_lon

    def get_num_sta_used(self):
        rslt = self.read_reg(I2C_USE_STAR, 1)
        return rslt[0] if rslt != -1 else 0

    def get_alt(self):
        rslt = self.read_reg(I2C_ALT_H, 3)
        return rslt[0]*256 + rslt[1] + rslt[2]/100.0 if rslt != -1 else 0.0

    def get_cog(self):
        rslt = self.read_reg(I2C_COG_H, 3)
        return rslt[0]*256 + rslt[1] + rslt[2]/100.0 if rslt != -1 else 0.0

    def get_sog(self):
        rslt = self.read_reg(I2C_SOG_H, 3)
        return rslt[0]*256 + rslt[1] + rslt[2]/100.0 if rslt != -1 else 0.0

    def get_gnss_mode(self):
        rslt = self.read_reg(I2C_GNSS_MODE, 1)
        return rslt[0] if rslt != -1 else 0

    def set_gnss(self, mode):
        self._txbuf[0] = mode
        self.write_reg(I2C_GNSS_MODE, self._txbuf)
        time.sleep(0.1)

    def enable_power(self):
        self._txbuf[0] = ENABLE_POWER
        self.write_reg(I2C_SLEEP_MODE, self._txbuf)
        time.sleep(0.1)

    def disable_power(self):
        self._txbuf[0] = DISABLE_POWER
        self.write_reg(I2C_SLEEP_MODE, self._txbuf)
        time.sleep(0.1)

    def rgb_on(self):
        self._txbuf[0] = RGB_ON
        self.write_reg(I2C_RGB_MODE, self._txbuf)
        time.sleep(0.1)

    def rgb_off(self):
        self._txbuf[0] = RGB_OFF
        self.write_reg(I2C_RGB_MODE, self._txbuf)
        time.sleep(0.1)

    def get_gnss_len(self):
        self._txbuf[0] = 0x55
        self.write_reg(I2C_START_GET, self._txbuf)
        time.sleep(0.1)
        rslt = self.read_reg(I2C_DATA_LEN_H, 2)
        return rslt[0]*256 + rslt[1] if rslt != -1 else 0

    def get_all_gnss(self):
        length = self.get_gnss_len()
        time.sleep(0.1)
        all_data = bytearray(length + 1)
        for offset in range(0, length, 32):
            size = min(32, length - offset)
            chunk = self.read_reg(I2C_ALL_DATA, size)
            if chunk != -1:
                all_data[offset:offset+size] = bytes((b if b != 0 else 0x0A) for b in chunk)
        return all_data

    def write_reg(self, reg, data):
        if self._mode == I2C_MODE:
            while True:
                try:
                    self.i2c.writeto_mem(self._i2c_addr, reg, data)
                    return
                except OSError:
                    print("Check GNSS connection!")
                    time.sleep(1)
        else:
            send = bytearray([reg | 0x80, data[0]])
            self.uart.write(send)

    def read_reg(self, reg, length):
        if self._mode == I2C_MODE:
            try:
                return list(self.i2c.readfrom_mem(self._i2c_addr, reg, length))
            except OSError:
                return -1
        else:
            self.uart.write(bytearray([reg & 0x7F, length]))
            time.sleep(0.05)
            start_time = time.ticks_ms()
            while time.ticks_diff(time.ticks_ms(), start_time) < 1000:
                if self.uart.any():
                    recv = self.uart.read(length)
                    return list(recv)
            return -1



