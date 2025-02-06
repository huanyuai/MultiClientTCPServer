"""
数据处理器 - 负责实时处理网络数据流
功能：
1. 多协议数据解析
2. 自动数据类型识别
3. 批量波形数据处理
4. 线程安全的消息格式化
"""

import struct
import time
from collections import defaultdict
from PyQt5.QtCore import pyqtSignal, QObject

class DataProcessor(QObject):
    """主数据处理引擎"""
    update_signal = pyqtSignal(str)      # 文本更新信号
    waveform_signal = pyqtSignal(str, list)  # 波形数据信号 (客户端ID, [(时间戳, 值)])
    
    def __init__(self, buffer_manager):
        """
        初始化参数
        :param buffer_manager: 环形缓冲区管理器
        """
        super().__init__()
        self.buffer_manager = buffer_manager
        self.running = True
        
        # 显示配置
        self._display_config = {'show_time': True, 'show_client': True}
        
        # 波形处理
        self.batch_size = 200  # 每200个点发送一次
        self.waveform_cache = defaultdict(list)

    def start_processing(self):
        """主处理循环（线程安全版）"""
        while self.running:
            has_data = False
            # 获取当前客户端快照
            with self.buffer_manager.lock:
                clients = list(self.buffer_manager.buffers.items())
            
            for client_id, buffer in clients:
                # 批量读取数据（8KB/次）
                while (data := buffer.get(8192)):
                    self._process_client(client_id, data)
                    has_data = True
                    if len(data) >= 8192 * 4:
                        break
            if not has_data:
                time.sleep(0.05)

    def _process_client(self, client_id, data):
        """处理单个客户端数据"""
        # 消息处理
        self.update_signal.emit(self._format_msg(data, client_id))
        
        # 波形处理
        if waveform := self._process_waveform(data):
            self._handle_waveform(client_id, waveform)

    def _format_msg(self, data, client_id) -> str:
        """生成格式化消息"""
        parts = []
        # 时间戳
        if self._display_config['show_time']:
            parts.append(time.strftime("[%H:%M:%S]"))
        # 客户端标识
        if self._display_config['show_client']:
            parts.append(f"[{client_id}]")
        # 内容部分
        parts.append(self._content_repr(data))
        return ' '.join(parts)

    def _content_repr(self, data) -> str:
        """数据内容表示"""
        try:  # 尝试文本解码
            text = data.decode('utf-8', errors='replace')[:50]
            return self._text_repr(text) if self._is_printable(text) else self._hex_repr(data)
        except UnicodeDecodeError:
            return self._hex_repr(data)

    def _process_waveform(self, data):
        """解析波形数据并返回所有有效值"""
        values = []
        for i in range(0, len(data), 6):
            packet = data[i:i+6]
            if len(packet) == 6 and packet[:2] == b'\x62\x74':
                value = struct.unpack('<I', packet[2:6])[0] / 1000.0
                values.append(value)
        return values

    def _handle_waveform(self, client_id, values):
        """完整发送所有数据点"""
        self.waveform_signal.emit(client_id, values)  # 实时发送所有数据

    @staticmethod
    def _is_printable(text) -> bool:
        """检查可打印字符"""
        return all(31 < ord(c) < 127 or c in '\t\n\r' for c in text)

    @staticmethod
    def _text_repr(text) -> str:
        """文本表示"""
        return f'<font color="blue">文本: {text}</font>'

    @staticmethod
    def _hex_repr(data) -> str:
        """HEX表示"""
        hex_str = ' '.join(f'{b:02X}' for b in data)
        return f'<font color="gray">HEX: {hex_str}</font>'

    def set_display_format(self, show_time=True, show_client=True):
        """设置显示格式"""
        self._display_config.update(show_time=show_time, show_client=show_client)


