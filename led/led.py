from machine import Pin

class Led:
    def __init__(self, pin):
        self.pin = pin
        self.led = Pin(self.pin, Pin.OUT)
    
    def toggle_led(self):
        self.led.value(not self.led.value())
    
    def led_on(self):
        self.led.value(1)
    
    def led_off(self):
        self.led.value(0)

