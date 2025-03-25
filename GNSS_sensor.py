import time
import machine
import ubinascii
import ustruct
import json

# I2C setup (GPIO 4 and 5 on Raspberry Pi Pico)
i2c = machine.I2C(0, scl=machine.Pin(5), sda=machine.Pin(4), freq=115200)

GNSS_ADDR = 0x20

# Calculate checksum
def calculate_checksum(sentence):
    checksum = 0
    for char in sentence:
        checksum ^= ord(char)
    return checksum

# Function to create the command
def create_command():
    command = "$PCAS02,1000*"
    checksum = calculate_checksum(command[1:])  # Skip $
    full_command = f"{command}{checksum:02X}\r\n"
    return full_command

# Function to send command to GNSS
def send_command(command):
    i2c.writeto(GNSS_ADDR, command.encode('utf-8'))

# Function to parse the data
def parse_data(data):
    date = f"{(data[0] << 8 | data[1])}-{data[2]}-{data[3]} {data[4]+2}:{data[5]}:{data[6]}"
    lat = f"{data[7]}.{(data[8] + (data[9] << 16 | data[10] << 8 | data[11])) / 60} {chr(data[18])}"
    lon = f"{data[13]}.{(data[14] + (data[15] << 16 | data[16] << 8 | data[17])) / 60} {chr(data[12])}"

    return date, lat, lon

# Main loop
def main():
    send_command(create_command())

    while True:
        i2c.writeto(GNSS_ADDR, bytearray([0]))  # Send read address
        data = i2c.readfrom(GNSS_ADDR, 50)  # Read 50 bytes of data
        
        date, lat, lon = parse_data(data)

        # Create JSON object
        json_data = {
            "date": date,
            "lat": lat,
            "lon": lon
        }

        # Print JSON
        print(json.dumps(json_data))

        time.sleep(1)

if __name__ == "__main__":
    main()
