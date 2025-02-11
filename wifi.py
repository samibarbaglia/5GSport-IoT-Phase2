import network
import time

SSID = "Galaxy_S9"
PASSWORD = "msmy7265"

def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(SSID, PASSWORD)
    
    print("Connected!", wlan.ifconfig())