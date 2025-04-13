import network
import time

SSID = ""
PASSWORD = ""
WAITING_FOR_WIFI_CONNECTION_SECONDS = 10

async def connect_wifi(ssid=SSID, password=PASSWORD):
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(ssid, password)
    start_time = time.time()
    while not wlan.isconnected():
        if time.time() - start_time > WAITING_FOR_WIFI_CONNECTION_SECONDS:
            print(f"Can't connect to ssid {ssid}")
            break
        print(f"Connecting wifi...")
        time.sleep(1)
    if wlan.isconnected():
        print("Connected!", wlan.ifconfig())