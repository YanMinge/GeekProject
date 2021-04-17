import sys
import time
if sys.version > '3':
    import queue
else:
    import Queue as queue

class frame_data_class():
    def __init__(self, rx_size, tx_size):
        self.frame_rx_queue = queue.Queue(rx_size)
        self.frame_tx_queue = queue.Queue(tx_size)

    def enqueue(self, item):
        if self.frame_rx_queue.full():
            #print("ble rx queue full")
            self.frame_rx_queue.queue.clear()
        self.frame_rx_queue.put(item)
        #print("enqueue time:", time.process_time())

    def dequeue(self):
        value = None
        if not self.frame_tx_queue.empty():
            value = self.frame_tx_queue.get_nowait()
        return value

    def send(self, item):
        if self.frame_tx_queue.full():
            self.frame_tx_queue.queue.clear()
        self.frame_tx_queue.put(item)

    def recv(self):
        value = None
        if not self.frame_rx_queue.empty():
            try:
                value = self.frame_rx_queue.get_nowait()
            except:
                print("Queue error")
            #print("recv time:", time.process_time())
        return value