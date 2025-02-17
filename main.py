import PyQt5
from PyQt5.QtWidgets import QMainWindow

import sys
import threading
import os
import time

from Module.Tcp import TcpLogic
from UI.MainWindow import MainWindowLogic
from Module.RingBuffer import BufferManager
from Module.DataProcessor import DataProcessor


class MainWindow(MainWindowLogic, TcpLogic):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.buffer_manager = BufferManager()
        self.processor = DataProcessor(self.buffer_manager)
        self.proc_thread = threading.Thread(target=self.processor.start_processing)
        self.proc_thread.start()

        # 确保信号正确连接
        self.tcp_signal_write_msg.connect(self.msg_write)
        self.link_signal.connect(self.link_signal_handler)
        self.disconnect_signal.connect(self.disconnect_signal_handler)
        self.processor.update_signal.connect(self.msg_write)
        self.processor.waveform_signal.connect(self.update_waveform)
        self.filename_signal.connect(self.filename_signal_handler)

    def filename_signal_handler(self, filename):
        """处理文件导入信号"""
        # 创建独立线程处理文件
        file_thread = threading.Thread(target=self.process_file_data, args=(filename,))
        file_thread.start()

    def process_file_data(self, filename):
        """处理文本格式的十六进制数据"""
        client_id = f"file_{os.path.basename(filename)}"
        try:
            with open(filename, 'r') as f:
                # 读取并清理数据
                hex_str = ''.join([line.strip().replace(' ', '') for line in f])
                
                # 转换为字节数据
                byte_data = bytes.fromhex(hex_str)
                
                # 分割6字节数据包
                packet_size = 6
                packets = [byte_data[i:i+packet_size] 
                          for i in range(0, len(byte_data), packet_size)]
                
                # 模拟实时发送
                total = len(packets)
                for i, packet in enumerate(packets):
                    if len(packet) == packet_size:
                        self.buffer_manager.add_data(client_id, packet)
                        # time.sleep(0.001)  # 1ms间隔，约1000Hz
                    
                    # 每处理1000个包更新进度
                    if i % 1000 == 0:
                        progress = (i+1)/total*100
                        print(f"文件回放进度: {progress:.1f}%")
        except Exception as e:
            print(f"文件处理错误: {str(e)}")

    def link_signal_handler(self, port):
        # 仅处理TCP服务端启动

        self.tcp_server_start(port)

    def disconnect_signal_handler(self):
        if self.link_flag == self.ServerTCP:
            self.tcp_close()

    def run(self):
        self.show()  # 显示界面

    def closeEvent(self, event):
        self.processor.running = False
        self.proc_thread.join()
        super().closeEvent(event)

    def set_display_format(self, show_time=True, show_client=True):
        """设置消息显示格式"""
        self.processor.set_display_format(show_time, show_client)


# 主程序入口
if __name__ == "__main__":
    app = PyQt5.QtWidgets.QApplication(sys.argv)
    ui = MainWindow()
    ui.run()  # ui就会显示出来
    sys.exit(app.exec_())
