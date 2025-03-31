
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