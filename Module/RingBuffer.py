from collections import deque
import threading
import time

class ClientBuffer:
    def __init__(self, client_id, max_size=10*1024*1024):  # 10MB/客户端
        self.client_id = client_id
        self.buffer = deque(maxlen=max_size)
        self.lock = threading.Lock()
        self.last_update = time.time()
        
    def put(self, data: bytes):
        with self.lock:
            self.buffer.extend(data)
            self.last_update = time.time()

    def get(self, size=1024):
        with self.lock:
            # 获取并删除已读取数据
            if size >= len(self.buffer):
                data = bytes(self.buffer)
                self.buffer.clear()
            else:
                data = bytes(list(self.buffer)[-size:])
                for _ in range(size):
                    self.buffer.popleft()
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