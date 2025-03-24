import network
import time
import json

SSID = ""
PASSWORD = ""

def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(SSID, PASSWORD)
    start_time = time.time()
    while not wlan.isconnected():
        if time.time() - start_time > 10:
            print(f"Can't connect to ssid {SSID}")
            break
        print(f"Connecting wifi...")
        time.sleep(1)
    if wlan.isconnected():
        print("Connected!", wlan.ifconfig())