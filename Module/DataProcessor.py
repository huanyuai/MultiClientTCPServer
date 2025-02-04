import json
import struct
import time
from PyQt5.QtCore import pyqtSignal, QObject

class DataParser:
    @staticmethod
    def detect_type(data: bytes) -> str:
        """更精确的数据类型检测"""
        try:
            # 优先检测文本
            text = data.decode('utf-8')
            if all(31 < c < 127 or c in (9,10,13) for c in data):  # 可打印ASCII字符
                return 'text'
            return 'hex'
        except UnicodeDecodeError:
            return 'hex'

class DataProcessor(QObject):
    update_signal = pyqtSignal(str)  # (格式化后的消息)
    
    def __init__(self, buffer_manager):
        super().__init__()
        self.buffer_manager = buffer_manager
        self.running = True
        self.last_process = {}
        self.display_options = {
            'show_time': True,
            'show_client': True
        }
        
    def start_processing(self):
        while self.running:
            processed = False
            for client_id, buffer in self.buffer_manager.buffers.items():
                raw_data = buffer.get(4096)  # 每次获取4KB
                if raw_data:
                    self._process(client_id, raw_data)
                    processed = True
            if not processed:
                time.sleep(0.1)  # 无数据时休眠更久
            
    def _process(self, client_id, data):
        # 添加调试信息
        print(f"[处理] {client_id} 收到 {len(data)}字节")
        
        # 处理间隔限制
        if time.time() - self.last_process.get(client_id, 0) < 0.1:
            return
        self.last_process[client_id] = time.time()

        # 解析数据类型
        data_type = self._detect_data_type(data)
        
        # 生成显示内容
        display_msg = self._format_display(data_type, data, client_id)
        
        # 解析地址
        try:
            ip, port = client_id.split(':')
            address = (ip, int(port))
        except ValueError:
            print(f"非法客户端ID格式: {client_id}")
            return
        
        # 发射信号
        self.update_signal.emit(display_msg)

    def _detect_data_type(self, data: bytes) -> str:
        """精确数据类型检测"""
        try:
            text = data.decode('utf-8')
            if all(31 < c < 127 or c in (9,10,13) for c in data):
                return 'text'
            return 'hex'
        except UnicodeDecodeError:
            return 'hex'

    def _format_display(self, data_type: str, data: bytes, client_id: str) -> str:
        """生成带格式的消息"""
        parts = []
        if self.display_options['show_time']:
            parts.append(time.strftime("[%H:%M:%S]"))
        if self.display_options['show_client']:
            parts.append(f"[{client_id}]")
        
        content = self._get_content(data_type, data)
        return ' '.join(parts + [content])

    def _get_content(self, data_type: str, data: bytes) -> str:
        """获取数据内容部分"""
        if data_type == 'text':
            text = data.decode('utf-8', errors='replace')[:50]
            return f'<font color="blue">文本: {text}</font>'
        else:
            hex_str = ' '.join(f'{b:02X}' for b in data[:8])
            if len(data) > 8:
                hex_str += '...'
            return f'<font color="gray">HEX: {hex_str}</font>'

    def _parse_address(self, client_id):
        ip, port = client_id.split(':')
        return (ip, int(port)) 

    def set_display_format(self, show_time=True, show_client=True):
        """设置显示格式
        参数：
            show_time - 显示时间戳 (默认True)
            show_client - 显示客户端ID (默认True)
        """
        self.display_options.update({
            'show_time': show_time,
            'show_client': show_client
        }) 