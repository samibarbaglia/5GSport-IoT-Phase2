import asyncio
import movesense as ms

BLE_SCAN_TIMEOUT = 60
END_OF_SERIAL = 192
SENSOR = ms.Sensor.IMU9
SAMPLERATE = 52 # Depends on sensor
REC_LENGTH = 30 # In seconds
START_DELAY = 5 # Wait N seconds after connecting
FILEPATH = "../data/movesense/" # CSV save location (FOLDER MUST EXIST)
sensors = ["IMU9", "HR", "ECG"] 

SAVE_TO_CSV = True # Option to disable saving data to a CSV.
async def main():
    try:
        print("Scanning BLE for Movesense device....")
        device = await asyncio.wait_for(ms.scan(END_OF_SERIAL), timeout=BLE_SCAN_TIMEOUT)
        if device is None:
            print("No Movesense device is found. Stop the program")
            return
        print(f"Found device with address {device.get_address()}")
        
        async with device as client:
            print(f"Subscribing to sensor data of movesense {device}")
            # record = await client.subscribe(
            #                                 sensor=SENSOR, 
            #                                 samplerate=SAMPLERATE, 
            #                                 # rec_length=REC_LENGTH, 
            #                                 start_delay=START_DELAY, 
            #                                 filepath=FILEPATH,
            #                                 save_to_csv=True
            #                             )
            record_task = asyncio.create_task(client.subscribe(
                                            sensor=SENSOR, 
                                            samplerate=SAMPLERATE, 
                                            # rec_length=REC_LENGTH, 
                                            start_delay=START_DELAY, 
                                            filepath=FILEPATH,
                                            save_to_csv=SAVE_TO_CSV
                                        ))
            print(f"Data subscription for IMU9 started.")
            await asyncio.sleep(25)
            device.trigger_unsubscribe()
            
            # Wait for the subscription task to complete
            record = await record_task
            
            df = record.to_pandas()
            print(df.tail(5))
    except asyncio.TimeoutError:
        print("Timeout: No movesense device found within the time limit.")
    except Exception as e:
        print(f"An error occurred: {e}")

asyncio.run(main())