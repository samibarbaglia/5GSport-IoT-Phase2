
class Queue:
    """Queue to handle data"""
    def __init__(self, max_len):
        self.queue_list = []
        self.max_len = max_len
    
    def enqueue(self, value):
        self.queue_list.append(value)
        if len(self.queue_list) > self.max_len:
            print("Queue got overloaded, data is removed from queue. Extend queue size to avoid this")
            self.queue_list.pop(0)

    def dequeue(self):
        if len(self.queue_list) != 0:
            return self.queue_list.pop(0)
        return None

    def get_length(self):
        return len(self.queue_list)

    def is_empty(self):
        return len(self.queue_list) == 0

QUEUE_SIZE = 50
ecg_queue = Queue(QUEUE_SIZE)
imu_queue = Queue(QUEUE_SIZE)
hr_queue = Queue(QUEUE_SIZE)

# data_queue.enqueue(1)
# data_queue.enqueue(2)
# data_queue.enqueue(3)
# data_queue.enqueue(4)

# while not data_queue.is_empty():
#     value = data_queue.dequeue()
#     print(value)
    
# import ujson

# data = {"name": "Pico W", "status": "running"}
# data2 = {"abc": 123}
# data2.update(data)
# json_str = ujson.dumps(data2)  # Convert dict to JSON string
# print(json_str)

# parsed_data = ujson.loads(json_str)  # Convert JSON string back to dict
# print(parsed_data["name"])