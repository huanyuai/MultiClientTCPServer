"""
数据处理器 - 负责实时处理网络数据流
功能：
1. 多协议数据解析 - 支持文本和二进制数据的自动识别与解析
2. 自动数据类型识别 - 智能判断数据类型并选择合适的显示方式
3. 批量波形数据处理 - 高效处理大量波形数据点
4. 线程安全的消息格式化 - 确保多线程环境下的数据安全
"""

import struct  # 用于二进制数据解析
import time    # 用于时间戳生成
from PyQt5.QtCore import pyqtSignal, QObject, QThread, QMutex

class DataProcessThread(QThread):
    """数据处理线程"""
    
    def __init__(self, processor, parent=None):
        """
        初始化数据处理线程
        :param processor: 数据处理器实例
        :param parent: 父对象
        """
        super().__init__(parent)
        self.processor = processor
        self.running = True
    
    def run(self):
        """线程运行函数"""
        while self.running:
            # 处理队列中的数据
            self.processor.process_queue()
            # 短暂休眠，减少CPU占用
            self.msleep(30)
    
    def stop(self):
        """停止线程"""
        self.running = False
        self.wait()


class DataProcessor(QObject):
    """
    主数据处理引擎
    继承自QObject以支持Qt信号机制
    """
    # 定义两个信号用于UI更新
    text_signal = pyqtSignal(str)         # 文本更新信号，发送格式化后的消息字符串
    waveform_signal = pyqtSignal(str, list)  # 波形数据信号，发送客户端ID和数据点列表
    
    def __init__(self, parent=None):
        """
        初始化数据处理器
        """
        super().__init__(parent)
        self.data_queue = {}  # 客户端数据队列
        self.mutex = QMutex()  # 用于线程同步
        
        # 消息显示配置选项
        self._display_config = {
            'show_time': True,    # 是否显示时间戳
            'show_client': True   # 是否显示客户端ID
        }
        
        # 创建并启动处理线程
        self.process_thread = DataProcessThread(self, self)
        self.process_thread.start()
    
    def add_data(self, client_id, data):
        """
        添加数据到处理队列
        :param client_id: 客户端标识符
        :param data: 原始数据
        """
        self.mutex.lock()
        if client_id not in self.data_queue:
            self.data_queue[client_id] = []
        self.data_queue[client_id].append(data)
        self.mutex.unlock()
    
    def process_queue(self):
        """处理队列中的所有数据"""
        self.mutex.lock()
        queue_snapshot = {k: v.copy() for k, v in self.data_queue.items() if v}
        # 清空原队列
        for client_id in queue_snapshot:
            self.data_queue[client_id] = []
        self.mutex.unlock()
        
        # 处理数据快照
        for client_id, data_list in queue_snapshot.items():
            for data in data_list:
                self._process_client_data(client_id, data)
    
    def _process_client_data(self, client_id, data):
        """
        处理单个客户端的数据
        :param client_id: 客户端标识符
        :param data: 待处理的原始数据
        """
        # 生成并发送消息到UI
        self.text_signal.emit(self._format_msg(data, client_id))
        
        # 尝试解析波形数据并处理
        if waveform := self._process_waveform(data):
            self.waveform_signal.emit(client_id, waveform)  # 实时发送所有数据点

    def _format_msg(self, data, client_id) -> str:
        """
        生成格式化消息
        :param data: 原始数据
        :param client_id: 客户端标识符
        :return: 格式化后的HTML消息字符串
        """
        parts = []
        # 添加时间戳
        if self._display_config['show_time']:
            parts.append(time.strftime("[%H:%M:%S]"))
        # 添加客户端标识
        if self._display_config['show_client']:
            parts.append(f"[{client_id}]")
        # 添加数据内容
        parts.append(self._content_repr(data))
        return ' '.join(parts)

    def _content_repr(self, data) -> str:
        """
        智能判断并格式化数据内容
        :param data: 原始数据
        :return: 格式化后的HTML字符串
        """
        try:  # 尝试UTF-8文本解码
            text = data.decode('utf-8', errors='replace')[:50]  # 限制长度避免过长
            return self._text_repr(text) if self._is_printable(text) else self._hex_repr(data)
        except UnicodeDecodeError:
            return self._hex_repr(data)

    def _process_waveform(self, data):
        """
        解析波形数据
        :param data: 原始数据
        :return: 解析出的波形值列表
        格式: 每6字节一组,前2字节为标识符0x62 0x74,后4字节为有符号整数值
        """
        values = []
        for i in range(0, len(data), 6):
            packet = data[i:i+6]
            if len(packet) == 6 and packet[:2] == b'\x62\x74':
                value = -struct.unpack('<I', packet[2:6])[0]/ 10000.0  # 转换为实际值
                values.append(value)
        return values

    @staticmethod
    def _is_printable(text) -> bool:
        """
        检查文本是否可打印
        :param text: 待检查文本
        :return: 是否全部为可打印字符
        """
        return all(31 < ord(c) < 127 or c in '\t\n\r' for c in text)

    @staticmethod
    def _text_repr(text) -> str:
        """
        生成文本数据的HTML表示
        :param text: 文本内容
        :return: 带颜色的HTML字符串
        """
        return f'<font color="blue">文本: {text}</font>'

    @staticmethod
    def _hex_repr(data) -> str:
        """
        生成二进制数据的十六进制HTML表示
        :param data: 二进制数据
        :return: 带颜色的HTML字符串
        """
        hex_str = ' '.join(f'{b:02X}' for b in data[:16])  # 只显示前16个字节
        if len(data) > 16:
            hex_str += f' ... (共{len(data)}字节)'
        return f'<font color="gray">HEX: {hex_str}</font>'

    def set_display_format(self, show_time=True, show_client=True):
        """
        设置消息显示格式
        :param show_time: 是否显示时间戳
        :param show_client: 是否显示客户端ID
        """
        self._display_config.update(show_time=show_time, show_client=show_client)
    
    def close(self):
        """关闭处理器，停止线程"""
        if hasattr(self, 'process_thread'):
            self.process_thread.stop()