from collections import deque
import threading
import time

class ClientBuffer:
    def __init__(self, client_id, max_size=10*1024*1024):  # 10MB/客户端
        self.client_id = client_id
        self.buffer = bytearray(max_size)
        self.head = 0
        self.tail = 0
        self.size = max_size
        self.lock = threading.Lock()
        
    def put(self, data: bytes):
        with self.lock:
            data_len = len(data)
            avail = self.size - (self.tail - self.head) % self.size
            if data_len > avail:
                return False  # 缓冲区已满
                
            if self.tail + data_len <= self.size:
                self.buffer[self.tail:self.tail+data_len] = data
            else:
                remain = self.size - self.tail
                self.buffer[self.tail:] = data[:remain]
                self.buffer[:data_len-remain] = data[remain:]
            self.tail = (self.tail + data_len) % self.size
            return True

    def get(self, size=1024):
        with self.lock:
            avail = (self.tail - self.head) % self.size
            if avail == 0:
                return b''
                
            recv_size = min(size, avail)
            if self.head + recv_size <= self.size:
                data = bytes(self.buffer[self.head:self.head+recv_size])
            else:
                part1 = self.buffer[self.head:]
                part2 = self.buffer[:recv_size-len(part1)]
                data = part1 + part2
            self.head = (self.head + recv_size) % self.size
            return data

class BufferManager:
    def __init__(self):
        self.buffers = {}
        self.lock = threading.Lock()
        
    def add_data(self, client_id: str, data: bytes):
        with self.lock:
            if client_id not in self.buffers:
                self.buffers[client_id] = ClientBuffer(client_id)
            self.buffers[client_id].put(data)
    
    def get_client_buffer(self, client_id: str) -> ClientBuffer:
        with self.lock:
            return self.buffers.get(client_id, None) 