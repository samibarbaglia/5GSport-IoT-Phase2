# 🌐 Innovation IoT Project

This project integrates a **Movesense device** with a **Raspberry Pi Pico WH**, forming an IoT system that collects movement and GNSS data and forwards it to an MQTT broker over Wi-Fi.

---

## 📱 movesense-device-app

Firmware application for the **Movesense device**.

### 🔧 Description

The application utilizes the **GATT SensorData protocol** to communicate with a client device (Raspberry Pi Pico WH). It includes a **movement detection feature** and implements power-saving behavior:

- If no movement is detected **and** BLE connection is lost for **60 seconds**, the Movesense device enters **PowerOff mode** to conserve battery.
- The device automatically **wakes from PowerOff** when:
  - Movement is detected, or
  - A BLE connection is re-established.

---

## 🧠 picoW-app

Firmware application for the **Raspberry Pi Pico WH**.

### 🔧 Description

The Pico WH functions as both a **microcontroller** and an **IoT gateway**, performing the following tasks:

- Connects to the Movesense device using the **GATT SensorData service** to retrieve sensor data.
- Reads location data from a **GNSS module** (DFRobot TEL0157).
- Forwards combined data to a pre-configured **MQTT broker** over Wi-Fi.

Tested on **MicroPython firmware v1.22**.

### 📦 Required MicroPython Packages

- `micropython-umqtt.simple`
- `micropython-umqtt.robust`

### 🎛 Features & Usability

| Button | Function                                                |
| ------ | ------------------------------------------------------- |
| `sw_0` | Scan for available Movesense BLE devices                |
| `sw_1` | Start/stop sensor data collection and MQTT transmission |
| `sw_2` | Reconnect to Wi-Fi and the MQTT broker                  |
