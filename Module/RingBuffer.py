from collections import deque
import threading
import time

class ClientBuffer:
    """
    客户端缓冲区类
    用于存储单个客户端的数据流,实现环形缓冲区功能
    """
    def __init__(self, client_id, max_size=128*1024*1024):  # 128MB/客户端
        """
        初始化客户端缓冲区
        :param client_id: 客户端标识符
        :param max_size: 缓冲区最大容量,默认128MB
        """
        self.client_id = client_id

        self.buffer = bytearray(max_size)  # 底层字节数组
        self.head = 0  # 读指针位置
        self.tail = 0  # 写指针位置
        self.size = max_size  # 缓冲区总大小
        self.lock = threading.Lock()  # 线程锁,保证线程安全
        
    def put(self, data: bytes):
        """
        写入数据到缓冲区
        :param data: 要写入的字节数据
        :return: 写入成功返回True,缓冲区已满返回False
        """
        with self.lock:
            data_len = len(data)
            # 计算可用空间
            avail = self.size - (self.tail - self.head) % self.size
            if data_len > avail:
                return False  # 缓冲区已满
                
            # 写入数据,处理环形写入的情况
            if self.tail + data_len <= self.size:
                # 不需要回环的情况
                self.buffer[self.tail:self.tail+data_len] = data
            else:
                # 需要回环的情况
                remain = self.size - self.tail
                self.buffer[self.tail:] = data[:remain]  # 写入第一部分
                self.buffer[:data_len-remain] = data[remain:]  # 写入剩余部分
            self.tail = (self.tail + data_len) % self.size
            return True

    def get(self, size=1024):
        """
        从缓冲区读取数据
        :param size: 要读取的字节数,默认1024
        :return: 读取到的字节数据,无数据时返回空bytes
        """
        with self.lock:
            # 计算可读数据量
            avail = (self.tail - self.head) % self.size
            if avail == 0:
                return b''
                
            # 确定实际读取大小
            recv_size = min(size, avail)
            # 读取数据,处理环形读取的情况
            if self.head + recv_size <= self.size:
                # 不需要回环的情况
                data = bytes(self.buffer[self.head:self.head+recv_size])
            else:
                # 需要回环的情况
                part1 = self.buffer[self.head:]
                part2 = self.buffer[:recv_size-len(part1)]
                data = part1 + part2
            self.head = (self.head + recv_size) % self.size
            return data

class BufferManager:
    """
    缓冲区管理器类
    管理多个客户端的缓冲区,提供线程安全的访问接口
    """
    def __init__(self):
        """初始化缓冲区管理器"""
        self.buffers = {}  # 存储所有客户端缓冲区的字典
        self.lock = threading.Lock()  # 线程锁
        
    def add_data(self, client_id: str, data: bytes):
        """
        添加数据到指定客户端的缓冲区
        :param client_id: 客户端标识符
        :param data: 要添加的字节数据
        """
        with self.lock:
            # 如果客户端不存在,则创建新的缓冲区
            if client_id not in self.buffers:
                self.buffers[client_id] = ClientBuffer(client_id)
            self.buffers[client_id].put(data)
    
    def get_client_buffer(self, client_id: str) -> ClientBuffer:
        """
        获取指定客户端的缓冲区
        :param client_id: 客户端标识符
        :return: 客户端缓冲区对象,不存在则返回None
        """
        with self.lock:
            return self.buffers.get(client_id, None) 